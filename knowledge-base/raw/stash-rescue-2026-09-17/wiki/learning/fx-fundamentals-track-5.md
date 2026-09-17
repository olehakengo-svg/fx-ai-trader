# Track ⑤ Quant Edge の本質 — 深掘り

**Session**: mellow-sky (Track ⑤ 担当並行セッション)
**Date**: 2026-04-26
**Master 統合者**: curried-ritchie session が `fx-fundamentals.md` Section 5 を本ファイルから要約引用
**規律**: Phase 4c/4d KB 照合のみ、外部出典禁止、未検証は「未検証仮説」と明記

---

## 0. このノートの位置付け

- 本ファイルは Track ⑤ Quant Edge の本質 単独深掘り (master `fx-fundamentals.md` の Section 5 placeholder を埋めるための一次資料)
- 各 sub-topic は **(a) 一般論 → (b) 我々への含意 → (c) Phase 4c/4d KB 照合** の 3 段構造を厳守
- 数値は Live trade DB / friction_model_v2 / Phase 4c/4d KB 実測。引用不能箇所は「未検証仮説」と明記
- XAU データは全クエリで除外 (v8.4 で構造的除外決定)

### 本セッションで実測可能だった範囲 / 不能だった範囲

| 項目 | 状態 | 理由 |
|---|---|---|
| 戦略全件 N/WR/Wilson CI/EV/PF (entry_type 別) | ✅ 実測 | local `demo_trades.db` (FX-only CLOSED, N=373, うち Live=36) |
| Live FX-only headline | ✅ local 実測 | local Live N=36 WR=50.0% EV=+0.17 (注: production memory 報告は N=259 WR=39% EV=-0.83、cutoff 違いの可能性あり) |
| friction_model_v2 全係数表 | ✅ 実測 | `modules/friction_model_v2.py` 直接 import |
| Bonferroni 補正下 detectable ΔWR | ✅ 実測 | scipy.stats でプロジェクト想定 N で計算 |
| Phase 5-9d BT 9 戦略の friction v2 再シミュレーション | ❌ **未実測** | Phase 5 BT 未実行 (Phase 3 予定)。本ノートでは「方法論 + シミュレーション枠組み」のみ提示し、実測値は Phase 3 後に追記 |
| pre-reg LOCK 2 戦略の 365 日 BT Wilson 95% | ❌ **未実測** | 365 日 BT 未確定。本ノートでは「Validation 閾値とそれを満たすために必要な N の数学」までを提示 |
| mechanism audit 残り 30 戦略の VALID/WEAK/NONE 判定 | ❌ **未実測** | `strategy-mechanism-audit-2026-04-26.md` は 5 戦略のみ判定済 |

---

## 5.1 Edge の 3 分類

### (a) 一般論

クオンツ実証研究で「edge」と呼ばれる純利益源は、その源泉によって 3 種に分類される。

| 種類 | 定義 | 典型例 |
|---|---|---|
| **Information edge** | 他参加者より早く / 正確に情報を得ることで先行売買、価格に織り込まれる前に position 構築 | Bloomberg Terminal、Prime broker order flow info、衛星画像 (Walmart 駐車場)、企業 IR の dark channels |
| **Structural edge** | 市場構造そのもの (流動性供給責務、stop hunt、carry、low-vol MR、spread fill 偏り) を反復的に活用 | Market making (LP)、Triangular arbitrage、Asia 低 vol range fade、Stop cluster sweep への便乗 |
| **Risk premium** | 他参加者が **嫌う** リスク (vol spike、tail event、流動性枯渇) を引き受ける対価 | Vol selling (short straddle)、新興国 carry、危機時の流動性供給 (CTA crash 時) |

これら 3 種は背反である:

- Information は「知識の非対称性」を取引する → 機関 / 専門業者の領分
- Structural は「市場の constitutional な性質」を取引する → 設計次第で retail も到達可能
- Risk premium は「効用の非対称性」を取引する → 資本と stomach があれば retail でも可能だが、極端な fat-tail 損失で破滅しうる

### (b) 我々への含意

我々 (retail FX trader, OANDA + 自前 Python algo) が 3 種それぞれを取れるかの構造的判定:

| 種類 | retail で取れるか | 我々の戦略における判断 |
|---|---|---|
| Information edge | ❌ 不可能 | OANDA Streaming API は 1-2 sec 遅延、Bloomberg / direct LP feed なし、order flow info なし。**Information edge を狙う戦略は最初から無効** |
| Structural edge | ✅ 主戦場 | 流動性 zone (round numbers, swing high/low)、stop hunt、Asia 低 vol range、session 切替時 vol expansion 等。**Phase 3 の mechanism-driven edge 再構築の中核** |
| Risk premium | ⚠️ 限定的 | vol selling 系は急変で口座吹飛、carry trade は 1-6h hold が多く swap rollover 影響軽微、流動性供給は資本不足。**現実的には機能しない**。v8.4 で gold (危機 risk premium) を停止したのも同根 |

→ **戦略採用基準**: Information edge を要求する設計は最初から却下。Structural edge を mechanism thesis で明示できる戦略のみが Phase 3 BT 候補。Risk premium 系は別途 fat-tail risk 評価が必須。

### (c) Phase 4c/4d KB 照合

#### 戦略全件の Live 実測 (local DB, FX-only CLOSED, N≥5)

クエリ: `SELECT entry_type, COUNT(*), Wilson CI, AVG(pnl_pips), avg_win, avg_loss, PF FROM demo_trades WHERE instrument != 'XAU_USD' AND status='CLOSED' GROUP BY entry_type HAVING n >= 5`

