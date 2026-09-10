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
    assert src is not None, (
        "tier gate commit が repo から読めない。定数の誤りか、shallow clone "
        "(CI は checkout fetch-depth: 0 が必須 — ci.yml test job) かを区別せよ"
    )
    assert "_SHADOW_MODE" in src and "_ELITE_LIVE" in src
    parent = aud._git("rev-parse", f"{aud.TIER_GATE_COMMIT}^")
    assert parent is not None
    before = aud._git("show", f"{parent.strip()}:modules/demo_trader.py")
    assert before is not None
    assert "_ELITE_LIVE" not in before, "親 commit に既に gate がある = 定数が誤り"


_HIST = [(datetime(2026, 4, 1, tzinfo=timezone.utc), "c_nogate"),
         (datetime(2026, 4, 5, tzinfo=timezone.utc), "c_allsend"),
         (datetime(2026, 4, 10, tzinfo=timezone.utc), "c_allow"),
         (datetime(2026, 4, 12, tzinfo=timezone.utc), "c_deny"),
         (datetime(2026, 5, 1, tzinfo=timezone.utc), "c_post")]

_POLICIES = {
    "c_nogate": (aud.POLICY_NO_GATE, "gate 未実装"),
    "c_allsend": (aud.POLICY_ALL_SEND, "return True 単文"),
    "c_allow": (aud.POLICY_ALLOW_BY_DEFAULT, "末尾 return True"),
    "c_deny": (aud.POLICY_DENY_BY_DEFAULT, "末尾 return False"),
    "c_post": (aud.POLICY_ALLOW_BY_DEFAULT, "末尾 return True"),
}


def _sets(**kw):
    demoted = {"_FORCE_DEMOTED": {"demoted_type"},
               "_PAIR_DEMOTED": {("pair_type", "EUR_USD")}}
    return {"c_nogate": {}, "c_allsend": {},
            "c_allow": dict(demoted), "c_deny": dict(demoted),
            "c_post": {"_FORCE_DEMOTED": set(), "_PAIR_DEMOTED": set()},
            **kw}


def _fire(ts_day, entry_type="anything", instrument="USD_JPY", **kw):
    return aud.audit_fire(datetime(2026, ts_day[0], ts_day[1],
                                   tzinfo=timezone.utc),
                          entry_type, instrument, _HIST,
                          kw.pop("sets", None) or _sets(),
                          dict(_POLICIES), **kw)


def test_no_gate_and_all_send_are_unconditional():
    """ゲート未実装 / 全送信期はランタイム状態に**不感** = 無条件に確定。"""
    assert _fire((4, 2))["verdict"] == aud.PERMITTED_NO_GATE
    assert _fire((4, 6))["verdict"] == aud.PERMITTED_ALL_SEND
    assert aud.UNCONDITIONAL_VERDICTS == frozenset(
        {aud.PERMITTED_NO_GATE, aud.PERMITTED_ALL_SEND})


def test_allow_by_default_verdict_is_conditional_not_unconditional():
    """allow-by-default は既定 return より手前でランタイム状態を見る。

    PR #230 Codex P1: `get_strategy_mode()=="off"` /
    `_promoted_types` の `status=="demoted"` は**ブロック方向**に働くので、
    「LEGIT 側は override に不感」は成り立たない。verdict 名で条件性を運ぶ。
    """
    res = _fire((4, 11))
    assert res["verdict"] == aud.PERMITTED_COND
    assert res["verdict"] not in aud.UNCONDITIONAL_VERDICTS
    assert res["verdict"] in aud.PERMITTED_VERDICTS
    assert "再構成不能" in res["why"] or "条件付き" in res["why"]


def test_deny_by_default_period_is_not_called_permitted():
    """deny-by-default 期の発火を「許可されていた」と言ってはいけない。

    PR #230 Codex P1: 降格集合の不在は「その 2 定数が無かった」しか示さず、
    `_is_promoted()` が True を返したことを示さない。
    """
    res = _fire((4, 13))
    assert res["verdict"] == aud.DENY_UNEXPLAINED
    assert res["verdict"] not in aud.PERMITTED_VERDICTS


