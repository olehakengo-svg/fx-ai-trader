"""E1 positioning pre-reg 判定ハーネスの pin テスト (§7 成果物規定)。

spec: knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md
(🔒 LOCKED)。「LOCF resampler / rank タイ規約 / DST 跨ぎ週 / ATR / join /
canary leak test を tests/ に pin してから verdict データに触れる」の pin 実体。

**全テストはオフライン・合成データのみ (§6-2)** — ネットワーク・本番 DB・
本番 positioning データへの接触は一切ない。実データへの初適用は verdict 期日
(first look 2026-10-15)。
"""
import json
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest

from tools import e1_positioning_prereg_eval as m


def utc(s):
    return m._utc(s)


# ══════════════════════════════════════════════════════════════════════
# 合成ワールド生成 (100% synthetic — §6-2)
# ══════════════════════════════════════════════════════════════════════

def make_bars(start, end, base=150.0, seed=1, sigma=0.02):
    """市場時間内のみに存在する M15 bar 列 (random walk)。"""
    t = start.replace(minute=start.minute - start.minute % 15,
                      second=0, microsecond=0)
    eps, o, h, l, c = [], [], [], [], []
    rng = np.random.default_rng(seed)
    px = base
    while t < end:
        if m.is_market_open(t):
            op = px
            cl_ = px + float(rng.normal(0, sigma))
            eps.append(t.timestamp())
            o.append(op)
            h.append(max(op, cl_) + 0.01)
            l.append(min(op, cl_) - 0.01)
            c.append(cl_)
            px = cl_
        t += timedelta(seconds=900)
    return m.bars_from_arrays(np.array(eps), np.array(o), np.array(h),
                              np.array(l), np.array(c))


def make_snapshot_rows(pair, grid, base_px, phase, seed):
    """20 分グリッドに沿った合成 outlook snapshot 行 (sin + noise の skew)。"""
    rows = []
    rng = np.random.default_rng(seed)
    for i, t in enumerate(grid):
        skew = 45.0 * math.sin(2 * math.pi * i / 720.0 + phase) \
            + float(rng.normal(0, 3))
        skew = max(-49.0, min(49.0, skew))
        long_pct = 50.0 + skew / 2.0
        rows.append({
            "instrument": pair, "book_type": "outlook",
            "snapshot_time": m._iso(t - timedelta(seconds=300)),
            "pct_long_total": round(long_pct, 4),
            "pct_short_total": round(100.0 - long_pct, 4),
            "buckets": {"avgLongPrice": base_px - 0.1,
                        "avgShortPrice": base_px + 0.1},
        })
    return rows


def simple_rows(pairs_ep_long):
    """resample_locf 直呼び用の instrument 行列。[(ep, long), ...]"""
    eps = np.array([e for e, _ in pairs_ep_long], dtype=float)
    longs = np.array([v for _, v in pairs_ep_long], dtype=float)
    return {"ep": eps, "long": longs, "short": 100.0 - longs,
            "avg_long": np.full(len(eps), np.nan),
            "avg_short": np.full(len(eps), np.nan)}


# ══════════════════════════════════════════════════════════════════════
# 市場時間 / DST (§2.2 M11 pin)
# ══════════════════════════════════════════════════════════════════════

class TestMarketHours:
    def test_dst_transition_week_2026_11_01(self):
        """DST 跨ぎ週: 2026-11-01 (US DST 終了) 前後で市場時間が 1h シフト。"""
        # 夏時間 (EDT、UTC−4): Fri close = 21:00 UTC
        assert m.is_market_open(utc("2026-10-30T20:59:00Z"))
        assert not m.is_market_open(utc("2026-10-30T21:00:00Z"))
        # DST 終了当日の日曜: 21:00 UTC = 16:00 EST → まだ closed、22:00 で open
        assert not m.is_market_open(utc("2026-11-01T21:00:00Z"))
        assert m.is_market_open(utc("2026-11-01T22:00:00Z"))
        # 冬時間 (EST、UTC−5): Fri close = 22:00 UTC
        assert m.is_market_open(utc("2026-11-06T21:30:00Z"))
        assert not m.is_market_open(utc("2026-11-06T22:00:00Z"))

    def test_grid_excludes_weekend_and_follows_dst(self):
        g = m.build_grid(utc("2026-10-30T20:00:00Z"),
                         utc("2026-11-01T23:00:00Z"))
        isos = [m._iso(t) for t in g]
        assert "2026-10-30T20:40:00Z" in isos          # EDT close 直前
        assert "2026-10-30T21:00:00Z" not in isos      # EDT close ちょうど
        k = isos.index("2026-10-30T20:40:00Z")
        assert isos[k + 1] == "2026-11-01T22:00:00Z"   # EST open (1h シフト)
        assert all(t.weekday() != 5 for t in g)        # 土曜スロットなし

    def test_market_seconds_across_weekend(self):
        a = utc("2026-07-17T20:00:00Z")   # Fri 16:00 EDT
        b = utc("2026-07-19T22:00:00Z")   # Sun 18:00 EDT
        assert m.market_seconds_between(a, b) == pytest.approx(2 * 3600)

    def test_trading_day_ny17_roll(self):
        assert m.trading_day(utc("2026-07-08T20:59:00Z")) == date(2026, 7, 8)
        assert m.trading_day(utc("2026-07-08T21:00:00Z")) == date(2026, 7, 9)


# ══════════════════════════════════════════════════════════════════════
# LOCF resampler (§2.2 pin)
# ══════════════════════════════════════════════════════════════════════

class TestLocfResampler:
    def test_locf_60s_margin(self):
        """snapshot_time ≤ t − 60s のみ有効。t−59s の行は使わない。"""
        t = utc("2026-07-15T12:00:00Z")   # Wed
        ep = t.timestamp()
        rows = simple_rows([(ep - 61, 60.0), (ep - 59, 70.0)])
        p = m.resample_locf({"P": rows}, {"P": [ep - 61, ep - 59]},
                            [ep - 59], [t])
        assert p["P"]["valid"][0]
        assert p["P"]["long"][0] == pytest.approx(60.0)

    def test_stale_cap_uses_verified_age_not_row_age(self):
        t = utc("2026-07-15T12:00:00Z")
        ep = t.timestamp()
        # (a) 行は 26h 前だが verified 10 分前 → LOCF 無期限有効 (§2.2 主モード)
        rows = simple_rows([(ep - 26 * 3600, 55.0)])
        p = m.resample_locf({"P": rows}, {"P": [ep - 26 * 3600, ep - 600]},
                            [ep - 600], [t])
        assert p["P"]["valid"][0]
        assert p["P"]["long"][0] == pytest.approx(55.0)
        # (b) 行はあるが最終 verified 3h 前 (>2h 市場時間) → NA
        p2 = m.resample_locf({"P": rows}, {"P": [ep - 3 * 3600]},
                             [ep - 600], [t])
        assert not p2["P"]["valid"][0]
        assert p2["stats"]["P"]["na_stale"] == 1

    def test_stale_cap_age_is_market_time_across_weekend(self):
        """金曜 16:30 NY verified → 日曜 17:20 NY スロット: 壁時計 ~49h でも
        市場時間 age は 50 分 → 有効 (§2.2 market-time age)。"""
        ver = utc("2026-07-17T20:30:00Z")   # Fri 16:30 EDT
        t = utc("2026-07-19T21:20:00Z")     # Sun 17:20 EDT
        ep_v, ep_t = ver.timestamp(), t.timestamp()
        rows = simple_rows([(ep_v, 62.0)])
        p = m.resample_locf({"P": rows}, {"P": [ep_v]}, [ep_v], [t])
        assert p["P"]["valid"][0]
        assert p["P"]["long"][0] == pytest.approx(62.0)
        assert ep_t - ep_v > 40 * 3600      # 壁時計では 2h を大きく超えている

    def test_locf_across_dst_transition_week_2026_11_01(self):
        """§2.2 M11: LOCF resampler の DST 跨ぎ週 (2026-11-01 EDT→EST) pin。

        金曜 EDT close (21:00 UTC) 直前の verified → 日曜 EST open (22:00 UTC)
        直後のスロット: 壁時計 ~50h でも市場時間 age は週末で凍結され、
        1h シフトを跨いで正しく計測される。"""
        # Fri 2026-10-30 16:30 EDT (= 20:30 UTC) verified、close まで 30 分
        ver = utc("2026-10-30T20:30:00Z")
        # Sun 2026-11-01 EST open (22:00 UTC) + 20 分のスロット
        t_ok = utc("2026-11-01T22:20:00Z")
        assert m.is_market_open(t_ok)
        ep_v = ver.timestamp()
        rows = simple_rows([(ep_v, 64.0)])
        p = m.resample_locf({"P": rows}, {"P": [ep_v]}, [ep_v], [t_ok])
        # age = Fri 30min + Sun 20min = 50min (市場時間) < 2h → LOCF 有効
        assert p["P"]["valid"][0]
        assert p["P"]["long"][0] == pytest.approx(64.0)
        assert t_ok.timestamp() - ep_v > 40 * 3600      # 壁時計は 2h を大幅超過
        # 対照: verified が Fri 13:30 EDT (17:30 UTC) → Fri 残 3.5h > 2h → NA
        ver2 = utc("2026-10-30T17:30:00Z")
        rows2 = simple_rows([(ver2.timestamp(), 64.0)])
        p2 = m.resample_locf({"P": rows2}, {"P": [ver2.timestamp()]},
                             [ep_v], [t_ok])
        assert not p2["P"]["valid"][0]
        assert p2["stats"]["P"]["na_stale"] == 1
        # 遷移週の Sun open 側スロットちょうど (22:00 UTC = EST 17:00) も
        # grid に存在し LOCF が効く (EDT 定義のままなら 21:00 と誤る)
        t_open = utc("2026-11-01T22:00:00Z")
        p3 = m.resample_locf({"P": rows}, {"P": [ep_v]}, [ep_v], [t_open])
        assert p3["P"]["valid"][0]

    def test_cycle_evidence_window_half_open(self):
        """cycle 証跡 (t−90min, t]: 証跡なし → 全ペア NA。境界ちょうど
        90min は窓の外 (半開)。"""
        t = utc("2026-07-15T12:00:00Z")
        ep = t.timestamp()
        rows = simple_rows([(ep - 2 * 3600, 60.0)])
        # 全証跡 (行 + verified + heartbeat) が 2h 前 → cycle fail
        p = m.resample_locf({"P": rows}, {"P": [ep - 2 * 3600]},
                            [ep - 2 * 3600], [t])
        assert not p["cycle_ok"][0]
        assert p["stats"]["P"]["na_cycle"] == 1
        # 境界: 証跡ちょうど 90min 前 → 窓外 → fail
        p2 = m.resample_locf({"P": rows}, {"P": [ep - 2 * 3600]},
                             [ep - 5400], [t])
        assert not p2["cycle_ok"][0]
        # 89min 前 → 窓内 → 稼働 (stale cap は verified 2h 前 = 有効)
        p3 = m.resample_locf({"P": rows}, {"P": [ep - 2 * 3600]},
                             [ep - 89 * 60], [t])
        assert p3["cycle_ok"][0]
        assert p3["P"]["valid"][0]

    def test_sanity_filters(self):
        """§2.5-4: pct 整合 / avg 当日レンジ / 単調性 / avg 非正→NaN。"""
        bars = {"P": make_bars(utc("2026-07-13T00:00:00Z"),
                               utc("2026-07-14T00:00:00Z"), base=150.0)}
        good = {"instrument": "P", "book_type": "outlook",
                "snapshot_time": "2026-07-13T10:00:00Z",
                "pct_long_total": 60.0, "pct_short_total": 40.0,
                "buckets": {"avgLongPrice": 150.0, "avgShortPrice": 150.1}}
        bad_sum = dict(good, snapshot_time="2026-07-13T11:00:00Z",
                       pct_long_total=60.5, pct_short_total=41.0)
        bad_avg = dict(good, snapshot_time="2026-07-13T12:00:00Z",
                       buckets={"avgLongPrice": 200.0, "avgShortPrice": 150.0})
        nonpos_avg = dict(good, snapshot_time="2026-07-13T13:00:00Z",
                          buckets={"avgLongPrice": 0.0, "avgShortPrice": 150.0})
        out_of_order = dict(good, snapshot_time="2026-07-13T09:00:00Z")
        oanda_row = dict(good, book_type="position")
        rows, st = m.sanity_filter(
            [good, bad_sum, bad_avg, nonpos_avg, out_of_order, oanda_row],
            bars, ["P"])
        assert st["excluded_pct_sum"] == 1
        assert st["excluded_avg_range"] == 1
        assert st["monotonicity_violations"] == 1
        assert st["rows_kept"] == 3                    # good + nonpos + ooo
        assert st["rows_total"] == 5                   # OANDA 行は型で除外 (§2.1)
        # avg 非正は行を残し avg のみ NaN (S3 を当該スロット NA、§2.1)
        k = int(np.argsort(rows["P"]["ep"])[-1])
        assert math.isnan(rows["P"]["avg_long"][k])


