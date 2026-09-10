"""ZN=F 1h cache 鮮度 pin の counterfactual テスト (2026-09-10, rule:R3).

故障の実測 (gh run log, run 34124847021 ほか 4/4):
  zn-cache-refresh.yml は fetch 成功 (rows 14225→14537, 右端 2026-09-04) の
  直後、commit 段の素の ``git add data/cache/yield/ZN_F_1h.parquet`` が
  .gitignore の ``data/cache/`` に拒否され exit 1 — 2026-08-17〜09-07 の
  全 run が取得データを捨てて死んでいた。track 済みファイルでも git >= 2.5x
  は ignored dir 配下への素の add を advice + exit 1 で拒否する (ローカル
  実測で再現済み)。修理は ``git add -f``。

pin する配線 (counterfactual = これらを殺すと本テストが落ちる):
  1. zn-cache-refresh.yml の add が ``-f`` 付きであること (素の add への
     退行 = 全 run 再死亡)。
  2. weekly-audit.yml が scripts/check_zn_cache_freshness.py を実行する
     こと — refresh が再び silent fail しても 1 週間で読み手が検知する。
     「収集済み ≠ 監視済み」(4 回の赤 run を誰も読んでいなかった)。
  3. 読み手スクリプト自体の red→green: stale / 欠損 / 空 → fail、
     fresh → pass。unknown を ok 側に畳まない。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

import scripts.check_zn_cache_freshness as zn_check
from modules.freshness_policy import ZN_CACHE_MAX_AGE_DAYS

REPO_ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def _write_parquet(path: Path, right_edge: datetime, *, tz_naive: bool = False) -> None:
    idx = pd.date_range(end=right_edge, periods=24, freq="1h", tz="UTC")
    if tz_naive:
        idx = idx.tz_localize(None)
    pd.DataFrame({"Close": 1.0}, index=idx).to_parquet(path)


# ══════════════════════════════════════════════════════════════
# 1. zn-cache-refresh.yml — git add -f 退行 pin
# ══════════════════════════════════════════════════════════════


def test_zn_refresh_workflow_uses_git_add_force():
    text = (REPO_ROOT / ".github" / "workflows" / "zn-cache-refresh.yml").read_text(
        encoding="utf-8"
    )
    assert "git add -f data/cache/yield/ZN_F_1h.parquet" in text, (
        "zn-cache-refresh.yml の add に -f が無い。data/cache/ は .gitignore "
        "対象なので素の git add は exit 1 で全 run が死ぬ (2026-08-17〜09-07 "
        "の 4/4 失敗の根因)"
    )


def test_zn_refresh_workflow_has_no_plain_git_add_on_cache():
    text = (REPO_ROOT / ".github" / "workflows" / "zn-cache-refresh.yml").read_text(
        encoding="utf-8"
    )
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "git add" in stripped and "data/cache" in stripped:
            assert "git add -f" in stripped, f"素の git add への退行: {stripped!r}"


# ══════════════════════════════════════════════════════════════
# 2. weekly-audit.yml — 読み手の配線 pin (counterfactual)
# ══════════════════════════════════════════════════════════════


def test_weekly_audit_wires_zn_freshness_reader():
    text = (REPO_ROOT / ".github" / "workflows" / "weekly-audit.yml").read_text(
        encoding="utf-8"
    )
    assert "scripts/check_zn_cache_freshness.py" in text, (
        "weekly-audit.yml から ZN cache 鮮度チェックの配線が消えている。"
        "refresh workflow の silent fail を読む者がいなくなる "
        "(収集済み ≠ 監視済み)"
    )
    # 読み手 job のブロック内で失敗が握り潰されていないこと
    job_block = text.split("zn-cache-freshness:", 1)
    assert len(job_block) == 2, "zn-cache-freshness job が無い"
    assert "continue-on-error" not in job_block[1], (
        "zn-cache-freshness job が continue-on-error で握り潰されている — "
        "落ちない読み手は write-only 監視と同じ"
    )


def test_reader_script_exists_and_uses_ssot_threshold():
    script = REPO_ROOT / "scripts" / "check_zn_cache_freshness.py"
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "ZN_CACHE_MAX_AGE_DAYS" in text, (
        "閾値が SSOT (modules/freshness_policy.py) から来ていない — "
        "閾値の二重定義は片方だけ更新される (PR #209 教訓)"
    )


# ══════════════════════════════════════════════════════════════
# 3. 読み手スクリプトの red→green
# ══════════════════════════════════════════════════════════════


def test_stale_cache_fails(tmp_path):
    p = tmp_path / "zn.parquet"
    _write_parquet(p, NOW - timedelta(days=ZN_CACHE_MAX_AGE_DAYS + 5))
    ok, msg = zn_check.run_check(p, now=NOW)
    assert not ok
    assert "STALE" in msg


def test_fresh_cache_passes(tmp_path):
    p = tmp_path / "zn.parquet"
    _write_parquet(p, NOW - timedelta(days=2))
    ok, msg = zn_check.run_check(p, now=NOW)
    assert ok, msg
    assert "OK" in msg


def test_fresh_cache_passes_with_naive_index(tmp_path):
    # 実ファイルは tz-aware UTC だが、naive で書かれても UTC として読む
    p = tmp_path / "zn.parquet"
    _write_parquet(p, NOW - timedelta(days=2), tz_naive=True)
    ok, msg = zn_check.run_check(p, now=NOW)
    assert ok, msg


def test_missing_cache_fails(tmp_path):
    # 「無ければ skip」は 126 日 no-op の原因 — 欠損は fail 側に倒す
    ok, msg = zn_check.run_check(tmp_path / "does_not_exist.parquet", now=NOW)
    assert not ok
    assert "存在しない" in msg


def test_empty_cache_fails(tmp_path):
    p = tmp_path / "zn.parquet"
    pd.DataFrame({"Close": pd.Series(dtype=float)}).to_parquet(p)
    ok, msg = zn_check.run_check(p, now=NOW)
    assert not ok


def test_main_exit_codes_and_discord_notify(tmp_path, monkeypatch):
    stale = tmp_path / "stale.parquet"
    _write_parquet(stale, datetime.now(timezone.utc) - timedelta(days=30))
    fresh = tmp_path / "fresh.parquet"
    _write_parquet(fresh, datetime.now(timezone.utc) - timedelta(hours=6))

    calls: list[str] = []
    monkeypatch.setattr(
        zn_check.urllib.request,
        "urlopen",
        lambda req, timeout=15: calls.append(req.full_url),
    )

    # stale + webhook 設定あり → exit 1 + Discord 通知
    monkeypatch.setenv("DISCORD_ERROR_WEBHOOK_URL", "https://example.invalid/hook")
    assert zn_check.main(["--path", str(stale)]) == 1
    assert calls == ["https://example.invalid/hook"]

    # fresh → exit 0、通知なし
    assert zn_check.main(["--path", str(fresh)]) == 0
    assert len(calls) == 1

    # scheme guard: https 以外は開かない (env 由来 URL の file:// 対策)
    calls.clear()
    monkeypatch.setenv("DISCORD_ERROR_WEBHOOK_URL", "file:///etc/passwd")
    assert zn_check.main(["--path", str(stale)]) == 1
    assert calls == []


def test_threshold_calibration_detects_one_missed_refresh():
    """較正 pin: 正常時 (~5.8 日) は誤検知せず、refresh 1 回失敗 (~12.8 日) を捕捉.

    refresh = 月曜 06:40 UTC / 読み手 = 日曜 02:00 UTC。閾値をこの間隔の
    外へ動かすと、正常誤検知 (下げすぎ) か 1 週間以内の検知不能 (上げすぎ)
    のどちらかが起きる。
    """
    assert 6 <= ZN_CACHE_MAX_AGE_DAYS <= 12, (
        f"ZN_CACHE_MAX_AGE_DAYS={ZN_CACHE_MAX_AGE_DAYS} は較正範囲外 — "
        "正常時右端年齢 ≈5.8 日 / 1 回失敗 ≈12.8 日の間に置くこと"
    )
