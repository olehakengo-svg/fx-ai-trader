"""P-V3/P-V4: _PAIR_SESSION_FILTER の pre-reg LOCK を全 live 経路で強制 + 観測性。

背景 (2026-07-02 zero-fire 診断 §2.1/§2.5):
    session filter は _PAIR_PROMOTED 分岐内でのみ評価され、bridge mode を
    手動で "live"/"sentinel" にすると filter より前に return True して
    pre-reg LOCK (vix Overlap-only) が黙って外れる構造だった。
    また窓外 shadow 化の audit は "shadow_tracking" 一律で、05-29 15:02 の
    Overlap 窓内 shadow の原因が事後特定不能だった。

仕様:
    - 新 method _promotion_allows_live(entry_type, instrument):
      _PAIR_SESSION_FILTER 登録なし → True / 登録あり → 現 UTC session が
      許可窓内のときだけ True。module-level datetime を読む (fixture 互換)。
    - _is_promoted: mode live/sentinel の手動昇格でも session filter を尊重。
      filter 未登録戦略の手動昇格は従来どおり無条件 True。
    - audit: session filter が live をブロックした trade の block_reason は
      "shadow_tracking(session_filter_out)" ("(" 切り詰め規約で prefix 互換)。
    - _block_counts: "{mode}:session_filter_live_block" を増分。
    - drift guard (tools/tier1_shadow_tracking_drift_guard.py) は enrich 済み
      reason も shadow_tracking 系として扱う (startswith)。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import modules.demo_trader as demo_trader_mod
from modules.demo_trader import DemoTrader
from edge_cell_test_helpers import fixed_datetime, make_trader, edge_cfg

VIX = "vix_carry_unwind"
INST = "USD_JPY"

# _SESSION_BOUNDS_UTC: Asia 0-7 / London 7-12 / Overlap 12-16 / NY 16-24
HOUR_IN = 13    # Overlap
HOUR_OUT = 8    # London


@pytest.fixture(autouse=True)
def _synthetic_vix_overlap_membership(monkeypatch):
    """2026-08-03 (rule:R2): vix Overlap pilot は本番 demote 済み
    (decisions/vix-pilot-early-demote-2026-08-03.md)。本 module が検証する
    session-filter *機構* はメンバーシップ非依存なので、合成の
    promoted+filtered vix セルを class attr に pin して機構カバレッジを
    本番 tier 変更から絶縁する (demote 自体の pin は
    tests/test_vix_pilot_demote_pin.py)。"""
    cell = (VIX, INST)
    monkeypatch.setattr(
        DemoTrader, "_PAIR_PROMOTED",
        frozenset(set(DemoTrader._PAIR_PROMOTED) | {cell}))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_DEMOTED",
        frozenset(t for t in DemoTrader._PAIR_DEMOTED if t != cell))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_SESSION_FILTER",
        {**DemoTrader._PAIR_SESSION_FILTER, cell: {"Overlap"}})


class _OandaModeStub:
    def __init__(self, mode=""):
        self._mode = mode

    def get_strategy_mode(self, _entry_type):
        return self._mode


def _minimal_trader(mode=""):
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = _OandaModeStub(mode)
    trader._promoted_types = {}
    trader._runtime_pair_demoted = set()
    return trader


@pytest.fixture
def clock(monkeypatch):
    def _set(hour):
        monkeypatch.setattr(demo_trader_mod, "datetime", fixed_datetime(hour))
    return _set


class TestPromotionAllowsLive:
    """新 method の単体仕様 (pre-reg 文書の呼称をそのまま実装)。"""

    def test_no_filter_entry_is_always_allowed(self, clock):
        clock(HOUR_OUT)
        trader = _minimal_trader()
        assert trader._promotion_allows_live("trendline_sweep", "EUR_USD") is True

    def test_filtered_entry_inside_window(self, clock):
        clock(HOUR_IN)
        trader = _minimal_trader()
        assert trader._promotion_allows_live(VIX, INST) is True

    def test_filtered_entry_outside_window(self, clock):
        clock(HOUR_OUT)
        trader = _minimal_trader()
        assert trader._promotion_allows_live(VIX, INST) is False


class TestIsPromotedRespectsSessionFilterUnderManualMode:
    """P-V3 本体: mode=live/sentinel の早期 return が LOCK を外さない。"""

    @pytest.mark.parametrize("mode", ["live", "sentinel"])
    def test_manual_mode_outside_window_is_blocked(self, clock, mode):
        clock(HOUR_OUT)
        trader = _minimal_trader(mode)
        assert trader._is_promoted(VIX, INST) is False

    @pytest.mark.parametrize("mode", ["live", "sentinel"])
    def test_manual_mode_inside_window_is_allowed(self, clock, mode):
        clock(HOUR_IN)
        trader = _minimal_trader(mode)
        assert trader._is_promoted(VIX, INST) is True

    def test_manual_mode_without_filter_keeps_unconditional_override(self, clock):
        # filter 未登録戦略の手動昇格 (全降格上書き) は従来挙動を維持
        clock(HOUR_OUT)
        trader = _minimal_trader("live")
        assert trader._is_promoted("trendline_sweep", "EUR_USD") is True

    def test_auto_mode_behavior_pin(self, clock):
        # 既存挙動の pin: auto は _PAIR_PROMOTED 分岐で filter 評価
        trader = _minimal_trader("auto")
        clock(HOUR_IN)
        assert trader._is_promoted(VIX, INST) is True
        clock(HOUR_OUT)
        assert trader._is_promoted(VIX, INST) is False


class TestIsPromotedExCauseAttribution:
    """P-V4 誤帰属防止: cause タグは deciding factor のみを指す。"""

    def test_session_filter_is_the_cause_outside_window(self, clock):
        clock(HOUR_OUT)
        trader = _minimal_trader("auto")
        allowed, cause = trader._is_promoted_ex(VIX, INST)
        assert allowed is False
        assert cause == "session_filter"

    def test_runtime_pair_demote_is_not_misattributed(self, clock):
        # watchdog runtime demote + 窓外 → cause は pair_demoted であって
        # session_filter ではない (audit 誤帰属で「窓さえ来れば発火する」と
        # 誤読させない)
        clock(HOUR_OUT)
        trader = _minimal_trader("auto")
        trader._runtime_pair_demoted = {(VIX, INST)}
        allowed, cause = trader._is_promoted_ex(VIX, INST)
        assert allowed is False
        assert cause == "pair_demoted"

    def test_mode_off_is_not_misattributed(self, clock):
        clock(HOUR_OUT)
        trader = _minimal_trader("off")
        allowed, cause = trader._is_promoted_ex(VIX, INST)
        assert allowed is False
        assert cause == "mode_off"

    def test_allowed_has_empty_cause(self, clock):
        clock(HOUR_IN)
        trader = _minimal_trader("auto")
        allowed, cause = trader._is_promoted_ex(VIX, INST)
        assert allowed is True
        assert cause == ""


def _vix_sell_sig(entry: float = 161.0):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": VIX,
        "confidence": 70,
        "score": 5.0,
        "sl": entry + 0.30,
        "tp": entry - 0.60,
        "atr": 0.15,
        "reasons": ["✅ VCU test signal"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _usdjpy_cfg():
    cfg = edge_cfg()
    cfg["symbol"] = "USDJPY=X"
    return cfg


class TestTickEntryObservability:
    """P-V4: 窓外 shadow 化が audit/block_counts から事後特定可能。"""

    @pytest.fixture(autouse=True)
    def _repin_demo_trader(self, monkeypatch):
        # tools/scalp_re_enable_bt.py (他テストが lazy import) は module body で
        # demo_trader.DemoTrader を stub に恒久置換する。make_trader は call 時
        # に再 import するため、full-suite 実行順によっては stub を掴む。
        # 本 module top-level import で捕まえた実クラスへ再ピンして絶縁する。
        monkeypatch.setattr(demo_trader_mod, "DemoTrader", DemoTrader)

    def test_outside_window_audit_reason_and_counter(self, tmp_path, monkeypatch):
        trader, logs = make_trader(tmp_path, monkeypatch, hour=HOUR_OUT)
        audits = []
        trader._add_oanda_audit = lambda **kw: audits.append(kw)

        trader._tick_entry("daytrade", _usdjpy_cfg(), _vix_sell_sig(), "15m", INST)

        assert audits, "audit row must be written for the skipped OANDA send"
        row = audits[-1]
        assert row["is_live"] is False
        assert row["block_reason"] == "shadow_tracking(session_filter_out)"
        assert trader._block_counts.get("daytrade:session_filter_live_downgrade") == 1
        assert (
            trader._block_counts_per_strategy.get(
                f"{VIX}:session_filter_live_downgrade") == 1
        )

    def test_inside_window_no_session_filter_attribution(self, tmp_path, monkeypatch):
        # 窓内で shadow になった場合 (別因) に session_filter_out を誤付与しない
        trader, logs = make_trader(tmp_path, monkeypatch, hour=HOUR_IN)
        audits = []
        trader._add_oanda_audit = lambda **kw: audits.append(kw)
        # 別因 shadow を強制: bridge inactive で live 送信不可でも
        # session filter 起因ではない
        trader._oanda.active = False

        trader._tick_entry("daytrade", _usdjpy_cfg(), _vix_sell_sig(), "15m", INST)

        assert audits, "audit row must be written even when shadowed for other cause"
        for row in audits:
            assert row.get("block_reason") != "shadow_tracking(session_filter_out)"
        assert "daytrade:session_filter_live_downgrade" not in getattr(
            trader, "_block_counts", {})


class TestDriftGuardAcceptsEnrichedReason:
    """P-V4 派生: drift guard が enrich 済み reason を shadow 系として扱う。"""

    def test_enriched_reason_still_counts_as_drift_candidate(self):
        from tools.tier1_shadow_tracking_drift_guard import is_drift_row_for_replay
        audit_row = {
            "bridge_status": "skipped",
            "block_reason": "shadow_tracking(session_filter_out)",
        }
        live_trade_row = {"is_shadow": 0, "oanda_trade_id": "999999"}
        assert is_drift_row_for_replay(audit_row, live_trade_row) is True

    def test_plain_reason_unchanged(self):
        from tools.tier1_shadow_tracking_drift_guard import is_drift_row_for_replay
        audit_row = {"bridge_status": "skipped", "block_reason": "shadow_tracking"}
        live_trade_row = {"is_shadow": 0, "oanda_trade_id": "999999"}
        assert is_drift_row_for_replay(audit_row, live_trade_row) is True