# ══════════════════════════════════════════════════════════════════════
# rank (§3.1 mid-rank 式 pin — 大量タイ・量子化・strictly trailing)
# ══════════════════════════════════════════════════════════════════════

class TestTrailingRank:
    def test_midrank_formula_with_quantized_ties(self):
        """量子化 1% 刻み (整数) の大量タイで r(t) が式どおり (§3.1 M4)。"""
        rng = np.random.default_rng(42)
        vals = np.round(rng.uniform(0, 20, 400))       # 21 値に量子化 → 大量タイ
        r = m.trailing_rank(vals, w_slots=100, min_coverage=0.7)
        for i in (150, 250, 399):
            win = vals[i - 100:i]
            v = vals[i]
            expected = (np.sum(win < v) + 0.5 * np.sum(win == v)) / 100.0
            assert r[i] == pytest.approx(expected), f"i={i}"
        # 全タイ窓 → mid-rank = 0.5
        const = np.full(200, 7.0)
        rc = m.trailing_rank(const, w_slots=100)
        assert rc[150] == pytest.approx(0.5)

    def test_window_excludes_t_and_is_strictly_trailing(self):
        rng = np.random.default_rng(1)
        vals = np.round(rng.uniform(0, 20, 400))
        r1 = m.trailing_rank(vals, w_slots=100)
        # (a) 未来の値は r(t) に影響しない
        vals2 = vals.copy()
        vals2[351:] = 9999.0
        r2 = m.trailing_rank(vals2, w_slots=100)
        assert r1[350] == pytest.approx(r2[350])
        assert r1[300] == pytest.approx(r2[300])
        # (b) 窓は t 自身を含まない: v(t) を最大化しても分母/窓は不変で r=1.0
        vals3 = vals.copy()
        vals3[350] = 9999.0
        r3 = m.trailing_rank(vals3, w_slots=100)
        assert r3[350] == pytest.approx(1.0)   # t 包含なら (100+0.5)/101 ≠ 1.0

    def test_coverage_floor_na(self):
        """窓内有効被覆 < 70% → rank NA (補間しない、§3.1)。"""
        vals = np.arange(300, dtype=float)
        vals[100:140] = np.nan                          # 40 スロット欠測
        r = m.trailing_rank(vals, w_slots=100)
        assert math.isnan(r[150])                       # 窓 [50,150) 被覆 60%
        assert not math.isnan(r[250])                   # 窓 [150,250) 被覆 100%


# ══════════════════════════════════════════════════════════════════════
# OHLCV join / 前方リターン / censoring (§2.3 pin)
# ══════════════════════════════════════════════════════════════════════

class TestJoinContract:
    def _bars(self):
        eps = np.arange(0, 40) * 900.0
        opens = np.arange(0, 40, dtype=float)           # open = bar index
        return m.bars_from_arrays(eps, opens, opens + 0.5, opens - 0.5,
                                  opens + 0.25)

    def test_entry_bar_strictly_after_slot(self):
        bars = self._bars()
        # grid t が bar open とちょうど一致 → その bar は使わず次 bar
        pos = m.entry_positions(bars, np.array([3600.0]))
        assert bars["ep"][pos[0]] == 4500.0
        # bar open の 1 秒後 → 同じく次 bar
        pos2 = m.entry_positions(bars, np.array([3601.0]))
        assert bars["ep"][pos2[0]] == 4500.0

    def test_forward_return_ends_at_entry_plus_h_open(self):
        bars = self._bars()
        fwd = m.forward_returns(bars, np.array([3600.0]), h_bars=2)
        # entry = bar open 4500 (open=5)、終端 = entry+2 bar の open (=7)
        assert fwd[0] == pytest.approx(7.0 - 5.0)
        # 終端 bar が存在しない → NaN
        fwd2 = m.forward_returns(bars, np.array([39 * 900.0]), h_bars=2)
        assert math.isnan(fwd2[0])

    def test_mid_uses_last_completed_bar(self):
        bars = self._bars()
        # t=3600: bar[3](2700-3600) は t で確定済み、bar[4](3600-) は進行中
        mid = m.mid_at_slots(bars, np.array([3600.0, 3599.0]))
        assert mid[0] == pytest.approx(bars["close"][3])
        assert mid[1] == pytest.approx(bars["close"][2])

    def test_censoring_cutoff_minus_h_market_time(self):
        cutoff = utc("2026-07-15T12:00:00Z")            # Wed
        slots = [utc("2026-07-15T08:00:00Z"),           # 4h 前ちょうど → 算入
                 utc("2026-07-15T08:20:00Z")]           # 3h40m 前 → 不算入
        cok = m.censor_mask(slots, cutoff, h_bars=16)
        assert cok[0] and not cok[1]
        # 週末を挟む market-time censoring: Fri 20:00 → Mon 00:00 UTC は
        # market 4h ちょうど (Fri 1h + Sun 3h) → h=4h で算入可
        cutoff2 = utc("2026-07-20T00:00:00Z")           # Sun 20:00 EDT (open)
        cok2 = m.censor_mask([utc("2026-07-17T20:00:00Z")], cutoff2, h_bars=16)
        assert cok2[0]
        cok3 = m.censor_mask([utc("2026-07-17T20:20:00Z")], cutoff2, h_bars=16)
        assert not cok3[0]


# ══════════════════════════════════════════════════════════════════════
# ATR (§2.3 pin — NY17:00 roll、完結 bar のみ、当日レンジ不混入)
# ══════════════════════════════════════════════════════════════════════

class TestAtr:
    def _world(self):
        """Mon 2026-07-06〜Fri 07-10、取引日 k の TR = 2(k+1) になる合成 bar。"""
        bars = make_bars(utc("2026-07-05T21:00:00Z"),
                         utc("2026-07-10T21:00:00Z"), base=100.0, sigma=0.0)
        days = [m.trading_day(datetime.fromtimestamp(e, tz=timezone.utc))
                for e in bars["ep"]]
        uniq = sorted(set(days))
        for j, d in enumerate(days):
            k = uniq.index(d)
            bars["high"][j] = 100.0 + (k + 1)
            bars["low"][j] = 100.0 - (k + 1)
            bars["open"][j] = 100.0
            bars["close"][j] = 100.0
        return bars, uniq

    def test_ny17_roll_and_tr_pin(self):
        bars, uniq = self._world()
        daily = m.build_daily_bars(bars)
        assert daily["day"] == uniq                     # NY17 roll の取引日列
        assert len(uniq) == 5                           # Mon..Fri (週末 bar なし)
        atr = m.atr_series(daily, n_atr=2)
        # TR_k = 2(k+1) (close 恒等 100 → prev close 項は劣位)
        # atr[k] = mean(TR[k-1], TR[k]) → atr[2] (Wed) = mean(4,6) = 5
        assert atr[2] == pytest.approx(5.0)
        assert atr[3] == pytest.approx(7.0)

    def test_completed_strictly_before_t(self):
        bars, _ = self._world()
        daily = m.build_daily_bars(bars)
        atr = m.atr_series(daily, n_atr=2)
        thu_end = m.ny17_utc(date(2026, 7, 9)).timestamp()  # Thu 17:00 EDT
        # t = Thu 境界ちょうど → Thu bar は「厳密に前」でない → Wed まで
        assert m.atr_at(daily, atr, thu_end) == pytest.approx(5.0)
        # t = 境界 + 1s → Thu まで
        assert m.atr_at(daily, atr, thu_end + 1.0) == pytest.approx(7.0)

    def test_intraday_range_not_mixed_in(self):
        """当日 (進行中) レンジの不混入 assert (§2.3 M3 の古典 look-ahead)。"""
        bars, _ = self._world()
        t_thu_noon = utc("2026-07-09T12:00:00Z").timestamp()
        daily = m.build_daily_bars(bars)
        atr = m.atr_series(daily, n_atr=2)
        a0 = m.atr_at(daily, atr, t_thu_noon)
        # Thu 当日のレンジを爆発させても t=Thu 昼の ATR は不変
        poisoned = {k: (v.copy() if isinstance(v, np.ndarray) else v)
                    for k, v in bars.items()}
        sel = poisoned["ep"] >= t_thu_noon - 3600
        poisoned["high"][sel] += 500.0
        poisoned["low"][sel] -= 500.0
        daily_p = m.build_daily_bars(poisoned)
        atr_p = m.atr_series(daily_p, n_atr=2)
        a1 = m.atr_at(daily_p, atr_p, t_thu_noon)
        assert a0 == pytest.approx(a1)
        assert a0 == pytest.approx(5.0)                 # Wed まで (完結分のみ)