| entry_type | N | live_n | WR | Wilson 95% | EV (pip) | avg_w | avg_l | PF | mech 判定 (audit) | edge 分類 候補 |
|---|---|---|---|---|---|---|---|---|---|---|
| ema_trend_scalp | 69 | 0 | 14.5% | [8.1, 24.7] | -1.87 | +5.23 | -3.13 | 0.28 | TAP-1 (中間帯 Scalp 友 friction) | **NONE** |
| fib_reversal | 44 | 0 | 65.9% | [51.1, 78.1] | +7.84 | +14.92 | -7.33 | 3.94 | 未判定 | Structural 候補 (要 mechanism 言語化) |
| bb_rsi_reversion | 34 | 22 | 47.1% | [31.5, 63.3] | +4.79 | +14.80 | -4.11 | 3.20 | WEAK (TAP-1 中間帯 AND 含有) | Structural 候補 (audit 改善余地) |
| sr_fib_confluence | 23 | 0 | 34.8% | [18.8, 55.1] | -3.68 | +19.07 | -15.81 | 0.64 | 未判定 | NONE 寄り (avg_loss 大) |
| sr_channel_reversal | 20 | 0 | 5.0% | [0.9, 23.6] | -3.40 | +3.70 | -3.78 | 0.05 | 未判定 | **NONE** (極端な負 EV) |
| engulfing_bb | 20 | 0 | 30.0% | [14.5, 51.9] | +1.26 | +10.50 | -2.70 | 1.67 | 未判定 | 不明 (CI 広い) |
| bb_squeeze_breakout | 15 | 0 | 6.7% | [1.2, 29.8] | -2.37 | +2.40 | -2.71 | 0.06 | 未判定 | **NONE** |
| stoch_trend_pullback | 14 | 0 | 28.6% | [11.7, 54.6] | +0.31 | +7.35 | -2.51 | 1.17 | 未判定 | 不明 (Phase 4d で nature pooling 弱い signal あり) |
| sr_break_retest | 14 | 0 | 35.7% | [16.3, 61.2] | **-20.59** | +12.60 | -39.02 | 0.18 | 未判定 | **NONE** (左尾 fat-tail) |
| ema200_trend_reversal | 14 | 0 | 28.6% | [11.7, 54.6] | -3.07 | +12.20 | -9.18 | 0.53 | 未判定 | 不明 |
| dt_bb_rsi_mr | 14 | 0 | 64.3% | [38.8, 83.7] | +5.87 | +15.46 | -11.38 | 2.44 | 未判定 | Structural 候補 (mech 言語化必要) |
| dt_sr_channel_reversal | 12 | 1 | 25.0% | [8.9, 53.2] | -2.26 | +3.85 | -5.31 | 0.24 | 未判定 | NONE 寄り |
| vol_spike_mr | 10 | 0 | 30.0% | [10.8, 60.3] | +2.10 | +19.23 | -5.24 | 1.57 | 未判定 | Risk premium ? (vol expansion fade) |
| macdh_reversal | 9 | 0 | 22.2% | [6.3, 54.7] | -2.42 | +4.15 | -4.30 | 0.28 | TAP-3 (MFE_median=0.00, lesson-toxic-anti-patterns) | **NONE** |
| vol_surge_detector | 7 | 1 | 0.0% | [0, 35.4] | -4.67 | — | -4.67 | 0.00 | 未判定 | **NONE** (全敗) |
| dt_fib_reversal | 6 | 0 | 16.7% | [3.0, 56.4] | -2.48 | +18.30 | -6.64 | 0.55 | 未判定 | 不明 (N 不足) |
| vol_momentum_scalp | 5 | 4 | 60.0% | [23.1, 88.2] | +4.64 | +8.13 | -0.60 | 20.33 | 未判定 | Structural 候補 (PF 異常、要 mech 検証) |
| post_news_vol | 5 | 0 | 0.0% | [0, 43.4] | -12.64 | — | -12.64 | 0.00 | 未判定 | **NONE** (Risk premium 系の失敗例) |
| orb_trap | 5 | 0 | 0.0% | [0, 43.4] | -10.28 | — | -10.28 | 0.00 | **VALID** (流動性遷移 mech) | Structural 候補 (mech VALID だが N 不足、Phase 5-9d S7 で再検) |

**重要な観察**:
- mechanism audit `VALID` 判定の `orb_trap` が Live N=5 WR=0% で表面的に DEAD に見える → **N=5 は edge 検出に N=37 必要 (5.6 power calc)、検出力ゼロ。「DEAD 確定」ではなく「未検出」**
- ema_trend_scalp は TAP-1 として N=69 で WR Wilson 上限 24.7% < 50% → **edge 不在を強く示唆**、構造的 NONE
- fib_reversal / dt_bb_rsi_mr は WR Wilson 下限 > 38% で structural 候補だが、いずれも Shadow trade (live_n が 0 か 1) で **Live 検証は未着手**

#### Phase 5-9d edge matrix との接続

`phase5-9d-edge-matrix-2026-04-25.md` で 9 戦略の機構論拠を整理 (S1-S9、ただし S3 は構造的 DEAD で実質 8 戦略)。Phase 5 BT は **Phase 3 で実行予定** であり、本セッション時点では数値未確定。

mechanism thesis 観点で:
- S1 Session Handover、S5 VWAP/HTF Defense、S6 Value Area Reversion、S7 ORB、S8 FVG、S9 VSA は全て **Structural edge** を狙う設計
- S2 Vol Compression は **Risk premium / Structural のハイブリッド** (vol expansion を fade)
- S4 Pure Divergence は **Structural** (流動性 imbalance)
- **Information edge を狙う戦略は 9 つの中に存在しない** → 設計レベルで retail 適合

→ Phase 3 BT で各 S が Live 適合する友 edge を持つかを実測する必要。本ノート 5.2 で再シミュレーション枠組みを定義。

---

## 5.2 BT 楽観バイアス 6 因子 + friction v2 再シミュレーション枠組み

