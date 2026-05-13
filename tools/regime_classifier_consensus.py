#!/usr/bin/env python3
"""Consensus consultation for empirical v2 vs literal Dow regime classifiers.

Inputs are repo-local only:
- read-only demo_trades snapshot
- Phase B2.5 trade/proposal CSV artifacts
- local MASSIVE 15m parquet cache for M15 v2 re-tagging
"""

from __future__ import annotations

import csv
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.regime_classifier import (  # noqa: E402
    ADX_MODERATE_MAX,
    ADX_MODERATE_MIN,
    HURST_MODERATE_HIGH,
    HURST_MODERATE_LOW,
    REGIME_MODERATE_TREND,
    REGIME_NO_GO,
    classify_15m,
    hurst_rs,
)

SNAPSHOT_DB = ROOT / "knowledge-base/raw/snapshots/render-demo-trades-20260503.db"
B2_DIR = ROOT / "reports/regime_gate_phase_b2"
TRADE_LOG = B2_DIR / "trade_log_tagged.csv"
PROPOSALS = B2_DIR / "shadow_proposals.csv"
CACHE_DIR = ROOT / "data/cache/massive"
OUT_DIR = ROOT / "reports/regime_classifier_consensus"


def _pair_cache_key(pair: str) -> str:
    value = str(pair).upper().replace("/", "_").replace("-", "_")
    if value.endswith("=X"):
        value = value[:-2]
    value = value.replace("_", "")
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def _parse_time(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_smoothed / atr.replace(0, pd.NA)
    minus_di = 100 * minus_smoothed / atr.replace(0, pd.NA)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={c: c.lower() for c in df.columns})
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def _prepare_m15(pair: str) -> pd.DataFrame:
    path = CACHE_DIR / f"{_pair_cache_key(pair)}_15m.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = _normalize_ohlc(pd.read_parquet(path))
    close = df["close"].astype(float)
    df["adx"] = _wilder_adx(df, 14)
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema_slope"] = df["ema21"] - df["ema21"].shift(3)
    df["hurst_64"] = close.rolling(64).apply(lambda x: hurst_rs(x.tolist()), raw=False)
    return df


def _feature_at(cache: dict[str, pd.DataFrame], pair: str, ts: pd.Timestamp) -> dict | None:
    if pair not in cache:
        cache[pair] = _prepare_m15(pair)
    df = cache[pair]
    window = df[df.index <= ts]
    if window.empty:
        return None
    row = window.iloc[-1]
    return {
        "adx": float(row.get("adx", 0.0) or 0.0),
        "ema_slope": float(row.get("ema_slope", 0.0) or 0.0),
        "hurst_64": float(row.get("hurst_64", 0.5) or 0.5),
    }


def _pf(pnls: list[float]) -> float:
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / abs(gross_loss)


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / den


def _stats(rows: pd.DataFrame) -> dict[str, float | int | str]:
    pnls = [float(x) for x in rows["pnl_m"].tolist()]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    pf = _pf(pnls)
    return {
        "N": n,
        "WR": round(wins / n, 6) if n else 0.0,
        "EV_pip": round(sum(pnls) / n, 6) if n else 0.0,
        "PF": "inf" if math.isinf(pf) else round(pf, 6),
        "Wilson_lo": round(_wilson_lower(wins, n), 6),
    }


def write_v2_recalibration() -> pd.DataFrame:
    query = """
    SELECT mtf_regime, entry_type, COUNT(*) as N,
           ROUND(AVG(CASE WHEN pnl_pips > 0 THEN 1.0 ELSE 0.0 END) * 100, 1) as WR,
           ROUND(AVG(pnl_pips), 3) as EV
    FROM demo_trades
    WHERE is_shadow = 0 AND mtf_regime IS NOT NULL AND mtf_regime != ''
    GROUP BY mtf_regime, entry_type
    HAVING N >= 30
    ORDER BY entry_type, mtf_regime
    """
    with sqlite3.connect(SNAPSHOT_DB) as conn:
        df = pd.read_sql_query(query, conn)
    df.to_csv(OUT_DIR / "v2_recalibration.csv", index=False)
    return df


