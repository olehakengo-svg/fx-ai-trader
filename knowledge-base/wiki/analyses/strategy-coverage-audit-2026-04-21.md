# Strategy Coverage Audit — 2026-04-21 Shadow/Live 完全 accounting

**日付**: 2026-04-21
**問い**: 本日の WIN characterization は 60 戦略のうち何 % をカバーしたか?

**結論**: **12/60 = 20% のみ深く characterize**. 残り 48 戦略 (80%) は insufficient/no data/never-fired.

---

## 1. Classification 集計

| Level | 基準 | N | 比率 |
|---|---|---:|---:|
| **L1-characterized** | Shadow WIN ≥ 15 | **12** | 20% |
| L2-partial | Shadow WIN 5-14 | 4 | 7% |
| L3-sparse | Shadow WIN 1-4 | 15 | 25% |
| **L4-no-wins** | Shadow WIN=0 (含 ELITE_LIVE) | **29** | 48% |

---

## 2. L1: Characterized (12 戦略) ← 本日の分析対象

| Strategy | S_Win | S_Loss | S_WR | L_Win | L_Loss | L_WR |
|---|---:|---:|---:|---:|---:|---:|
| ema_trend_scalp | 71 | 223 | 24.1% | 0 | 0 | — |
| fib_reversal | 66 | 120 | 35.5% | 0 | 0 | — |
| stoch_trend_pullback | 42 | 102 | 29.2% | 0 | 0 | — |
| **bb_rsi_reversion** | 38 | 92 | 29.2% | **120** | **135** | **47.1%** |
| engulfing_bb | 32 | 70 | 31.4% | 0 | 0 | — |
| macdh_reversal | 30 | 80 | 27.3% | 0 | 0 | — |
| sr_channel_reversal | 30 | 96 | 23.8% | 0 | 0 | — |
| sr_fib_confluence | 25 | 77 | 24.5% | 0 | 0 | — |
| bb_squeeze_breakout | 23 | 62 | 27.1% | 0 | 0 | — |
| ema_pullback | 17 | 25 | 40.5% | 0 | 0 | — |
| dt_bb_rsi_mr | 16 | 19 | 45.7% | 0 | 0 | — |
| ema_cross | 16 | 30 | 34.8% | 0 | 0 | — |

**注**: 12 戦略中 **11 が shadow-only** (Live 0件). **bb_rsi_reversion のみ Live 120W/135L WR 47%** — 唯一 live characterization が可能.

これは重要な制約: 本日の shadow WIN conditions はすべて shadow-derived. Live での再現性は未検証.

## 3. L2: Partial (4 戦略) — narrative のみ可能

| Strategy | S_Win | S_Loss | S_WR | L_Win | L_Loss | L_WR | 備考 |
|---|---:|---:|---:|---:|---:|---:|---|
| dt_sr_channel_reversal | 12 | 24 | 33.3% | 5 | 5 | 50.0% | |
| vol_surge_detector | 10 | 31 | 24.4% | 21 | 22 | 48.8% | **本日 USD_JPY 復活** |
| trend_rebound | 9 | 13 | 40.9% | 5 | 11 | 31.2% | post-Cutoff positive |
| ema200_trend_reversal | 8 | 12 | 40.0% | 0 | 2 | 0.0% | |

## 4. L3: Sparse (15 戦略) — 個別 trade 記述のみ

| Strategy | S_Win | L_Win | 備考 |
|---|---:|---:|---|
| orb_trap | 4 | 0 | FORCE_DEMOTED |
| post_news_vol | 4 | 2 | PAIR_PROMOTED × GBP/EUR |
| sr_break_retest | 3 | 0 | FORCE_DEMOTED |
| trendline_sweep | 3 | 0 | ELITE_LIVE でも shadow のみ |
| v_reversal | 3 | 0 | |
| xs_momentum | 3 | 0 | PAIR_PROMOTED × GBP/EUR |
| dt_fib_reversal | 2 | 0 | **本日 PAIR_PROMOTED 撤回** |
| ema_ribbon_ride | 2 | 0 | |
| vix_carry_unwind | 2 | 0 | |
| vol_momentum_scalp | 2 | 8 | PAIR_PROMOTED EUR_JPY |
| doji_breakout | 1 | 1 | PAIR_PROMOTED |
| inducement_ob | 1 | 0 | FORCE_DEMOTED |
| lin_reg_channel | 1 | 0 | FORCE_DEMOTED |
| squeeze_release_momentum | 1 | 0 | PAIR_PROMOTED |
| vwap_mean_reversion | 1 | 1 | PAIR_PROMOTED 4 pairs |

**注目**: `vwap_mean_reversion` は **4 pair PAIR_PROMOTED** だが Live N=2 のみ (W=1 L=1). 次 Audit B 第二弾の最重要対象.

## 5. L4: No-wins (29 戦略) — **half the system**

### 5.1 完全未 fire (shadow も live も 0)

| Strategy | Tier | 懸念度 |
|---|---|---|
| **gbp_deep_pullback** | **ELITE_LIVE** | 🚨 **高** — 全く発火しない ELITE |
| gold_* (4 戦略) | daytrade PP/EL未指定 | 中 — XAU stopped |
| confluence_scalp, london_*, session_vol_expansion 等 | daytrade PP/EL未指定 | 低 — 未昇格戦略 |
| adx_trend_continuation, gotobi_fix, hmm_regime_filter, jpy_basket_trend, tokyo_nakane_momentum, turtle_soup | Phase0 Shadow Gate | 中 — shadow 蓄積中 |
| atr_regime_break | FORCE_DEMOTED | 低 — 全 BT 劣悪 |

