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
13. (PR #285 review P2 5 巡目) 当月 RT ゼロでも target_usd が読めれば既定 units で
   割る (target_default_units)。固定 26 は target も読めない telemetry のみ。
12. (PR #285 review P2 4 巡目) enabled:false (STATUS_VOLUME_KEEPER_ENABLE=0) /
   target_usd==0 は計画 RT 0 (default 26 を当てない)。両成分未測定の行は burn 0 →
   sentinel に折り畳まず fit_fallback で露出。
11. (PR #285 review P2 3 巡目) CSV が当月内から始まる窓では last_rt_at で前後分割
   しない (回収 RT は last_rt_at を更新しない) — rt_count==0 のみ確定、他は unavailable。
10. (PR #285 review P2 2 巡目) 月次 RT 数は worker の stop rule (volume>=target
   で停止、届かなければ丸ごと 1 RT) と同じ ceil(target/per_rt)。round は 8,000u で 1 RT 過小。
9. (PR #285 review P2 ×2) keeper ¥/RT は telemetry の units で線形スケール
   (SVK_UNITS 20k/5k で月次総額不変、RT 数×単価が反比例) / telemetry の month が
   asof と違う (UTC 月替わり 00:00 cron) 間は edge を unavailable にし、前月
   rt_count で keeper burn を打ち消さない。既知 NG 入力で pin。
14. (2026-09-23 rule:R3) 入出金 (OANDA TRANSFER_FUNDS) は edge に不可視 — 台帳を差し引けば
   burn は入金 ¥100k / 出金 ¥50k の有無で不変、窓に入る日も抜ける日も跳ねない。台帳なし
   (None) は unavailable (ゼロと偽らない)。窓の両端は NAV 採取時刻で判定、時刻の無い
   legacy 端の同日 tx は unavailable (両端対称)。既知 NG 入力 (台帳を見ない) で sentinel を pin。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
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
    # 当月 RT ゼロでも target は読める → 既定 units で割る (固定 26 ではない)
    assert nfp.keeper_rt_per_month({"target_usd": 520000.0, "volume_usd": 0.0,
                                    "rt_count": 0}) == (26, "target_default_units")
    assert nfp.keeper_burn_per_day(26) == pytest.approx(2080.0 / 30.44)


def test_keeper_rt_per_month_is_ceiling_like_the_worker_stop_rule():
    """worker は毎 RT 前に volume>=target を見て止まる → 実行数 = ceil(target/per_rt)。
    (PR #285 review P2 2 巡目) 8,000u: 520000/16000 = 32.5 → 33。round (銀行丸め) は 32。"""
    k8 = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 16000.0 * 5, "rt_count": 5}
    assert nfp.keeper_rt_per_month(k8) == (33, "api")
    assert round(520000 / 16000) == 32  # 既知 NG 入力: 修正前の値
    # 割り切れる場合は不変 (10k: 26 / 20k: 13)。端数 1 単位でも 1 RT 増える
    assert nfp.keeper_rt_per_month({"target_usd": 520000.0, "volume_usd": 20000.0, "rt_count": 1}) == (26, "api")
    assert nfp.keeper_rt_per_month({"target_usd": 520001.0, "volume_usd": 20000.0, "rt_count": 1}) == (27, "api")
    # worker 挙動と一致することを stop rule の直接シミュレーションで確認
    vol, n = 0.0, 0
    while vol < 520000.0:
        vol += 16000.0; n += 1
    assert n == 33


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
    burn, basis = nfp.edge_burn_per_day(rows[:-1], nav_now, asof, keeper, transfers=[])
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
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, keeper, transfers=[])
    assert "nav_delta:2026-09-15->2026-10-05:20d" in basis
    assert "keeper_rt_in_window=12" in basis
    assert burn == pytest.approx(0.0, abs=0.05)


def test_edge_window_on_31st_still_covers_whole_current_month():
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 47, 280_000.0, 10.0, {})
    asof = date(2026, 10, 31)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, keeper, transfers=[])
    assert not basis.startswith("unavailable"), basis
    assert "nav_delta:2026-09-30->2026-10-31:31d" in basis


