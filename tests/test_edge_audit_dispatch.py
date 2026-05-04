"""Tests for tools/edge_audit_dispatch.py (W4-EDA Task 3)."""
import json
import subprocess
import sys


def test_dispatch_writes_queue_file_with_replaced_placeholders(tmp_path):
    template = (
        "---\n"
        "id: {{TASK_ID}}\n"
        "title: \"[W4-EDA] Edge Design Audit — {{STRATEGY}}\"\n"
        "created_at: {{CREATED_AT}}\n"
        "---\n\n"
        "Strategy: {{STRATEGY}} ({{STRATEGY_PATH}})\n"
        "Tier: {{TIER}} / {{SOURCE_TIER}}\n"
        "Pairs: {{PAIRS}}\n"
        "Metrics:\n```json\n{{HISTORICAL_METRICS_JSON}}\n```\n"
    )
    template_path = tmp_path / "_PROMPT_TEMPLATE.md"
    template_path.write_text(template)

    metrics = [{"strategy": "bb_rsi_reversion", "pair": "EUR_JPY", "pf": 1.05, "kelly": 0.12}]
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "tools/edge_audit_dispatch.py",
            "--strategy",
            "bb_rsi_reversion",
            "--strategy-path",
            "strategies/scalp/bb_rsi.py",
            "--tier",
            "Tier 3 (FORCE_DEMOTED)",
            "--source-tier",
            "force_demoted",
            "--pairs",
            "ALL",
            "--metrics",
            json.dumps(metrics),
            "--template",
            str(template_path),
            "--queue-dir",
            str(queue_dir),
            "--created-at",
            "2026-05-04T15:00:00+0900",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    written = list(queue_dir.glob("*-w4-eda-bb_rsi_reversion.md"))
    assert len(written) == 1
    body = written[0].read_text()
    assert "bb_rsi_reversion" in body
    assert "strategies/scalp/bb_rsi.py" in body
    assert "force_demoted" in body
    assert '"pf": 1.05' in body
    # all placeholders substituted
    for placeholder in (
        "{{TASK_ID}}",
        "{{STRATEGY}}",
        "{{STRATEGY_PATH}}",
        "{{TIER}}",
        "{{SOURCE_TIER}}",
        "{{PAIRS}}",
        "{{HISTORICAL_METRICS_JSON}}",
        "{{CREATED_AT}}",
    ):
        assert placeholder not in body, f"unsubstituted: {placeholder}"
    # filename includes timestamp + strategy
    assert written[0].name.startswith("20260504")
    assert written[0].name.endswith("-w4-eda-bb_rsi_reversion.md")


def test_dispatch_creates_queue_dir_if_missing(tmp_path):
    template_path = tmp_path / "_PROMPT_TEMPLATE.md"
    template_path.write_text("S={{STRATEGY}}\n")
    queue_dir = tmp_path / "fresh" / "queue"
    assert not queue_dir.exists()

    result = subprocess.run(
        [
            sys.executable,
            "tools/edge_audit_dispatch.py",
            "--strategy",
            "x",
            "--strategy-path",
            "p",
            "--tier",
            "Tier 1",
            "--source-tier",
            "elite_live",
            "--pairs",
            "ALL",
            "--metrics",
            "[]",
            "--template",
            str(template_path),
            "--queue-dir",
            str(queue_dir),
            "--created-at",
            "2026-05-04T15:00:00+0900",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert queue_dir.exists()
    assert any(queue_dir.glob("*-w4-eda-x.md"))
