#!/usr/bin/env python3
"""Deduplicate price shock survivor cells into pair/TF/direction families."""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


DB_PATH = ROOT / "data" / "price_shock_grid_cells.db"
REPORT_DIR = ROOT / "reports" / "price_shock_reversion_grid"
CSV_PATH = REPORT_DIR / "dedup_families.csv"
SHORTLIST_PATH = REPORT_DIR / "shadow_promote_shortlist.md"
AUDIT_PATH = REPORT_DIR / "dedup_audit.md"
EXPECTED_SHADOW_CELLS = 227
EXPECTED_FAMILIES = 23

CSV_COLUMNS = [
    "family_key",
    "pair",
    "tf",
    "direction",
    "rep_cell_id",
    "rep_percentile",
    "rep_horizon",
    "rep_vol_q",
    "n_trades",
    "win_rate",
    "wilson_lower_95",
    "profit_factor",
    "ev_pct",
    "ev_pip",
    "bonferroni_pass",
    "bh_fdr_pass",
    "family_cell_count",
    "bonf_pass_count",
    "bh_pass_count",
    "wilson_lo_mean",
    "wilson_lo_max",
    "ev_pct_mean",
    "n_trades_max",
    "n_trades_min",
    "horizon_coverage",
    "percentile_coverage",
    "vol_q_coverage",
    "tier",
    "tier_reason",
]


@dataclass(frozen=True)
class FamilyRow:
    family_key: str
    pair: str
    tf: str
    direction: str
    rep: sqlite3.Row
    family_cell_count: int
    bonf_pass_count: int
    bh_pass_count: int
    wilson_lo_mean: float
    wilson_lo_max: float
    ev_pct_mean: float
    n_trades_max: int
    n_trades_min: int
    horizon_coverage: int
    percentile_coverage: int
    vol_q_coverage: int
    raw_tier: str
    tier: str
    tier_reason: str


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_shadow_cells(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            """
            SELECT *
            FROM price_shock_grid_cells
            WHERE verdict = 'SHADOW_CANDIDATE'
            ORDER BY pair, tf, direction, cell_id
            """
        ).fetchall()


def family_key(row: sqlite3.Row) -> str:
    return f"{row['pair']}_{row['tf']}_{row['direction']}"


def representative(cells: list[sqlite3.Row]) -> sqlite3.Row:
    return sorted(
        cells,
        key=lambda row: (
            -int(row["bonferroni_pass"] or 0),
            -int(row["bh_fdr_pass"] or 0),
            -float(row["wilson_lower_95"] or 0.0),
            -float(row["ev_pct"] or 0.0),
            -int(row["n_trades"] or 0),
            str(row["cell_id"]),
        ),
    )[0]


def raw_tier_for(
    bonf_pass_count: int,
    bh_pass_count: int,
    wilson_lo_max: float,
    n_trades_max: int,
) -> tuple[str, str]:
    if bonf_pass_count >= 3 and wilson_lo_max >= 0.55 and n_trades_max >= 100:
        return "Tier 1", "bonf_pass_count>=3, wilson_lo_max>=0.55, n_trades_max>=100"
    if bonf_pass_count >= 1 and wilson_lo_max >= 0.52 and n_trades_max >= 60:
        return "Tier 2", "bonf_pass_count>=1, wilson_lo_max>=0.52, n_trades_max>=60"
    if bh_pass_count >= 1 and wilson_lo_max >= 0.50 and n_trades_max >= 30:
        return "Tier 3", "bh_pass_count>=1, wilson_lo_max>=0.50, n_trades_max>=30"

    missing: list[str] = []
    if bh_pass_count < 1:
        missing.append("bh_pass_count<1")
    if wilson_lo_max < 0.50:
        missing.append("wilson_lo_max<0.50")
    if n_trades_max < 30:
        missing.append("n_trades_max<30")
    return "Tier 4", "REJECT: " + ", ".join(missing)


def cap_sort_key(row: FamilyRow) -> tuple[float, int, int, int, str]:
    return (
        -row.wilson_lo_max,
        -row.bonf_pass_count,
        -row.bh_pass_count,
        -row.n_trades_max,
        row.family_key,
    )