def test_edge_unavailable_when_no_keeper_telemetry_or_young_csv():
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 40, 280_000.0, 10.0, {})
    asof = date(2026, 10, 25)
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, None, transfers=[])
    assert burn == 0.0 and basis.startswith("unavailable:no_keeper_telemetry")
    # CSV が当月内から始まり、当月 RT の前後分割が telemetry で確定できない
    young = [r for r in rows if r["date"] >= "2026-10-03"]
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    burn, basis = nfp.edge_burn_per_day(young, nav_now, asof, keeper, transfers=[])
    assert burn == 0.0 and basis.startswith("unavailable:keeper_split_unknown")


def test_young_window_completed_month_with_old_last_rt_is_still_unknown():
    """(PR #285 review P2 3 巡目) 回収 RT (_recover_stale_trades) は rt_count を増やすが
    last_rt_at を更新しない → 「last_rt_at ≤ 窓開始 ∧ 当月完了」は窓内 RT 不在の証明でない。
    既知 NG 入力: 修正前は keeper_rt_in_window=0 で回収 RT の損失が edge に転嫁されていた。"""
    rows, nav_now = _synthetic_rows(date(2026, 10, 12), 14, 280_000.0, 0.0, {})
    nav_now -= 160.0  # 10-20 に回収 RT 1 本 (spread 損 ¥80 + 逆行 ¥80) が窓内に落ちた
    rows.append({"date": "2026-10-25", "nav_jpy": f"{nav_now:.0f}"})
    asof = date(2026, 10, 26)
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}  # 回収分は時刻なし
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, keeper, transfers=[])
    assert burn == 0.0 and basis.startswith("unavailable:keeper_split_unknown"), basis
    # 当月 RT ゼロ (rt_count 0) なら窓内 keeper 支出 0 と確定できる
    fresh = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 0.0,
             "rt_count": 0, "last_rt_at": ""}
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, fresh, transfers=[])
    assert basis.startswith("nav_delta:") and "keeper_rt_in_window=0" in basis
    assert burn == pytest.approx(160.0 / 14, abs=0.05)


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
    dec = nfp.decomposed_burn_per_day(rows[:-1], nav_now, date(2026, 10, 30), keeper, transfers=[])
    assert dec["edge_basis"].startswith("nav_delta:") and "keeper_rt_in_window=13" in dec["edge_basis"]
    assert dec["edge"] == pytest.approx(10.0, abs=0.6), dec
    # 単価を ¥80 固定にすると keeper 差し引きが半分になり drift が ¥1,040/窓 分過大に見える
    wrong = nfp.decomposed_burn_per_day(rows[:-1], nav_now, date(2026, 10, 30), keeper,
                                        jpy_per_rt=80.0, transfers=[])
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
    dec = nfp.decomposed_burn_per_day(rows, nav_now, asof, stale, transfers=[])
    assert dec["edge"] == 0.0
    assert dec["edge_basis"].startswith("unavailable:keeper_month_mismatch(2026-10!=2026-11)")
    assert dec["burn"] == pytest.approx(dec["keeper"])  # keeper burn は打ち消されない
    # RT 数 (比) は前月 telemetry でも有効 — keeper 分は default に落ちない
    assert (dec["rt_per_month"], dec["rt_basis"]) == (26, "api")
    # 既知 NG 入力: month を見ずに前月 rt_count 26 を当月支出とすると
    # edge = −(0 + 26×80)/span < 0 で keeper 分 (+68.3) を打ち消す
    e_wrong, _ = nfp.edge_burn_per_day(rows, nav_now, asof, stale | {"month": "2026-11"}, transfers=[])
    assert e_wrong < 0 and abs(e_wrong) > 0.9 * dec["keeper"]
    # 当月 telemetry (roll 後、rt_count 0) が来れば edge は測れる
    fresh = {"month": "2026-11", "target_usd": 520000.0, "volume_usd": 0.0,
             "rt_count": 0, "last_rt_at": ""}
    dec2 = nfp.decomposed_burn_per_day(rows, nav_now, asof, fresh, transfers=[])
    assert dec2["edge_basis"].startswith("nav_delta:") and "keeper_rt_in_window=0" in dec2["edge_basis"]
    assert dec2["edge"] == pytest.approx(0.0, abs=0.05)