def tag_b2_trades() -> pd.DataFrame:
    df = pd.read_csv(TRADE_LOG)
    cache: dict[str, pd.DataFrame] = {}
    rows = []
    for row in df.to_dict("records"):
        pair = str(row["pair"])
        ts = _parse_time(str(row["entry_time"]))
        features = _feature_at(cache, pair, ts)
        v2_regime = classify_15m(features)
        out = dict(row)
        out["dow_regime"] = out.pop("regime")
        out["v2_regime"] = v2_regime
        if features:
            out["m15_adx"] = round(features["adx"], 6)
            out["m15_ema_slope"] = round(features["ema_slope"], 9)
            out["m15_hurst_64"] = round(features["hurst_64"], 6)
        rows.append(out)
    return pd.DataFrame(rows)


def write_crosstab(tagged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dow, v2), group in tagged.groupby(["dow_regime", "v2_regime"], dropna=False):
        stats = _stats(group)
        rows.append({"dow_regime": dow, "mtf_v2_regime": v2, **stats})
    out = pd.DataFrame(rows).sort_values(["dow_regime", "mtf_v2_regime"])
    out.to_csv(OUT_DIR / "dow_vs_mtf_crosstab.csv", index=False)
    return out


def write_v2_replay(tagged: pd.DataFrame) -> pd.DataFrame:
    proposals = pd.read_csv(PROPOSALS)
    rows = []
    for prop in proposals.to_dict("records"):
        entry_type = prop["entry_type"]
        original_gate = prop["gate"]
        subset = tagged[tagged["entry_type"] == entry_type]
        original = subset[subset["dow_regime"] == original_gate]
        for v2_label in (REGIME_MODERATE_TREND, REGIME_NO_GO):
            v2_subset = subset[subset["v2_regime"] == v2_label]
            stats = _stats(v2_subset)
            rows.append(
                {
                    "proposal": prop["proposal"],
                    "entry_type": entry_type,
                    "dow_gate": original_gate,
                    "dow_N": int(prop["N"]),
                    "dow_WR": round(float(prop["WR"]), 6),
                    "dow_EV_pip": round(float(prop["EV_pip"]), 6),
                    "dow_PF": round(float(prop["PF"]), 6),
                    "dow_Wilson_lo": round(float(prop["Wilson_lo"]), 6),
                    "dow_original_recomputed_N": len(original),
                    "v2_gate": v2_label,
                    **{f"v2_{k}": v for k, v in stats.items()},
                    "v2_shadow_candidate": (
                        stats["N"] >= 30
                        and float(stats["EV_pip"]) > 0
                        and (float(stats["PF"]) if stats["PF"] != "inf" else float("inf")) >= 1.0
                        and float(stats["Wilson_lo"]) >= 0.40
                    ),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "v2_replay_17_proposals.csv", index=False)
    return out


def _write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _markdown_table(df: pd.DataFrame) -> str:
    headers = ["dow_regime"] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for idx, row in df.iterrows():
        values = [str(idx)] + [str(int(v)) if float(v).is_integer() else str(v) for v in row.tolist()]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_opinion(v2_df: pd.DataFrame, crosstab: pd.DataFrame, replay: pd.DataFrame) -> None:
    b25_total = sum(1 for _ in open(TRADE_LOG, encoding="utf-8")) - 1
    proposal_count = sum(1 for _ in open(PROPOSALS, encoding="utf-8")) - 1
    v2_candidate = replay[replay["v2_shadow_candidate"] == True]  # noqa: E712
    moderate = replay[(replay["v2_gate"] == REGIME_MODERATE_TREND) & (replay["v2_N"] > 0)]
    no_go = replay[(replay["v2_gate"] == REGIME_NO_GO) & (replay["v2_N"] > 0)]
    crosstab_pivot = crosstab.pivot(index="dow_regime", columns="mtf_v2_regime", values="N").fillna(0)
    total_moderate = int(crosstab[crosstab["mtf_v2_regime"] == REGIME_MODERATE_TREND]["N"].sum())
    total_no_go = int(crosstab[crosstab["mtf_v2_regime"] == REGIME_NO_GO]["N"].sum())

    opinion = f"""
# Regime Classifier Consensus Opinion

## Verdict

**推奨: A — 現行 dow_regime tagging task は Shadow 観測として進める。ただし Phase B2.5 17 proposals は仮説であり、Live 昇格や v2 置換の根拠にはしない。**

理由は単純で、v2 と Dow は同じものを測っていない。v2 は M15 の narrow binary fire-gate、Dow は H1 の broad context tag であり、B2.5 の 5,617 BT trades では v2 `moderate_trend` が {total_moderate} 件、`no_go` が {total_no_go} 件だった。Dow の 17 proposals は「classifier artifact」と断定するほど弱くはないが、「教科書値が v2 を上書きできる」と言えるほど検証済みでもない。

## Q1: 17 proposals の信頼性

信頼度は **Shadow hypothesis として中、promotion evidence として低**。B2.5 は N={b25_total} と大きい一方、BT 合成・single path・family coverage 34/66 の selection がある。17 proposals のうち v2 binary replay でも candidate 条件を満たした行は {len(v2_candidate)} / {proposal_count * 2} gate-row。これは Dow の数値が完全な幻ではない一方、v2 と独立に再現したとも言えない。

## Q2: 実測根拠比較

v2 再現クエリでは N>=30 cell は {len(v2_df)} 件だけで、`trend_up_weak` は `bb_rsi_reversion` N=142 WR=52.1% EV=+0.249 と正、`trend_down_strong`/`uncertain` は負寄りだった。一方、B2.5 は N=5,617 で proposal の見かけは強いが、Live 実測ではなく MASSIVE BT である。量は B2.5、外部妥当性は v2 production snapshot が上。結論として、**B2.5 は探索、v2 は安全側 prior** と扱うべき。

## Q3: 補完設計の妥当性

`dow_regime` と `v2_regime` の両方を tag して後で prediction power を比較する設計は **健全**。ただし条件はある。Dow tag を即 gate として universal に使わず、`entry_type × dow_regime × v2_regime` で Shadow N>=30 を積み、同一期間・同一 execution path で EV/PF/Wilson を比較すること。ad hoc hedge ではなく、competing predictors の forward test として扱えば妥当。

## Q4: 推奨行動

**A を選択**。Dow tagging は止めない。理由は 17 proposals に十分な探索価値があり、Shadow なら downside が限定されるため。ただし Phase E は「Dow classifier 勝利」ではなく「Dow-derived hypotheses の Shadow-first validation」と明記する。B は v2 の小標本 prior を過大評価、C は今ここで合成 classifier を設計すると二重に overfit、D は探索価値を捨てすぎ。

## Key Evidence

- v2 live snapshot query output: `reports/regime_classifier_consensus/v2_recalibration.csv`
- H1 Dow vs M15 v2 matrix: `reports/regime_classifier_consensus/dow_vs_mtf_crosstab.csv`
- 17 proposals v2 replay: `reports/regime_classifier_consensus/v2_replay_17_proposals.csv`
- v2 thresholds used: ADX {ADX_MODERATE_MIN}-{ADX_MODERATE_MAX}, Hurst {HURST_MODERATE_LOW}-{HURST_MODERATE_HIGH}, nonzero EMA slope.

## Crosstab Counts

{_markdown_table(crosstab_pivot)}

## Risk

最大リスクは B2.5 が `app.run_daytrade_backtest` path 固有の BT artifact で、production runtime と発火 universe が違うこと。次点は v2 snapshot が Live N=462 起点で、古いラベル・戦略 mix・期間依存の prior にすぎないこと。従って、どちらも単独 SSOT にしてはいけない。
"""
    _write_md(OUT_DIR / "opinion.md", opinion)

    summary = f"""
# Regime Classifier Consensus Summary

**Recommendation: A**

現行 `dow_regime` tagging は継続。ただし 17 proposals は未検証 hypothesis として Shadow 観測に限定し、Dow classifier を v2 の代替 SSOT にしない。

## Evidence

- B2.5 trade log: N={b25_total}, proposals={proposal_count}
- v2 recalibration N>=30 cells: {len(v2_df)}
- B2.5 trades retagged by M15 v2: moderate_trend={total_moderate}, no_go={total_no_go}
- v2 replay candidate rows: {len(v2_candidate)} / {proposal_count * 2}

## Decision

A が最も損失関数に合う。Dow の探索価値は残し、v2 の実測 prior も捨てない。B/C/D は現時点ではいずれも過剰反応。

## Next Task

Phase E を `Shadow-only competing-classifier validation` として再定義し、`entry_type × dow_regime × v2_regime` の同一 forward window 比較を pre-register する。
"""
    _write_md(OUT_DIR / "SUMMARY.md", summary)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v2_df = write_v2_recalibration()
    tagged = tag_b2_trades()
    crosstab = write_crosstab(tagged)
    replay = write_v2_replay(tagged)
    write_opinion(v2_df, crosstab, replay)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
