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


def test_sweep_reversion_eurgbp_live_pinned_off_regardless_of_env(monkeypatch):
    monkeypatch.setenv("SWEEP_REVERSION_EURGBP_LIVE_ENABLE", "1")
    import modules.demo_trader as dt
    importlib.reload(dt)
    try:
        assert dt.DemoTrader._SWEEP_REVERSION_EURGBP_LIVE_ENABLE is False
        assert not dt.DemoTrader._sweep_reversion_eurgbp_live_eligible(
            "sweep_reversion_eurgbp_late", "EUR_GBP")
    finally:
        monkeypatch.delenv("SWEEP_REVERSION_EURGBP_LIVE_ENABLE", raising=False)
        importlib.reload(dt)