def test_fallback_trips_follow_reported_target_before_first_trip():
    """(PR #285 review P2 5 巡目) SVK_MONTHLY_TARGET_USD は可変。月初 (volume=rt_count=0)
    に固定 26 を当てると $260k 設定で keeper burn が 2 倍に見える。既知 NG 入力で pin。"""
    k260 = {"month": "2026-10", "target_usd": 260000.0, "volume_usd": 0.0, "rt_count": 0,
            "last_rt_at": ""}
    assert nfp.keeper_rt_per_month(k260) == (13, "target_default_units")
    assert nfp.KEEPER_RT_PER_MONTH_DEFAULT == 26  # 修正前はこれが返っていた
    # 端数は切り上げ (worker stop rule と同じ)
    assert nfp.keeper_rt_per_month({"target_usd": 250000.0, "volume_usd": 0, "rt_count": 0}) == (13, "target_default_units")
    # 固定 26 は target が読めない telemetry のみ
    assert nfp.keeper_rt_per_month({"enabled": True, "running": False}) == (26, "default")
    assert nfp.keeper_rt_per_month({"target_usd": "n/a"}) == (26, "default")
    # 初 RT 後は観測 per-RT 出来高 (api) に切り替わり、10k units なら値は連続
    assert nfp.keeper_rt_per_month(k260 | {"volume_usd": 20000.0, "rt_count": 1}) == (13, "api")
    dec = nfp.decomposed_burn_per_day(_rows(upto="2026-09-21"), 275517.0, date(2026, 10, 1), k260)
    assert dec["keeper"] == pytest.approx(13 * 80.0 / 30.44)


def test_disabled_keeper_projects_zero_planned_trips_not_default_26(tmp_path):
    """(PR #285 review P2 4 巡目) STATUS_VOLUME_KEEPER_ENABLE=0 の get_worker_status payload。"""
    disabled = {"enabled": False, "running": False, "note": "worker not started in this process"}
    assert nfp.keeper_disabled(disabled) and not nfp.keeper_disabled(KEEPER_0922)
    assert not nfp.keeper_disabled(None)
    assert nfp.keeper_rt_per_month(disabled) == (0, "disabled")
    assert nfp.keeper_rt_per_month({"enabled": True, "running": False}) == (26, "default")
    assert nfp.keeper_rt_per_month({"month": "2026-10", "target_usd": 0.0, "volume_usd": 0.0,
                                    "rt_count": 0}) == (0, "target_zero")
    rows = _rows(upto="2026-09-21")
    dec = nfp.decomposed_burn_per_day(rows, 275517.0, date(2026, 9, 21), disabled)
    assert dec["keeper"] == 0.0 and dec["rt_basis"] == "disabled"
    assert dec["edge_basis"].startswith("unavailable:keeper_disabled")
    # 既知 NG 入力: 修正前は default 26 × ¥80 / 30.44 = 68.3/日 が乗っていた
    assert dec["burn"] == 0.0 and dec["burn"] != pytest.approx(26 * 80.0 / 30.44)
    # 両成分未測定の行は sentinel 99999 に折り畳まず fit (行不足なら audit default) へ
    csv_path = tmp_path / "nav.csv"
    for d, nav, *_ in REAL_ROWS_0907_0921:
        nfp.append_row(float(nav), asof=date.fromisoformat(d), path=csv_path, keeper=disabled)
    row = nfp.read_rows(csv_path)[-1]
    assert row["method"] == "fit_fallback"
    assert row["burn_per_day_jpy"] == row["burn_fit_per_day_jpy"]
    assert int(row["days_to_floor"]) == int(row["days_to_floor_fit"]) != nfp.DAYS_SENTINEL_NO_BURN
    assert row["burn_keeper_per_day_jpy"] == "0.0"
    # 通常 (keeper 有効) 行は decomposed のまま
    row2 = nfp.append_row(275517.0, asof=date(2026, 9, 22), path=csv_path, keeper=KEEPER_0922)
    assert row2["method"] == "decomposed"


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
    monkeypatch.setattr(nfp, "fetch_transfers", lambda *a, **k: [])  # 台帳 0 件 (network 遮断)
    # append_row は CSV_PATH を既定引数で束縛しているので path を差し替えて呼ぶ
    monkeypatch.setattr(nfp, "append_row",
                        lambda nav, asof=None, path=None, keeper=None, transfers=None, nav_ts=None:
                        nfp.build_row(nav, asof, [], keeper, transfers=transfers, nav_ts=nav_ts))
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
        row = nfp.build_row(nav, d, rows, keeper, transfers=[])  # 入出金ゼロ前提
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