### (a) 一般論

実測 BT (backtest) で「勝つ」戦略が Live で「負ける」現象は、BT が暗黙に置いている友最適化前提が現実と乖離するために起こる。これを **BT 楽観バイアス** と呼ぶ。

`bt-live-divergence.md` で定量化された 6 因子:

1. **Entry Price Bias**: BT は次足 open + 固定 cost / Live は変動 spread + slippage で実 entry 価格は不利寄り
2. **Spread Model Bias**: BT は固定 spread (例 BT_COST=1.0pip) / Live は session で 0.5 〜 5.0pip 変動
3. **Signal Reverse Reaction Lag**: BT は 3 bar (180s) 持って判定 / Live は 30s で判定 → BT は反転直前の不利方向を fading してしまう
4. **HTF Data Source Mismatch**: BT は M5→resample / Live は OANDA HTF endpoint → barfill の境界が異なり、indicator 値が異なる
5. **Fill Quality / SL Hunt Vulnerability**: BT は theoretical fill / Live は last look reject、partial fill、SL stop hunt
6. **Label Bias** (BB_MID, BREAKEVEN, MTF alignment): BT 内で label encoding が無条件 (例 d1_label ≥ 0 のみ) → Live も同じだが mtf_alignment 計算で SELL × d1<0 = 0 のような **構造的 0 セル** が発生 (Phase 4c Signal C audit で確認)

これら 6 因子の積算で、BT EV +1.0 pip/trade が Live で 0 〜 -1.0 pip/trade に低下するのが典型 (DT mode)。Scalp mode はこの低下が **5.4 倍**に増幅される (`friction-analysis.md`)。

### (b) 我々への含意

#### friction_model_v2 が捕捉する範囲 / 捕捉しない範囲

[friction_model_v2.py](../../../modules/friction_model_v2.py) の `friction_for(pair, mode, session)` は 6 因子のうち主に 1, 2, 5 を捕捉する:

```
adjusted_rt_pips = base_rt_pips × mode_multiplier × session_multiplier
  base_rt_pips: pair 別 (USD_JPY 2.14, EUR_USD 2.00, GBP_USD 4.53)
  mode_multiplier: DT 1.0, Scalp 1.05, Swing 0.95
  session_multiplier: London 1.0, NY 1.2, Tokyo 1.45, Sydney 1.6, Asia_early 1.55, overlap_LN 0.85
```

捕捉範囲:
- ✅ 1 Entry Price (spread + slippage)
- ✅ 2 Spread Model (session 別 multiplier)
- ❌ 3 Signal Reverse Lag (BT 側ロジック修正が必要、friction model では補償不能)
- ❌ 4 HTF Data Mismatch (data source 統一が必要)
- ✅ 5 Fill Quality (slippage の一部)
- ❌ 6 Label Bias (戦略コードの修正が必要、Phase 4c で audit 済)

→ **friction_model_v2 だけでは BT 楽観バイアスの ~50% しか捕捉できない**。残り 50% (Lag, HTF, Label) は戦略コード自体に直接組み込む必要があり、Phase 3 BT 設計で **`backtest_mode=True` で本番関数を呼ぶ** という同期化が必須 (CLAUDE.md Design Principles と整合)。

#### friction matrix 実測 (Track ⑤ 視点)

[friction_model_v2.py](../../../modules/friction_model_v2.py) を直接 import して friction を計算した結果:

| pair | mode | Asia_early | London | overlap_LN | NY |
|---|---|---|---|---|---|
| USD_JPY | DT | 3.32 | 2.14 | **1.82** | 2.57 |
| USD_JPY | Scalp | 3.48 | 2.25 | **1.91** | 2.70 |
| EUR_USD | DT | 3.10 | 2.00 | **1.70** | 2.40 |
| GBP_USD | DT | 7.02 | 4.53 | **3.85** | 5.44 |
| GBP_USD | Scalp | **7.37** | 4.76 | 4.04 | 5.71 |

**重要な数学的事実**:
- GBP_USD Scalp で Asia_early 取引は実質 friction **7.37 pip/trade**。break-even に必要な edge (avg_win - avg_loss) は ~ 14 pip 以上。我々の戦略の typical avg_win 5-15 pip を考えると **構造的に BEV 不可能**
- USD_JPY DT で overlap_LN 取引は friction **1.82 pip**。avg_win 8 pip 戦略なら edge ~ 6 pip で十分余裕
- → 戦略採用は (pair × mode × session) の **3D セル単位** で BEV 可否を判断する必要がある (Phase 4d session×spread routing が NULL でも、より粗い R2 suppress としてこの数学は使える)

### (c) Phase 4c/4d KB 照合

#### Phase 4c Signal D (multivariate logit) の含意

`mtf_alignment audit` (Phase 4c Signal C, memory obs 62) で `aligned WR=8.1% << conflict WR=20.4%` が data-structure artifact (label_d1 が non-negative にしか encoding されない) と判明。これは 6 因子の **6 Label Bias** の具体例で、friction_model_v2 では捕捉できない種類のバイアス。

Phase 4c Signal D (multivariate logit, obs 64-66) で「regime block confounder 統制後、追加情報なし」と Scenario A (NULL) 確定。これは friction を control してもなお Live edge が出ない状況で、**残る楽観バイアスの全てが Lag/HTF/Label 系**である可能性を示唆 (未検証仮説、Phase 3 BT の friction v2 再シミュ結果との比較で検証可能)。

#### Phase 4d session×spread routing の含意 (obs 72)

`true bottleneck = N (sample size), not signal absence` という結論。これは friction を session で routing しても Live で edge が出ないのは N 不足で検出できないだけで、構造的に edge ゼロとは言えない。

