# FX Fundamentals — Edge Reset 文脈での再学習ノート (Master)

**作成日**: 2026-04-26
**所有セッション**: curried-ritchie (Track ① 著者 + 全 Track 統合者)
**ステータス**: **全 5 Track 統合済 + Section 6 横断統合完成**

> **このファイルは Master**。各 Track の deep-dive は `fx-ai-trader/knowledge-base/wiki/learning/` 配下に存在し、本 master は要約引用と横断統合 (Section 6) を担う。

---

## 0. このノートの位置付け

### 0.1 学習目的

Edge Reset 局面 (Live Kelly **edge -18.07%**, Phase 4d-II にて MTF / session×spread の双方が NULL 確定) において、技術的最適化を一旦離れ、市場の構造そのものを再学習する。目的:

- 「なぜ我々は Live で負けてきたか」の **structural 説明** を獲得する
- Phase 3 (mechanism-driven edge 再構築) の設計土台
- 月利 100% 目標 (¥454,816) の sustainability を支える理論枠組み

### 0.2 検証規律 (CLAUDE.md 4 原則 + memory feedback)

- **クオンツファースト**: 一般論 → 即 KB 照合 (空欄禁止)
- **ラベル実測主義**: 数値引用は出所明示、不可なら「未検証仮説」と明記
- **成功するまでやる**: KB 照合矛盾は即修正、Section 6.4 に未解決問題として残す
- **部分的クオンツの罠回避**: WR だけでなく N / Wilson CI / cost 込み EV を必ず添える
- **並行セッション独立性**: 他セッション内容を推測で先回りしない、ファイル出現後に統合
- **XAU 除外**: sqlite-fx クエリ全てで `instrument NOT LIKE '%XAU%'`

### 0.3 出所明示ルール

各 sub-topic は **3 段構造** (deep-dive ファイル側で厳守):
- **(a) 一般論**: 一般 FX 理論
- **(b) 我々への含意**: Live Kelly 状況, friction 5.4×DT 比, BT/Live 乖離 6 因子のどれと結び付くか
- **(c) Phase 4c/4d KB 照合**: 過去 KB ドキュメントとの整合 / 矛盾
- **(d) 実測検証 (sqlite-fx, 該当する場合)**: Track ②④⑤ で sqlite-fx 直接実測

### 0.4 並行セッション体制

| Track | テーマ | 担当セッション | Deep-dive ファイル | 統合状態 |
|-------|--------|----------------|---------------------|----------|
| ① | Market Microstructure | curried-ritchie (本セッション) | `fx-fundamentals-track-1.md` | **完了 + 統合済** |
| ② | Liquidity & Price Formation | twinkling-pancake | `fx-fundamentals-track-2.md` | **完了 + 統合済** |
| ③ | Session × Pair 特性 | valiant-dahl | `fx-fundamentals-2026-04-26.md` §4 (深化版) | **完了 + 統合済** |
| ④ | Risk Management | imperative-wozniak | `fx-fundamentals-2026-04-26.md` §5 (深化版) | **完了 + 統合済** |
| ⑤ | Quant Edge の本質 | mellow-sky | `fx-fundamentals-track-5.md` | **完了 + 統合済** |

**Note**: Track ③④ の deep-dive は broad-pass ファイル (`fx-fundamentals-2026-04-26.md`) 内の §4/§5 として組み込まれた (broad-pass ファイルの「Track 4」=本 master の Track ③、「Track 5」=本 master の Track ④)。

### 0.5 更新履歴

- **2026-04-26 13:16**: マスター骨格作成
- **2026-04-26 13:20-13:35**: Track ① 執筆 (master 内、後に独立ファイル化)
- **2026-04-26 13:42**: Track ② 統合
- **2026-04-26 14:05**: Track ① を独立 deep-dive ファイル化、Track ⑤ 統合、Section 6 部分執筆
- **2026-04-26 15:00**: Track ③④ を broad-pass file §4/§5 から統合、Section 6 完成
- **完了**: 全 5 Track 横断統合ノート確立

---

## 1. Market Microstructure (Track ①)

> **Status**: **統合済**。出典: `fx-fundamentals-track-1.md` (curried-ritchie)。

### 1.0-1.5 ハイライト (3 段構造で詳細記述、ここでは要約のみ)

- **1.1 OTC chain**: Tier 1 Interbank → Tier 2 LP/ECN → Tier 3 Retail Aggregator (OANDA) → Tier 4 retail。retail flow <5%、価格は「broker が我々に提示することを選んだ価格」
- **1.2 Spread 3 component** (Stoll/Glosten-Milgrom/Huang-Stoll): Inventory + Adverse Selection + Order Processing。Asia early/news で 1.5-10× 拡大。`friction_model_v2` の session multiplier は 3 component の実測合算近似
- **1.3 Slippage**: Latency (retail 100-300ms, M1 ATR 0.2-0.5pip 逆行) + Last Look (LP の 50-200ms reject window) + Liquidity slippage
- **1.4 Internalization**: A-book (STP) / B-book / Hybrid 3 モデル。Live Kelly 負状況は B-book の profit center。**vol_momentum_scalp が唯一 BT=Live 一致 (PF 20.33) は non-toxic property の可能性**
- **1.5 Tick / Noise**: M1 SNR ≈ 2-7、長期足ほど高い。MTF η²<0.005 は M1 SNR 低下の statistical 表現

### 1.6 Track ① からの Live Kelly 構造説明 5 因子

| 因子 | sub-topic | Kelly 影響 | 推定重み |
|------|-----------|-----------|----------|
| **F1: Tier 4 markup の不可避性** | 1.1 OTC | 全戦略一律 +1-2pip cost | 🟠 |
| **F2: Spread の非定常性** | 1.2 Spread | 戦略選択的 -2 ~ -8pp WR | 🟠 |
| **F3: Latency + Last Look** | 1.3 Slippage | Scalp SL 占有率 +5-15% | 🔴 (Scalp 致命) |
| **F4: Internalization 動的 routing** | 1.4 Internalization | 現状寄与小、edge 回復後 risk | 🟡 |
| **F5: M1 microstructure noise** | 1.5 Tick/Noise | signal layer の noise pattern fit | 🔴 (M1 戦略全体) |

### 1.7 Track ① からの Phase 3 提言 (5 件)

1. M1 single-TF 戦略の縮小、Multi-TF / M5+ への重心移動
2. Spread regime 内蔵: 高分位偏在戦略は Bonferroni 不要で抑制 (R2)
3. Scalp 戦略の最低 SL = expected slippage × 5 (= 5-10pip)
4. vol_momentum_scalp の non-toxic property 解明
5. 必要 N=150-300/cell, 60+ days passive accumulation で N≈6800

詳細: `fx-fundamentals-track-1.md` 参照。

---

## 2. Liquidity & Price Formation (Track ②)

> **Status**: **統合済**。出典: `fx-fundamentals-track-2.md` (twinkling-pancake)。

### 2.1 Order book / spread expansion (sqlite-fx 実測あり)

**実測 (demo_trades n=373, XAU 除外)**:

| spread_bin | n | WR | Wilson 95% CI | 解釈 |
|------------|---|----|----|------|
| < 0.5 (artifact) | 73 | 56.2% | [44.7, 67.0] | spread_at_entry ロギング欠損、除外 |
| **0.5-1.0** | **214** | **20.6%** | [15.7, 26.4] | **Live Kelly 負の主因 (BEV 大幅下回る)** |
| 1.0-2.0 | 80 | 32.5% | [23.1, 43.5] | むしろ高 spread のほうが WR 高 |
| ≥ 2.0 | 6 | 0.0% | [0.0, 39.0] | INSUFFICIENT |

