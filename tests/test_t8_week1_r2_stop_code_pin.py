"""T8 初週 pre-reg ゲート抵触 → R2 LIVE 転送停止の code pin 回帰テスト。

env フラグでは再武装可能なため code で固定する (lesson: KV disable は pin にならない)。
根拠: knowledge-base/wiki/decisions/t8-week1-gate-breach-2026-07-06.md
復帰は forensic 完了 + 再 LOCK の PR のみ (このテストの削除/変更を伴う = レビュー必須)。
"""
import os
import importlib


def test_hull_donchian_fade_live_pinned_off_regardless_of_env(monkeypatch):
    monkeypatch.setenv("HULL_DONCHIAN_FADE_LIVE_ENABLE", "1")
    import modules.demo_trader as dt
    importlib.reload(dt)
    try:
        assert dt.DemoTrader._HULL_DONCHIAN_FADE_LIVE_ENABLE is False
        assert not dt.DemoTrader._hull_donchian_fade_live_eligible(
            "hull_donchian_fade", "EUR_USD")
    finally:
        monkeypatch.delenv("HULL_DONCHIAN_FADE_LIVE_ENABLE", raising=False)
        importlib.reload(dt)


def test_sweep_reversion_eurgbp_live_unpinned_by_ps1a_option_b(monkeypatch):
    """P-S1(a) Option B (user 条件付き承認 2026-07-24) による pin 解除の対称 pin。

    解除も env ではなく code 定数で行われる — env で再無効化できないことを固定
    (lesson: KV/env は pin にならない。有効化/無効化とも変更 = テスト変更を伴う
    PR = レビュー必須構造を維持)。
    根拠: knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md §3.3
    """
    monkeypatch.setenv("SWEEP_REVERSION_EURGBP_LIVE_ENABLE", "0")
    import modules.demo_trader as dt
    importlib.reload(dt)
    try:
        assert dt.DemoTrader._SWEEP_REVERSION_EURGBP_LIVE_ENABLE is True
        assert dt.DemoTrader._sweep_reversion_eurgbp_live_eligible(
            "sweep_reversion_eurgbp_late", "EUR_GBP")
        # cell スコープ: 他ペア/他戦略は不変
        assert not dt.DemoTrader._sweep_reversion_eurgbp_live_eligible(
            "sweep_reversion_eurgbp_late", "GBP_USD")
        assert not dt.DemoTrader._sweep_reversion_eurgbp_live_eligible(
            "eurgbp_daily_mr", "EUR_GBP")
    finally:
        monkeypatch.delenv("SWEEP_REVERSION_EURGBP_LIVE_ENABLE", raising=False)
        importlib.reload(dt)