# ── 14. 入出金 (OANDA TRANSFER_FUNDS) は edge に不可視 (2026-09-23、rule:R3) ────
# 欠陥: edge_jpy = (nav_now − nav_start) + keeper 窓内支出 は broker NAV Δ の残差で、
# 入出金の調整が無かった (repo 全体で TRANSFER_FUNDS 参照 0 件)。入金 ¥D が窓に入ると
# burn_edge が負に転じ合計 burn ≤ 0 → project() が sentinel 99999 → F4 が最長 30 日
# 発火不能、窓を抜けると逆方向に跳ねる。pin は性質 (台帳を差し引けば burn は入出金の
# 有無で不変) で書く。


def _tx(amount: float, when: str, typ: str = "TRANSFER_FUNDS", tid: str = "900001") -> dict:
    """OANDA v20 TransferFundsTransaction の最小形 (time は ns 精度 Z 表記)。"""
    return {"id": tid, "type": typ, "amount": f"{amount:.4f}", "time": when,
            "fundingReason": "CLIENT_FUNDING" if amount > 0 else "CLIENT_WITHDRAWAL",
            "accountBalance": "0.0000"}


_KEEPER_OCT_NO_RT = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 0.0,
                     "rt_count": 0, "last_rt_at": ""}


def _drift_rows_oct30() -> tuple[list[dict[str, str]], float, date]:
    rows, nav_now = _synthetic_rows(date(2026, 9, 15), 45, 280_000.0, 10.0, {})
    return rows, nav_now, date(2026, 10, 30)  # 窓 09-30 → 10-30 (30d)、drift 10/日


def test_deposit_inside_window_is_invisible_to_edge_burn():
    rows, nav_now, asof = _drift_rows_oct30()
    base, base_basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[])
    assert base == pytest.approx(10.0, abs=0.6) and base_basis.startswith("nav_delta:")
    deposit = _tx(100_000.0, "2026-10-10T02:00:00.000000000Z")
    with_dep, basis = nfp.edge_burn_per_day(rows, nav_now + 100_000.0, asof, _KEEPER_OCT_NO_RT,
                                            transfers=[deposit])
    assert with_dep == pytest.approx(base, abs=1e-9), basis
    assert "transfers_jpy=+100000" in basis and "n_transfers=1" in basis
    # 既知 NG 入力: 台帳を見ない (= 入出金ゼロと偽る) と入金が edge に化け burn<0 → sentinel
    blind, _ = nfp.edge_burn_per_day(rows, nav_now + 100_000.0, asof, _KEEPER_OCT_NO_RT, transfers=[])
    assert blind < 0
    assert nfp.project(nav_now + 100_000.0, blind, asof)[0] == nfp.DAYS_SENTINEL_NO_BURN
    # 台帳あり: project は入金で伸びた NAV を正しい burn で割る (sentinel ではない)
    days, _ = nfp.project(nav_now + 100_000.0, with_dep, asof)
    assert days != nfp.DAYS_SENTINEL_NO_BURN and days > nfp.project(nav_now, base, asof)[0]