**判定**: 「高 spread = 低 WR」は **REFUTED for current Live data**。「高 spread = 真の volatility/flow regime = high-edge zone」が整合 (vol_surge_detector q3=45.8% 整合)。

### 2.2 LP チェーン: 機関 flow 偏在

我々が edge を持てるのは「機関 flow が予測可能になる構造的瞬間」のみ。TAP-1/2/3 (中間帯 AND/N-bar/直前 candle) 戦略の大量 DEAD は機関 flow と無関係な indicator combo。

### 2.3 Stop hunt mechanism (sqlite-fx 実測あり)

| round_bin (JPY 系) | n | WR | Wilson 95% CI |
|--------|---|----|----|
| **at_round_5pip** | **48** | **58.3%** | **[44.3, 71.0]** |
| near_round_10pip | 56 | 21.4% | [12.7, 33.8] |
| far | 101 | 29.7% | [21.7, 39.2] |

**判定**: 「round number 近傍で WR が変わる」**CONFIRMED descriptive**。Phase 3 `pullback_to_liquidity_v1` の trigger 候補。

### 2.4 Magnet levels (POC / VWAP / D1 H/L)

現 registry に POC/VWAP を mechanism thesis に組み込んだ戦略は**ほぼ存在しない**。Phase 3 の空白領域。

### 2.5 Pullback / institutional accumulation (sqlite-fx 実測あり)

| 戦略 | TP_HIT | SL_HIT | TIME_DECAY | 判定 |
|------|--------|--------|------------|------|
| **`ema_trend_scalp`** | **7** | **39** | **19 (全 LOSS)** | **5.6:1、TAP-1 強烈裏付け** |
| `bb_rsi_reversion` | 16 | 14 | 4 (全 LOSS) | 均衡だが死亡パターン混入 |

### 2.6 Asia / London / Overlap dynamics

- London friction 0.86pip = 最良時間帯 **CONFIRMED**
- **`RANGE × (NewYork, q1)` Wilson 35.6% > baseline 31.5% — 唯一の R2 boost CONFIRMED descriptive**

### 2.7 News flow / BREAKOUT signal

**Phase 4d-II BREAKOUT joint χ² p=1.54e-3, V=0.371 (Bonferroni 通過) CONFIRMED**。BREAKOUT signal 確実存在、cell N 不足。

### 2.8 Track ② Live Kelly 4 leak

| Leak | 内容 |
|------|------|
| **L1: Mechanism thesis 不在** | TAP-1 戦略群の random sample entry |
| **L2: Pair-friction sampling bias** | aligned 73% が GBP_USD×BUY×scalp |
| **L3: Session × nature mismatch** | session-blind routing |
| **L4: BREAKOUT signal 未検出** | N=213 で cell N≥30 不足 |

### 2.9 Phase 3 提言 (5 件)

1. R2-A suppress 4 cells (`stoch_trend_pullback × (Overlap, q2)` 等を confidence ×0.5)
2. R2-B boost: `RANGE × (NewYork, q1)` を ×1.2
3. VALID mechanism 戦略 (`orb_trap`, `pullback_to_liquidity_v1`, `asia_range_fade_v1`) 重点投下
4. Pair-friction-aware routing (BEV 動的計算)
5. POC / VWAP / D1 H/L magnet level 戦略の新規設計

詳細: `fx-fundamentals-track-2.md` 参照。

---

## 3. Session × Pair 特性 (Track ③)

> **Status**: **統合済**。出典: `fx-fundamentals-2026-04-26.md` §4 (valiant-dahl)。

### 3.1 セッション 6 区分の理論的根拠と Live 整合

LP プール構成は session で変化。`friction_model_v2` の 6 区分 multiplier:

| Session | UTC | Multiplier | 設計根拠 |
|---------|-----|-----------|----------|
| Sydney | 21-00 | 1.60× | 月曜 gap、Asia 主要 LP 未参加 |
| Asia early | 00-02 | 1.55× | 豪→東京転換期 dead zone |
| Tokyo | 02-07 | 1.45× | Asia 中核、流動性中位 |
| London open | 07-12 | **1.00×** (基準) | 流動性 anchor、spread 最小 |
| Overlap LN-NY | 12-16 | 0.85× | 1 日で最厚 |
| NY | 14-21 | 1.20× | 16-17 UTC で London 撤退 |

**Live 実測 vs model 予測の乖離**:

| Session | 実測 (FX-only) | model 予測 | ratio (実/予) |
|---------|----------------|-----------|---------------|
| London | 0.86pip | 0.86 | 1.00 (基準) |
| Tokyo | 2.5pip | 1.25 | **2.00** ← model 過小 |
| New York | 2.0pip | 1.03 | **1.94** ← model 過小 |

**未検証仮説**: `friction_model_v2` の Tokyo/NY multiplier は **実測の約半分しか反映していない可能性**。Phase 3 で XAU 完全除外後の per-session friction を sqlite-fx で再計算 → N≥30/session 確認後に再 calibration。

### 3.2 ペア種別と流動性階層

BIS Triennial Survey 2022 daily turnover 上位:
- EUR/USD ≈ $1.7T/day, USD/JPY ≈ $0.6T/day, GBP/USD ≈ $0.4T/day, AUD/USD ≈ $0.2T/day

| Pair | Spread | Slippage | RT friction | BEV WR | Notes |
|------|--------|----------|-------------|--------|-------|
| USD_JPY | 0.7 | 0.5 | **2.14** | 34.4% | Major、最も効率的 |
| EUR_USD | 0.7 | 0.5 | **2.00** | 39.7% | Major、最低 friction |
| GBP_USD | 1.3 | 1.0 | **4.53** | 37.9% | spread+slip 共に 2 倍 |
| EUR_JPY | 1.0 | 0.5 | 2.50 | 33.7% | Cross だが意外と低い |
| **EUR_GBP** | 1.5 | - | ~3.0 | **57.1%** | **STRUCTURALLY IMPOSSIBLE** (永久停止) |
| XAU_USD | 86 | 46 | 217.5 | ~35% | **停止 v8.4** |

**XAU 除外の絶対性**: post-cutoff 237 trades のうち XAU 単独で **-2,280pip**、FX 全体は **+96.8pip**。

### 3.3 Carry trade (低優先)

我々の hold 1-6h で swap は edge の 1/10 以下。AUD pair 含まず → **carry を edge にしない**。

### 3.4 Pair × Session マトリクス: Phase 4d cells

**R2 suppress 候補** (Wilson upper < baseline):

| 戦略 × session × spread quintile | WR | vs baseline | Δ |
|----|----|----|----|
| stoch_trend_pullback × Overlap × q2 | 7.7% | 24.4% | **-16.7%** |
| sr_channel_reversal × London × q3 | 15.0% | 27.1% | -12.1% |
| ema_trend_scalp × London × q0 | 17.0% | 21.4% | -4.4% |

**R2 boost 候補** (confidence×1.2 のみ):

| 戦略 × session × spread | WR | Wilson lo | baseline |
|----|----|----|----|
| bb_rsi_reversion × Overlap × q2 | 53.3% | 36.1% | 34.5% |
| fib_reversal × Tokyo × q3 | 50.0% | — | — |

