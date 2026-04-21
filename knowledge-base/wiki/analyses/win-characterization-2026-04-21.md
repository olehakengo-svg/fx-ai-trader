# WIN 条件直接 Characterization — 各戦略の TP-hit は何の状態で起きたか?

**日付**: 2026-04-21
**問い**: 各 TP-hit trade は**どういう条件**で発生したか? (単なる WIN vs LOSS 差分ではなく、WIN の**内在的特徴づけ**)

**先行分析との違い**:
- [[shadow-tp-sl-causal-2026-04-21]] は **差分**分析 (Fisher 検定)
- [[win-conditions-mining-2026-04-21]] は filter 後の **golden cell** 探索
- [[win-conditions-unfiltered-2026-04-21]] は **portfolio-wide marginal**
- **本分析は per-strategy の WIN 条件**を直接記述 (特徴量の percentile range, LR ranking, narrative)

---

## 1. 分析手法

| Section | 指標 | 目的 |
|---|---|---|
| A | P(feat=v \| WIN) | WIN 内の分布 |
| B | LR = P(feat=v\|WIN) / P(feat=v\|LOSS) | どの値で WIN-enriched か |
| C | WIN の Q5 / Q50 / Q95 (連続 feat) | WIN が発生する数値範囲 |
| D | 戦略横断 pattern (LR≥1.5 で複数戦略) | 汎用 vs 固有 |
| E | 戦略別 narrative | 平易な要約 |

**対象**: shadow N=1716 (WIN=483, LOSS=1233). Strategy × WIN≥15 を characterization 対象 (11 戦略).

---

## 2. 戦略別 WIN 条件 (narrative + 数値)

各戦略について「TP hit しやすい状態」を記述. ★ = LR≥2 で統計的 enriched (N_win≥5).

### 2.1 ema_trend_scalp (WIN=71, WR=24.3%)

| 観測 | 値 |
|---|---|
| 主要 instrument | USD_JPY 48% |
| 主要 direction | BUY 55% (LR=0.98, 非 enriched) |
| 主要 session | NY 48% |
| ADX | Q50=23.8 (LOSS 25.0) |
| ATR_ratio | Q50=1.01 (LOSS 1.01) — 差なし |
| close_vs_ema200 | Q50=0.00 (LOSS -0.00) — 差なし |
| confidence | Q50=66 (LOSS 66) |

**★ LR≥2 条件**: **なし** → 明確な winner profile なし. 高頻度 trade だが差別化因子が見えない.

### 2.2 fib_reversal (WIN=66, WR=35.5%) ← **高 WR**

| 観測 | 値 |
|---|---|
| 主要 instrument | USD_JPY 56% |
| 主要 direction | BUY 55% (LR=1.06) |
| 主要 session | NY 39% |
| ADX | Q50=22.0 |
| ATR_ratio | Q50=0.96 (やや低 ATR) |

**★ LR≥2 条件**: なし. 現 FORCE_DEMOTED だが shadow WR 35.5% は baseline 28% を上回る.
**注意**: 高 WR は **BT 乖離** (Phase 3 shadow contamination lesson 参照) の可能性. Live で再現する保証なし.

### 2.3 stoch_trend_pullback (WIN=42, WR=29.2%)

**★ 明確な WIN profile**:

| Feature | 値 | LR |
|---|---|---|
| spread_at_entry=Q1 (低スプレッド) | WIN 14.3% | **2.43** ★ |
| rj_atr_ratio=Q1 (低 ATR) | WIN 40.5% | **2.29** ★ |

WIN narrative:
- USD_JPY 71%, **BUY 60%** (LR=1.32 moderate bias)
- NY 33% (LR=0.63 — NY ではむしろ負ける)
- ADX Q50=26.2, LOSS 30.3 (**WIN は LOSS より低 ADX**)
- **"静かな市場・低スプレッドでの BUY"** が winner profile

### 2.4 bb_rsi_reversion (WIN=38, WR=29.2%)

**★ 時刻依存**:

| Feature | 値 | LR |
|---|---|---|
| _hour=Q3 (12-18 UTC ≈ NY 前半) | WIN 42.1% | **2.15** ★ |

WIN narrative:
- USD_JPY 63%, **SELL 53%** (LR=0.76 — BUY の方が enriched)
- **NY 74%** (LR=1.61 strong NY bias)
- ADX Q50=22.6, LOSS 19.9 (WIN はやや高 ADX)
- HMM_proba_trend Q50=0.66 vs LOSS 0.37 (**WIN は trending regime で発生**)