def test_withdrawal_inside_window_is_invisible_to_edge_burn_symmetric():
    """対称側: 出金 (amount<0) も不可視。台帳を見ないと損失に化け F4 が偽早期発火する。"""
    rows, nav_now, asof = _drift_rows_oct30()
    base, _ = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[])
    wd = _tx(-50_000.0, "2026-10-20T05:00:00.000000000Z")
    with_wd, basis = nfp.edge_burn_per_day(rows, nav_now - 50_000.0, asof, _KEEPER_OCT_NO_RT,
                                           transfers=[wd])
    assert with_wd == pytest.approx(base, abs=1e-9), basis
    assert "transfers_jpy=-50000" in basis
    blind, _ = nfp.edge_burn_per_day(rows, nav_now - 50_000.0, asof, _KEEPER_OCT_NO_RT, transfers=[])
    assert blind > base * 50  # ¥50k/30d ≈ 1,667/日 の偽 burn


def test_edge_burn_does_not_rebound_when_deposit_leaves_window():
    """入金が窓に入る日も窓を抜けた日も burn = drift (跳ねない)。
    窓外 (start_row 以前) の入金は nav_start に含まれているので差し引かない (台帳側で日付除外)。"""
    rows, _ = _synthetic_rows(date(2026, 9, 15), 45, 280_000.0, 10.0, {})
    dep_day = date(2026, 9, 20)
    for r in rows:  # 09-20 以降の行は入金 +100k を含む NAV
        if date.fromisoformat(r["date"]) >= dep_day:
            r["nav_jpy"] = f"{float(r['nav_jpy']) + 100_000.0:.0f}"
    deposit = _tx(100_000.0, "2026-09-20T01:00:00.000000000Z")
    # (a) 入金が窓内 (asof 10-10: 窓 09-15 → 10-10、start_row は入金前)
    rows_a = [r for r in rows if r["date"] < "2026-10-10"]
    nav_a = float(rows_a[-1]["nav_jpy"]) - 10.0
    burn_a, basis_a = nfp.edge_burn_per_day(rows_a, nav_a, date(2026, 10, 10), _KEEPER_OCT_NO_RT,
                                            transfers=[deposit])
    assert basis_a.startswith("nav_delta:2026-09-15->2026-10-10") and "n_transfers=1" in basis_a
    assert burn_a == pytest.approx(10.0, abs=0.6), basis_a
    # (b) 入金が窓外 (asof 10-30: 窓 09-30 → 10-30、start_row は入金後)
    nav_b = float(rows[-1]["nav_jpy"]) - 10.0
    burn_b, basis_b = nfp.edge_burn_per_day(rows, nav_b, date(2026, 10, 30), _KEEPER_OCT_NO_RT,
                                            transfers=[deposit])
    assert basis_b.startswith("nav_delta:2026-09-30->2026-10-30") and "n_transfers=0" in basis_b
    assert burn_b == pytest.approx(10.0, abs=0.6), basis_b
    # 既知 NG (修正前の跳ね): 台帳なしだと (a) は −3,323/日、(b) は +10/日 に跳ぶ
    blind_a, _ = nfp.edge_burn_per_day(rows_a, nav_a, date(2026, 10, 10), _KEEPER_OCT_NO_RT, transfers=[])
    assert blind_a < -3000


def test_edge_unavailable_when_transfer_ledger_missing_not_silent_zero():
    """台帳取得不能 (None) は「入出金ゼロ」に折り畳まず unavailable (fail-loud)。keeper 分は残る。"""
    rows, nav_now, asof = _drift_rows_oct30()
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=None)
    assert burn == 0.0 and basis.startswith("unavailable:transfers_unavailable")
    keeper = {"month": "2026-10", "target_usd": 520000.0, "volume_usd": 520000.0,
              "rt_count": 26, "last_rt_at": "2026-10-09T01:00:00+00:00"}
    dec = nfp.decomposed_burn_per_day(rows, nav_now, asof, keeper, transfers=None)
    assert dec["edge"] == 0.0 and dec["edge_basis"].startswith("unavailable:transfers_unavailable")
    assert dec["burn"] == pytest.approx(dec["keeper"]) and dec["burn"] > 0
    # 既定引数でも同じ (省略 = 台帳未参照 = unavailable、ゼロと偽らない)
    burn2, basis2 = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT)
    assert burn2 == 0.0 and basis2.startswith("unavailable:transfers_unavailable")