# ══════════════════════════════════════════════════════════════════════
# canary leak test (§4.5-3 — 検出器がリークを fail させることの pin)
# ══════════════════════════════════════════════════════════════════════

class TestCanaryLeak:
    def test_suite_green_on_production_impls(self):
        res = m.run_canary_suite()
        assert res["pass"], res

    def test_detects_locf_future_leak(self):
        """未来 snapshot (t−60s 規約破り) を受け取る LOCF → 検出 (fail)。"""
        def leaky_locf(rows, ver, cyc, grid):
            return m.resample_locf(rows, ver, cyc, grid, margin_sec=-3600)
        res = m.run_canary_suite(locf_impl=leaky_locf)
        assert not res["pass"]
        assert not res["checks"]["locf_future_injection"]["pass"]
        # シグナル注入 canary も同時に検出 (未来リターン値を持つ未来行)
        assert not res["checks"]["signal_future_value_injection"]["pass"]

    def test_detects_atr_path_leak(self):
        """ATR 経路への注入 (§4.5-3 明示要件): 進行中の当日 bar を ATR に
        含めるリーク実装 → 検出 (fail)。"""
        def leaky_atr(daily, atr, t_ep):
            k = int(np.searchsorted(daily["end_ep"], t_ep, side="left"))
            k = min(k, len(atr) - 1)
            v = float(atr[k])
            return v if not math.isnan(v) else float(atr[max(0, k - 1)])
        res = m.run_canary_suite(atr_impl=leaky_atr)
        assert not res["checks"]["atr_future_injection"]["pass"]
        assert not res["pass"]

    def test_detects_join_leak(self):
        """entry bar に grid t ちょうどの bar を使うリーク join → 検出。"""
        def leaky_fwd(bars, slot_ep, h_bars):
            pos = np.searchsorted(bars["ep"], slot_ep, side="left")
            out = np.full(len(slot_ep), np.nan)
            ok = (pos + h_bars) < len(bars["ep"])
            out[ok] = (bars["open"][pos[ok] + h_bars]
                       - bars["open"][pos[ok]])
            return out
        res = m.run_canary_suite(fwd_impl=leaky_fwd)
        assert not res["checks"]["fwd_return_window"]["pass"]
        assert not res["pass"]

    def test_detects_rank_window_future_leak(self):
        """§6-4/§4.5-3: 中心窓 (未来半分を含む) rank 実装 → canary が検出。"""
        def centered_rank(values, w_slots=100, min_coverage=0.7,
                          expanding=False):
            n = len(values)
            out = np.full(n, np.nan)
            half = w_slots // 2
            for i in range(n):
                v = values[i]
                if math.isnan(v):
                    continue
                win = np.concatenate([values[max(0, i - half):i],
                                      values[i + 1:i + 1 + half]])
                finite = win[~np.isnan(win)]
                if finite.size < min_coverage * w_slots:
                    continue
                out[i] = (np.sum(finite < v)
                          + 0.5 * np.sum(finite == v)) / finite.size
            return out
        res = m.run_canary_suite(rank_impl=centered_rank)
        assert not res["checks"]["rank_trailing_window"]["pass"]
        assert not res["pass"]

    def test_detects_rank_window_t_inclusion(self):
        """§3.1: 窓に t 自身を含める rank 実装 (v(t) 極大化で r≠1.0) → 検出。"""
        def inclusive_rank(values, w_slots=100, min_coverage=0.7,
                           expanding=False):
            n = len(values)
            out = np.full(n, np.nan)
            for i in range(n):
                v = values[i]
                if math.isnan(v):
                    continue
                lo = 0 if expanding else max(0, i - w_slots)
                win = values[lo:i + 1]              # t 包含 (リーク規約)
                finite = win[~np.isnan(win)]
                if finite.size < min_coverage * w_slots:
                    continue
                out[i] = (np.sum(finite < v)
                          + 0.5 * np.sum(finite == v)) / finite.size
            return out
        res = m.run_canary_suite(rank_impl=inclusive_rank)
        assert not res["checks"]["rank_trailing_window"]["pass"]
        assert not res["pass"]

    def test_detects_mid_in_progress_bar_leak(self):
        """§2.3: mid(t) に進行中 bar の close を使うリーク実装 → 検出。"""
        def leaky_mid(bars, slot_ep):
            pos = np.searchsorted(bars["ep"], slot_ep, side="right") - 1
            out = np.full(len(slot_ep), np.nan)
            ok = pos >= 0
            out[ok] = bars["close"][pos[ok]]        # 進行中 bar (確定前)
            return out
        res = m.run_canary_suite(mid_impl=leaky_mid)
        assert not res["checks"]["mid_completed_bar_only"]["pass"]
        assert not res["pass"]

    def test_passthrough_leak_detection_sensitivity(self):
        """貫通型: signal := 前方リターンの合成 world で |pooled IC| ≈ 1 を
        「リーク検出」できる感度が rank→score→IC 経路にあること。
        経路を無害化する regression (定数 rank 等) は fail する。"""
        res = m.run_canary_suite()
        chk = res["checks"]["leak_passthrough_detection"]
        assert chk["pass"], chk
        def dead_rank(values, w_slots=100, min_coverage=0.7, expanding=False):
            out = np.full(len(values), 0.5)         # 情報を伝えない rank
            out[np.isnan(values)] = np.nan
            return out
        res2 = m.run_canary_suite(rank_impl=dead_rank)
        assert not res2["checks"]["leak_passthrough_detection"]["pass"]
        assert not res2["pass"]


# ══════════════════════════════════════════════════════════════════════
# events (§3.4 pin — 交差 / hysteresis / NA リセット / 金曜窓 / +1 slot 遅延)
# ══════════════════════════════════════════════════════════════════════

def _midweek_slots(n):
    g = m.build_grid(utc("2026-07-14T00:00:00Z"), utc("2026-07-16T23:59:00Z"))
    assert len(g) >= n
    return g[:n]


class TestEvents:
    def test_crossing_and_hysteresis(self):
        ranks = np.array([0.50, 0.85, 0.92, 0.93, 0.85, 0.79, 0.91,
                          0.50, 0.15, 0.09, 0.15, 0.21, 0.08])
        slots = _midweek_slots(len(ranks))
        evs = m.crossing_events(ranks, slots)
        # SELL: 0.85→0.92 で発火、0.80 を戻すまで再発火なし、0.79 で re-arm
        # → 0.79→0.91 で 2 発目。BUY 側も対称 (0.20 re-arm)。
        assert [(e["i"], e["dir"]) for e in evs] == [
            (2, -1), (6, -1), (9, +1), (12, +1)]
        assert all(e["blocked"] == "" for e in evs)

    def test_na_gap_resets_state(self):
        """直前有効スロットとの市場時間ギャップ > 2h → リセット (§3.4)。
        リセット直後の最初の有効スロットは比較対象を持たず発火しない。"""
        nan = float("nan")
        ranks = np.array([0.85] + [nan] * 7 + [0.95, 0.96])   # 160min ギャップ
        slots = _midweek_slots(len(ranks))
        assert m.crossing_events(ranks, slots) == []
        # ギャップ ≤ 2h なら NA を挟む交差は成立する
        ranks2 = np.array([0.85, nan, nan, 0.95])              # 60min ギャップ
        evs2 = m.crossing_events(ranks2, slots[:4])
        assert [(e["i"], e["dir"]) for e in evs2] == [(3, -1)]

    def test_friday_close_window_blocks_new_events(self):
        """NY Fri 15:00–17:00 の新規 event 発火禁止 (§3.4、DST 追随)。"""
        g = m.build_grid(utc("2026-07-17T14:00:00Z"),
                         utc("2026-07-17T20:40:00Z"))          # Fri (EDT)
        iso = [m._iso(t) for t in g]
        i_blocked = iso.index("2026-07-17T19:20:00Z")          # 15:20 NY
        i_ok = iso.index("2026-07-17T18:40:00Z")               # 14:40 NY
        ranks = np.full(len(g), 0.5)
        ranks[i_ok - 1], ranks[i_ok] = 0.85, 0.92
        ranks[i_blocked - 1], ranks[i_blocked] = 0.05, 0.15    # BUY 側 re-arm 済み想定
        # BUY: 0.10 の上→下抜きが必要なので値を作り直す
        ranks[i_blocked - 1], ranks[i_blocked] = 0.15, 0.09
        evs = m.crossing_events(ranks, g)
        by_i = {e["i"]: e for e in evs}
        assert by_i[i_ok]["blocked"] == ""
        assert by_i[i_blocked]["blocked"] == "friday"

    def test_plus_one_slot_delay_mechanism(self):
        """ナイフエッジ #3-(ii) +1 グリッド slot 遅延の機構 pin。"""
        ranks = np.array([0.5, 0.85, 0.92, 0.93, 0.93, 0.93])
        slots = _midweek_slots(len(ranks))
        evs0 = m.crossing_events(ranks, slots)
        evs1 = m.crossing_events(ranks, slots, delay_slots=1)
        assert [(e["i"], e["dir"]) for e in evs0] == [(2, -1)]
        assert [(e["i"], e["dir"]) for e in evs1] == [(3, -1)]

    def test_year_end_window_blocks_only_look2(self):
        g = m.build_grid(utc("2026-12-21T00:00:00Z"),
                         utc("2026-12-21T06:00:00Z"))          # Mon (年末窓内)
        ranks = np.full(len(g), 0.5)
        ranks[3], ranks[4] = 0.85, 0.92
        ye = (utc(m.YEAR_END_EXCL[0]), utc(m.YEAR_END_EXCL[1]))
        evs = m.crossing_events(ranks, g, year_end=ye)
        assert evs[0]["blocked"] == "year_end"
        evs2 = m.crossing_events(ranks, g, year_end=None)      # first look
        assert evs2[0]["blocked"] == ""