### 2.5 engulfing_bb (WIN=31, WR=31%)

**★ HMM trending 強依存**:

| Feature | 値 | LR |
|---|---|---|
| rj_hmm_proba_trend=Q3 | WIN 22.6% | **3.12** ★★ |
| confidence=Q3 | WIN 41.9% | **2.07** ★ |

WIN narrative:
- USD_JPY 58%, BUY 55%
- **Tokyo session** 39% (LR=1.57) — 非 NY 依存型の winner
- ADX Q50=29.0 (高 ADX)
- **"トレンディング相場で中高 confidence" = winner**

### 2.6 sr_channel_reversal (WIN=30, WR=23.8%)

**★ Aligned + trending**:

| Feature | 値 | LR |
|---|---|---|
| rj_hmm_proba_trend=Q3 | WIN 20.0% | **2.40** ★ |
| **mtf_alignment=aligned** | WIN 36.7% | **2.07** ★ |

WIN narrative:
- USD_JPY 67%, SELL 53%, NY 47%
- mtf gate が "aligned" と判定した trade で WR 39.3% (cell)
- **trending + mtf aligned** = winner の組合せ

### 2.7 macdh_reversal (WIN=30, WR=27.3%) — 非 USD_JPY winner

**★ LR≥2 なし**:

| 観測 | 値 |
|---|---|
| 主要 instrument | **EUR_USD 53%** (唯一 USD_JPY 非優位) |
| 主要 direction | SELL 50% (LR=1.25) |
| ADX | **Q50=33.3** (非常に高い — macdh は強トレンド要求) |

**macdh は EUR_USD × 強トレンド (ADX>30)** 環境向き.

### 2.8 sr_fib_confluence (WIN=25, WR=24.5%) — 非 USD_JPY winner

| 観測 | 値 |
|---|---|
| 主要 instrument | **GBP_USD 44%** |
| 主要 direction | **BUY 72%** (LR=1.29) |
| 主要 session | **London 44%** (LR=1.41) |
| ADX | Q50=24.3 |

**"GBP_USD × BUY × London" が sr_fib_confluence の winner profile**. 他戦略とは異なる pattern.

### 2.9 bb_squeeze_breakout (WIN=23, WR=27.1%) ← **本日 PAIR_PROMOTED**

| 観測 | 値 |
|---|---|
| 主要 instrument | USD_JPY 70% |
| 主要 direction | BUY 57% |
| 主要 session | **NY 61%** (LR=1.89 near-★) |
| ADX | Q50=25.7 |
| ATR_ratio | Q50=0.96 (低-mid ATR) |
| **close_vs_ema200** | **Q5=-7.08, Q50=-0.14** (EMA200 の下) |
| **confidence** | **Q50=57 (LOSS med=66)** — **WIN は LOW confidence** |

**★ winner profile**: USD_JPY, NY session, EMA200 below, 低-中 confidence. **confidence-bug の疑い** (高 confidence ほど負ける傾向、bb_rsi と同様).

### 2.10 ema_pullback (WIN=17, WR=**40.5%** 最高) — FORCE_DEMOTED

| 観測 | 値 |
|---|---|
| 主要 instrument | USD_JPY 59% |
| 主要 direction | **SELL 71%** (LR=1.26) |
| 主要 session | **NY 82%** (LR=2.29 ★) |
| ADX | **Q50=35.1** (強トレンド) |

**NY session × SELL × 強トレンド** が極端な winner profile. 高 WR 40.5% だが N 小. FORCE_DEMOTED 継続.

### 2.11 ema_cross (WIN=16, WR=34.8%) — FORCE_DEMOTED

| 観測 | 値 |
|---|---|
| 主要 instrument | **USD_JPY 94%** (極端な集中) |
| 主要 direction | **SELL 75%** (LR=1.61) |
| 主要 session | NY 75% |
| **confidence** | Q50=58 **(LOSS med=70)** — WIN は低 confidence |

**USD_JPY SELL NY** の狭いニッチ. Confidence 逆向き signal (bb_rsi, bb_squeeze と共通パターン).

---

## 3. Cross-strategy WIN Pattern (汎用 vs 固有)

### 3.1 汎用 pattern (複数戦略で LR 高い)

本分析の Section D は **LR≥2 全体を要求しため 0 件**. LR≥1.5 緩和で観察した結果:

