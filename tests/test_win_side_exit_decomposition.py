"""Pin the shadow exit regime break and the win-side decomposition estimand.

背景: knowledge-base/wiki/analyses/win-side-exit-regime-break-2026-06-03.md
shadow trade の SL 変更は commit ab7a4931 (2026-06-03T07:58Z) まで dead code
だったため、この時刻の前後で shadow の payoff 統計は別 estimand になる。

pin は「性質」で書く (lesson_validity_check_pins_proxy_2026_09_02):
時変の実測値ではなく、(a) 境界定数、(b) SL_HIT ラベル衝突への対処
(close_reason は必ず outcome と組で集計する)、(c) 境界で分割されること、を固定する。
"""
import importlib.util
import json
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "win_side_exit_decomposition.py"


def _load():
    spec = importlib.util.spec_from_file_location("win_side_exit_decomposition", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def wsed():
    return _load()


def test_regime_break_constant_is_the_shadow_sl_persist_deploy(wsed):
    """境界は commit ab7a4931 のデプロイ時刻 (UTC)。動かす場合は analyses ページも更新。"""
    assert wsed.SHADOW_EXIT_REGIME_BREAK == "2026-06-03T07:58"


def test_default_split_is_the_regime_break(wsed):
    """既定の分割点が月境界などの恣意的な値へ戻っていないこと。"""
    assert wsed.SHADOW_EXIT_REGIME_BREAK.startswith("2026-06-03")
    src = _TOOL.read_text()
    assert '"--split-at", default=SHADOW_EXIT_REGIME_BREAK' in src


def _payload(trades):
    return {"count": len(trades), "trades": trades}


def _t(entry, outcome, pnl, reason, **kw):
    d = {
        "entry_type": "s", "instrument": "EUR_JPY", "direction": "BUY",
        "entry_time": entry, "exit_time": entry, "outcome": outcome,
        "pnl_pips": pnl, "close_reason": reason, "dedup_violation": 0,
        "is_shadow": 1, "mafe_favorable_pips": abs(pnl or 0.0), "mafe_adverse_pips": 0.0,
    }
    d.update(kw)
    return d


def test_load_clean_applies_the_declared_filters(wsed, tmp_path):
    """XAU 除外 / dedup_violation=1 除外 / outcome∈{WIN,LOSS} の 3 条件。"""
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-07-01T00:00:00+00:00", "WIN", 3.0, "SL_HIT"),
        _t("2026-07-02T00:00:00+00:00", "WIN", 3.0, "SL_HIT", instrument="XAU_USD"),
        _t("2026-07-03T00:00:00+00:00", "WIN", 3.0, "SL_HIT", dedup_violation=1),
        _t("2026-07-04T00:00:00+00:00", None, None, None),
        _t("2026-07-05T00:00:00+00:00", "BREAKEVEN", 0.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    assert len(rows) == 1, "XAU / dedup / non-WIN,LOSS のいずれかが素通りしている"


def test_close_reason_is_never_aggregated_without_outcome(wsed, tmp_path):
    """SL_HIT は BE/trail 利確を含む混成ラベル。outcome 分割なしの集計は禁止。

    同一 close_reason に WIN と LOSS を混ぜた入力で、WIN 側平均が LOSS に
    汚染されないことを確認する (project_sl_hit_label_collision)。
    """
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-07-01T00:00:00+00:00", "WIN", 4.0, "SL_HIT"),
        _t("2026-07-02T00:00:00+00:00", "LOSS", -20.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    table = wsed.reason_outcome_table(rows, "t")
    assert "| SL_HIT | 1 | 4.00 | 1 | 20.00 |" in table


def test_split_separates_pre_and_post_regime_rows(wsed, tmp_path):
    """境界直前/直後の行が別期間へ落ちること (日付ではなく時刻まで効く)。"""
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-06-03T07:57:00+00:00", "WIN", 20.0, "MAX_HOLD_TIME"),
        _t("2026-06-03T07:59:00+00:00", "WIN", 4.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    brk = wsed.SHADOW_EXIT_REGIME_BREAK
    pre = [r for r in rows if (r["entry_time"] or "") < brk]
    post = [r for r in rows if (r["entry_time"] or "") >= brk]
    assert len(pre) == 1 and len(post) == 1
    assert pre[0]["reason"] == "MAX_HOLD_TIME"
    assert post[0]["reason"] == "SL_HIT"


def test_shift_share_is_reported_as_non_identified_when_groups_are_disjoint(wsed, tmp_path):
    """群が前後で交わらない場合、mix/within の分解は補完値に過ぎない。

    分解自体は走るが、合計が実際の Δavg_win と一致することだけを保証する
    (数字を「群内劣化 100%」と読ませないための健全性チェック)。
    """
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-05-01T00:00:00+00:00", "WIN", 20.0, "MAX_HOLD_TIME"),
        _t("2026-07-01T00:00:00+00:00", "WIN", 4.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    brk = wsed.SHADOW_EXIT_REGIME_BREAK
    a = [r for r in rows if (r["entry_time"] or "") < brk]
    b = [r for r in rows if (r["entry_time"] or "") >= brk]
    _, mix, within = wsed.shift_share(a, b, "reason")
    assert mix + within == pytest.approx(4.0 - 20.0, abs=1e-6)
