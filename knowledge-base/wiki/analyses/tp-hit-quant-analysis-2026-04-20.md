# TP-hit Quant Analysis — 2026-04-20 (実行日 2026-04-22)

**研究スコープ**: 全戦略×全通貨ペアで TP を達成した（= outcome=WIN）トレードの統計分析。
「どのような条件で TP-hit が起きたか」「その条件は再現性があるか」を数学的に問う。
**本ドキュメントは KB 記録のみ — 実装提案・戦略変更提案は一切しない**（[[lesson-reactive-changes]]）。

## データウィンドウ（重要 — [[lesson-all-time-vs-post-cutoff-confusion]]）

| 項目 | 値 |
|---|---|
| データソース | `GET /api/demo/trades?limit=5000` (Render prod) |
| 取得日時 | 2026-04-22 00:41 UTC |
| raw total trades | 2,525 |
| 非XAU | 2,500 |
| status=CLOSED 非XAU | 2,496（BREAKEVEN 229 含む） |
| outcome ∈ {WIN, LOSS} 非XAU | 2,267（本分析の分母） |
| **TP-hit (outcome=WIN)** | **698**（= pre/post cutoff 合算） |
| close_reason=TP_HIT のみ | 469（狭義） |
| Cutoff | 2026-04-16T08:00:00+00:00（`_FIDELITY_CUTOFF`） |
| Pre-cutoff WIN | 445 / Post-cutoff WIN | 253 |
| Live WIN (is_shadow=0) | 173 / Shadow WIN (is_shadow=1) | 525 |

### TP-hit の定義
本分析では **TP-hit = `outcome == 'WIN'`** を採用（= プラス決済で終わったトレード）。  
この定義は brief 記載の「TP-hit 709」に近い（実データ更新で 698 に微減）。  
狭義の `close_reason == 'TP_HIT'` は 469 件のみ — 残り 229 WIN の close_reason 内訳:

| close_reason | N | 説明 |
|---|---|---|
| TP_HIT | 458 | ローカル TP タッチ |
| OANDA_SL_TP | 108 | OANDA 側での TP 約定（broker bracket） |
| SIGNAL_REVERSE | 92 | 反対シグナル発生で clamp close（利益確定） |
| MAX_HOLD_TIME | 29 | 最大保有時間タイムアウト時にプラス |
| MANUAL_CLOSE | 9 | 手動閉じ |
| WEEKEND_CLOSE | 2 | 金曜ポジション強制決済 |

→ "TP-hit" は 機構上 6 種の exit ルートを含むため、「価格がTPに到達」以上に広い概念。以下の分析ではこの **outcome=WIN** 定義を採用。

## Base Rate（基準率）

| Window | N | WIN | WR |
|---|---|---|---|
| All closed (outcome=WIN/LOSS) non-XAU | 2,267 | 698 | **30.79%** |
| Pre-cutoff | 1,315 | 445 | 33.84% |
| Post-cutoff | 952 | 253 | 26.58% |
| Live only | 378 | 169 | 44.71%（★pre-cutoff 主体）|
| Shadow only | 1,889 | 529 | 28.00% |

**所見**:
- Pre/Post cutoff で 7.3pp 差 — post-cutoff では WR が低下。  
- Live pool は pre-cutoff 378 trades のみ（post-cutoff Live N=0 — 現状 Live はほぼ停止）。  
- 「Live WR 44.7%」は Fidelity Cutoff 前の汚染データを多く含む点に注意 ([[lesson-all-time-vs-post-cutoff-confusion]])。

---

## Phase 1 — セグメンテーション（WR 分布）

### 1.1 Strategy × Pair（Top 15, N≥20）