class TestTrades:
    def _world(self):
        start = utc("2026-06-07T21:00:00Z")                    # Sun open (EDT)
        end = utc("2026-07-03T21:00:00Z")
        bars = make_bars(start, end, base=150.0, seed=3)
        grid = m.build_grid(start, end)
        daily = m.build_daily_bars(bars)
        atr = m.atr_series(daily)                              # ATR14 (本番値)
        return bars, grid, daily, atr

    def test_holding_overlap_dedup_is_per_horizon(self):
        """同一ペア×方向ホールド中の重複エントリー禁止 (§3.4) — h 毎に判定。
        5h 間隔の 2 event: h=4h は 2 trade、h=24h は 1 trade。"""
        bars, grid, daily, atr = self._world()
        iso = [m._iso(t) for t in grid]
        i1 = iso.index("2026-07-01T10:00:00Z")                 # Wed
        i2 = iso.index("2026-07-01T15:00:00Z")                 # +5h
        events = [{"i": i1, "dir": -1, "blocked": ""},
                  {"i": i2, "dir": -1, "blocked": ""}]
        slot_ep = np.array([t.timestamp() for t in grid])
        cutoff = utc("2026-07-03T21:00:00Z")
        kw = dict(bars=bars, slots=grid, slot_ep=slot_ep, daily=daily,
                  atr=atr, pair="EUR_USD", stat="S1", cutoff=cutoff,
                  burnin=grid[0])
        tr4 = m.build_trades(events, hname="4h", **kw)
        tr24 = m.build_trades(events, hname="24h", **kw)
        assert len(tr4) == 2
        assert len(tr24) == 1
        # exit = entry + h_bars 番目 bar の open (§2.3/§3.4 time-exit)
        t0 = tr4[0]
        entry_ep = utc(t0["entry_time"]).timestamp()
        exit_ep = utc(t0["exit_time"]).timestamp()
        assert exit_ep - entry_ep == pytest.approx(16 * 900)
        # 逆方向はホールド中でも建てられる (同一ペア×方向のみ禁止)
        events2 = [{"i": i1, "dir": -1, "blocked": ""},
                   {"i": i2, "dir": +1, "blocked": ""}]
        assert len(m.build_trades(events2, hname="24h", **kw)) == 2

    def test_censoring_rejects_late_events(self):
        bars, grid, daily, atr = self._world()
        iso = [m._iso(t) for t in grid]
        cutoff = utc("2026-07-03T21:00:00Z")                   # Fri close
        i_late = iso.index("2026-07-03T18:00:00Z")             # cutoff まで 3h
        slot_ep = np.array([t.timestamp() for t in grid])
        tr = m.build_trades([{"i": i_late, "dir": -1, "blocked": ""}],
                            bars, grid, slot_ep, daily, atr, "EUR_USD",
                            "S1", "4h", cutoff, grid[0])
        assert tr == []                                        # cutoff − h 打ち切り


class TestFirstTouch:
    def test_sl_priority_and_timeout_close(self):
        hi = np.array([101.0, 103.0])
        lo = np.array([99.0, 97.0])
        cl = np.array([100.5, 100.0])
        # 両ヒット bar → SL 優先 (ハウス保守規約)
        pnl, leg = m.first_touch(hi, lo, cl, 100.0, +1, 2.0, 2.0)
        assert (pnl, leg) == (-2.0, "sl")
        # fut_close tie-break (Secondary) は bar close 決済
        pnl2, leg2 = m.first_touch(hi, lo, cl, 100.0, +1, 2.0, 2.0,
                                   tie="fut_close")
        assert leg2 == "tie_close" and pnl2 == pytest.approx(0.0)
        # timeout = 最終 bar close 決済
        pnl3, leg3 = m.first_touch(hi, lo, cl, 100.0, +1, 10.0, 10.0)
        assert leg3 == "timeout" and pnl3 == pytest.approx(0.0)
        # SELL 側 TP
        pnl4, leg4 = m.first_touch(hi, lo, cl, 100.0, -1, 2.5, 10.0)
        assert (pnl4, leg4) == (2.5, "tp")


# ══════════════════════════════════════════════════════════════════════
# Gate 1 統計 (§4.1 pin — MBB null / 埋め込み検出 / IM df=7 / BH-FDR)
# ══════════════════════════════════════════════════════════════════════

def _make_obs(seed, beta=0.0, n_days=40, per_day=6, n_pairs=2):
    """合成 IC 観測 panel。beta>0 で fwd に signal を埋め込む。"""
    rng = np.random.default_rng(seed)
    obs = {}
    for p in range(n_pairs):
        n = n_days * per_day
        score = rng.normal(0, 1, n)
        fwd = beta * score + rng.normal(0, 1, n)
        day = np.repeat(np.arange(1, n_days + 1), per_day)
        obs[f"P{p}"] = {"score": score, "fwd": fwd, "day": day,
                        "slot_i": np.arange(n)}
    return obs


class TestGate1Stats:
    def test_im_df7_and_t_pinned(self):
        """IM 併設検定: 40 営業日 / 5 日 block → 8 block、df=7 (§4.1 M10 pin)。
        t/p は block IC 列から scipy で再計算した値と一致する。"""
        from scipy.stats import t as tdist
        obs = _make_obs(11, beta=0.3)
        res = m.im_test(obs)
        assert res["n_blocks"] == 8 and res["df"] == 7
        arr = np.array(res["block_ics"])
        se = arr.std(ddof=1) / np.sqrt(8)
        t_exp = arr.mean() / se
        assert res["t"] == pytest.approx(t_exp, abs=2e-3)
        assert res["p"] == pytest.approx(float(tdist.sf(t_exp, 7)), abs=2e-4)

    def test_embedded_signal_detected_and_max_composition(self):
        obs = _make_obs(5, beta=1.0)
        g = m.gate1_combo(obs, n_boot=400, seed=7, combo_idx=0, look=1,
                          sens_boot=50)
        assert g["pooled_ic"] > 0.3
        assert g["p_gate1"] == max(g["p_mbb"], g["im"]["p"])   # 二重検定 (§4.1)
        assert g["p_gate1"] < 0.02

    def test_null_p_not_small(self):
        """シャッフル同等の null (beta=0) で p が小さくならない (uniform 近傍)。"""
        ps = []
        for k in range(5):
            obs = _make_obs(100 + k, beta=0.0)
            g = m.gate1_combo(obs, n_boot=250, seed=9, combo_idx=k, look=1,
                              sens_boot=10)
            ps.append(g["p_mbb"])
        assert min(ps) > 0.01
        assert 0.15 < float(np.mean(ps)) < 0.95

    def test_second_look_is_bootstrap_only(self):
        obs = _make_obs(3, beta=0.5)
        g = m.gate1_combo(obs, n_boot=200, seed=7, combo_idx=0, look=2,
                          sens_boot=10)
        assert g["p_gate1"] == g["p_mbb"]
        assert g["im"]["p"] is None and "skipped" in g["im"]

    def test_deterministic_given_seed(self):
        obs = _make_obs(5, beta=0.4)
        g1 = m.gate1_combo(obs, n_boot=200, seed=42, combo_idx=1, look=1,
                           sens_boot=10)
        g2 = m.gate1_combo(obs, n_boot=200, seed=42, combo_idx=1, look=1,
                           sens_boot=10)
        assert g1["p_mbb"] == g2["p_mbb"] and g1["im"] == g2["im"]

    def test_im_se_zero_is_sign_aware(self):
        """se=0 退化 (全 block IC 同値): 宣言符号なら p=0、逆符号なら p=1 —
        符号盲目の「mean<0 でも p=0」を封鎖 (§4.1 片側 H1: IC > 0)。"""
        def perfect_obs(sign):
            rng = np.random.default_rng(3)
            obs = {}
            for p in range(2):
                score = rng.normal(0, 1, 60)
                obs[f"P{p}"] = {"score": score, "fwd": sign * score,
                                "day": np.repeat(np.arange(1, 11), 6),
                                "slot_i": np.arange(60)}
            return obs
        pos = m.im_test(perfect_obs(+1.0))          # 全 block IC = +1 → se=0
        assert pos["p"] == pytest.approx(0.0)
        assert math.isinf(pos["t"]) and pos["t"] > 0
        neg = m.im_test(perfect_obs(-1.0))          # 全 block IC = −1 → se=0
        assert neg["p"] == pytest.approx(1.0)       # 逆符号を最有意にしない
        assert math.isinf(neg["t"]) and neg["t"] < 0

    def test_mbb_joint_day_draw_across_pairs(self):
        """§4.1「暦ブロックを**全ペア同時に** resample」の pin — draw 毎に
        全ペアへ同一の sampled day 集合が適用される (per-pair 独立化 regression
        は null のクロスペア相関を破壊し反保守 = 偽 PASS 側)。"""
        obs = _make_obs(21, beta=0.0, n_days=30, per_day=4, n_pairs=2)
        draws = []
        def spy(sub):
            if len(sub) == 2:
                draws.append((np.sort(sub["P0"]["day"]).copy(),
                              np.sort(sub["P1"]["day"]).copy()))
            return 0.0
        m.mbb_pvalue(obs, spy, n_boot=25, seed_key=(9, 9))
        assert len(draws) >= 20                      # point 1 回 + boot draws
        full = np.sort(obs["P0"]["day"])
        resampled = 0
        for d0, d1 in draws[1:]:                     # [0] は point 計算
            # 両ペアの day multiset が完全一致 (per_day が同数なので直接比較可)
            assert np.array_equal(d0, d1)
            if not np.array_equal(d0, full):
                resampled += 1
        assert resampled > 0                         # 実際に resample されている

    def test_day_block_draw_contiguous_index_blocks(self):
        """block 構成の実装規約 pin: block = sorted unique 観測日列の
        **index 上で連続する L 個** (観測日が疎なら暦間隔を跨ぐ — 宣言済み)。"""
        days = np.array([1, 2, 10, 11, 20, 21, 30, 31, 40, 41])
        rng = np.random.default_rng(0)
        draw = m._day_blocks_draw(days, 5, rng)
        assert len(draw) == len(days)
        idx = {int(d): i for i, d in enumerate(days)}
        for c in range(0, len(draw), 5):
            chunk = [idx[int(d)] for d in draw[c:c + 5]]
            assert chunk == list(range(chunk[0], chunk[0] + 5))


class TestBhFdr:
    def test_bh_fdr_logic_pin(self):
        pvals = {"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5,
                 "e": None, "f": 0.03}
        out = m.bh_fdr(pvals, q=0.05, m=6)
        assert out["a"]["survive"] is True                     # 0.001 ≤ 0.05·1/6
        for k in ("b", "c", "d", "f"):
            assert out[k]["survive"] is False
        assert out["e"] == {"p": None, "rank": None, "threshold": None,
                            "survive": False}
        # 全て小さい場合は step-up で全通過
        out2 = m.bh_fdr({"a": 0.001, "b": 0.005, "c": 0.01}, q=0.05, m=6)
        assert all(out2[k]["survive"] for k in ("a", "b", "c"))
        # m 固定: 同じ p でも m が大きいと閾値が締まる
        out3 = m.bh_fdr({"a": 0.02}, q=0.05, m=1)
        out4 = m.bh_fdr({"a": 0.02}, q=0.05, m=6)
        assert out3["a"]["survive"] and not out4["a"]["survive"]


