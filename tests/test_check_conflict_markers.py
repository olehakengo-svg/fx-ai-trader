# -*- coding: utf-8 -*-
"""scripts/hooks/check_conflict_markers.py — 行頭 conflict マーカー検査 (2026-10-22 R3)。

性質で pin する: (1) 行頭のマーカー 3 種だけを検出する、(2) 本文中の引用 (KB の事故記述に
含まれる `<<<<<<<`) には反応しない、(3) `======` 6 本や `======= x` は対象外、(4) バイナリ・
不在は skip して落ちない、(5) CLI は違反で 1 / clean で 0 / 引数なしで 2。git は使わない
(GIT_* リーク教訓 2026-09-22)。
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hooks" / "check_conflict_markers.py"

spec = importlib.util.spec_from_file_location("check_conflict_markers", SCRIPT)
ccm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccm)


def test_detects_the_three_line_anchored_markers():
    text = "a\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> origin/main\nz\n"
    hits = ccm.find_markers(text)
    assert [h[0] for h in hits] == [2, 4, 6]
    assert [h[1] for h in hits] == ["<<<<<<<", "=======", ">>>>>>>"]


def test_ignores_markers_quoted_inside_prose():
    # KB の事故記述そのもの: 行頭ではないので反応しない (2026-10-20 の偽陽性停止の再演回避)
    text = ("- 教訓: 解決スクリプトが本文中の `<<<<<<<` に反応して停止した\n"
            "  '>>>>>>> origin' という文字列を含む行\n"
            "数式の区切り ====== (6 本) や ======= 7 本の後に文字がある行\n")
    assert ccm.find_markers(text) == []


def test_exact_seven_equals_line_only():
    assert ccm.find_markers("======\n") == []
    assert ccm.find_markers("========\n") == []
    assert ccm.find_markers("=======\n") == [(1, "=======")]
    assert ccm.find_markers("======= rest\n") == []


def test_scan_skips_binary_and_missing_files(tmp_path, capsys):
    bad = tmp_path / "x.bin"
    bad.write_bytes(b"\x00\x01<<<<<<< HEAD\n")
    txt = tmp_path / "ok.md"
    txt.write_text("clean\n", encoding="utf-8")
    out = ccm.scan([str(bad), str(tmp_path / "missing.md"), str(txt)])
    assert out == []
    err = capsys.readouterr().err
    assert "skip" in err


def test_scan_reports_path_line_and_marker(tmp_path):
    f = tmp_path / "changelog.md"
    f.write_text("# head\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> x\n", encoding="utf-8")
    out = ccm.scan([str(f)])
    assert out == [f"{f}:2: <<<<<<<", f"{f}:4: =======", f"{f}:6: >>>>>>>"]


def test_cli_exit_codes(tmp_path):
    dirty = tmp_path / "d.md"
    dirty.write_text("<<<<<<< HEAD\n", encoding="utf-8")
    clean = tmp_path / "c.md"
    clean.write_text("fine\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(clean)], capture_output=True, text=True)
    assert r.returncode == 0
    r = subprocess.run([sys.executable, str(SCRIPT), "--stdin"], input=f"{dirty}\n{clean}\n",
                       capture_output=True, text=True)
    assert r.returncode == 1 and "d.md:1: <<<<<<<" in r.stdout
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 2


def test_stdin0_keeps_literal_non_ascii_and_spaced_paths(tmp_path):
    jp = tmp_path / "セッション ログ 2026-10-22.md"  # 非 ASCII + 空白
    jp.write_text("ok\n<<<<<<< HEAD\n", encoding="utf-8")
    spaced = tmp_path / " leading-space.md"
    spaced.write_text("clean\n", encoding="utf-8")
    payload = f"{jp}\0{spaced}\0".encode("utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), "--stdin0"], input=payload, capture_output=True)
    out = r.stdout.decode("utf-8")
    assert r.returncode == 1 and "セッション ログ 2026-10-22.md:2: <<<<<<<" in out
    assert "skip" not in r.stderr.decode("utf-8")  # 空白付きパスも字義どおり読めている


def test_hook_wires_the_checker_against_the_index_with_nul_paths_and_renames():
    hook = (ROOT / "scripts" / "hooks" / "git-pre-commit.sh").read_text(encoding="utf-8")
    assert "check_conflict_markers.py" in hook
    assert "--stdin0 --index" in hook
    assert "--name-only -z --diff-filter=ACMR" in hook  # rename/copy を含め、quotePath を避ける
    assert "--diff-filter=AM\"" not in hook
