"""family A pass-1 — label-free であること + 凍結窓の pin (2026-09-18)。

pass-1 の存在理由は「explore outcome に触れずに park 判定できること」なので、
label を読まないことがこのモジュールの最重要性質。
"""
import datetime as dt
import pathlib

from tools import family_a_pass1 as p1
from tools import family_a_ladder_detector as det


def test_explore_window_matches_the_freeze():
    assert (p1.EXPLORE_START, p1.EXPLORE_END) == (dt.date(2022, 1, 7), dt.date(2026, 7, 29))


def test_module_never_reads_intervention_labels():
    src = pathlib.Path(p1.__file__).read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    # 唯一の出現は _FORBIDDEN タプル内 (構造ガードの定義そのもの)
    assert code.count("interventions_daily") == 1
    assert "amount_yen" not in code
    assert "pass2" not in code.replace("pass2_unlocked", "")


def test_run_reports_frozen_params_and_gate_shape():
    res = p1.run()
    assert res["params"] == {"T": 5, "R": 20, "H": 20, "trigger": 4}
    g = res["gates"]
    for k in ("n_business_days", "n_events", "event_years", "armed_fraction",
              "gate_a_specificity", "gate_b_supply", "pass2_unlocked"):
        assert k in g
    assert g["pass2_unlocked"] == (g["gate_a_specificity"] and g["gate_b_supply"])


def test_rolled_forward_conferences_are_reported():
    """A-8 の roll-forward が readout に現れること (黙って消えない)。"""
    res = p1.run()
    rolled = res["conferences_rolled_forward"]
    assert "2026-05-04" in rolled, "L4 非営業日会見が readout から落ちている"
    assert all(not det.is_business_day(dt.date.fromisoformat(d)) for d in rolled)


def test_effective_level_hist_has_no_level_5():
    """A-1 remap 後、explore 窓に L5 (leading) は 1 件も無いはず。

    corpus の L5 は全て retrospective で降格される。将来 `レートチェック` が
    出現したらこの pin が落ちる = 設計上の想定変化に気付ける。
    """
    res = p1.run()
    assert "5" not in res["effective_level_hist"]


# --- Codex P2 (PR #268): 文書化された起動形態が実際に動くこと ------------------
def test_documented_invocations_both_work():
    """docstring の 2 形態を実際に起動して確認する (README 嘘の防止)。"""
    import subprocess
    root = pathlib.Path(p1.__file__).resolve().parents[1]
    for cmd in (["python3", "tools/family_a_pass1.py"],
                ["python3", "-m", "tools.family_a_pass1"]):
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"{cmd} -> rc={r.returncode}\n{r.stderr[-800:]}"
        assert '"pass2_unlocked"' in r.stdout, f"{cmd} の出力が想定外"


def test_path_bootstrap_has_no_import_side_effect():
    """ライブラリ import 時に sys.path をいじらないこと (CLAUDE.md 規律)。"""
    src = pathlib.Path(p1.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        if "sys.path.insert" in line and not line.lstrip().startswith("#"):
            assert line.startswith("    "), "sys.path 操作が __main__ ガード外にある"
