# Shadow-only Strategy Coverage & WIN Characterization

**日付**: 2026-04-21
**修正**: 先の [[strategy-coverage-audit-2026-04-21]] は Live 列を含めてしまった.
ユーザー指示 "LIVE ではなく shadow で" に従い、**純粋に shadow data のみ**で再分析.

## 1. Classification 集計 (shadow only)

全 60 tier-master 戦略 + 5 ghost strategies = 65 entries:

| Level | 基準 | N | 比率 |
|---|---|---:|---:|
| L1-characterized | Shadow WIN ≥ 15 | 12 | 18% |
| L2-partial | Shadow WIN 5-14 | 4 | 6% |
| L3-sparse | Shadow WIN 1-4 | 19 | 29% |
| L4-no-wins | Shadow WIN = 0 | 30 | 46% |
| └ L4a fired-but-lost | Shadow LOSS ≥ 1 | 9 | |
| └ L4b never-fired | Shadow ALL = 0 | 21 | |

## 2. L1: Full Shadow Characterization — 参照先

[[win-characterization-2026-04-21]] に 12 戦略の winner profile を記録済 (shadow ベース).

## 3. L2: Shadow Minimal Profile (新情報)

### 3.1 dt_sr_channel_reversal (WR 32.4%, W=12 L=25)

| Feature | Shadow WIN pattern | LR |
|---|---|---:|
| Session | **Tokyo** (4/12) | **2.78** ★ |
| Instrument | USD_JPY 50%, GBP_USD 25% | — |
| Direction | BUY 58% | 0.86 |
| ADX Q50 | **40.6** (強トレンド) | — |
| ATR_ratio | 1.04 (mid) | — |

**発見**: Tokyo session × 強トレンドで winner. UNIVERSAL_SENTINEL だが Tokyo 限定なら promote 候補.

### 3.2 vol_surge_detector (WR 24.4%, W=10 L=31) — 本日 USD_JPY 復活

| Feature | Shadow WIN pattern | LR |
|---|---|---:|
| Session | **London** (4/10) | **2.48** ★ |
| Instrument | USD_JPY 70% (本日復活 trial と一致) | — |
| Direction | 5BUY/5SELL 均衡 | — |
| ADX Q50 | 32.2 | — |
| ATR_ratio | 1.34 (高 volatility 嗜好) | — |
| Confidence | **WIN med=54 / LOSS med=63** | 逆向き |

**発見**: London session + 高 volatility が winner. **Confidence 逆向き signal は 4 戦略目** (bb_rsi, bb_squeeze, ema_cross, vol_surge). Scoring 構造 bug 仮説を補強.

### 3.3 trend_rebound (WR 40.9%, W=9 L=13)

| Feature | Shadow WIN pattern |
|---|---|
| Instrument | USD_JPY 56% |
| Direction | **SELL 67%** |
| Session | balanced (NY/London/Tokyo ~equal) |
| ADX Q50 | 31.7 (強トレンド) |
| ATR_ratio | 1.04 |

**発見**: High-WR だが session 独立. USD_JPY SELL で強トレンド時の rebound が機能.

### 3.4 ema200_trend_reversal (WR 40.0%, W=8 L=12)

| Feature | Shadow WIN pattern | LR |
|---|---|---:|
| Direction | **SELL 75%** | **2.25** ★ |
| Instrument | USD_JPY 75% |
| ADX Q50 | **17.5 (LOW — range 環境)** | — |
| Confidence | **WIN med=58 / LOSS med=42** (正向き!) | — |

**発見**: **ema200_trend_reversal は confidence signal が正向き** (高 conf が勝つ). L1 で逆向きだった bb_rsi/bb_squeeze/ema_cross と対照的. 戦略間で scoring 挙動が分かれる = 戦略依存.

## 4. L3: Per-trade WIN Listing (19 戦略)

以下は shadow で WIN 1-4 回だった戦略 (情報量少なめ). 特記事項のみ:

### 4.1 🚨 vwap_mean_reversion — 最重要 red flag

| Shadow | W=1 L=10 WR=**9.1%** |
|---|---|
| 現 Tier | **PAIR_PROMOTED × 4 pair** (EUR_JPY, GBP_JPY, EUR_USD, GBP_USD) |
| LOT_BOOST | **1.8x × 2 (EUR_JPY/GBP_JPY)**, 2.0x (JPY cross 他) |
| Shadow 唯一の WIN | 2026-04-21 GBP_USD SELL tokyo conf=50 ADX=24 |

**BT claim**: EUR_JPY EV=+3.85, GBP_JPY EV=+5.17, GBP_USD EV=+0.758, EUR_USD EV=+0.615
**Shadow 実測**: WR 9.1% (N=11)

**gap 巨大**. dt_fib_reversal (本日 Audit B 第一弾で demote) と同じパターン. **次セッション Audit B 第二弾の最優先候補**.

### 4.2 wick_imbalance_reversion — 0 wins

| Shadow | W=0 L=2 |
|---|---|
| 現 Tier | PAIR_PROMOTED × GBP_USD |
| 発火頻度 | 非常に低い (N=2) |

**BT claim**: GBP_USD N=40 WR=70% EV=+0.123. **Shadow で再現せず N 極少**.

