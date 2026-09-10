"""WS4 T15 quality-gate regression tests (fable5 audit P1-6 / P1-7 / P1-8, rule:R3).

P1-6: `_resend_pending_oanda_trades` の再送ガード共通化 —
      FORCE/PAIR demotion に加えて Q4 / SHIELD mode / aggregate Kelly /
      MC-ruin を resend 直前に再実行する (defense-in-depth)。
P1-7: CI paths filter 撤廃 + hip1 holdout guard の CI job 化 +
      dev.agent.yaml の誤った --no-verify 根拠の訂正 (退行 pin)。
P1-8: run_scalp_backtest inline SCALP_BT_QUALIFIED と本番 enabled scalp
      戦略の drift 機械検査 (scripts/check.py step 5b)。意図的 drift で
      red になることを合成 fixture で確認する (red→green 検証)。
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import modules.demo_trader as demo_trader_mod
from modules.demo_trader import DemoTrader

import scripts.check as check_mod

REPO_ROOT = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════
# P1-6: resend promote-gate 共通ヘルパー
# ══════════════════════════════════════════════════════════════


def _bare_trader(monkeypatch, *, elite=False, agg_kelly=0.1, ruin=0.1,
                 strat_mode="auto", pair_demoted=False):
    """DemoTrader.__new__ ベースの軽量 trader (constructor 副作用なし)。

    gate helper が参照する依存だけを注入する。既定値は「全 gate 通過」。
    """
    trader = DemoTrader.__new__(DemoTrader)
    trader._add_log = lambda *_a, **_k: None
    trader._runtime_pair_demoted = (
        {("gate_test_type", "USD_JPY")} if pair_demoted else set()
    )
    monkeypatch.setattr(trader, "_is_elite_live",
                        lambda *_a, **_k: elite, raising=False)
    monkeypatch.setattr(trader, "_get_aggregate_kelly",
                        lambda: agg_kelly, raising=False)
    monkeypatch.setattr(trader, "_get_ruin_probability",
                        lambda: ruin, raising=False)
    oanda = MagicMock()
    oanda.get_strategy_mode.return_value = strat_mode
    trader._oanda = oanda
    return trader


def test_resend_gate_passes_when_all_gates_clear(monkeypatch):
    trader = _bare_trader(monkeypatch)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    assert trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80) is None


def test_resend_gate_blocks_force_demoted(monkeypatch):
    trader = _bare_trader(monkeypatch)
    # _FORCE_DEMOTED は class 集合 — 実在の恒久 demoted 戦略で検証
    force_demoted = next(iter(DemoTrader._FORCE_DEMOTED))
    reason = trader._resend_promote_gate_block_reason(
        force_demoted, "USD_JPY", "scalp", confidence=80)
    assert reason == "FORCE_DEMOTED_GATE"


def test_resend_gate_blocks_pair_demoted(monkeypatch):
    trader = _bare_trader(monkeypatch, pair_demoted=True)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    reason = trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80)
    assert reason == "PAIR_DEMOTED_GATE"


def test_resend_gate_blocks_q4(monkeypatch):
    trader = _bare_trader(monkeypatch)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: True)
    reason = trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80)
    assert reason == "Q4_GATE"


def test_resend_gate_q4_exempts_elite(monkeypatch):
    trader = _bare_trader(monkeypatch, elite=True)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: True)
    assert trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80) is None


def test_resend_gate_blocks_shield_mode(monkeypatch):
    trader = _bare_trader(monkeypatch)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    blocked_mode = next(iter(DemoTrader._OANDA_MODE_BLOCKED))
    reason = trader._resend_promote_gate_block_reason(
        "gate_test_type", "EUR_USD", blocked_mode, confidence=80)
    assert reason == "SHIELD_MODE_GATE"


def test_resend_gate_shield_mode_exempts_whitelist(monkeypatch):
    trader = _bare_trader(monkeypatch)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    whitelisted = next(iter(DemoTrader._SHIELD_EUR_DT_WHITELIST))
    assert trader._resend_promote_gate_block_reason(
        whitelisted, "EUR_USD", "daytrade_eur", confidence=80) is None


def test_resend_gate_blocks_negative_aggregate_kelly(monkeypatch):
    trader = _bare_trader(monkeypatch, agg_kelly=-0.25)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    reason = trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80)
    assert reason == "AGG_KELLY_GATE"


def test_resend_gate_kelly_minlot_bypass_preserved(monkeypatch):
    """1000u 固定契約 (pre-reg bypass) は主経路同様に agg Kelly gate を免除。

    2026-08-03: `next(iter(set))` は member 選択が非決定で、demote 済み member
    (vix_carry_unwind、PAIR_DEMOTED_GATE が Kelly 判定より先に発火) を掴むと
    偽 FAIL する。live-capable な weekend_gap_fade を明示指定して Kelly bypass
    機構のみを検証する。"""
    trader = _bare_trader(monkeypatch, agg_kelly=-0.25)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    bypass_type = "weekend_gap_fade"
    assert bypass_type in DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES
    assert trader._resend_promote_gate_block_reason(
        bypass_type, "USD_JPY", "scalp", confidence=80) is None


def test_resend_gate_blocks_mc_ruin(monkeypatch):
    trader = _bare_trader(monkeypatch, ruin=0.85)
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    reason = trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80)
    assert reason == "MC_RUIN_GATE"


def test_resend_gate_sentinel_strategy_mode_exempts_kelly_and_ruin(monkeypatch):
    """SENTINEL (0.01lot データ収集) は主経路同様 Kelly/MC-ruin gate 免除。"""
    trader = _bare_trader(monkeypatch, agg_kelly=-0.25, ruin=0.85,
                          strat_mode="sentinel")
    monkeypatch.setattr(demo_trader_mod, "_q4_should_shadow",
                        lambda _et, _c: False)
    assert trader._resend_promote_gate_block_reason(
        "gate_test_type", "USD_JPY", "scalp", confidence=80) is None


def _resend_env(monkeypatch, *, block_reason):
    """_resend_pending_oanda_trades の end-to-end fixture."""
    trader = DemoTrader.__new__(DemoTrader)
    logs = []
    trader._add_log = logs.append
    oanda = MagicMock()
    oanda.active = True
    oanda.is_mode_allowed.return_value = True
    trader._oanda = oanda
    db = MagicMock()
    from datetime import datetime, timezone
    db.get_open_trades_without_oanda.return_value = [{
        "trade_id": "T15-1", "direction": "BUY", "sl": 1.0, "tp": 2.0,
        "mode": "scalp", "instrument": "USD_JPY",
        "entry_time": datetime.now(timezone.utc).isoformat(),
        "entry_type": "gate_test_type", "confidence": 80,
    }]
    trader._db = db
    monkeypatch.setattr(
        trader, "_resend_promote_gate_block_reason",
        lambda *_a, **_k: block_reason, raising=False)
    return trader, oanda, logs


def test_resend_loop_skips_when_gate_blocks(monkeypatch):
    trader, oanda, logs = _resend_env(monkeypatch, block_reason="AGG_KELLY_GATE")
    trader._resend_pending_oanda_trades()
    assert not oanda.open_trade.called, (
        "gate block 時は resend してはならない (P1-6 defense-in-depth)")
    assert any("[AGG_KELLY_GATE] resend skipped" in m for m in logs)


def test_resend_loop_sends_when_gate_clears(monkeypatch):
    trader, oanda, logs = _resend_env(monkeypatch, block_reason=None)
    trader._resend_pending_oanda_trades()
    assert oanda.open_trade.call_count == 1, "gate 通過時は従来通り補完送信する"


# ══════════════════════════════════════════════════════════════
# P1-7: CI 品質ゲート pin
# ══════════════════════════════════════════════════════════════


def test_ci_yaml_has_no_paths_filter():
    """push trigger の paths filter 再導入 (テスト盲点の復活) を封鎖。"""
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8")
    real_lines = [
        ln for ln in ci_text.splitlines() if not ln.strip().startswith("#")
    ]
    assert not any(re.match(r"\s*paths\s*:", ln) for ln in real_lines), (
        "P1-7: ci.yml に paths filter を再導入してはならない "
        "(tests/tools/agents/knowledge-base 変更で CI が走らない盲点が復活する)")


def test_ci_yaml_runs_hip1_holdout_guard():
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8")
    assert "hip1-holdout-guard" in ci_text
    assert "tools/precommit/check_holdout_manifest.py" in ci_text, (
        "P1-7: HIP-1 holdout 改変ガードは CI job として実行されなければならない")


def test_dev_agent_yaml_does_not_blame_hip1_for_full_pytest():
    """--no-verify 根拠の誤記 (hip1 が full pytest を走らせる) の復活を封鎖。"""
    text = (REPO_ROOT / "agents" / "cma" / "dev.agent.yaml").read_text(
        encoding="utf-8")
    assert "hip1-holdout-manifest, always_run) が full pytest" not in text, (
        "P1-7: full pytest の原因はカスタム pre-commit スクリプト側であり "
        "hip1-holdout-manifest ではない (監査 P1-7 で訂正済み)")


# ══════════════════════════════════════════════════════════════
# P1-8: scalp BT QUALIFIED_TYPES drift 検査
# ══════════════════════════════════════════════════════════════


def test_scalp_bt_qualified_sync_green_on_repo():
    errors, _warns = check_mod.check_scalp_bt_qualified_sync()
    assert errors == [], f"P1-8 drift 検査が実リポジトリで red: {errors}"


def _drift_fixture(tmp_path, *, app_body, strategies):
    app_py = tmp_path / "app.py"
    app_py.write_text(app_body, encoding="utf-8")
    scalp_dir = tmp_path / "scalp"
    scalp_dir.mkdir()
    for fname, name, enabled in strategies:
        scalp_dir.joinpath(fname).write_text(
            f'class S:\n    name = "{name}"\n    enabled = {enabled}\n',
            encoding="utf-8")
    return app_py, scalp_dir


def test_scalp_bt_qualified_sync_red_on_intentional_drift(tmp_path, monkeypatch):
    """意図的 drift (enabled 戦略が BT set にも除外リストにも無い) で red。"""
    app_py, scalp_dir = _drift_fixture(
        tmp_path,
        app_body=(
            'SCALP_BT_QUALIFIED = {\n    "bb_rsi_reversion",\n}\n'
            'SCALP_BT_EXCLUDED_TYPES = {\n    "mtf_counter_trend_scalp",\n}\n'
        ),
        strategies=[
            ("bb_rsi.py", "bb_rsi_reversion", True),
            ("drifted.py", "drifted_new_scalp", True),
        ],
    )
    monkeypatch.setattr(check_mod, "APP_PY", app_py)
    monkeypatch.setattr(check_mod, "SCALP_DIR", scalp_dir)
    errors, _warns = check_mod.check_scalp_bt_qualified_sync()
    assert any("drifted_new_scalp" in e for e in errors), (
        f"意図的 drift が ERROR にならなかった: {errors}")


def test_scalp_bt_qualified_sync_green_when_documented_exclusion(tmp_path, monkeypatch):
    """除外リストに載っていれば green (意図的除外の文書化パス)。"""
    app_py, scalp_dir = _drift_fixture(
        tmp_path,
        app_body=(
            'SCALP_BT_QUALIFIED = {\n    "bb_rsi_reversion",\n}\n'
            'SCALP_BT_EXCLUDED_TYPES = {\n    "vec_only_scalp",\n}\n'
        ),
        strategies=[
            ("bb_rsi.py", "bb_rsi_reversion", True),
            ("vec_only.py", "vec_only_scalp", True),
        ],
    )
    monkeypatch.setattr(check_mod, "APP_PY", app_py)
    monkeypatch.setattr(check_mod, "SCALP_DIR", scalp_dir)
    errors, _warns = check_mod.check_scalp_bt_qualified_sync()
    assert errors == []


def test_scalp_bt_qualified_sync_red_on_contradictory_overlap(tmp_path, monkeypatch):
    """qualified かつ excluded の矛盾登録は red。"""
    app_py, scalp_dir = _drift_fixture(
        tmp_path,
        app_body=(
            'SCALP_BT_QUALIFIED = {\n    "bb_rsi_reversion",\n}\n'
            'SCALP_BT_EXCLUDED_TYPES = {\n    "bb_rsi_reversion",\n}\n'
        ),
        strategies=[("bb_rsi.py", "bb_rsi_reversion", True)],
    )
    monkeypatch.setattr(check_mod, "APP_PY", app_py)
    monkeypatch.setattr(check_mod, "SCALP_DIR", scalp_dir)
    errors, _warns = check_mod.check_scalp_bt_qualified_sync()
    assert any("両方に登録" in e for e in errors)


def test_scalp_bt_excluded_types_match_audit_p18():
    """audit P1-8 で特定された 3 戦略が文書化された除外として登録済み。"""
    excluded, err = check_mod.extract_set(
        REPO_ROOT / "app.py", "SCALP_BT_EXCLUDED_TYPES")
    assert err is None
    assert {"mtf_trend_follow_scalp", "mtf_counter_trend_scalp",
            "mtf_regime_trend_cascade_scalp"} <= excluded
