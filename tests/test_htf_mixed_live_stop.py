"""HTF mixed cell stop: trendline_sweep×GBP_USD live 転送停止 (rule:R2)。

背景 (2026-07-07 T1 forensic §7 / mtf-mixed-gate-noop-forensic-2026-07-07):
    close_analysis タグ「⚖️ 4H+1D 不一致 → シグナル抑制中」は診断のみで、
    v9.1 HTF Hard Block は htf_agreement が bull/bear の時しか候補を除外
    しない (mixed = 候補フィルタ no-op)。trendline_sweep は自前 HTF guard を
    持たず (self-contained guard 欠如)、mixed 状態の候補が無抑制で live 転送
    されていた。clean live 2026-06-03..07-03: mixed N=15 EV=-3.38p/-50.7p
    vs aligned N=4 +1.5p。shadow mixed N=7 EV=-7.20p が corroborate。

仕様:
    - DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS 登録セルの候補は
      htf_agreement == "mixed" のとき候補リストから除外され、
      shadow_emit_signals へ退避する (is_shadow=1 強制、live 送信ゼロ)。
    - 退避候補の reasons に [HTF_MIXED_LIVE_STOP] タグを付与し、
      HTF_BLOCK_SHADOW_RESCUE 由来 shadow とセグメント分離可能にする。
    - mixed 以外 (bull/bear/空) では無変換 — bull/bear は既存 v9.1
      Hard Block の責務であり、本機構は重複適用しない。
"""
from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine


def _cand(entry_type: str, signal: str = "BUY", score: float = 5.0) -> Candidate:
    return Candidate(
        signal=signal, confidence=65, sl=1.340, tp=1.360,
        reasons=["test"], entry_type=entry_type, score=score,
    )


class TestHtfMixedLiveStop:

    def test_cell_is_registered(self):
        assert ("trendline_sweep", "GBP_USD") in DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS

    def test_mixed_stops_registered_cell_only(self):
        engine = DaytradeEngine()
        cands = [_cand("trendline_sweep"), _cand("doji_breakout")]
        kept, stopped = engine.split_htf_mixed_live_stop(
            cands, "GBP_USD", htf_agreement="mixed")
        assert [c.entry_type for c in kept] == ["doji_breakout"]
        assert [c.entry_type for c in stopped] == ["trendline_sweep"]

    def test_stopped_candidate_is_tagged(self):
        engine = DaytradeEngine()
        _, stopped = engine.split_htf_mixed_live_stop(
            [_cand("trendline_sweep")], "GBP_USD", htf_agreement="mixed")
        assert len(stopped) == 1
        assert any("HTF_MIXED_LIVE_STOP" in r for r in stopped[0].reasons)

    def test_other_pair_not_stopped(self):
        engine = DaytradeEngine()
        kept, stopped = engine.split_htf_mixed_live_stop(
            [_cand("trendline_sweep")], "EUR_USD", htf_agreement="mixed")
        assert stopped == []
        assert [c.entry_type for c in kept] == ["trendline_sweep"]

    def test_non_mixed_agreement_is_passthrough(self):
        engine = DaytradeEngine()
        for agreement in ("bull", "bear", "", "neutral"):
            kept, stopped = engine.split_htf_mixed_live_stop(
                [_cand("trendline_sweep")], "GBP_USD", htf_agreement=agreement)
            assert stopped == [], f"agreement={agreement!r} must not stop"
            assert [c.entry_type for c in kept] == ["trendline_sweep"]

    def test_empty_candidates(self):
        engine = DaytradeEngine()
        kept, stopped = engine.split_htf_mixed_live_stop(
            [], "GBP_USD", htf_agreement="mixed")
        assert kept == []
        assert stopped == []
