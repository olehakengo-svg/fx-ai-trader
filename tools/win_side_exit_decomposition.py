#!/usr/bin/env python3
"""Win-side exit decomposition — なぜ avg_win が縮んだのかを実測で分解する。

背景: 2026-09-13 cell deepdive (`knowledge-base/raw/cell_deepdive/2026-09-13/`) が
`sr_anti_hunt_bounce` の R:R 反転 (2.30 → 0.25) を検出し、その主因が「負け拡大」ではなく
**avg_win の 1/5 への縮小** (19.03p → 3.5〜5.9p) であることを特定した。本ツールはその
avg_win 縮小を close_reason / MFE capture / pair mix の3軸へ帰属させる。

estimand (宣言):
  対象 = 指定 entry_type の **closed trade** のうち **指定 stream (既定 shadow) のみ** /
  XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}。
  avg_win = outcome=WIN 行の pnl_pips 平均 (pips)。
  比較は clean cohort のみ (pre = exit < 遷移窓 START / post = entry ≥ 遷移窓 END)。
  「市場機会」の比較は固定ホライズン excursion (§6, --bars-dir) で行う — exit 非依存を意図するが、約定建玉ゆえ建玉ゲート経由の選別が残る (CONTROL_SELECTION_CAVEAT)。
  「勝ち側 capture」= WIN 行の pnl_pips / mafe_favorable_pips。
  ⚠️ close_reason="SL_HIT" は BE/トレール利確も含む混成ラベル
  (MEMORY project_sl_hit_label_collision)。よって全ての close_reason 分解は
  **outcome で必ず分割**して読む。close_reason 単独での集計は行わない。

出力は stdout の Markdown。副作用なし。

Usage:
  curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" -o /tmp/prod_trades.json
  python3 tools/win_side_exit_decomposition.py /tmp/prod_trades.json --strategy sr_anti_hunt_bounce
  python3 tools/win_side_exit_decomposition.py /tmp/prod_trades.json --strategy ALL \
      --stream shadow --bars-dir <{PAIR}_1m.parquet のディレクトリ>   # §6 exit 非依存対照つき
  (data/cache/massive の 1m キャッシュは 2026-04-15 前後で終わるので、対象期間を覆う 1m を
   MASSIVE から取得したディレクトリを渡すこと。被覆しない pair は common_coverage で落ちる)
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── shadow exit regime break ──────────────────────────────────────────────
# commit ab7a4931 "fix(exit): persist shadow SL changes directly to DB" 以前、
# shadow trade の SL 変更は OandaBridge.modify_sl_sync の False 戻りにより毎 iteration
# ロールバックされていた。すなわち BE-lock / SMC BE+0.1 / ATR×0.8 BE / ATR×1.5 trail /
# v6.4 TP extender の **全てが shadow 上で dead code** だった
# (lesson-shadow-sl-rollback-bug-2026-06-03)。帰結: この遷移の前後で shadow の payoff
# 統計 (avg_win / R:R / WR / hold time) は **別の estimand** になる。
#
# 境界は 1 点ではなく **遷移窓** [START, END) として扱う (PR #253 review 4002255783):
#   START = commit object の時刻 2026-06-03T07:58:28Z。fix はこれより前に稼働し得ない。
#           (旧定数 "07:58" は分切り捨てで、07:58:00–07:58:27 を誤って post に入れていた)
#   END   = Render の deploy 完了時刻は記録が無い (Render workspace 未選択 / KB・lesson に
#           時刻記載なし)。挙動の証拠: shadow で最初の「WIN かつ close_reason=SL_HIT」
#           (BE/trail が利益側で刈った署名、pre-fix 前日まで日次 0%) は exit 08:01:26Z、
#           以後連続。よって fix は遅くとも 08:01:26Z には稼働。保守的に 09:00:00Z まで
#           (約 1 時間) を不確実窓として除外する。感度は --transition-end で確認する。
# 主要の比較は clean cohort のみで行う (PR #253 review 4002219368):
#   clean pre  = exit_time  <  START  (全保有期間が fix 前)
#   clean post = entry_time >= END    (全保有期間が fix 後)
#   それ以外 (遷移窓を跨ぐ・窓内で建つ) は除外し、件数を別報告する。
SHADOW_EXIT_REGIME_BREAK = "2026-06-03T07:58:28+00:00"          # 遷移窓 START (commit 時刻)
SHADOW_EXIT_REGIME_FIRST_SIGNATURE = "2026-06-03T08:01:26+00:00"  # 挙動上の稼働確認 (上限)
SHADOW_EXIT_REGIME_TRANSITION_END = "2026-06-03T09:00:00+00:00"   # 保守的除外窓 END (既定)

PIP_JPY = 0.01
PIP_OTHER = 0.0001


def month_of(iso: str | None) -> str:
    return (iso or "")[:7] or "unknown"


def parse_ts(iso: str | None) -> datetime | None:
    """ISO 文字列 → aware UTC datetime。文字列比較は秒/小数/TZ 表記揺れで誤るため使わない。"""
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _hold_hours(entry_iso: str | None, exit_iso: str | None) -> float | None:
    a, b = parse_ts(entry_iso), parse_ts(exit_iso)
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 3600.0


def stream_of(t: dict) -> str:
    """Live/Shadow 厳格分離 (MEMORY feedback_live_vs_shadow_strict_separation)。

    live   = oanda_trade_id != ''  (is_shadow=0 単独では live と判定しない)
    shadow = oanda_trade_id == '' かつ is_shadow == 1
    それ以外 (is_shadow=0 かつ oanda_trade_id 無し) = ambiguous — どちらにも入れない。
    """
    if str(t.get("oanda_trade_id") or "").strip():
        return "live"
    if t.get("is_shadow") in (1, True, "1"):
        return "shadow"
    return "ambiguous"


def load_clean(path: str, strategy: str | None, stream: str = "shadow",
               outcomes: tuple[str, ...] | None = ("WIN", "LOSS")) -> list[dict]:
    """stream ∈ {"shadow", "live"}。既定は shadow — ab7a4931 が変えたのは shadow 執行のみ
    (PR #253 review 4002219365: live 行を混ぜると境界の比較が交絡する)。

    outcomes=None は outcome で選ばない (BREAKEVEN / 未決済も含む全 entry)。
    exit 非依存の対照 (§6) はこちらを使う — BE/trail は ±0.5p 以内の決済 = BREAKEVEN を
    生むので、WIN/LOSS 限定の母集団は exit 機構に選別されている (PR #310 review 4151271131)。
    """
    if stream not in ("shadow", "live"):
        raise ValueError(f"stream must be 'shadow' or 'live', got {stream!r}")
    with open(path) as f:
        payload = json.load(f)
    out = []
    for t in payload.get("trades", []):
        if strategy and t.get("entry_type") != strategy:
            continue
        if stream_of(t) != stream:
            continue
        if "XAU" in (t.get("instrument") or ""):
            continue
        if t.get("dedup_violation") == 1:
            continue
        if outcomes is not None and t.get("outcome") not in outcomes:
            continue
        out.append({
            "trade_id": t.get("id"),
            "entry_type": t.get("entry_type"),
            "instrument": t.get("instrument"),
            "direction": t.get("direction"),
            "win": t.get("outcome") == "WIN",
            "pnl": float(t.get("pnl_pips") or 0.0),
            "mfe": float(t.get("mafe_favorable_pips") or 0.0),
            "mae": float(t.get("mafe_adverse_pips") or 0.0),
            "reason": t.get("close_reason") or "(null)",
            "entry_time": t.get("entry_time"),
            "exit_time": t.get("exit_time"),
            "entry_dt": parse_ts(t.get("entry_time")),
            "exit_dt": parse_ts(t.get("exit_time")),
            "entry_price": float(t["entry_price"]) if t.get("entry_price") not in (None, "") else None,
            "hold_h": _hold_hours(t.get("entry_time"), t.get("exit_time")),
            "month": month_of(t.get("entry_time")),
            "is_shadow": stream == "shadow",
            "stream": stream,
        })
    return out


def split_cohorts(rows: list[dict], start: str, end: str | None = None
                  ) -> tuple[list[dict], list[dict], list[dict]]:
    """clean pre / clean post / 除外 (遷移窓に掛かる建玉) へ分割する。

    clean pre  = exit_time  <  start   (保有期間全体が fix 前)
    clean post = entry_time >= end     (保有期間全体が fix 後)
    それ以外 = excluded (境界を跨ぐ / 遷移窓内で建つ / 時刻欠損)。
    entry_time だけで振り分けると、fix 前に建って fix 後に BE/trail を受けた建玉が
    pre 群に混入する (PR #253 review 4002219368)。
    """
    s = parse_ts(start)
    e = parse_ts(end) if end else s
    if s is None or e is None or e < s:
        raise ValueError(f"invalid transition window [{start}, {end})")
    pre, post, excl = [], [], []
    for r in rows:
        en, ex = r.get("entry_dt"), r.get("exit_dt")
        if ex is not None and ex < s:
            pre.append(r)
        elif en is not None and en >= e:
            post.append(r)
        else:
            excl.append(r)
    return pre, post, excl


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def fmt(x: float | None, nd: int = 2) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def period_key(r: dict) -> str:
    """月キー。main が付けた cohort があれば境界月を pre/post に割る
    (境界月 2026-06 を 1 行に混ぜると別 estimand の合算になる)。"""
    c = r.get("cohort")
    m = r["month"]
    return f"{m}·{c}" if c and m == r.get("split_month") else m


def summary_row(rows: list[dict]) -> dict:
    """N / WR / avg_win / avg_loss / R:R / EV / WIN 行の SL_HIT 率。"""
    w = [r["pnl"] for r in rows if r["win"]]
    l = [-r["pnl"] for r in rows if not r["win"]]
    aw, al = mean(w), mean(l)
    sl_win = sum(1 for r in rows if r["win"] and r["reason"] == "SL_HIT")
    return {
        "n": len(rows), "wr": (len(w) / len(rows)) if rows else None,
        "avg_win": aw if w else None, "avg_loss": al if l else None,
        "rr": (aw / al) if (w and al > 0) else None,
        "ev": mean([r["pnl"] for r in rows]) if rows else None,
        "slhit_win_share": (sl_win / len(w)) if w else None,
    }


def monthly_table(rows: list[dict]) -> str:
    by_m = defaultdict(list)
    for r in rows:
        by_m[period_key(r)].append(r)
    lines = ["| month | N | WR | avg_win | avg_loss | R:R | EV_net |",
             "|---|---|---|---|---|---|---|"]
    for m in sorted(by_m):
        rs = by_m[m]
        w = [r["pnl"] for r in rs if r["win"]]
        l = [-r["pnl"] for r in rs if not r["win"]]
        aw, al = mean(w), mean(l)
        rr = (aw / al) if al > 0 else None
        lines.append(f"| {m} | {len(rs)} | {len(w)/len(rs):.1%} | {fmt(aw) if w else '—'} | "
                     f"{fmt(al) if l else '—'} | {fmt(rr)} | {mean([r['pnl'] for r in rs]):+.2f} |")
    return "\n".join(lines)


def reason_outcome_table(rows: list[dict], label: str) -> str:
    """close_reason × outcome。SL_HIT ラベル衝突があるため outcome 分割は必須。"""
    g = defaultdict(list)
    for r in rows:
        g[(r["reason"], "WIN" if r["win"] else "LOSS")].append(r)
    reasons = sorted({k[0] for k in g})
    lines = [f"**{label}**", "",
             "| close_reason | N_win | avg_win | N_loss | avg_loss | win_share |",
             "|---|---|---|---|---|---|"]
    tot_w = sum(1 for r in rows if r["win"])
    for rsn in reasons:
        w = [x["pnl"] for x in g.get((rsn, "WIN"), [])]
        l = [-x["pnl"] for x in g.get((rsn, "LOSS"), [])]
        share = (len(w) / tot_w) if tot_w else 0.0
        lines.append(f"| {rsn} | {len(w)} | {fmt(mean(w)) if w else '—'} | {len(l)} | "
                     f"{fmt(mean(l)) if l else '—'} | {share:.1%} |")
    return "\n".join(lines)


def shift_share(rows_a: list[dict], rows_b: list[dict], key: str) -> tuple[str, float, float]:
    """avg_win の A→B 変化を mix 効果 / within 効果へ分解 (Oaxaca 型)。

    avg_win = Σ_k s_k * m_k  (s = 構成比, m = 群内 avg_win)
    Δ = Σ_k (s_k^B - s_k^A) * m_k^A   [mix]
      + Σ_k s_k^B * (m_k^B - m_k^A)   [within]
    群が片側にしか無い場合、その群の欠側 m は反対側の全体 avg_win で代用 (保守的)。
    """
    wa = [r for r in rows_a if r["win"]]
    wb = [r for r in rows_b if r["win"]]
    if not wa or not wb:
        return "(片側に WIN 行が無く分解不能)", 0.0, 0.0
    ga, gb = defaultdict(list), defaultdict(list)
    for r in wa:
        ga[r[key]].append(r["pnl"])
    for r in wb:
        gb[r[key]].append(r["pnl"])
    base_a, base_b = mean([r["pnl"] for r in wa]), mean([r["pnl"] for r in wb])
    keys = sorted(set(ga) | set(gb))
    mix = within = 0.0
    lines = ["| " + key + " | share_A | avg_win_A | share_B | avg_win_B | mix寄与 | within寄与 |",
             "|---|---|---|---|---|---|---|"]
    for k in keys:
        sa = len(ga.get(k, [])) / len(wa)
        sb = len(gb.get(k, [])) / len(wb)
        ma = mean(ga[k]) if k in ga else base_a
        mb = mean(gb[k]) if k in gb else base_b
        c_mix = (sb - sa) * ma
        c_within = sb * (mb - ma)
        mix += c_mix
        within += c_within
        lines.append(f"| {k} | {sa:.1%} | {fmt(ma)} | {sb:.1%} | {fmt(mb)} | {c_mix:+.2f} | {c_within:+.2f} |")
    lines.append(f"| **合計** | | **{fmt(base_a)}** | | **{fmt(base_b)}** | **{mix:+.2f}** | **{within:+.2f}** |")
    return "\n".join(lines), mix, within


def capture_table(rows: list[dict]) -> str:
    """勝ち側 capture = realized / MFE。roadmap v2.3 T3 の capture 0.0944 と同じ軸。"""
    by_m = defaultdict(list)
    for r in rows:
        if r["win"] and r["mfe"] > 0:
            by_m[period_key(r)].append(r)
    lines = ["| month | N_win(MFE>0) | avg_MFE | avg_win | capture | 取り残し |",
             "|---|---|---|---|---|---|"]
    for m in sorted(by_m):
        rs = by_m[m]
        amfe, apnl = mean([r["mfe"] for r in rs]), mean([r["pnl"] for r in rs])
        lines.append(f"| {m} | {len(rs)} | {fmt(amfe)} | {fmt(apnl)} | "
                     f"{fmt(apnl/amfe, 3) if amfe > 0 else '—'} | {fmt(amfe-apnl)} |")
    return "\n".join(lines)


def hold_hours(rows: list[dict], win: bool = True) -> str:
    """WIN (または LOSS) 行の保有時間。

    ⚠️ 保有時間は exit 機構そのものの関数。exit 機構の変化の **記述** には使えるが、
    市場機会の対照には使えない (PR #253 review 4002255778)。
    中央値は偶数コホートで上側中央値にならないよう statistics.median
    (PR #253 review 4002219370)。
    """
    by_m = defaultdict(list)
    for r in rows:
        if r["win"] == win and r["hold_h"] is not None:
            by_m[period_key(r)].append(r["hold_h"])
    lab = "WIN" if win else "LOSS"
    lines = [f"| month | N_{lab} | median_hold_h | avg_hold_h |", "|---|---|---|---|"]
    for m in sorted(by_m):
        h = by_m[m]
        lines.append(f"| {m} | {len(h)} | {fmt(statistics.median(h))} | {fmt(mean(h))} |")
    return "\n".join(lines)


# ── exit 非依存を意図した対照: 固定ホライズン excursion ──────────────────────

# 生成レポートにも KB と同じ caveat を出す (PR #310 review 4152175652 / 4152231474)
CONTROL_SELECTION_CAVEAT = (
    "> ⚠️ **この対照は完全な exit 非依存ではない**: 母集団は約定した建玉であり、建玉上限 / "
    "post-exit cooldown のゲートを経由するため、BE/trail で早く決済されると枠が空いて post 期に "
    "別の entry が入りうる (= exit regime による選別)。点推定の大きさで市場寄与を上限評価する "
    "解釈 (例: 『振幅縮小は avg_win の縮小を説明できない』) はしない。真の対照はゲート前の候補シグナル基準 (未実施)。"
)
# mafe_favorable_pips は全行で exit 時点に censored されるため、exit 機構が変わると
# 機械的に動く (PR #253 review 4002255778)。entry 時刻・entry 価格・方向だけを使い、
# 価格バー (既定 1m) で [entry, entry + H] にクリップした窓の最大有利/不利幅を測れば、
# exit 機構に依存しない市場側の順行余地になる。
# 注: バーは MASSIVE (mid 系)、entry_price は OANDA 側の約定想定値で、
# 半スプレッド程度の basis が両期間に対称に乗る。1m 足なら窓の先頭・末尾のずれは各 ≤1 分。

def pip_size(instrument: str | None) -> float:
    return PIP_JPY if "JPY" in (instrument or "") else PIP_OTHER


def load_bars(bars_dir: str, instrument: str, tf: str = "1m"):
    import pandas as pd  # 遅延 import (§0-§5 は pandas 不要)
    p = Path(bars_dir) / f"{instrument}_{tf}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df.rename(columns={c: c.capitalize() for c in df.columns})
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df.sort_index()


def fixed_horizon_excursion(row: dict, bars, horizon_min: int, bar_minutes: int = 1,
                            max_gap_min: int = 5) -> tuple[float, float] | None:
    """(favorable_pips, adverse_pips) — **[entry, entry + horizon_min] にクリップした窓**。

    窓 = 開始が ceil(entry, bar) 以上 かつ 終了 (開始 + bar) が entry + horizon 以下の
    バーだけ。1m 足なら測定窓は名目 horizon から先頭・末尾とも ≤1 分しかずれない。
    旧実装 (entry 以後の最初の 15m バーから H 本) は非整列 entry で先頭最大 15 分を欠き
    末尾に最大 15 分を足していた (PR #310 review 4151347679)。

    exit_time / close_reason / mafe_* は一切参照しない (exit 非依存)。
    None = entry 情報欠損 / 窓にバー無し / 窓の先頭・末尾の欠落 > max_gap_min − bar_minutes /
    内部の隣接バー間隔 > max_gap_min (週末・ベンダー欠損を跨ぐ窓を黙って混ぜない、
    PR #310 review 4151253825)。15m 足で使う場合は max_gap_min=15 で厳密連続になる。
    """
    import pandas as pd
    en, px = row.get("entry_dt"), row.get("entry_price")
    d = (row.get("direction") or "").upper()
    if bars is None or en is None or px is None or d not in ("BUY", "SELL"):
        return None
    ts = pd.Timestamp(en)
    step = pd.Timedelta(minutes=bar_minutes)
    start = ts.ceil(f"{bar_minutes}min")
    # 末尾の期待開始は選択した足のグリッド上で取る (非整列 entry × >1m 足で有効窓を欠落扱いしない、PR #310 review 4152127036)
    last_start = (ts + pd.Timedelta(minutes=horizon_min)).floor(f"{bar_minutes}min") - step
    if last_start < start:
        return None
    lo_i = bars.index.searchsorted(start, side="left")
    hi_i = bars.index.searchsorted(last_start, side="right")
    w = bars.iloc[lo_i:hi_i]
    if len(w) == 0:
        return None
    edge = pd.Timedelta(minutes=max_gap_min) - step
    if (w.index[0] - start) > edge or (last_start - w.index[-1]) > edge:
        return None
    if len(w) > 1 and ((w.index[1:] - w.index[:-1]) > pd.Timedelta(minutes=max_gap_min)).any():
        return None
    ps = pip_size(row.get("instrument"))
    hi, lo = float(w["High"].max()), float(w["Low"].min())
    # 起点からの excursion は負にならない (本番 MAFE と同じく 0 で clamp、PR #310 review 4151271136)
    if d == "BUY":
        return max(0.0, (hi - px) / ps), max(0.0, (px - lo) / ps)
    return max(0.0, (px - lo) / ps), max(0.0, (hi - px) / ps)


def overlap_blocks(entry_dts: list, horizon_min: int) -> list[int]:
    """excursion 窓 [entry, entry + horizon] が重なる (連鎖的に繋がる) 観測を同じブロックにする。

    UTC 日でブロックを切ると、日付境界を跨いで重なる 240 分窓が別ブロックに分かれ、
    従属な観測を独立に resample してしまう (PR #310 review 4152000632)。時刻順に並べ、
    次の entry が現ブロック内の窓の最遅終端より後になった時点で新ブロックを開始する。
    戻り値は入力と同順のブロック番号。
    """
    from datetime import timedelta as _td
    order = sorted(range(len(entry_dts)), key=lambda i: entry_dts[i])
    out = [0] * len(entry_dts)
    blk, end = -1, None
    for i in order:
        t = entry_dts[i]
        if end is None or t > end:
            blk += 1
            end = t + _td(minutes=horizon_min)
        else:
            end = max(end, t + _td(minutes=horizon_min))
        out[i] = blk
    return out


def boot_median_diff(a: list[float], b: list[float], n: int = 2000, seed: int = 0,
                     a_blocks: list | None = None, b_blocks: list | None = None,
                     min_blocks: int = 5) -> tuple[float, float] | None:
    """median(b) − median(a) の percentile bootstrap 95% CI。

    a_blocks / b_blocks (値と同順のブロックキー) を渡すと **ブロック bootstrap**:
    同じブロック (例: overlap_blocks の重なり窓ブロック) の観測をまとめて復元抽出する。同時刻に複数の
    pair / 戦略が発火すると excursion 窓が重なり強く従属するので、行単位の i.i.d.
    resample は CI を不当に狭くする (PR #310 review 4151311925)。

    どちらかの群のブロック数が min_blocks 未満なら None (CI 算出不可) を返す —
    ブロック 1 個では全 resample が同一になり、幅ゼロの退化した「95% CI」を出してしまう
    (PR #310 review 4151937674)。
    """
    rng = random.Random(seed)

    def groups(vals, keys):
        if keys is None:
            return [[v] for v in vals]
        g = defaultdict(list)
        for v, k in zip(vals, keys):
            g[k].append(v)
        return list(g.values())

    ga, gb = groups(a, a_blocks), groups(b, b_blocks)
    if len(ga) < min_blocks or len(gb) < min_blocks:
        return None

    def draw(gs):
        out = []
        for _ in range(len(gs)):
            out.extend(gs[rng.randrange(len(gs))])
        return out

    ds = []
    for _ in range(n):
        ds.append(statistics.median(draw(gb)) - statistics.median(draw(ga)))
    ds.sort()
    return ds[int(0.025 * n)], ds[int(0.975 * n) - 1]


def type_matched_means(pre: list[tuple[str, float]], post: list[tuple[str, float]]
                       ) -> tuple[float, float, int, float] | None:
    """entry_type 構成を揃えた pre/post 平均 (両側に在る type のみ、重み = pre の構成比)。

    戻り値 = (pre 平均, post 再重み付け平均, 共通 type 数, 共通 type が覆う pre 行の比率)。
    pre 側も **同じ共通 type 集合** に制限する — pre 全体の平均と post の再重み付け
    平均を比べると、片側にしか無い type の分だけ比較対象がずれる。
    """
    ga, gb = defaultdict(list), defaultdict(list)
    for k, v in pre:
        ga[k].append(v)
    for k, v in post:
        gb[k].append(v)
    keys = [k for k in ga if k in gb]
    n_common = sum(len(ga[k]) for k in keys)
    if not keys or n_common == 0:
        return None
    w = {k: len(ga[k]) / n_common for k in keys}
    return (sum(w[k] * mean(ga[k]) for k in keys),
            sum(w[k] * mean(gb[k]) for k in keys),
            len(keys), n_common / len(pre))


def match_key(row: dict) -> str:
    """構成揃え mean のセルキー = instrument × entry_type × direction。

    direction を含めないと、セル内の BUY/SELL 構成シフトで有利/不利幅の点推定が動く
    (PR #310 review 4152312707、registry review-backlog-310-p2-excursion-input-snapshot)。
    direction 欠損は "?" で独立セルにし、BUY/SELL と混ぜない。
    """
    d = (row.get("direction") or "").upper() or "?"
    return f"{row.get('instrument')}|{row.get('entry_type')}|{d}"


def split_entries(rows: list[dict], start: str, end: str) -> tuple[list[dict], list[dict]]:
    """exit 非依存の対照用: entry 時刻だけで pre (< START) / post (>= END) に分ける。

    固定ホライズン excursion は市場の性質で exit 機構を通らないので、exit_time を
    分割に使わない (使うと「いつ決済されたか」= exit 機構で母集団が選ばれる)。
    """
    s, e = parse_ts(start), parse_ts(end)
    pre = [r for r in rows if r.get("entry_dt") is not None and r["entry_dt"] < s]
    post = [r for r in rows if r.get("entry_dt") is not None and r["entry_dt"] >= e]
    return pre, post


def drop_boundary_crossing(pre: list[dict], start: str, horizon_min: int) -> list[dict]:
    """pre のうち excursion 窓 [entry, entry + horizon] が遷移窓 START を越える行を落とす。

    越える pre 窓は、遷移窓 (~1 時間) の直後に建った post 窓と同じ価格バーを共有し得るので、
    群ごとに別々に作ったブロックでは独立に resample されてしまう (PR #310 review 4152047567)。
    pre 窓を START 以前で閉じれば、post 窓 (END 以降に開始) とは必ず交わらない。
    """
    from datetime import timedelta as _td
    s = parse_ts(start)
    return [r for r in pre if r.get("entry_dt") is not None
            and r["entry_dt"] + _td(minutes=horizon_min) <= s]


def common_coverage(pre: list[dict], post: list[dict], bar_end: dict[str, object],
                    horizon_min: int, fresh_slack_days: int = 7,
                    bar_start: dict[str, object] | None = None):
    """pre/post を **同じ instrument 集合 × 同じ時間被覆** に揃える (PR #310 review 4151253820)。

    キャッシュ終端が pair ごとに違う (07-21 で切れる pair がある) と、post 側だけ一部 pair の
    行が黙って落ち、pre と post で instrument 構成が別物になる (cache-selection bias)。
    S = キャッシュ終端が最新終端から fresh_slack_days 以内の instrument。
    cutoff = S の最短終端 − horizon。両群とも instrument ∈ S ∧ entry_dt ≤ cutoff に制限する。
    戻り値 = (pre', post', S, cutoff)。bar_end = {instrument: 最終バー時刻 or None}。
    bar_start (任意) を渡すと、キャッシュ始端が両群の最早 entry より後の instrument も S から
    外す (始端側の非対称 = pre だけが落ちる型を同様に防ぐ)。
    """
    from datetime import timedelta as _td
    ends = {k: v for k, v in bar_end.items() if v is not None}
    if not ends:
        return [], [], set(), None
    latest = max(ends.values())
    S = {k for k, v in ends.items() if v >= latest - _td(days=fresh_slack_days)}
    if bar_start is not None:
        dts = [r["entry_dt"] for r in pre + post if r.get("entry_dt") is not None]
        if dts:
            first = min(dts)
            S = {k for k in S if bar_start.get(k) is not None and bar_start[k] <= first}
        if not S:
            return [], [], set(), None
    cutoff = min(ends[k] for k in S) - _td(minutes=horizon_min)

    def keep(r):
        return r["instrument"] in S and r.get("entry_dt") is not None and r["entry_dt"] <= cutoff
    return [r for r in pre if keep(r)], [r for r in post if keep(r)], S, cutoff


def excursion_control_table(pre: list[dict], post: list[dict], bars_dir: str,
                            horizons: tuple[int, ...] = (60, 240), bars_tf: str = "1m",
                            split_start: str | None = None,
                            freeze: dict | None = None) -> str:
    """horizons は分。bars_tf の足で [entry, entry + horizon] にクリップして測る。

    split_start を渡すと、窓が START を越える pre 行を horizon ごとに落とす
    (drop_boundary_crossing — 群を跨ぐ窓の重なりを無くす)。

    freeze (dict) を渡すと per-entry の派生結果 (trade_id / cohort / horizon / fav / adv /
    block_id / match_key) と被覆の計数を書き込む — write_freeze() がリポジトリに凍結する
    (registry review-backlog-310-p2-excursion-input-snapshot: 入力未凍結の表は再現不能)。
    """
    cache: dict[str, object] = {}
    bar_min = int(bars_tf.rstrip("m"))
    max_gap = max(5, bar_min)

    def bars_for(inst):
        if inst not in cache:
            cache[inst] = load_bars(bars_dir, inst, bars_tf)
        return cache[inst]

    lines = ["| horizon | 群 | N (被覆) | 被覆率 (共通被覆内) | median 有利幅 | mean 有利幅 | median 不利幅 | "
             "mean 不利幅 | median 有利/不利 比 |",
             "|---|---|---|---|---|---|---|---|---|"]
    notes = []
    insts = {r["instrument"] for r in pre + post}
    bar_end, bar_start = {}, {}
    for i in insts:
        b = bars_for(i)
        ok = b is not None and len(b)
        bar_end[i] = b.index[-1].to_pydatetime() if ok else None
        bar_start[i] = b.index[0].to_pydatetime() if ok else None
    for h in horizons:
        hpre = drop_boundary_crossing(pre, split_start, h) if split_start else pre
        cpre, cpost, S, cutoff = common_coverage(hpre, post, bar_end, h, bar_start=bar_start)
        notes.append(f"- {h} 分: 共通被覆 = instrument {sorted(S)} / entry ≤ "
                     f"{cutoff.isoformat() if cutoff else '—'} — 除外 pre {len(hpre) - len(cpre)} 行 / "
                     f"post {len(post) - len(cpost)} 行 / 窓が START を越える pre {len(pre) - len(hpre)} 行")
        if freeze is not None:
            freeze.setdefault("common_coverage", []).append({
                "horizon_min": h, "instruments": sorted(S),
                "entry_cutoff": cutoff.isoformat() if cutoff else None,
                "pre_dropped_coverage": len(hpre) - len(cpre), "post_dropped_coverage": len(post) - len(cpost),
                "pre_dropped_boundary_crossing": len(pre) - len(hpre)})
        res = {}
        for lab, rows in (("pre", cpre), ("post", cpost)):
            fav, adv, tf, ta, days, kept = [], [], [], [], [], []
            for r in rows:
                x = fixed_horizon_excursion(r, bars_for(r["instrument"]), h, bar_min, max_gap)
                if x is None:
                    continue
                days.append(r["entry_dt"])
                fav.append(x[0])
                adv.append(x[1])
                key = match_key(r)
                tf.append((key, x[0]))
                ta.append((key, x[1]))
                kept.append(r)
            blocks = overlap_blocks(days, h)
            res[lab] = (fav, adv, tf, ta, len(rows), blocks)
            if freeze is not None:
                for r, f_, a_, b_ in zip(kept, fav, adv, blocks):
                    freeze.setdefault("rows", []).append({
                        "trade_id": r.get("trade_id"), "instrument": r.get("instrument"),
                        "entry_type": r.get("entry_type"), "direction": (r.get("direction") or "").upper(),
                        "entry_time": r.get("entry_time"), "cohort": lab, "horizon_min": h,
                        "favorable_pips": round(f_, 4), "adverse_pips": round(a_, 4),
                        "block_id": b_, "match_key": match_key(r)})
                freeze.setdefault("coverage", []).append({
                    "horizon_min": h, "cohort": lab, "rows_in_coverage": len(rows),
                    "rows_measured": len(fav), "blocks": len(set(blocks))})
        for lab in ("pre", "post"):
            fav, adv, _, _, n_all, _ = res[lab]
            if not fav:
                lines.append(f"| {h} 分 | {lab} | 0 | — | — | — | — | — | — |")
                continue
            ma = statistics.median(adv)
            lines.append(
                f"| {h} 分 | {lab} | {len(fav)} | {len(fav) / n_all:.1%} | "
                f"{fmt(statistics.median(fav))} | {fmt(mean(fav))} | "
                f"{fmt(ma)} | {fmt(mean(adv))} | "
                f"{fmt(statistics.median(fav) / ma, 3) if ma > 0 else '—'} |")
        fa, fb = res["pre"][0], res["post"][0]
        if len(fa) >= 2 and len(fb) >= 2:
            ci = boot_median_diff(fa, fb, a_blocks=res["pre"][5], b_blocks=res["post"][5])
            ci_txt = (f"重なり窓ブロック bootstrap 95% [{ci[0]:+.2f}, {ci[1]:+.2f}]" if ci
                      else "CI 算出不可 — ブロック不足")
            notes.append(f"- {h} 分: median 有利幅 post−pre = "
                         f"{statistics.median(fb) - statistics.median(fa):+.2f}p "
                         f"({ci_txt}、ブロック数 pre {len(set(res['pre'][5]))} / post {len(set(res['post'][5]))})")
            tmf = type_matched_means(res["pre"][2], res["post"][2])
            tma = type_matched_means(res["pre"][3], res["post"][3])
            if tmf and tma:
                notes.append(f"  - instrument×entry_type×direction 構成を揃えた mean (共通 {tmf[2]} cell, pre 行の "
                             f"{tmf[3]:.1%}): 有利幅 pre {tmf[0]:.2f} → post {tmf[1]:.2f}p / "
                             f"不利幅 pre {tma[0]:.2f} → post {tma[1]:.2f}p")
    return "\n".join(lines) + ("\n\n" + "\n".join(notes) if notes else "")


def sha256_file(path: str | Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


FREEZE_FILES = ("excursion_per_entry.csv", "manifest.json", "report.md")


def _atomic_write(path: Path, data: str, *, newline: str | None = None) -> None:
    """同 dir の一時ファイルに書いて rename — 途中失敗で壊れた凍結を残さない。"""
    import os
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline=newline) as f:
        f.write(data)
    os.replace(tmp, path)


def write_freeze(freeze_dir: str, freeze: dict, *, trades_json: str, trades_rows: int,
                 trades_fetched_at: str | None, bars_dir: str, bars_tf: str,
                 instruments: list[str], bars_fetched_at: str | None, params: dict,
                 overwrite: bool = False) -> dict:
    """§6 の入力と per-entry 派生結果をリポジトリに凍結する (再現性の担保)。

    - excursion_per_entry.csv: 行 = (trade_id, cohort, horizon) ごとの fav / adv / block_id / match_key
    - manifest.json: trades_json の sha256 / 行数 / 取得時刻、bars ファイルごとの sha256 / 行数 / 先頭・末尾、
      取得パラメータ (horizons / split / stream / strategy / bars_tf / match_key)、tool の git HEAD
    値を再計算せずとも表の数値は CSV から再集計でき、入力の同一性は sha256 で検証できる。

    既存の凍結 dir には書かない (overwrite=False、PR #328 review 4266607770): KB が引用中の snapshot を
    黙って置換しない。別入力なら別 dir を切る。生成元は git HEAD だけでなく本スクリプトの content sha256 と
    dirty 状態も記録する (PR #328 review 4266607766: 未コミット変更で生成すると HEAD は親 commit を指す)。
    """
    import csv
    import subprocess
    out = Path(freeze_dir)
    existing = [n for n in FREEZE_FILES if (out / n).exists()]
    if existing and not overwrite:
        raise SystemExit(f"freeze dir {out} に既存の凍結 {existing} がある — 別 dir を切るか --freeze-overwrite を明示せよ")
    out.mkdir(parents=True, exist_ok=True)
    rows = freeze.get("rows", [])
    cols = ["trade_id", "instrument", "entry_type", "direction", "entry_time", "cohort",
            "horizon_min", "favorable_pips", "adverse_pips", "block_id", "match_key"]
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in cols})
    _atomic_write(out / "excursion_per_entry.csv", buf.getvalue(), newline="")
    files = {}
    for inst in sorted(instruments):
        p = Path(bars_dir) / f"{inst}_{bars_tf}.parquet"
        if not p.exists():
            files[inst] = None
            continue
        b = load_bars(bars_dir, inst, bars_tf)
        files[inst] = {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size,
                       "rows": int(len(b)), "first": b.index[0].isoformat(), "last": b.index[-1].isoformat()}
    tool_path = Path(__file__).resolve()
    repo = tool_path.parents[1]
    head, dirty = None, None
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True, timeout=10).stdout.strip() or None
        st = subprocess.run(["git", "status", "--porcelain", "--", str(tool_path)], cwd=repo,
                            capture_output=True, text=True, timeout=10)
        dirty = bool(st.stdout.strip()) if st.returncode == 0 else None
    except Exception:  # noqa: BLE001 — git 不在でも凍結は書く (sha256 が生成元の同一性を担う)
        pass
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": {"path": "tools/win_side_exit_decomposition.py", "sha256": sha256_file(tool_path),
                 "git_head": head, "git_dirty": dirty,
                 "note": "生成元の同一性は sha256 で検証する (git_dirty=true なら git_head は親 commit で、生成コードを含まない)"},
        "trades_json": {"path": str(trades_json), "sha256": sha256_file(trades_json),
                        "bytes": Path(trades_json).stat().st_size, "rows_in_payload": trades_rows,
                        "fetched_at": trades_fetched_at,
                        "source": "/api/demo/trades (可変 endpoint — 同一性は sha256 でのみ主張する)"},
        "bars": {"dir": str(bars_dir), "tf": bars_tf, "fetched_at": bars_fetched_at,
                 "source": "MASSIVE (tools/fetch_massive_data.py)", "files": files},
        "params": dict(params, match_key="instrument|entry_type|direction"),
        "common_coverage": freeze.get("common_coverage", []),
        "coverage": freeze.get("coverage", []),
        "rows_written": len(rows),
    }
    _atomic_write(out / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    """--freeze-dir 指定時は report 本文を明示ストリームに集め、凍結ガード通過後に report.md も同 dir へ
    原子的に書く (PR #328 review 4266657605: shell redirect は in-process ガードより先に report を切り詰める)。

    2026-10-15 (rule:R3): `contextlib.redirect_stdout` は **プロセス全体の sys.stdout** を差し替えるため、
    同プロセスの他スレッド (pytest では先行 test が起動した demo_trader の daemon MainLoop: `[MainLoop/scalp]
    tick #1 ok …`) の print が report.md の先頭に混入した (main CI 2026-10-15T03:13Z 実測、`startswith` pin が
    検知)。report は `_run(out=)` に渡した StringIO にだけ書き、グローバル stdout は差し替えない。"""
    import io
    import sys
    args = _parse_args()
    if not args.freeze_dir:
        _run(args)
        return
    buf = io.StringIO()
    _run(args, out=buf)  # 既存凍結があれば write_freeze が SystemExit → report も書かない
    # report を先に永続 — stdout が先に閉じていても (| head / CI cancel) 部分凍結を残さない (PR #328 review 4266711506)
    _atomic_write(Path(args.freeze_dir) / "report.md", buf.getvalue())
    sys.stdout.write(buf.getvalue())


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("trades_json")
    ap.add_argument("--strategy", default="sr_anti_hunt_bounce",
                    help="entry_type。'ALL' で全戦略横断")
    ap.add_argument("--stream", default="shadow", choices=("shadow", "live"),
                    help="shadow = oanda_trade_id 無し ∧ is_shadow=1 (既定) / "
                         "live = oanda_trade_id != ''。両 stream を混ぜた集計はしない")
    ap.add_argument("--split-at", default=SHADOW_EXIT_REGIME_BREAK,
                    help="遷移窓 START。clean pre = exit_time < これ "
                         f"(既定 = commit ab7a4931 時刻 {SHADOW_EXIT_REGIME_BREAK})")
    ap.add_argument("--transition-end", default=SHADOW_EXIT_REGIME_TRANSITION_END,
                    help="遷移窓 END。clean post = entry_time >= これ "
                         f"(既定 = 保守的除外窓 {SHADOW_EXIT_REGIME_TRANSITION_END})")
    ap.add_argument("--bars-dir", default=None,
                    help="{PAIR}_{TF}.parquet のディレクトリ。指定時のみ §6 対照 (exit 非依存を意図、選別 caveat 付き) を出す")
    ap.add_argument("--bars-tf", default="1m",
                    help="§6 の足 (既定 1m — 窓を entry から ≤1 分精度でクリップできる)")
    ap.add_argument("--freeze-dir", default=None,
                    help="§6 の per-entry 派生結果 (CSV) + 入力 sha256 / 取得パラメータ (manifest.json) を書く先 "
                         "(--bars-dir 必須)。無指定の §6 は再現不能な一回限りの記述になる")
    ap.add_argument("--trades-fetched-at", default=None, help="trades_json の取得時刻 (ISO、manifest に記録)")
    ap.add_argument("--bars-fetched-at", default=None, help="bars の取得時刻 (ISO、manifest に記録)")
    ap.add_argument("--freeze-overwrite", action="store_true",
                    help="既存の凍結 dir を置換する (既定は拒否 — KB が引用中の snapshot を守る)")
    args = ap.parse_args()
    if args.freeze_dir and not args.bars_dir:
        ap.error("--freeze-dir は --bars-dir と併用する")
    return args


def _run(args: argparse.Namespace, out=None) -> None:
    """本体。`out` を渡すと report 本文はそこにだけ書く (既定 = sys.stdout)。
    グローバル stdout の差し替えに頼らないので、他スレッドの print が report に混入しない。"""
    import functools
    import sys
    _p = functools.partial(print, file=(out if out is not None else sys.stdout))
    strat = None if args.strategy == "ALL" else args.strategy
    rows = load_clean(args.trades_json, strat, args.stream)
    if not rows:
        raise SystemExit(f"no clean rows for {args.strategy} / stream={args.stream}")

    a, b, excl = split_cohorts(rows, args.split_at, args.transition_end)
    split_month = month_of(args.split_at)
    for lab, grp in (("pre", a), ("post", b)):
        for r in grp:
            r["cohort"], r["split_month"] = lab, split_month
    clean = a + b

    _p(f"# Win-side exit decomposition — {args.strategy} / stream={args.stream}\n")
    _p(f"- N = **{len(rows)}** (stream={args.stream} / XAU除外 / dedup除外 / outcome∈{{WIN,LOSS}})")
    _p(f"- span: {min(r['entry_time'] or '' for r in rows)} → {max(r['entry_time'] or '' for r in rows)}")
    _p(f"- 遷移窓 [{args.split_at}, {args.transition_end})")
    _p(f"- clean pre (exit < START) N={len(a)} / clean post (entry ≥ END) N={len(b)} / "
          f"**除外 (窓を跨ぐ・窓内で建つ) N={len(excl)}**")
    if excl:
        ex = summary_row(excl)
        _p(f"  - 除外群: WR {fmt(ex['wr'], 3)} / avg_win {fmt(ex['avg_win'])} / "
              f"WIN 行 SL_HIT 率 {fmt(ex['slhit_win_share'], 3)}")
    _p()

    _p("## 0. 期間サマリ (clean cohort)\n")
    _p("| 群 | N | WR | avg_win | avg_loss | R:R | EV | WIN 行の SL_HIT 率 |")
    _p("|---|---|---|---|---|---|---|---|")
    for lab, grp in (("pre", a), ("post", b)):
        sr = summary_row(grp)
        _p(f"| {lab} | {sr['n']} | {fmt(sr['wr'], 3)} | {fmt(sr['avg_win'])} | {fmt(sr['avg_loss'])} | "
              f"{fmt(sr['rr'])} | {fmt(sr['ev'])} | {fmt(sr['slhit_win_share'], 3)} |")
    _p()

    _p("## 1. 月次ペイオフ (境界月は pre/post に分割、除外群は含まない)\n")
    _p(monthly_table(clean), "\n")

    _p("## 2. close_reason × outcome (SL_HIT ラベル衝突対応)\n")
    _p(reason_outcome_table(a, "clean pre"), "\n")
    _p(reason_outcome_table(b, "clean post"), "\n")

    _p("## 3. avg_win 変化の帰属 — shift-share 分解\n")
    for key, label in (("reason", "close_reason 軸"), ("instrument", "pair 軸")):
        tbl, mix, within = shift_share(a, b, key)
        d = mix + within
        _p(f"### {label}\n")
        _p(tbl, "\n")
        if d:
            _p(f"→ Δavg_win = {d:+.2f}p のうち mix {mix:+.2f}p ({mix/d:.0%}) / "
                  f"within {within:+.2f}p ({within/d:.0%})\n")

    _p("## 4. 勝ち側 capture (realized / MFE) — exit 機構の記述のみ\n")
    _p("> ⚠️ MFE は exit 時点までしか観測されない (全行で censored)。exit を早めると測定 MFE は"
          "機械的に縮む。市場機会の対照には使えない — §6 を見ること。\n")
    _p(capture_table(clean), "\n")

    _p("## 5. 保有時間 (exit 機構の記述指標 — 市場対照ではない)\n")
    _p(hold_hours(clean, win=True), "\n")
    _p(hold_hours(clean, win=False), "\n")

    if args.bars_dir:
        _p(f"## 6. exit 非依存を意図した対照 (exit regime による選別あり) — 固定ホライズン excursion ([entry, entry+H] を {args.bars_tf} 足でクリップ)\n")
        _p(CONTROL_SELECTION_CAVEAT + "\n")
        ent = load_clean(args.trades_json, strat, args.stream, outcomes=None)
        ea, eb = split_entries(ent, args.split_at, args.transition_end)
        _p(f"> 母集団 = outcome を問わない全 entry (BREAKEVEN / 未決済を含む) N={len(ent)}、"
              f"entry 時刻だけで分割 (pre {len(ea)} / post {len(eb)})。excursion は 0 で clamp。\n")
        freeze: dict | None = {} if args.freeze_dir else None
        _p(excursion_control_table(ea, eb, args.bars_dir, bars_tf=args.bars_tf,
                                      split_start=args.split_at, freeze=freeze), "\n")
        if freeze is not None:
            with open(args.trades_json) as f:
                n_payload = len(json.load(f).get("trades", []))
            m = write_freeze(args.freeze_dir, freeze, trades_json=args.trades_json, trades_rows=n_payload,
                             trades_fetched_at=args.trades_fetched_at, bars_dir=args.bars_dir,
                             bars_tf=args.bars_tf, instruments=sorted({r["instrument"] for r in ent}),
                             bars_fetched_at=args.bars_fetched_at,
                             params={"strategy": args.strategy, "stream": args.stream,
                                     "split_at": args.split_at, "transition_end": args.transition_end,
                                     "horizons_min": [60, 240], "bars_tf": args.bars_tf,
                                     "population": "outcome を問わない全 entry (XAU 除外 / dedup 除外)"},
                             overwrite=args.freeze_overwrite)
            _p(f"> 🧊 入力凍結: `{args.freeze_dir}/excursion_per_entry.csv` ({m['rows_written']} 行) + "
                  f"`manifest.json` (trades sha256 {m['trades_json']['sha256'][:12]}…, bars {len(m['bars']['files'])} pair) + "
                  f"`report.md` (本出力)\n")


if __name__ == "__main__":
    main()