def test_static_demote_membership_contradicts_the_fire():
    assert _fire((4, 11), entry_type="demoted_type")["verdict"] == aud.CONTRADICTS
    assert _fire((4, 11), entry_type="pair_type",
                 instrument="EUR_USD")["verdict"] == aud.CONTRADICTS
    # ペア限定降格は他ペアには効かない
    assert _fire((4, 11), entry_type="pair_type",
                 instrument="USD_JPY")["verdict"] == aud.PERMITTED_COND


def test_unresolvable_code_state_is_not_folded_into_permitted():
    res = aud.audit_fire(datetime(2026, 4, 11, tzinfo=timezone.utc),
                         "anything", "USD_JPY", _HIST,
                         _sets(c_allow=None), dict(_POLICIES))
    assert res["verdict"] == aud.UNRESOLVED
    unknown = aud.audit_fire(datetime(2026, 4, 11, tzinfo=timezone.utc),
                             "anything", "USD_JPY", _HIST, _sets(),
                             {**_POLICIES, "c_allow": (aud.POLICY_UNKNOWN, "?")})
    assert unknown["verdict"] == aud.UNRESOLVED


def test_post_gate_fire_needs_further_explanation():
    assert _fire((5, 2))["verdict"] == aud.POST_GATE


def test_promotion_policy_is_read_from_the_function_not_inferred():
    """policy は `_is_promoted()` の実体から読む (降格集合の不在から推論しない)。

    PR #230 Codex P1: 04-02 の発火を「降格集合が無い」だけで
    `LEGIT_NO_DEMOTE_MECHANISM` としていたのは根拠不足だった。
    実 git 履歴で 3 形が判別できることを主張する。
    """
    assert aud.promotion_policy_at("e3d02a0ff")[0] == aud.POLICY_NO_GATE
    assert aud.promotion_policy_at("8a42d7764")[0] == aud.POLICY_ALL_SEND
    assert aud.promotion_policy_at("0" * 40)[0] == aud.POLICY_UNKNOWN
    # 現 HEAD の `_is_promoted` は `_is_promoted_ex(...)["allowed"]` へ委譲する
    # ので既定を静的に決められない → UNKNOWN。これは**保守側**の挙動で、
    # UNKNOWN は許可 verdict ではなく UNRESOLVED に流れる (安全な向き)。
    assert aud.promotion_policy_at("origin/main")[0] == aud.POLICY_UNKNOWN


def test_unknown_policy_routes_to_unresolved_not_permitted():
    """方針が決められないときは許可側に流さない (委譲形 `_is_promoted` 等)。"""
    res = aud.audit_fire(datetime(2026, 4, 11, tzinfo=timezone.utc),
                         "anything", "USD_JPY", _HIST, _sets(),
                         {**_POLICIES, "c_allow": (aud.POLICY_UNKNOWN, "委譲形")})
    assert res["verdict"] == aud.UNRESOLVED
    assert res["verdict"] not in aud.PERMITTED_VERDICTS


def test_cell_verdict_takes_the_worst_of_its_fires():
    """1 件でも重い判定があればセルはそれ — 平均で薄めない。"""
    rep = aud.audit({"demoted_type|USD_JPY|BUY": [
        "2026-04-12T00:00:00+00:00", "2026-04-13T00:00:00+00:00"]})
    cell = rep["cells"][0]
    worst = min((f["verdict"] for f in cell["per_fire"]),
                key=lambda v: aud.VERDICT_SEVERITY[v])
    assert cell["cell_verdict"] == worst