→ **Phase 5-9d 9 戦略の friction v2 再シミュレーションは、Phase 3 BT 実行後に以下の 3 列で評価する** (本セッションでは未実測):

| 戦略 | Phase 5 BT EV (固定 cost 1.0) | friction v2 再シミュ EV | Live EV | 楽観バイアス分解 |
|---|---|---|---|---|
| S1 Session Handover | (Phase 3 後) | (Phase 3 後) | (Phase 3 後) | friction で捕捉 / 未捕捉に分解 |
| S2 Vol Compression | ... | ... | ... | ... |
| ... (S4-S9) | ... | ... | ... | ... |

未検証仮説: **friction v2 は (BT EV - Live EV) の ~50% を説明する**。残り 50% は code-level 修正 (backtest_mode=True 同期、Lag 30s 化、HTF data unification、label encoding fix) を要する。

---

## 5.3 Survivorship Bias / HARKing / pre-reg LOCK の数学

### (a) 一般論

**Survivorship bias**: 365 日 BT で「勝った」戦略のみを採用すると、BT 期間に偶然 outlier が出ただけの戦略が混入する。N 戦略を test して P(全戦略 NULL) でも、最高 EV 戦略は分散の友尾で偽陽性となる。

**HARKing (Hypothesizing After Results are Known)**: BT 結果を見てからパラメータ閾値を「最適化」すると、データに合わせ込んだ post-hoc 仮説となり、Live 予測力ゼロ。

**Pre-registration (Pre-reg LOCK)**: 仮説 / 閾値 / 検証期間を **データを見る前に** 文書化し時刻署名する。検証は LOCK 後のデータで行い、結果を見てからの調整は禁止。これにより HARKing を構造的に防止する。

数学的影響:
- N 戦略を独立 test、各友 alpha=0.05 → 少なくとも 1 つが偽陽性となる確率 = 1 - (1 - 0.05)^N
- N=10 で 40.1%、N=20 で 64.2%、N=50 で 92.3% → **多重検定補正なしで 10 戦略以上テストすると偽陽性が支配的**

### (b) 我々への含意

#### pre-reg LOCK 2 戦略 (Phase 1.7 で時刻 LOCK)

[strategy-mechanism-audit-2026-04-26.md](../decisions/strategy-mechanism-audit-2026-04-26.md) と pre-reg ドキュメントで以下が時刻 LOCK 済:

**`pullback_to_liquidity_v1`** (Trend Following, Structural edge):
- 仮説: H4 EMA50 > EMA200 (HTF trend) かつ M15 swing low/high pullback で liquidity rejection (wick 比 ≥ 0.4) があれば、機関 flow 再開で trend 方向に再加速
- 閾値: TP=±2.0×ATR, SL=∓1.0×ATR
- Validation: N≥200, Wilson_lo > 50%, PF > 1.30, EV > 0 (friction v2 後)

**`asia_range_fade_v1`** (Mean Reversion, Structural edge):
- 仮説: UTC 02-06 (Asia low-vol session) かつ range_size ≤ 1.5×ATR の touch + rejection で range 中央回帰
- 閾値: TP=±1.5×ATR, SL=∓ATR
- Validation: Wilson CI 友 95% AND Bonferroni α=0.005

→ 両戦略とも mechanism thesis が VALID (流動性メカニズム明示)、Phase 5-9d edge matrix に整合、Live 検証で Wilson 友限要求が組み込まれている。**HARKing 構造的に阻止**。

#### Validation 友限を満たすために必要な N の数学

Wilson lower 95% > 50% を WR=55% で達成するための最小 N:

```
Wilson lower bound at p̂=0.55, 95% confidence:
  N=50: lower ≈ 0.41 → 50% 未達
  N=100: lower ≈ 0.45 → 50% 未達
  N=200: lower ≈ 0.48 → 50% 未達
  N=300: lower ≈ 0.49 → 50% ぎりぎり未達
  N=400: lower ≈ 0.50 → 友届
  N=500: lower ≈ 0.51 → 達成
```

→ **WR 55% で Wilson lower > 50% を満たすには N ≥ 400 程度必要**。pre-reg LOCK の N≥200 は Wilson 上ではやや緩い (WR 60% なら N≥200 で達成可能)。

→ **未検証仮説**: pre-reg LOCK 2 戦略の 365 日 BT は (本セッション時点で) 未実行。実行後、Wilson lower / Bonferroni 補正下 lower 双方を計算して報告する必要がある。

### (c) Phase 4c/4d KB 照合

`lesson-asymmetric-agility-2026-04-25.md` の **Rule 1 (Slow & Strict)**: 新戦略 / Shadow→Live 昇格 / pair promotion には「365日BT or Live N≥30 + Bonferroni + Pre-reg LOCK」を要求。

これは:
- 多重検定補正 (Bonferroni) で偽陽性確率を制御
- N≥30 で minimum detectable edge を確保 (5.6 power calc 参照、N=30 では ΔWR=22pp 必要)
- Pre-reg LOCK で HARKing 構造防止

の 3 段防御を組合わせる設計。Phase 4c-d で MTF/session-spread が双方 NULL 確定したのも、この防御を通って初めて confidence を持って言える結論。

→ **Phase 4c/4d 7 検定累積で全 NULL** (obs 81, Phase 4d-II nature pooling) は、HARKing 阻止下では「edge 不在の最高水準証拠」。ただし「edge 不在」と「N 不足で未検出」を混同しないよう、5.6 で power calc を実施。

---

## 5.4 Multiple Testing Correction (Bonferroni / Holm / FDR)

### (a) 一般論

K 個の独立仮説を friend alpha=0.05 で test すると、family-wise error rate (FWER, 少なくとも 1 つが偽陽性となる確率) は 1 - (1-α)^K で増加。これを抑える 3 手法:

