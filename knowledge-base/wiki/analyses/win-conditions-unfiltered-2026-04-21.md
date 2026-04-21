# WIN Conditions — Unfiltered Marginal Distribution

**日付**: 2026-04-21
**姉妹分析**: [[win-conditions-mining-2026-04-21]] (filtered "golden cells")

## 目的

[[win-conditions-mining-2026-04-21]] は filter 後の "golden cells" のみ報告していた. **cherry-picking bias** への対策として、本文書は **全 shadow trade・全 feature・全 category の unfiltered marginal distribution** を記録する.

## 🚨 最重要発見: Regime data の 84% は missing

| Feature | WIN 中 missing 割合 |
|---|---:|
| mtf_regime | **84.1%** |
| mtf_vol_state | **84.1%** |
| mtf_d1_label | **84.1%** (default="3" のみ) |
| mtf_h4_label | **84.1%** (default="3" のみ) |
| mtf_alignment | **84.1%** |

**意味**: regime engine (v9.2.1, 2026-04 以降稼働) 以前の trade は regime tags が無い.
→ **先の regime 分析は実質 16% (~272 trades) の subset に基づいていた**.

これが先の [[shadow-tp-sl-causal-2026-04-21]] Phase 3 で regime 系が null finding になった一因 (data availability の問題 × 真の null effect が混在).

## 1. Strategy-level Unfiltered Summary (N 制限なし)

全 44 戦略 × shadow:

### 高 WR (baseline 28.1% を上回る, N≥20)

| Strategy | N | WIN | LOSS | WR |
|---|---:|---:|---:|---:|
| dt_bb_rsi_mr | 35 | 16 | 19 | **45.7%** |
| trend_rebound | 22 | 9 | 13 | **40.9%** |
| ema200_trend_reversal | 20 | 8 | 12 | **40.0%** |
| ema_pullback | 42 | 17 | 25 | **40.5%** |
| fib_reversal | 186 | 66 | 120 | 35.5% |
| ema_cross | 46 | 16 | 30 | 34.8% |
| dt_sr_channel_reversal | 36 | 12 | 24 | 33.3% |
| engulfing_bb | 100 | 31 | 69 | 31.0% |

**注意**: これらは **すべて FORCE_DEMOTED / SHADOW-only**. 高 shadow WR と 365d BT EV は**無関係** (過去の判断履歴を参照).
例: `ema_pullback` は shadow WR 40.5% だが FORCE_DEMOTED (v9.1 削除). Shadow での勝ち方と Live での勝ち方は別問題 — Phase 3 shadow contamination 教訓を再確認.

### 低 WR (要注意)

| Strategy | N | WR |
|---|---:|---:|
| dual_sr_bounce | 22 | **9.1%** |
| vol_momentum_scalp | 19 | 10.5% |
| sr_break_retest | 24 | 12.5% |

## 2. Portfolio-wide Marginal — Unfiltered

全 shadow 1,716 trades (WIN=483, LOSS=1233, baseline WR=28.1%).

### 2.1 Instrument (where WIN concentrates)

| Instrument | N | W | L | WR | WIN share | 判定 |
|---|---:|---:|---:|---:|---:|---|
| USD_JPY | 951 | 266 | 685 | 28.0% | **55.1%** | baseline |
| EUR_USD | 438 | 129 | 309 | **29.5%** | 26.7% | +1.4pp |
| GBP_USD | 242 | 67 | 175 | 27.7% | 13.9% | baseline |
| **EUR_JPY** | **46** | **6** | **40** | **13.0%** ↓ | 1.2% | **-15pp 致命的** |

### 2.2 Direction — symmetric at portfolio level

| | N | W | L | WR |
|---|---:|---:|---:|---:|
| BUY | 905 | 255 | 650 | 28.2% |
| SELL | 811 | 228 | 583 | 28.1% |

**意味**: 先の bb_rsi BUY非対称性 (40% vs 19%) は **strategy-specific** であり portfolio-wide ではない. 全体に direction filter を掛ける根拠はなし.

