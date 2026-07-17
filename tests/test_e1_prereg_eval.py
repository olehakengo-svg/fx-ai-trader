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

    def test_overall_verdict_priority(self):
        ov = m.overall_verdict
        assert ov({"a": "C1", "b": "C3"}, False, False) == "PASS"
        assert ov({"a": "C3", "b": "C4"}, False, False) == "UNDERPOWERED"
        assert ov({"a": "C4", "b": "C5"}, False, False) == "REJECT-F"
        assert ov({"a": "C2", "b": "C5"}, False, False) == "REJECT"
        assert ov({}, True, False) == "POSTPONE"
        assert ov({}, True, True) == "DEFERRED"                # 2 回目不達


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


class TestMainGuards:
    def test_refuses_real_data_without_verdict_flag(self, tmp_path, capsys):
        """§6-2 構造的強制: synthetic 宣言なし + --verdict-run なし → 拒否。"""
        art = tmp_path / "artifact.json"
        art.write_text(json.dumps({"snapshots": [], "health": []}))
        rc = m.main(["--artifact", str(art), "--ohlcv-dir", str(tmp_path)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "verdict" in err and "§6-2" in err

    def test_self_check_mode(self, capsys):
        rc = m.main(["--self-check"])
        assert rc == 0
        out = capsys.readouterr().out
        assert json.loads(out)["pass"] is True