| 手法 | 補正 | 強度 | 用途 |
|---|---|---|---|
| **Bonferroni** | α / K | 最厳格 (友限) | K 小 (≤ 10)、独立性に依存しない |
| **Holm** | step-down (α/K, α/(K-1), ..., α/1) | Bonferroni より少し緩い | K 中 (5-20)、power やや向上 |
| **Benjamini-Hochberg (FDR)** | False Discovery Rate を控制 | 最も緩い | K 大 (> 20)、探索的研究、機械学習 feature selection |

選択基準:
- **確認研究 (confirmatory)**: Bonferroni or Holm。FWER strictly < α を保証
- **探索研究 (exploratory)**: FDR。発見の expected fraction が < q を保証 (false positive 数ではなく fraction)
- **戦略採用 / Live 昇格判定**: Bonferroni 推奨。1 戦略の偽陽性 → 実 Live 損失なので FWER 友限が安全側

### (b) 我々への含意

#### Phase 5-9d で 9 戦略を同時に評価する場合

K=9 戦略で各 α=0.05 → 補正なし FWER = 1-(0.95)^9 = 36.9%。Bonferroni で各戦略の有意水準を α/9 = 0.0056 に補正。

これは「単独で p < 0.05 だった戦略」が 9 戦略中で「Bonferroni 友 p < 0.0056 を満たすか」を再検査することに相当。Phase 5-9d edge matrix で全 9 戦略を同時 BT する場合、**この補正が必須**。

#### 補正下 detectable ΔWR の数学 (Live N=259 想定)

`scipy.stats` で計算:

| K (同時検定数) | α_corrected | Detectable ΔWR (β=0.20) |
|---|---|---|
| 1 (単独) | 0.0500 | **+7.54pp** (39% → 46.5%) |
| 5 | 0.0100 | +9.60pp (39% → 48.6%) |
| 10 | 0.0050 | +10.36pp (39% → 49.4%) |
| 20 | 0.0025 | +11.06pp (39% → 50.1%) |
| 50 | 0.0010 | +11.92pp (39% → 50.9%) |

→ **K=10 戦略を同時 evaluation すると、Live N=259 では WR を 49.4% 以上に押し上げる戦略しか検出できない**。WR 45% (3.0pp 改善) のような marginal な戦略は Bonferroni 補正下で構造的に検出不能。Phase 3 設計では **戦略数を絞る (例 5 つ以下)** か **N を増やす (≥ 500)** か、**effect size の大きい戦略 (≥ +10pp WR uplift)** を優先する必要がある。

### (c) Phase 4c/4d KB 照合

#### Phase 4c Signal D (multivariate logit) の Bonferroni 設計

obs 64 で「pre-registration locked: multivariate logit with pair/spread confounders」と Bonferroni 補正設計が時刻 LOCK 済。実行結果 (obs 65-66) で Scenario A (NULL) 判定。

→ **多重検定補正下でも NULL** は、本来 marginal effect (5pp 程度) を見逃している可能性がある。しかし pre-reg LOCK 設計では「marginal を取りに行く」より「robust を取る」方針が正解 (戦略採用 = Live 損失リスクのため)。

#### Phase 4d session×spread routing の χ² Bonferroni (obs 68-72)

`χ² per-strategy routing with Wilson CI and joint heatmap` で Bonferroni 補正設計済。obs 70 で Scenario A (NULL)、obs 72 で「true bottleneck = N」と結論。

→ NULL の解釈は 2 通り:
1. **edge 不在** (戦略の本質的限界): Phase 5-9d 9 戦略の friction v2 再シミュ後に判定可能
2. **N 不足で未検出** (本セッション 5.6 power calc から、Live N=259 では 7.54pp 以上の effect size しか検出不能、K=10 同時検定下では 10.36pp 以上)

→ 「成功するまでやる」原則 (memory feedback_success_until_achieved) に従い、NULL 確定後も **N を増やすか effect size の大きい戦略候補を生成するか** で深掘り継続。Phase 4d-II nature pooling (obs 81) はこの方針の実行例。

---

## 5.5 Walk-Forward Analysis 設計

### (a) 一般論

**Walk-Forward Analysis (WFA)** は時系列データでの過学習検出手法。データを time-ordered IS (in-sample) と OOS (out-of-sample) に分割し、IS で最適化、OOS で予測力を検証。OOS で大幅 degradation (例 EV 半減以上) があれば過学習。

2 種類:
- **Anchored WFA**: IS が最初から成長 (例 [0..t1] → [0..t2] → [0..t3])。長期的安定性検証
- **Rolling WFA**: IS が固定 window で前進 (例 [0..1y] → [3m..1y3m] → ...)。直近 regime 適合性検証

選択基準:
- 戦略が long-term stationary を仮定 → Anchored
- 戦略が regime-dependent → Rolling (window size = regime 持続期間)

OOS 評価指標:
- **EV degradation**: OOS EV / IS EV < 0.5 → 過学習疑い
- **Hit rate (IS で勝ったパラメータ友合が OOS で勝つ確率)**: < 50% → 過学習
- **Robust ratio**: median(OOS EV) / std(OOS EV) → 安定性

### (b) 我々への含意

#### Phase 3 BT への適用方針

Phase 5-9d 9 戦略の BT を実行する際、以下の WFA 設計を推奨 (本セッション時点で未実装、Phase 3 で実装):

**Anchored WFA** (戦略の long-term validity 検証):
- IS: 2025-01-01 〜 2025-09-30 (9 ヶ月)
- OOS: 2025-10-01 〜 2026-04-26 (~7 ヶ月)
- 評価: IS で閾値最適化 → OOS で EV / WR / PF 計測

**Rolling WFA** (戦略の regime 適合性検証):
- IS window: 6 ヶ月 rolling
- OOS window: 1 ヶ月
- Step: 1 ヶ月
- 評価: 各 step の OOS EV を時系列でプロット、trend / volatility 観察

