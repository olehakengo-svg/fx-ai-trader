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
  「市場機会」の比較は exit 非依存の固定ホライズン excursion (§6, --bars-dir) でのみ行う。
  「勝ち側 capture」= WIN 行の pnl_pips / mafe_favorable_pips。
  ⚠️ close_reason="SL_HIT" は BE/トレール利確も含む混成ラベル
  (MEMORY project_sl_hit_label_collision)。よって全ての close_reason 分解は
  **outcome で必ず分割**して読む。close_reason 単独での集計は行わない。

出力は stdout の Markdown。副作用なし。

Usage:
  curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" -o /tmp/prod_trades.json
  python3 tools/win_side_exit_decomposition.py /tmp/prod_trades.json --strategy sr_anti_hunt_bounce
  python3 tools/win_side_exit_decomposition.py /tmp/prod_trades.json --strategy ALL \
      --stream shadow --bars-dir data/cache/massive    # §6 exit 非依存対照つき
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


# ── exit 非依存の対照: 固定ホライズン excursion ────────────────────────────
# mafe_favorable_pips は全行で exit 時点に censored されるため、exit 機構が変わると
# 機械的に動く (PR #253 review 4002255778)。entry 時刻・entry 価格・方向だけを使い、
# 価格バーから「entry 以後の最初の 15m バーから H 本」の最大有利/不利幅を測れば、
# exit 機構に依存しない市場側の順行余地になる。
# 注: バーは MASSIVE 15m (mid 系)、entry_price は OANDA 側の約定想定値で、
# 半スプレッド程度の basis が両期間に対称に乗る。entry〜次バー開始 (<15 分) は窓外。

def pip_size(instrument: str | None) -> float:
    return PIP_JPY if "JPY" in (instrument or "") else PIP_OTHER


def load_bars(bars_dir: str, instrument: str, tf: str = "15m"):
    import pandas as pd  # 遅延 import (§0-§5 は pandas 不要)
    p = Path(bars_dir) / f"{instrument}_{tf}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df.rename(columns={c: c.capitalize() for c in df.columns})
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df.sort_index()


def fixed_horizon_excursion(row: dict, bars, horizon_bars: int,
                            bar_minutes: int = 15) -> tuple[float, float] | None:
    """(favorable_pips, adverse_pips) — entry 以後の最初のバーから horizon_bars 本。

    exit_time / close_reason / mafe_* は一切参照しない (exit 非依存)。
    None = entry 情報欠損 / バー不足 / 最初のバーが entry から 1 本分以上遅い /
    窓内に 1 本でも欠落 (連続バーの間隔が bar_minutes と一致しない — 週末・ベンダー欠損)。
    総 span だけの判定は内部欠落を通してしまう (PR #310 review 4151253825)。
    """
    import pandas as pd
    en, px = row.get("entry_dt"), row.get("entry_price")
    d = (row.get("direction") or "").upper()
    if bars is None or en is None or px is None or d not in ("BUY", "SELL"):
        return None
    ts = pd.Timestamp(en)
    i = bars.index.searchsorted(ts, side="left")
    w = bars.iloc[i:i + horizon_bars]
    if len(w) < horizon_bars:
        return None
    if w.index[0] - ts > pd.Timedelta(minutes=bar_minutes):
        return None
    step = pd.Timedelta(minutes=bar_minutes)
    if horizon_bars > 1 and not (w.index[1:] - w.index[:-1] == step).all():
        return None
    ps = pip_size(row.get("instrument"))
    hi, lo = float(w["High"].max()), float(w["Low"].min())
    # 起点からの excursion は負にならない (本番 MAFE と同じく 0 で clamp、PR #310 review 4151271136)
    if d == "BUY":
        return max(0.0, (hi - px) / ps), max(0.0, (px - lo) / ps)
    return max(0.0, (px - lo) / ps), max(0.0, (hi - px) / ps)


def boot_median_diff(a: list[float], b: list[float], n: int = 2000, seed: int = 0
                     ) -> tuple[float, float]:
    """median(b) − median(a) の percentile bootstrap 95% CI。"""
    rng = random.Random(seed)
    ds = []
    for _ in range(n):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        ds.append(statistics.median(rb) - statistics.median(ra))
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


def split_entries(rows: list[dict], start: str, end: str) -> tuple[list[dict], list[dict]]:
    """exit 非依存の対照用: entry 時刻だけで pre (< START) / post (>= END) に分ける。

    固定ホライズン excursion は市場の性質で exit 機構を通らないので、exit_time を
    分割に使わない (使うと「いつ決済されたか」= exit 機構で母集団が選ばれる)。
    """
    s, e = parse_ts(start), parse_ts(end)
    pre = [r for r in rows if r.get("entry_dt") is not None and r["entry_dt"] < s]
    post = [r for r in rows if r.get("entry_dt") is not None and r["entry_dt"] >= e]
    return pre, post


