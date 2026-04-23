# Edge Matrix — Session × Horizon × Regime (2026-04-23)

**目的**: Tokyo/London/NY × Scalp(1m/5m)/DT(15m) × Range/Trend の 3 軸で、
数学的クオンツ観点から「検証すべきエッジ」を体系化する。

**位置づけ**: 観測前の仮説マップ。実装提案ではない。
判断プロトコル (CLAUDE.md) 遵守: Shadow N≥30 + walk-forward 730d 再検証後に判断。

---

## 0. 軸の定義

### Session (UTC)
| Session | UTC | JST | 特性 |
|---------|-----|-----|------|
| Tokyo | 0–7 | 9–16 | 低 σ / range 優位 / Gotobi effect |
| London | 7–13 | 16–22 | 中 σ / trend 開始 / order flow 主導 |
| NY | 13–21 | 22–06 | 高 σ / fundamentals 主導 / news 反応 |
| Off | 21–24 | 06–09 | 流動性最低 / noise |

**現実観測値** (session-zoo-2026-04-23.md, portfolio-wide):
- Tokyo: N=1456 EV=+0.273 WR=17.5% (per trade_log row count share)
- London: N=3758 EV=+0.256 WR=45.1%
- NY: N=3065 EV=+0.123 WR=36.8%

### Horizon
| Horizon | TF | Target | Friction impact |
|---------|-----|--------|----------------|
| Scalp | 1m/5m | 3-10 pip | **極大** (RT 2-4.5 pip で WR_BE > 50%) |
| DT | 15m | 10-30 pip | 中 (RT 2-4.5 pip で WR_BE > 35%) |
| Swing | 1h/4h | 30-100 pip | 小 |

### Regime
| Regime | Hurst H | 戦略相性 |
|--------|---------|----------|
| Range | H < 0.45 | mean-reversion 優位 |
| Neutral | 0.45 ≤ H ≤ 0.55 | 混合 |
| Trend | H > 0.55 | momentum / breakout 優位 |

---

## 1. Tokyo Session エッジ仮説

### T1. AR(1) Momentum Alignment
**仮説**: Tokyo は intra-session autocorrelation が正 (Baillie-Bollerslev 1989)。
prior 5-bar return 符号がエントリー方向と一致する場合 WR が上昇する。

**Math**:
- ρ_TOK(5bar) ≈ +0.05-0.08 (FX intraday の既知値)
- P(trade win | aligned) - P(trade win | counter) ≥ 0.05 が観測できれば有意

**Tool**: `tools/edge_lab.py` T1 セクション
**N要件**: session × pair で N≥50
**Priority**: ⭐⭐⭐

### T2. Gotobi Effect (JPY pairs only)
**仮説**: 5,10,15,20,25,月末に日系輸出企業の JPY 買い決済フローが集中 (Ito-Hashimoto 2006)。
Tokyo session × JPY 5 および 10 付近で USD_JPY/EUR_JPY/GBP_JPY の
LONG エッジが低下、SHORT エッジが上昇する可能性。

**Math**:
- E[Δ_JPY | Gotobi & Tokyo] - E[Δ_JPY | other] の検定
- t-stat ≥ 2.0 なら Bonferroni 後残る

**Tool**: `tools/edge_lab.py` T2 セクション
**N要件**: JPY × Tokyo × Gotobi で N≥30 (年 60 Gotobi × hit rate ~50%)
**Priority**: ⭐⭐⭐ (JPY scalp フィルタに直結)

### T3. Asia Range Breakout (Tokyo close → London open)
**仮説**: Tokyo 午後〜London 初動で Tokyo range を breakout する場合、
London 流動性流入により trend 継続性が高い (Andersen-Bollerslev 1997)。

**Math**:
- Tokyo range = max(H) - min(L) over UTC 0-7
- Breakout = close > Tokyo_max or close < Tokyo_min at UTC 7-9
- E[|Δ| | breakout] > E[|Δ| | non-breakout] の検定