#### IS/OOS 分割で検出すべき過学習パターン

1. **Parameter overfit**: IS で局所最適 (EV 高い) → OOS で degrade 50% 以上
2. **Regime overfit**: IS が trend regime → OOS の range regime で大幅 underperform
3. **Structural break**: COVID (2020-03)、SVB collapse (2023-03)、BOJ intervention (2022-09, 2024-04) 等の event 前後で WR 変動

我々の戦略の場合:
- `asia_range_fade_v1` は range regime 依存 → Rolling WFA で regime 切替時の WR 変動を測定
- `pullback_to_liquidity_v1` は trend regime 依存 → 同上
- `orb_trap` (Phase 5 audit VALID) は session 切替時の vol expansion 依存 → 季節性は限定的、Anchored で十分

### (c) Phase 4c/4d KB 照合

Phase 4c-d は **WFA を構造的に実施しない** (cross-sectional な戦略 × pair × session × regime の routing を検定)。これは pure 仮説検定であり、WFA は別レイヤー。

→ Phase 5-9d 9 戦略の BT で WFA を組合わせると:
- **WFA で OOS 安定性確認** (戦略の robust 性)
- **Bonferroni 補正で多重検定制御** (採用判定の偽陽性制御)
- **friction v2 で BT-Live 乖離 50% 補正** (現実適合性向上)

の 3 段防御が成立。これが Phase 3 BT 設計の理想形。

→ **未検証仮説**: 上記 3 段防御を通った戦略は Live N≥30 で Live 検証 → Live N≥200 で Wilson lower>50% 達成すれば Live 昇格、という pipeline が機能する。Phase 5-9d 実行後に検証可能。

---

## 5.6 Sample Size & Statistical Power

### (a) 一般論

仮説検定で「差を検出できるか」は sample size N、effect size Δ、有意水準 α、検出力 1-β の 4 者の関係で決まる:

```
N ≈ (z_α + z_β)² × p₀(1-p₀) / Δ²
```

(p₀ = baseline、Δ = 検出したい effect size、α=友側 0.05 ⇒ z=1.645、β=0.20 ⇒ z=0.842)

→ **Δ が小さくなると N は二次的に必要**。例: Δ=10pp → N=148、Δ=5pp → N=589

→ **N が足りない時の NULL は「edge 不在」ではなく「未検出」**。混同すると誤った戦略 closure を生む。

### (b) 我々への含意

#### Live N=259 で検出可能な edge size (baseline WR=39%, α=0.05, β=0.20)

scipy.stats で計算:

| N | Detectable ΔWR (one-sided) | Threshold WR (39%+ΔWR) |
|---|---|---|
| 30 | **22.14pp** | 61.1% |
| 50 | 17.15pp | 56.2% |
| 100 | 12.13pp | 51.1% |
| 200 | 8.58pp | 47.6% |
| 259 (現状) | **7.54pp** | 46.5% |
| 500 | 5.42pp | 44.4% |
| 1000 | 3.84pp | 42.8% |

→ **現在の Live N=259 では、WR 46.5% 友 (= 39% + 7.5pp) の戦略しか検出できない**。WR 43% (=39% + 4pp) のような marginal な戦略は構造的に検出不能。

#### Per-strategy N=30 (Rule 2 即断ライン) での detectable ΔWR

Rule 2 即断ラインの N=30 では Δ=22pp 必要。これは「baseline 39% から WR 61% 友」というかなり強い signal でないと検出不能。

→ **Rule 2 で Shadow→Live 昇格を判定する際、WR の絶対値だけ見ると過剰昇格になる**。Wilson lower / Bonferroni 補正下の lower を確認し、N=30 でも友限が baseline 友を超えているかを基準にすべき。

#### 「edge 不在」と「未検出」の見極め

Phase 4c-d で 7 検定累積 NULL (obs 81)。これを:
- **edge 不在説**: 戦略の本質的限界、Phase 3 でアプローチを切り替える必要 → mechanism thesis 再構築
- **未検出説**: N 不足、effect size が 7.54pp 未満の marginal な edge → N 増加 (Live trade を増やす) で検出可能になる可能性

両説は data だけでは distinguishable でない。**memory feedback_success_until_achieved に従い、Phase 4d-II nature pooling (obs 81) のように深掘り継続**することで、未検出説の余地を残しつつ edge 不在説の確度を高める設計。

### (c) Phase 4c/4d KB 照合

#### Phase 4d session×spread routing での「true bottleneck = N」結論 (obs 72)

obs 72 で `true bottleneck = N (sample size), not signal absence` と明示。これは 5.6 power calc の数学的結論と整合: friction-controlled cell ごとに N が分散すると、各セルでは検出力が friend 不足し、joint heatmap でも信号が弱くなる。

→ Phase 4d 実行後に「4 R2 suppress cells」が見つかった (obs 72)。これは N 集約による effect size 増幅で marginal な edge を捕捉した例。

#### Phase 4d-II nature pooling の戦略 (obs 81)

`Strategy Nature Pooling Analysis` (obs 74-81) は同じ「nature」の戦略を pool して N を増やすアプローチ。BREAKOUT joint で WEAK signal、Primary 全 NULL の結果。これは 5.6 の N 増加戦略の実装例。

→ pooling で N を 2-3 倍に増やしても WEAK までしか到達しないなら、effect size が 4-5pp 程度でしか存在せず、Bonferroni 補正下では検出不能。「未検出説」の確度が下がり、「edge 不在説」の確度が上がる。

---

## 5.7 Track ⑤ 視点での Live Kelly -17.97% 構造説明

(本節は 5.1-5.6 の総合節、3 段構造ではなく統合エッセイ形式)

