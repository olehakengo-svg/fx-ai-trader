"""P-S1(b): HTF Hard Block で消える候補の shadow 退避 + P-S3 診断セット分離。

背景 (2026-07-02 zero-fire 診断 §3):
    sweep_reversion_eurgbp_late は本番同一フィードで 4 回 emit していたが、
    v9.1 HTF Hard Block (htf=bear→BUY 全排除) が shadow/side-channel 記録より
    前に候補ごと削除し、全期間発火 0 (shadow 含む) になっていた。
    4原則#3 (Shadow データ蓄積は削らない、2026-05-28 user 明文化) 違反。

仕様:
    - DaytradeEngine.HTF_BLOCK_SHADOW_RESCUE に登録された戦略の候補が
      HTF Hard Block で除外された場合、shadow_emit_signals へ退避する
      (is_shadow=1 強制、live 送信はゼロのまま)。
    - 退避候補の reasons に [HTF_BLOCK_SHADOW_RESCUE] タグを付与し、
      通常 shadow と区別可能にする (P-S1(a) 決裁用のデータ分離)。
    - P-S3: _COUNT_GATE_BYPASS_LIVE_EXCEPTIONS (live gate bypass) は
      _SILENT_DROP_DIAG_TYPES (ログのみ) から派生しない明示集合に分離。
      06-12 世代 3 戦略は診断のみ追加され、live gate bypass は不変。
"""
from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine


def _cand(entry_type: str, signal: str = "BUY", score: float = 4.0) -> Candidate:
    return Candidate(
        signal=signal, confidence=65, sl=0.860, tp=0.870,
        reasons=["test"], entry_type=entry_type, score=score,
    )


class TestHtfBlockShadowRescue:

    def test_sweep_is_registered_for_rescue(self):
        assert "sweep_reversion_eurgbp_late" in DaytradeEngine.HTF_BLOCK_SHADOW_RESCUE

    def test_rescue_returns_only_registered_strategies(self):
        engine = DaytradeEngine()
        blocked = [_cand("sweep_reversion_eurgbp_late"), _cand("ema_cross")]
        rescued = engine.split_htf_block_shadow_rescue(blocked, htf_agreement="bear")
        assert [c.entry_type for c in rescued] == ["sweep_reversion_eurgbp_late"]

    def test_rescued_candidate_is_tagged(self):
        engine = DaytradeEngine()
        blocked = [_cand("sweep_reversion_eurgbp_late")]
        rescued = engine.split_htf_block_shadow_rescue(blocked, htf_agreement="bear")
        assert any("HTF_BLOCK_SHADOW_RESCUE" in r for r in rescued[0].reasons)

    def test_empty_blocked_list(self):
        engine = DaytradeEngine()
        assert engine.split_htf_block_shadow_rescue([], htf_agreement="bear") == []


class TestSilentDropDiagSeparationPin:
    """P-S3: 診断セット拡張が live gate bypass に波及しないことの pin。"""

    # 2026-07-02 時点の live gate bypass 集合 (user 決裁済みメンバーのみ)。
    # このテストは「診断セットへの追加が bypass に漏れない」ことを固定する。
    _EXPECTED_COUNT_GATE_BYPASS = frozenset({
        "kalman_d7_po_dn_flip",
        "kalman_d7_ema75_break",
        "kalman_d7_trail_atr",
        "zz_pivot_v60_sr",
        "zz_pivot_v60_sr_lo",
        "pivot_detector_v2_5",
    })

    def test_count_gate_bypass_membership_unchanged(self):
        from modules.demo_trader import DemoTrader
        assert (
            frozenset(DemoTrader._COUNT_GATE_BYPASS_LIVE_EXCEPTIONS)
            == self._EXPECTED_COUNT_GATE_BYPASS
        )

    def test_0612_generation_in_diag_types_only(self):
        from modules.demo_trader import DemoTrader
        gen_0612 = {
            "sweep_reversion_eurgbp_late",
            "hull_donchian_fade",
            "usdjpy_carry_dip_accumulator",
        }
        assert gen_0612 <= set(DemoTrader._SILENT_DROP_DIAG_TYPES)
        assert not (gen_0612 & set(DemoTrader._COUNT_GATE_BYPASS_LIVE_EXCEPTIONS))
