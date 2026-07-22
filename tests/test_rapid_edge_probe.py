"""rapid_edge_probe (S2 共通ハーネス) のオフラインテスト — 合成 fixture のみ、parquet/API 不要.

pin の核心:
  1. OOS 構造遮断 — デフォルトで 2024-01-01 以降の bar/entry が一切出ない (unlock flag なしにアクセス不能)
  2. 小語彙検証 — 未知語彙は即 ValueError (silent fallback 禁止)
  3. causal entry — trigger 確定 bar の次 bar open で entry
  4. first-touch SL 優先 (event_modality_lib §3.5 ハウス保守規約と同一)
  5. seed 固定 — ダミー series は決定的
  6. レポート規律ヘッダ (診断≠判定 / 再試行禁止チェックリスト) の自動印字
  7. モジュール import 時の副作用なし
"""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import event_modality_lib as L  # noqa: E402
from tools import rapid_edge_probe as R  # noqa: E402


# ─── fixture: 合成 bars (2022 → 2025 まで伸ばして OOS 遮断を検証可能に) ─────
def synth_bars(pairs=("USD_JPY", "EUR_USD"), start="2022-01-03", periods=96 * 1000):
    return R.make_synth_bars(list(pairs), start=start, periods=periods)


def base_spec(**over):
    raw = {
        "name": "t_probe",
        "direction_source": {"kind": "technical", "condition": "momentum_sign", "lookback": 20},
        "entry_trigger": {"kind": "none"},
        "pairs": ["USD_JPY", "EUR_USD"],
        "horizons": [16],
        "holding": {"mode": "bars"},
        "window": {"start": "2022-01-01", "end": "2025-12-31"},
    }
    raw.update(over)
    return raw


# ═══ 1. OOS 構造遮断 ═══════════════════════════════════════════════════════
def test_oos_blocked_by_default_no_entry_after_boundary():
    bars = synth_bars()  # データは 2025 年まで存在する
    assert max(df.index.max() for df in bars.values()) > pd.Timestamp("2024-06-01", tz="UTC")
    spec = R.normalize_spec(base_spec())
    res = R.run_probe(spec, bars=bars)
    assert res["oos_locked"] is True
    assert res["max_entry_ts"] is not None
    assert pd.Timestamp(res["max_entry_ts"]) < pd.Timestamp(R.OOS_BOUNDARY_UTC, tz="UTC")
    # 実効窓も探索窓終端でクランプされている
    assert res["window_effective"]["end"] <= R.EXPLORE_END


def test_oos_clamp_is_structural_slice():
    """遮断は bars の物理スライス — エンジンのどの段も OOS bar を見られない。"""
    bars = synth_bars()
    spec = R.normalize_spec(base_spec())
    clamped = R.clamp_oos(bars["USD_JPY"], spec, unlock_oos=False)
    assert clamped.index.max() < pd.Timestamp(R.OOS_BOUNDARY_UTC, tz="UTC")


def test_oos_unlock_requires_explicit_flag(capsys):
    bars = synth_bars()
    spec = R.normalize_spec(base_spec())
    res = R.run_probe(spec, bars=bars, unlock_oos=True)
    assert res["oos_locked"] is False
    # unlock 時は警告が stderr に出る
    assert "unlock-oos" in capsys.readouterr().err
    # unlock なら 2024+ の entry が存在しうる (データが 2025 まであるので)
    assert pd.Timestamp(res["max_entry_ts"]) >= pd.Timestamp(R.OOS_BOUNDARY_UTC, tz="UTC")


def test_event_calendar_also_clamped():
    bars = synth_bars()
    cal = {"NFP": [L.et_to_utc(d.date(), 8, 30).isoformat()
                   for d in pd.date_range("2022-02-04", "2025-06-06", freq="4W")]}
    spec = R.normalize_spec(base_spec(
        direction_source={"kind": "event", "event": "NFP", "rule": "uncond_usd_long"}))
    events = R.load_calendar(spec, unlock_oos=False, calendar=cal)
    assert events and max(events) < pd.Timestamp(R.OOS_BOUNDARY_UTC, tz="UTC")


# ═══ 2. 小語彙検証 (silent fallback 禁止) ═══════════════════════════════════
@pytest.mark.parametrize("mutate,msg", [
    ({"direction_source": {"kind": "astrology"}}, "kind"),
    ({"direction_source": {"kind": "event", "event": "GDP", "rule": "fade"}}, "event"),
    ({"direction_source": {"kind": "event", "event": "NFP", "rule": "yolo"}}, "rule"),
    ({"direction_source": {"kind": "technical", "condition": "rsi_magic"}}, "condition"),
    ({"entry_trigger": {"kind": "martingale"}}, "entry_trigger"),
    ({"holding": {"mode": "forever"}}, "holding"),
    ({"horizons": ["h99"]}, "horizon"),
    ({"pairs": ["USD_ZZZ"]}, "摩擦テーブル"),
    ({"name": "bad name!"}, "name"),
])
def test_unknown_vocab_raises(mutate, msg):
    with pytest.raises(ValueError, match=msg):
        R.normalize_spec(base_spec(**mutate))