class TestGate2:
    def _trades(self, n, mean, seed=1):
        rng = np.random.default_rng(seed)
        out = []
        for i in range(n):
            net = float(rng.normal(mean, 1.0))
            out.append({"net_pips": net, "ft_net_pips": net * 0.8,
                        "stress_net_pips": net - 1.0, "ftc_net_pips": net,
                        "norm_net": net / 10.0,
                        "entry_day": (date(2026, 8, 3)
                                      + timedelta(days=i % 20)).isoformat()})
        return out

    def test_positive_ev_detected(self):
        tr = self._trades(100, 3.0)
        g = m.gate2_combo(tr, n_boot=300, seed=5, combo_idx=0)
        assert g["n"] == 100 and not g["n_lt_60"]
        assert g["ev_time_exit"] > 0 and g["p_ev"] < 0.05

    def test_n_gate_skips_test(self):
        """§4.2(d): N<60 は検定せず点推定のみ (自動 UNDERPOWERED の短絡なし)。"""
        g = m.gate2_combo(self._trades(40, 3.0), n_boot=300, seed=5,
                          combo_idx=0)
        assert g["n_lt_60"] is True and g["p_ev"] is None
        assert g["ev_time_exit"] is not None                   # 点推定は出す


# ══════════════════════════════════════════════════════════════════════
# classify (§4.4 pin — C1〜C5 全分岐 + フラグ + Step 2)
# ══════════════════════════════════════════════════════════════════════

class TestClassify:
    BASE = dict(gate1_survive=True, ic_point=0.1, n_trades=80,
                ev_time_exit=2.0, ev_first_touch=1.0, ev_stress=0.5,
                gate2_p_ok=True, knife_pass=True, confirmatory_ok=True,
                signflip_significant=False, partial_ic_point=0.05)

    def test_c1_full_pass(self):
        assert m.classify_combo(**self.BASE) == ("C1", [])

    def test_c1_confounded_flag(self):
        cls, flags = m.classify_combo(**{**self.BASE,
                                         "partial_ic_point": -0.02})
        assert cls == "C1" and "CONFOUNDED" in flags           # PASS-with-flag

    def test_c1_confirmatory_untested_does_not_block(self):
        cls, flags = m.classify_combo(**{**self.BASE, "confirmatory_ok": None})
        assert cls == "C1" and "CONFIRMATORY_UNTESTED" in flags

    def test_confirmatory_fail_blocks_c1(self):
        cls, _ = m.classify_combo(**{**self.BASE, "confirmatory_ok": False})
        assert cls == "C3"                                     # 点は正 → C3 へ

    def test_c2_sequencing_reversal_beats_c4(self):
        """time-exit 正 ∧ first-touch ≤0 は Gate1 通過でも C2 (REJECT 側)。"""
        cls, _ = m.classify_combo(**{**self.BASE, "ev_first_touch": -0.5,
                                     "gate2_p_ok": False})
        assert cls == "C2"

    def test_c3_underpowered_eligible(self):
        cls, _ = m.classify_combo(**{**self.BASE, "gate1_survive": False,
                                     "gate2_p_ok": False})
        assert cls == "C3"

    def test_n_gate_routes_to_point_classes(self):
        """N<60: C1 不可、点推定で C3/C2 へ (§4.2(d) M5)。"""
        cls, _ = m.classify_combo(**{**self.BASE, "n_trades": 30,
                                     "gate2_p_ok": False})
        assert cls == "C3"
        cls2, _ = m.classify_combo(**{**self.BASE, "n_trades": 30,
                                      "gate2_p_ok": False,
                                      "ev_first_touch": -0.1})
        assert cls2 == "C2"

    def test_c4_reject_f(self):
        cls, _ = m.classify_combo(**{**self.BASE, "ev_time_exit": -1.0,
                                     "ev_first_touch": -1.0,
                                     "gate2_p_ok": False})
        assert cls == "C4"                                     # Gate1 通過 ∧ EV≤0

    def test_c5_and_signflip_flag(self):
        cls, flags = m.classify_combo(**{**self.BASE, "gate1_survive": False,
                                         "ic_point": -0.15,
                                         "ev_time_exit": -1.0,
                                         "ev_first_touch": -1.0,
                                         "gate2_p_ok": False,
                                         "signflip_significant": True})
        assert cls == "C5" and "SIGN-FLIP" in flags

    def test_knife_fail_blocks_c1(self):
        cls, _ = m.classify_combo(**{**self.BASE, "knife_pass": False})
        assert cls == "C3"

    def test_confirmatory_untested_flag_only_on_c1(self):
        """CONFIRMATORY_UNTESTED は PASS 候補 (C1) 限定 — C2〜C5 (検査適用外)
        をフラグで汚さない (§2.4 [^4] の注記対象は PASS)。"""
        for over in ({"gate1_survive": False, "gate2_p_ok": False,
                      "knife_pass": None},                      # C3
                     {"ev_first_touch": -0.5, "gate2_p_ok": False},  # C2
                     {"ev_time_exit": -1.0, "ev_first_touch": -1.0,
                      "gate2_p_ok": False}):                    # C4
            cls, flags = m.classify_combo(
                **{**self.BASE, "confirmatory_ok": None, **over})
            assert cls != "C1"
            assert "CONFIRMATORY_UNTESTED" not in flags, cls

    def test_overall_verdict_priority(self):
        ov = m.overall_verdict
        assert ov({"a": "C1", "b": "C3"}, False, False) == "PASS"
        assert ov({"a": "C3", "b": "C4"}, False, False) == "UNDERPOWERED"
        assert ov({"a": "C4", "b": "C5"}, False, False) == "REJECT-F"
        assert ov({"a": "C2", "b": "C5"}, False, False) == "REJECT"
        assert ov({}, True, False) == "POSTPONE"
        assert ov({}, True, True) == "DEFERRED"                # 2 回目不達

    def test_overall_verdict_look2_landing_set(self):
        """§4.4 Step 2 / M8: look=2 の着地は PASS/REJECT-F/REJECT のみ —
        C3 は REJECT へ畳まれ UNDERPOWERED は構造的に到達不能 (3 回目 look 封鎖)。"""
        ov = m.overall_verdict
        assert ov({"a": "C3"}, False, False, 2) == "REJECT"    # modal path pin
        assert ov({"a": "C3", "b": "C4"}, False, False, 2) == "REJECT-F"
        assert ov({"a": "C1", "b": "C3"}, False, False, 2) == "PASS"
        assert ov({"a": "C2", "b": "C5"}, False, False, 2) == "REJECT"
        # 品質 gate 経路は look=2 でも POSTPONE/DEFERRED (統計着地ではない)
        assert ov({}, True, False, 2) == "POSTPONE"
        assert ov({}, True, True, 2) == "DEFERRED"
        # 統計着地の全域が制約集合に入る
        for cls in ("C1", "C2", "C3", "C4", "C5"):
            assert ov({"a": cls}, False, False, 2) in (
                "PASS", "REJECT-F", "REJECT")


# ══════════════════════════════════════════════════════════════════════
# jump detector / 品質 gate (§2.5 pin)
# ══════════════════════════════════════════════════════════════════════

def _mini_panel(pairs, n, grid, valid_fn=None, skew_fn=None):
    panel = {"slots": grid[:n],
             "slot_ep": np.array([t.timestamp() for t in grid[:n]]),
             "cycle_ok": np.ones(n, dtype=bool)}
    for q, p in enumerate(pairs):
        valid = np.array([valid_fn(q, i) if valid_fn else True
                          for i in range(n)])
        skew = np.array([skew_fn(q, i) if skew_fn else 10.0
                         for i in range(n)])
        panel[p] = {"valid": valid, "skew": skew,
                    "long": 50 + skew / 2, "short": 50 - skew / 2,
                    "avg_long": np.full(n, np.nan),
                    "avg_short": np.full(n, np.nan)}
    return panel


class TestJumpAndQuality:
    def test_jump_forward_24h_exclusion_no_retroactive(self):
        """≥4 ペア同時 |Δskew|>20pp → 前方 +24h (市場時間) のみ除外 (§2.5-7 M2)。"""
        grid = m.build_grid(utc("2026-07-14T00:00:00Z"),
                            utc("2026-07-16T23:59:00Z"))
        pairs = [f"P{k}" for k in range(6)]
        n = 216

        def skew_fn(q, i):
            return 40.0 if (q < 4 and i >= 50) else 10.0      # 4 ペアが i=50 で jump
        panel = _mini_panel(pairs, n, grid, skew_fn=skew_fn)
        mask, idx = m.jump_exclusion_mask(panel, pairs)
        assert idx == [50]
        assert not mask[49]                                    # 遡及除外なし
        assert mask[50] and mask[50 + 72]                      # +24h 境界含む
        assert not mask[50 + 73]

        def skew3_fn(q, i):
            return 40.0 if (q < 3 and i >= 50) else 10.0      # 3 ペアでは不発
        panel3 = _mini_panel(pairs, n, grid, skew_fn=skew3_fn)
        mask3, idx3 = m.jump_exclusion_mask(panel3, pairs)
        assert idx3 == [] and not mask3.any()

    def test_quality_gates_coverage_exclusion_and_family_postpone(self):
        grid = m.build_grid(utc("2026-07-06T00:00:00Z"),
                            utc("2026-07-10T20:59:00Z"))       # Mon..Fri
        n = len(grid)
        pairs = ["A", "B"]

        def valid_fn(q, i):
            return True if q == 0 else (i % 2 == 0)            # B は 50%
        panel = _mini_panel(pairs, n, grid, valid_fn=valid_fn)
        burnin = {p: grid[0] for p in pairs}
        cutoff = utc("2026-07-10T21:00:00Z")
        qg = m.quality_gates(panel, pairs, burnin, cutoff, {"rows_total": 0})
        assert qg["pairs"]["A"]["pass"]
        assert not qg["pairs"]["B"]["pass"]
        assert qg["pairs"]["B"]["fail_reason"] == "coverage<90%"
        assert qg["excluded_pairs"] == ["B"]
        assert qg["surviving_pairs"] == ["A"]
        assert qg["postpone"] is True                          # <4 ペア (§2.5-3)


# ══════════════════════════════════════════════════════════════════════
# 入力ガード (§2.2 health book 成分 / §2.3 cutoff クリップ)
# ══════════════════════════════════════════════════════════════════════

