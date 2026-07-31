"""P-S1(a) Option B 実装の pin テスト (draft branch — トリガ成立日にマージ)。

対象: (1) order 層 12-bar min-spacing (2) HTF Hard Block cell exemption
(3) registry 置換 (4) hydration 窓。
決裁: knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md §3.1-3.3
手順: knowledge-base/wiki/decisions/sweep-reversion-ps1a-execution-runbook-2026-07-31.md
"""
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from strategies.daytrade import DaytradeEngine

SWEEP = "sweep_reversion_eurgbp_late"
ROOT = Path(__file__).resolve().parents[1]


def _light_trader(db: DemoDB) -> DemoTrader:
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = db
    trader._lock = threading.RLock()
    trader._recent_signal_emits = {}
    trader._order_min_spacing_last_accept = {}
    trader._dedup_stats = DemoTrader._new_dedup_stats()
    trader._add_log = lambda _msg: None
    return trader


class TestOrderMinSpacing:
    """§3.1: 検証済み estimand (12y grid dedup_indices gap=12) の live 受理点執行。"""

    def test_blocks_within_12_bars_and_counts_dedicated_reason(self, tmp_path):
        trader = _light_trader(DemoDB(str(tmp_path / "sp1.db")))
        t0 = datetime(2026, 7, 6, 21, 15, tzinfo=timezone.utc)
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0, tf="15m", mode="daytrade_eurgbp") is None
        # 同夜 1 バー後 (§1.1 実測 07-06 21:32 の再emit パターン) は live block
        blocked = trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0 + timedelta(minutes=15),
            tf="15m", mode="daytrade_eurgbp")
        assert blocked is not None
        # 専用 reason key で order_bar_dedup と区別 (§3.1)
        assert trader._block_counts["daytrade_eurgbp:order_min_spacing"] == 1
        assert trader._block_counts_per_strategy[f"{SWEEP}:order_min_spacing"] == 1

    def test_pointer_does_not_advance_on_blocked_emit(self, tmp_path):
        """dedup_indices 意味論: 落とした emit はポインタを進めない。"""
        trader = _light_trader(DemoDB(str(tmp_path / "sp2.db")))
        t0 = datetime(2026, 7, 6, 21, 0, tzinfo=timezone.utc)
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0, tf="15m", mode="m") is None
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0 + timedelta(minutes=165),
            tf="15m", mode="m") is not None
        # t0+180m は「最後に受理した t0」から 12 バー — 受理される
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0 + timedelta(minutes=180),
            tf="15m", mode="m") is None

    def test_exact_12_bars_is_accepted(self, tmp_path):
        """境界: research grid `i - keep[-1] >= gap` — ちょうど 3h は keep。"""
        trader = _light_trader(DemoDB(str(tmp_path / "sp3.db")))
        t0 = datetime(2026, 7, 6, 21, 0, tzinfo=timezone.utc)
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0, tf="15m", mode="m") is None
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", t0 + timedelta(hours=3),
            tf="15m", mode="m") is None

    def test_non_registered_strategy_unaffected(self, tmp_path):
        """戦略別 opt-in — 登録外の戦略は挙動不変 (§3.1)。"""
        trader = _light_trader(DemoDB(str(tmp_path / "sp4.db")))
        t0 = datetime(2026, 7, 6, 21, 0, tzinfo=timezone.utc)
        for _ in range(3):
            assert trader._maybe_reserve_order_min_spacing(
                "hull_donchian_fade", "EUR_USD", "BUY", t0,
                tf="15m", mode="m") is None
        assert "m:order_min_spacing" not in getattr(trader, "_block_counts", {})

    def test_hydration_window_covers_12_bars(self):
        """§3.1: hydration 窓 >= 12x15m=3h (怠ると deploy 直後に spacing 素通り)。"""
        assert DemoTrader._order_min_spacing_hydrate_window_sec() >= 12 * 900

    def test_hydration_seeds_only_registered_strategies(self, tmp_path):
        trader = _light_trader(DemoDB(str(tmp_path / "sp5.db")))
        ts = datetime(2026, 7, 6, 21, 16, tzinfo=timezone.utc)
        n = trader._hydrate_order_min_spacing({
            (SWEEP, "EUR_GBP", "BUY"): ts,
            ("other_strategy", "EUR_USD", "BUY"): ts,
        })
        assert n == 1
        # 再起動直後でも hydrated 時刻から 12 バー以内の emit は block (restart 耐性)
        assert trader._maybe_reserve_order_min_spacing(
            SWEEP, "EUR_GBP", "BUY", ts + timedelta(minutes=30),
            tf="15m", mode="m") is not None


class TestHtfHardBlockExemption:
    """§3.2: cell-scoped exemption。blast radius = 1 cell のみ。"""

    def test_exempt_cell_registered(self):
        assert (SWEEP, "EUR_GBP") in DaytradeEngine.HTF_HARD_BLOCK_EXEMPT_CELLS

    def test_exempt_set_is_single_cell(self):
        assert DaytradeEngine.HTF_HARD_BLOCK_EXEMPT_CELLS == frozenset(
            {(SWEEP, "EUR_GBP")})

    def test_predicate_cell_scope(self):
        assert DaytradeEngine.htf_hard_block_exempt(SWEEP, "EUR_GBP")
        assert not DaytradeEngine.htf_hard_block_exempt(SWEEP, "GBP_USD")
        assert not DaytradeEngine.htf_hard_block_exempt("ema_cross", "EUR_GBP")

    def test_rescue_registration_left_in_place(self):
        # rescue 機構は他戦略/将来用に残置 (§3.2)。exemption 発動時、当該候補は
        # blocked にならないため rescue を経由しない (構造的に排他)。
        assert SWEEP in DaytradeEngine.HTF_BLOCK_SHADOW_RESCUE


class TestSweepLivePinReleased:
    """§3.3-3: code pin 解除 — env に依存しない (KV/env は pin にならない)。"""

    def test_pin_constant_is_true(self):
        assert DemoTrader._SWEEP_REVERSION_EURGBP_LIVE_ENABLE is True

    def test_eligibility_cell_scope(self):
        assert DemoTrader._sweep_reversion_eurgbp_live_eligible(SWEEP, "EUR_GBP")
        assert not DemoTrader._sweep_reversion_eurgbp_live_eligible(SWEEP, "GBP_USD")
        assert not DemoTrader._sweep_reversion_eurgbp_live_eligible(
            "hull_donchian_fade", "EUR_USD")


class TestRegistrySwap:
    """§3.3-4: DEFER 決定点クローズ → live withdrawal watch へ置換。"""

    def _registry(self):
        p = ROOT / "knowledge-base" / "wiki" / "decisions" / "prereg-trigger-registry.json"
        return {t["id"]: t for t in json.loads(p.read_text())["triggers"]}

    def test_defer_entry_resolved(self):
        assert self._registry()["t8-sweep-defer-decision"]["active"] is False

    def test_withdrawal_watch_active_and_cell_scoped(self):
        w = self._registry()["ps1a-sweep-live-withdrawal-watch"]
        assert w["active"] is True
        assert w["type"] == "live_count_decision"
        assert w["entry_type"] == SWEEP
        assert w["instrument"] == "EUR_GBP"
        assert w["n_decide"] == 10
