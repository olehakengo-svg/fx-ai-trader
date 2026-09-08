"""M1 KPI readout (clean live 30d PnL) の estimand と読み手配線を pin する。

pin の書き方は「性質」であって「構文」ではない
(lesson: project_freshness_ui_ssot_pin_property_2026_08_29)。
- estimand の各条件は **その条件を外すと数値が変わる** ことで pin する
- 読み手の配線は **呼ばれているか** まで pin する
  (lesson: project_engine_tick_liveness_2026_08_28 — 検知器も write-only になりうる)
"""
from __future__ import annotations

import ast
import inspect
from datetime import datetime
from pathlib import Path

import pytest

from tools import m1_clean_live_monitor as m1

ANCHOR = datetime(2026, 9, 4, 0, 0, 0)


def row(
    days_ago: float,
    pnl: float,
    *,
    trade_id: str | None = None,
    oanda_trade_id: str = "oanda-1",
    instrument: str = "USD_JPY",
    status: str = "CLOSED",
    dedup_violation: int = 0,
    is_shadow: int = 0,
    entry_type: str = "demo_strategy",
    direction: str = "BUY",
) -> dict:
    ts = ANCHOR - __import__("datetime").timedelta(days=days_ago)
    return {
        "trade_id": trade_id or f"t{days_ago}-{pnl}",
        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "pnl_pips": pnl,
        "oanda_trade_id": oanda_trade_id,
        "instrument": instrument,
        "status": status,
        "dedup_violation": dedup_violation,
        "is_shadow": is_shadow,
        "entry_type": entry_type,
        "direction": direction,
    }


# --------------------------------------------------------------------------
# estimand: 各条件が実際に効いていること (外すと数字が動く = 性質での pin)
# --------------------------------------------------------------------------

def test_live_is_oanda_trade_id_not_is_shadow():
    """LIVE 判定は oanda_trade_id。is_shadow=0 単独では LIVE にしない。

    FLAG_DRIFT 行 (is_shadow=0 かつ oanda_trade_id 空) を数えると
    live_fill_stagnation と同型の estimand 混同になる。
    """
    flag_drift = row(1, 999.0, oanda_trade_id="", is_shadow=0)
    real_live = row(1, 5.0, oanda_trade_id="abc", is_shadow=0)
    assert m1.is_clean_live(flag_drift) is False
    assert m1.is_clean_live(real_live) is True
    out = m1.summarize([flag_drift, real_live], ANCHOR)
    assert out["n"] == 1
    assert out["sum_pips"] == 5.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"instrument": "XAU_USD"},
        {"dedup_violation": 1},
        {"status": "OPEN"},
    ],
)
def test_excluded_rows_do_not_enter_the_window(kwargs):
    keeper = row(1, 10.0, trade_id="keep")
    dropped = row(1, 500.0, trade_id="drop", **kwargs)
    out = m1.summarize([keeper, dropped], ANCHOR)
    assert out["n"] == 1, f"{kwargs} が除外されていない"
    assert out["sum_pips"] == 10.0


def test_missing_pnl_is_excluded():
    r = row(1, 0.0)
    r["pnl_pips"] = None
    assert m1.is_clean_live(r) is False


def test_unparseable_timestamp_is_dropped_not_counted_as_now():
    """壊れた created_at を「今」として扱うと窓が汚染される。"""
    bad = row(1, 100.0, trade_id="bad")
    bad["created_at"] = "not-a-timestamp"
    out = m1.summarize([bad, row(1, 3.0)], ANCHOR)
    assert out["n"] == 1
    assert out["sum_pips"] == 3.0


def test_window_boundary_is_exactly_days():
    """窓幅は実時間 30 日。境界の内外で行が入れ替わること。"""
    inside = row(29.9, 1.0, trade_id="in")
    outside = row(30.1, 1000.0, trade_id="out")
    future = row(-1, 1000.0, trade_id="future")
    out = m1.summarize([inside, outside, future], ANCHOR)
    assert out["n"] == 1
    assert out["sum_pips"] == 1.0


# --------------------------------------------------------------------------
# verdict: 3 状態が実際に切り替わること
# --------------------------------------------------------------------------

