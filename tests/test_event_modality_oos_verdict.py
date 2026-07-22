"""E15 phase-0 OOS 判定器の契約 pin (rule:R1 手続き、pre-reg §10-6).

pre-reg: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
「canary/leak/join 契約を tests/ に pin してから OOS データに触れる」(§10-6) の履行。
合成データのみ使用 — 実 OOS データ不使用。estimand 本体の pin は
tests/test_event_modality_lib.py (§10-6 済) — 重複させない。

pin する契約:
  - 判定分岐 C1/C2/C3/C4/C5 (§8、排他・この順) + 全体 PASS/UNDERPOWERED/FAIL
  - BH-FDR (q=0.05、m=m0 固定 — p 未定義でも分母を縮めない)
  - event-block bootstrap の決定論 seed + 効果検出/null 弁別 (§5c レグ A)
  - Ibragimov–Müller 併設検定 df=blocks−1 (§5c レグ A)
  - combo p = max(p_boot, p_IM)
  - ナイフエッジ #1 LOFO / #2 隣接格子点列挙 / #4 集中度 (LOPO・top block・collision)
  - リーク canary が「注入されたリーク」を検出すること (§5c-3 — 検出能力の pin)
  - entry +1 バー遅延 (§5c-3) が entry のみ動かし R0 を変えないこと
  - OOS 窓ガード (t_e 帰属、§3.4)
  - 摩擦バリアント stress1/stress2 の式 (§3.5)
  - gross 抽出 + 摩擦線形適用 = event_trade(friction=判定値) と等価 (join 契約)
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from tools import event_modality_lib as L
from tools import event_modality_oos_verdict as V


# ─── 合成 M15 frame (lib テストと同型) ──────────────────────────────────────
def _make_m15(n, start="2024-06-01 00:00", base=1.1000):
    idx = pd.date_range(start=pd.Timestamp(start, tz="UTC"), periods=n,
                        freq="15min")
    o = np.full(n, base)
    return pd.DataFrame({"Open": o, "High": o + 0.0002, "Low": o - 0.0002,
                         "Close": o.copy()}, index=idx)


# ─── §3.5 摩擦バリアント式 ──────────────────────────────────────────────────
def test_friction_variants_formula():
    fv = V.friction_variants("EUR_USD")   # f=2.00
    assert fv["base"] == pytest.approx(2.00)
    assert fv["stress1"] == pytest.approx(3.00)    # max(2.5, 3.0)
    assert fv["stress2"] == pytest.approx(3.75)    # 3.0 * 1.25
    fv = V.friction_variants("GBP_USD")   # f=4.53 → 1.25f=5.6625 > f+1
    assert fv["stress1"] == pytest.approx(5.6625)
    assert fv["stress2"] == pytest.approx(7.078125)


# ─── BH-FDR (m=m0 固定) ─────────────────────────────────────────────────────
def test_bh_fdr_m_fixed_and_none():
    p = {"a": 0.001, "b": 0.02, "c": None, "d": 0.9}
    out = V.bh_fdr(p, q=0.05, m=6)
    assert out["a"]["survive"] is True         # 0.001 <= 0.05*1/6
    assert out["b"]["survive"] is False        # 0.02 > 0.05*2/6
    assert out["c"]["survive"] is False and out["c"]["rank"] is None
    assert out["d"]["survive"] is False
    # m は縮めない: defined 3 個でも threshold は m=6 基準 (6 桁丸め)
    assert out["a"]["threshold"] == pytest.approx(0.05 / 6, abs=1e-6)


def test_bh_fdr_step_up():
    # BH の step-up: rank2 が通れば rank1 も通る
    p = {"a": 0.012, "b": 0.015}
    out = V.bh_fdr(p, q=0.05, m=6)
    # 0.015 <= 0.05*2/6=0.0167 → k_max=2 → 両方 survive
    assert out["a"]["survive"] and out["b"]["survive"]


# ─── event-block bootstrap (§5c レグ A) ─────────────────────────────────────
def test_event_block_bootstrap_deterministic():
    rng = np.random.default_rng(3)
    # 弱効果 (p が床値 1/(B+1) に張り付かない中間域) で seed 差が観測できる
    vals = rng.normal(0.12, 1.0, 60)
    blocks = np.repeat([f"e{i}" for i in range(20)], 3)
    r1 = V.event_block_bootstrap(vals, blocks, 400, (123, 0))
    r2 = V.event_block_bootstrap(vals, blocks, 400, (123, 0))
    r3 = V.event_block_bootstrap(vals, blocks, 400, (123, 1))
    assert r1["p_one"] == r2["p_one"]          # seed 決定論
    assert r1["n_blocks"] == 20
    assert 0.005 < r1["p_one"] < 0.9           # 中間域 (床/天井でない)
    assert r3["p_one"] != r1["p_one"]          # 別 seed は別系列


def test_event_block_bootstrap_discriminates():
    rng = np.random.default_rng(5)
    blocks = np.repeat([f"e{i}" for i in range(25)], 4)
    strong = rng.normal(2.0, 1.0, 100)
    null = rng.normal(0.0, 1.0, 100)
    p_strong = V.event_block_bootstrap(strong, blocks, 800, (9, 0))["p_one"]
    p_null = V.event_block_bootstrap(null, blocks, 800, (9, 0))["p_one"]
    assert p_strong < 0.01
    assert p_null > 0.10


def test_event_block_bootstrap_degenerate():
    r = V.event_block_bootstrap(np.array([1.0, 2.0]), np.array(["e", "e"]),
                                100, (1, 0))
    assert r["p_one"] is None and r["n_blocks"] == 1


# ─── Ibragimov–Müller 併設検定 ──────────────────────────────────────────────
def test_im_block_test_df_is_blocks_minus_1():
    rng = np.random.default_rng(11)
    blocks = np.repeat([f"e{i}" for i in range(20)], 5)
    vals = rng.normal(1.0, 1.0, 100)
    r = V.im_block_test(vals, blocks)
    assert r["n_blocks"] == 20 and r["df"] == 19
    assert r["p"] is not None and r["p"] < 0.05


def test_im_block_test_degenerate():
    assert V.im_block_test(np.array([1.0]), np.array(["e"]))["p"] is None
    # 全 block 同値かつ正 → p=0 (最有意)、負 → p=1
    same_pos = V.im_block_test(np.array([1.0, 1.0]), np.array(["a", "b"]))
    assert same_pos["p"] == 0.0
    same_neg = V.im_block_test(np.array([-1.0, -1.0]), np.array(["a", "b"]))
    assert same_neg["p"] == 1.0


# ─── §8 判定分岐 (排他、この順) ─────────────────────────────────────────────
def test_classify_c1_requires_all():
    base = {"leg_a_pass": True, "ev_te": 1.0, "ev_ft": 1.0,
            "leg_b_d": True, "leg_b_all": True, "knife_all": True}
    assert V.classify_combo(base) == "C1"
    for k, v in (("leg_a_pass", False), ("leg_b_all", False),
                 ("knife_all", False)):
        s = dict(base)
        s[k] = v
        assert V.classify_combo(s) != "C1"


def test_classify_c2_sequencing_before_c3():
    # te>0 ∧ ft≤0 は power 不足でも C2 (C3 より先に判定 — §8 順序)
    s = {"leg_a_pass": False, "ev_te": 2.0, "ev_ft": -0.5,
         "leg_b_d": False, "leg_b_all": False, "knife_all": False}
    assert V.classify_combo(s) == "C2"


def test_classify_c3_underpowered():
    s = {"leg_a_pass": False, "ev_te": 2.0, "ev_ft": 1.5,
         "leg_b_d": False, "leg_b_all": False, "knife_all": False}
    assert V.classify_combo(s) == "C3"
    # B(d) 達成なら C3 に落ちない (leg A 不通過 → C5)
    s["leg_b_d"] = True
    assert V.classify_combo(s) == "C5"


def test_classify_c4_reject_f():
    s = {"leg_a_pass": True, "ev_te": -0.3, "ev_ft": -1.0,
         "leg_b_d": True, "leg_b_all": False, "knife_all": False}
    assert V.classify_combo(s) == "C4"


def test_overall_verdict_branches():
    assert V.overall_verdict(["C5", "C5", "C2"]) == "FAIL"
    assert V.overall_verdict(["C3", "C5"]) == "UNDERPOWERED"
    assert V.overall_verdict(["C1", "C3", "C5"]) == "PASS"


# ─── ナイフエッジ ───────────────────────────────────────────────────────────
def test_knife_fold_lofo():
    # 2024 fold に効果集中 → 除外で符号反転 → fail
    net = np.array([10.0] * 6 + [-1.0] * 6)
    folds = np.array(["2024"] * 6 + ["2025"] * 6)
    r = V.knife_fold_lofo(net, folds)
    assert r["best_fold"] == "2024" and r["pass"] is False
    # 均等な正効果 → pass
    net2 = np.array([2.0] * 6 + [1.0] * 6)
    assert V.knife_fold_lofo(net2, folds)["pass"] is True


def test_knife_top_block_share():
    # top block 寄与 = 50/110 ≈ 45% > 40% → fail
    net = np.array([50.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    blocks = np.array(["e1", "e2", "e3", "e4", "e5", "e6", "e7"])
    r = V.knife_top_block(net, blocks)
    assert r["top_block"] == "e1" and r["pass"] is False
    # 均等 → share=1/7 ≤ 40% ∧ 除外後正 → pass
    net2 = np.full(7, 10.0)
    assert V.knife_top_block(net2, blocks)["pass"] is True


def test_knife_lopo_and_collision_excl():
    net = np.array([5.0, 5.0, 5.0, -30.0])
    pairs = np.array(["EUR_USD", "GBP_USD", "USD_JPY", "EUR_USD"])
    # EUR_USD を除くと mean(5,5)=5>0 だが、USD_JPY を除くと mean(5,5,-30)<0 → fail
    assert V.knife_lopo(net, pairs)["pass"] is False
    assert V.knife_lopo(np.full(4, 2.0), pairs)["pass"] is True
    # collision 除外: フラグ 0 件 = vacuous pass
    r = V.knife_excl_mask(net, np.zeros(4, dtype=bool), "collision")
    assert r["pass"] is True and r["n_excluded"] == 0
    # 負け trade が collision → 除外後も符号維持 (full<0, rest... ) を検査
    full_pos = np.array([3.0, 3.0, -2.0])
    r2 = V.knife_excl_mask(full_pos, np.array([False, False, True]),
                           "collision")
    assert r2["pass"] is True and r2["rest_ev"] == pytest.approx(3.0)


# ─── 隣接格子点列挙 (§5c-2) ─────────────────────────────────────────────────
def test_neighbors_enumeration():
    c = {"family": "e15", "event": "FOMC", "rule": "follow",
         "w0": 60, "h": "h12"}
    keys = sorted(V.combo_key(n) for n in V.neighbors_of(c))
    assert keys == sorted(["FOMC|follow|w030|h12", "FOMC|follow|w060|h4",
                           "FOMC|follow|w060|h24"])
    # h 端 (h24) は隣 1 つ + W0 の計 2
    c2 = {"family": "e15", "event": "CPI", "rule": "fade",
          "w0": 30, "h": "h24"}
    keys2 = sorted(V.combo_key(n) for n in V.neighbors_of(c2))
    assert keys2 == sorted(["CPI|fade|w060|h24", "CPI|fade|w030|h12"])
    # uncond は W0 固定 → h 隣のみ
    c3 = {"family": "e15", "event": "NFP", "rule": "uncond_usd_long",
          "w0": 30, "h": "h12"}
    assert len(V.neighbors_of(c3)) == 2


# ─── OOS 窓ガード (§3.4 t_e 帰属) ───────────────────────────────────────────
def test_oos_window_guard():
    cal = {"CPI": ["2023-12-12T13:30:00+00:00",   # 探索窓 → 除外
                   "2024-01-11T13:30:00+00:00",   # OOS → 採用
                   "2026-06-10T12:30:00+00:00",   # OOS 末端 → 採用
                   "2026-07-15T12:30:00+00:00"]}  # 窓外 → 除外
    evs = V.oos_events(cal, "CPI")
    assert len(evs) == 2
    assert all(pd.Timestamp("2024-01-01", tz="UTC") <= t
               <= pd.Timestamp("2026-07-01", tz="UTC") for t in evs)


# ─── join 契約: gross 抽出 + 摩擦線形適用 = event_trade(friction=判定値) ──────
def test_gross_plus_friction_equals_lib_net(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(300)
    t_e = m.index[100]
    m.iloc[102, m.columns.get_loc("Open")] = 1.1000
    m.iloc[102 + 96, m.columns.get_loc("Open")] = 1.1030
    gross = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24",
                          friction=0.0)
    net = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24")
    assert net.time_exit_pip == pytest.approx(
        gross.time_exit_pip - L.FRICTION["EUR_USD"])
    assert net.first_touch_pip == pytest.approx(
        gross.first_touch_pip - L.FRICTION["EUR_USD"])


# ─── entry +1 バー遅延 (§5c-3): entry のみ動き R0 は不変 ─────────────────────
def test_entry_delay_shifts_entry_only(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(300)
    t_e = m.index[100]
    m.iloc[102, m.columns.get_loc("Open")] = 1.1000   # 通常 entry バー
    m.iloc[103, m.columns.get_loc("Open")] = 1.1010   # 遅延 entry バー
    base = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24",
                         friction=0.0)
    delay = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24",
                          friction=0.0, entry_delay_bars=1)
    assert base.entry_pos == 102 and delay.entry_pos == 103
    # delay=0 は従来挙動と同一 (default 不変)
    base2 = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24",
                          friction=0.0, entry_delay_bars=0)
    assert base2.entry_pos == base.entry_pos
    assert base2.time_exit_pip == pytest.approx(base.time_exit_pip)
    # fade/follow の R0 定義 (W0 窓) は遅延で不変 — 方向が同じ
    m.iloc[100, m.columns.get_loc("Open")] = 1.1000
    m.iloc[101, m.columns.get_loc("Close")] = 1.1010   # R0 > 0
    f0 = L.event_trade(m, m, t_e, "EUR_USD", "follow", 30, "h24",
                       friction=0.0)
    f1 = L.event_trade(m, m, t_e, "EUR_USD", "follow", 30, "h24",
                       friction=0.0, entry_delay_bars=1)
    assert f0.direction == f1.direction == 1


# ─── TradeOutcome.atr 露出 (レグ A 正規化用) ────────────────────────────────
def test_trade_outcome_exposes_atr(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0064)
    m = _make_m15(300)
    out = L.event_trade(m, m, m.index[100], "EUR_USD", "uncond_usd_short",
                        30, "h24", friction=0.0)
    assert out.atr == pytest.approx(0.0064)


# ─── §5c-3 canary の検出能力: 注入リークを False で検出すること ──────────────
def test_leak_canary_detects_injected_r0_leak(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(300)
    t_e = m.index[100]
    m.iloc[110, m.columns.get_loc("Close")] = 1.2000   # entry 後の未来バー

    def leaky_r0(m15, t_e_, w0_min):
        # 未来リターン (entry 後バー) を R0 経路に注入した壊れた実装
        return float(m15["Close"].iloc[110]) - float(m15["Open"].iloc[100])

    monkeypatch.setattr(L, "compute_r0", leaky_r0)
    assert L.leak_canary(m, m, t_e, "EUR_USD", "follow", 30, "h24") is False


def test_leak_canary_detects_injected_atr_leak(monkeypatch):
    m = _make_m15(96 * 40)
    t_e = m.index[96 * 30]

    def leaky_atr(daily, t):
        # 未来 daily バー数に依存する壊れた ATR (poison で行数が変わる → 検出)
        return 0.0001 * len(daily)

    monkeypatch.setattr(L, "atr14d_before", leaky_atr)
    assert L.leak_canary(m, m, t_e, "EUR_USD", "uncond_usd_short",
                         30, "h24") is False


def test_leak_canary_clean_engine_passes(monkeypatch):
    # 対照: 本物のエンジン (無注入) は True — 検出器が過検出しないこと
    m = _make_m15(96 * 40)
    daily = L.build_daily_from_m15(m)
    t_e = m.index[96 * 30]
    assert L.leak_canary(m, daily, t_e, "EUR_USD", "uncond_usd_short",
                         30, "h24") is True


# ─── p_combo = max(p_boot, p_IM) + 判定パイプ end-to-end (合成) ──────────────
def test_run_verdict_p_combo_max_and_pipeline():
    ext = V._synth_extracted(effect_pip=25.0)
    out = V.run_verdict(ext, n_boot=400)
    r = out["results"][0]
    assert r["leg_a"]["p_combo"] == pytest.approx(
        max(r["leg_a"]["p_boot"], r["leg_a"]["im"]["p"]))
    assert r["classification"] == "C1" and out["verdict"] == "PASS"
    # null → 非有意 + FAIL
    out_null = V.run_verdict(V._synth_extracted(effect_pip=0.0), n_boot=400)
    assert out_null["verdict"] == "FAIL"
    # UNDERPOWERED 分岐: blocks を 15 未満に (機構整合 te>0 ∧ ft>0 のまま)
    ext_up = V._synth_extracted(effect_pip=25.0, n_events=10)
    out_up = V.run_verdict(ext_up, n_boot=400)
    assert out_up["results"][0]["classification"] == "C3"
    assert out_up["verdict"] == "UNDERPOWERED"


def test_run_verdict_empty_trades_fail_loud():
    ext = V._synth_extracted(effect_pip=25.0)
    ext["candidates"][0]["trades"] = []
    out = V.run_verdict(ext, n_boot=100)
    assert out["results"][0]["classification"] == "C5"
    assert out["verdict"] == "FAIL"