def test_transfer_ledger_ignores_non_transfer_types_and_flags_malformed():
    rows, nav_now, asof = _drift_rows_oct30()
    base, _ = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[])
    # REJECT は残高を動かさない / DAILY_FINANCING は edge 側 (trade 由来) — どちらも差し引かない
    noise = [_tx(100_000.0, "2026-10-10T02:00:00.000000000Z", typ="TRANSFER_FUNDS_REJECT"),
             _tx(-12.5, "2026-10-11T21:00:00.000000000Z", typ="DAILY_FINANCING")]
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=noise)
    assert burn == pytest.approx(base, abs=1e-9) and "n_transfers=0" in basis
    # 窓内 TRANSFER_FUNDS の amount が読めない → unavailable (0 と折り畳まない)
    bad = _tx(100_000.0, "2026-10-10T02:00:00.000000000Z") | {"amount": "n/a"}
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[bad])
    assert burn == 0.0 and basis.startswith("unavailable:transfers_malformed")
    # time が読めない TRANSFER_FUNDS も窓判定不能 → unavailable
    bad_t = _tx(100_000.0, "not-a-time")
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[bad_t])
    assert burn == 0.0 and basis.startswith("unavailable:transfers_malformed")


def test_transfer_window_bounds_use_nav_timestamps_and_fail_closed_on_legacy_boundary():
    """窓の両端は NAV 採取時刻 (start_row.nav_ts_utc / nav_ts) で判定する。
    時刻の無い legacy 端に入出金が同日で載ると前後が決まらない → unavailable (両端対称)。"""
    rows, nav_now, asof = _drift_rows_oct30()
    base, _ = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[])
    # start 端 (legacy 行、時刻なし) に同日入金 → 判定不能
    on_start = _tx(100_000.0, "2026-09-30T02:00:00.000000000Z")
    burn, basis = nfp.edge_burn_per_day(rows, nav_now + 100_000.0, asof, _KEEPER_OCT_NO_RT,
                                        transfers=[on_start])
    assert burn == 0.0 and basis.startswith("unavailable:transfer_on_start_bound")
    # start 行に nav_ts_utc があれば時刻で前後を切る
    stamped = [dict(r, nav_ts_utc="2026-09-30T06:00:00+00:00") if r["date"] == "2026-09-30" else r
               for r in rows]
    before_write = _tx(100_000.0, "2026-09-30T02:00:00.000000000Z")  # nav_start に既に含まれる
    burn, basis = nfp.edge_burn_per_day(stamped, nav_now, asof, _KEEPER_OCT_NO_RT,
                                        transfers=[before_write])
    assert burn == pytest.approx(base, abs=1e-9) and "n_transfers=0" in basis
    after_write = _tx(100_000.0, "2026-09-30T08:00:00.000000000Z")  # Δ に含まれる → 差し引く
    burn, basis = nfp.edge_burn_per_day(stamped, nav_now + 100_000.0, asof, _KEEPER_OCT_NO_RT,
                                        transfers=[after_write])
    assert burn == pytest.approx(base, abs=1e-9) and "n_transfers=1" in basis
    # asof 端: nav_ts なしで同日入金 → 判定不能 / nav_ts ありなら時刻で切る
    on_asof = _tx(100_000.0, "2026-10-30T08:00:00.000000000Z")
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT, transfers=[on_asof])
    assert burn == 0.0 and basis.startswith("unavailable:transfer_on_asof_bound")
    ts = datetime(2026, 10, 30, 6, 0, tzinfo=timezone.utc)
    burn, basis = nfp.edge_burn_per_day(rows, nav_now, asof, _KEEPER_OCT_NO_RT,
                                        transfers=[on_asof], nav_ts=ts)  # 採取後の入金 = 未反映
    assert burn == pytest.approx(base, abs=1e-9) and "n_transfers=0" in basis
    early = _tx(100_000.0, "2026-10-30T02:00:00.000000000Z")
    burn, basis = nfp.edge_burn_per_day(rows, nav_now + 100_000.0, asof, _KEEPER_OCT_NO_RT,
                                        transfers=[early], nav_ts=ts)
    assert burn == pytest.approx(base, abs=1e-9) and "n_transfers=1" in basis