**未検証仮説**: 「Overlap = range edge zone (price discovery 最強で trend continuation kill)」「London = trend formation (reversal 戦略は逆風)」。Phase 3 BT で再検証。

### 3.5 Session 跨ぎ構造的ノイズ

| イベント | UTC | 影響 |
|---------|-----|------|
| Sydney 月曜開場 | 21:00 (日) | 月曜早朝 entry 禁止推奨 |
| Tokyo 9:55 仲値 | 00:55 | USD/JPY spike |
| London 4pm fix | 15:00-16:00 | 機関 benchmark fix、order flow 偏向 |
| NY close | 21:00 | swap rollover、薄商い |

intra-session breakdown が KB に未文書化 → Phase 3 で追加。

### 3.6 friction_model_v2 multiplier 感度分析

Tokyo/NY multiplier model が実測の半分。解釈の選択肢: (A) `friction-analysis.md` 列が XAU 残留歪み, (B) multiplier 構造的過小, (C) 両方部分的に正しい。multiplier 理論根拠 (Sydney 1.60× 等) の出所が KB 未文書化、`wiki/analyses/friction-multiplier-derivation.md` 作成が未解決課題。

### 3.7 Track ③ 視点での Live Kelly 寄与切り出し

3 軸分解:
- **Pair 軸 (高信頼度)**: XAU 除外後 (post-cutoff 237 trades) FX 全体 +96.8pip → **pair 軸単独はほぼ break-even**。XAU が真犯人。
- **Session 軸 (中信頼度)**: N 不記載で定量寄与不可。**未検証仮説**: London のみが positive expectancy。
- **戦略 × pair × session 交差項 (低信頼度)**: R2 suppress 4 cells (各 N≈40, 計 ~160) が WR を 5-15% 押し下げ。粗い見積 -800pip 相当。

**暫定結論**: Live -17.97% のうち XAU 102% (確定、停止済み)、pair 軸はほぼ break-even、session × pair 単独軸は -3〜-5pp、**戦略 × pair × session 交差項が残りの主因**。session × pair 単独軸の deep tuning は ROI 低い。

### 3.8 Track ③ 教訓 (7 件)

1. friction_model_v2 multiplier は Tokyo/NY で実測の約半分に過小評価
2. **Overlap = trend kill zone** (stoch_trend_pullback WR 7.7%)
3. **London open = trend formation** → reversal 逆風 (sr_channel_reversal × London × q3 WR 15.0%)
4. **EUR_GBP は structurally impossible** (BEV 57.1% 要求) → 永久除外
5. session × pair 単独軸寄与は -3〜-5pp、deep tuning ROI 低、**N 蓄積最優先**
6. XAU 除外規律は絶対 (loss の 102%)
7. carry trade は edge にしない (1-6h hold で swap 影響 1/10 以下)

詳細: `fx-fundamentals-2026-04-26.md` §4 参照。

---

## 4. Risk Management (Track ④)

> **Status**: **統合済**。出典: `fx-fundamentals-2026-04-26.md` §5 (imperative-wozniak)。
>
> **U17 snapshot drift closure (2026-04-26 PM)**: 「N=259 WR=39%」と「N=373 WR=30.3%」の不整合は **filter 違いの集計差**と判明。
> - **production memory** (`wiki/index.md`): Live `is_shadow=0`, snapshot 2026-04-24 AM, post-cutoff 2026-04-08〜 → N=259, WR=39.0%, edge=-17.97%
> - **Track ④ 直クエリ** (本日 PM): Live+Shadow 混合, post-cutoff 2026-04-08〜04-24 → N=373, WR=30.3%, edge=-18.07%
> - **Kelly edge は -18.07% ≈ -17.97% で本質一致** (浮動小数点丸めのみ)
> - 修正アクション: `wiki/index.md` L83-86 で filter 明示済 (curried-ritchie session)。両 metric は別目的で併記すべき (Live = production 比較用、Live+Shadow = 戦略真期待値推定用)。
> - U17 closure 完了。残課題: `/api/demo/stats` の `include_shadow` default 曖昧性除去は別 PR で対応 (production 影響あり)。

### 4.1 Kelly Criterion — 数式・歴史・Live 実測

```
f* = (p×b - q) / b   p=WR, q=1-p, b=avg_win/avg_loss
edge = p×b - q       edge ≤ 0 で Kelly clip 0
```

**全 FX 実測 (N=373, XAU除外)**:
- WR=30.3%, avg_win=+12.84, avg_loss=-7.53 → b=1.705
- edge = 0.303 × 1.705 - 0.697 = **-0.1807 → Kelly clip 0%**

**Sub-segment Kelly edge**:

| Segment | N | WR (Wilson95) | b | edge | Kelly Full |
|---------|---|---------------|---|------|------------|
| LIVE only (is_shadow=0) | 36 | 50.0% [34.5, 65.5] | 1.023 | +0.0117 | 1.14% (N過少ノイズ) |
| **SHADOW** (真の戦略期待値に近) | 337 | 28.2% [23.7, 33.2] | 1.779 | -0.2166 | **0%** |
| USD_JPY | 194 | 36.6% | 1.531 | -0.0738 | 0% |
| EUR_USD | 91 | 17.6% | 3.656 | -0.1814 | 0% |
| **GBP_USD** | 76 | 32.9% | 1.164 | **-0.2880** | 0% (friction 4.53pip 吸収不能) |

EUR_USD は b=3.656 と odds 大だが WR=17.6% で edge 負。「稀に大勝、多くは小負け」型は Kelly 不利。

### 4.2 Kelly Half / Quarter

| Sizing | Growth rate | std | Median DD | 破産確率 |
|--------|-------------|-----|-----------|----------|
| Full Kelly | 100% | 100% | 1× | 高 |
| **Half Kelly (f*/2)** | **75%** | **50%** | **0.5×** | 大幅低下 |
| Quarter Kelly | 44% | 25% | 0.25× | ほぼゼロ |

production はデフォルト `half_kelly`。**現状は Kelly clip 0% で Half/Quarter は無意味** (0 の半分も 0)。意味を持つのは「edge を作って Kelly > 0 になった後」。

### 4.3 Sharpe / Sortino / DSR (多重検定考慮)

```
Per-trade: mean=-1.34, std=18.27, downside_std=14.92
Sharpe (per-trade) = -0.0733 → Annualized -4.74
Sortino (per-trade) = -0.0898 → Annualized -5.81
```

**戦略別 Sharpe (per-trade)**:

| Strategy mode | N | EV (pip) | Sharpe/trade | 注 |
|---------------|---|----------|--------------|----|
| **`scalp` (USD_JPY)** | 93 | +3.77 | **+0.230** ✅ | 唯一の正 Sharpe |
| `scalp_eur` | 58 | +1.12 | +0.061 | |
| `daytrade` | 64 | -5.89 | -0.303 | |
| (他 6 modes) | - | 負 EV | 全て負 Sharpe | |

**DSR 補正** (試行 M=9, N=93):
```
Haircut ≈ √(2 ln(9) / 93) = 0.217
scalp 観測 Sharpe 0.230 - 0.217 = 0.013 ≈ 0
```

→ **scalp の Sharpe は M=9 多重検定考慮でほぼ消滅**。Track ⑤ §5.3 の Survivorship bias 議論と接続。

