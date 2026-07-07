"""2026-07-07 v2.3 WS1 T1 (rule:R2): wick_imbalance_reversion × GBP_USD demote pin.

30d clean live N=12 WR=41.7% EV=-3.91 -46.9pip (Wilson_lo 19.3% < BEV 37.9%)。
昇格根拠 365d BT (N=40 WR=70.0% EV=+0.123 PF=1.44) を live が反証。
live 発火は全期間 100% BUY のため pair 粒度 demote = BUY セル閉鎖と等価。
詳細: knowledge-base/wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md §7

再昇格は R1 (365d BT + Bonferroni + Pre-reg LOCK) のみ — このテストの変更を伴う
PR がその執行点になる。
"""

from modules.demo_trader import DemoTrader

CELL = ("wick_imbalance_reversion", "GBP_USD")


def test_wick_gbpusd_removed_from_pair_promoted():
    assert CELL not in DemoTrader._PAIR_PROMOTED, (
        "wick_imbalance_reversion×GBP_USD は 2026-07-07 R2 demote 済み。"
        "再昇格は R1 手続き (analyses/payoff-asymmetry-diagnosis-2026-07-07.md) を経ること"
    )


def test_wick_gbpusd_in_pair_demoted():
    assert CELL in DemoTrader._PAIR_DEMOTED, (
        "demote は _PAIR_PROMOTED 除去 + _PAIR_DEMOTED 追加の両輪 (write-path shadow 強制)"
    )


def test_wick_gbpusd_resolves_pair_demoted_tier():
    trader = DemoTrader.__new__(DemoTrader)
    assert trader._resolve_tier("wick_imbalance_reversion", "GBP_USD") == "PAIR_DEMOTED"