| strategy × pair | N | WIN | WR% | lift | 95%CI |
|---|---|---|---|---|---|
| bb_rsi_reversion × USD_JPY | 299 | 127 | 42.5 | 1.38 | [37.0, 48.1] |
| vol_surge_detector × USD_JPY | 59 | 24 | 40.7 | 1.32 | [29.1, 53.4] |
| ema_pullback × USD_JPY | 25 | 10 | 40.0 | 1.30 | [23.4, 59.3] |
| sr_fib_confluence × GBP_USD | 28 | 11 | 39.3 | 1.28 | [23.6, 57.6] |
| trend_rebound × USD_JPY | 24 | 9 | 37.5 | 1.22 | [21.2, 57.3] |
| bb_rsi_reversion × EUR_USD | 83 | 31 | 37.3 | 1.21 | [27.7, 48.1] |
| engulfing_bb × EUR_USD | 28 | 10 | 35.7 | 1.16 | [20.7, 54.2] |
| ema_cross × USD_JPY | 42 | 15 | 35.7 | 1.16 | [23.0, 50.8] |
| fib_reversal × EUR_USD | 76 | 27 | 35.5 | 1.15 | [25.7, 46.7] |
| sr_channel_reversal × GBP_USD | 24 | 8 | 33.3 | 1.08 | [18.0, 53.3] |
| fib_reversal × USD_JPY | 117 | 38 | 32.5 | 1.05 | [24.7, 41.4] |
| stoch_trend_pullback × EUR_USD | 28 | 9 | 32.1 | 1.04 | [17.9, 50.7] |
| engulfing_bb × USD_JPY | 75 | 24 | 32.0 | 1.04 | [22.5, 43.2] |
| macdh_reversal × EUR_USD | 51 | 16 | 31.4 | 1.02 | [20.3, 45.0] |
| bb_squeeze_breakout × USD_JPY | 53 | 16 | 30.2 | 0.98 | [19.5, 43.5] |

- 最多 TP-hit: **bb_rsi_reversion × USD_JPY = 127 件** — 戦略×ペア単独で全 TP-hit の 18.2%。
- Top 5 のうち 4 つが USD_JPY。単一通貨への偏りが強い（構造的理由: USD_JPY N 最多・BEV_WR=34.4% も最良）。

### 1.2 Regime

| regime | N | WIN | WR% | lift | 95%CI |
|---|---|---|---|---|---|
| RANGE | 1,084 | 343 | 31.6 | 1.03 | [28.9, 34.5] |
| TREND_BULL | 622 | 187 | 30.1 | 0.98 | [26.6, 33.8] |
| TREND_BEAR | 528 | 154 | 29.2 | 0.95 | [25.5, 33.2] |
| unknown | 33 | 14 | 42.4 | 1.38 | N<50 無視 |

**所見**: Regime 単独では lift ≈ 1.0 で差はほぼない。regime 単独は TP-hit 予測力ゼロ。

### 1.3 Direction / TF / Session / MTF-alignment

| 軸 | 値 | N | WR% | lift |
|---|---|---|---|---|
| direction | BUY | 1,162 | 31.7 | 1.03 |
|  | SELL | 1,105 | 29.9 | 0.97 |
| tf | 1m | 1,265 | 33.8 | 1.10 |
|  | 5m | 536 | 25.9 | 0.84 |
|  | 15m | 448 | 28.3 | 0.92 |
| session | ny | 935 | 32.5 | 1.06 |
|  | london_pre | 790 | 30.6 | 0.99 |
|  | tokyo | 493 | 29.4 | 0.96 |
|  | late (20-24UTC) | 49 | 14.3 | 0.46 |
| mtf_alignment | aligned | 138 | 35.5 | 1.15 |
|  | conflict | 320 | 24.7 | 0.80 |
|  | unknown | 33 | 21.2 | 0.69 |
|  | (未設定) | 1,774 | 31.7 | 1.03 |