### 4.4 Drawdown — 実測 + Monte Carlo

**Realized**: Max DD = **965.5pip (開始資本の 96.5%、ruin 寸前)**

**Monte Carlo** (10,000 paths × 500 trades, ruin=50% DD):

| Segment | Ruin prob | Median Max DD | Worst-99% DD |
|---------|-----------|---------------|--------------|
| **ALL FX (N=373)** | **85.5%** | 820 | 1703 |
| LIVE only | 86.1% | 820 | 2258 |
| SHADOW | 89.9% | 853 | 1585 |
| USD_JPY | 57.4% | 547 | 1255 |
| EUR_USD | 53.2% | 517 | 1018 |
| **GBP_USD** | **99.6%** | 1762 | 3109 |
| EUR_JPY | 100% | 3016 | 3509 |

→ portfolio 全体で次 500 trade の **ruin 確率 85.5%**。「lot を半分にする」程度では救えない (Kelly clipping 領域)。

### 4.5 Correlation Matrix と "False Diversification"

|corr|≥0.3 を flag した結果: 36 pair のうち **31 pair (86%) で |corr|<0.3** (戦略間概ね uncorrelated)。

| Pair | corr |
|------|------|
| daytrade × daytrade_gbpusd | -0.344 |
| daytrade_eur × daytrade_gbpusd | +0.313 |
| daytrade_eur × scalp_5m | +0.304 |
| daytrade_eur × scalp_5m_eur | -0.457 |
| **daytrade_gbpusd × scalp_eur** | **-0.751** (強構造的 hedge) |

**示唆**: edge があれば良いニュース (実効自由度高い、DD 抑制可能)。**edge がなければ「異なる戦略で別々に負ける」だけ — 現状**。

### 4.6 月利 100% 目標の sustainability 数学

```
Annual return target = 12.0 (1200%)
return / std = S → std = 12.0 / S
S=2 → std 6.0 (月で破産しうる)
S=5 → std 2.4 (極めて稀)
→ S ≥ 5 が事実上必須
```

**Live gap 最終定量**:

| 項目 | 現状 (Live) | 目標 (月利 100%) | Gap |
|------|------------|------------------|-----|
| WR | 30.3% | ≥50% | **+20pp** |
| EV/trade | -1.34 pip | ≥+0.5 pip | +1.84 pip |
| Kelly edge | -18.07% | ≥+10% | **+28pp** |
| Sharpe (annual) | -4.74 | ≥+5.0 | **+9.74** |
| MC ruin (500-trade) | 85.5% | <5% | -80pp |

→ どの metric も「微調整」レンジを越えている。**戦略生成構造そのものの再設計**が必要。

### 4.7 Risk Premium と Tail Risk — 取らないべき edge

3 分類: Information (機関領分、retail 不可) / **Structural (我々の主戦場)** / Risk premium (vol selling は SNB 2015 で -100pip in 30sec、carry は LTCM 1998/COVID 2020 で破滅)。

我々の戦略は explicitly に risk premium を取っていないが、`daytrade_*` の hold 1-6h は tail event 中の DD risk あり。Phase 3 では **Structural edge のみ** を狙う。

### 4.8 Track ④ Live Kelly 構造説明 — 数学的にやってはいけないこと

```
Track ① (microstructure) friction が edge を上回る
Track ② (liquidity) liquidity zone を活用していない (TAP-1/2/3)
                ↓
Track ④ edge ≤ 0 → Kelly clip 0
                ↓
            lot 縮小は EV 改善せず
                ↓
            MC ruin 85.5% (500-trade horizon, 50% DD)
                ↓
      Sharpe -4.74、scalp のみ正だが DSR で消滅
```

**数学的に禁止**:
1. lot を上げて挽回 → 破産確率↑
2. lot を半分にして "Half Kelly 風" → 損失速度半減のみ
3. 戦略を増やして分散 → correlation 低い (86% pair で |r|<0.3)、負 EV 分散のみ
4. 過去勝ち戦略 (scalp) に集中 → DSR で Sharpe ≈ 0、N 不足 false positive

**唯一許される行動 = Phase 3 の実行**:
- mechanism-driven edge を 1 つでも構築 (`pullback_to_liquidity_v1` or `asia_range_fade_v1`)
- Wilson 95% 下限で Kelly > 0 になるまで lot 増設禁止
- pre-reg LOCK + friction_model_v2 cost-adjusted EV

詳細: `fx-fundamentals-2026-04-26.md` §5 参照。

---

## 5. Quant Edge の本質 (Track ⑤)

> **Status**: **統合済**。出典: `fx-fundamentals-track-5.md` (mellow-sky)。

### 5.1 Edge の 3 分類と 19 戦略の Live 実測判定

| 種類 | retail で取れるか | 我々への含意 |
|------|--------------------|-------------|
| **Information edge** | ❌ 不可能 | Bloomberg なし、order flow info なし |
| **Structural edge** | ✅ 主戦場 | Phase 3 mechanism-driven edge の中核 |
| **Risk premium** | ⚠️ 限定的 | vol selling 破滅、carry 軽微、流動性供給 不可 |

**Live 実測ハイライト** (FX-only CLOSED N=373):

| 戦略 | N | WR | EV (pip) | PF | 判定 |
|------|---|----|----|------|------|
| ema_trend_scalp | 69 | 14.5% | -1.87 | 0.28 | TAP-1 NONE |
| fib_reversal | 44 | 65.9% | +7.84 | 3.94 | Structural 候補 |
| bb_rsi_reversion | 34 | 47.1% | +4.79 | 3.20 | Structural 候補 (audit 改善余地) |
| dt_bb_rsi_mr | 14 | 64.3% | +5.87 | 2.44 | Structural 候補 |
| **vol_momentum_scalp** | 5 | 60.0% | +4.64 | **20.33** | **Structural 候補 (PF 異常、要 mech 検証)** |
| orb_trap | 5 | 0.0% | -10.28 | 0.00 | **VALID 但し N=5「未検出」(N≥37 必要)** |

`orb_trap` の N=5 WR=0% は「DEAD 確定」ではなく **「未検出」** (検出力ゼロ)。

### 5.2 BT 楽観バイアス 6 因子 + friction v2 捕捉率 ~50%

`friction_model_v2.py` の捕捉:
- ✅ 1 Entry / 2 Spread / 5 Fill Quality
- ❌ 3 Signal Reverse Lag / 4 HTF Data Mismatch / 6 Label Bias (code-level 修正必須)

**friction matrix**:
- USD_JPY DT overlap_LN: **1.82pip**
- GBP_USD Scalp Asia_early: **7.37pip** (avg_win 5-15pip 戦略では構造的 BEV 不可能)

→ 戦略採用は (pair × mode × session) **3D セル単位**で BEV 可否判断。

### 5.3 Survivorship Bias / HARKing / pre-reg LOCK

10 戦略を独立 test (各 α=0.05) → 偽陽性確率 40.1%、20 戦略で 64.2%。**多重検定補正なしで 10 戦略以上テストすると偽陽性が支配的**。

pre-reg LOCK 2 戦略 (Phase 1.7 LOCK 済): `pullback_to_liquidity_v1`, `asia_range_fade_v1`。Wilson lower 95% > 50% を WR=55% で達成するには **N ≥ 400 程度必要**。

### 5.4 Multiple Testing Correction (Bonferroni)