### 2.3 Session

| Session | N | WR | WIN share |
|---|---:|---:|---:|
| **NY** | 740 | 29.9% ↑ | 45.8% |
| London | 498 | 27.7% | 28.6% |
| Tokyo | 478 | 25.9% ↓ | 25.7% |

NY +1.8pp, Tokyo -2.2pp — 小さい差. Session-based global filter の根拠としては弱い.

### 2.4 mtf_alignment (16% subset only)

**Where data exists**:

| Alignment | N | WR | 判定 |
|---|---:|---:|---|
| **aligned** | 90 | **35.6%** ↑ | +7.5pp vs baseline |
| conflict | 192 | 21.4% ↓ | -6.7pp vs baseline |

**14pp gap**. これは最も clean な portfolio-wide signal. ただし:
- Data availability 限定 (16% of trades)
- すでに `strategy_aware_alignment` gate が conflict → shadow downgrade を実装済 (v9.3)

### 2.5 rj_hmm_regime (56% subset)

| HMM Regime | N | WR |
|---|---:|---:|
| ranging | 471 | 24.0% ↓ |
| trending | 361 | 26.9% |
| (missing) | 884 | 30.9% |

HMM regime-based filter で大きな edge なし.

## 3. Filtered vs Unfiltered 比較

| 観点 | Filtered (golden cells) | Unfiltered |
|---|---|---|
| 対象戦略数 | 7 | 44 |
| 対象 trade 数 | ~900 (filter pass 後) | 1,716 |
| 最大 Lift 報告 | 2.35x | 1.27x (mtf_alignment aligned) |
| Bonferroni 問題 | "top cell" bias | 全 null も見える |
| 決定根拠 | Hypothesis 生成向き | Portfolio-wide 判断向き |

**Filtered 分析は hypothesis 生成**に、**Unfiltered 分析は portfolio gate 判断**に使うべき.

## 4. 真の Actionable Findings

### 4.1 確実な findings

1. **EUR_JPY は WR 13%** (N=46) — portfolio-wide で実弾除外が強く示唆される. 既存 PAIR_DEMOTED チェック要.
2. **mtf_alignment aligned vs conflict = 14pp gap** — 既に v9.3 gate で実装済. 継続監視.

### 4.2 弱い findings

3. NY session slight edge (+1.8pp) — 単独 gate 根拠としては弱い.
4. EUR_USD slight edge (+1.4pp) — 同上.

### 4.3 仮説 (更なる検定必要)

5. Golden cells (filtered 分析) — shadow で 2026-05-05 まで蓄積して確認.
6. Regime engine 稼働後 (84% 解消後) の regime-based 分析を reconfirm.

## 5. 先の誤解の訂正

先の分析で「regime は WIN/LOSS を予測しない (p>0.2, V<0.24)」と報告したが、真の state は:

> **regime data が 84% missing. 有効 subset (16%, ~280 trades) で検定したため N-unpowered の null finding だった可能性がある**.

従って今後の regime 再評価は:
- regime engine 稼働後 (2026-04 以降) の trade のみに絞る
- N が十分蓄積後に再検定
- post-2026-05-01 で subset が 40%+ になった時点で再評価

## 6. 統計的 caveat

1. **Marginal distribution ≠ causal**: category × category 交絡 (instrument × regime など) は marginal では見えない
2. **Shadow ≠ Live**: 本分析の全結果は shadow. Live での再現性は未検証.
3. **Pre-v9.x artifact**: 古い trade は当時のロジックで生成. 現在のロジックと挙動が異なる.

## 7. Source

- Script: `/tmp/win_unfiltered_analysis.py`
- Raw output: `/tmp/win_unfiltered.txt`
- Related:
  - [[win-conditions-mining-2026-04-21]] (filtered golden cells)
  - [[shadow-tp-sl-causal-2026-04-21]] (differential WIN vs LOSS)
  - [[pre-registration-2026-04-21]] (LIVE 監視)
