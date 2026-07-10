"""FORCE_DEMOTED > PAIR_PROMOTED precedence unification (2026-07-09, rule:R3).

Latent 疑義の解消: シグナル経路の `_is_pair_promoted_live` (fail-closed,
2026-06-12 live-tier-exempt-leak-audit 9b16ebb5) と `_is_promoted_ex`
(旧 docstring「PP がグローバル FD を解除」) で FD∩PP セルの precedence が
逆だった。正準セマンティクスは 2026-04-27 rule:R2 以降「FD 優先 + FD∩PP は
禁止構成 (tier_integrity_check.py check#1 ERROR)」であり、送信直前の
`_apply_force_demoted_final_gate` も PP 例外なしに shadow 強制する。
本テストは (1) FD∩PP=∅ 静的不変量を CI で強制し、(2) 仮に交差が生まれても
`_is_promoted_ex` が FD 先勝ちで fail-closed になることを固定する。
"""

import pytest

from modules.demo_trader import DemoTrader


class _StubOanda:
    def __init__(self, mode="auto"):
        self._mode = mode

    def get_strategy_mode(self, entry_type):
        return self._mode


def _bare_trader():
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = _StubOanda()
    trader._promoted_types = {}
    trader._runtime_pair_demoted = set()
    return trader


def test_force_demoted_and_pair_promoted_are_disjoint():
    """tier_integrity_check.py check#1 と同じ不変量を CI 側でも固定する。

    FD∩PP は 2026-04-27 rule:R2 で禁止構成と決まった (post_news_vol 前例)。
    tier_integrity_check.py は手動運用のため、経路間 precedence 差が実害化
    する唯一の入口 (交差セルの登録) を pytest でも封鎖する。
    """
    pp_strategies = {strat for strat, _ in DemoTrader._PAIR_PROMOTED}
    overlap = pp_strategies & DemoTrader._FORCE_DEMOTED
    assert overlap == set(), (
        f"FORCE_DEMOTED ∩ PAIR_PROMOTED = {overlap} — 禁止構成。"
        "ペア限定復活は FORCE_DEMOTED から戦略を外し、PAIR_PROMOTED + "
        "負けペアの PAIR_DEMOTED 登録で行う (bb_squeeze 2026-04-21 / "
        "donchian 2026-05-27 前例)"
    )


def test_pair_promoted_and_pair_demoted_are_disjoint():
    """tier_integrity_check.py check#8 相当 (同一セルの PP∩PD 矛盾) を CI 固定。"""
    overlap = set(DemoTrader._PAIR_PROMOTED) & set(DemoTrader._PAIR_DEMOTED)
    assert overlap == set(), f"PAIR_PROMOTED ∩ PAIR_DEMOTED = {overlap}"


def test_is_promoted_ex_force_demoted_beats_pair_promoted(monkeypatch):
    """FD∩PP 仮想セルは _is_promoted_ex でも FD 先勝ちで block されること。

    歴史的実例 (post_news_vol×GBP_USD, 2026-04-27 撤回) を再現。シグナル経路
    (_is_live_tier_exempt) / 最終送信 gate / resend gate は既に FD 先勝ちで、
    ここが PP 先勝ちだと「live 資格あり判定 → 送信直前で強制 shadow」の
    経路間矛盾 (audit 誤帰属 + silent 死コード) になる。
    """
    assert "post_news_vol" in DemoTrader._FORCE_DEMOTED
    monkeypatch.setattr(
        DemoTrader,
        "_PAIR_PROMOTED",
        set(DemoTrader._PAIR_PROMOTED) | {("post_news_vol", "GBP_USD")},
    )
    trader = _bare_trader()

    allowed, cause = trader._is_promoted_ex("post_news_vol", "GBP_USD")

    assert allowed is False
    assert cause == "force_demoted"


def test_is_promoted_ex_clean_pair_promoted_cell_stays_live():
    """FD に居ない PAIR_PROMOTED セルは従来どおり live 資格を維持 (回帰ガード)。"""
    assert ("doji_breakout", "GBP_USD") in DemoTrader._PAIR_PROMOTED
    assert "doji_breakout" not in DemoTrader._FORCE_DEMOTED
    trader = _bare_trader()

    allowed, cause = trader._is_promoted_ex("doji_breakout", "GBP_USD")

    assert allowed is True
    assert cause == ""


def test_final_gate_forces_shadow_for_fd_pp_cell(monkeypatch):
    """送信直前 gate は PP 例外なしに FD を shadow 強制する (既存挙動の pin)。

    _is_promoted_ex の precedence をどう並べても、FD∩PP セルが live 送信
    され得ないことの決定層はここ (9b16ebb5 で導入済み)。
    """
    monkeypatch.setattr(
        DemoTrader,
        "_PAIR_PROMOTED",
        set(DemoTrader._PAIR_PROMOTED) | {("post_news_vol", "GBP_USD")},
    )
    trader = DemoTrader.__new__(DemoTrader)
    logs = []
    trader._add_log = logs.append

    is_shadow, is_promoted, shadow_at_open = trader._apply_force_demoted_final_gate(
        entry_type="post_news_vol",
        instrument="GBP_USD",
        is_shadow=False,
        is_promoted=True,
        shadow_at_open=False,
    )

    assert is_shadow is True
    assert is_promoted is False
    assert shadow_at_open is True
    assert any("[FORCE_DEMOTED_GATE]" in msg for msg in logs)