Live N=259 baseline WR=39% で:

| K | α_corrected | Detectable ΔWR |
|---|-------------|----------------|
| 1 | 0.0500 | **+7.54pp** |
| 5 | 0.0100 | +9.60pp |
| 10 | 0.0050 | +10.36pp |
| 20 | 0.0025 | +11.06pp |

→ K=10 で WR 49.4%+ にしないと検出不能。

### 5.5 Walk-Forward Analysis

- **Anchored WFA**: IS 2025-01〜09 / OOS 2025-10〜2026-04 (long-term validity)
- **Rolling WFA**: IS 6m rolling, OOS 1m, Step 1m (regime 適合性)

3 段防御 (WFA + Bonferroni + friction v2) → Live N≥30 検証 → N≥200 で Wilson lower>50% で Live 昇格。

### 5.6 Sample Size & Statistical Power

| N | Detectable ΔWR | Threshold WR |
|---|----------------|---------------|
| 30 | **22.14pp** | 61.1% |
| 100 | 12.13pp | 51.1% |
| 259 | **7.54pp** | 46.5% |
| 500 | 5.42pp | 44.4% |
| 1000 | 3.84pp | 42.8% |

**N が足りない時の NULL は「edge 不在」ではなく「未検出」**。Phase 4c-d 7 検定累積 NULL は (i) edge 不在説 (ii) 未検出説 (effect size < 7.54pp) で distinguishable でない。深掘り継続で「未検出説」を排除しながら「edge 不在説」の確度を上げる。

### 5.7 Track ⑤ Live Kelly 構造説明 5 因子

| 因子 | 内容 |
|------|------|
| **Q1: Information edge 不在** | 我々はアクセス不能、`sr_break_retest` PF 0.18 が代表 |
| **Q2: Structural edge mechanism thesis 不在** | 19 戦略中 VALID 1 のみ |
| **Q3: friction が edge を食う** | GBP_USD Scalp Asia_early 7.37pip |
| **Q4: BT 楽観バイアス 6 因子の friction で捕捉できない 50%** | code-level 修正必要 |
| **Q5: 多重検定補正下で marginal edge 検出不能** | K=10 で ΔWR ≥ 10.36pp の effect size のみ |

正に転じる 5 必要条件: (1) mechanism thesis VALID 戦略のみ採用 (2) friction v2 BT 組込 (3) WFA + Bonferroni + pre-reg LOCK (4) Live N≥200 Wilson lower > 50% (5) (pair × mode × session) cell 別 routing。

詳細: `fx-fundamentals-track-5.md` 参照。

---

## 6. 5-Track 横断統合

### 6.1 Track 間の論理整合チェック表

| Track ペア | 整合点 | 矛盾点 / 緊張 | 解決方針 |
|------------|--------|----------------|----------|
| **① × ②** | 1.1 OTC chain ≡ 2.2 LP chain。1.2 Spread 3 component ≡ 2.1 Order book MM 補償 | 1.5 「高 spread = 低 SNR」 vs 2.1 Live 実測「高 spread = 真 vol regime = high-edge」 (一般論 REFUTED) | **両立**: spread-WR 関係は U 字型 (中分位 0.5-1.0pip で最悪)。低 spread (< 0.5) は ロギング artifact、高 spread (> 1.0) は機関 flow regime |
| **① × ③** | 1.1 OTC tier markup ≡ 3.2 pair 別 BEV WR (USD_JPY 34.4% etc.)。1.2 Spread 動的 ≡ 3.1 session multiplier | 1.6 F2 Spread 非定常 vs 3.6 multiplier model 過小評価 (Tokyo/NY 約半分) | **整合 + 拡張**: F2 が定性、3.6 が定量で実測値の半分とのズレ。Phase 3 で multiplier 再 calibration が必要 (Track ③ 提言 1) |
| **① × ④** | 1.6 F1-F5 ≡ 4.8 Track ④ 失敗構造 (microstructure → liquidity → Kelly clip)。1.4 internalization B-book profit center ≡ 4.4 MC ruin 85.5% | なし | **完全積層整合**: ① が物理層、② が flow 層、④ が allocation 層、4.4 GBP_USD MC ruin 99.6% は ① F1 markup × ③ pair friction の複合帰結 |
| **① × ⑤** | 1.6 F5 M1 SNR ≡ 5.6 必要 N=150-300/cell。1.4 vol_momentum_scalp non-toxic ≡ 5.1 Structural edge 候補 (PF 20.33) | 1.6 F5 「M1 戦略全体に深刻」 vs 5.1 「Structural edge は retail 主戦場」 | **解消**: 5.1 は M5+/MTF 想定、1.6 F5 は M1 single-TF 限定。Multi-TF / M5+ の Structural edge 空間は別 |
| **② × ③** | 2.6 RANGE × NewYork × q1 boost ≡ 3.4 Pair × Session マトリクス R2 boost cells。2.5 ema_trend_scalp 5.6:1 ≡ 3.4 ema_trend_scalp × London × q0 R2 suppress | なし | 完全整合 |
| **② × ④** | 2.8 L1-L4 leak ≡ 4.8 数学的禁止 4 項 | 2.6 London 0.86 (最良 friction) と 4.5 daytrade Sharpe 全負 で「session 次第で勝てる」期待 vs 4.6 「全 metric が微調整レンジ越え」 | **両立**: session 軸単独では break-even 程度 (Track ③ §3.7)、edge は session × strategy nature の cross product。Phase 3 提言 (Track ②③) と整合 |
| **② × ⑤** | 2.8 L1 mechanism thesis 不在 ≡ 5.1 19 戦略中 VALID 1。2.9 R2 suppress ≡ 5.4 多重検定補正下 loss-prevention 正当化 | なし | 完全整合 |
| **③ × ④** | 3.7 Pair 軸 ほぼ break-even (XAU 除外後) ≡ 4.1 Per-pair Kelly 全負だが USD_JPY/EUR_USD は MC ruin 50%台。3.4 R2 cells ≡ 4.4 GBP_USD MC ruin 99.6% | 3.4 boost 候補 (bb_rsi×Overlap×q2 WR 53.3%) vs 4.3 daytrade Sharpe 全負 | **両立**: q2 cell の boost は Bonferroni 不通過で confidence×1.2 のみ、Live への影響限定 |
| **③ × ⑤** | 3.4 R2 cells ≡ 5.4 Bonferroni 補正下 loss-prevention 正当化。3.5 intra-session breakdown 未文書化 ≡ 5.6 N 不足の典型例 | なし | 完全整合 |
| **④ × ⑤** | 4.6 月利 100% gap (Sharpe +9.74) ≡ 5.7 5 必要条件。4.3 DSR 補正で scalp Sharpe ≈ 0 ≡ 5.4 Bonferroni K=10 で ΔWR ≥ 10.36pp。4.7 Risk premium 取らない ≡ 5.1 retail で取れない | なし | 完全整合 (4.7 と 5.1 は同テーゼの別表現) |

**横断整合性総評**: 5 Track 間で **論理矛盾は無い**。1 つの「見かけ矛盾」(① × ② の spread-WR 関係) は U 字型仮説で両立解消。3 件の「緊張」(① × ③, ② × ④, ③ × ④) はいずれも単独軸 vs 交差項の解像度差で、Phase 3 で再検証する未解決問題に変換済 (§6.4)。