def test_verdict_no_data_and_not_met():
    assert m1.summarize([], ANCHOR)["verdict"] == "NO_DATA"
    losers = [row(i, -5.0, trade_id=f"l{i}") for i in range(1, 10)]
    assert m1.summarize(losers, ANCHOR)["verdict"] == "NOT_MET"


def test_small_positive_window_is_underpowered_not_met():
    """正の符号でも N が薄く分散が大きければ MET を名乗らない。

    2026-09-04 の実データ形状 (N=15, 大勝ち 2 + 大負け 1) の縮約。
    """
    pnls = [63.7, 38.2, 29.0, 20.1, 3.0, 0.8, 0.7, 0.0,
            -4.9, -4.9, -11.6, -11.7, -11.8, -13.3, -77.5]
    rows = [row(1 + i * 0.5, p, trade_id=f"r{i}") for i, p in enumerate(pnls)]
    out = m1.summarize(rows, ANCHOR)
    assert out["sum_pips"] > 0
    assert out["verdict"] == "MET_UNDERPOWERED"
    assert out["p_le_zero"] > m1.SIGN_ALPHA
    # 1 件抜くだけで符号が消える約定が存在する = 脆弱
    assert out["fragility"]["n_sign_flipping_trades"] >= 1


def test_verdict_met_requires_resolved_sign():
    """一貫して勝っていて分散が小さければ MET に到達できる (到達不能な状態ではない)。"""
    rows = [row(1 + i * 0.2, 8.0 + (i % 3), trade_id=f"w{i}") for i in range(40)]
    out = m1.summarize(rows, ANCHOR)
    assert out["verdict"] == "MET"
    assert out["p_le_zero"] < m1.SIGN_ALPHA


def test_bootstrap_is_deterministic():
    """同じ入力で CI が動かないこと (日次レポートが毎回ぶれると読めない)。"""
    rows = [row(1 + i * 0.3, (-1) ** i * (5 + i), trade_id=f"b{i}") for i in range(12)]
    a = m1.summarize(rows, ANCHOR)
    b = m1.summarize(rows, ANCHOR)
    assert (a["ci95_lo"], a["ci95_hi"], a["p_le_zero"]) == (b["ci95_lo"], b["ci95_hi"], b["p_le_zero"])


# --------------------------------------------------------------------------
# 符号反転の帰属 — 本 PR の中核 (rolling 窓は成果ゼロでも符号が反転する)
# --------------------------------------------------------------------------

def test_mechanical_flip_detected_when_old_loss_ages_out():
    """新規約定ゼロのまま古い大負けが窓外へ抜けた場合を MECHANICAL_FLIP にする。

    2026-09-04 実例の縮約: 2026-07-31 の −123.2p が抜けただけで符号が反転した。
    """
    rows = [
        row(31.0, -123.2, trade_id="old_loss"),   # 7 日前の窓には居た / 今は窓外
        row(20.0, 10.0, trade_id="a"),
        row(15.0, 15.0, trade_id="b"),
    ]
    out = m1.summarize(rows, ANCHOR, lookback=7)
    fa = out["flip_attribution"]
    assert out["sum_pips"] > 0
    assert fa["sign_flipped"] is True
    assert fa["mechanical_flip"] is True
    assert fa["n_added"] == 0
    assert fa["n_aged_out"] == 1
    assert fa["aged_out_detail"][0]["pnl_pips"] == -123.2
    assert "MECHANICAL_FLIP" in m1.to_markdown(out)


def test_genuine_flip_is_not_labelled_mechanical():
    """新規の勝ちで符号が反転した場合は MECHANICAL_FLIP にしない。"""
    rows = [
        row(20.0, -30.0, trade_id="old_loss_still_in_window"),
        row(1.0, 90.0, trade_id="new_win"),
    ]
    out = m1.summarize(rows, ANCHOR, lookback=7)
    fa = out["flip_attribution"]
    assert fa["sign_flipped"] is True
    assert fa["mechanical_flip"] is False
    assert "MECHANICAL_FLIP" not in m1.to_markdown(out)