def build_family_rows(cells: list[sqlite3.Row]) -> list[FamilyRow]:
    grouped: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
    for cell in cells:
        grouped.setdefault((cell["pair"], cell["tf"], cell["direction"]), []).append(cell)

    rows: list[FamilyRow] = []
    for (pair, tf, direction), family_cells in grouped.items():
        rep = representative(family_cells)
        bonf_count = sum(int(cell["bonferroni_pass"] or 0) for cell in family_cells)
        bh_count = sum(int(cell["bh_fdr_pass"] or 0) for cell in family_cells)
        wilsons = [float(cell["wilson_lower_95"] or 0.0) for cell in family_cells]
        ev_pcts = [float(cell["ev_pct"] or 0.0) for cell in family_cells]
        n_trades = [int(cell["n_trades"] or 0) for cell in family_cells]
        wilson_max = max(wilsons)
        n_max = max(n_trades)
        raw_tier, reason = raw_tier_for(bonf_count, bh_count, wilson_max, n_max)
        rows.append(
            FamilyRow(
                family_key=f"{pair}_{tf}_{direction}",
                pair=pair,
                tf=tf,
                direction=direction,
                rep=rep,
                family_cell_count=len(family_cells),
                bonf_pass_count=bonf_count,
                bh_pass_count=bh_count,
                wilson_lo_mean=mean(wilsons),
                wilson_lo_max=wilson_max,
                ev_pct_mean=mean(ev_pcts),
                n_trades_max=n_max,
                n_trades_min=min(n_trades),
                horizon_coverage=len({int(cell["horizon_bars"]) for cell in family_cells}),
                percentile_coverage=len({float(cell["percentile"]) for cell in family_cells}),
                vol_q_coverage=len({str(cell["vol_quintile"]) for cell in family_cells}),
                raw_tier=raw_tier,
                tier=raw_tier,
                tier_reason=reason,
            )
        )

    return apply_tier_caps(rows)


def apply_tier_caps(rows: list[FamilyRow]) -> list[FamilyRow]:
    caps = {"Tier 1": 5, "Tier 2": 5, "Tier 3": 5}
    accepted: set[str] = set()
    capped: list[FamilyRow] = []
    for tier in ("Tier 1", "Tier 2", "Tier 3"):
        candidates = sorted((row for row in rows if row.raw_tier == tier), key=cap_sort_key)
        for idx, row in enumerate(candidates):
            if idx < caps[tier]:
                accepted.add(row.family_key)

    for row in rows:
        if row.family_key in accepted or row.raw_tier == "Tier 4":
            capped.append(row)
            continue
        capped.append(
            FamilyRow(
                **{
                    **row.__dict__,
                    "tier": "Tier 4",
                    "tier_reason": f"REJECT: {row.raw_tier} qualified but exceeded max family cap",
                }
            )
        )
    return sorted(capped, key=lambda row: (row.tier, cap_sort_key(row)))