def test_append_row_persists_nav_timestamp_for_future_window_bounds(tmp_path):
    csv_path = tmp_path / "nav.csv"
    ts = datetime(2026, 9, 24, 0, 5, 12, tzinfo=timezone.utc)
    row = nfp.append_row(275_472.0, asof=date(2026, 9, 24), path=csv_path, keeper=KEEPER_0922
                         | {"month": "2026-09"}, transfers=[], nav_ts=ts)
    assert row["nav_ts_utc"] == ts.isoformat()
    assert nfp.FIELDNAMES[:6] == nfp.LEGACY_FIELDNAMES and "nav_ts_utc" in nfp.FIELDNAMES
    assert nfp.read_rows(csv_path)[0]["nav_ts_utc"] == ts.isoformat()


def test_main_fetches_transfer_ledger_over_window_and_exposes_unavailable(monkeypatch):
    payload = {"oanda": {"heartbeat": {"nav": str(NAV_0922), "status": "ok",
                                       "last_check": "2026-09-23T06:00:00.123456+00:00",
                                       "nav_at": "2026-09-23T06:00:00.123456+00:00"}},
               "status_volume_keeper": KEEPER_0922}
    monkeypatch.setattr(nfp, "fetch_status", lambda *a, **k: payload)
    calls, captured = [], {}
    monkeypatch.setattr(nfp, "fetch_transfers",
                        lambda app_base, d_from, d_to, timeout=30: calls.append((d_from, d_to)) or None)

    def _fake_append(nav, asof=None, path=None, keeper=None, transfers=None, nav_ts=None):
        captured.update(transfers=transfers, nav_ts=nav_ts)
        return nfp.build_row(nav, asof, [], keeper, transfers=transfers, nav_ts=nav_ts)
    monkeypatch.setattr(nfp, "append_row", _fake_append)
    assert nfp.main(["--append"]) == 0
    asof = datetime.now(timezone.utc).date()
    (d_from, d_to), = calls
    assert d_from <= asof - timedelta(days=nfp.EDGE_WINDOW_DAYS) and d_to > asof  # 窓を覆う
    assert captured["transfers"] is None  # 取得不能はそのまま渡す (ゼロと偽らない)
    assert captured["nav_ts"] == datetime(2026, 9, 23, 6, 0, 0, 123456, tzinfo=timezone.utc)


def test_fetch_transfers_returns_none_on_failure_or_bad_scheme(monkeypatch):
    assert nfp.fetch_transfers("file:///etc", date(2026, 9, 1), date(2026, 9, 2)) is None

    class _Resp:
        def __init__(self, body): self._b = body
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return self._b
    seen = {}

    def _urlopen(req, timeout=30):
        seen["url"] = req.full_url
        return _Resp(b'{"count": 1, "transactions": [{"type": "TRANSFER_FUNDS", "amount": "1.0000",'
                     b' "time": "2026-09-01T00:00:00.000000000Z", "id": "1"}]}')
    monkeypatch.setattr(nfp.urllib.request, "urlopen", _urlopen)
    got = nfp.fetch_transfers("https://x.test", date(2026, 9, 1), date(2026, 9, 3))
    assert got == [{"type": "TRANSFER_FUNDS", "amount": "1.0000",
                    "time": "2026-09-01T00:00:00.000000000Z", "id": "1"}]
    assert seen["url"] == "https://x.test/api/oanda/transfers?from=2026-09-01&to=2026-09-03"

    def _boom(req, timeout=30):
        raise OSError("down")
    monkeypatch.setattr(nfp.urllib.request, "urlopen", _boom)
    assert nfp.fetch_transfers("https://x.test", date(2026, 9, 1), date(2026, 9, 3)) is None
    # payload に transactions 配列が無い (route 変更/エラー JSON) も None
    monkeypatch.setattr(nfp.urllib.request, "urlopen", lambda req, timeout=30: _Resp(b'{"error": "x"}'))
    assert nfp.fetch_transfers("https://x.test", date(2026, 9, 1), date(2026, 9, 3)) is None