**Tool**: 新規 `tools/tokyo_range_breakout.py` ✅ 実装済, `tools/tokyo_range_breakout_wfa.py` ✅ WFA 実装済
**N要件**: pair × year で N≈200 (daily 1 event)
**Priority**: ⭐⭐⭐ (当初 ⭐⭐ → 365d BT で強シグナル確認 → WFA で STABLE_EDGE 確定)

**検証結果 (2026-04-23)**:
- 365d BT: USD_JPY UP N=98 mean=+17.67 WR=72.4% t=4.48 (Bonferroni-safe)
- WFA (IS/OOS 各 158-159d): **4/5 ペアで UP breakout STABLE_EDGE**
  - USD_JPY / EUR_JPY / GBP_JPY / GBP_USD = 🟢 STABLE_EDGE
  - EUR_USD = 🟡 NOISY_BUT_ALIVE
  - 全 DOWN breakout = 🟡 NOISY_BUT_ALIVE (variance 大)
- 判定: **構造的エッジ (非カーブフィット)** — Shadow N≥30 段階へ進める準備完了
- 参照: `raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.md`

### T4. Tokyo Fix Mean Reversion (00:55 UTC)
**仮説**: 9:55 JST (Tokyo Fix) 付近で機関系 benchmark flow が集中。
直前 5-10 分のトレンドが Fix 後に reversal する (Osler-Savaser 2011)。

**Math**:
- window [UTC 0:50, 0:55] の return と [UTC 0:55, 1:00] の return の相関
- ρ < -0.1 なら有意
- JPY pair で最強

**Tool**: 新規 `tools/tokyo_fix_reversal.py` 必要
**N要件**: 252 日 (年 252 営業日)
**Priority**: ⭐⭐ (既存戦略 vwap_mean_reversion と重複の可能性)

---

## 2. London Session エッジ仮説

### L1. Order Flow Imbalance (Cont-Kukanov-Stoikov 2014)
**仮説**: London open 直後 (UTC 7:00-8:30) は trade imbalance が最大。
bid/ask volume proxy (bar の wick ratio) が信号になる。

**Math**:
- OFI proxy = (close - low) / (high - low) - 0.5 (wick-based)
- ρ(OFI, next-bar return) > 0.05 なら信号価値あり

**Tool**: 新規 `tools/london_ofi.py` 必要 (tick データ不要、bar proxy 使用)
**N要件**: pair × window で N≥200
**Priority**: ⭐⭐⭐

### L2. London Fix (16:00 BST = 15:00 UTC)
**仮説**: WMR Fix 付近で月末 rebalance flow が集中。GBP pair で trend reversal。
既存戦略 `london_fix_reversal` は BT EV=-0.15 で負 — 再検証。

**Math**:
- month-end 5 days × UTC 14:30-15:30 で return 反転
- 既存の失敗原因: filter が甘い可能性 (month-end & Fix 限定ではなく常時)

**Tool**: `tools/london_fix_reversal.py` (既存) + month-end filter 追加
**N要件**: 12 months × 5 days × 3 pairs = N≥180
**Priority**: ⭐⭐ (失敗戦略の救済、優先度低)

### L3. London-NY Overlap Volatility Burst (UTC 13:00-15:00)
**仮説**: 両 session overlap で σ が 1.3× 上昇 (Andersen-Bollerslev 1997)。
既存 atr_trend_filter と session_time_bias が捕捉しているはず — 再確認。

**Tool**: `tools/bt_session_zoo.py` 既存結果で観察
**Priority**: ⭐ (既存戦略で捕捉済み可能性)

---

## 3. NY Session エッジ仮説

### N1. News-Gated NY Entry
**仮説**: NY 13:30 UTC (major US data) 前後 ±30 分を除くと WR が上昇する。
**Math**: NY trade を {pre-news, post-news, news-free} に分類し WR 差を検定。
**Tool**: 新規 `tools/nfp_gated_ny.py` — 経済指標カレンダー使用 (FRED API or static)
**N要件**: 12 months × ~20 events = N≈240
**Priority**: ⭐⭐⭐ (friction 最大の NY での selective entry)

