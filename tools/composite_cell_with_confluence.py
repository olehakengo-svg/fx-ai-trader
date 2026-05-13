#!/usr/bin/env python3
"""Gap 1 retrospective confluence analysis on Phase B2.5 trade log."""

from __future__ import annotations

import math
import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cross_pair_confluence import compute_confluence  # noqa: E402
from tools.composite_cell_retrospective_analysis import tag_trades as tag_dow_v2_trades  # noqa: E402

B2_DIR = ROOT / "reports" / "regime_gate_phase_b2"
TRADE_LOG = B2_DIR / "trade_log_tagged.csv"
OUT_DIR = ROOT / "reports" / "gap1_cross_pair_confluence"
MIN_CELL_N = 30
ALPHA = 0.05


def _parse_time(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _pf(pnls: Iterable[float]) -> float:
    values = [float(v) for v in pnls]
    gross_win = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / den


def _stats(rows: pd.DataFrame) -> dict:
    pnls = [float(v) for v in rows["pnl_m"].tolist()]
    n = len(pnls)
    wins = sum(1 for v in pnls if v > 0)
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 6) if n else 0.0,
        "EV_pip": round(sum(pnls) / n, 6) if n else 0.0,
        "PF": "inf" if math.isinf(pf) else round(pf, 6),
        "Wilson_lo": round(_wilson_lower(wins, n), 6),
    }


def _cell_stats(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for key, group in df.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        record = dict(zip(group_cols, key))
        record.update(_stats(group))
        rows.append(record)
    return pd.DataFrame(rows)


def tag_trades() -> pd.DataFrame:
    df = tag_dow_v2_trades()
    cache: dict[str, pd.DataFrame] = {}
    rows: list[dict] = []
    for row in df.to_dict("records"):
        result = compute_confluence(
            primary_pair=str(row["pair"]),
            primary_dir=str(row["sig"]),
            entry_time=_parse_time(str(row["entry_time"])),
            cache=cache,
        )
        out = dict(row)
        out["confluence_score"] = result.score
        out["confluence_confirmations"] = result.confirmations
        out["confluence_required"] = result.required
        out["confluence_details"] = result.details_json()
        rows.append(out)
    return pd.DataFrame(rows)


def write_bonferroni(by_strategy: pd.DataFrame, group_cols: list[str], filename: str) -> pd.DataFrame:
    eligible = by_strategy[by_strategy["N"] >= MIN_CELL_N].copy()
    m_eff = len(eligible)
    alpha_prime = ALPHA / m_eff if m_eff else 0.0
    rows: list[dict] = []
    for row in eligible.to_dict("records"):
        p_value = binomtest(int(row["wins"]), int(row["N"]), p=0.5, alternative="greater").pvalue
        record = {col: row[col] for col in group_cols}
        record.update(
            {
                "N": int(row["N"]),
                "wins": int(row["wins"]),
                "WR": row["WR"],
                "EV_pip": row["EV_pip"],
                "PF": row["PF"],
                "Wilson_lo": row["Wilson_lo"],
                "m_eff": m_eff,
                "alpha_prime": alpha_prime,
                "p_value": p_value,
                "bonferroni_pass": bool(p_value <= alpha_prime and float(row["EV_pip"]) > 0),
            }
        )
        rows.append(record)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["bonferroni_pass", "p_value"], ascending=[False, True])
    out.to_csv(OUT_DIR / filename, index=False)
    return out