**所見**:
- 1m TF が 5m/15m より +7.9pp 高 WR (N=1,265, 統計有意)。**ただし R-multiple と EV で検証必要**（後述）。
- late session (20-24 UTC) の WR=14.3% は顕著に低い（N=49、幅広 CI）。  
- `mtf_alignment=aligned` は +4.7pp lift — 既知 [[bb-rsi-reversion]] REGIME_ADAPTIVE と整合。

### 1.4 Window × Pool

| window_pool | N | WIN | WR% | lift |
|---|---|---|---|---|
| pre_live | 378 | 169 | 44.7 | 1.45 |
| pre_shadow | 937 | 276 | 29.5 | 0.96 |
| post_shadow | 947 | 249 | 26.3 | 0.85 |
| post_live | 0 | 0 | — | — |

**最重要所見**: Pre-cutoff Live の WR=44.7% は Post-cutoff shadow WR=26.3% を **18.4pp** 上回る。  
これは Fidelity Cutoff の意味 ([[lesson-clean-slate-2026-04-16]]) をそのまま反映し、pre-cutoff の数値を使った結論は全て再検証対象。

---

## Phase 2 — TP-hit vs LOSS Feature Contrast（Mann-Whitney U, Bonferroni補正）

| feature | N_WIN | N_LOSS | median_WIN | median_LOSS | mean_WIN | mean_LOSS | z | p | Bonf pass (α=0.0071) |
|---|---|---|---|---|---|---|---|---|---|
| score | 698 | 1,569 | 0.000 | 0.000 | 0.428 | 0.294 | -0.80 | 0.422 | no |
| confidence | 698 | 1,569 | 61.0 | 63.0 | 59.55 | 61.16 | -3.28 | 0.00102 | **YES (negative)** |
| ema_conf | 698 | 1,569 | 64.0 | 66.0 | 65.02 | 66.43 | -2.68 | 0.0075 | marginal no |
| spread_at_entry | 698 | 1,569 | 0.80 | 0.80 | 0.763 | 0.842 | -4.27 | 1.94e-05 | **YES** |
| mafe_favorable_pips | 698 | 1,569 | 5.4 | 0.0 | 6.66 | 1.10 | -25.08 | 8.1e-139 | **YES ** (post-hoc) |
| mafe_adverse_pips | 698 | 1,569 | 0.9 | 3.6 | 1.26 | 4.54 | -25.26 | 9.9e-141 | **YES** (post-hoc) |
| slippage_pips | 698 | 1,569 | 0.40 | 0.40 | 0.423 | 0.380 | -1.37 | 0.171 | no |

**Bonferroni 通過 5 件、ただし解釈に注意**:
1. **mafe_favorable / mafe_adverse** は **intra-trade post-hoc 指標**。TP-hit と機構上ほぼ同義（分母=母集団から WIN を抜き出せば favorable が大きいのは当然）。**これらは再現性条件として採用しない**。
2. **spread_at_entry が WIN で 0.08 pip 低い**（0.763 vs 0.842） — 経済的には BEV_WR=34.4% を 1pp 近く押し上げる実効的エッジ。低スプレッド時の発注が TP-hit と相関。
3. **confidence が WIN で 1.6 低い**（負の相関！）— 直感に反するが、high-confidence ほど thin edge で失敗する可能性を示唆（[[lesson-confidence-ic-zero.md]] と整合）。
4. **score の分布は WIN vs LOSS で統計的に識別不能**（p=0.42） — 現行 score_gate は TP-hit 予測力ゼロ。

---

## Phase 3 — 再現性条件マイニング（事前予測可能な特徴のみ）

### 除外方針（データリーク防止）
`mafe_favorable`, `mafe_adverse`, `mafe_ratio`, `exit_price`, `pnl_*`, `outcome` は **トレード進行中/終了後** に観測される変数であり、**エントリー時点で取得不能**。Phase 3 の候補から明示除外し、以下の **エントリー時点で確定している特徴のみ**で条件候補を作成した。