### N2. NY Close Drift (UTC 20:00-21:00)
**仮説**: NY close 直前 1 時間は liquidity 枯渇で small-cap 動き。
既存 FORCE_DEMOTED 戦略に含まれる可能性。
**Priority**: ⭐

### N3. NY Open Gap Fade
**仮説**: Tokyo close (UTC 7:00 日本時間 16:00) → NY open (UTC 13:30) gap を fade。
**Math**: gap = open_NY - close_Tokyo, return_NY_first_hour と ρ < 0 なら fade エッジ。
**Priority**: ⭐⭐

---

## 4. Scalp (1m/5m) エッジ仮説

### S1. Tick Imbalance (1m)
**仮説**: 1m bar の wick ratio が high-σ 条件下で反転シグナル。
**Math**: wick_ratio = |open-close| / (high-low); < 0.3 かつ σ_z > 1.0 で MR エッジ。
**N要件**: 1m × 30d × 5 pairs = N≈216,000 bar
**Priority**: ⭐⭐

### S2. Micro Liquidity Holes (1m vol spike)
**仮説**: 1m bar の vol が 95th percentile を超える直後 2-3 bars で MR。
**Priority**: ⭐⭐

### S3. Round-Number Magnetism (Osler 2003)
**仮説**: 価格が .00/.50 (JPY) or .0000/.0050 (non-JPY) に接近する際に reaction。
**Math**: distance_pips < 2.0 の bar で SHORT/LONG bias を検定。
**Tool**: `tools/edge_lab.py` S3 セクション
**N要件**: all bars, close < 2pip from round = ~10% = N≈36,500
**Priority**: ⭐⭐⭐

### S4. Sub-Bar Momentum Persistence
**仮説**: 5m bar の prior 3 bars 同方向連続後 1-bar 継続確率 > 50%。
**Priority**: ⭐

---

## 5. DT (15m) エッジ仮説

### D1. Volatility Regime Filter
**仮説**: σ_20bar z-score (対 σ_60bar baseline) の quintile で WR 差が出る。
- Q1 (low vol): MR 戦略優位
- Q5 (high vol): trend 戦略優位
- Q3 (mid vol): friction が最大に相対的に重く負 EV

**Math**: σ_z = (σ_20 - μ_σ_60) / std_σ_60
**Tool**: `tools/edge_lab.py` D1 セクション
**N要件**: 既存 trade_log すべて = N≈8,000
**Priority**: ⭐⭐⭐

### D2. ATR-normalized stop (既存 vs fixed-pip)
**仮説**: 既存 fixed-pip stop は高 σ 期で過早 stop out。
ATR-normalized stop で WR が上昇するか。
**Priority**: ⭐⭐

### D3. Multi-timeframe Agreement (15m × 1h × 4h)
**仮説**: 3 TF EMA slope が同方向の場合のみエントリー → WR 上昇。
既存 HMM agreement cache が類似機能を持つ — 再確認。
**Priority**: ⭐⭐

---

## 6. Range/Trend Regime エッジ仮説

### R1. Hurst-Gated Strategy Selection
**仮説**: H < 0.45 では MR 戦略 only, H > 0.55 では trend 戦略 only。
既存 mean_reversion 系 と momentum 系 の strategy-pair separation を Hurst で switch。

**Math**: R/S analysis on 50 prior 15m bars; H ∈ [0, 1]
**Tool**: `tools/edge_lab.py` R1 セクション
**N要件**: 既存 trade_log すべて
**Priority**: ⭐⭐⭐ (最も汎用)

### R2. ADX Trend Strength
**仮説**: ADX > 25 で trend 戦略 EV 上昇、< 20 で MR 戦略 EV 上昇。
**Priority**: ⭐⭐ (ADX は既存 indicator)

### R3. Volatility Term Structure
**仮説**: σ_short / σ_long ratio > 1.3 → short-term vol expansion → breakout probability up。
**Priority**: ⭐

---

## 7. Trend-specific エッジ仮説

### TR1. Trend Exhaustion (RSI divergence)
**仮説**: price new high + RSI lower high → trend exhaustion → MR entry。
**Priority**: ⭐⭐