def _markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    show = df.head(max_rows).copy()
    if show.empty:
        return "_No rows._"
    headers = [str(c) for c in show.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for record in show.to_dict("records"):
        values = []
        for header in headers:
            value = record[header]
            if isinstance(value, float):
                values.append(f"{value:.6g}" if math.isfinite(value) else str(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _component_coverage(tagged: pd.DataFrame) -> pd.DataFrame:
    rows: dict[str, dict] = {}
    for raw in tagged.get("confluence_details", pd.Series(dtype=str)).fillna("").tolist():
        try:
            details = json.loads(raw)
        except Exception:
            continue
        for component in details.get("components", []) or []:
            name = str(component.get("component", "UNKNOWN"))
            record = rows.setdefault(
                name,
                {"component": name, "N": 0, "confirmed": 0, "missing_or_error": 0, "flat": 0},
            )
            record["N"] += 1
            if component.get("confirms") is True:
                record["confirmed"] += 1
            if component.get("observed") == "flat":
                record["flat"] += 1
            if component.get("observed") == "NULL" or component.get("error"):
                record["missing_or_error"] += 1
    out = pd.DataFrame(rows.values())
    if out.empty:
        return out
    out["confirm_rate"] = (out["confirmed"] / out["N"]).round(6)
    out["missing_error_rate"] = (out["missing_or_error"] / out["N"]).round(6)
    return out.sort_values(["missing_or_error", "component"], ascending=[False, True])


def write_outputs(tagged: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tagged.to_csv(OUT_DIR / "trade_log_with_confluence.csv", index=False)

    global_df = _cell_stats(tagged, ["confluence_score"]).sort_values("confluence_score")
    global_df.to_csv(OUT_DIR / "crosstab_global.csv", index=False)

    by_strategy = _cell_stats(tagged, ["entry_type", "confluence_score"]).sort_values(
        ["entry_type", "confluence_score"]
    )
    by_strategy.to_csv(OUT_DIR / "crosstab_by_strategy.csv", index=False)

    four_axis = _cell_stats(
        tagged, ["entry_type", "dow_regime", "v2_regime", "confluence_score"]
    ).sort_values(
        ["entry_type", "dow_regime", "v2_regime", "confluence_score"]
    )
    four_axis.to_csv(OUT_DIR / "composite_4axis_strategy_dow_v2_confluence.csv", index=False)

    bonf_confluence = write_bonferroni(
        by_strategy, ["entry_type", "confluence_score"], "bonferroni_by_strategy_confluence.csv"
    )
    bonf_composite = write_bonferroni(
        four_axis,
        ["entry_type", "dow_regime", "v2_regime", "confluence_score"],
        "bonferroni_by_strategy_dow_v2_confluence.csv",
    )

    pass_confluence = bonf_confluence[bonf_confluence["bonferroni_pass"] == True] if not bonf_confluence.empty else bonf_confluence  # noqa: E712
    pass_composite = bonf_composite[bonf_composite["bonferroni_pass"] == True] if not bonf_composite.empty else bonf_composite  # noqa: E712
    proposals = pass_composite.copy() if not pass_composite.empty else pass_confluence.copy()
    if not proposals.empty:
        proposals["proposal_action"] = "forward_shadow_only_no_live_promotion"
        proposals["proposal_scope"] = "cell_specific_no_universal_gate"
    proposals.to_csv(OUT_DIR / "proposals.csv", index=False)

    coverage = _component_coverage(tagged)
    coverage.to_csv(OUT_DIR / "component_coverage.csv", index=False)

    mixed = global_df[global_df["confluence_score"] == "MIXED"]
    strong = global_df[global_df["confluence_score"] == "STRONG"]
    weak = global_df[global_df["confluence_score"] == "WEAK"]

    if not pass_confluence.empty or not pass_composite.empty:
        verdict = "CONDITIONAL_EDA_CANDIDATE"
        next_action = "forward Shadow accumulation only; do not convert confluence into a universal gate."
    else:
        verdict = "REJECT_FOR_PROMOTION_HOLD_FOR_OBSERVATION"
        next_action = "keep confluence as observation tag and require forward Shadow N before any gate proposal."

    summary = f"""# Gap 1 Cross-Pair Confluence Summary

VERDICT: {verdict}

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: {len(tagged)}
- Cache: local MASSIVE 1h parquet; DXY uses proxy when no `DXY_1h.parquet` exists.
- Live impact: none. This is retrospective EDA and observation-layer tagging only.

## Global Crosstab

{_markdown_table(global_df, 10)}

## Bonferroni

- strategy x confluence eligible cells: {int(bonf_confluence["m_eff"].iloc[0]) if not bonf_confluence.empty else 0}
- passing strategy x confluence cells: {len(pass_confluence)}
- strategy x dow x v2 x confluence eligible cells: {int(bonf_composite["m_eff"].iloc[0]) if not bonf_composite.empty else 0}
- passing strategy x dow x v2 x confluence cells: {len(pass_composite)}

Top adjusted rows:

{_markdown_table(bonf_composite if not bonf_composite.empty else bonf_confluence, 12)}

## Component Coverage

{_markdown_table(coverage, 12)}

Missing/error components are not imputed and do not confirm confluence. The mapping remains literal; no post-hoc replacement is applied.

## Confluence Distribution

- STRONG N: {int(strong.iloc[0]["N"]) if not strong.empty else 0}
- WEAK N: {int(weak.iloc[0]["N"]) if not weak.empty else 0}
- MIXED N: {int(mixed.iloc[0]["N"]) if not mixed.empty else 0}

## Next Action

{next_action}
"""
    verdict_md = f"""# Gap 1 Cross-Pair Confluence Verdict

VERDICT: {verdict}

This run does not authorize Live promotion or a universal confluence gate. It only adds the observation tag and checks whether the frozen Phase B2.5 trade log shows enough retrospective structure to justify forward collection.

## Artifacts

- `trade_log_with_confluence.csv`
- `crosstab_global.csv`
- `crosstab_by_strategy.csv`
- `composite_4axis_strategy_dow_v2_confluence.csv`
- `bonferroni_by_strategy_confluence.csv`
- `bonferroni_by_strategy_dow_v2_confluence.csv`
- `proposals.csv`
- `component_coverage.csv`

## Result

{_markdown_table(global_df, 10)}

## Risk

Pairs with only two literal requirements cannot produce STRONG by the pre-registered 3-confirmation threshold. That is preserved rather than post-hoc tuned.
"""
    (OUT_DIR / "SUMMARY.md").write_text(summary.strip() + "\n", encoding="utf-8")
    (OUT_DIR / "verdict.md").write_text(verdict_md.strip() + "\n", encoding="utf-8")


def main() -> None:
    tagged = tag_trades()
    write_outputs(tagged)
    print(f"wrote confluence analysis artifacts to {OUT_DIR}")


if __name__ == "__main__":
    main()