def common_coverage(pre: list[dict], post: list[dict], bar_end: dict[str, object],
                    horizon_bars: int, bar_minutes: int = 15, fresh_slack_days: int = 7):
    """pre/post を **同じ instrument 集合 × 同じ時間被覆** に揃える (PR #310 review 4151253820)。

    キャッシュ終端が pair ごとに違う (07-21 で切れる pair がある) と、post 側だけ一部 pair の
    行が黙って落ち、pre と post で instrument 構成が別物になる (cache-selection bias)。
    S = キャッシュ終端が最新終端から fresh_slack_days 以内の instrument。
    cutoff = S の最短終端 − horizon。両群とも instrument ∈ S ∧ entry_dt ≤ cutoff に制限する。
    戻り値 = (pre', post', S, cutoff)。bar_end = {instrument: 最終バー時刻 or None}。
    """
    from datetime import timedelta as _td
    ends = {k: v for k, v in bar_end.items() if v is not None}
    if not ends:
        return [], [], set(), None
    latest = max(ends.values())
    S = {k for k, v in ends.items() if v >= latest - _td(days=fresh_slack_days)}
    cutoff = min(ends[k] for k in S) - _td(minutes=bar_minutes * horizon_bars)

    def keep(r):
        return r["instrument"] in S and r.get("entry_dt") is not None and r["entry_dt"] <= cutoff
    return [r for r in pre if keep(r)], [r for r in post if keep(r)], S, cutoff


def excursion_control_table(pre: list[dict], post: list[dict], bars_dir: str,
                            horizons: tuple[int, ...] = (4, 16)) -> str:
    cache: dict[str, object] = {}

    def bars_for(inst):
        if inst not in cache:
            cache[inst] = load_bars(bars_dir, inst)
        return cache[inst]

    lines = ["| horizon | 群 | N (被覆) | 被覆率 (共通被覆内) | median 有利幅 | mean 有利幅 | median 不利幅 | "
             "mean 不利幅 | median 有利/不利 比 |",
             "|---|---|---|---|---|---|---|---|---|"]
    notes = []
    insts = {r["instrument"] for r in pre + post}
    bar_end = {}
    for i in insts:
        b = bars_for(i)
        bar_end[i] = b.index[-1].to_pydatetime() if b is not None and len(b) else None
    for h in horizons:
        cpre, cpost, S, cutoff = common_coverage(pre, post, bar_end, h)
        notes.append(f"- {h * 15} 分: 共通被覆 = instrument {sorted(S)} / entry ≤ "
                     f"{cutoff.isoformat() if cutoff else '—'} — 除外 pre {len(pre) - len(cpre)} 行 / "
                     f"post {len(post) - len(cpost)} 行")
        res = {}
        for lab, rows in (("pre", cpre), ("post", cpost)):
            fav, adv, tf, ta = [], [], [], []
            for r in rows:
                x = fixed_horizon_excursion(r, bars_for(r["instrument"]), h)
                if x is None:
                    continue
                fav.append(x[0])
                adv.append(x[1])
                key = f"{r['instrument']}|{r['entry_type']}"
                tf.append((key, x[0]))
                ta.append((key, x[1]))
            res[lab] = (fav, adv, tf, ta, len(rows))
        for lab in ("pre", "post"):
            fav, adv, _, _, n_all = res[lab]
            if not fav:
                lines.append(f"| {h * 15} 分 ({h} 本) | {lab} | 0 | — | — | — | — | — | — |")
                continue
            ma = statistics.median(adv)
            lines.append(
                f"| {h * 15} 分 ({h} 本) | {lab} | {len(fav)} | {len(fav) / n_all:.1%} | "
                f"{fmt(statistics.median(fav))} | {fmt(mean(fav))} | "
                f"{fmt(ma)} | {fmt(mean(adv))} | "
                f"{fmt(statistics.median(fav) / ma, 3) if ma > 0 else '—'} |")
        fa, fb = res["pre"][0], res["post"][0]
        if len(fa) >= 2 and len(fb) >= 2:
            lo, hi = boot_median_diff(fa, fb)
            notes.append(f"- {h * 15} 分: median 有利幅 post−pre = "
                         f"{statistics.median(fb) - statistics.median(fa):+.2f}p "
                         f"(bootstrap 95% [{lo:+.2f}, {hi:+.2f}])")
            tmf = type_matched_means(res["pre"][2], res["post"][2])
            tma = type_matched_means(res["pre"][3], res["post"][3])
            if tmf and tma:
                notes.append(f"  - instrument×entry_type 構成を揃えた mean (共通 {tmf[2]} cell, pre 行の "
                             f"{tmf[3]:.1%}): 有利幅 pre {tmf[0]:.2f} → post {tmf[1]:.2f}p / "
                             f"不利幅 pre {tma[0]:.2f} → post {tma[1]:.2f}p")
    return "\n".join(lines) + ("\n\n" + "\n".join(notes) if notes else "")


