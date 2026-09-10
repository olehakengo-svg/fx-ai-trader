"""D クラス estimand 監査の pin。

背景: `tools/live_roster_attrition.py` の旧 `D_NEVER_PROMOTED` は
「**現在**の昇格集合に不在」を根拠に「当時も未昇格 = 本来出てはいけなかった
発火」と主張していた (PR #226 Codex P1 finding #2、未読マージ)。
2026-09-10 の監査で 15 セル中 14 セル (26/28 約定) が当時の設計どおり
LIVE 可と判明し、旧解釈は棄却された。

pin は**性質**で書く (構文 pin は両方向に誤る — lesson 2026-08-29/09-02):
  (a) 2 モジュールの tier gate 定数が一致する
  (b) gate 前の約定は「降格集合に載っていなければ」LEGIT
  (c) gate 前でも降格集合に載っていれば ILLEGIT (逆方向も効く)
  (d) 「コードが読めない」と「降格機構が存在しない」を折り畳まない
  (e) D の subclass が約定時刻で分かれ、gate 後を含むセルは要説明側へ
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

import live_roster_attrition as lra  # noqa: E402
import roster_d_class_estimand_audit as aud  # noqa: E402


def test_tier_gate_constant_is_the_same_in_both_modules():
    """値を import せず複製しているので一致を pin する (SSOT の代替)。"""
    assert lra.TIER_GATE_UTC == aud.TIER_GATE_UTC


def test_tier_gate_is_anchored_to_a_real_commit_that_introduced_the_gate():
    """定数が実在の commit を指し、その commit で gate が導入されていること。

    日付だけを pin すると「なぜその日か」が失われ、後から誰も検証できない。
    """
    src = aud._git("show", f"{aud.TIER_GATE_COMMIT}:modules/demo_trader.py")
    assert src is not None, "tier gate commit が repo に無い"
    assert "_SHADOW_MODE" in src and "_ELITE_LIVE" in src
    parent = aud._git("rev-parse", f"{aud.TIER_GATE_COMMIT}^")
    assert parent is not None
    before = aud._git("show", f"{parent.strip()}:modules/demo_trader.py")
    assert before is not None
    assert "_ELITE_LIVE" not in before, "親 commit に既に gate がある = 定数が誤り"


_HIST = [(datetime(2026, 4, 1, tzinfo=timezone.utc), "c_nomech"),
         (datetime(2026, 4, 10, tzinfo=timezone.utc), "c_sets"),
         (datetime(2026, 5, 1, tzinfo=timezone.utc), "c_post")]


def _cache(**kw):
    return {"c_nomech": {},
            "c_sets": {"_FORCE_DEMOTED": {"demoted_type"},
                       "_PAIR_DEMOTED": {("pair_type", "EUR_USD")}},
            "c_post": {"_FORCE_DEMOTED": set(), "_PAIR_DEMOTED": set()},
            **kw}


def test_pre_gate_fire_not_in_demote_sets_is_legit():
    res = aud.audit_fire(datetime(2026, 4, 12, tzinfo=timezone.utc),
                         "anything", "USD_JPY", _HIST, _cache())
    assert res["verdict"] == aud.LEGIT


def test_pre_gate_fire_that_was_demoted_is_illegitimate():
    """逆方向 — gate 前でも降格集合に載っていれば違反。"""
    res = aud.audit_fire(datetime(2026, 4, 12, tzinfo=timezone.utc),
                         "demoted_type", "USD_JPY", _HIST, _cache())
    assert res["verdict"] == aud.ILLEGIT
    pair = aud.audit_fire(datetime(2026, 4, 12, tzinfo=timezone.utc),
                          "pair_type", "EUR_USD", _HIST, _cache())
    assert pair["verdict"] == aud.ILLEGIT
    # ペア限定降格は他ペアには効かない
    other = aud.audit_fire(datetime(2026, 4, 12, tzinfo=timezone.utc),
                           "pair_type", "USD_JPY", _HIST, _cache())
    assert other["verdict"] == aud.LEGIT


def test_absent_demote_mechanism_is_not_folded_into_unresolved():
    """「降格機構が存在しない時期」と「コードが読めない」を別の箱へ。

    折り畳むと「機構が無かった (= 全送信が設計)」を「調べられなかった」と
    誤読する (2026-08-30 の fetch_json blind と同型)。
    """
    absent = aud.audit_fire(datetime(2026, 4, 5, tzinfo=timezone.utc),
                            "anything", "USD_JPY", _HIST, _cache())
    assert absent["verdict"] == aud.LEGIT_NO_MECH
    unreadable = aud.audit_fire(datetime(2026, 4, 12, tzinfo=timezone.utc),
                                "anything", "USD_JPY", _HIST,
                                _cache(c_sets=None))
    assert unreadable["verdict"] == aud.UNRESOLVED
    assert absent["verdict"] != unreadable["verdict"]


def test_post_gate_fire_needs_further_explanation():
    res = aud.audit_fire(datetime(2026, 5, 2, tzinfo=timezone.utc),
                         "anything", "USD_JPY", _HIST, _cache())
    assert res["verdict"] == aud.POST_GATE


def test_cell_verdict_takes_the_worst_of_its_fires():
    """1 件でも違反があればセルは違反 — 平均で薄めない。"""
    rep = aud.audit({"demoted_type|USD_JPY|BUY": [
        "2026-04-12T00:00:00+00:00", "2026-04-13T00:00:00+00:00"]})
    # 実 git 履歴で走るので verdict の値ではなく「最悪を採る」性質のみ pin
    cell = rep["cells"][0]
    order = {aud.ILLEGIT: 0, aud.POST_GATE: 1, aud.UNRESOLVED: 2,
             aud.LEGIT: 3, aud.LEGIT_NO_MECH: 4}
    worst = min((f["verdict"] for f in cell["per_fire"]),
                key=lambda v: order[v])
    assert cell["cell_verdict"] == worst


def test_real_d_cells_are_overwhelmingly_legitimate():
    """2026-09-10 監査の実結果を回帰として固定する。

    dual_sr_bounce×USD_JPY×BUY だけが `_FORCE_DEMOTED` 在籍中に 2 発火。
    他 14 セルは allow-by-default 期 = 「本来出てはいけなかった発火」ではない。
    """
    rep = aud.audit({
        "dual_sr_bounce|USD_JPY|BUY": ["2026-04-13T16:01:03+00:00",
                                       "2026-04-13T13:01:06+00:00",
                                       "2026-04-07T05:45:37+00:00"],
        "vol_surge_detector|EUR_USD|BUY": ["2026-04-07T16:04:00+00:00"],
        "pivot_breakout|USD_JPY|BUY": ["2026-04-02T14:04:00+00:00"],
    })
    by = {(c["entry_type"], c["instrument"], c["direction"]): c["cell_verdict"]
          for c in rep["cells"]}
    assert by[("dual_sr_bounce", "USD_JPY", "BUY")] == aud.ILLEGIT
    assert by[("vol_surge_detector", "EUR_USD", "BUY")] == aud.LEGIT
    assert by[("pivot_breakout", "USD_JPY", "BUY")] == aud.LEGIT_NO_MECH


# ------------------------------------------------- parent tool's D subclass
def _stops():
    return {"force_demoted": set(), "pair_demoted": set(),
            "pair_promoted": set(), "universal_sentinel": set(),
            "htf_mixed_stop": set(), "shadow_always": set(),
            "shadow_demoted": set(), "shadow_retired": set()}


def _row(when: datetime):
    return {"entry_type": "unpromoted", "instrument": "USD_JPY",
            "direction": "BUY", "oanda_trade_id": "1", "dedup_violation": 0,
            "pnl_pips": 0.0, "created_at": when.isoformat()}


def test_d_subclass_splits_on_the_tier_gate():
    """D は「gate 前だけ」と「gate 後を含む」で別の問いになる。"""
    anchor = (lra.TIER_GATE_UTC + timedelta(days=10)).date().isoformat()
    now = lra.TIER_GATE_UTC + timedelta(days=200)
    pre = lra.build_report([_row(lra.TIER_GATE_UTC - timedelta(hours=1))],
                           anchor=anchor, now=now, stops=_stops())
    assert pre["subcounts"] == {"D1_PRE_TIER_GATE": 1}
    post = lra.build_report([_row(lra.TIER_GATE_UTC - timedelta(hours=1)),
                             _row(lra.TIER_GATE_UTC + timedelta(hours=1))],
                            anchor=anchor, now=now, stops=_stops())
    assert post["subcounts"] == {"D2_POST_TIER_GATE": 1}


def test_class_name_no_longer_claims_never_promoted():
    """旧称は過去形の主張を名前で運んでいた — 復活させないための pin。"""
    assert "D_NEVER_PROMOTED" not in lra.CLASSES
    assert "D_NOT_LIVE_ELIGIBLE_NOW" in lra.CLASSES


def test_demote_sets_at_returns_empty_dict_not_none_when_sets_are_absent():
    """`demote_sets_at` 自身の契約 pin。

    上の `test_absent_demote_mechanism_...` は合成 cache を注入するため
    この関数を迂回する = 関数側の折り畳みを検出できない。契約は関数で pin する:
      - 降格集合が無い時期の commit → `{}` (読めた、けれど集合が無い)
      - 存在しない commit           → `None` (読めなかった)
    """
    # 8a42d776 = "temp: disable OANDA strategy promotion filter" (2026-04-03)
    # この時点の `_is_promoted()` は `return True` で降格集合が存在しない。
    absent = aud.demote_sets_at("8a42d7764")
    assert absent == {}, f"降格集合が無い時期を {absent!r} と報告している"
    assert absent is not None, "None に折り畳むと『機構が無い』が『不明』になる"
    # 現在の HEAD には両集合がある (対照)
    present = aud.demote_sets_at("origin/main")
    assert present and "_FORCE_DEMOTED" in present and "_PAIR_DEMOTED" in present
    # 実在しない commit は None
    assert aud.demote_sets_at("0" * 40) is None