class TestInputGuards:
    def test_extract_health_checks_book_component(self):
        """verified key の book 成分検査: estimand は outlook のみ (§2.1) —
        旧 OANDA book (position/order) の検証成功で staleness を更新しない。"""
        health = [
            {"key": "verified:USD_JPY:outlook", "value": "2026-07-15T12:00:00Z"},
            {"key": "verified:USD_JPY:position", "value": "2026-07-15T13:00:00Z"},
            {"key": "verified:EUR_USD:order", "value": "2026-07-15T13:00:00Z"},
            {"key": "verified:EUR_USD", "value": "2026-07-15T13:00:00Z"},
            {"key": "last_cycle_at", "value": "2026-07-15T13:30:00Z"},
        ]
        ver, cyc = m.extract_health_events(health, ["USD_JPY", "EUR_USD"])
        assert len(ver["USD_JPY"]) == 1                # outlook のみ採用
        assert ver["EUR_USD"] == []                    # order / book 欠落は不採用
        assert len(cyc) == 1

    def test_clip_bars_to_cutoff(self):
        """§2.3: cutoff までに完結 (open+900s ≤ cutoff) した bar のみ —
        フル版 parquet を渡しても境界スロットの前方リターンが cutoff 後の
        価格を消費しない (切詰め規約非依存)。"""
        cutoff = utc("2026-07-15T12:00:00Z")
        ep0 = cutoff.timestamp()
        eps = np.array([ep0 - 2700, ep0 - 1800, ep0 - 900, ep0, ep0 + 900])
        vals = np.arange(5, dtype=float)
        bars = m.bars_from_arrays(eps, vals, vals + 1, vals - 1, vals)
        out, n_clip = m.clip_bars_to_cutoff(bars, cutoff)
        assert n_clip == 2                             # open=cutoff (未完結) + 未来
        assert out["ep"][-1] == pytest.approx(ep0 - 900)
        out2, n2 = m.clip_bars_to_cutoff(out, cutoff)
        assert n2 == 0 and out2 is out                 # 冪等 (切詰め済みは無変換)


# ══════════════════════════════════════════════════════════════════════
# compute_stat_series (§3.2 S2 lag / S3 pain 式の数値 pin)
# ══════════════════════════════════════════════════════════════════════

class TestStatSeries:
    def _panel(self, n=80):
        valid = np.ones(n, dtype=bool)
        valid[5] = False
        skew = np.linspace(-20.0, 20.0, n)
        return {"slot_ep": np.arange(n) * 1200.0,
                "X": {"valid": valid, "skew": skew,
                      "long": np.full(n, 60.0), "short": np.full(n, 40.0),
                      "avg_long": np.full(n, 151.0),
                      "avg_short": np.full(n, 149.0)}}

    def test_s2_is_72_slot_lag_difference(self):
        panel = self._panel()
        out = m.compute_stat_series(panel, "X", np.full(80, 150.0),
                                    np.full(80, 2.0))
        skew = out["S1"]
        assert math.isnan(out["S2"][71])               # lag 端点未満は NA
        assert out["S2"][72] == pytest.approx(skew[72] - skew[0])
        assert out["S2"][79] == pytest.approx(skew[79] - skew[7])
        # 端点が invalid (NA) なら S2 も NA (両端点有効時のみ)
        assert math.isnan(out["S1"][5])
        assert math.isnan(out["S2"][77])               # 77 − 72 = 5 (invalid)

    def test_s3_pain_formula_sign_and_atr_denominator(self):
        panel = self._panel()
        out = m.compute_stat_series(panel, "X", np.full(80, 150.0),
                                    np.full(80, 2.0))
        # pain = [L/100·(avgL−mid) − S/100·(mid−avgS)] / ATR
        #      = [0.6·(151−150) − 0.4·(150−149)] / 2.0 = 0.1
        assert out["S3"][10] == pytest.approx(0.1)
        # long 側が水没 (avgL > mid が深い) ほど pain は正に増える符号系
        panel2 = self._panel()
        panel2["X"]["avg_long"] = np.full(80, 154.0)
        out2 = m.compute_stat_series(panel2, "X", np.full(80, 150.0),
                                     np.full(80, 2.0))
        assert out2["S3"][10] > out["S3"][10]
        # ATR 未定義/非正は S3 NA (§2.3 分母)
        atr_bad = np.full(80, 2.0)
        atr_bad[20] = np.nan
        atr_bad[21] = 0.0
        out3 = m.compute_stat_series(panel, "X", np.full(80, 150.0), atr_bad)
        assert math.isnan(out3["S3"][20]) and math.isnan(out3["S3"][21])
        # invalid スロットは S1/S3 とも NA
        assert math.isnan(out["S3"][5])


# ══════════════════════════════════════════════════════════════════════
# partial IC (§4.4 CONFOUNDED の実体 — momentum 統制の pin)
# ══════════════════════════════════════════════════════════════════════