def fmt_float(value: Any, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def csv_record(row: FamilyRow) -> dict[str, Any]:
    rep = row.rep
    return {
        "family_key": row.family_key,
        "pair": row.pair,
        "tf": row.tf,
        "direction": row.direction,
        "rep_cell_id": rep["cell_id"],
        "rep_percentile": fmt_float(rep["percentile"], 3).rstrip("0").rstrip("."),
        "rep_horizon": rep["horizon_bars"],
        "rep_vol_q": rep["vol_quintile"],
        "n_trades": rep["n_trades"],
        "win_rate": fmt_float(rep["win_rate"], 6),
        "wilson_lower_95": fmt_float(rep["wilson_lower_95"], 6),
        "profit_factor": fmt_float(rep["profit_factor"], 6),
        "ev_pct": fmt_float(rep["ev_pct"], 6),
        "ev_pip": fmt_float(rep["ev_pip"], 6),
        "bonferroni_pass": rep["bonferroni_pass"],
        "bh_fdr_pass": rep["bh_fdr_pass"],
        "family_cell_count": row.family_cell_count,
        "bonf_pass_count": row.bonf_pass_count,
        "bh_pass_count": row.bh_pass_count,
        "wilson_lo_mean": fmt_float(row.wilson_lo_mean, 6),
        "wilson_lo_max": fmt_float(row.wilson_lo_max, 6),
        "ev_pct_mean": fmt_float(row.ev_pct_mean, 6),
        "n_trades_max": row.n_trades_max,
        "n_trades_min": row.n_trades_min,
        "horizon_coverage": row.horizon_coverage,
        "percentile_coverage": row.percentile_coverage,
        "vol_q_coverage": row.vol_q_coverage,
        "tier": row.tier,
        "tier_reason": row.tier_reason,
    }


def write_csv(rows: list[FamilyRow], path: Path = CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(csv_record(row))


def strategy_path(row: FamilyRow) -> str:
    bucket = "scalp" if row.tf == "H1" else "daytrade"
    pair_lc = row.pair.lower()
    direction_lc = "long" if row.direction == "LONG_SHOCK" else "short"
    return f"strategies/{bucket}/price_shock_rev_{pair_lc}_{direction_lc}.py"


def pct_text(value: float) -> str:
    return f"{value * 100:g}"


def tier_counts(rows: list[FamilyRow]) -> dict[str, int]:
    return {tier: sum(1 for row in rows if row.tier == tier) for tier in ("Tier 1", "Tier 2", "Tier 3", "Tier 4")}


def render_family(row: FamilyRow) -> list[str]:
    rep = row.rep
    pct = pct_text(float(rep["percentile"]))
    direction_text = "ロング" if row.direction == "LONG_SHOCK" else "ショート"
    shock_text = "下位" if row.direction == "LONG_SHOCK" else "上位"
    return [
        f"### {row.family_key}",
        f"- **Rep cell**: `{rep['cell_id']}` - pct={pct}, horizon={rep['horizon_bars']}, vol_q={rep['vol_quintile']}",
        (
            "- **Stats**: "
            f"N={rep['n_trades']}, WR={float(rep['win_rate']):.3f}, "
            f"Wilson_lo={float(rep['wilson_lower_95']):.3f}, PF={float(rep['profit_factor']):.2f}, "
            f"EV={float(rep['ev_pct']):.4f}% ({float(rep['ev_pip']):.2f}pip)"
        ),
        (
            "- **Robustness**: "
            f"bonf={row.bonf_pass_count}/family={row.family_cell_count} cell, "
            f"horizon_cov={row.horizon_coverage}/4, pct_cov={row.percentile_coverage}/3"
        ),
        (
            f"- **思想**: 価格が{shock_text}{pct}% percentile 急変 + "
            f"vol_q={rep['vol_quintile']} -> next bar open {direction_text} -> "
            f"{rep['horizon_bars']} bars 後 close"
        ),
        "- **Phase B 実装要点**:",
        f"  - Strategy file: `{strategy_path(row)}`",
        "  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter",
        "  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)",
        f"  - Pair scope: {row.pair} only (cross-pair 拡張は別 BT 必要)",
        "",
    ]


def write_shortlist(rows: list[FamilyRow], path: Path = SHORTLIST_PATH) -> None:
    counts = tier_counts(rows)
    lines = [
        "# Shadow Promote Shortlist (Phase A 分析)",
        "",
        "## Verdict",
        (
            f"**Tier 1 {counts['Tier 1']} family / Tier 2 {counts['Tier 2']} family / "
            f"Tier 3 {counts['Tier 3']} family / Tier 4 {counts['Tier 4']} family**"
        ),
        "",
    ]
    headings = {
        "Tier 1": "## Tier 1 (TOP PROMOTE) - Phase B 実装最優先",
        "Tier 2": "## Tier 2 (PROMOTE)",
        "Tier 3": "## Tier 3 (WATCH)",
    }
    for tier in ("Tier 1", "Tier 2", "Tier 3"):
        lines.extend([headings[tier], ""])
        tier_rows = [row for row in rows if row.tier == tier]
        if not tier_rows:
            lines.extend(["該当なし。", ""])
            continue
        for row in sorted(tier_rows, key=cap_sort_key):
            lines.extend(render_family(row))

    lines.extend(
        [
            "## Tier 4 (REJECT)",
            "| Family | Rep Wilson_lo | Rep N | bonf_pass | Reason |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in sorted((row for row in rows if row.tier == "Tier 4"), key=cap_sort_key):
        rep = row.rep
        lines.append(
            f"| {row.family_key} | {float(rep['wilson_lower_95']):.3f} | {rep['n_trades']} | "
            f"{row.bonf_pass_count} | {row.tier_reason} |"
        )

    lines.extend(
        [
            "",
            "## 思想",
            "価格自身の極値分位後 mean reversion edge。Family 単位で dedup し、horizon/percentile/vol_q overlap を真の独立 edge から切り分けた。",
            "",
            "## 設計欠陥 (現時点で見える)",
            "- BT は固定 horizon exit (動的 SL/TP なし) - Live では cost-aware exit が edge を削る可能性",
            "- Q5 (高ボラ) 集中 - vol 分位の look-ahead 排除確認済 (rolling 1512-bar) だが、Live regime shift で Q5 定義が変動するリスク",
            "- Cross-pair correlation 未補正 - EUR_GBP / EUR_AUD / EUR_USD 同時 trigger で portfolio concentration risk",
            "",
            "## Phase B 推奨スケジュール",
            "1. **Week 1**: Tier 1 上位 3 family を strategy module 化、unit test",
            "2. **Week 2**: demo_trader 統合 + shadow execution 開始",
            "3. **Week 3-6**: N >= 30 Live Shadow 蓄積、Wilson_lo 維持確認",
            "4. **Week 7**: Live promote 判定 (R1: 365日BT + Bonferroni、または Live N >= 30 + Wilson_lo >= 0.50)",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def audit_selection(rows: list[FamilyRow], cells: list[sqlite3.Row]) -> list[str]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    for cell in cells:
        grouped.setdefault(family_key(cell), []).append(cell)
    checks: list[str] = []
    for row in sorted(rows, key=cap_sort_key)[:3]:
        expected = representative(grouped[row.family_key])
        result = "PASS" if expected["cell_id"] == row.rep["cell_id"] else "FAIL"
        checks.append(f"- {result}: {row.family_key} representative `{row.rep['cell_id']}`")
    return checks


def write_audit(rows: list[FamilyRow], cells: list[sqlite3.Row], path: Path = AUDIT_PATH) -> None:
    counts = tier_counts(rows)
    shadow_count = len(cells)
    family_count = len(rows)
    lines = [
        "# Price Shock Dedup Audit",
        "",
        "## Source Counts",
        f"- DB SHADOW_CANDIDATE cell count: {shadow_count}",
        f"- survivors.md expected count: {EXPECTED_SHADOW_CELLS}",
        f"- Count match: {'PASS' if shadow_count == EXPECTED_SHADOW_CELLS else 'FAIL'}",
        f"- Family count: {family_count}",
        f"- Expected family count: {EXPECTED_FAMILIES}",
        f"- Family count match: {'PASS' if family_count == EXPECTED_FAMILIES else 'FAIL'}",
        "",
        "## Tier Counts",
        f"- Tier 1: {counts['Tier 1']}",
        f"- Tier 2: {counts['Tier 2']}",
        f"- Tier 3: {counts['Tier 3']}",
        f"- Tier 4: {counts['Tier 4']}",
        f"- Tier 1+2+3 total: {counts['Tier 1'] + counts['Tier 2'] + counts['Tier 3']} / max 15",
        f"- Tier cap check: {'PASS' if counts['Tier 1'] + counts['Tier 2'] + counts['Tier 3'] <= 15 else 'FAIL'}",
        "",
        "## Representative Selection Spot Check",
        *audit_selection(rows, cells),
        "",
        "## Method",
        "- Family key is literal `(pair, tf, direction)`.",
        "- Representative selection order is Bonferroni pass, BH-FDR pass, Wilson lower 95, EV%, N, cell_id.",
        "- Tier thresholds are literal pre-registration rules; caps are max 5 families per Tier 1/2/3.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(db_path: Path = DB_PATH, report_dir: Path = REPORT_DIR) -> list[FamilyRow]:
    cells = fetch_shadow_cells(db_path)
    rows = build_family_rows(cells)
    write_csv(rows, report_dir / CSV_PATH.name)
    write_shortlist(rows, report_dir / SHORTLIST_PATH.name)
    write_audit(rows, cells, report_dir / AUDIT_PATH.name)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    rows = run(args.db, args.report_dir)
    counts = tier_counts(rows)
    print(
        f"wrote {len(rows)} families: "
        f"T1={counts['Tier 1']} T2={counts['Tier 2']} T3={counts['Tier 3']} T4={counts['Tier 4']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