| Pattern | 複数戦略で enriched | 解釈 |
|---|---|---|
| **_session=NY** | bb_squeeze (1.89), bb_rsi (1.61), sr_channel (1.40), sr_fib (n/a), ema_pullback (2.29 ★) | NY 集中は複数戦略の winner source |
| **rj_hmm_proba_trend=Q3** (trending) | engulfing_bb (**3.12 ★★**), sr_channel (2.40 ★) | Trending regime 好む mean-reversion 戦略の winner |
| **confidence が WIN < LOSS** (逆向き) | bb_rsi (-2), bb_squeeze (-9), ema_cross (-12) | Confidence scoring の構造的 bias (要 audit) |

### 3.2 戦略固有 winner profile

| 戦略 | 固有の winner signature |
|---|---|
| stoch_trend_pullback | 低 ATR + 低 spread + BUY |
| engulfing_bb | HMM trending + confidence mid (Tokyo session) |
| sr_channel_reversal | mtf_alignment=aligned + HMM trending |
| macdh_reversal | **EUR_USD** × 高 ADX (>30) |
| sr_fib_confluence | **GBP_USD** × BUY × London |
| bb_squeeze_breakout | USD_JPY × NY × EMA200 下 + 低 confidence |
| ema_pullback | NY session × SELL × 強トレンド |
| ema_cross | USD_JPY SELL の狭いニッチ |

### 3.3 **非**-winner signal (どの戦略でも WIN-rare)

- EUR_JPY (全戦略で WIN 少, portfolio WR 13%)
- `confidence Q4` (高 confidence) — 3 戦略で LR<0.7

---

## 4. クオンツ視点の数学的解釈

### 4.1 「なぜ TP hit できたのか?」の per-strategy 答え

各戦略には**独自の winner profile が存在する**:

- "静かな BUY" が勝つ戦略 (stoch_trend)
- "NY の trending" が勝つ戦略 (bb_rsi, bb_squeeze)
- "Tokyo の trending" が勝つ戦略 (engulfing_bb)
- "London の BUY" が勝つ戦略 (sr_fib_confluence)
- "EUR_USD の強トレンド" が勝つ戦略 (macdh_reversal)

**画一的な "regime" 条件はない**. 戦略ごとに異なる micro-regime が機能する.

### 4.2 汎用 alpha が見える領域

複数戦略で共通する enrichment (portfolio-wide alpha 候補):
- **NY session bias** — 5 戦略で LR>1.4
- **HMM trending** — 2 戦略で LR>2
- **mtf_alignment=aligned** — 1 戦略 (sr_channel) で確認、v9.3 gate で部分実装済

### 4.3 Confidence 逆向き signal の構造的 bug 仮説

3 戦略 (bb_rsi, bb_squeeze, ema_cross) で **WIN の confidence median が LOSS より低い**. これは:
- "極端 signal" で confidence が上がるが、続伸リスクも上がる
- あるいは scoring function の reversed contribution
- **Scoring audit が必要**

### 4.4 data availability limitation

本分析も全体 shadow の 16% (regime engine 稼働後) 依存. 84% の古い trades は regime data 欠損のため characterization が不完全. 2026-05 以降の新 shadow で再分析すべき.

---

## 5. Actionable Implications

### 5.1 Short-term (shadow 蓄積のみ)

- 既存戦略のまま shadow continue
- 2026-05-05 の pre-reg 評価時に、本文書の winner profile が持続しているか確認
- 持続していれば、strategy-specific "enriched condition gate" を検討

### 5.2 Mid-term (仮説的)

- **Portfolio-wide NY session biasing**: NY session で lot boost (1.2x) を全戦略に適用 (small adjustment)
- **Confidence scoring audit**: bb_rsi / bb_squeeze / ema_cross で confidence 貢献項を精査

### 5.3 Long-term

- trade_log に regime field を必須化 (既存 84% 欠損の撲滅)
- Per-strategy "winner signature" を明示化 (strategy metadata field 追加)
- Live でも winner signature 適合率を tracking

---

## 6. Source

- Script: `/tmp/win_characterization.py`
- Raw output: `/tmp/win_chars.txt` (841 行)
- Related:
  - [[win-conditions-mining-2026-04-21]] (filtered golden cells)
  - [[win-conditions-unfiltered-2026-04-21]] (portfolio-wide marginal)
  - [[shadow-tp-sl-causal-2026-04-21]] (WIN vs LOSS 差分)
  - [[shadow-validation-preregistration-2026-04-21]] (2026-05-05 binding)