### 4.3 その他注目 L3

- **xs_momentum** (PAIR_PROMOTED): Shadow W=3 すべて `GBP_USD BUY NY conf=73` の 3 件同一パターン — 特定条件依存
- **vix_carry_unwind** (PAIR_PROMOTED): Shadow W=2 both `USD_JPY SELL London/Tokyo conf=70`
- **squeeze_release_momentum** (PAIR_PROMOTED): Shadow W=1 GBP_USD BUY Tokyo
- **post_news_vol** (PAIR_PROMOTED): Shadow W=4 mixed sessions

これら **PAIR_PROMOTED で shadow N が極少** の戦略群は、Audit B 第二弾の対象群. BT-Live/Shadow 乖離を個別確認すべき.

## 5. L4a: Fired But Lost All (9 戦略)

| Strategy | Shadow L | Tier | 備考 |
|---|---:|---|---|
| streak_reversal | 4 | UNIVERSAL_SENTINEL (削除候補) | - |
| vol_spike_mr | 3 | UNIVERSAL_SENTINEL | 全 shadow 負け |
| donchian_momentum_breakout | 2 | ghost (tier-master 未登録) | - |
| session_time_bias | 2 | **ELITE_LIVE** | Shadow 0W 2L. BT 正 EV だが shadow 負け. 要監視 |
| wick_imbalance_reversion | 2 | **PAIR_PROMOTED** | 上記参照 |
| htf_false_breakout | 1 | UNIVERSAL_SENTINEL | |
| intraday_seasonality | 1 | FORCE_DEMOTED | |
| mtf_reversal_confluence | 1 | UNIVERSAL_SENTINEL | |
| three_bar_reversal | 1 | Phase0 Shadow Gate | |

**session_time_bias (ELITE_LIVE)** は shadow N=2 と極少だが 0 勝. ELITE_LIVE 昇格の根拠が shadow で弱い.

## 6. L4b: Never Fired in Shadow (21 戦略)

全く shadow trade が発生していない戦略:

**ELITE_LIVE / PAIR_PROMOTED (要調査)**:
- **gbp_deep_pullback** (ELITE_LIVE) — 発火条件故障疑い

**Phase0 Shadow Gate (未昇格, 通常)**:
- adx_trend_continuation, confluence_scalp, gold_pips_hunter, gold_trend_momentum, gold_vol_break, hmm_regime_filter, jpy_basket_trend, london_breakout, london_fix_reversal, london_ny_swing, london_session_breakout, london_shrapnel, session_vol_expansion, tokyo_nakane_momentum, turtle_soup

**Stopped (XAU)**:
- gold_pips_hunter, gold_trend_momentum, gold_vol_break (XAU v8.4 stopped)

**その他**:
- atr_regime_break (FORCE_DEMOTED), eurgbp_daily_mr, gotobi_fix, liquidity_sweep

## 7. Ghost Strategies (tier-master 未登録)

shadow trade は出ているが tier-master の sync 漏れ:

| Strategy | Shadow W | Shadow L |
|---|---:|---:|
| dual_sr_bounce | 2 | 20 |
| pivot_breakout | 2 | 3 |
| h1_fib_reversal | 1 | 4 |
| ny_close_reversal | 1 | 3 |
| donchian_momentum_breakout | 0 | 2 |

**修正必要**: tier-master drift. これらは code には残っているが wiki/tier に反映されていない.

## 8. 本日の WIN 分析の真の scope (shadow only)

- 12 戦略 (L1) : 深く characterize 済
- 4 戦略 (L2) : shadow minimal profile を本文書で追加
- 19 戦略 (L3) : per-trade listing のみ (統計不可)
- 30 戦略 (L4) : shadow wins 0 (分析不可能)

**総 shadow 分析可能 = 16 戦略 (25%) / 65 entries**

## 9. 次セッション Shadow-based 優先順位

### 優先度 A (urgent)
1. **vwap_mean_reversion Audit B**: PAIR_PROMOTED ×4 pair だが shadow WR 9.1%. dt_fib_reversal と同じ demote 候補検討
2. Ghost 5 戦略の tier-master 統合

### 優先度 B
3. L2 戦略 (dt_sr_channel_reversal, vol_surge_detector, trend_rebound, ema200_trend_reversal) の shadow winner profile を戦略 wiki に反映
4. Confidence 逆向き signal (4 戦略: bb_rsi, bb_squeeze, ema_cross, vol_surge_detector) の scoring 構造 audit

### 優先度 C (data 蓄積後)
5. L3 戦略の shadow N 蓄積待ち (2026-05-05)
6. L4b never-fired 戦略の発火条件診断 (特に gbp_deep_pullback ELITE_LIVE)

## 10. Source

- Script: `/tmp/shadow_only_coverage.py`
- Raw output: `/tmp/shadow_coverage.txt` (191 lines)
- 先行: [[strategy-coverage-audit-2026-04-21]] (Live 混在で誤り — 本文書で訂正)
- 関連:
  - [[win-characterization-2026-04-21]] (L1 12 戦略の shadow winner profile)
  - [[win-conditions-unfiltered-2026-04-21]] (portfolio-wide)