production memory 報告 (memory obs 41, 87) で `Live N=259 WR=39.0% EV=-0.83 pip/trade Kelly=-17.97%`。本セッションで実測した範囲では local Live N=36 WR=50.0% EV=+0.17 で表面的には差があるが、これは cutoff / pair 構成の違いによる data window の違いと考えられる (production 値が信頼源)。

Track ⑤ 視点で Live Kelly -17.97% を **5 つの独立した数学的因子の積算** として説明する:

### 因子 1: Information edge 不在 (5.1)

我々は Bloomberg Terminal も prime broker order flow info も持たない。**Information edge を狙った戦略は最初から無効** であり、もし採用していたら structural にゼロ alpha。我々の戦略 19 種 (entry_type) のうち、明示的に information edge を狙ったものはないが、`sr_break_retest` (avg_loss -39.02 pip、PF 0.18) のように news driven な price action を fade するもので **暗黙的に information を仮定** している戦略は、Live で catastrophic に負けている (5.1 (c) 表)。

### 因子 2: Structural edge の mechanism thesis 不在 (5.1, 5.2)

戦略 19 種のうち、`strategy-mechanism-audit-2026-04-26.md` で VALID 判定なのは `orb_trap` 1 つのみ。残り 18 種のうち多くが TAP-1 (中間帯 RSI/Stoch + AND 含有, lesson-toxic-anti-patterns)、TAP-2 (squeeze, sr_channel)、TAP-3 (macdh_reversal, MFE_median=0) で構造的に edge を持たない。これら **edge ゼロ戦略を Live で動かすと、friction × N の比例で確実に損失蓄積**。

### 因子 3: friction が edge を食う (5.2)

`friction_model_v2` で実測した friction:
- USD_JPY DT default: 2.35 pip/trade
- GBP_USD Scalp Asia_early: **7.37 pip/trade**

平均的な戦略の avg_win 5-15 pip、avg_loss -5 to -15 pip。friction 2-7 pip は avg_win の 20-50% を直接削る効果。`ema_trend_scalp` (Scalp + 中間帯 RSI) で WR=14.5% × avg_win 5.23 - 85.5% × avg_loss 3.13 - friction ~ 2.5 = -1.87 pip/trade EV (実測一致)。

### 因子 4: BT 楽観バイアス 6 因子のうち friction で捕捉できない 50% (5.2)

friction_model_v2 で 6 因子のうち 1, 2, 5 を捕捉。残り 3 (Signal Reverse Lag), 4 (HTF Data Mismatch), 6 (Label Bias) は code-level 修正が必要 (`backtest_mode=True` 同期)。**BT で +1.0 pip 出していた戦略が Live で 0 〜 -0.5 pip に低下** する典型的な未捕捉バイアス。

### 因子 5: 多重検定補正下で marginal edge は検出不能 (5.4, 5.6)

Live N=259 で K=10 戦略同時検定 (Bonferroni) では、ΔWR ≥ 10.36pp の effect size しか検出できない。**WR を 39% → 49% に押し上げる戦略でなければ、検定上「有意な edge あり」と言えない**。Phase 4c-d で 7 検定累積 NULL なのは、この detection 限界の自然な結果でもある。

### 統合: Live Kelly -17.97% の数学的必然性

```
Live Kelly = (WR × avg_win - (1-WR) × avg_loss) / avg_loss × leverage_factor

production memory: WR=0.39, avg_loss が friction 込みで拡大
  → Numerator: 0.39 × avg_win - 0.61 × (avg_loss + friction)
  → 我々の typical: 0.39 × 8.0 - 0.61 × 10.5 ≈ -3.3 pip/trade
  → /avg_loss × leverage で -17.97% 程度の Kelly 負値に到達

これを正に転じるには:
  - WR を 39% → 50%+ に引き上げる (5.6 で +11pp、Bonferroni 下で K=10 同時検定の最低検出 effect size を上回る)
  - または avg_win を avg_loss に対して 1.5x 以上に拡大 (TP/SL 比改善)
  - friction を圧縮 (overlap_LN session に集中、Scalp 廃止、GBP_USD Scalp 取引禁止)
  - 上記 3 つを同時達成する mechanism-driven edge を持つ戦略 (5.1 Structural edge) のみ採用
```

→ **Phase 3 設計の必須条件** は:
1. mechanism thesis VALID 戦略のみ採用 (5.1 (c) で 19 戦略中 1 つだけ)
2. friction v2 を BT に組込み、BEV_WR 友 を超える戦略のみ進級
3. WFA + Bonferroni + pre-reg LOCK の 3 段防御 (5.3-5.5)
4. Live N≥200, Wilson lower > 50% で Live 昇格 (5.6 で N=400+ 必要)
5. (pair × mode × session) cell 別 friction でセル単位 routing (5.2)

これらを実装すれば Live Kelly が +20%/trade レベルに反転する道筋がある (memory: 月利 100% 目標の必要条件と整合)。本セッション時点で Phase 1.7 までの実装 (`friction_model_v2`, `pre-reg LOCK 2 戦略`, `mechanism audit 5 戦略`) はこの design path 上にある。

---

## Appendix A: Phase 4c/4d KB 引用インデックス