def test_series_lag_days_must_be_causal():
    with pytest.raises(ValueError, match="lag_days"):
        R.normalize_spec(base_spec(
            direction_source={"kind": "series", "column": "__dummy_x__", "lag_days": 0}))


# ═══ 3. causal entry ════════════════════════════════════════════════════════
def test_breakout_entry_is_next_bar_open():
    """breakout が bar k の close で確定 → entry_pos は k+1 (look-ahead なし)。"""
    n = 200
    idx = pd.date_range("2022-01-03", periods=n, freq="15min", tz="UTC")
    base = np.full(n, 1.0)
    k = 100
    base[k:] = 1.01  # bar k で 20-bar 高値をブレイク
    df = pd.DataFrame({"Open": base, "High": base + 0.0001,
                       "Low": base - 0.0001, "Close": base}, index=idx)
    buy_ok, _ = R.trigger_masks(df, {"kind": "breakout", "lookback": 20,
                                     "ema_period": 20, "search_bars": 16})
    assert buy_ok[k] and not buy_ok[k - 1]
    e = R._entry_after_trigger(df, buy_ok, ~buy_ok, 1, 90, 120)
    assert e == k + 1


def test_technical_scores_causal_shift():
    """momentum_sign の score は bar i の close までしか見ない。"""
    n = 100
    idx = pd.date_range("2022-01-03", periods=n, freq="15min", tz="UTC")
    close = np.linspace(1.0, 1.1, n)
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close}, index=idx)
    s = R.technical_scores(df, {"condition": "momentum_sign", "lookback": 20})
    assert np.isnan(s.iloc[10])              # warmup 中は NaN
    assert s.iloc[50] == pytest.approx(close[50] - close[30])


# ═══ 4. first-touch SL 優先 ═════════════════════════════════════════════════
def test_first_touch_sl_priority_same_bar():
    """同一バーで TP/SL 両ヒット → SL 優先 (§3.5 ハウス保守規約)。"""
    n = 96 * 40
    idx = pd.date_range("2022-01-03", periods=n, freq="15min", tz="UTC")
    base = np.full(n, 1.0)
    df = pd.DataFrame({"Open": base, "High": base + 0.0002,
                       "Low": base - 0.0002, "Close": base}, index=idx)
    e = n - 200
    # entry バーで両側に大きくヒゲ (barrier はどちらにも当たる)
    df.iloc[e, df.columns.get_loc("High")] = 2.0
    df.iloc[e, df.columns.get_loc("Low")] = 0.5
    memo = R.AtrMemo(L.build_daily_from_m15(df))
    skips = {}
    out = R.simulate_outcome(df, memo, e, 1, 16, "EUR_USD",
                             {"mode": "first_touch", "tp_sigma": 1.0, "sl_sigma": 1.0}, skips)
    assert out is not None
    assert out["pips"] < 0  # SL 側 (摩擦込みで必ず負)


def test_atr_memo_matches_lib():
    bars = synth_bars(pairs=("EUR_USD",), periods=96 * 120)
    df = bars["EUR_USD"]
    daily = L.build_daily_from_m15(df)
    memo = R.AtrMemo(daily)
    ts = df.index[96 * 60]
    assert memo.before(ts) == pytest.approx(L.atr14d_before(daily, ts), rel=1e-12)


def test_censored_horizon_counted_not_silent():
    bars = synth_bars(pairs=("EUR_USD",), periods=96 * 30)
    df = bars["EUR_USD"]
    memo = R.AtrMemo(L.build_daily_from_m15(df))
    skips = {}
    out = R.simulate_outcome(df, memo, len(df) - 5, 1, 96, "EUR_USD", {"mode": "bars"}, skips)
    assert out is None and skips["censored_horizon"] == 1


# ═══ 5. seed 固定 / 決定性 ══════════════════════════════════════════════════
def test_dummy_series_deterministic():
    bars = synth_bars(pairs=("USD_JPY",), periods=96 * 50)
    df = bars["USD_JPY"]
    ds = {"kind": "series", "column": "__dummy_e20__", "file": None, "lag_days": 1}
    a = R.series_scores(df, "USD_JPY", ds)
    b = R.series_scores(df, "USD_JPY", ds)
    pd.testing.assert_series_equal(a, b)
    assert set(a.dropna().unique()) <= {-1.0, 1.0}