# --------------------------------------------------------------------------
# 読み手の配線 — 「書いたが呼ばれない」を防ぐ
# --------------------------------------------------------------------------

def test_quant_gate_status_calls_the_m1_readout():
    """日次 Tier A レポートが M1 を実際に呼んでいること (構造 pin)。

    値の一致ではなく「build_report が m1 の読み出しを呼ぶ」構造を pin する。
    """
    from tools import quant_gate_status as qgs

    assert qgs.m1 is m1, "quant_gate_status が別の m1 実装を掴んでいる"
    tree = ast.parse(inspect.getsource(qgs.build_report))
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "run_m1_readout" in called, "build_report が M1 読み出しを呼んでいない"

    src = inspect.getsource(qgs.run_m1_readout)
    assert "m1.build_report" in src, "run_m1_readout が m1 を呼んでいない"


def test_m1_section_is_emitted_before_other_sections():
    """Discord は 1900 字で切られる。M1 が末尾だと届かない。"""
    from tools import quant_gate_status as qgs
    from tools.alpha_budget_tracker import _empty_state

    report = {
        "generated_at": "2026-09-04T00:00:00+00:00",
        "m1_readout": m1.summarize([row(1, 5.0)], ANCHOR),
        "quant_readiness": "readiness-body",
        "alpha_budget": _empty_state("2026-09"),
        "candidate_queue_7d": {"total": 0, "pass": 0, "shadow_only": 0, "recent_names": []},
        "prereg_trigger_watch": "watch-body",
    }
    md = qgs.to_markdown(report)
    assert "## M1 KPI" in md
    assert md.index("## M1 KPI") < md.index("## Readiness")
    assert md.index("## M1 KPI") < md.index("watch-body")


def test_m1_readout_failure_does_not_break_daily_report():
    """M1 の取得失敗で日次レポート全体を落とさない。"""
    from tools import quant_gate_status as qgs
    from tools.alpha_budget_tracker import _empty_state

    md = qgs.to_markdown({
        "generated_at": "2026-09-04T00:00:00+00:00",
        "m1_readout": {"error": "RequestException: boom"},
        "quant_readiness": "r",
        "alpha_budget": _empty_state("2026-09"),
        "candidate_queue_7d": {"total": 0, "pass": 0, "shadow_only": 0, "recent_names": []},
        "prereg_trigger_watch": "w",
    })
    assert "読み出し失敗" in md
    assert "## Readiness" in md


def test_module_import_has_no_side_effects():
    """tools/*.py はライブラリでもある — import 時に副作用を持たせない。"""
    src = Path(m1.__file__).read_text()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            pytest.fail(f"module-level call at line {node.lineno}")
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                fn = node.value.func
                name = getattr(fn, "id", getattr(fn, "attr", ""))
                assert name in {"frozenset", "set", "dict", "tuple"}, (
                    f"module-level call {name} at line {node.lineno}"
                )


# --------------------------------------------------------------------------
# 監視器の故障を「異常なし」と折り畳まない — 2026-09-08
# --------------------------------------------------------------------------

def test_prereg_watch_crash_is_reported_as_failure_not_content(monkeypatch):
    """subprocess の exit code を無視すると traceback が本文として流れる。

    2026-09-08 実発生: registry の 1 エントリ欠損で prereg_trigger_watch が
    KeyError 落ちし、stderr の traceback が daily Discord にそのまま本文として
    載っていた (2 日間、51 エントリ全て未監視)。読み手にとって「監視器が
    落ちた」と「監視器が異常なしと言った」が同じに見えていた。
    """
    import subprocess

    from tools import quant_gate_status as qgs

    class _R:
        returncode = 1
        stdout = ""
        stderr = 'Traceback (most recent call last):\nKeyError: \'requirements\''

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
    out = qgs.run_prereg_trigger_watch()
    assert "🔴" in out and "exit 1" in out
    assert "未監視" in out
    assert "KeyError" in out, "原因が読み手に届いていない"