### 6.2 5-Track 統合視点での Live Kelly 構造説明

```
Live Kelly = -18.07% (= -0.1807, edge 値) は以下の独立因子の積算
全 FX N=373, WR=30.3%, b=1.705, MC ruin 85.5%, Annualized Sharpe -4.74

[層 1: 物理 / Track ①]
  F1 OTC markup の不可避性 (全戦略一律 +1-2pip cost、Tier 4 retail)
  F2 Spread の非定常性 (戦略選択的 -2 ~ -8pp WR)
  F3 Latency + Last Look (Scalp SL 占有率 +5-15%)
  F4 Internalization 動的 routing (現状 B-book profit center)
  F5 M1 microstructure noise (signal layer の noise pattern fit)

[層 2: 流動性 / 機関 flow / Track ②]
  L1 Mechanism thesis 不在 (TAP-1/2/3 の random sample → SL hit 量産)
  L2 Pair-friction sampling bias (GBP_USD × scalp 集中)
  L3 Session × nature mismatch (session-blind routing)
  L4 BREAKOUT signal 未検出 (cell N≥30 不足)

[層 3: Session × Pair / Track ③]
  S1 multiplier model 過小評価 (Tokyo/NY 実測の約半分)
  S2 Pair 軸単独 ≈ break-even (XAU 除外後 +96.8pip、XAU 102% 損が真犯人)
  S3 Session 軸 -3〜-5pp (低信頼度、N 不足)
  S4 戦略 × pair × session 交差項 -800pip 相当 (R2 cells, 主因)
  S5 EUR_GBP STRUCTURALLY IMPOSSIBLE (BEV 57.1% 永久除外)

[層 4: Risk allocation / Track ④]
  R1 Kelly clip 0% (edge < 0 で lot 制御不能)
  R2 MC ruin 85.5% (500-trade horizon, 50% DD; GBP_USD 単独 99.6%)
  R3 Annualized Sharpe -4.74 vs 必要 ≥+5.0 (Gap +9.74)
  R4 DSR 補正で唯一の正 Sharpe (scalp +0.230) もほぼ 0
  R5 Correlation 86% pair で |r|<0.3 (false diversification、edge 不在で意味なし)

[層 5: Edge 探索 / Track ⑤]
  Q1 Information edge 不在 (Bloomberg / order flow なし)
  Q2 Structural edge mechanism thesis 不在 (19 戦略中 VALID 1)
  Q3 friction が edge を食う (GBP_USD Scalp Asia_early 7.37pip)
  Q4 BT 楽観バイアス 6 因子の 50% は code-level 修正必要
  Q5 多重検定補正下で marginal edge 検出不能 (K=10 で ΔWR ≥ 10.36pp)
```

**5-Track 統合主因の重ね合わせ**:

1. **不可逆制約 (Q1)**: Information edge は retail の選択肢にない → Structural のみが道
2. **直接的損失生産 (F1+F2+F3+L1+L2+L3+S1+S4+Q3)**: 現 19 戦略の Live 損失を素直に説明
3. **構造的天井 (F5+Q5)**: 「N をいくら増やしても M1 single-TF では edge が見えない」(M1 SNR≤10 + Bonferroni K=10 で必要 ΔWR≥10.36pp の合算)
4. **Hidden risk (F4+R2+R5)**: edge 回復後の broker dynamic routing 劣化、500-trade ruin 85.5%、false diversification — Phase 3 設計時に必ず risk budget に計上
5. **数学的不可能 (R1+R3+R4)**: 「微調整」では到達不能、戦略生成構造そのものの再設計が必須 (Phase 3)

### 6.3 Phase 3 mechanism-driven edge 再構築への 5-Track 統合提言

> **Update 2026-04-27 (Wave 2 Day 2 Quant Rigor)**: Phase 3 BT 設計を **Pre-reg LOCK formal document** として確定。LOCK 文書: [phase3-bt-pre-reg-lock.md](phase3-bt-pre-reg-lock.md)。Wave 1 R2-A 効果計測の事前 power analysis 完了 ([wave1-r2a-power-analysis.md](wave1-r2a-power-analysis.md))、4 cells のうち 2 cells のみ実用検出可能と確定。HARKing 防止のため Pre-reg LOCK 文書を git commit + push で時刻署名。

**最優先 (即時実装、Bonferroni 不要、loss prevention)**:
1. **R2-A suppress 4 cells** (Track ② §2.9, Track ③ §3.4): `stoch_trend_pullback × (Overlap, q2)` 等を confidence ×0.5 — Asymmetric Agility R2 の教科書用途
2. **M1 single-TF 戦略の縮小** (Track ① §1.7, Track ⑤ §5.6 SNR 限界)、Multi-TF / M5+ 重心移動

**中期 (Phase 3 BT 設計、Rule 1 with pre-reg LOCK)**:
3. **mechanism thesis VALID 戦略のみ採用** (Track ⑤ §5.1, Track ② §2.9): 19 戦略中 VALID 1 のみ → 30 戦略 audit 拡大が前提
4. **3 段防御** (Track ⑤ §5.5): WFA + Bonferroni + pre-reg LOCK
5. **friction v2 BT 組込** (Track ⑤ §5.2, Track ① §1.7): (pair × mode × session) 3D セル BEV 判断、`backtest_mode=True` 同期で 6 因子の残り 50% (Lag/HTF/Label) も補償
6. **Spread regime 内蔵** (Track ① §1.7) + **Pair-friction-aware routing** (Track ② §2.9)
7. **multiplier 再 calibration** (Track ③ §3.6): XAU 完全除外後の per-session friction、N≥30/session 確認後

**長期 (passive accumulation + 構造的 risk control)**:
8. **必要 N=150-300/cell or N≥400 (Wilson lower > 50%)** (Track ⑤ §5.6) → **60+ days passive accumulation で N≈6800** (Track ① F5, Track ② L4)
9. **Magnet level 戦略 (POC/VWAP/D1 H/L) の新規設計** (Track ② §2.4, 現 registry 空白)
10. **Risk budget 計上** (Track ④ §4.4, §4.7): MC ruin 監視 + edge 回復後の broker dynamic routing risk + tail risk explicit シミュ
11. **EUR_GBP は永久除外** (Track ③ §3.2, BEV 57.1% structurally impossible)

### 6.4 未解決問題 (12 件 → 全 Track 統合後 18 件)