def test_run_probe_deterministic():
    bars = synth_bars()
    spec = R.normalize_spec(base_spec(
        direction_source={"kind": "series", "column": "__dummy_e20__"},
        entry_trigger={"kind": "breakout", "lookback": 20}))
    r1 = R.run_probe(spec, bars=synth_bars())
    r2 = R.run_probe(spec, bars=bars)
    assert r1["cells"] == r2["cells"]
    assert r1["spec_hash"] == r2["spec_hash"]


# ═══ 6. event 方向 (USD-leg 変換の配管 pin) ═════════════════════════════════
def test_event_uncond_usd_long_direction_per_pair():
    bars = synth_bars()
    cal = {"NFP": [L.et_to_utc(d.date(), 8, 30).isoformat()
                   for d in pd.date_range("2022-02-04", "2023-11-03", freq="4W")]}
    spec = R.normalize_spec(base_spec(
        direction_source={"kind": "event", "event": "NFP", "rule": "uncond_usd_long"}))
    res_trades = {}
    for pair in ["USD_JPY", "EUR_USD"]:
        m15 = R.clamp_oos(bars[pair], spec, False)
        memo = R.AtrMemo(L.build_daily_from_m15(m15))
        events = R.load_calendar(spec, False, calendar=cal)
        trades = R.gen_trades_event(spec, pair, m15, events, memo, {})
        res_trades[pair] = trades
    assert res_trades["USD_JPY"] and all(t.direction == 1 for t in res_trades["USD_JPY"])
    assert res_trades["EUR_USD"] and all(t.direction == -1 for t in res_trades["EUR_USD"])


# ═══ 7. レポート規律 + draft pre-reg ════════════════════════════════════════
def test_report_discipline_header_and_checklist(tmp_path):
    bars = synth_bars()
    spec = R.normalize_spec(base_spec())
    res = R.run_probe(spec, bars=bars)
    paths = R.write_outputs(res, spec, str(tmp_path), draft_prereg=True,
                            prereg_dir=str(tmp_path))
    md = open(paths["md"], encoding="utf-8").read()
    assert "判定ではない" in md
    assert "live/tier 判断" in md
    assert "再試行禁止チェックリスト" in md
    for name, _, _ in R.FALSIFIED_CHECKLIST:
        assert name in md
    assert "価格モダリティ round-3" in md
    # json ミラー
    js = json.load(open(paths["json"], encoding="utf-8"))
    assert js["verdict_authority"].startswith("NONE")
    assert js["oos_locked"] is True


def test_draft_prereg_skeleton_is_draft_not_locked(tmp_path):
    bars = synth_bars()
    spec = R.normalize_spec(base_spec())
    res = R.run_probe(spec, bars=bars)
    paths = R.write_outputs(res, spec, str(tmp_path), draft_prereg=True,
                            prereg_dir=str(tmp_path))
    text = open(paths["prereg_draft"], encoding="utf-8").read()
    assert "DRAFT" in text and "LOCKED ではない" in text
    assert R.OOS_BOUNDARY_UTC in text          # OOS 窓の明記
    assert "TODO" in text                      # 自動 LOCK 不能 (人手の必須項目が残る)
    assert "UNDERPOWERED" in text


def test_dummy_series_flagged_in_report(tmp_path):
    bars = synth_bars()
    spec = R.normalize_spec(base_spec(
        direction_source={"kind": "series", "column": "__dummy_e20__"}))
    res = R.run_probe(spec, bars=bars)
    assert res["dummy_series"] is True
    md = R.render_md(res, spec)
    assert "DUMMY series" in md and "E20" in md


# ═══ 8. モジュールトップ副作用禁止 ══════════════════════════════════════════
def test_import_has_no_side_effects():
    code = ("import sys; sys.argv=['x','--bogus']; "
            "import tools.rapid_edge_probe as m; print('IMPORT_OK')")
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "IMPORT_OK"


# ═══ 9. 同梱実例 spec の整合 (実データ不要 — 正規化のみ) ════════════════════
def test_bundled_example_specs_are_valid():
    for fn in ("nfp_usd_24h.json", "rate_diff_breakout_template.json"):
        raw = R.load_spec_file(os.path.join(REPO, "tools", "rapid_probe_specs", fn))
        spec = R.normalize_spec(raw)
        # 実例は探索窓内に閉じている (OOS に触れない)
        assert spec.window["end"] <= R.EXPLORE_END
    # 実例 (b) は E20 待ちのダミー構造であることが spec 自体に明記されている
    raw_b = R.load_spec_file(os.path.join(
        REPO, "tools", "rapid_probe_specs", "rate_diff_breakout_template.json"))
    assert raw_b["direction_source"]["column"].startswith("__dummy")
    assert "E20" in raw_b["description"]
