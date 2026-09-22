"""「HTTP 全盲」と「サービス停止」を外部から分離する検知器 (rule:R3, 2026-09-22).

2026-09-22 00:15〜03:33Z、本番 web service は **プロセスもエンジンも生きたまま**
HTTP だけが 3h18m 応答しなかった (knowledge-base/wiki/analyses/
http-blind-fork-poisoning-2026-09-22.md)。既存の ``api_unreachable`` は 4 本全滅を
「サービスの死」として通知し、読み手 (daily report の LLM) はそれを
「Render 無料 tier のスリープ」と**捏造**した。

外部 (状態を持たない cron) が持てる証拠は fetch の**失敗クラス**だけである:

  - ``ReadTimeout`` = TCP 接続は成立し、応答が timeout 内に来ない
    → **プロセスは listen している。HTTP 層が返ってこない** (= http_blind)
  - ``ConnectionError`` / 5xx = 接続拒否・リセット・edge 502
    → **プロセスが serving していない** (= api_down: デプロイ / 再起動 / 停止)

判定は modules/freshness_policy.classify_outage が SSOT で、watcher と
daily_report が同じ関数を読む (閾値の二重定義禁止の既存方針と同じ)。

counterfactual (実測済): watcher の ``check_api_reachability`` から
``classify_outage`` の分岐を消すと ``test_all_read_timeouts_is_http_blind`` が
``api_unreachable`` を返して落ちる。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from modules import freshness_policy as fp

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "anomaly_watcher_blind", ROOT / "scripts" / "anomaly_watcher.py"
)
aw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aw)

RT = ("ReadTimeout: HTTPSConnectionPool(host='fx-ai-trader.onrender.com', port=443): "
      "Read timed out. (read timeout=15)")
CE = ("ConnectionError: HTTPSConnectionPool(host='fx-ai-trader.onrender.com', port=443): "
      "Max retries exceeded")
H502 = "HTTPError: 502 Server Error: Bad Gateway for url: https://fx-ai-trader.onrender.com/x"


def _fail(path: str, reason: str) -> "aw.FetchOutcome":
    return aw.FetchOutcome(path, False, {}, reason)


# ── SSOT 側 (freshness_policy) ──────────────────────────────────────────
class TestClassifyFetchFailure:
    @pytest.mark.parametrize("reason, expected", [
        (RT, fp.FAIL_TIMEOUT),
        ("ReadTimeoutError: ...", fp.FAIL_TIMEOUT),
        ("timeout: timed out", fp.FAIL_TIMEOUT),          # urllib (daily_report)
        ("TimeoutError: The read operation timed out", fp.FAIL_TIMEOUT),
        (CE, fp.FAIL_CONNECTION),
        ("URLError: <urlopen error [Errno 111] Connection refused>", fp.FAIL_CONNECTION),
        ("ConnectionResetError: [Errno 104]", fp.FAIL_CONNECTION),
        ("RemoteDisconnected: Remote end closed connection", fp.FAIL_CONNECTION),
        (H502, fp.FAIL_HTTP_STATUS),
        ("HTTPError: HTTP Error 503: Service Unavailable", fp.FAIL_HTTP_STATUS),
        ("JSONDecodeError: Expecting value", fp.FAIL_OTHER),
        ("", fp.FAIL_OTHER),
    ])
    def test_classes(self, reason, expected):
        assert fp.classify_fetch_failure(reason) == expected

    def test_connect_timeout_is_not_blind(self):
        """接続段階の timeout は「listen していない」側 — blind と混ぜない。"""
        assert fp.classify_fetch_failure(
            "ConnectTimeout: HTTPSConnectionPool(...) Connection to host timed out"
        ) == fp.FAIL_CONNECTION


class TestClassifyOutage:
    def test_all_read_timeouts_is_http_blind(self):
        out = fp.classify_outage({f"/p{i}": RT for i in range(5)})
        assert out["kind"] == fp.OUTAGE_HTTP_BLIND
        assert out["n_timeout"] == 5 and out["n_connection"] == 0

    def test_all_connection_errors_is_api_down(self):
        out = fp.classify_outage({"/a": CE, "/b": H502, "/c": CE})
        assert out["kind"] == fp.OUTAGE_API_DOWN

    def test_mixed_is_reported_as_mixed_not_collapsed(self):
        """timeout と connection error が混在 = 遷移中 (再起動直後など)。
        どちらかに畳むと切り分けが消える。"""
        out = fp.classify_outage({"/a": RT, "/b": CE})
        assert out["kind"] == fp.OUTAGE_MIXED

    def test_other_only_is_unknown(self):
        out = fp.classify_outage({"/a": "JSONDecodeError: x"})
        assert out["kind"] == fp.OUTAGE_UNKNOWN

    def test_empty_is_unknown(self):
        assert fp.classify_outage({})["kind"] == fp.OUTAGE_UNKNOWN

    def test_human_text_is_provided_and_does_not_invent_causes(self):
        """読み手 (LLM / 人) に渡す文言は「何が観測されたか」だけを述べる。
        原因の断定語 (スリープ / 無料 tier / コールドスタート) を含まない。"""
        for reasons in ({"/a": RT}, {"/a": CE}, {"/a": RT, "/b": CE}, {}):
            text = fp.classify_outage(reasons)["summary"]
            assert text
            for banned in fp.INVENTED_CAUSE_PATTERNS:
                assert banned not in text, (reasons, banned)


# ── 検知器側 (anomaly_watcher) ───────────────────────────────────────────
class TestHttpBlindEvent:
    def test_all_read_timeouts_fire_http_blind_not_api_unreachable(self):
        outcomes = {p: _fail(p, RT) for p in aw.WATCHED_PATHS}
        ev = aw.check_api_reachability(outcomes, attempts=4, waited_sec=210.0)
        assert len(ev) == 1
        assert ev[0]["type"] == "http_blind"
        assert ev[0]["outage_kind"] == fp.OUTAGE_HTTP_BLIND
        assert ev[0]["n_failed"] == len(aw.WATCHED_PATHS)
        assert ev[0]["attempts"] == 4 and ev[0]["waited_sec"] == 210.0

    def test_connection_errors_still_fire_api_unreachable(self):
        """既存の意味は不変 — デプロイ/再起動の 502 は api_unreachable のまま。"""
        outcomes = {p: _fail(p, H502) for p in aw.WATCHED_PATHS}
        ev = aw.check_api_reachability(outcomes)
        assert ev[0]["type"] == "api_unreachable"
        assert ev[0]["outage_kind"] == fp.OUTAGE_API_DOWN

    def test_mixed_failures_stay_api_unreachable_with_kind_mixed(self):
        outcomes = {p: _fail(p, RT if i % 2 else CE) for i, p in enumerate(aw.WATCHED_PATHS)}
        ev = aw.check_api_reachability(outcomes)
        assert ev[0]["type"] == "api_unreachable"
        assert ev[0]["outage_kind"] == fp.OUTAGE_MIXED

    def test_partial_failure_is_unchanged(self):
        outcomes = {p: aw.FetchOutcome(p, True, {}, "") for p in aw.WATCHED_PATHS}
        outcomes["/api/demo/status"] = _fail("/api/demo/status", RT)
        ev = aw.check_api_reachability(outcomes)
        assert ev[0]["type"] == "api_endpoint_failed"

    def test_http_blind_notifies_hourly_and_is_not_silenced(self):
        assert "http_blind" not in aw.NOTIFY_NEVER
        assert aw.NOTIFY_EVERY_HOURS["http_blind"] == 1

    def test_http_blind_line_says_engine_state_is_unknown_from_outside(self):
        """行文言: 「プロセスは listen / HTTP 無応答 / engine 生死は外部から不明 /
        Render ログ [MainLoop] を見よ」。汎用 fallback に落ちていないこと。
        原因の断定 (スリープ等) を含まないこと。"""
        outcomes = {p: _fail(p, RT) for p in aw.WATCHED_PATHS}
        line = aw._event_line(aw.check_api_reachability(outcomes)[0])
        assert line.startswith("- ")
        assert "HTTP" in line and "MainLoop" in line
        assert "engine" in line.lower() or "エンジン" in line
        assert "不明" in line
        for banned in fp.INVENTED_CAUSE_PATTERNS:
            assert banned not in line
        assert not line.startswith("- http_blind: {")

    def test_watcher_uses_the_shared_classifier(self):
        """SSOT pin: watcher が判定を再実装していないこと (閾値二重定義の教訓)。"""
        src = (ROOT / "scripts" / "anomaly_watcher.py").read_text(encoding="utf-8")
        assert "classify_outage(" in src
        assert "OUTAGE_HTTP_BLIND" in src
        # watcher 側で ReadTimeout を直に文字列比較していない
        assert 'startswith("ReadTimeout' not in src
