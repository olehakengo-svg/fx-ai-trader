"""estimand 宣言表 + チェッカーの契約テスト (rule:R3, 2026-09-10).

2 層を pin する:

1. **実宣言表がリポジトリ実体と整合している** — reader/threshold_source/
   detector の配線が切れたら (ファイル改名・参照削除) 本テストが CI で落ちる。
   これにより宣言表そのものが「読まれる計装」になる。
2. **チェッカー自体の counterfactual** — 「検査を書いたら、検査対象を壊して
   検査が落ちることを確認する」教訓 (PR #208 の counterfactual ⑥ 素通り /
   MEMORY project_monitoring_blind_during_outage_2026_08_30 「counterfactual
   初回素通り = pin 無しの証拠」) の適用。宣言表の 1 エントリの reader を
   偽パスに書き換えた fixture で checker が ERROR を出すことを pin する。
   これが無いと、checker の検証ロジックが黙って no-op 化しても
   (126 日 no-op の型) 全テスト green のままになる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import estimand_declaration_check as edc  # noqa: E402

DECLARATIONS = ROOT / edc.DEFAULT_DECLARATIONS


@pytest.fixture(scope="module")
def real_doc():
    return edc.load_declarations(DECLARATIONS)


# ── 1. 実宣言表 vs リポジトリ実体 ────────────────────────────────────────

def test_real_declarations_have_no_wiring_errors(real_doc):
    """宣言表の配線 (reader / threshold_source / detector / counterfactual
    パス) がリポジトリ実体と一致していること。ここが落ちたら、宣言表と
    コードのどちらかが動いた = 同じコミットで揃えよ (KB 運用ルール)。"""
    errors, _warns = edc.check_declarations(real_doc, ROOT)
    assert errors == [], "\n".join(errors)


def test_minimum_series_are_declared(real_doc):
    """メタ監査 R3 で名指しされた 8 系列が最低限宣言されていること。
    宣言表からの黙った削除 (「面倒だから消す」) を防ぐ。"""
    names = {s.get("name") for s in real_doc["series"]}
    required = {
        "engine_tick_stall",
        "candidate_stagnation",
        "trade_row_freshness",
        "live_fill_stagnation",
        "live_n_stagnation",
        "db_write_probe",
        "m1_clean_live_kpi",
        "shadow_promote_r2_alert",
    }
    missing = required - names
    assert not missing, f"宣言表から必須系列が消えている: {sorted(missing)}"
    assert len(names) >= 8


def test_default_run_is_warn_not_fail_and_strict_fails():
    """既知の MISSING (返済計画は analyses doc §5) は WARN = exit 0。
    --strict では exit 1。MISSING が全返済されたら strict 側の期待を
    反転させて、以後の退行 (新たな MISSING) を CI で止めること。"""
    code, report = edc.run_check(DECLARATIONS, ROOT, strict=False)
    assert code == 0
    assert report["errors"] == []
    assert report["warnings"], "既知の MISSING が消えたなら本テストの期待を更新せよ"

    strict_code, _ = edc.run_check(DECLARATIONS, ROOT, strict=True)
    assert strict_code == 1


def test_clocks_match_the_ssot_docstring(real_doc):
    """時計の宣言が modules/freshness_policy.py の SSOT 表と一致すること。
    (取り違えは PR #207/#209 で実際に踏んだ型 — 週末に毎回誤発火 or
    本物の週末停止を毎週見逃す)。"""
    clocks = {s["name"]: s["clock"] for s in real_doc["series"]}
    assert clocks["engine_tick_stall"] == "wall"
    assert clocks["candidate_stagnation"] == "market_open"
    assert clocks["trade_row_freshness"] == "market_open"
    assert clocks["live_n_stagnation"] == "market_open"
    assert clocks["live_fill_stagnation"] == "market_open"
    # M1 は暦月の符号を問う KPI — 市場オープン換算しない (tools/m1_clean_live_monitor.py docstring)
    assert clocks["m1_clean_live_kpi"] == "wall"


# ── 2. チェッカー自体の counterfactual ──────────────────────────────────

def _mutated_run(tmp_path: Path, old: str, new: str, count: int = 1):
    """実宣言表のテキストを 1 箇所書き換えた fixture を tmp に置いて検査。
    パーサ→チェッカーの実経路 (main が通る経路と同じ) を使う。"""
    text = DECLARATIONS.read_text(encoding="utf-8")
    assert text.count(old) >= count, f"fixture の前提が崩れた: {old!r} が宣言表に無い"
    mutated = text.replace(old, new, count)
    assert mutated != text
    fixture = tmp_path / "estimand_declarations.yml"
    fixture.write_text(mutated, encoding="utf-8")
    return edc.run_check(fixture, ROOT, strict=False)


def test_fake_reader_path_is_detected(tmp_path):
    """counterfactual: 1 エントリの reader を偽パスに書き換える → ERROR。
    これが通らないなら checker は配線を見ていない (write-only 検査)。"""
    code, report = _mutated_run(
        tmp_path,
        '"render.yaml :: anomaly_watcher.py"',
        '"render_gone.yaml :: anomaly_watcher.py"',
    )
    assert code == 1
    assert any("render_gone.yaml" in e and "実在しない" in e for e in report["errors"]), report


def test_reader_that_stops_referencing_the_detector_is_detected(tmp_path):
    """counterfactual: reader ファイルは実在するが宣言された文字列を含まない
    → ERROR (配線切れ)。ファイル存在チェックだけでは「読み手はいるが
    別のものを読んでいる」を素通りさせる。"""
    code, report = _mutated_run(
        tmp_path,
        '"tools/quant_gate_status.py :: m1_clean_live_monitor"',
        '"tools/quant_gate_status.py :: m1_totally_absent_token"',
    )
    assert code == 1
    assert any(
        "quant_gate_status.py" in e and "参照していない" in e for e in report["errors"]
    ), report


def test_fake_counterfactual_test_path_is_detected(tmp_path):
    """counterfactual: counterfactual_test を実在しないテストパスに書き換える
    → ERROR。「テストがある」と宣言してテストが無いのは MISSING より悪い。"""
    code, report = _mutated_run(
        tmp_path,
        '"tests/test_live_fill_stagnation.py"',
        '"tests/test_live_fill_stagnation_gone.py"',
    )
    assert code == 1
    assert any("test_live_fill_stagnation_gone.py" in e for e in report["errors"]), report


def test_fake_threshold_symbol_is_detected(tmp_path):
    """counterfactual: threshold_source のシンボルを偽名に → ERROR。
    閾値 SSOT の改名 (freshness_policy リファクタ等) に宣言表が追従しない
    状態を CI で止める。"""
    code, report = _mutated_run(
        tmp_path,
        '"modules/freshness_policy.py:LIVE_FILL_STAGNATION_HOURS"',
        '"modules/freshness_policy.py:LIVE_FILL_STAGNATION_HOURS_RENAMED"',
    )
    assert code == 1
    assert any("LIVE_FILL_STAGNATION_HOURS_RENAMED" in e for e in report["errors"]), report


def test_invalid_clock_is_detected(tmp_path):
    """schema counterfactual: clock の値域外 (時計の取り違えは名乗り違いと
    同格の estimand 欠陥) → ERROR。"""
    code, report = _mutated_run(tmp_path, "clock: market_open", "clock: local_time", 1)
    assert code == 1
    assert any("clock" in e for e in report["errors"]), report


def test_unknown_field_is_rejected(tmp_path):
    """schema counterfactual: typo フィールド (counterfactual_tset 等) を黙って
    無視すると、必須フィールド検査が「書いたつもり」を素通りさせる。"""
    code, report = _mutated_run(
        tmp_path, "    notes:", "    nootes:", 1
    )
    assert code == 1
    assert any("未知のフィールド" in e for e in report["errors"]), report


def test_missing_stays_a_warning_not_an_error():
    """MISSING の意味論 pin: WARN であって ERROR ではない (exit 0)。
    ERROR に格上げすると、既知負債の列挙が「表に書かない」インセンティブに
    変わる — 宣言表は正直であるほど価値がある。格上げは全返済後に --strict
    を CI 既定にする形で行う (説明文書 §6)。"""
    doc = {
        "version": "1",
        "series": [
            {
                "name": "x_series",
                "claims": "テスト用",
                "population": "テスト用",
                "clock": "wall",
                "threshold_source": "modules/freshness_policy.py:N_STAGNATION_HOURS",
                "reader": ["render.yaml :: anomaly_watcher.py"],
                "counterfactual_test": "MISSING",
            }
        ],
    }
    errors, warns = edc.check_declarations(doc, ROOT)
    assert errors == []
    assert any("MISSING" in w for w in warns)


def test_parser_rejects_tabs_and_garbage_instead_of_skipping():
    """パーサ counterfactual: 読めない行を黙って読み飛ばすと「宣言したつもり」
    が検査対象から静かに消える (ZN 計装契約バグの型)。ParseError で落ちること。"""
    with pytest.raises(edc.ParseError):
        edc.parse_declarations_text("version: 1\nseries:\n\t- name: x\n")
    with pytest.raises(edc.ParseError):
        edc.parse_declarations_text("version: 1\nseries:\n   - name: bad_indent\n")


def test_module_import_has_no_side_effects():
    """モジュールトップ副作用禁止の pin: import しても argv を読まない・
    環境を触らない。(cron/CI どちらからも安全に import できること)。"""
    import importlib

    saved_argv = list(sys.argv)
    sys.argv = ["pytest", "--this-flag-would-crash-argparse"]
    try:
        importlib.reload(edc)
    finally:
        sys.argv = saved_argv