### 候補プール
- Strategy × pair（N≥30 の全組合せ）
- Regime (RANGE / TREND_BULL / TREND_BEAR / unknown)
- Direction (BUY / SELL)
- TF (1m / 5m / 15m)
- Session (tokyo / london_pre / ny / late)
- MTF alignment (aligned / conflict / unknown / blank)
- score_bucket (>=3, <=0)
- confidence (>=60), ema_conf (>=60)
- spread (<=0.8)
- mtf_vol_state, layer1_dir, gate_group, mode
- Composite: strat × pair × regime / × session / × direction（N≥30）

候補数: **m = 107**、Bonferroni α = 0.05 / 107 = **0.000467**

### 採択基準（全項目 AND）
1. N ≥ 30
2. Lift ≥ 1.20
3. Wilson 95% CI 下限 > base rate (30.79%)
4. Binomial p < α_Bonferroni

### Bonferroni 通過条件（5件）

| # | Condition | N | WIN | WR% | Lift | Wilson 95%CI | p(binom) | 備考 |
|---|---|---|---|---|---|---|---|---|
| 1 | bb_rsi_reversion × EUR_USD × BUY | 31 | 20 | **64.5** | 2.10 | [46.9, 78.9] | 4.7e-05 | N 境界、高 WR |
| 2 | bb_rsi_reversion × USD_JPY × BUY | 141 | 65 | 46.1 | 1.50 | [38.1, 54.3] | 8.2e-05 | 最大 N の有意条件 |
| 3 | bb_rsi_reversion × USD_JPY × regime=RANGE | 186 | 80 | 43.0 | 1.40 | [36.1, 50.2] | 3.1e-04 | 最大 N |
| 4 | bb_rsi_reversion × USD_JPY | 299 | 127 | 42.5 | 1.38 | [37.0, 48.1] | 1.2e-05 | base marginal aggregation |
| 5 | layer1_dir=bull | 281 | 116 | 41.3 | 1.34 | [35.7, 47.1] | 1.4e-04 | MTF htf bias indicator |

**全 5 件が bb_rsi_reversion 関連または MTF-bull に集約**。他戦略は Bonferroni α=0.00047 を通過できなかった。

### DSR-style Multiple-Testing Deflation
- Tests performed: m=107
- Expected false-positives (α=0.05 naive): 107×0.05 = 5.4
- Observed passes at Bonferroni: 5
- **結論**: Bonferroni 通過数（5）は帰無仮説下の偽陽性期待値（5.4）と同程度 → **family-wise シグナルは弱い**。個別条件の採択は Phase 5 安定性チェックに依存する。

---

## Phase 4 — Kelly-like EV per Condition

`pnl_pips` / `pnl_r` 実データから各条件の EV・シャープ・Kelly を算出。

| Condition | N | WR% | EV(pip) | EV(R) | σ(pip) | Sharpe | Kelly frac | Wilson 95%CI |
|---|---|---|---|---|---|---|---|---|
| bb_rsi_reversion × EUR_USD × BUY | 31 | 64.5 | **+1.84** | +0.38 | 4.09 | +0.45 | **+0.413** | [46.9, 78.9] |
| bb_rsi_reversion × USD_JPY × BUY | 141 | 46.1 | **-0.12** | -0.00 | 4.82 | -0.02 | -0.028 | [38.1, 54.3] |
| bb_rsi_reversion × USD_JPY × RANGE | 186 | 43.0 | **-0.54** | -0.11 | 4.66 | -0.12 | -0.128 | [36.1, 50.2] |
| bb_rsi_reversion × USD_JPY | 299 | 42.5 | **-0.46** | -0.08 | 4.80 | -0.10 | -0.107 | [37.0, 48.1] |
| layer1_dir=bull | 281 | 41.3 | **-0.66** | -0.10 | 5.61 | -0.12 | -0.152 | [35.7, 47.1] |