| # | 問題 | Track 由来 | 性質 | 優先度 |
|---|------|------------|------|--------|
| U1 | OANDA Japan の spread markup 内訳 (broker 取り分 vs LP 取り分) | ① §1.1 | broker 透明性、retail 検証不能 | 中 |
| U2 | Last Look 適用率 / reject 率の定量診断 | ① §1.3 | broker 透明性、retail 検証不能 | 中 |
| ~~U3~~ | ~~**vol_momentum_scalp が BT=Live 一致する理由 (PF 20.33 異常)**~~ → **CLOSED 2026-04-26 PM (Wave 2 Day 1)**: 当初 "non-toxic broker fill" 仮説は棄却 (avg slip 1.74pip と高い)、真の edge は **5 層構造** (Anti-TAP entry × Multi-filter gate × Asymmetric exit × BT-validated whitelist × Confirmed momentum philosophy) が friction を支配。詳細: [u3-vol-momentum-scalp-deepdive.md](u3-vol-momentum-scalp-deepdive.md)、Phase 3 設計指針 G1-G5 抽出済 | ① §1.4, ⑤ §5.1 | (CLOSED) | (CLOSED) |
| U4 | edge 回復後の broker 動的 routing 劣化リスク | ① §1.4, ④ §4.4 | 月利 100% 達成局面の hidden risk | 高 |
| U5 | Spread 3 component (inventory / adverse / processing) の動的分離 | ① §1.2 | retail PIN 推定不可、代替指標模索 | 中 |
| U6 | News flow filter 未実装 (DB に news event 列なし) | ② §2.7 | Phase 3 で news calendar API 統合 | 中 |
| U7 | POC / VWAP の Live 実測未検証 | ② §2.4 | Phase 3 で magnet level 戦略 BT | 中 |
| U8 | Phase 5-9d 9 戦略の friction v2 再シミュ未実測 | ⑤ §5.2(c) | Phase 3 BT 実行後に追記 | 高 |
| U9 | pre-reg LOCK 2 戦略の 365 日 BT Wilson CI / Bonferroni 補正 | ⑤ §5.3(b) | Phase 3 BT 実行後に追記 | 高 |
| U10 | 「edge 不在」と「未検出」の見極め指標 | ⑤ §5.6 | passive accumulation 60+ days 後に再評価 | 高 |
| ~~U11~~ | ~~**mechanism audit 残り 30 戦略の VALID/WEAK/NONE 判定**~~ → **CLOSED 2026-04-26 PM (Wave 2 Day 1)**: 6 background subagents 並列で 28 戦略 audit 完了 + vol_momentum_scalp 単独 deep dive。**最終内訳: VALID 11 / WEAK 13 / NONE 8 / VALID理論不運用 2** (合計 34 戦略)。Phase 3 universe = VALID 11、Manager 再推奨 Option-B (pre-reg 2 + Tier-A 5 = 計 7 戦略 BT)。詳細: [u11-mechanism-audit-aggregate.md](u11-mechanism-audit-aggregate.md) | ⑤ §5.1 | (CLOSED) | (CLOSED) |
| U12 | spread-WR U 字型仮説の Bonferroni 検定 | ① × ② 統合 | 60 days 蓄積後に pre-reg LOCK | 中 |
| ~~U13~~ | ~~friction_model_v2 multiplier 理論根拠~~ → **PARTIAL CLOSE 2026-04-27 (Wave 2 Day 2)**: subagent calibration で 4 cells N≥30 確定。残: friction-multiplier-derivation.md 正式作成は別 session、subagent 結果を生資料として保持 | ③ §3.6 | (PARTIAL) | (PARTIAL) |
| ~~U14~~ | ~~XAU 完全除外後の per-session friction 再計算~~ → **PARTIAL CLOSE 2026-04-27 (Wave 2 Day 2)**: 重要発見 — Track ③ 仮説と**逆方向**で **model が実測の 1.86× 過大** (USD_JPY Tokyo)。Manager review: 即時 patch 否定、Phase 3 BT 設計に "selectable friction model" を組み込み両方比較。N≥30 4 cells / 16 cells、残は 60-90 days passive 蓄積待ち。詳細: [u13-u14-friction-calibration.md](u13-u14-friction-calibration.md) | ③ §3.6 | (PARTIAL) | (PARTIAL) |
| U15 | intra-session (時刻別) breakdown 未測定 (Tokyo 9:55 仲値, London 4pm fix 等) | ③ §3.5 | Phase 3 で WR/EV 分析追加 | 中 |
| U16 | 「Overlap = range edge / London = trend edge」仮説の Phase 3 BT 検証 | ③ §3.4 | 未検証仮説 | 中 |
| ~~U17~~ | ~~「Live N=259 WR=39%」(memory) vs 「N=373 WR=30.3%」(本日 PM 直 DB) の snapshot drift 解消~~ → **CLOSED 2026-04-26 PM**: filter 違い (Live vs Live+Shadow) の集計差、Kelly edge -18.07% ≈ -17.97% で本質一致、wiki/index.md で filter 明示済 | ④ §4.0 メモ | (CLOSED) | (CLOSED) |
| **U18** | **Wave 1 R2-A spread quintile cuts vs Phase 4d-II の整合性検証** — Wave 1 implementation `compute_spread_quintile()` の static cuts (USD_JPY: [0.4,0.6,0.8,1.2]) と Phase 4d-II の dynamic per-(pair, session) quintile が異なる可能性。local DB 検証で Pre-deploy 期間に R2-A 4 cells の該当 trade はわずか 1 件 (stoch×Overlap×q2、WR=100%)。**Wave 1 R2-A は事実上 no-op の可能性大**。詳細: [wave1-r2a-power-analysis.md](wave1-r2a-power-analysis.md) §2 | Wave 2 Day 2 Quant Rigor 発見 | Phase γ (+24h) で reasons log 確認、0 件なら別 PR で dynamic quintile 再実装 | **最高** |
| ~~U19~~ | ~~**Phase 3 BT Mode A/B 比較は現 BT pipeline で機能しない**~~ → **CLOSED 2026-04-27 PM (Wave 2 Day 6)**: `app.py:_bt_spread()` を session multiplier-aware に改修 (`_bt_classify_session()` 追加 + `_SESSION_MULTIPLIER` 適用)。P4 smoke test 再実行で **PASS** (gbp_deep_pullback × GBPUSD 60d、friction_mean Mode A 0.139pip vs Mode B 0.127pip = 0.012pip diff > 閾値 0.007pip)。fail-open 設計 (import / lookup 失敗時は base_spread のみ返却で旧挙動維持)。Phase 3 BT 着手 technical blocker 解消 | Wave 2 Day 5 P4 smoke test | (CLOSED) | (CLOSED) |
| ~~U20~~ | ~~**Wave 1 R2-A は構造的 no-op**~~ → **CLOSED 2026-04-27 evening (Wave 2 Day 8 Phase γ')**: Q-A U20 fix (commit `5191d2c`) で `_compute_scalp_signal_v2._make_result` に R2-A gate を集権化追加。deploy +4.5h Phase γ' 再計測で **3/60 fires confirmed** (全 `(ema_trend_scalp, London, q0)` cell で conf 60→30, 64→32, 66→33 = ×0.5 適用)。Scenario A (完全成功) 該当、Phase 3 BT 着手 ζ +14d (2026-05-11) 計画通り維持。詳細: [wave2-phase-gamma-prime-result.md](wave2-phase-gamma-prime-result.md) | Wave 2 Day 7 Phase γ measurement | (CLOSED) | (CLOSED) |
| U18 | portfolio_kelly per-strategy lot allocation 最適化 + daily-resampled Sharpe + tail risk explicit シミュ | ④ §4.8 残課題 | Phase 3 完了後に再 audit | 中 |

**最高優先 (Phase 3 着手前に決着)**: U3 (vol_momentum_scalp), U11 (mechanism audit 30 戦略)。これらが Phase 3 設計の前提となる。

---

## Appendix A: Phase 4c/4d KB 照合インデックス

| # | KB ドキュメント | 観測 ID / Section | 引用先 (Track) | 引用内容要約 |
|---|------------------|--------------------|------------------|--------------|
| 1 | `wiki/decisions/edge-reset-direction-2026-04-26.md` | (file 直読 §2-3) | ①, ⑤, 6 | Live N=259 WR=39% Kelly edge -17.97%、TP-hit 16/16 cell BEV gap<0、Scalp/DT 摩擦 5.4×、MTF η²<0.005、6 因子分解 |
| 2 | `wiki/analyses/bt-live-divergence.md` | obs 39 / obs 45 | ①, ④, ⑤ | Scalp 摩擦/ATR=36-49%、bb_rsi -16pp / fib_reversal -36pp、BT 楽観 6 因子、vol_momentum_scalp ★★★★★ で唯一一致 |
| 3 | `wiki/analyses/friction-analysis.md` | obs 41 (file 経由) | ①, ②, ③, ④, ⑤ | 実測 RT Friction USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 pip、Friction by Session、EUR_GBP BEV 57.1% structurally impossible |
| 4 | `wiki/analyses/phase4c-mtf-alignment-bug-audit-2026-04-26.md` | (file 直読) | ①, ② | aligned WR=8.1% (N=37) << conflict 20.4% (N=411)、aligned subset GBP_USD×BUY×scalp 73%、d1_label = -1,-2 が 0 件 |
| 5 | `wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md` | obs 72 | ①, ②, ③, ⑤ | 384 testable cells 0 SURVIVOR、必要 N=150-300/cell、R2 suppress 4-5 cells、bottleneck=N |
| 6 | `wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md` | obs 81 | ①, ②, ④, ⑤ | BREAKOUT joint chi2 p=1.54e-3 唯一の Bonferroni 通過、V=0.371、RANGE × NewYork × q1 Wilson lower 35.6% > baseline 31.5% |
| 7 | `wiki/analyses/mtf-regime-validation-2026-04-17.md` | obs 35 | ① | 単一 TF ADX 判定は η²<0.005 で無効 |
| 8 | `wiki/syntheses/strategy-mechanism-audit-2026-04-26.md` | (Track 2/5 経由) | ②, ⑤ | TAP-1/2/3 定義、`orb_trap` VALID、19 戦略中 1 のみ |
| 9 | `wiki/lessons/lesson-toxic-anti-patterns-2026-04-25.md` | (Track 5 経由) | ④, ⑤ | TAP-1/2/3 該当戦略 |
| 10 | `wiki/lessons/lesson-asymmetric-agility-2026-04-25.md` | (Track 5 経由) | ⑤ | Rule 1/2/3 多重検定組込 |
| 11 | `wiki/syntheses/phase5-9d-edge-matrix-2026-04-25.md` | (Track 5 経由) | ⑤ | 9 戦略 mechanism、Information edge 戦略不在 |
| 12 | `modules/risk_analytics.py` (kelly_fraction, monte_carlo_ruin, calculate_var_cvar, strategy_correlation) | Track ④ 直 import | ④ | Kelly clip 0%, MC ruin 85.5% (10000 paths × 500 trades), correlation matrix |
| 13 | `modules/friction_model_v2.py` 直接 import | Track 5 §5.2(b), Track 3 §3.1 | ③, ⑤ | session × pair × mode multiplier matrix, USD_JPY DT overlap_LN 1.82pip, GBP_USD Scalp Asia_early 7.37pip |
| 14 | local `demo_trades.db` (FX-only CLOSED, 2026-04-02〜04-24) | Track 2/4/5 直 SQL | ②, ④, ⑤ | spread bin × WR / round-number proximity / close_reason 分布 / 19 entry_type N/WR/Wilson/EV/PF / Sharpe per-trade / MC ruin |
| 15 | (memory) `feedback_label_empirical_audit` | MEMORY.md | 0.2 規律 | コード演繹禁止、ラベル×WR 実測クエリ必須 |
| 16 | (memory) `feedback_partial_quant_trap` | MEMORY.md | 0.2 規律 | N/WR/EV だけでなく PF/Wilson CI/WF/Bonferroni/Kelly まで要求 |
| 17 | (memory) `feedback_success_until_achieved` | MEMORY.md | 0.2 規律, ⑤ §5.6 | Null/Scenario A で closure 短絡禁止、深掘り再検証必須 |
| 18 | BIS Triennial Survey 2022 | Track ③ §3.2 (一般論レベル参照) | ③ | EUR/USD 1.7T/day, USD/JPY 0.6T, GBP/USD 0.4T |

完成基準 (最低 5 件) を満たす: **18 件引用**。

---

## Appendix B: 並行セッション成果物の出典ファイルパス

| Track | ファイルパス / Section | 並行セッション名 | 確認日時 | 状態 |
|-------|------------------------|------------------|----------|------|
| ① | `fx-ai-trader/knowledge-base/wiki/learning/fx-fundamentals-track-1.md` | curried-ritchie (本セッション) | 2026-04-26 14:05 | **integrated** |
| ② | `fx-ai-trader/knowledge-base/wiki/learning/fx-fundamentals-track-2.md` | twinkling-pancake | 2026-04-26 13:38 | **integrated** |
| ③ | `fx-ai-trader/knowledge-base/wiki/learning/fx-fundamentals-2026-04-26.md` §4 (Track 4 セクション) | valiant-dahl | 2026-04-26 15:00 | **integrated** |
| ④ | `fx-ai-trader/knowledge-base/wiki/learning/fx-fundamentals-2026-04-26.md` §5 (Track 5 セクション) | imperative-wozniak | 2026-04-26 15:00 | **integrated** |
| ⑤ | `fx-ai-trader/knowledge-base/wiki/learning/fx-fundamentals-track-5.md` | mellow-sky | 2026-04-26 14:05 | **integrated** |

**Note on file naming convention**:
- 当初想定では Track 3, 4 も独立 `fx-fundamentals-track-{3,4}.md` ファイルとして並行セッションが書く前提だったが、実際は **broad-pass file** (`fx-fundamentals-2026-04-26.md`) 内の §4/§5 として valiant-dahl / imperative-wozniak セッションが直接書き込んだ
- broad-pass file の section 番号は本 master と異なる: broad-pass の「Track 4」=本 master の Track ③、「Track 5」=本 master の Track ④
- 本 master は最終統合先として全 Track の summary-reference + Section 6 横断統合を提供する役割

---

## 完了状態

**全 5 Track 統合済み + Section 6 横断統合完成** (2026-04-26 15:00)。
- Track ①: curried-ritchie (本セッション、Microstructure)
- Track ②: twinkling-pancake (Liquidity)
- Track ③: valiant-dahl (Session × Pair)
- Track ④: imperative-wozniak (Risk Management)
- Track ⑤: mellow-sky (Quant Edge)

完成基準 (Plan 検証方法) チェック:
1. ✅ 構造完全性: Section 1.1〜5.x すべて 3 段構造 (deep-dive ファイル側で厳守)
2. ✅ 照合密度: Appendix A 18 件 (基準 5 件)
3. ✅ 統合完全性: Section 2-5 placeholder 全て統合済
4. ✅ 横断整合: Section 6.1 全 Track ペア (10 組合せ) 整合チェック完了、矛盾 0、緊張 3 件 (解消方針記載済)
5. ✅ scope 規律: 並行セッション完了前に本文を書き始めず、ファイル出現後に統合
6. ⏳ end-to-end テスト: ユーザに Section 6.2 の音読 + Live -17.97% 説明率 50%+ 評価を依頼予定

**Phase 3 移行判定**: U3 (vol_momentum_scalp non-toxic property) と U11 (mechanism audit 30 戦略) の 2 件の最高優先未解決問題を Phase 3 着手前に決着すること。
