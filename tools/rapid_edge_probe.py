#!/usr/bin/env python3
"""rapid_edge_probe.py — S2 (R3 診断) 共通ハーネス: 仮説スペック 1 ファイル → 標準診断レポート.

位置づけ (edge-development-pipeline-2026-07-18 §2 S2):
  仮説の「爆速実装→テスト」フローの探索段を標準化する。YAML/JSON スペック 1 枚から
  探索窓のみで IC / 摩擦調整 EV / N / fold 3 分割安定性 / 発火頻度を計測し、
  S3 pre-reg 起案に値するかの**目安** (判定ではない) を印字する。

**規律 (組み込みで強制)**:
  - 探索診断 ≠ 判定。本ツールの出力から live/tier 判断は禁止 (レポートヘッダに自動印字)。
  - OOS 窓 (2024-01-01〜) はデフォルト構造遮断 — bars を load 直後に物理スライスするため、
    エンジンのどの段も OOS バーに触れない。明示 flag (--unlock-oos) + 警告なしにアクセス不能。
  - falsified 6 系統 + 価格モダリティ 3 周の再試行チェックリストをレポートに自動表示。
  - seed 固定 (SEED)。silent except 禁止 (skip は全て理由付きカウント)。
  - モジュールトップ副作用禁止 (import 時に I/O / argparse / thread を実行しない)。

再利用 (再発明禁止):
  - estimand コア = tools/event_modality_lib.py (§3.5 SSOT: ATR14d/σ_h、first-touch SL 優先、
    NY17:00 roll daily、coverage gate、E1 §3.4 凍結摩擦テーブル、USD-leg 方向変換)
  - IC 規律 = channel_edge_ic_explore.py と同型 (Spearman、閾値最適化禁止、causal 特徴のみ)
  - データ = data/cache/massive/{PAIR}_15m.parquet (12y フル版、部分 parquet 罠に注意)
  - イベントカレンダー = knowledge-base/raw/bt-results/e15_e7_event_calendar.json

スペック小語彙 (これ以外は ValueError — 語彙を増やす時は本ファイルと使い方 doc を同時更新):
  direction_source.kind : event | series | technical
    event    : {event: NFP|CPI|FOMC, rule: fade|follow|uncond_usd_long|uncond_usd_short, w0_min}
    series   : {column, file (csv; date + per-pair 列 or column 単列), lag_days}
               column が "__dummy" 始まり = 決定的ダミー ±1 (構造検証専用、エッジ期待ゼロ)
    technical: {condition: momentum_sign|ema_trend, lookback / fast+slow}
  entry_trigger.kind    : none | breakout | pullback
  holding.mode          : bars | first_touch (TP=SL=σ_h × tp_sigma/sl_sigma、SL 優先)
  horizons              : M15 bar 数 (int) or 名前 h1/h4/h12/h24

CLI:
  python3 tools/rapid_edge_probe.py run --spec tools/rapid_probe_specs/nfp_usd_24h.json
  python3 tools/rapid_edge_probe.py run --spec ... --draft-prereg   # pre-reg スケルトン自動 draft
  python3 tools/rapid_edge_probe.py self-test                        # 合成データ dry-run (data 不要)

使い方 1 ページ: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_modality_lib as L  # noqa: E402

# ─── 定数 (モジュールトップは定数のみ — I/O 副作用なし) ─────────────────────
SEED = 20260722                    # 乱数はダミー series 生成のみ。診断本体に乱数なし。
EXPLORE_START_DEFAULT = "2014-01-01"
EXPLORE_END = "2023-12-31"         # 探索窓終端。OOS = 2024-01-01〜 (E15/E1 と同一境界)
OOS_BOUNDARY_UTC = "2024-01-01"    # この時刻以降の bar は構造遮断 (明示 unlock なしで不可視)

MASSIVE_DIR = os.path.join(_REPO, "data", "cache", "massive")
CALENDAR_JSON = os.path.join(_REPO, "knowledge-base", "raw", "bt-results",
                             "e15_e7_event_calendar.json")
DEFAULT_OUTDIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results")
PREREG_OUTDIR = os.path.join(_REPO, "knowledge-base", "wiki", "decisions")

VOCAB_DIRECTION_KINDS = ("event", "series", "technical")
VOCAB_EVENT_RULES = ("fade", "follow", "uncond_usd_long", "uncond_usd_short")
VOCAB_EVENTS = ("NFP", "CPI", "FOMC")
VOCAB_TECHNICAL = ("momentum_sign", "ema_trend")
VOCAB_TRIGGERS = ("none", "breakout", "pullback")
VOCAB_HOLDING = ("bars", "first_touch")
NAMED_HORIZONS = dict(L.HORIZON_BARS)  # {"h1":4,"h4":16,"h12":48,"h24":96}

# S3 起案検討の**目安** (判定ではない — レポートに明記して印字)
GUIDE_MIN_N = 60
GUIDE_MIN_FOLD_AGREE = 2   # /3
GUIDE_MIN_PAIR_POS_FRAC = 0.5

DISCIPLINE_HEADER = """\
> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。"""

# falsified 6 系統 + 価格モダリティ 3 周 (再試行禁止チェックリスト — 自動表示)
FALSIFIED_CHECKLIST = (
    ("H4 水平線 level", "3-way IC null (N=10k-15k)、再試行禁止", "project_h4_level_edge_falsified"),
    ("チャネル (回帰±2σ/平行)", "6-pair IC null 2026-06-25、再試行禁止", "project_channel_edge_falsified"),
    ("水平 sweep&reclaim", "負EV (6-pair) 2026-06-25、再試行禁止", "project_sweep_reclaim_horizontal_falsified"),
    ("mtf_regime_switch SELL 非対称", "sub-friction、摩擦込み REJECT", "project_mtf_regime_switch_falsified"),
    ("bb_rsi_reversion", "T10 KILL N=495 friction>edge、セル分割/フィルタ再生の再試行禁止", "project_bb_rsi_reversion_falsified"),
    ("T11 LDN朝×counter-USD MR", "敵対的検証で REJECT (擬似反復/閾値リーク)", "project_t11_ldn_counter_usd_mr_falsified"),
    ("価格モダリティ round-1", "WS3 stage-2 barrier/EV 化 FAIL", "ws3-stage2-barrier-ev-prereg-2026-07-09 §8"),
    ("価格モダリティ round-2", "OOS FAIL 0/5 (PR #79)", "ws3-round2-explore-prereg-2026-07-10 §8"),
    ("価格モダリティ round-3", "crossasset divergence FAIL → 外部仮説転進", "ws3-round3-crossasset-divergence-prereg-2026-07-13"),
)

_UTC = timezone.utc


# ═══════════════════════════════════════════════════════════════════════════
# スペック読込・検証
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class ProbeSpec:
    name: str
    description: str
    direction: dict
    trigger: dict
    pairs: list
    horizons: list          # M15 bar 数 (int) に正規化済み
    holding: dict
    window: dict            # {"start": str, "end": str}
    notes: str = ""
    raw: dict = field(default_factory=dict)
    spec_hash: str = ""


def load_spec_file(path: str) -> dict:
    """YAML/JSON スペックファイルを dict へ。YAML は pyyaml がある場合のみ (無ければ明示エラー)。"""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml  # optional dependency — 環境に無い場合は JSON を使う
        except ImportError as exc:
            raise RuntimeError(
                f"YAML spec ({path}) には pyyaml が必要。JSON スペックを使うか pyyaml を導入する"
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _req(d: dict, key: str, ctx: str):
    if key not in d:
        raise ValueError(f"spec {ctx}: 必須キー '{key}' がない")
    return d[key]


def normalize_spec(raw: dict) -> ProbeSpec:
    """小語彙の検証 + 正規化。未知語彙は即 ValueError (silent fallback 禁止)。"""
    name = str(_req(raw, "name", "top"))
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"spec name は [a-zA-Z0-9_]+ のみ: {name!r}")

    ds = dict(_req(raw, "direction_source", "top"))
    kind = _req(ds, "kind", "direction_source")
    if kind not in VOCAB_DIRECTION_KINDS:
        raise ValueError(f"direction_source.kind={kind!r} は小語彙 {VOCAB_DIRECTION_KINDS} 外")
    if kind == "event":
        ev = _req(ds, "event", "direction_source")
        if ev not in VOCAB_EVENTS:
            raise ValueError(f"direction_source.event={ev!r} は {VOCAB_EVENTS} 外")
        rule = _req(ds, "rule", "direction_source")
        if rule not in VOCAB_EVENT_RULES:
            raise ValueError(f"direction_source.rule={rule!r} は {VOCAB_EVENT_RULES} 外")
        ds.setdefault("w0_min", 30)
    elif kind == "series":
        _req(ds, "column", "direction_source")
        ds.setdefault("file", None)
        ds.setdefault("lag_days", 1)
        if int(ds["lag_days"]) < 1:
            raise ValueError("series.lag_days は >=1 (公表当日 bar への look-ahead を構造排除)")
    else:  # technical
        cond = _req(ds, "condition", "direction_source")
        if cond not in VOCAB_TECHNICAL:
            raise ValueError(f"direction_source.condition={cond!r} は {VOCAB_TECHNICAL} 外")
        if cond == "momentum_sign":
            ds.setdefault("lookback", 20)
        else:
            ds.setdefault("fast", 20)
            ds.setdefault("slow", 50)

    tr = dict(raw.get("entry_trigger", {"kind": "none"}))
    tkind = tr.get("kind", "none")
    if tkind not in VOCAB_TRIGGERS:
        raise ValueError(f"entry_trigger.kind={tkind!r} は小語彙 {VOCAB_TRIGGERS} 外")
    tr.setdefault("lookback", 20)      # breakout チャネル幅
    tr.setdefault("ema_period", 20)    # pullback EMA
    tr.setdefault("search_bars", 16)   # event kind: t_e+W0 から trigger を探す最大 bar 数

    pairs = list(_req(raw, "pairs", "top"))
    for p in pairs:
        if p not in L.FRICTION:
            raise ValueError(f"pair {p!r} は摩擦テーブル (E1 §3.4 凍結) に無い — 追加は R1 手続き")

    horizons = []
    for h in _req(raw, "horizons", "top"):
        if isinstance(h, str):
            if h not in NAMED_HORIZONS:
                raise ValueError(f"horizon {h!r} は {sorted(NAMED_HORIZONS)} 外 (int bar 数も可)")
            horizons.append(NAMED_HORIZONS[h])
        else:
            hb = int(h)
            if hb <= 0 or hb > 96 * 20:
                raise ValueError(f"horizon bars={hb} が範囲外 (1〜{96*20})")
            horizons.append(hb)

    hold = dict(raw.get("holding", {"mode": "bars"}))
    if hold.get("mode", "bars") not in VOCAB_HOLDING:
        raise ValueError(f"holding.mode={hold.get('mode')!r} は {VOCAB_HOLDING} 外")
    hold.setdefault("mode", "bars")
    hold.setdefault("tp_sigma", 1.0)
    hold.setdefault("sl_sigma", 1.0)

    win = dict(raw.get("window", {}))
    win.setdefault("start", EXPLORE_START_DEFAULT)
    win.setdefault("end", EXPLORE_END)

    canon = json.dumps(raw, sort_keys=True, ensure_ascii=False)
    return ProbeSpec(
        name=name,
        description=str(raw.get("description", "")),
        direction=ds, trigger=tr, pairs=pairs, horizons=sorted(set(horizons)),
        holding=hold, window=win, notes=str(raw.get("notes", "")), raw=raw,
        spec_hash=hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16],
    )


# ═══════════════════════════════════════════════════════════════════════════
# データ読込 + OOS 構造遮断
# ═══════════════════════════════════════════════════════════════════════════
def clamp_oos(m15: pd.DataFrame, spec: ProbeSpec, unlock_oos: bool) -> pd.DataFrame:
    """OOS 構造遮断: bars を窓 [start, min(end, OOS 境界)) に物理スライス。

    以降のどの計算段も遮断された bar には触れない (horizon が境界を跨ぐ trade は
    bar 不在により censored — 事後裁量なしの構造遮断)。unlock_oos=True のみ解除。
    """
    start = pd.Timestamp(spec.window["start"], tz="UTC")
    end_excl = pd.Timestamp(spec.window["end"], tz="UTC") + pd.Timedelta(days=1)
    if not unlock_oos:
        end_excl = min(end_excl, pd.Timestamp(OOS_BOUNDARY_UTC, tz="UTC"))
    out = m15.loc[(m15.index >= start) & (m15.index < end_excl)]
    return out


def load_bars_from_disk(spec: ProbeSpec, unlock_oos: bool) -> tuple:
    """parquet から (bars, coverage) を読込。coverage < gate のペアは理由付き除外。"""
    bars, coverage = {}, {}
    for pair in spec.pairs:
        f = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
        if not os.path.exists(f):
            coverage[pair] = {"status": "MISSING_PARQUET", "included": False}
            continue
        m15 = pd.read_parquet(f)
        if m15.index.tz is None:
            m15.index = m15.index.tz_localize("UTC")
        m15 = clamp_oos(m15, spec, unlock_oos)
        if m15.empty:
            coverage[pair] = {"status": "EMPTY_AFTER_CLAMP", "included": False}
            continue
        cov = L.market_time_coverage(
            m15, spec.window["start"],
            min(spec.window["end"], EXPLORE_END) if not unlock_oos else spec.window["end"])
        included = cov >= L.COVERAGE_GATE
        coverage[pair] = {"coverage": round(cov, 4), "included": bool(included)}
        if included:
            bars[pair] = m15
    return bars, coverage


def load_calendar(spec: ProbeSpec, unlock_oos: bool, calendar=None) -> list:
    """イベント t_e (UTC Timestamp) リスト。OOS 境界でクランプ (calendar 側も遮断)。"""
    if calendar is None:
        if not os.path.exists(CALENDAR_JSON):
            raise FileNotFoundError(
                f"event calendar not found: {CALENDAR_JSON} — "
                "tools/event_calendar_build.py で先に構築する")
        with open(CALENDAR_JSON, "r", encoding="utf-8") as fh:
            calendar = json.load(fh).get("events", {})
    ev_type = spec.direction["event"]
    ts = [pd.Timestamp(x) for x in calendar.get(ev_type, [])]
    ts = [t if t.tz is not None else t.tz_localize("UTC") for t in ts]
    start = pd.Timestamp(spec.window["start"], tz="UTC")
    end_excl = pd.Timestamp(spec.window["end"], tz="UTC") + pd.Timedelta(days=1)
    if not unlock_oos:
        end_excl = min(end_excl, pd.Timestamp(OOS_BOUNDARY_UTC, tz="UTC"))
    return sorted(t for t in ts if start <= t < end_excl)


# ═══════════════════════════════════════════════════════════════════════════
# 方向 series (causal) — signal 値は bar i の close 時点までの情報のみ
# ═══════════════════════════════════════════════════════════════════════════
def make_dummy_series(index: pd.DatetimeIndex) -> pd.Series:
    """決定的ダミー ±1 (日次、seed 固定)。E20 外部 series 接続までの構造検証専用。"""
    days = pd.DatetimeIndex(sorted(set(index.normalize())))
    rng = np.random.default_rng(SEED)
    vals = rng.choice(np.array([-1.0, 1.0]), size=len(days))
    daily = pd.Series(vals, index=days)
    return daily.reindex(index.normalize()).set_axis(index)


def series_scores(m15: pd.DataFrame, pair: str, ds: dict) -> pd.Series:
    """外部 series → bar 毎 score。lag_days で公表遅延を構造化 (look-ahead 排除)。"""
    col = ds["column"]
    lag = int(ds["lag_days"])
    if col.startswith("__dummy"):
        base = make_dummy_series(m15.index)
        # ダミーも lag を通す (実 series と同じ配管を検証するため)
        daily = base.groupby(base.index.normalize()).first()
        shifted = daily.shift(lag)
        return shifted.reindex(m15.index.normalize()).set_axis(m15.index)
    if not ds.get("file"):
        raise ValueError(f"series.column={col!r} はダミーでないのに file が無い "
                         "(実 series 接続は E20 feasibility 通過後)")
    ext = pd.read_csv(ds["file"], parse_dates=["date"])
    if pair in ext.columns:
        s = ext.set_index("date")[pair]
    elif col in ext.columns:
        s = ext.set_index("date")[col]
    else:
        raise ValueError(f"series file に列 {pair!r} も {col!r} も無い")
    s.index = pd.DatetimeIndex(s.index).tz_localize("UTC")
    daily = s.sort_index().shift(lag)  # 公表 lag: 値は lag 日後の bar から有効
    return daily.reindex(m15.index.normalize(), method="ffill").set_axis(m15.index)


def technical_scores(m15: pd.DataFrame, ds: dict) -> pd.Series:
    """テクニカル条件 → bar 毎 score (連続値、IC 用)。全て bar i close までの情報のみ。"""
    close = m15["Close"]
    if ds["condition"] == "momentum_sign":
        k = int(ds["lookback"])
        return close - close.shift(k)
    # ema_trend
    fast = close.ewm(span=int(ds["fast"]), adjust=False).mean()
    slow = close.ewm(span=int(ds["slow"]), adjust=False).mean()
    return fast - slow


# ═══════════════════════════════════════════════════════════════════════════
# entry trigger (causal) — bar i の close までで条件判定、entry は bar i+1 open
# ═══════════════════════════════════════════════════════════════════════════
def trigger_masks(m15: pd.DataFrame, trigger: dict) -> tuple:
    """(buy_ok, sell_ok) boolean 配列。bar i で True = bar i close 時点で条件成立。"""
    n = len(m15)
    kind = trigger["kind"]
    if kind == "none":
        ones = np.ones(n, dtype=bool)
        return ones, ones
    close = m15["Close"].values
    if kind == "breakout":
        lb = int(trigger["lookback"])
        hi_roll = pd.Series(m15["High"].values).rolling(lb).max().shift(1).values
        lo_roll = pd.Series(m15["Low"].values).rolling(lb).min().shift(1).values
        buy_ok = np.where(np.isfinite(hi_roll), close > hi_roll, False)
        sell_ok = np.where(np.isfinite(lo_roll), close < lo_roll, False)
        return buy_ok.astype(bool), sell_ok.astype(bool)
    # pullback: 方向トレンド中の EMA タッチ + 方向側 close
    ep = int(trigger["ema_period"])
    ema = pd.Series(close).ewm(span=ep, adjust=False).mean().values
    low = m15["Low"].values
    high = m15["High"].values
    warm = np.arange(n) >= ep
    buy_ok = (low <= ema) & (close > ema) & warm
    sell_ok = (high >= ema) & (close < ema) & warm
    return buy_ok.astype(bool), sell_ok.astype(bool)


# ═══════════════════════════════════════════════════════════════════════════
# トレードシミュレーション (event_modality_lib §3.5 と同一規約: SL 優先 / open exit)
# ═══════════════════════════════════════════════════════════════════════════
class AtrMemo:
    """L.atr14d_before の trade-day 単位 memoize (per-pair)。計算規約は L と同一。"""

    def __init__(self, daily: pd.DataFrame):
        self._daily = daily
        self._memo = {}

    def before(self, ts: pd.Timestamp) -> float:
        t_ny = pd.Timestamp(ts).tz_convert("America/New_York")
        key = (t_ny - pd.Timedelta(hours=17)).normalize().date()
        if key not in self._memo:
            self._memo[key] = L.atr14d_before(self._daily, ts)
        return self._memo[key]


@dataclass
class Trade:
    entry_pos: int
    entry_ts: pd.Timestamp
    direction: int
    score: float
    outcomes: dict  # horizon(bars) -> {"pips": friction 調整後, "raw_fwd": 方向なし fwd pips}


def simulate_outcome(m15: pd.DataFrame, atr_memo: AtrMemo, e: int, d: int,
                     h_bars: int, pair: str, holding: dict, skips: dict):
    """1 entry × 1 horizon の摩擦調整 pips。censored/ATR NaN は skip 理由をカウントして None。"""
    if e + h_bars >= len(m15):
        skips["censored_horizon"] = skips.get("censored_horizon", 0) + 1
        return None
    pip = L.pip_size(pair)
    friction = L.FRICTION[pair]
    o = m15["Open"].values
    entry = float(o[e])
    raw_fwd = (float(o[e + h_bars]) - entry) / pip  # 方向なし (IC 用)
    if holding["mode"] == "bars":
        return {"pips": d * raw_fwd - friction, "raw_fwd": raw_fwd}
    # first_touch (σ_h barrier、SL 優先 — L.event_trade §3.5 と同一規約)
    atr = atr_memo.before(m15.index[e])
    if not np.isfinite(atr) or atr <= 0:
        skips["atr_nan"] = skips.get("atr_nan", 0) + 1
        return None
    sigma = atr * math.sqrt((h_bars / L.BARS_PER_HOUR) / 24.0)
    tp = entry + d * sigma * float(holding["tp_sigma"])
    sl = entry - d * sigma * float(holding["sl_sigma"])
    hi = m15["High"].values
    lo = m15["Low"].values
    ft = None
    for j in range(e, e + h_bars):
        hit_sl = (lo[j] <= sl) if d > 0 else (hi[j] >= sl)
        hit_tp = (hi[j] >= tp) if d > 0 else (lo[j] <= tp)
        if hit_sl:  # 同一バー両ヒットは SL 優先 (ハウス保守規約)
            ft = -abs(entry - sl) / pip
            break
        if hit_tp:
            ft = abs(tp - entry) / pip
            break
    if ft is None:
        ft = d * raw_fwd  # timeout = open[e+h]
    return {"pips": ft - friction, "raw_fwd": raw_fwd}


def _entry_after_trigger(m15, buy_ok, sell_ok, d, start_pos, max_pos):
    """[start_pos, max_pos) で方向 d の trigger が立つ最初の bar j → entry = j+1。無ければ None。"""
    mask = buy_ok if d > 0 else sell_ok
    for j in range(start_pos, min(max_pos, len(m15) - 1)):
        if mask[j]:
            return j + 1
    return None


# ═══════════════════════════════════════════════════════════════════════════
# トレード生成 (kind 別)
# ═══════════════════════════════════════════════════════════════════════════
def gen_trades_event(spec: ProbeSpec, pair: str, m15: pd.DataFrame,
                     events: list, atr_memo: AtrMemo, skips: dict) -> list:
    trades = []
    rule = spec.direction["rule"]
    w0 = int(spec.direction["w0_min"])
    buy_ok, sell_ok = trigger_masks(m15, spec.trigger)
    max_h = max(spec.horizons)
    idx = m15.index
    for t_e in events:
        r0 = L.compute_r0(m15, t_e, w0) if rule in ("fade", "follow") else 0.0
        d = L.rule_direction(rule, pair, r0)
        if d == 0:
            skips["zero_direction"] = skips.get("zero_direction", 0) + 1
            continue
        anchor_ts = pd.Timestamp(t_e) + pd.Timedelta(minutes=w0)
        try:
            anchor = int(idx.get_loc(anchor_ts))
        except KeyError:
            skips["missing_anchor_bar"] = skips.get("missing_anchor_bar", 0) + 1
            continue
        if spec.trigger["kind"] == "none":
            e = anchor
        else:
            e = _entry_after_trigger(m15, buy_ok, sell_ok, d, anchor,
                                     anchor + int(spec.trigger["search_bars"]))
            if e is None:
                skips["no_trigger"] = skips.get("no_trigger", 0) + 1
                continue
        # score: fade = −R0 / follow = +R0 (連続、IC 用)。uncond は ±1 定数。
        if rule == "fade":
            score = -float(r0) / L.pip_size(pair) if r0 is not None else 0.0
        elif rule == "follow":
            score = float(r0) / L.pip_size(pair) if r0 is not None else 0.0
        else:
            score = float(d)
        outcomes = {}
        for h in spec.horizons:
            r = simulate_outcome(m15, atr_memo, e, d, h, pair, spec.holding, skips)
            if r is not None:
                outcomes[h] = r
        if outcomes:
            trades.append(Trade(e, idx[e], d, score, outcomes))
        _ = max_h  # 明示: event kind は event 単位で非重複 (bar step 不要)
    return trades


def gen_trades_scored(spec: ProbeSpec, pair: str, m15: pd.DataFrame,
                      atr_memo: AtrMemo, skips: dict) -> list:
    """series / technical: bar 毎 score → 方向 = sign(score)。非重複 (entry 後 max horizon skip)。"""
    ds = spec.direction
    if ds["kind"] == "series":
        scores = series_scores(m15, pair, ds).values
    else:
        scores = technical_scores(m15, ds).values
    buy_ok, sell_ok = trigger_masks(m15, spec.trigger)
    max_h = max(spec.horizons)
    n = len(m15)
    warmup = max(int(spec.trigger.get("lookback", 0)),
                 int(spec.trigger.get("ema_period", 0)),
                 int(ds.get("lookback", 0)), int(ds.get("slow", 0)), 1)
    trades = []
    i = warmup
    idx = m15.index
    while i < n - 1:
        sc = scores[i]
        if not np.isfinite(sc) or sc == 0:
            i += 1
            continue
        d = 1 if sc > 0 else -1
        if not (buy_ok[i] if d > 0 else sell_ok[i]):
            i += 1
            continue
        e = i + 1  # signal は bar i close で確定 → entry は次 bar open (causal)
        outcomes = {}
        for h in spec.horizons:
            r = simulate_outcome(m15, atr_memo, e, d, h, pair, spec.holding, skips)
            if r is not None:
                outcomes[h] = r
        if outcomes:
            trades.append(Trade(e, idx[e], d, float(sc), outcomes))
            i = e + max_h  # 非重複: 最長 horizon 完了まで再 entry しない
        else:
            i += 1
    return trades


# ═══════════════════════════════════════════════════════════════════════════
# 集計: IC / EV / fold 3 分割 / 発火頻度
# ═══════════════════════════════════════════════════════════════════════════
def _fold_edges(start: pd.Timestamp, end: pd.Timestamp) -> list:
    span = (end - start) / 3
    return [start + span, start + 2 * span]


def _fold_of(ts, edges) -> int:
    for k, e in enumerate(edges):
        if ts <= e:
            return k
    return 2


def summarize_cell(trades: list, h: int, edges: list, years: float) -> dict:
    """1 (pair × horizon) セルの標準診断。"""
    rows = [(t.entry_ts, t.score, t.outcomes[h]) for t in trades if h in t.outcomes]
    if not rows:
        return {"N": 0}
    pips = np.array([r[2]["pips"] for r in rows], dtype=float)
    raw = np.array([r[2]["raw_fwd"] for r in rows], dtype=float)
    scores = np.array([r[1] for r in rows], dtype=float)
    n = len(pips)
    ic = None
    ic_p = None
    if len(set(np.round(scores, 12))) >= 2 and n >= 8:
        rho, p = stats.spearmanr(scores, raw)
        if np.isfinite(rho):
            ic, ic_p = float(rho), float(p)
    fold_ev = {0: [], 1: [], 2: []}
    for ts, _, oc in rows:
        fold_ev[_fold_of(ts, edges)].append(oc["pips"])
    fold_signs = [int(np.sign(np.mean(v))) for v in fold_ev.values() if v]
    agree = max(sum(1 for s in fold_signs if s > 0),
                sum(1 for s in fold_signs if s < 0)) if fold_signs else 0
    return {
        "N": int(n),
        "ev_friction_pips": float(np.mean(pips)),
        "median_pips": float(np.median(pips)),
        "wr": float(np.mean(pips > 0)),
        "std_pips": float(np.std(pips, ddof=1)) if n > 1 else None,
        "ic": ic, "ic_p": ic_p,
        "fold_signs": fold_signs,
        "fold_agreement": int(agree),
        "fires_per_year": float(n / years) if years > 0 else None,
    }


def pooled_summary(all_trades: dict, h: int, edges: list, years: float) -> dict:
    """全ペア pooled + ペア別 EV>0 比率。"""
    pool = []
    pair_pos = 0
    pair_count = 0
    for pair, trades in all_trades.items():
        cell = [t.outcomes[h]["pips"] for t in trades if h in t.outcomes]
        if cell:
            pair_count += 1
            if np.mean(cell) > 0:
                pair_pos += 1
        pool.extend((t.entry_ts, t.outcomes[h]["pips"])
                    for t in trades if h in t.outcomes)
    if not pool:
        return {"N": 0}
    pips = np.array([p for _, p in pool], dtype=float)
    fold_ev = {0: [], 1: [], 2: []}
    for ts, p in pool:
        fold_ev[_fold_of(ts, edges)].append(p)
    fold_signs = [int(np.sign(np.mean(v))) for v in fold_ev.values() if v]
    agree = max(sum(1 for s in fold_signs if s > 0),
                sum(1 for s in fold_signs if s < 0)) if fold_signs else 0
    n = len(pips)
    guide = bool(
        np.mean(pips) > 0 and n >= GUIDE_MIN_N and agree >= GUIDE_MIN_FOLD_AGREE
        and pair_count > 0 and (pair_pos / pair_count) >= GUIDE_MIN_PAIR_POS_FRAC
        and all(s > 0 for s in fold_signs)
    )
    return {
        "N": n,
        "ev_friction_pips": float(np.mean(pips)),
        "wr": float(np.mean(pips > 0)),
        "fold_signs": fold_signs,
        "fold_agreement": int(agree),
        "pairs_positive": f"{pair_pos}/{pair_count}",
        "fires_per_year": float(n / years) if years > 0 else None,
        "s3_consider_hint": guide,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 実行本体
# ═══════════════════════════════════════════════════════════════════════════
def run_probe(spec: ProbeSpec, unlock_oos: bool = False,
              bars=None, calendar=None) -> dict:
    """spec → 診断 dict。bars/calendar 注入可 (テスト用オフライン fixture)。

    注入 bars にも clamp_oos を必ず適用する — OOS 遮断は入口非依存の構造。
    """
    if unlock_oos:
        print("⚠️⚠️ --unlock-oos: OOS 窓 (2024-01-01〜) への構造遮断を解除している。"
              "これは S4 判定器の役割であり S2 診断で使うことは規律違反。", file=sys.stderr)
    if bars is None:
        bars, coverage = load_bars_from_disk(spec, unlock_oos)
    else:
        bars = {p: clamp_oos(df, spec, unlock_oos) for p, df in bars.items()}
        bars = {p: df for p, df in bars.items() if not df.empty}
        coverage = {p: {"coverage": None, "included": True, "note": "injected"}
                    for p in bars}
    if not bars:
        raise RuntimeError("有効ペアが 0 — parquet 存在と coverage gate (0.90) を確認")

    events = None
    if spec.direction["kind"] == "event":
        events = load_calendar(spec, unlock_oos, calendar=calendar)
        if not events:
            raise RuntimeError(f"窓内にイベント 0 件 ({spec.direction['event']})")

    w_start = pd.Timestamp(spec.window["start"], tz="UTC")
    w_end = pd.Timestamp(spec.window["end"], tz="UTC")
    if not unlock_oos:
        w_end = min(w_end, pd.Timestamp(EXPLORE_END, tz="UTC"))
    edges = _fold_edges(w_start, w_end)
    years = max((w_end - w_start).days / 365.25, 1e-9)

    all_trades = {}
    skips = {}
    for pair, m15 in bars.items():
        pskips = {}
        atr_memo = AtrMemo(L.build_daily_from_m15(m15))
        if spec.direction["kind"] == "event":
            trades = gen_trades_event(spec, pair, m15, events, atr_memo, pskips)
        else:
            trades = gen_trades_scored(spec, pair, m15, atr_memo, pskips)
        all_trades[pair] = trades
        skips[pair] = pskips

    cells = {}
    for pair, trades in all_trades.items():
        for h in spec.horizons:
            cells[f"{pair}:h{h}"] = summarize_cell(trades, h, edges, years)
    pooled = {f"h{h}": pooled_summary(all_trades, h, edges, years)
              for h in spec.horizons}

    max_entry_ts = None
    entry_ts_all = [t.entry_ts for tr in all_trades.values() for t in tr]
    if entry_ts_all:
        max_entry_ts = max(entry_ts_all).isoformat()

    return {
        "tool": "rapid_edge_probe",
        "stage": "S2_R3_DIAGNOSTIC",
        "verdict_authority": "NONE — 探索診断。live/tier 判断禁止。次ステージ = S3 pre-reg 起案のみ",
        "generated_utc": datetime.now(_UTC).isoformat(),
        "seed": SEED,
        "spec_name": spec.name,
        "spec_hash": spec.spec_hash,
        "spec": spec.raw,
        "window_effective": {"start": str(w_start.date()), "end": str(w_end.date())},
        "oos_locked": not unlock_oos,
        "oos_boundary": OOS_BOUNDARY_UTC,
        "max_entry_ts": max_entry_ts,
        "coverage": coverage,
        "skips": skips,
        "n_events": len(events) if events is not None else None,
        "cells": cells,
        "pooled": pooled,
        "dummy_series": bool(spec.direction.get("column", "").startswith("__dummy")),
    }


# ═══════════════════════════════════════════════════════════════════════════
# レポート (md) + pre-reg draft
# ═══════════════════════════════════════════════════════════════════════════
def _fmt(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def render_md(result: dict, spec: ProbeSpec) -> str:
    lines = []
    lines.append(f"# rapid_edge_probe S2 診断 — {spec.name}")
    lines.append("")
    lines.append(DISCIPLINE_HEADER)
    if not result["oos_locked"]:
        lines.append("> **⚠️⚠️ OOS UNLOCK 状態で実行されている — S2 診断としては無効。**")
    lines.append("")
    lines.append(f"- 生成: {result['generated_utc']} / tool seed={result['seed']} / "
                 f"spec_hash=`{result['spec_hash']}`")
    lines.append(f"- 仮説: {spec.description or '(spec description なし)'}")
    if spec.notes:
        lines.append(f"- notes: {spec.notes}")
    lines.append(f"- 実効窓: {result['window_effective']['start']} 〜 "
                 f"{result['window_effective']['end']} "
                 f"(OOS 境界 {result['oos_boundary']} で構造遮断"
                 f"{'済み' if result['oos_locked'] else '解除⚠️'})")
    if result.get("dummy_series"):
        lines.append("- **⚠️ DUMMY series 実行**: direction_source はダミー列 (決定的 ±1、"
                     "エッジ期待ゼロ)。外部 series 接続は E20 feasibility (別 agent) の結果待ち。"
                     "本レポートは配管の構造検証のみに使うこと。")
    lines.append("")
    lines.append("## 再試行禁止チェックリスト (falsified 6 系統 + 価格モダリティ 3 周)")
    lines.append("")
    lines.append("本仮説が以下の再試行に該当しないことを S1 で確認済みであること (該当時は即中止):")
    lines.append("")
    lines.append("| 系統 | 結論 | 参照 |")
    lines.append("|---|---|---|")
    for name, verdict, ref in FALSIFIED_CHECKLIST:
        lines.append(f"| {name} | {verdict} | `{ref}` |")
    lines.append("")
    lines.append("(参考) month-end WMR fix も REJECT 済み (2026-06-18)。")
    lines.append("")
    lines.append("## Coverage / skip")
    lines.append("")
    lines.append("| pair | coverage | included |")
    lines.append("|---|---|---|")
    for pair, cov in result["coverage"].items():
        lines.append(f"| {pair} | {_fmt(cov.get('coverage'), 4)} | "
                     f"{cov.get('included')}{' (' + cov['status'] + ')' if 'status' in cov else ''} |")
    lines.append("")
    skips_flat = {p: s for p, s in result["skips"].items() if s}
    if skips_flat:
        lines.append(f"skip 理由 (silent except 禁止 — 全件カウント): `{json.dumps(skips_flat, ensure_ascii=False)}`")
        lines.append("")
    if result.get("n_events") is not None:
        lines.append(f"イベント件数 (窓内): {result['n_events']}")
        lines.append("")
    lines.append("## ペア × horizon 診断")
    lines.append("")
    lines.append("| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for key, c in result["cells"].items():
        if c["N"] == 0:
            lines.append(f"| {key} | 0 | — | — | — | — | — | — | — |")
            continue
        lines.append(
            f"| {key} | {c['N']} | {_fmt(c['ev_friction_pips'])} | {_fmt(c['median_pips'])} | "
            f"{_fmt(c['wr'])} | {_fmt(c['ic'], 3)} | {_fmt(c['ic_p'], 4)} | "
            f"{c['fold_signs']} | {_fmt(c['fires_per_year'], 1)} |")
    lines.append("")
    lines.append("## Pooled (全ペア) + 次ステージ判定の目安")
    lines.append("")
    lines.append("| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for hk, p in result["pooled"].items():
        if p["N"] == 0:
            lines.append(f"| {hk} | 0 | — | — | — | — | — | — |")
            continue
        hint = "🟡 S3 起案検討に値する (目安)" if p["s3_consider_hint"] else "⬜ 目安未達"
        lines.append(
            f"| {hk} | {p['N']} | {_fmt(p['ev_friction_pips'])} | {_fmt(p['wr'])} | "
            f"{p['fold_signs']} | {p['pairs_positive']} | {_fmt(p['fires_per_year'], 1)} | {hint} |")
    lines.append("")
    lines.append(f"**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥{GUIDE_MIN_N} ∧ "
                 f"fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥{GUIDE_MIN_PAIR_POS_FRAC:.0%}。"
                 "目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。")
    lines.append("")
    lines.append("---")
    lines.append("*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: "
                 "knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*")
    return "\n".join(lines) + "\n"


def render_prereg_draft(result: dict, spec: ProbeSpec) -> str:
    """S3 pre-reg スケルトン (型 B: discovery→凍結→OOS) を自動 draft。LOCK はしない。"""
    today = datetime.now(_UTC).date().isoformat()
    cand_rows = []
    for key, c in result["cells"].items():
        if c["N"] >= GUIDE_MIN_N and c.get("ev_friction_pips", 0) > 0 \
                and c.get("fold_agreement", 0) >= GUIDE_MIN_FOLD_AGREE:
            cand_rows.append(
                f"| {key} | {c['N']} | {c['ev_friction_pips']:.2f} | {c['fold_signs']} |")
    lines = [
        f"# pre-reg DRAFT — {spec.name} ({today})",
        "",
        "> **状態: 🔓 DRAFT — LOCKED ではない。** rapid_edge_probe --draft-prereg による自動スケルトン。",
        "> LOCK には: (1) 本文の TODO 全解消 (2) user 通知 (live 影響型は user 決裁) (3) registry 期日登録",
        "> (4) 判定器の実装 + test pin (LOCK 後・verdict 前) が必要 (pipeline §2 S3/S4)。",
        "",
        "## §1 仮説と経済機構",
        "",
        f"- 仮説: {spec.description or 'TODO'}",
        "- 経済機構 (なぜエッジが存在しうるか): **TODO — 必須。機構なき pre-reg は起案不可**",
        "- falsified 6 系統 + 価格 3 周との区別: **TODO — S1 裁定表へのリンク**",
        "",
        "## §2 候補凍結 (S2 診断からの機械抽出 — LOCK 時に確定)",
        "",
        f"- S2 診断: spec_hash=`{result['spec_hash']}` / 探索窓 "
        f"{result['window_effective']['start']}〜{result['window_effective']['end']} "
        "(OOS 未接触)",
        "- 凍結候補 (目安通過セル、LOCK 時に m₀ 確定・以後変更不可):",
        "",
        "| cell | N | EV_fric(pips) | fold符号 |",
        "|---|---|---|---|",
    ]
    lines.extend(cand_rows if cand_rows else ["| (目安通過セルなし — 起案前に仮説を見直す) | | | |"])
    lines.extend([
        "",
        "## §3 データ / 摩擦 / 執行 estimand",
        "",
        "- 価格: data/cache/massive 15m parquet (coverage gate 0.90、部分 parquet 罠に注意)",
        "- 摩擦: E1 §3.4 凍結テーブル (event_modality_lib.FRICTION) — 変更は R1",
        "- estimand: entry = signal 確定次 bar open / exit = "
        f"{spec.holding['mode']} (first_touch は TP=SL=σ_h、同一バー両ヒット SL 優先)",
        "",
        "## §4 OOS 窓と判定期日",
        "",
        f"- OOS 窓: **{OOS_BOUNDARY_UTC} 〜 cache 末尾** (探索窓と非重畳、first look のみ)",
        "- verdict 期日: **TODO (LOCK 日 + 実装数日、registry 登録必須)**",
        "- 中間 peeking 禁止 (§10-1 同型): OOS 窓のイベント×リターン結合統計は verdict まで一切計算しない",
        "",
        "## §5 判定規則 (テンプレ — LOCK 前に数値を固定)",
        "",
        "- 多重性: BH-FDR q=0.05 (family = 凍結候補 m₀ 全体) — **TODO: family 定義を明文化**",
        "- 有意性: block bootstrap (event/週 block) p 値 — **TODO: block 定義**",
        "- N gate: セル N≥ **TODO** ∧ event/期間 block ≥ **TODO** (UNDERPOWERED 分岐を必ず定義)",
        "- ナイフエッジ 3 点検査 (T11 教訓): 閾値近傍安定性 / 擬似反復 / リーク",
        "",
        "## §6 固定分岐 (観測前に固定)",
        "",
        "- PASS → S5 実装 pre-reg (D4 必須 4 項目、user 承認 D3 SLA 48h)",
        "- UNDERPOWERED → **TODO: 蓄積継続 or クローズ条件**",
        "- REJECT → 系統クローズ + falsified 台帳へ追記 (再試行禁止)",
        "",
        "## §7 LOCK チェックリスト",
        "",
        "- [ ] TODO 全解消 / - [ ] user 通知 (self-LOCK は純研究のみ) / "
        "- [ ] registry 期日 / - [ ] 判定器 test pin",
        "",
        "---",
        "*rapid_edge_probe.py --draft-prereg による自動生成スケルトン (draft であり pre-reg 効力なし)*",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, spec: ProbeSpec, outdir: str,
                  draft_prereg: bool, prereg_dir=None) -> dict:
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now(_UTC).strftime("%Y_%m_%d")
    base = os.path.join(outdir, f"rapid_probe_{spec.name}_{stamp}")
    paths = {"json": base + ".json", "md": base + ".md"}
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
    with open(paths["md"], "w", encoding="utf-8") as fh:
        fh.write(render_md(result, spec))
    if draft_prereg:
        pdir = prereg_dir if prereg_dir else PREREG_OUTDIR
        os.makedirs(pdir, exist_ok=True)
        day = datetime.now(_UTC).strftime("%Y-%m-%d")
        paths["prereg_draft"] = os.path.join(
            pdir, f"prereg-draft-{spec.name.replace('_', '-')}-{day}.md")
        with open(paths["prereg_draft"], "w", encoding="utf-8") as fh:
            fh.write(render_prereg_draft(result, spec))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# self-test (合成データ、オフライン)
# ═══════════════════════════════════════════════════════════════════════════
def make_synth_bars(pairs, start="2020-01-06", periods=96 * 500, seed=SEED) -> dict:
    """決定的な合成 M15 bars (self-test / テスト fixture 用)。"""
    idx = pd.date_range(start, periods=periods, freq="15min", tz="UTC")
    rng = np.random.default_rng(seed)
    out = {}
    for k, pair in enumerate(pairs):
        scale = 0.01 if pair.endswith("JPY") else 0.0001
        base = (100.0 if pair.endswith("JPY") else 1.0) + np.cumsum(
            rng.normal(0, 3 * scale, periods))
        out[pair] = pd.DataFrame({
            "Open": base,
            "High": base + 10 * scale,
            "Low": base - 10 * scale,
            "Close": base + rng.normal(0, 2 * scale, periods),
        }, index=idx)
        _ = k
    return out


def self_test() -> int:
    """合成 bars + 合成カレンダーで 3 kind × trigger を end-to-end 結線検証 (data 不要)。"""
    pairs = ["USD_JPY", "EUR_USD"]
    bars = make_synth_bars(pairs)
    cal = {"NFP": [L.et_to_utc(d.date(), 8, 30).isoformat()
                   for d in pd.date_range("2020-02-07", "2023-11-03", freq="4W")]}
    specs = [
        {"name": "st_event", "direction_source": {"kind": "event", "event": "NFP",
                                                  "rule": "uncond_usd_long"},
         "entry_trigger": {"kind": "none"}, "pairs": pairs, "horizons": ["h4", "h24"],
         "holding": {"mode": "bars"}, "window": {"start": "2020-01-01", "end": "2023-12-31"}},
        {"name": "st_series", "direction_source": {"kind": "series", "column": "__dummy_e20__"},
         "entry_trigger": {"kind": "breakout", "lookback": 20}, "pairs": pairs,
         "horizons": [16], "holding": {"mode": "first_touch"},
         "window": {"start": "2020-01-01", "end": "2023-12-31"}},
        {"name": "st_tech", "direction_source": {"kind": "technical",
                                                 "condition": "momentum_sign", "lookback": 20},
         "entry_trigger": {"kind": "pullback", "ema_period": 20}, "pairs": pairs,
         "horizons": [16, 96], "holding": {"mode": "bars"},
         "window": {"start": "2020-01-01", "end": "2023-12-31"}},
    ]
    for raw in specs:
        spec = normalize_spec(raw)
        res = run_probe(spec, bars=bars, calendar=cal)
        assert res["oos_locked"] is True
        if res["max_entry_ts"] is not None:
            assert pd.Timestamp(res["max_entry_ts"]) < pd.Timestamp(OOS_BOUNDARY_UTC, tz="UTC")
        for c in res["cells"].values():
            if c["N"]:
                assert np.isfinite(c["ev_friction_pips"])
        md = render_md(res, spec)
        assert "判定ではない" in md and "再試行禁止" in md
        print(f"self-test {spec.name}: OK "
              f"(pooled N={[p['N'] for p in res['pooled'].values()]})")
    print("self-test: all OK (synthetic — no edge expected)")
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    runp = sub.add_parser("run", help="spec を実行して診断レポートを出力")
    runp.add_argument("--spec", required=True, help="YAML/JSON 仮説スペック 1 ファイル")
    runp.add_argument("--outdir", default=DEFAULT_OUTDIR)
    runp.add_argument("--draft-prereg", action="store_true",
                      help="S3 pre-reg スケルトンを自動 draft (LOCK はしない)")
    runp.add_argument("--unlock-oos", action="store_true",
                      help="⚠️ OOS 構造遮断の解除 (S4 判定器専用 — S2 で使うのは規律違反)")
    sub.add_parser("self-test", help="合成データ dry-run (data 不要)")
    args = parser.parse_args(argv)

    if args.mode == "self-test":
        return self_test()
    if args.mode != "run":
        parser.print_help()
        return 1

    spec = normalize_spec(load_spec_file(args.spec))
    result = run_probe(spec, unlock_oos=args.unlock_oos)
    paths = write_outputs(result, spec, args.outdir, args.draft_prereg)
    print(f"S2 診断完了 (探索窓のみ — これは診断であり判定ではない): {spec.name}")
    for k, v in paths.items():
        print(f"  {k}: {os.path.relpath(v, _REPO)}")
    for hk, p in result["pooled"].items():
        if p["N"]:
            print(f"  pooled {hk}: N={p['N']} EV_fric={p['ev_friction_pips']:.2f}p "
                  f"fold={p['fold_signs']} hint={'S3-CONSIDER' if p['s3_consider_hint'] else 'not-yet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