def test_prereg_watch_success_returns_plain_body(monkeypatch):
    import subprocess

    from tools import quant_gate_status as qgs

    class _R:
        returncode = 0
        stdout = "## Pre-reg Trigger Watch\n- ok"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
    out = qgs.run_prereg_trigger_watch()
    assert out.startswith("## Pre-reg Trigger Watch")
    assert "🔴" not in out


def test_partial_eval_error_keeps_the_healthy_trigger_results(monkeypatch):
    """exit 2 = 一部エントリのみ EVAL_ERROR。本文を捨てると盲点が再現する。

    PR #227 Codex P1: 壊れた 1 件が他エントリの TRIGGERED を隠すなら、
    隔離ラッパが防ぐはずのものをこの層で作り直してしまう。
    """
    import subprocess

    from tools import quant_gate_status as qgs

    class _R:
        returncode = 2
        stdout = ("## Pre-reg Trigger Watch\n"
                  "### 🔴 TRIGGERED — 執行/判定期日\n"
                  "- **t5-jpy-cap-restore-price**: D1 close=153.7 < 159.50\n"
                  "### 🔴 EVAL ERROR\n- **broken**: KeyError")
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
    out = qgs.run_prereg_trigger_watch()
    assert "t5-jpy-cap-restore-price" in out, "健全な TRIGGERED が消えている"
    assert "EVAL ERROR" in out
    assert "exit 2" in out
    assert "全 trigger 未監視" not in out, "部分故障を全滅と誤って名乗っている"


def test_watcher_failure_appears_before_the_discord_cutoff(monkeypatch):
    """Discord は 1900 字で切られ watch 節は最後尾 — 故障が届かない。

    PR #227 Codex P1: 「本文には出ているが読み手には届かない」= 本 PR が
    直している 2 日間 blind と同型。故障の 1 行は M1 直後へ引き上げる。
    """
    from tools import quant_gate_status as qgs
    from tools.alpha_budget_tracker import _empty_state

    watch = (f"{qgs.WATCH_ALERT_MARK} **監視器が exit 2 — 一部 trigger が評価不能**\n"
             "## Pre-reg Trigger Watch\n" + ("- filler\n" * 400))
    md = qgs.to_markdown({
        "generated_at": "2026-09-08T00:00:00+00:00",
        "m1_readout": m1.summarize([row(1, 5.0)], ANCHOR),
        "quant_readiness": "readiness-body\n" * 100,
        "alpha_budget": _empty_state("2026-09"),
        "candidate_queue_7d": {"total": 0, "pass": 0, "shadow_only": 0,
                               "recent_names": []},
        "prereg_trigger_watch": watch,
    })
    assert qgs.WATCH_ALERT_MARK in md[:1900], (
        "監視器故障が 1900 字カットの外側にあり Discord に届かない")
    assert md.index(qgs.WATCH_ALERT_MARK) < md.index("## Readiness")


def test_no_alert_line_when_the_watcher_is_healthy():
    from tools import quant_gate_status as qgs
    assert qgs.extract_watch_alert("## Pre-reg Trigger Watch\n- 👁 watching") == ""


def test_watcher_alert_precedes_the_unbounded_m1_section():
    """M1 節はセル数に比例して伸びる — その後ろだと押し出される。

    PR #227 Codex P1 7 巡目: 「読み手に届く位置」は絶対位置ではなく
    相対順序で決まる。故障 banner は M1 より前。
    """
    from tools import quant_gate_status as qgs
    from tools.alpha_budget_tracker import _empty_state

    rows = [row(i, 1.0) for i in range(1, 400)]
    md = qgs.to_markdown({
        "generated_at": "2026-09-08T00:00:00+00:00",
        "m1_readout": m1.summarize(rows, ANCHOR),
        "quant_readiness": "readiness-body",
        "alpha_budget": _empty_state("2026-09"),
        "candidate_queue_7d": {"total": 0, "pass": 0, "shadow_only": 0,
                               "recent_names": []},
        "prereg_trigger_watch": f"{qgs.WATCH_ALERT_MARK} **監視器が exit 2**\nbody",
    })
    assert md.index(qgs.WATCH_ALERT_MARK) < md.index("M1"), "M1 より後ろにある"
    assert qgs.WATCH_ALERT_MARK in md[:1900]
