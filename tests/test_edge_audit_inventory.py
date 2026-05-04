"""Tests for tools/build_edge_audit_inventory.py (W4-EDA Task 1)."""
import json
import subprocess
import sys


def test_inventory_normalizes_string_list_schema(tmp_path):
    """Real tier-master.json uses list[str] for elite_live / force_demoted."""
    tier_master = {
        "elite_live": ["trendline_sweep"],
        "pair_promoted": [["doji_breakout", "GBP_USD"]],
        "force_demoted": ["ema_cross", "atr_regime_break"],
        "scalp_sentinel": ["bb_rsi_reversion"],
        "universal_sentinel": [],
        "pair_demoted": [],
    }
    src = tmp_path / "tier-master.json"
    src.write_text(json.dumps(tier_master))
    out = tmp_path / "_INVENTORY.md"
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "extra_phase0.py").write_text("# unclassified")

    result = subprocess.run(
        [
            sys.executable,
            "tools/build_edge_audit_inventory.py",
            "--source",
            str(src),
            "--out",
            str(out),
            "--strategies-dir",
            str(strategies_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    # Tier 1 has trendline_sweep + doji_breakout
    tier1 = body.split("## Tier 2")[0]
    assert "trendline_sweep" in tier1
    assert "doji_breakout" in tier1
    # Tier 2 phase0 discovered from strategies dir
    tier2 = body.split("## Tier 2")[1].split("## Tier 3")[0]
    assert "extra_phase0" in tier2
    # Tier 3 has both force_demoted strategies
    tier3 = body.split("## Tier 3")[1].split("## Tier 4")[0]
    assert "ema_cross" in tier3
    assert "atr_regime_break" in tier3


def test_inventory_groups_by_tier(tmp_path):
    tier_master = {
        "elite_live": [{"strategy": "trendline_sweep"}],
        "pair_promoted": [
            {"strategy": "doji_breakout", "pair": "GBP_USD"},
            {"strategy": "doji_breakout", "pair": "USD_JPY"},
        ],
        "force_demoted": [{"strategy": "ema_cross"}],
        "scalp_sentinel": [{"strategy": "bb_rsi_reversion"}],
        "phase0_shadow": [{"strategy": "adx_trend_continuation"}],
    }
    src = tmp_path / "tier-master.json"
    src.write_text(json.dumps(tier_master))
    out = tmp_path / "_INVENTORY.md"

    result = subprocess.run(
        [
            sys.executable,
            "tools/build_edge_audit_inventory.py",
            "--source",
            str(src),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    for tier in [
        "Tier 1 (LIVE)",
        "Tier 2 (Shadow)",
        "Tier 3 (FORCE_DEMOTED)",
        "Tier 4 (SCALP_SENTINEL)",
    ]:
        assert tier in body, f"missing section: {tier}"
    # doji_breakout dedup'd into one row, both pairs joined
    assert body.count("| doji_breakout |") == 1
    assert "GBP_USD, USD_JPY" in body
    # ordering
    assert (
        body.index("Tier 1")
        < body.index("Tier 2")
        < body.index("Tier 3")
        < body.index("Tier 4")
    )


def test_inventory_dedupe_across_tiers(tmp_path):
    """If a strategy appears in multiple source tiers, only the higher tier wins."""
    tier_master = {
        "elite_live": [],
        "pair_promoted": [{"strategy": "doji_breakout", "pair": "GBP_USD"}],
        "force_demoted": [{"strategy": "doji_breakout"}],  # duplicate
        "scalp_sentinel": [],
        "phase0_shadow": [],
    }
    src = tmp_path / "tier-master.json"
    src.write_text(json.dumps(tier_master))
    out = tmp_path / "_INVENTORY.md"

    result = subprocess.run(
        [
            sys.executable,
            "tools/build_edge_audit_inventory.py",
            "--source",
            str(src),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    assert body.count("| doji_breakout |") == 1
    # appears under Tier 1, not Tier 3
    tier1_section = body.split("## Tier 2")[0]
    tier3_section = body.split("## Tier 3")[1].split("## Tier 4")[0] if "## Tier 4" in body else body.split("## Tier 3")[1]
    assert "doji_breakout" in tier1_section
    assert "doji_breakout" not in tier3_section