def test_transfers_reader_wiring_tool_path_matches_app_route():
    """書き手 (app.py route) と読み手 (tool の path 定数) が同じ URL を指す (write-only 教訓)。"""
    assert nfp.TRANSFERS_PATH == "/api/oanda/transfers"
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert f'@app.route("{nfp.TRANSFERS_PATH}")' in src


def test_registry_f4_message_records_transfer_funds_adjustment():
    reg = json.loads((ROOT / "knowledge-base" / "wiki" / "decisions" /
                      "prereg-trigger-registry.json").read_text(encoding="utf-8"))
    e = [t for t in reg["triggers"]
         if t["id"] == "project-falsification-f4-nav-floor-clock"][0]
    assert "TRANSFER_FUNDS" in e["message"] and "2026-09-23" in e["message"]
    vals = {c["column"]: (c["op"], c["value"]) for c in e["source"]["match"]}
    assert vals["days_to_floor"] == ("<=", 90)  # condition 不変


def test_nav_ts_comes_from_successful_nav_fetch_only():
    """(PR #295 review P2) heartbeat.last_check は失敗時も進む (nav は前回値のまま) —
    asof 端の時刻は NAV と一緒に更新される nav_at のみ。無ければ status=ok の last_check
    (同じ update で書かれる)。失敗 heartbeat の last_check は None (asof 端は日付判定 →
    同日入出金は unavailable、fail-closed)。既知 NG 入力: 障害中の payload。"""
    ok_hb = {"nav": "275472.0", "status": "ok", "last_check": "2026-09-23T06:00:00+00:00",
             "nav_at": "2026-09-23T05:59:30+00:00"}
    assert nfp.nav_ts_from_status({"oanda": {"heartbeat": ok_hb}}) == datetime(
        2026, 9, 23, 5, 59, 30, tzinfo=timezone.utc)  # nav_at 優先
    legacy_ok = {"nav": "275472.0", "status": "ok", "last_check": "2026-09-23T06:00:00+00:00"}
    assert nfp.nav_ts_from_status({"oanda": {"heartbeat": legacy_ok}}) == datetime(
        2026, 9, 23, 6, 0, tzinfo=timezone.utc)
    outage = {"nav": "275472.0", "status": "error", "error": "timeout",
              "last_check": "2026-09-23T09:00:00+00:00"}  # nav は 06:00 の値、時刻は失敗時刻
    assert nfp.nav_ts_from_status({"oanda": {"heartbeat": outage}}) is None
    assert nfp.nav_ts_from_status({"oanda": {"heartbeat": {"nav": "1", "last_check": "2026-09-23T09:00:00+00:00"}}}) is None
    # nav_at があれば障害中でも NAV の採取時刻として使える
    outage_with_nav_at = outage | {"nav_at": "2026-09-23T06:00:00+00:00"}
    assert nfp.nav_ts_from_status({"oanda": {"heartbeat": outage_with_nav_at}}) == datetime(
        2026, 9, 23, 6, 0, tzinfo=timezone.utc)


def test_main_passes_none_nav_ts_during_heartbeat_outage_not_now(monkeypatch):
    payload = {"oanda": {"heartbeat": {"nav": str(NAV_0922), "status": "error", "error": "timeout",
                                       "last_check": "2026-09-23T09:00:00+00:00"}},
               "status_volume_keeper": KEEPER_0922}
    monkeypatch.setattr(nfp, "fetch_status", lambda *a, **k: payload)
    monkeypatch.setattr(nfp, "fetch_transfers", lambda *a, **k: [])
    captured = {}

    def _fake_append(nav, asof=None, path=None, keeper=None, transfers=None, nav_ts=None):
        captured["nav_ts"] = nav_ts
        return nfp.build_row(nav, asof, [], keeper, transfers=transfers, nav_ts=nav_ts)
    monkeypatch.setattr(nfp, "append_row", _fake_append)
    assert nfp.main(["--append"]) == 0
    assert captured["nav_ts"] is None  # 失敗時刻や取得時刻で埋めない
