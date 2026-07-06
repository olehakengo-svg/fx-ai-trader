"""T5 JPYキャップ撤退 pre-reg 発動 → LIVE lot 0.5x SIZE lever の回帰テスト。

トリガー「USD_JPY D1 close > 160.80」は 2026-06-18 に成立 (以降14営業日連続超え)。
pre-reg の発動アクションは機械的・裁量禁止 (rule:R2)。
根拠: knowledge-base/wiki/decisions/jpy-cap-exit-prereg-2026-06-12.md
解除は復帰条件の KB 記録 + このテストの変更を伴う PR のみ = レビュー必須。
env/KV 経路は意図的に不在 (lesson: KV disable は pin にならない)。
"""
import modules.demo_trader as dt

TARGETS = (
    "vsg_jpy_reversal",
    "dt_sr_channel_reversal",
    "vix_carry_unwind",
    "ema200_trend_reversal",
)


def _trader():
    # __init__ はスレッド/DB を起動するため回避。lever は self 状態を使わない。
    return dt.DemoTrader.__new__(dt.DemoTrader)


def test_lever_is_code_pinned_active():
    assert dt.JPY_CAP_EXIT_SIZE_LEVER_ACTIVE is True
    assert dt.JPY_CAP_EXIT_SIZE_LEVER_STRATEGIES == frozenset(TARGETS)


def test_lever_halves_live_units_for_all_target_strategies():
    t = _trader()
    for name in TARGETS:
        units, applied = t._resolve_jpy_cap_exit_size_lever(
            5000, name, is_shadow=False)
        assert applied is True
        assert units == 2500


def test_lever_never_touches_shadow():
    t = _trader()
    for name in TARGETS:
        units, applied = t._resolve_jpy_cap_exit_size_lever(
            5000, name, is_shadow=True)
        assert applied is False
        assert units == 5000


def test_lever_noop_for_non_target_strategies():
    t = _trader()
    for name in ("trendline_sweep", "doji_breakout", "orb_trap"):
        units, applied = t._resolve_jpy_cap_exit_size_lever(
            5000, name, is_shadow=False)
        assert applied is False
        assert units == 5000


def test_lever_floor_preserves_1000u_validation_lot_contract():
    """vix Overlap pilot 等の 1000u 固定契約 (agg-Kelly bypass の正当性根拠) を
    温存する。floor で変化しない場合は applied=False (タグを付けない)。"""
    t = _trader()
    units, applied = t._resolve_jpy_cap_exit_size_lever(
        1000, "vix_carry_unwind", is_shadow=False)
    assert applied is False
    assert units == 1000

    units, applied = t._resolve_jpy_cap_exit_size_lever(
        2000, "vix_carry_unwind", is_shadow=False)
    assert applied is True
    assert units == 1000  # floor に当たるが減額は発生 → applied=True