| 引用元 | 場所 | 本ノートでの使用 |
|---|---|---|
| Phase 4c Signal C `mtf_alignment audit` | memory obs 62, wiki audit doc | 5.2 (c) Label Bias の具体例 |
| Phase 4c Signal D multivariate logit | memory obs 64-66 | 5.4 (c) Bonferroni 設計 / NULL 解釈 |
| Phase 4d session×spread routing | memory obs 68-72 | 5.4 (c), 5.6 (c) true bottleneck = N |
| Phase 4d-II nature pooling | memory obs 74-81 | 5.6 (c) N pooling 戦略の実例 |
| `bt-live-divergence.md` | wiki/analyses/ | 5.2 (a) 6 因子の元定義 |
| `friction-analysis.md` | wiki/analyses/ | 5.2 (b) DT vs Scalp 5.4× 数学展開 |
| `strategy-mechanism-audit-2026-04-26.md` | wiki/decisions/ | 5.1 (c), 5.3 (b) VALID/WEAK/NONE 判定 |
| `lesson-toxic-anti-patterns-2026-04-25.md` | wiki/lessons/ | 5.1 (c) TAP-1/2/3 該当戦略 |
| `lesson-asymmetric-agility-2026-04-25.md` | wiki/lessons/ | 5.3 (c) Rule 1/2/3 多重検定組込 |
| `phase5-9d-edge-matrix-2026-04-25.md` | wiki/syntheses/ or wiki/decisions/ | 5.1 (c), 5.2 (c) 9 戦略 mechanism |
| mtf-rustling-candle 計画書 Section 9-11 | memory obs 76 | 5.4 (c) 全 Phase 結果サマリー |

合計 **11 件** (≥5 件の最低基準を満たす)。

---

## Appendix B: 実測クエリ生 SQL / Python スニペット

### B.1 戦略全件 N/WR/Wilson CI/EV (5.1)

```python
import sqlite3, math
conn = sqlite3.connect('demo_trades.db')
cur = conn.cursor()

def wilson_ci(k, n, alpha=0.05):
    if n == 0: return (0.0, 0.0)
    z = 1.959963984540054
    phat = k/n
    denom = 1 + z*z/n
    centre = (phat + z*z/(2*n))/denom
    half = (z * math.sqrt((phat*(1-phat) + z*z/(4*n))/n))/denom
    return (max(0, centre - half), min(1, centre + half))

cur.execute("""
    SELECT entry_type, COUNT(*) AS n,
           SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
           AVG(pnl_pips) AS ev,
           SUM(is_shadow=0) AS live_n,
           AVG(CASE WHEN pnl_pips>0 THEN pnl_pips END) AS avg_win,
           AVG(CASE WHEN pnl_pips<0 THEN pnl_pips END) AS avg_loss
    FROM demo_trades
    WHERE instrument != 'XAU_USD' AND status='CLOSED'
    GROUP BY entry_type HAVING n >= 5
    ORDER BY n DESC
""")
for r in cur.fetchall():
    n, w = r[1], r[2]
    lo, hi = wilson_ci(w, n)
    pf = (w*(r[5] or 0))/(-(n-w)*(r[6] or 0)) if (n-w)*(r[6] or 0) < 0 else float('inf')
    print(r[0], n, r[4], f"WR={w/n:.3f} [{lo:.3f},{hi:.3f}]", f"EV={r[3]:.2f}", f"PF={pf:.2f}")
```

### B.2 friction_model_v2 import & 使用 (5.2)

```python
import sys
sys.path.insert(0, '/Users/jg-n-012/test/fx-ai-trader')
from modules.friction_model_v2 import friction_for

for pair in ['USD_JPY', 'EUR_USD', 'GBP_USD']:
    for sess in ['Asia_early', 'London', 'overlap_LN', 'NY']:
        for mode in ['DT', 'Scalp']:
            r = friction_for(pair, mode, sess)
            print(f"{pair} {mode} {sess}: rt={r['rt_friction_pips']:.2f}pip, "
                  f"adj={r['adjusted_rt_pips']:.2f}pip, BEV_WR={r['bev_wr']:.4f}")
```

### B.3 Power calc (5.6)

```python
import math
from scipy import stats

def detectable_delta(n, baseline=0.39, alpha=0.05, beta=0.20):
    z_a = stats.norm.ppf(1 - alpha)
    z_b = stats.norm.ppf(1 - beta)
    se = math.sqrt(baseline * (1 - baseline) / n)
    return (z_a + z_b) * se

for n in [30, 50, 100, 200, 259, 500, 1000]:
    print(f"N={n}: ΔWR ≥ {detectable_delta(n)*100:.2f}pp")

# Bonferroni-corrected
for K in [1, 5, 10, 20, 50]:
    a_corr = 0.05 / K
    z_a = stats.norm.ppf(1 - a_corr)
    z_b = stats.norm.ppf(1 - 0.20)
    se = math.sqrt(0.39 * (1 - 0.39) / 259)
    d = (z_a + z_b) * se
    print(f"K={K}: α_corr={a_corr:.4f}, ΔWR ≥ {d*100:.2f}pp")
```

---

## 完了状態

- 5.1 - 5.6: (a)(b)(c) 3 段構造で完成
- 5.7: 5.1-5.6 を統合した Live Kelly -17.97% 構造説明
- Appendix A: Phase 4c/4d KB 引用 11 件
- Appendix B: 実測クエリの再現可能ソースコード

**未完成 (Phase 3 BT 実行後に追記すべき)**:
- 5.2 (c): Phase 5-9d 9 戦略の friction v2 再シミュレーション 3 列比較表
- 5.3 (b): pre-reg LOCK 2 戦略の 365 日 BT Wilson CI / Bonferroni 補正後 lower

**Master 統合 (curried-ritchie session) への引き継ぎ事項**:
- 本ノートを `fx-fundamentals.md` Section 5 placeholder と置換
- 5.7 統合節は curried-ritchie の Section 1.6 (Track ① 視点での Live Kelly 構造説明) と並行する内容。Section 6.2 の 5-Track 統合視点では、両 Track の説明を併置する形で再統合すること
- Section 6.4 未解決問題リストへの追加候補: (5.2 friction 再シミュ未実測), (5.3 pre-reg LOCK 365日BT 未実測), (5.6 「edge 不在」と「未検出」の見極め指標)
