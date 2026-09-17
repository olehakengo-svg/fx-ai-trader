"""mof_statements_daily の per-source isolation を固定する test pin (network 不要)。

背景 (2026-09-17, rule:R3): main() が dict literal で 5 ソースを直列評価していたため、
最後段の GDELT が 429 で raise すると先に成功していた 4 ソースの成果ごとプロセスが落ち、
workflow の commit step が走らず runner の ephemeral disk ごと破棄されていた。
実害: 2026-09-16 run 35163419350 が `[daily-conf] new=1` (my20260915.html) /
`[daily-rss] new=1` / `[score] 512 conferences` まで到達して全破棄 (repo 側 511 で停止)。

固定する不変条件:
  1. soft ソース (gdelt) の失敗は raise しない — 他ソースは全て実行される
  2. hard ソース (interventions/conferences/score/rss) の失敗は raise する
  3. raise は **全ソース試行後** — 後段のソースを道連れにしない
  4. 失敗ソースも summary に error を残す (サイレント欠損の禁止)
"""
import pytest

from tools import mof_statements_daily as D


def _patch_steps(monkeypatch, failing: dict):
    """_STEPS を全てスタブ化し、failing に挙げた名前だけ raise させる。"""
    called = []

    def make(name):
        def fn():
            called.append(name)
            if name in failing:
                raise failing[name]
            return {"ok": name}
        return fn

    monkeypatch.setattr(
        D, "_STEPS", tuple((n, make(n)) for n, _ in D._STEPS)
    )
    return called


def test_soft_gdelt_failure_does_not_raise_and_others_run(monkeypatch):
    called = _patch_steps(monkeypatch, {"gdelt": RuntimeError("http 429")})
    summary = D.main()

    assert [n for n, _ in D._STEPS] == called          # 全ソース試行
    assert "error" in summary["gdelt"]
    assert "429" in summary["gdelt"]["error"]
    for name in ("interventions", "conferences", "score", "rss"):
        assert summary[name] == {"ok": name}


def test_hard_failure_raises_but_only_after_all_sources_ran(monkeypatch):
    called = _patch_steps(monkeypatch, {"conferences": RuntimeError("mof 503")})

    with pytest.raises(RuntimeError, match="hard sources failed: conferences"):
        D.main()

    # 中断されずに後段 (score/rss/gdelt) まで到達していること = 部分成果が残る
    assert [n for n, _ in D._STEPS] == called


def test_hard_and_soft_failures_are_reported_separately(monkeypatch):
    _patch_steps(
        monkeypatch,
        {"rss": RuntimeError("rss timeout"), "gdelt": RuntimeError("http 429")},
    )
    with pytest.raises(RuntimeError) as exc:
        D.main()

    msg = str(exc.value)
    assert "rss" in msg
    assert "gdelt" not in msg            # soft は raise 理由に含めない


def test_gdelt_is_the_only_soft_source():
    """soft 指定の拡大は「失敗が観測されなくなる」ので pin する。"""
    assert D._SOFT_SOURCES == {"gdelt"}
