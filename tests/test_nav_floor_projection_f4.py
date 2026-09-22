"""F4 資金時計 — decomposed 推定器 (2026-09-22 方法変更) の性質 pin。

pin する性質 (構文でなく性質で):
1. 09-15〜09-21 の実 CSV 入力 (fit が 82→…→40.4 と振動した窓) を与えたとき、
   decomposed は ±10% 内で安定し、fit のみだと安定しない。
2. counterfactual: days_to_floor 列は decomposed の値であり fit の値ではない
   (primary を fit に戻すと落ちる)。fit は参考列に残る。
3. keeper 分は telemetry (target/volume/rt_count) から決定論的に出る。
4. edge 分は broker NAV Δ から当月 keeper 支出を差し引いた残差。測れない窓は
   0 に折り畳まず basis に unavailable を明示する。
5. 既存 6 列は不変 (registry csv_row_match の読み手が壊れない)。
6. API 取得失敗は exit 1 + 行を書かない。cron 側 (daily-report.yml) は step
   outcome を Notify で露出する (握り潰し禁止)。
7. registry F4 message が方法変更 + 発火日シフトを記録し condition は不変。
8. 再現値 pin: 09-22 以降 keeper のみ / drift 13.7 の 2 経路で decomposed 読み手の
   初回発火日 (2027-01-05 / 2026-12-04) — 推定器を変えたら数値が動いて落ちる。
9. (PR #285 review P2 ×2) keeper ¥/RT は telemetry の units で線形スケール
   (SVK_UNITS 20k/5k で月次総額不変、RT 数×単価が反比例) / telemetry の month が
   asof と違う (UTC 月替わり 00:00 cron) 間は edge を unavailable にし、前月
   rt_count で keeper burn を打ち消さない。既知 NG 入力で pin。
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from tools import nav_floor_projection as nfp

ROOT = Path(__file__).resolve().parent.parent

# data/monitoring/nav_floor_projection.csv の 2026-09-07〜09-21 実行 (先頭 6 列)。
# 09-13 (日) / 09-20 (日) は cron 仕様 (1-5) で行なし。
REAL_ROWS_0907_0921 = [
    ("2026-09-07", 276304, 82.0, 174, "audit_default"),
    ("2026-09-10", 275586, 82.0, 165, "audit_default"),
    ("2026-09-11", 275677, 82.0, 166, "audit_default"),
    ("2026-09-12", 275677, 82.0, 166, "audit_default"),
    ("2026-09-14", 275517, 82.0, 164, "audit_default"),
    ("2026-09-15", 275517, 82.0, 164, "audit_default"),
    ("2026-09-16", 275517, 74.8, 180, "fit"),
    ("2026-09-17", 275517, 64.3, 210, "fit"),
    ("2026-09-18", 275517, 55.8, 242, "fit"),
    ("2026-09-19", 275517, 55.8, 242, "fit"),
    ("2026-09-21", 275517, 40.4, 334, "fit"),
]
# /api/demo/status.status_volume_keeper 2026-09-22 08:40Z 実測
KEEPER_0922 = {"month": "2026-09", "target_usd": 520000.0, "volume_usd": 520000.0,
               "rt_count": 26, "last_rt_at": "2026-09-14T01:01:07.662843+00:00"}
NAV_0922 = 275516.8319


def _rows(upto: str | None = None, strict: bool = True) -> list[dict[str, str]]:
    out = []
    for d, nav, burn, days, method in REAL_ROWS_0907_0921:
        if upto is not None and ((d >= upto) if strict else (d > upto)):
            continue
        out.append({"date": d, "nav_jpy": str(nav), "burn_per_day_jpy": str(burn),
                    "days_to_floor": str(days), "floor_date_est": "", "method": method})
    return out


# ── 1. 安定性 (実 CSV 入力) ──────────────────────────────────────────

def test_decomposed_stable_within_10pct_on_real_0915_0921_but_fit_is_not():
    fits, decs = [], []
    for day in range(15, 22):
        asof = date(2026, 9, day)
        rows = _rows(upto=asof.isoformat())
        fitted = nfp.fit_burn_per_day(rows)
        fits.append(fitted if fitted is not None else nfp.DEFAULT_BURN_PER_DAY)
        decs.append(nfp.decomposed_burn_per_day(rows, 275517.0, asof, KEEPER_0922)["burn"])
    mean_dec = sum(decs) / len(decs)
    assert all(abs(x - mean_dec) / mean_dec <= 0.10 for x in decs), decs
    # fit は同じ入力で 1.5 倍以上動く (82.0 → 48.7、CSV 記録では 74.8 → 40.4)
    assert max(fits) / min(fits) > 1.10, fits
    # keeper のみ (edge は窓不足で unavailable) = 26 × ¥80 ÷ 30.44
    assert mean_dec == pytest.approx(26 * 80.0 / 30.44, rel=1e-6)


def test_decomposed_edge_unavailable_is_labelled_not_silent_zero():
    rows = _rows(upto="2026-09-21")
    dec = nfp.decomposed_burn_per_day(rows, 275517.0, date(2026, 9, 21), KEEPER_0922)
    assert dec["edge"] == 0.0
    assert dec["edge_basis"].startswith("unavailable:")


# ── 2. counterfactual: primary は decomposed、fit は参考列 ──────────────

def test_days_to_floor_column_is_decomposed_not_fit(tmp_path):
    csv_path = tmp_path / "nav.csv"
    nfp.append_row(276304.0, asof=date(2026, 9, 7), path=csv_path, keeper=KEEPER_0922)
    # 実 CSV の 09-07〜09-19 行を書き込んだ状態を再現 (append_row を順に叩く)
    for d, nav, *_ in REAL_ROWS_0907_0921[1:-1]:
        nfp.append_row(float(nav), asof=date.fromisoformat(d), path=csv_path,
                       keeper=KEEPER_0922)
    row = nfp.append_row(275517.0, asof=date(2026, 9, 21), path=csv_path,
                         keeper=KEEPER_0922)
    assert row["method"] == "decomposed"
    dec = float(row["burn_per_day_jpy"])
    fit = float(row["burn_fit_per_day_jpy"])
    assert dec == pytest.approx(68.3, abs=0.05)
    assert fit == pytest.approx(48.7, abs=0.05)  # 参考列に fit が生きている
    assert int(row["days_to_floor"]) == nfp.project(275517.0, dec, date(2026, 9, 21))[0]
    assert int(row["days_to_floor_fit"]) == nfp.project(275517.0, fit, date(2026, 9, 21))[0]
    # primary を fit に戻すと days_to_floor が 197 → 277 に動く = ここで落ちる
    assert int(row["days_to_floor"]) != int(row["days_to_floor_fit"])
    assert int(row["days_to_floor"]) == 197


def test_legacy_six_columns_unchanged_and_first_in_header(tmp_path):
    assert nfp.FIELDNAMES[:6] == ["date", "nav_jpy", "burn_per_day_jpy",
                                  "days_to_floor", "floor_date_est", "method"]
    csv_path = tmp_path / "nav.csv"
    nfp.append_row(275517.0, asof=date(2026, 9, 22), path=csv_path, keeper=KEEPER_0922)
    header = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header[:6] == nfp.FIELDNAMES[:6]
    assert "burn_fit_per_day_jpy" in header and "edge_basis" in header


# ── 3. keeper 分 (決定論) ──────────────────────────────────────────

def test_keeper_rt_per_month_from_telemetry_and_fallback():
    assert nfp.keeper_rt_per_month(KEEPER_0922) == (26, "api")
    # 月初 (rt_count 3、volume 60k) でも per-RT 出来高から 26 が出る
    assert nfp.keeper_rt_per_month({"target_usd": 520000.0, "volume_usd": 60000.0,
                                    "rt_count": 3}) == (26, "api")
    assert nfp.keeper_rt_per_month(None) == (nfp.KEEPER_RT_PER_MONTH_DEFAULT, "default")
    assert nfp.keeper_rt_per_month({"target_usd": 520000.0, "volume_usd": 0.0,
                                    "rt_count": 0}) == (26, "default")
    assert nfp.keeper_burn_per_day(26) == pytest.approx(2080.0 / 30.44)


# ── 4. edge 分 (NAV Δ 残差) ────────────────────────────────────────

def _synthetic_rows(start: date, days: int, nav0: float, drift: float,
                    keeper_drops: dict[date, float]) -> tuple[list[dict[str, str]], float]:
    rows, nav = [], nav0
    for i in range(days):
        d = start + timedelta(days=i)
        nav -= drift + keeper_drops.get(d, 0.0)
        rows.append({"date": d.isoformat(), "nav_jpy": f"{nav:.0f}"})
    return rows, nav


def test_edge_burn_recovers_drift_after_keeper_deduction():
    # 10-01〜10-09 に 26 RT × ¥80 = ¥2,080、加えて毎日 ¥13.7 の edge drift
    drops = {date(2026, 10, d): 3 * 80.0 for d in range(1, 9)}
    drops[date(2026, 10, 9)] = 2 * 80.0
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 45, 280_000.0, 13.7, drops)
    asof = date(2026, 10, 30)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    burn, basis = nfp.edge_burn_per_day(rows[:-1], nav_now, asof, keeper, 26)
    assert burn == pytest.approx(13.7, abs=0.6), basis  # 整数丸めの分だけ許容
    assert basis.startswith("nav_delta:") and "keeper_rt_in_window=26" in basis
    # keeper を差し引かないと drift が 3 倍以上に見える — 差し引きが効いている証拠
    naive = -(nav_now - float(rows[0]["nav_jpy"])) / (asof - date(2026, 9, 15)).days
    assert naive > 13.7 * 3


def test_edge_window_never_cuts_previous_month_burst():
    # asof 10-05: 単純な 30 日窓は 09-05 に始まり 09 月 burst (〜09-14) を跨ぐ。
    # 窓開始は 09-15 に切り上がる。
    drops = {date(2026, 9, d): 3 * 80.0 for d in range(1, 10)}
    rows, nav_now = _synthetic_rows(date(2026, 8, 20), 46, 280_000.0, 0.0, drops)
    asof = date(2026, 10, 5)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 240000.0,
              "rt_count": 12, "last_rt_at": "2026-10-04T01:00:00+00:00"}
    # 当月 12 RT 分 (¥960) を 10-01〜10-04 に落とす
    nav_now -= 960.0
    rows.append({"date": "2026-10-04", "nav_jpy": f"{nav_now:.0f}"})
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, keeper, 26)
    assert "nav_delta:2026-09-15->2026-10-05:20d" in basis
    assert "keeper_rt_in_window=12" in basis
    assert burn == pytest.approx(0.0, abs=0.05)


def test_edge_window_on_31st_still_covers_whole_current_month():
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 47, 280_000.0, 10.0, {})
    asof = date(2026, 10, 31)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, keeper, 26)
    assert not basis.startswith("unavailable"), basis
    assert "nav_delta:2026-09-30->2026-10-31:31d" in basis


def test_edge_unavailable_when_no_keeper_telemetry_or_young_csv():
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 40, 280_000.0, 10.0, {})
    asof = date(2026, 10, 25)
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, None, 26)
    assert burn == 0.0 and basis.startswith("unavailable:no_keeper_telemetry")
    # CSV が当月内から始まり、当月 RT の前後分割が telemetry で確定できない
    young = [r for r in rows if r["date"] >= "2026-10-03"]
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    burn, basis = nfp.edge_burn_per_day(young, nav_now, asof, keeper, 26)
    assert burn == 0.0 and basis.startswith("unavailable:keeper_split_unknown")


# ── 5. PR #285 review P2 ×2: units スケール / 月不一致 ────────────────

def test_keeper_jpy_per_rt_scales_with_configured_units_total_invariant():
    """SVK_UNITS を変えても月次 keeper 総額 (target 固定) は不変 — 単価 × RT 数。"""
    k20 = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
           "rt_count": 13}  # 20k units → 40k/RT → 13 RT
    k5 = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
          "rt_count": 52}   # 5k units → 10k/RT → 52 RT
    assert nfp.keeper_units(k20) == (20000, "api")
    assert nfp.keeper_units(k5) == (5000, "api")
    assert nfp.keeper_units(None) == (nfp.KEEPER_REF_UNITS, "default")
    assert nfp.keeper_jpy_per_rt(k20) == (pytest.approx(160.0), "api")
    assert nfp.keeper_jpy_per_rt(k5) == (pytest.approx(40.0), "api")
    assert nfp.keeper_jpy_per_rt(KEEPER_0922) == (pytest.approx(80.0), "api")
    assert nfp.keeper_jpy_per_rt(None) == (80.0, "default")
    rows = _rows(upto="2026-09-21")
    d10 = nfp.decomposed_burn_per_day(rows, 275517.0, date(2026, 10, 21), KEEPER_0922 | {"month": "2026-10"})
    d20 = nfp.decomposed_burn_per_day(rows, 275517.0, date(2026, 10, 21), k20)
    d5 = nfp.decomposed_burn_per_day(rows, 275517.0, date(2026, 10, 21), k5)
    assert (d20["rt_per_month"], d20["jpy_per_rt"]) == (13, pytest.approx(160.0))
    assert (d5["rt_per_month"], d5["jpy_per_rt"]) == (52, pytest.approx(40.0))
    # 既知 NG 入力: 単価固定 ¥80 だと 20k で 13×80 = ¥1,040/月 に半減する (review 指摘値)
    assert d20["keeper"] == pytest.approx(2080.0 / 30.44)
    assert d5["keeper"] == pytest.approx(2080.0 / 30.44)
    assert d10["keeper"] == pytest.approx(2080.0 / 30.44)
    assert nfp.keeper_burn_per_day(13, 80.0) == pytest.approx(1040.0 / 30.44)  # 修正前の値


def test_edge_deduction_uses_scaled_jpy_per_rt():
    # 20k units、10-01〜10-05 に 13 RT × ¥160 = ¥2,080、drift 10/日
    drops = {date(2026, 10, d): 3 * 160.0 for d in range(1, 5)}
    drops[date(2026, 10, 5)] = 160.0
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 45, 280_000.0, 10.0, drops)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 13, "last_rt_at": "2026-10-05T01:00:00+00:00"}
    dec = nfp.decomposed_burn_per_day(rows[:-1], nav_now, date(2026, 10, 30), keeper)
    assert dec["edge_basis"].startswith("nav_delta:") and "keeper_rt_in_window=13" in dec["edge_basis"]
    assert dec["edge"] == pytest.approx(10.0, abs=0.6), dec
    # 単価を ¥80 固定にすると keeper 差し引きが半分になり drift が ¥1,040/窓 分過大に見える
    wrong = nfp.decomposed_burn_per_day(rows[:-1], nav_now, date(2026, 10, 30), keeper,
                                        jpy_per_rt=80.0)
    assert wrong["edge"] > dec["edge"] + 20


def test_edge_unavailable_when_keeper_month_differs_from_asof():
    """UTC 月替わり 00:00 cron: keeper loop が _roll_counters を呼ぶ前は前月 telemetry。"""
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 47, 280_000.0, 0.0, {})
    asof = date(2026, 11, 1)
    stale = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
             "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    assert nfp.keeper_month_mismatch(stale, asof) == "keeper_month_mismatch(2026-10!=2026-11)"
    assert nfp.keeper_month_mismatch(stale, date(2026, 10, 31)) is None
    assert nfp.keeper_month_mismatch({"target_usd": 520000.0}, asof).startswith("keeper_month_unknown")
    dec = nfp.decomposed_burn_per_day(rows, nav_now, asof, stale)
    assert dec["edge"] == 0.0
    assert dec["edge_basis"].startswith("unavailable:keeper_month_mismatch(2026-10!=2026-11)")
    assert dec["burn"] == pytest.approx(dec["keeper"])  # keeper burn は打ち消されない
    # RT 数 (比) は前月 telemetry でも有効 — keeper 分は default に落ちない
    assert (dec["rt_per_month"], dec["rt_basis"]) == (26, "api")
    # 既知 NG 入力: month を見ずに前月 rt_count 26 を当月支出とすると
    # edge = −(0 + 26×80)/span < 0 で keeper 分 (+68.3) を打ち消す
    e_wrong, _ = nfp.edge_burn_per_day(rows, nav_now, asof, stale | {"month": "2026-11"}, 26)
    assert e_wrong < 0 and abs(e_wrong) > 0.9 * dec["keeper"]
    # 当月 telemetry (roll 後、rt_count 0) が来れば edge は測れる
    fresh = {"month": "2026-11", "target_usd": 520000.0, "volume_usd": 0.0,
             "rt_count": 0, "last_rt_at": ""}
    dec2 = nfp.decomposed_burn_per_day(rows, nav_now, asof, fresh)
    assert dec2["edge_basis"].startswith("nav_delta:") and "keeper_rt_in_window=0" in dec2["edge_basis"]
    assert dec2["edge"] == pytest.approx(0.0, abs=0.05)


# ── 6. 失敗の露出 (tool exit 1 + cron 側) ────────────────────────────

def test_main_exits_1_and_writes_no_row_when_api_down(monkeypatch, tmp_path, capsys):
    csv_path = tmp_path / "nav.csv"
    monkeypatch.setattr(nfp, "CSV_PATH", csv_path)
    monkeypatch.setattr(nfp, "fetch_status", lambda *a, **k: None)
    rc = nfp.main(["--append"])
    assert rc == 1
    assert not csv_path.exists()
    assert "取得不能" in capsys.readouterr().out


def test_main_writes_decomposed_row_from_status_payload(monkeypatch, tmp_path):
    csv_path = tmp_path / "nav.csv"
    monkeypatch.setattr(nfp, "CSV_PATH", csv_path)
    payload = {"oanda": {"heartbeat": {"nav": str(NAV_0922)}},
               "status_volume_keeper": KEEPER_0922}
    monkeypatch.setattr(nfp, "fetch_status", lambda *a, **k: payload)
    # append_row は CSV_PATH を既定引数で束縛しているので path を差し替えて呼ぶ
    monkeypatch.setattr(nfp, "append_row",
                        lambda nav, asof=None, path=None, keeper=None:
                        nfp.build_row(nav, asof, [], keeper))
    assert nfp.main(["--append"]) == 0


def test_daily_report_workflow_exposes_nav_floor_step_outcome():
    """continue-on-error で緑になる step の失敗を Notify が Discord に出す。"""
    wf = (ROOT / ".github" / "workflows" / "daily-report.yml").read_text(encoding="utf-8")
    assert "id: nav-floor" in wf
    assert "steps.nav-floor.outcome" in wf
    assert "nav_floor writer FAILED" in wf


# ── 7. registry F4: 方法変更を記録、condition 不変 ───────────────────

def test_registry_f4_message_records_decomposed_switch_condition_unchanged():
    reg = json.loads((ROOT / "knowledge-base" / "wiki" / "decisions" /
                      "prereg-trigger-registry.json").read_text(encoding="utf-8"))
    e = [t for t in reg["triggers"]
         if t["id"] == "project-falsification-f4-nav-floor-clock"][0]
    assert "decomposed" in e["message"] and "2026-09-22" in e["message"]
    vals = {c["column"]: (c["op"], c["value"]) for c in e["source"]["match"]}
    assert vals["days_to_floor"] == ("<=", 90)
    f3 = [t for t in reg["triggers"]
          if t["id"] == "project-falsification-f3-m1-durable-cell"][0]
    assert "D11" in f3["message"] and "両基準" in f3["message"]


# ── 8. 再現値 pin: decomposed 読み手の初回発火日 ─────────────────────

def _simulate_first_fire(drift: float) -> tuple[str, str]:
    """09-22 以降、keeper burst = 毎月 1〜9 日 3 RT/日、writer 毎日成功を仮定。"""
    rows = _rows()
    nav, d = NAV_0922, date(2026, 9, 22)
    rt, last_rt = 26, "2026-09-14"
    first, floor_day = None, None
    while d <= date(2027, 7, 31):
        if (d.year, d.month) != (2026, 9):
            if d.day == 1:
                rt = 0
            if 1 <= d.day <= 9 and rt < 26:
                n = min(3, 26 - rt)
                nav -= n * 80.0
                rt += n
                last_rt = d.isoformat()
        nav -= drift
        keeper = {"month": d.strftime("%Y-%m"), "target_usd": 520000.0,
                  "volume_usd": rt * 20000.0, "rt_count": rt, "last_rt_at": last_rt}
        row = nfp.build_row(nav, d, rows, keeper)
        rows.append(row)
        if first is None and int(row["days_to_floor"]) <= 90:
            first = d.isoformat()
        if floor_day is None and nav <= nfp.FLOOR_JPY:
            floor_day = d.isoformat()
        d += timedelta(days=1)
    return first, floor_day


def test_reproduced_fire_dates_keeper_only_and_with_drift():
    assert _simulate_first_fire(0.0) == ("2027-01-05", "2027-04-05")
    assert _simulate_first_fire(13.7) == ("2026-12-04", "2027-03-04")