### 🚨 重大な発見: 高 WR だが 負 EV
Phase 3 で Bonferroni 通過した 5 条件のうち、**4 条件 (80%) が Kelly < 0 = 負 EV**。  
WR=42-46% は BEV_WR=34.4% を 8-12pp 上回るが、**friction と負 R-multiple 部分（SL hit の R=-1.0）でキャンセル**され Kelly は 0 以下。  
[[bb-rsi-reversion]] の "Edge = 0.45pip/trade (extremely thin)" と整合。「高 WR = 再現性ある勝ち」は **誤読**。

### 唯一の +EV: bb_rsi_reversion × EUR_USD × BUY
- EV = +1.84 pip, Kelly = +0.413（half-Kelly でも +0.21）
- ただし **N=31** は Kelly 採用に必要な N≥30 をぎりぎり通過、σ=4.09 で Sharpe +0.45 は微弱
- Wilson lower=46.9% は印象より幅広。CI 上限 78.9% からの狭窄にはあと数十件の post-cutoff N が必要

---

## Phase 5 — 安定性（Stability）: Pre/Post Cutoff × Live/Shadow

[[lesson-orb-trap-bt-divergence]] 流儀で、同一条件下で pre/post/live/shadow の **EV 符号が一致するか**を検査。

| Condition | pre N | pre EV | post N | post EV | live N | live EV | shadow N | shadow EV | sign_ok |
|---|---|---|---|---|---|---|---|---|---|
| bb_rsi_reversion × EUR_USD × BUY | 25 | +1.24 | 6 | +4.33 | 24 | +1.12 | 7 | +4.30 | **YES (4/4 positive)** |
| bb_rsi_reversion × USD_JPY × BUY | 104 | +0.02 | 37 | -0.50 | 96 | +0.12 | 45 | -0.63 | **no (flip)** |
| bb_rsi_reversion × USD_JPY × RANGE | 110 | +0.16 | 76 | -1.56 | 100 | +0.17 | 86 | -1.37 | **no (flip)** |
| bb_rsi_reversion × USD_JPY | 213 | +0.01 | 86 | -1.63 | 198 | +0.10 | 101 | -1.56 | **no (flip)** |
| layer1_dir=bull | 274 | -0.66 | 7 | -0.69 | 118 | +0.20 | 163 | -1.29 | **no (flip)** |

### 読み取り
- **bb_rsi_reversion × EUR_USD × BUY** のみ 4 window 全てで EV > 0（再現性強）。**ただし post-cutoff N=6 は統計無意**、Live N=24 も境界。
- **bb_rsi_reversion × USD_JPY 系 3 条件は全て post-cutoff で EV 反転**。Pre-cutoff +0.01〜+0.16 → Post-cutoff -0.50〜-1.63 という 0.5-1.8pip の悪化は、orb-trap と同じ curve-fit/regime-shift 脆弱性のシグナル。
- **layer1_dir=bull**: Live pool では +0.20 だが shadow では -1.29。live/shadow routing ([[lesson-shadow-contamination]]) の差を反映している可能性あり — 単独条件としての採択は不適切。

---

## 最終トリアージ

| 条件 | Bonferroni | Wilson CI | EV+ | 符号一致 | 判定 |
|---|---|---|---|---|---|
| **bb_rsi_reversion × EUR_USD × BUY** | ✅ | ✅ | ✅ (+1.84 pip) | ✅ (4/4) | **最も robust、ただし N=31 境界** |
| bb_rsi_reversion × USD_JPY × BUY | ✅ | ✅ | ❌ (-0.12) | ❌ | 脆弱（post 反転）|
| bb_rsi_reversion × USD_JPY × RANGE | ✅ | ✅ | ❌ (-0.54) | ❌ | 脆弱（post 反転）|
| bb_rsi_reversion × USD_JPY | ✅ | ✅ | ❌ (-0.46) | ❌ | 脆弱（post 反転）|
| layer1_dir=bull | ✅ | ✅ | ❌ (-0.66) | ❌ | pool 間で符号反転 |