def main() -> None:
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
                    help="{PAIR}_15m.parquet のディレクトリ。指定時のみ §6 exit 非依存対照を出す")
    args = ap.parse_args()

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

    print(f"# Win-side exit decomposition — {args.strategy} / stream={args.stream}\n")
    print(f"- N = **{len(rows)}** (stream={args.stream} / XAU除外 / dedup除外 / outcome∈{{WIN,LOSS}})")
    print(f"- span: {min(r['entry_time'] or '' for r in rows)} → {max(r['entry_time'] or '' for r in rows)}")
    print(f"- 遷移窓 [{args.split_at}, {args.transition_end})")
    print(f"- clean pre (exit < START) N={len(a)} / clean post (entry ≥ END) N={len(b)} / "
          f"**除外 (窓を跨ぐ・窓内で建つ) N={len(excl)}**")
    if excl:
        ex = summary_row(excl)
        print(f"  - 除外群: WR {fmt(ex['wr'], 3)} / avg_win {fmt(ex['avg_win'])} / "
              f"WIN 行 SL_HIT 率 {fmt(ex['slhit_win_share'], 3)}")
    print()

    print("## 0. 期間サマリ (clean cohort)\n")
    print("| 群 | N | WR | avg_win | avg_loss | R:R | EV | WIN 行の SL_HIT 率 |")
    print("|---|---|---|---|---|---|---|---|")
    for lab, grp in (("pre", a), ("post", b)):
        sr = summary_row(grp)
        print(f"| {lab} | {sr['n']} | {fmt(sr['wr'], 3)} | {fmt(sr['avg_win'])} | {fmt(sr['avg_loss'])} | "
              f"{fmt(sr['rr'])} | {fmt(sr['ev'])} | {fmt(sr['slhit_win_share'], 3)} |")
    print()

    print("## 1. 月次ペイオフ (境界月は pre/post に分割、除外群は含まない)\n")
    print(monthly_table(clean), "\n")

    print("## 2. close_reason × outcome (SL_HIT ラベル衝突対応)\n")
    print(reason_outcome_table(a, "clean pre"), "\n")
    print(reason_outcome_table(b, "clean post"), "\n")

    print("## 3. avg_win 変化の帰属 — shift-share 分解\n")
    for key, label in (("reason", "close_reason 軸"), ("instrument", "pair 軸")):
        tbl, mix, within = shift_share(a, b, key)
        d = mix + within
        print(f"### {label}\n")
        print(tbl, "\n")
        if d:
            print(f"→ Δavg_win = {d:+.2f}p のうち mix {mix:+.2f}p ({mix/d:.0%}) / "
                  f"within {within:+.2f}p ({within/d:.0%})\n")

    print("## 4. 勝ち側 capture (realized / MFE) — exit 機構の記述のみ\n")
    print("> ⚠️ MFE は exit 時点までしか観測されない (全行で censored)。exit を早めると測定 MFE は"
          "機械的に縮む。市場機会の対照には使えない — §6 を見ること。\n")
    print(capture_table(clean), "\n")

    print("## 5. 保有時間 (exit 機構の記述指標 — 市場対照ではない)\n")
    print(hold_hours(clean, win=True), "\n")
    print(hold_hours(clean, win=False), "\n")

    if args.bars_dir:
        print("## 6. exit 非依存の対照 — 固定ホライズン excursion (entry 以後の 15m バー H 本)\n")
        ent = load_clean(args.trades_json, strat, args.stream, outcomes=None)
        ea, eb = split_entries(ent, args.split_at, args.transition_end)
        print(f"> 母集団 = outcome を問わない全 entry (BREAKEVEN / 未決済を含む) N={len(ent)}、"
              f"entry 時刻だけで分割 (pre {len(ea)} / post {len(eb)})。excursion は 0 で clamp。\n")
        print(excursion_control_table(ea, eb, args.bars_dir), "\n")


if __name__ == "__main__":
    main()