### TR2. Pullback Depth Optimization
**仮説**: trend 中の 38.2% / 50% / 61.8% Fib pullback でエントリー。
既存 gbp_deep_pullback が類似 — 他 pair に拡張余地。
**Priority**: ⭐⭐

### TR3. Breakout Confirmation (volume + range)
**仮説**: breakout bar の volume が 20-bar median × 1.5 以上なら true breakout。
FX は volume proxy なので bar range で代替。
**Priority**: ⭐⭐

### TR4. Trend Day Filter (opening range breakout)
**仮説**: NY open 30 分 range を breakout する日は trend day。後続 bars を trend 方向に限定。
**Priority**: ⭐⭐

---

## 8. 優先度統合マトリクス

### ⭐⭐⭐ (即座に観察すべき、N既存 or 薄データで成立)
| ID | エッジ | データ源 | Status (2026-04-23) |
|----|-------|---------|--------------------|
| **T3** | Tokyo Range UP breakout × 4 pair | tokyo_range_breakout_wfa.py | 🟢 **STABLE_EDGE 確定 → Shadow 候補** |
| T1 | AR(1) momentum × session | edge_lab.py (post-hoc) | 🔴 **逆向き** — counter-alignment (MR) が momentum より高 EV |
| T2 | Gotobi × JPY | edge_lab.py + calendar | 🔴 **not actionable** — Bonferroni 後 p>0.05 |
| L1 | London OFI proxy | 新規 `tools/london_ofi.py` | 🟡 weak (ρ<0.05), filter 用途 |
| N1 | News-gated NY | 新規 `tools/nfp_gated_ny.py` | ⏸ 次セッション (edge_lab 再実行後 post-hoc) |
| S3 | Round-number magnetism | edge_lab.py (post-hoc) | 🟡 pair依存 (USD_JPY/GBP_JPY close, EUR_USD far) |
| D1 | Vol z-score quintile | edge_lab.py (post-hoc) | 🟡 pair依存 (USD_JPY/EUR_USD low vol, EUR_JPY high vol) |
| R1 | Hurst regime | edge_lab.py (post-hoc) | 🔴 **不使用** — regime EV 差 <0.1p で discriminator 弱 |

### ⭐⭐⭐ 補足: Cross hypothesis 発見
| Cross | 発見 | 含意 |
|-------|------|------|
| vwap_MR × Hurst | **Trend regime (H>0.55) で最も強い** (USD_JPY +1.47 EV, GBP_JPY +1.15) | 「MR-only in H<0.45」gate は**誤り** — vwap_MR は trend 内 pullback で hit |

### ⭐⭐ (次回優先度、BT データ蓄積後に検証)
T4, L2, N3, S1, S2, D2, D3, R2, TR1-TR4

### ⭐ (低優先、既存戦略で捕捉済み可能性)
L3, N2, S4, R3

---

## 9. 次ステップ (観察フェーズ)

### 実行順
1. **edge_lab.py 実行** — T1/T2/D1/R1/S3 を 1 passで (実行中)
2. **結果解釈** — CLAUDE.md 判断プロトコル (1 BT では実装不可、walk-forward 730d 必須)
3. **新規ツール構築** — L1 (london_ofi), N1 (nfp_gated_ny), T3 (tokyo_range_breakout)
4. **Shadow N≥30 蓄積判断** — 最良 quartile/quintile のみ観察登録

### 判断プロトコル
- **GO 条件**: (a) N ≥ min-n AND (b) Top - Bottom quintile EV 差 ≥ 0.3pip AND (c) 複数 pair で同方向の傾き
- **NO-GO**: Bonferroni-corrected p > 0.05

### 保留事項
- Phase 2 の VWAP conf_adj re-calibration (strategy-category-specific) — 別セッション
- sr_fib_confluence_tight_sl 実装 — VWAP fix 再測定後

---

## Source & Generation
- Generated: 2026-04-23
- Related: raw/bt-results/session-zoo-2026-04-23.md (Tokyo edge discovery)
- Tool: tools/edge_lab.py (T1/T2/D1/R1/S3 unified analyzer)
- Protocol: CLAUDE.md 判断プロトコル (observation only until WF 730d)