def test_real_d_cells_verdicts_are_pinned():
    """2026-09-10 監査 (PR #230 修正後) の実結果を回帰として固定する。

    `dual_sr_bounce×USD_JPY×BUY` だけが `_FORCE_DEMOTED` 在籍中に 2 発火。
    04-02 は gate 未実装、04-03/04-06 は全送信期 = **無条件**に許可。
    それ以外の allow-by-default 期は**条件付き**。
    """
    rep = aud.audit({
        "dual_sr_bounce|USD_JPY|BUY": ["2026-04-13T16:01:03+00:00",
                                       "2026-04-13T13:01:06+00:00",
                                       "2026-04-07T05:45:37+00:00"],
        "vol_surge_detector|EUR_USD|BUY": ["2026-04-07T16:04:00+00:00"],
        "pivot_breakout|USD_JPY|BUY": ["2026-04-02T14:04:00+00:00"],
        "turtle_soup|GBP_USD|BUY": ["2026-04-06T07:42:00+00:00"],
    })
    by = {(c["entry_type"], c["instrument"], c["direction"]): c["cell_verdict"]
          for c in rep["cells"]}
    assert by[("dual_sr_bounce", "USD_JPY", "BUY")] == aud.CONTRADICTS
    assert by[("vol_surge_detector", "EUR_USD", "BUY")] == aud.PERMITTED_COND
    assert by[("pivot_breakout", "USD_JPY", "BUY")] == aud.PERMITTED_NO_GATE
    assert by[("turtle_soup", "GBP_USD", "BUY")] == aud.PERMITTED_ALL_SEND
    # 無条件に確定した件数が report に出ていること (主張の強さを readout に運ぶ)
    assert rep["unconditional_permitted_fires"] == 2
    assert rep["conditional_permitted_fires"] == 2
    assert rep["contradicting_fires"] == 2
    assert rep["total_fires"] == 6


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


def test_d2_cells_are_not_counted_as_attributed():
    """D2 (要説明) を attributed_share の分子に数えない。

    PR #230 Codex P2: `--anchor` を tier gate 後に動かすと D2 が現れ、
    「定義上要説明」なのに帰属済みとして share を黙って膨らませていた。
    """
    anchor = (lra.TIER_GATE_UTC + timedelta(days=10)).date().isoformat()
    now = lra.TIER_GATE_UTC + timedelta(days=200)
    # D1 のみ → 帰属済み
    d1 = lra.build_report([_row(lra.TIER_GATE_UTC - timedelta(hours=1))],
                          anchor=anchor, now=now, stops=_stops())
    assert d1["subcounts"] == {"D1_PRE_TIER_GATE": 1}
    assert d1["attributed_share"] == 1.0
    # D2 を含む → 未帰属側 (share が 1.0 を下回る)
    d2 = lra.build_report([_row(lra.TIER_GATE_UTC + timedelta(hours=1))],
                          anchor=anchor, now=now, stops=_stops())
    assert d2["subcounts"] == {"D2_POST_TIER_GATE": 1}
    assert d2["attributed_share"] == 0.0, "要説明の D2 を帰属済みに数えている"


def test_unparsable_demotion_assignment_fails_closed(tmp_path, monkeypatch):
    """個別代入の解析失敗を飛ばして「完全に読めた」と扱わない。

    PR #230 Codex P2 2 巡目: `continue` で飛ばすと、部分的にしか読めていない
    降格集合を完全とみなし、在籍していたセルを PERMITTED 側へ落とす。
    """
    src = ("class D:\n"
           "    _FORCE_DEMOTED = {'a'}\n"
           "    _PAIR_DEMOTED = {(x, 'EUR_USD') for x in names}\n")

    def fake_git(*args):
        return src if args[0] == "show" else None

    monkeypatch.setattr(aud, "_git", fake_git)
    assert aud.demote_sets_at("deadbeef") is None, "部分解析を完全扱いしている"


def test_withdrawn_26_of_28_claim_is_not_in_any_readout():
    """撤回した主張が readout に残っていないこと (PR #230 Codex P2 2 巡目)。

    引用可否は KB に書いても、**ツールの docstring が readout の一部**なので
    そこに残っていれば毎回再生産される。
    """
    import pathlib
    for name in ("live_roster_attrition.py", "roster_d_class_estimand_audit.py"):
        text = (REPO / "tools" / name).read_text(encoding="utf-8")
        # 撤回済みの主張形 (「26/28 は正当/LIVE 可」) が肯定形で残っていないか
        for bad in ("26/28 約定) は当時の設計どおり", "26 / 28 は正当"):
            assert bad not in text, f"{name} に撤回済みの主張が残っている: {bad}"
        if "26/28" in text:
            assert "撤回" in text, f"{name}: 26/28 に触れるなら撤回を明記せよ"