class TestPartialIc:
    def _obs(self, mode, n=900, seed=8):
        rng = np.random.default_rng(seed)
        mid = np.cumsum(rng.normal(0, 1.0, n)) + 100.0
        slot_i = np.arange(400, n - 20)
        c24 = mid[slot_i] - mid[slot_i - 72]
        if mode == "confounded":                       # signal = momentum の写像
            score = c24 + rng.normal(0, 0.1, len(slot_i))
            fwd = c24 + rng.normal(0, 0.1, len(slot_i))
        else:                                          # momentum と独立な直接効果
            score = rng.normal(0, 1.0, len(slot_i))
            fwd = score + rng.normal(0, 0.5, len(slot_i))
        day = (slot_i // 72).astype(int)
        obs = {"P": {"score": score, "fwd": fwd, "day": day, "slot_i": slot_i}}
        return obs, {"P": mid}

    def test_momentum_confound_is_removed(self):
        obs, mid = self._obs("confounded")
        plain = m.spearman(obs["P"]["score"], obs["P"]["fwd"])
        res = m.partial_ic_combo(obs, mid)
        assert plain > 0.9                             # 素の IC は強い
        assert res["n"] > 100
        assert abs(res["pooled_partial_ic"]) < 0.3     # 統制後はほぼ消える

    def test_direct_signal_survives_control(self):
        obs, mid = self._obs("direct")
        res = m.partial_ic_combo(obs, mid)
        assert res["pooled_partial_ic"] > 0.5          # 直接効果は残る

    def test_insufficient_n_returns_none(self):
        obs, mid = self._obs("direct")
        o = obs["P"]
        small = {"P": {k: o[k][:3] for k in o}}
        res = m.partial_ic_combo(small, mid)
        assert res["pooled_partial_ic"] is None
        assert res["per_pair"]["P"]["partial_ic"] is None


# ══════════════════════════════════════════════════════════════════════
# confirmatory 複製検査 (§2.4 — ok True/False/None + 有意逆転の 4 分岐)
# ══════════════════════════════════════════════════════════════════════

class TestConfirmatory:
    def _ctx(self, ev_mean, weeks=8.0, n_trades=40, ic_sign=0.0, seed=2):
        rng = np.random.default_rng(seed)
        score = rng.normal(0, 1, 300)
        fwd = ic_sign * score + rng.normal(0, 0.2 if ic_sign else 1.0, 300)
        obs = {"CP": {"score": score, "fwd": fwd,
                      "day": np.repeat(np.arange(1, 31), 10),
                      "slot_i": np.arange(300)}}
        trades = [{"net_pips": float(rng.normal(ev_mean, 0.5)),
                   "ft_net_pips": 0.0, "stress_net_pips": 0.0,
                   "ftc_net_pips": 0.0, "norm_net": 0.0,
                   "entry_day": (date(2026, 8, 3)
                                 + timedelta(days=i % 20)).isoformat()}
                  for i in range(n_trades)]
        return {"ic_obs": {"S1x4h": obs}, "trades": {"S1x4h": trades},
                "eval_span_weeks": weeks}

    def test_no_data_defers(self):
        res = m.confirmatory_check(None, "S1x4h", 100, 7, 0)
        assert res["ok"] is None

    def test_ineligible_defers_with_note(self):
        for kw in ({"weeks": 4.0}, {"n_trades": 20}):
            res = m.confirmatory_check(self._ctx(2.0, **kw), "S1x4h", 100, 7, 0)
            assert res["ok"] is None
            assert res["eligible"] is False
            assert "未検査" in res["note"]

    def test_positive_ev_passes(self):
        res = m.confirmatory_check(self._ctx(2.0), "S1x4h", 100, 7, 0)
        assert res["ok"] is True and res["eligible"] is True
        assert res["point_net_ev"] > 0

    def test_negative_ev_blocks(self):
        res = m.confirmatory_check(self._ctx(-2.0), "S1x4h", 100, 7, 0)
        assert res["ok"] is False
        assert "EV" in res["note"]
        assert "user_review_required" not in res

    def test_significant_reversal_requires_user_review(self):
        """pooled IC が宣言と逆符号で両側有意 → PASS 保留 + user 裁定 (§2.4)。"""
        res = m.confirmatory_check(self._ctx(2.0, ic_sign=-1.0), "S1x4h",
                                   300, 7, 0)
        assert res["ok"] is False
        assert res["user_review_required"] is True
        assert res["reversal_two_sided_p"] < 0.05


# ══════════════════════════════════════════════════════════════════════
# knife_edge fail 側分岐 (データ不足 → 全 gate FAIL、限定 PASS なし)
# ══════════════════════════════════════════════════════════════════════

class TestKnifeEdgeFailBranches:
    def test_empty_family_fails_all_gates(self):
        ctx = {"ic_obs": {"S1x4h": {}}, "trades": {"S1x4h": []},
               "pairs": [], "gate2": {}, "canary": {"pass": True}}
        out = m.knife_edge_combo(ctx, "S1", "4h")
        assert out["pass"] is False
        assert out["fold"]["pass"] is False
        assert "note" in out["fold"]                   # fold 構成不能
        assert out["grid"]["pass"] is False
        assert out["grid"]["adjacent_pos"] == 0        # 隣接 gate2 なし → 0
        assert out["leak"]["pass"] is False            # delay EV なし
        assert out["cross_pair"]["limited_pass"] is None

    def test_canary_fail_blocks_leak_gate(self):
        ctx = {"ic_obs": {"S1x4h": {}}, "trades": {"S1x4h": []},
               "pairs": [], "gate2": {}, "canary": {"pass": False}}
        out = m.knife_edge_combo(ctx, "S1", "4h")
        assert out["leak"]["canary_pass"] is False
        assert out["leak"]["pass"] is False


# ══════════════════════════════════════════════════════════════════════
# §2.2 fallback 必須診断 (NA 時間帯分布 + 閑散集中 → DEFERRED 機械判定)
# ══════════════════════════════════════════════════════════════════════

class TestFallbackDiagnostics:
    def _grid_and_panel(self, quiet_frac):
        grid = m.build_grid(utc("2026-07-13T00:00:00Z"),
                            utc("2026-07-17T20:59:00Z"))     # Mon..Fri
        ny = [t.astimezone(m._ny()).hour for t in grid]
        quiet_idx = [i for i, h in enumerate(ny)
                     if h in m.FALLBACK_QUIET_NY_HOURS]
        busy_idx = [i for i, h in enumerate(ny)
                    if h not in m.FALLBACK_QUIET_NY_HOURS]
        n_quiet = int(80 * quiet_frac)
        slots = quiet_idx[:n_quiet] + busy_idx[:80 - n_quiet]
        panel = {"stats": {"P": {"na_stale_slots": slots}}}
        return grid, panel

    def test_quiet_concentration_detected(self):
        grid, panel = self._grid_and_panel(quiet_frac=1.0)
        diag = m.fallback_stale_diagnostics(panel, grid, ["P"])
        assert diag["na_stale_total"] == 80
        assert diag["quiet_na_share"] == pytest.approx(1.0)
        assert diag["quiet_concentration"] is True

    def test_uniform_distribution_not_concentrated(self):
        grid, panel = self._grid_and_panel(quiet_frac=0.4)   # ≈ スロット比率並み
        diag = m.fallback_stale_diagnostics(panel, grid, ["P"])
        assert diag["quiet_concentration"] is False

    def test_min_count_guard(self):
        """総数 < 50 では集中判定しない (少数 NA での spurious DEFERRED 防止)。"""
        grid, panel = self._grid_and_panel(quiet_frac=1.0)
        panel["stats"]["P"]["na_stale_slots"] = \
            panel["stats"]["P"]["na_stale_slots"][:30]
        diag = m.fallback_stale_diagnostics(panel, grid, ["P"])
        assert diag["na_stale_total"] == 30
        assert diag["quiet_concentration"] is False


# ══════════════════════════════════════════════════════════════════════
# run_eval 統合 (合成 6 ペア世界での full dry-run — §6-2 準拠)
# ══════════════════════════════════════════════════════════════════════

def _smoke_world(cutoff_iso="2026-09-11T06:33:31Z"):
    t0 = utc(m.T0_PRIMARY)
    cutoff = utc(cutoff_iso)
    grid = m.build_grid(t0, cutoff)
    bars_by_pair = {}
    snapshots = []
    for q, pair in enumerate(m.PRIMARY):
        bars_by_pair[pair] = make_bars(t0 - timedelta(days=1), cutoff,
                                       base=150.0 + q, seed=10 + q)
        snapshots.extend(make_snapshot_rows(pair, grid, 150.0 + q,
                                            phase=q * 1.1, seed=100 + q))
    artifact = {"snapshots": snapshots, "health": [], "synthetic": True}
    return artifact, bars_by_pair, cutoff


class TestRunEvalIntegration:
    @pytest.fixture(scope="class")
    def smoke(self):
        artifact, bars, cutoff = _smoke_world()
        res = m.run_eval(artifact, bars, cutoff, look=1, seed=m.SEED_DEFAULT,
                         n_boot=40, sens_boot=8)
        return artifact, bars, cutoff, res

    def test_full_pipeline_structure(self, smoke):
        _, _, _, res = smoke
        assert res["canary"]["pass"]
        assert res["quality_gates"]["postpone"] is False
        assert sorted(res["surviving_pairs"]) == sorted(m.PRIMARY)
        combos = [f"{s}x{h}" for s, h in m.COMBOS]
        assert sorted(res["combos"].keys()) == sorted(combos)
        assert res["verdict"]["overall"] in (
            "PASS", "UNDERPOWERED", "REJECT-F", "REJECT", "DEFERRED")
        for c in combos:
            assert res["combos"][c]["class"] in ("C1", "C2", "C3", "C4", "C5")
            # N<60 combo は Gate2 検定なし (§4.2(d))
            g2 = res["combos"][c]["gate2"]
            if g2["n"] < m.MIN_TRADES_GATE2:
                assert g2["p_ev"] is None
        # trade は発生している (合成 sin skew が extreme を横断する設計)
        assert sum(len(v) for v in res["trade_list"].values()) > 0
        # seed / n_boot / cutoff が JSON に固定される (§7 再現性)
        assert res["seed"] == m.SEED_DEFAULT and res["n_boot"] == 40
        # 出力は JSON 直列化可能
        json.dumps(res, default=str)

    def test_quality_diagnostics_recorded(self, smoke):
        """量子化粒度 (ペア×統計毎、§2.5-7) + stale cap 診断の JSON 記録 pin。"""
        _, _, _, res = smoke
        for pair in res["surviving_pairs"]:
            qz = res["quality_gates"]["pairs"][pair]["quantization"]
            assert set(qz.keys()) == {"S1", "S2", "S3"}
            assert qz["S1"] > 0 and qz["S2"] > 0        # sin+noise skew は多値
        # smoke world は health 系列なし → fallback 記録 + 必須診断併記、
        # ただし rows が 20 分毎に来るため na_stale ≈ 0 → 集中なし → 統計続行
        assert res["stale_cap_mode"] == "fallback"
        diag = res["quality_gates"]["stale_cap_fallback"]
        assert diag["quiet_concentration"] is False
        # cutoff (06:33:31Z) を跨ぐ進行中 bar (06:30 open) は機械クリップされ
        # 件数が fail-loud 記録される (§2.3 切詰め規約非依存)
        clip = res["inputs"]["bars_clipped_beyond_cutoff"]
        assert set(clip.keys()) == set(m.PRIMARY)
        assert all(v == 1 for v in clip.values())
        assert res["missing_parquet"]["primary"] == []

    def test_deterministic_rerun(self, smoke):
        artifact, bars, cutoff, res = smoke
        res2 = m.run_eval(artifact, bars, cutoff, look=1,
                          seed=m.SEED_DEFAULT, n_boot=40, sens_boot=8)
        assert res2["verdict"]["overall"] == res["verdict"]["overall"]
        assert res2["verdict"]["classes"] == res["verdict"]["classes"]
        for c in res["combos"]:
            assert (res2["combos"][c]["gate1"]["p_mbb"]
                    == res["combos"][c]["gate1"]["p_mbb"])
            assert (res2["combos"][c]["gate1"]["pooled_ic"]
                    == res["combos"][c]["gate1"]["pooled_ic"])

    def test_family_gate_postpone_skips_statistics(self):
        """§2.5-3: postpone は look を消費しない = 統計段を実行しない
        (中間 peeking の構造的抑止)。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-07-24T06:33:31Z")
        bars = {p: make_bars(t0 - timedelta(days=1), cutoff, seed=1)
                for p in m.PRIMARY[:4]}
        artifact = {"snapshots": [], "health": [], "synthetic": True}
        res = m.run_eval(artifact, bars, cutoff, look=1, n_boot=10)
        assert res["verdict"]["overall"] == "POSTPONE"
        assert "combos" not in res                             # 統計は未計算
        res2 = m.run_eval(artifact, bars, cutoff, look=1, n_boot=10,
                          postponed_before=True)
        assert res2["verdict"]["overall"] == "DEFERRED"        # 2 回目不達

    def test_look2_requires_c3_combo_list(self):
        """§4.4: second look の対象は first look C3 combo のみ —
        明示指定なしの look=2 実行は引数契約で即拒否 (敗者復活の封鎖)。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-07-24T06:33:31Z")
        bars = {p: make_bars(t0 - timedelta(days=1), cutoff, seed=1)
                for p in m.PRIMARY[:4]}
        artifact = {"snapshots": [], "health": [], "synthetic": True}
        with pytest.raises(RuntimeError, match="C3"):
            m.run_eval(artifact, bars, cutoff, look=2, n_boot=10,
                       look2_combos=None)

    def test_look2_landing_set_and_adjacent_gate2(self, smoke):
        """F1 pin: look=2 の着地 ∈ {PASS,REJECT-F,REJECT,POSTPONE,DEFERRED}
        (UNDERPOWERED 到達不能) + gate2 点推定は全 6 combo で常時計算
        (knife #2(ii) の隣接参照が look=2 でも成立)。"""
        artifact, bars, cutoff, _ = smoke
        res = m.run_eval(artifact, bars, cutoff, look=2, seed=m.SEED_DEFAULT,
                         n_boot=40, sens_boot=8, look2_combos=["S1x4h"])
        assert res["verdict"]["overall"] in (
            "PASS", "REJECT-F", "REJECT", "POSTPONE", "DEFERRED")
        assert res["verdict"]["overall"] != "UNDERPOWERED"
        assert list(res["combos"].keys()) == ["S1x4h"]  # 対象 combo のみ判定
        all_combos = sorted(f"{s}x{h}" for s, h in m.COMBOS)
        assert sorted(res["gate2_all_combos"].keys()) == all_combos
        for c, g2 in res["gate2_all_combos"].items():
            assert "ev_time_exit" in g2                 # 点推定は全 combo
            if c != "S1x4h":
                assert g2["p_ev"] is None               # 検定は対象 combo のみ

    def test_stale_cap_mode_recorded(self):
        """§2.2: stale_cap_mode は結果 JSON に必ず記録 — verified 系列があれば
        primary、無ければ fallback (postpone 早期 return 経路でも)。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-07-24T06:33:31Z")
        bars = {p: make_bars(t0 - timedelta(days=1), cutoff, seed=1)
                for p in m.PRIMARY[:4]}
        art_nohealth = {"snapshots": [], "health": [], "synthetic": True}
        res = m.run_eval(art_nohealth, bars, cutoff, look=1, n_boot=10)
        assert res["stale_cap_mode"] == "fallback"
        health = [{"key": f"verified:{p}:outlook",
                   "value": m._iso(t0)} for p in m.PRIMARY[:4]]
        art_health = {"snapshots": [], "health": health, "synthetic": True}
        res2 = m.run_eval(art_health, bars, cutoff, look=1, n_boot=10)
        assert res2["stale_cap_mode"] == "primary"

    def test_verdict_run_requires_primary_parquet(self):
        """§2.5-1 fail-loud: primary parquet 1 個欠落での verdict 実行を拒否
        (無言の family 縮小 = 品質 gate 迂回を封鎖)。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-07-24T06:33:31Z")
        bars = {p: make_bars(t0 - timedelta(days=1), cutoff, seed=1)
                for p in m.PRIMARY[:5]}                 # AUD_JPY 欠落
        artifact = {"snapshots": [], "health": [], "synthetic": True}
        with pytest.raises(RuntimeError, match="parquet 欠落"):
            m.run_eval(artifact, bars, cutoff, look=1, n_boot=10,
                       verdict_run=True)

    def test_verdict_run_requires_verified_series_or_fallback_flag(self):
        """§2.2 LOCK (主モード確定): verified 系列欠落の verdict 実行は
        fail-loud — 明示 --fallback-mode でのみ続行可、mode は JSON に記録。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-07-24T06:33:31Z")
        bars = {p: make_bars(t0 - timedelta(days=1), cutoff, seed=1)
                for p in m.PRIMARY}
        artifact = {"snapshots": [], "health": [], "synthetic": True}
        with pytest.raises(RuntimeError, match="verified"):
            m.run_eval(artifact, bars, cutoff, look=1, n_boot=10,
                       verdict_run=True)
        res = m.run_eval(artifact, bars, cutoff, look=1, n_boot=10,
                         verdict_run=True, fallback_mode=True)
        assert res["stale_cap_mode"] == "fallback"

    def test_fallback_quiet_concentration_connects_to_deferred(self):
        """§2.2 事前固定分岐の wiring: fallback モード + 2h-cap NA の閑散帯
        (NY 17–03) 集中 → verdict = DEFERRED (統計段は実行しない)。"""
        t0 = utc(m.T0_PRIMARY)
        cutoff = utc("2026-08-07T06:33:31Z")
        grid = m.build_grid(t0, cutoff)
        bars = {}
        snapshots = []
        ny = m._ny()
        for q, pair in enumerate(m.PRIMARY[:4]):
            bars[pair] = make_bars(t0 - timedelta(days=1), cutoff,
                                   base=150.0 + q, seed=30 + q)
            for t in grid:
                if pair == m.PRIMARY[0] and 18 <= t.astimezone(ny).hour < 22:
                    continue                            # 閑散帯で更新停止
                lp = 55.0
                snapshots.append({
                    "instrument": pair, "book_type": "outlook",
                    "snapshot_time": m._iso(t - timedelta(seconds=300)),
                    "pct_long_total": lp, "pct_short_total": 100.0 - lp})
        artifact = {"snapshots": snapshots, "health": [], "synthetic": True}
        res = m.run_eval(artifact, bars, cutoff, look=1, n_boot=10)
        assert res["stale_cap_mode"] == "fallback"
        diag = res["quality_gates"]["stale_cap_fallback"]
        assert diag["na_stale_total"] >= m.FALLBACK_NA_MIN_COUNT
        assert diag["quiet_concentration"] is True
        assert res["verdict"]["overall"] == "DEFERRED"
        assert "combos" not in res                      # 統計段は未実行


# ══════════════════════════════════════════════════════════════════════
# C1/PASS 経路の end-to-end pin (埋め込み強 contrarian シグナル合成世界)
# — 偽 PASS コスト最大の経路を verdict データに触れる前に一度は通す (§7)
# ══════════════════════════════════════════════════════════════════════

def _strong_world(cutoff_iso="2026-10-08T06:33:31Z", period_slots=360,
                  seed0=50):
    """skew = sin 波 (周期 5 日) / 価格 drift = −skew に比例 (contrarian が
    真に機能する世界)。摩擦 (2.0–4.5p) ≪ 4h drift (~70p) で C1 到達可能。"""
    t0 = utc(m.T0_PRIMARY)
    cutoff = utc(cutoff_iso)
    grid = m.build_grid(t0, cutoff)
    t0_ep = t0.timestamp()
    period_sec = period_slots * 1200.0
    bars_by_pair = {}
    snapshots = []
    health = []
    for q, pair in enumerate(m.PRIMARY):
        pip = m._pip(pair)
        base = 150.0 if pair.endswith("_JPY") else 1.5
        phase = q * 0.7
        rng = np.random.default_rng(seed0 + q)

        def skew_norm(ts_ep):
            return math.sin(2 * math.pi * (ts_ep - t0_ep) / period_sec + phase)

        for t in grid:
            sk = 45.0 * skew_norm(t.timestamp()) + float(rng.normal(0, 1.0))
            sk = max(-49.0, min(49.0, sk))
            lp = 50.0 + sk / 2.0
            snapshots.append({
                "instrument": pair, "book_type": "outlook",
                "snapshot_time": m._iso(t - timedelta(seconds=300)),
                "pct_long_total": round(lp, 4),
                "pct_short_total": round(100.0 - lp, 4)})
        health.append({"key": f"verified:{pair}:outlook", "value": m._iso(t0)})

        eps, o, h, l, c = [], [], [], [], []
        px = base
        t = (t0 - timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        while t < cutoff:
            if m.is_market_open(t):
                drift = -5.0 * pip * skew_norm(t.timestamp())
                op = px
                cl = px + drift + float(rng.normal(0, 0.5 * pip))
                eps.append(t.timestamp())
                o.append(op)
                h.append(max(op, cl) + 2 * pip)
                l.append(min(op, cl) - 2 * pip)
                c.append(cl)
                px = cl
            t += timedelta(seconds=900)
        bars_by_pair[pair] = m.bars_from_arrays(
            np.array(eps), np.array(o), np.array(h), np.array(l), np.array(c))
    artifact = {"snapshots": snapshots, "health": health, "synthetic": True}
    return artifact, bars_by_pair, cutoff


class TestC1PassPath:
    @pytest.fixture(scope="class")
    def strong(self):
        artifact, bars, cutoff = _strong_world()
        # n_boot=150: p_min = 1/151 ≈ 0.0066 < BH rank-1 閾値 0.05/6 ≈ 0.0083
        res = m.run_eval(artifact, bars, cutoff, look=1, seed=m.SEED_DEFAULT,
                         n_boot=150, sens_boot=10, verdict_run=True)
        return res

    def test_overall_pass_with_c1(self, strong):
        res = strong
        assert res["stale_cap_mode"] == "primary"       # health 系列供給済み
        assert res["quality_gates"]["postpone"] is False
        assert res["verdict"]["classes"]["S1x4h"] == "C1"
        assert res["verdict"]["overall"] == "PASS"
        assert any("実装 pre-reg" in n for n in res["verdict"]["notes"])

    def test_c1_gates_and_knife_four_points(self, strong):
        c = strong["combos"]["S1x4h"]
        # Gate 1: pooled IC 強正 + FDR 通過 (p = max(p_MBB, p_IM))
        assert c["gate1"]["pooled_ic"] > 0.5
        assert c["gate1_fdr"]["survive"] is True
        # Gate 2: N≥60 ∧ p_ev ≤ 0.05 ∧ 3 点 EV 正 (time-exit/first-touch/stress)
        g2 = c["gate2"]
        assert g2["n"] >= m.MIN_TRADES_GATE2
        assert g2["p_ev"] is not None and g2["p_ev"] <= 0.05
        assert g2["ev_time_exit"] > 0 and g2["ev_first_touch"] > 0
        assert g2["ev_stress"] > 0
        assert "block_basis" in g2                       # 実装規約の宣言 (§4.2)
        # ナイフエッジ 4 点 (§4.5): #1 fold / #2 grid / #3 leak+delay / #4 記録
        ke = c["knife_edge"]
        assert ke["pass"] is True
        assert ke["fold"]["pass"] and ke["fold"]["rest_ic"] > 0
        assert len(ke["fold"]["fold_ic"]) == 3
        assert ke["grid"]["pass"]
        assert set(ke["grid"]["threshold_evs"].keys()) == {"0.85", "0.95"}
        assert ke["grid"]["adjacent_pos"] >= 1           # 隣接 combo 点 EV 参照
        assert ke["grid"]["sens_ic"]["W10"] > 0
        assert ke["grid"]["sens_ic"]["expanding"] > 0
        assert ke["leak"]["pass"] and ke["leak"]["delay1_ev"] > 0
        assert ke["cross_pair"]["limited_pass"] is None  # JPY/非JPY とも正

    def test_c1_confirmatory_untested_and_stage_b(self, strong):
        c = strong["combos"]["S1x4h"]
        # confirmatory ペア無し → ok=None (未検査を明記、PASS は止めない §2.4)
        assert c["confirmatory"]["ok"] is None
        assert "CONFIRMATORY_UNTESTED" in c["flags"]
        # Stage B (§4.3 記述のみ) は Gate1+2 通過 combo で出力される
        assert "stage_b" in c
        assert len(c["stage_b"]["per_pair"]) == len(m.PRIMARY)
        for pair, d in c["stage_b"]["per_pair"].items():
            assert d["ic"] is not None

    def test_non_c1_combos_unpolluted(self, strong):
        """S3 (avg 価格なし → 全 NA) は event 0 → C5、CONFIRMATORY_UNTESTED
        フラグ無し (PASS 候補限定の注記、minor fix pin)。"""
        for combo in ("S3x4h", "S3x24h"):
            c = strong["combos"][combo]
            assert c["class"] == "C5"
            assert "CONFIRMATORY_UNTESTED" not in c["flags"]
            assert c["gate2"]["n"] == 0


class TestMainGuards:
    def test_refuses_real_data_without_verdict_flag(self, tmp_path, capsys):
        """§6-2 構造的強制: synthetic 宣言なし + --verdict-run なし → 拒否。"""
        art = tmp_path / "artifact.json"
        art.write_text(json.dumps({"snapshots": [], "health": []}))
        rc = m.main(["--artifact", str(art), "--ohlcv-dir", str(tmp_path)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "verdict" in err and "§6-2" in err

    def test_verdict_run_refuses_missing_parquet(self, tmp_path, capsys):
        """§2.5-1 fail-loud: --verdict-run は 13 ペア parquet 完備必須 —
        1 ファイル欠落でも欠落リストを表示して拒否 (無言の family 縮小封鎖)。"""
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("2026-07-15", periods=8, freq="15min", tz="UTC")
        df = pd.DataFrame({"Open": 1.0, "High": 1.1, "Low": 0.9, "Close": 1.0},
                          index=idx)
        df.to_parquet(tmp_path / "USD_JPY_15m.parquet")
        art = tmp_path / "artifact.json"
        art.write_text(json.dumps({"snapshots": [], "health": [],
                                   "synthetic": True}))
        rc = m.main(["--artifact", str(art), "--ohlcv-dir", str(tmp_path),
                     "--verdict-run"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "parquet 欠落" in err and "EUR_USD" in err

    def test_self_check_mode(self, capsys):
        rc = m.main(["--self-check"])
        assert rc == 0
        out = capsys.readouterr().out
        assert json.loads(out)["pass"] is True
