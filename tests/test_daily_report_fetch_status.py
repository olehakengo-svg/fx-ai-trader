"""daily_report — API 取得失敗は「unreachable, cause unknown」としてのみ報告する (rule:R3, 2026-09-22).

2026-09-22 03:11Z の pre_tokyo レポートは、本番 HTTP が全盲 (プロセスは生存) の
最中に生成され、LLM が「Render 無料 tier 特有のスリープ」という**存在しない原因**
を書いた (本サービスは Pro plan、スリープしない)。生成器の欠陥は 2 つ:

  1. ``fetch_json`` が失敗を ``{}`` に潰し、「取れなかった」と「空だった」も
     「なぜ取れなかったか (失敗クラス)」も LLM に渡っていなかった
  2. 原因を推測するなという規則がプロンプトに無く、出力の後検査も無かった

固定する性質:
  A. fetch 結果は ok / payload / error_class / error を分離して持つ
  B. 取得状況テーブルは失敗を「unreachable, cause unknown (class)」と書き、
     原因の断定語を含まない
  C. LLM 出力に原因の捏造語が含まれたら、生成器が脚注で明示的に訂正する
     (黙って書き換えない / 黙って通さない)
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from modules import freshness_policy as fp

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "daily_report_under_test", ROOT / "scripts" / "daily_report.py"
)
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)


def test_fetch_outcome_separates_failure_from_empty(monkeypatch):
    import socket

    def boom(*a, **kw):
        raise socket.timeout("timed out")

    monkeypatch.setattr(dr.urllib.request, "urlopen", boom)
    out = dr.fetch_outcome("https://example.invalid/api/demo/status")
    assert out.ok is False and out.payload == {}
    assert out.error_class == fp.FAIL_TIMEOUT
    assert "timed out" in out.error


def test_fetch_json_stays_backward_compatible(monkeypatch):
    """既存呼び出し (payload dict を期待) を壊さない。"""
    monkeypatch.setattr(dr, "fetch_outcome",
                        lambda url, timeout=15: dr.FetchResult(url, False, {}, fp.FAIL_TIMEOUT, "x"))
    assert dr.fetch_json("u") == {}


def test_fetch_status_table_reports_unknown_cause_only():
    results = {
        "status": dr.FetchResult("u1", False, {}, fp.FAIL_TIMEOUT, "timeout: timed out"),
        "trades": dr.FetchResult("u2", False, {}, fp.FAIL_TIMEOUT, "timeout: timed out"),
        "oanda": dr.FetchResult("u3", True, {"active": True}, "", ""),
    }
    table = dr.preprocess_fetch_status(results)
    assert "unreachable" in table and "cause unknown" in table
    assert fp.FAIL_TIMEOUT in table
    # 全滅ではない (oanda は取れた) → 部分失敗として書く
    assert "失敗 2/3" in table and "1/3 本成功" in table
    for banned in fp.INVENTED_CAUSE_PATTERNS:
        assert banned not in table
    # 明示規則: 原因を推測しない / Pro plan
    assert "推測" in table and "Pro" in table


def test_fetch_status_table_all_ok_is_short():
    results = {"status": dr.FetchResult("u", True, {"a": 1}, "", "")}
    table = dr.preprocess_fetch_status(results)
    assert "1/1" in table and "unreachable" not in table


def test_flag_invented_causes_detects_and_footnotes():
    report = "## 課題\n- Render側のコールドスタート（無料tier特有のスリープ）が原因\n"
    hits = dr.flag_invented_causes(report)
    assert hits, "捏造原因の語を検出できていない"
    fixed = dr.append_generator_correction(report, hits, n_failed=2)
    assert fixed.startswith(report), "本文を黙って書き換えてはならない"
    assert "生成器注記" in fixed and "cause unknown" in fixed
    for h in hits:
        assert h in fixed  # どの語を訂正したかを明示する


def test_flag_invented_causes_silent_on_clean_report():
    assert dr.flag_invented_causes("## 前日サマリー\nPnL +12.3p N=4\n") == []


def test_prompt_sent_to_llm_carries_fetch_table_and_no_cause_vocabulary(monkeypatch):
    """LLM へ実際に送る user メッセージを捕まえて検査する (テキスト pin ではなく実挙動).

    - DATA FETCH テーブルが**先頭ブロック**にある (何が取れていないかを知らずに
      数値を語らせない)
    - 原因の断定語を生成器側からは一切供給しない
    - 規則 5 (原因を書かない) が入っている
    """
    captured: dict[str, str] = {}

    def fake_call(system, messages, max_tokens=2500):
        captured["system"] = system
        captured["user"] = messages[0]["content"]
        return "ok"

    monkeypatch.setattr(dr, "call_claude", fake_call)
    monkeypatch.setattr(dr, "load_kb_context", lambda: "")
    results = {
        "status": dr.FetchResult("u1", False, {}, fp.FAIL_TIMEOUT, "timeout: timed out"),
        "trades": dr.FetchResult("u2", False, {}, fp.FAIL_TIMEOUT, "timeout: timed out"),
    }
    data = {k: r.payload for k, r in results.items()}
    dr.run_analyst(data, "pre_tokyo", None, fetch_results=results)
    user = captured["user"]
    assert "### DATA FETCH" in user
    assert user.index("### DATA FETCH") < user.index("### STATUS")
    assert "unreachable, cause unknown" in user
    assert "原因は書かない" in user or "原因を推測してはいけない" in user
    for banned in fp.INVENTED_CAUSE_PATTERNS:
        assert banned.lower() not in user.lower(), f"プロンプトが原因語 {banned!r} を供給している"