**最も robust**: bb_rsi_reversion × EUR_USD × BUY — WR 64.5% [46.9, 78.9], EV +1.84 pip, Kelly +0.41, 4 window sign-coherent. 警告: N=31（post-cutoff N=6 は別途 N≥20 蓄積後に再検証必須）。

**最も脆弱**: bb_rsi_reversion × USD_JPY × RANGE — pre-cutoff EV +0.16 から post-cutoff EV -1.56 へ 1.7 pip 悪化。[[bb-rsi-reversion]] の post-cutoff shadow EV=-1.83 と完全整合し、[[lesson-orb-trap-bt-divergence]] (短期高 WR は curve-fit 疑う) の典型例。

## 制限事項と caveats

1. **Post-cutoff Live N=0**: 現行 Live ルーティングでは post-cutoff 期間の Live pool が空（Fidelity cutoff=2026-04-16、Live shutdown=v9.x）。Live re-enable 後の N≥30 蓄積待ち。
2. **Shadow データは score_gate 通過分のみ** ([[shadow-baseline-2026-04-20]] Truncated Sample Bias)。 Post-P1 score_gate bypass の新規データで再検証必要。
3. **close_reason の多元性**: "TP-hit" に TP_HIT / OANDA_SL_TP / SIGNAL_REVERSE / MAX_HOLD_TIME を含むため、純粋な「価格が TP へ到達」の再現性とは乖離。close_reason 別の再分析は future work。
4. **pnl_r は 全 WIN で正値**（LOSS 側の負 R は含まない） — 本分析の EV は全サンプル（WIN+LOSS）加重で算出している点に注意。
5. **m=107 の multiple testing 補正を適用済み**だが、条件を事後選別した時点で事前仮説ではなくなる → 本分析は **hypothesis-generating exploratory analysis** であり confirmatory ではない。confirmatory 再検証は post-cutoff N≥100 の pre-registered 条件で行うべき（[[pre-registration-2026-04-21]] 方式）。
6. **XAU は全処理で除外**（[[feedback_exclude_xau]]）。

## 数学的まとめ（re-usable formulas）

- P(TP-hit | cond) = k/n, Wilson 95% CI = (centre ± half) with `centre=(p+z²/2n)/(1+z²/n)`, `half=z√(p(1-p)/n+z²/4n²)/(1+z²/n)`
- Expected R per condition: E[R|cond] = avg(pnl_r over all trades in cond) (includes LOSS contribution)
- Kelly fraction (per-condition): `f* = P - (1-P)/b`, where b = avg(win_pip) / avg(loss_pip)
- Bonferroni: α_adjusted = α / m, m = # of candidate conditions tested

## 成果物

- 本ページ: `knowledge-base/wiki/analyses/tp-hit-quant-analysis-2026-04-20.md`
- 集計 CSV: `knowledge-base/raw/analysis/tp-hit-raw-2026-04-20.csv`
- 再現スクリプト: `scripts/analyze_tp_hits.py`（再実行は `curl > /tmp/trades_all.json && python3 scripts/analyze_tp_hits.py`）

## Related

- [[bb-rsi-reversion]] — 本分析の中心戦略、post-cutoff EV=-1.76 と整合
- [[shadow-baseline-2026-04-20]] — 既知の shadow baseline、USD_JPY の EV 悪化と一致
- [[lesson-orb-trap-bt-divergence]] — 短期高 WR curve-fit 脆弱性の先行事例
- [[lesson-all-time-vs-post-cutoff-confusion]] — データウィンドウ明示の必要性
- [[lesson-reactive-changes]] — 分析→対策を分離するプロセス遵守
- [[pre-registration-2026-04-21]] — confirmatory 再検証の形式
- [[mtf-regime-validation-2026-04-17]] — MTF alignment の符号検査