### 5.2 Live-only firing (shadow なし、live only)

| Strategy | L_W | L_L | L_WR | 備考 |
|---|---:|---:|---:|---|
| mtf_reversal_confluence | 5 | 4 | **55.6%** | 健闘 |
| gold_trend_momentum | 2 | 1 | 66.7% | 小 N, XAU |
| three_bar_reversal | 1 | 1 | 50.0% | 小 N |
| liquidity_sweep | 1 | 0 | 100% | N=1 |
| htf_false_breakout | 1 | 0 | 100% | N=1 |

### 5.3 **ELITE_LIVE / PAIR_PROMOTED で負け確定中**

| Strategy | Live | WR | 🚨 |
|---|---:|---:|---|
| **session_time_bias** (ELITE_LIVE) | 0W, 4L | **0.0%** | 🚨 全敗 |
| **streak_reversal** (Phase0 SG) | 0W, 4L (shadow) | 0.0% | 高懸念 |
| vol_spike_mr (UNIVERSAL_SENTINEL) | 0W, 3L (shadow) | 0.0% | 中 |
| wick_imbalance_reversion (PAIR_PROMOTED GBP_USD) | 0W, 2L (shadow) | 0.0% | 中 |

**session_time_bias** は **ELITE_LIVE tier (最高昇格)** で Live 4 loss / 0 win. 本日の Audit B 第二弾候補として最優先化すべき.

## 6. Tier-master との drift: "Ghost strategies"

trade data に firing があるが tier-master に載っていない:

| Strategy | Occurs | 備考 |
|---|---|---|
| donchian_momentum_breakout | 2 shadow_loss | tier-master 未登録の死コード firing? |
| dual_sr_bounce | 20 shadow_loss | v9.1 で削除されたはずが残留? |
| h1_fib_reversal | 4 shadow_loss | v9.1 削除対象が残留 |
| ny_close_reversal | 1 shadow_win, 3 shadow_loss | v8.9 新戦略、tier-master 未反映 |
| pivot_breakout | 2 shadow_win, 3 shadow_loss | v9.1 削除対象が残留 |

→ **tier_integrity_check.py は問題なくパスしているが、実コードと tier-master の微妙な drift が存在**. 次セッションでの修正推奨.

## 7. 本日の分析の真の coverage

| Metric | 値 |
|---|---:|
| Tier-master 登録戦略 | 60 |
| 本日 WIN characterized | 12 (20%) |
| L2 partial も含めた characterization | 16 (27%) |
| L3 sparse まで含めた "analyzed" | 31 (52%) |
| **完全に unanalyzed** | **29 (48%)** |

## 8. 提示した "戦略固有 winner profile" の真の適用範囲

本日 [[win-characterization-2026-04-21]] で提示した 8 件の戦略固有 pattern は **L1 = 12 戦略のみ**. 残り 48 戦略には以下の status:

- **L2-L3 (19 戦略)**: 次の shadow 蓄積期間 (2026-05-05) で N=15 到達次第追加分析
- **L4 firing なし (10 戦略)**: そもそも発火しない理由を調査必要
- **L4 live-only (5 戦略)**: live data でのみ characterization (今後)
- **L4 負け確定 (4 戦略)**: 緊急 audit 候補 (特に session_time_bias ELITE_LIVE)

## 9. 即 action 項目 (ユーザー判断待ち)

### 9.1 🚨 session_time_bias 緊急 audit
ELITE_LIVE で Live 0W 4L. 365d BT EV は +0.215/+0.113/+0.580 (3 pair positive) だったが実弾で全敗.
Audit B 第二弾の最優先候補.

### 9.2 🚨 gbp_deep_pullback 発火診断
ELITE_LIVE かつ BT 正 EV だが shadow 0 / live 0. Signal 発火条件を検査.

### 9.3 Tier-master drift 修正
Ghost strategies 5 件を tier-master に反映、または code から削除.

### 9.4 L2-L4 戦略の shadow 蓄積促進
現状 firing が少ない戦略を特定し、条件緩和か廃止判断.

---

## 10. 本日 characterization が covered でない戦略 (次セッション対象)

特に **live で active** だが shadow で不足の戦略は早期 accounting 対象:

- vol_surge_detector (L2, 本日 USD_JPY 復活 trial)
- trend_rebound (L2, 40.9% shadow WR だが live 劣化)
- vwap_mean_reversion (L3, 4 pair PAIR_PROMOTED だが N=2 live)
- post_news_vol (L3, 2 pair PAIR_PROMOTED)
- xs_momentum (L3, 2 pair PAIR_PROMOTED)
- wick_imbalance_reversion (L4, PAIR_PROMOTED GBP_USD だが 0W)

これらは "promoted だが未検証" の最高リスク群.

---

## 11. Source
- Script: `/tmp/strategy_coverage.py`
- Raw output: `/tmp/strategy_coverage_result.txt` (予定)
- Related:
  - [[win-characterization-2026-04-21]] (L1 12 戦略の winner profile)
  - [[audit-b-promoted-strategies-2026-04-21]] (Audit B 第一弾)
  - [[tier-master]] (60 戦略の公式 tier)
