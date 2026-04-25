# Lesson: 17 戦略の解剖から抽出した「Toxic Anti-Pattern (猛毒の法則)」 (2026-04-25)

## 0. 目的と禁則

`_FORCE_DEMOTED` 17 戦略を**救済しない**前提で、ソースコードと負けデータを横断
解析し、新戦略設計で**絶対に避けるべきロジック構造**を言語化する.

**改善案・V2 ロジック・救済仮説は本ファイルでは提示禁止**. 純粋な失敗の構造分析.

## 1. 解析対象 (DEAD/REJECT 7 戦略のソース確認済)

| 戦略 | ファイル | Live N | Live EV | med MFE |
|---|---|---|---|---|
| ema_trend_scalp | strategies/scalp/ema_trend_scalp.py | 680 | -1.47 | 1.25 |
| fib_reversal | strategies/scalp/fib.py | 269 | -0.59 | 0.60 |
| sr_channel_reversal | strategies/scalp/sr_channel_reversal.py | 228 | -0.90 | 0.90 |
| stoch_trend_pullback | strategies/scalp/stoch_pullback.py | 204 | -0.96 | 1.00 |
| engulfing_bb | strategies/scalp/engulfing_bb.py | 177 | -0.49 | 1.80 |
| macdh_reversal | strategies/scalp/macdh.py | 134 | -1.13 | **0.00** |
| ema_pullback | strategies/scalp/ema_pullback.py | 45 | +0.01 | - |

(参考: 残り 10 戦略 atr_regime_break, dt_bb_rsi_mr, ema_cross, ema_ribbon_ride,
inducement_ob, intraday_seasonality, lin_reg_channel, orb_trap, sr_break_retest,
sr_fib_confluence は数値だけ参照; ソースコード共通項抽出には十分)

---

## 2. Toxic Anti-Pattern 一覧 (TAP)

### 🔴 TAP-1: 「中間帯オシレーター AND フィルター」(構造的にエッジゼロ領域)

**該当**: ema_trend_scalp, stoch_trend_pullback, ema_pullback, sr_channel_reversal

```python
# ema_trend_scalp.py
BBPB_BUY_MIN = 0.25; BBPB_BUY_MAX = 0.75   # ← BB 中間帯
RSI_BUY_MIN = 30;    RSI_BUY_MAX = 65      # ← RSI 中間帯

# stoch_pullback.py
prev_stoch_buy = 48   # 中間直下
stoch_max_buy = 70    # 中間直上 → 上限 70 まで許容
```

**失敗の構造**:
- BB%B 0.25-0.75 = 全 5m bar の **〜70% 以上** が該当 (Bollinger 1992 設計上 68% 帯).
- RSI 30-65 / Stoch 48-70 も同様の中間帯.
- → これらの AND 結合は `(0.7) × (0.7) × (0.7) ≈ 0.34` でフィルタ通過率 34%
- 大量 N (680, 228, 204) を生成するが、**通過したシグナルは平均的相場の random sample** にすぎない.
- BB extreme (<0.10 or >0.90) は bb_rsi / vwap_mr 等の MR 系が陣取り、**中間帯は構造的にエッジが立たない領域**.

**証拠**: ema_trend_scalp は N=680 だが 27 cell 全てで EV<0. 救済 cell **0 個**.

---

### 🔴 TAP-2: 「N-bar pattern matching」(lookback overfit)

**該当**: macdh_reversal (致命傷), engulfing_bb, sr_channel_reversal

```python
# macdh.py
if (ctx.macdh > ctx.macdh_prev          # bar t > bar t-1
    and ctx.macdh_prev <= ctx.macdh_prev2):  # bar t-1 ≤ bar t-2
    # 3 bar 連続反転パターン

# engulfing_bb.py
_is_bullish = (ctx.prev_close < ctx.prev_open
               and ctx.entry > ctx.open_price
               and _curr_body > _prev_body * self.body_mult)
# 2 bar の「包み足」パターン
```

**失敗の構造**:
- 3 bar 連続パターン (`macdh_prev ≤ macdh_prev2 < macdh`) はランダムウォーク下で偶発的に大量発生する事象 (確率 1/8).
- 「包み足」も 2 bar level でランダムウォーク確率 ~1/4.
- これらを「反転シグナル」と命名すると = **アポフェニア (パターン認識バイアス)**.
- MACD-H 自体が EMA 差分の差分 (3 階微分) で **本質的にラグ** + ノイズ増幅.
- → macdh_reversal の **med MFE = 0.00p** は決定的証拠. 半数のトレードがエントリー直後に逆行 = predictive power がリアルタイムでゼロ.

**証拠**: macdh_reversal Live N=134, EV=-1.13, **MFE 中央値 0.00 pip** (= 平均ではなく中央値が 0).

---

### 🔴 TAP-3: 「直前 candle 方向単独確認」(random walk と等価)

**該当**: ema_trend_scalp, sr_channel_reversal, engulfing_bb, stoch_trend_pullback (全 7 戦略中 6戦略で使用)

```python
# ema_trend_scalp.py
if ctx.entry <= ctx.open_price:    # BUY なのに陰線 → 棄却
    return None
# = "BUY エントリーには陽線確認"

# sr_channel_reversal.py
if ctx.entry > ctx.open_price:
    score += 0.3   # ボーナス加点
```

**失敗の構造**:
- 5m bar level で「Close > Open (陽線)」確率 ≈ 50% (ランダムウォーク).
- これを「反転確認」「バウンス確認」と称してフィルタすると、**シグナル数を半減 (50%) させて偽陽性率を変えない**.
- 実際は陽線/陰線は次の 5m での価格方向と無相関 (mean-reversion 強い相場では負相関).
- → フィルタとしての価値ゼロ、ノイズを増幅して N を稼ぐだけ.

---

### 🔴 TAP-4: 「TP=ATR×1.5-1.8, SL=ATR×0.5-1.0」(摩擦死構造)

**該当**: ema_trend_scalp, macdh_reversal, sr_channel_reversal, engulfing_bb, stoch_pullback

```python
# ema_trend_scalp.py
SL_ATR_MULT = 1.0
TP_ATR_MULT = 1.8

# macdh.py
tp_mult = 1.5
sl_mult = 1.0

# sr_channel_reversal.py
tp_mult = 1.5
sl_mult = 0.5    # ← 異常に浅い SL
```

**失敗の構造 (ema_trend_scalp が N=680 で MFE が出ない理由)**:

USD/JPY 5m の典型値:
- ATR7 ≈ 3-5pip
- Spread (Round-Trip) ≈ 1.6-2.1pip (USD/JPY 摩擦テーブル)
- 設定 TP = ATR×1.8 ≈ **5.4-9pip**
- 設定 SL = ATR×1.0 ≈ **3-5pip**

**摩擦比率**:
- TP 到達時 net pnl ≈ 5.4 - 1.6 = **3.8pip (TPの 70%)**
- SL 到達時 net loss ≈ -3.0 - 1.6 = **-4.6pip (SLの 153%)**
- 実 W:L 比 = 3.8 / 4.6 = **0.83** (名目 RR 1.8 → 実 RR 0.83)
- → BE WR 必要値 = 1 / (1 + 0.83) = **54.6%**

中間帯フィルター通過後の random sample は WR ≈ **20-25%** (BB extreme でない領域は MR 効果薄い)
→ **20% << 54.6%** で構造的 EV 負確定.

加えて **med MFE 1.25p** (TP 到達なしで TIME_DECAY_EXIT or SL_HIT が大半):
- 5m level の小幅変動 (±1-2p) で揺らぐ間にスプレッドコストが累積
- "TP まで届かないで撤退する" = 摩擦死の典型像

**証拠**: ema_trend_scalp N=680 で **med MFE 1.25p** << TP 距離 5-9p. TP 到達率は推定 5-10%.

---

### 🔴 TAP-5: 「Score ボーナス線形加算による confidence 膨張」

**該当**: 全 7 戦略

```python
# ema_trend_scalp.py
score = 3.0
if ctx.adx >= 30:           score += 0.5   # ボーナス1
if EMA perfect order:       score += 0.5   # ボーナス2
if ctx.macdh > 0:           score += 0.4   # ボーナス3
if ctx.macdh > ctx.macdh_prev: score += 0.3   # ボーナス4
if +DI > -DI:               score += 0.3   # ボーナス5
conf = int(min(85, 50 + score * 4))   # → score 5.0 で conf 70 に膨張
```

**失敗の構造**:
- ボーナス条件は **互いに強相関** (ADX強 と DI方向一致 と EMA順列 は同じ trend を別角度で測定):
  - ADX≥30 ⊂ EMA perfect order ⊂ DI direction agree
  - → 独立変数として 3 票加算するが、実質は 1 票分の情報
- MACD-H 正/負 と MACD-H 反転は MACD-H 値の関数同士で**完全相関**
- → score 膨張で confidence が 50→85 に届くが、**predictive power はほぼ +0**
- Confidence v2 の Q4 penalty (`apply_penalty`) は確かに ADX>31 で減点するが、**根本の冗長加算は残る**

**証拠**: confidence v2 Q4 gate (ELITE 免除前) が機能していたが、それでも Live で全 EV<0.
= confidence 膨張が predictive を真に持っていたら Q4 gate 通過後の高 conf 群が EV+ になるはず → ならない.

---

### 🔴 TAP-6: 「学術引用による authority bias」

**該当**: ema_trend_scalp ("Moskowitz 2012", "Murphy 1999", "Edwards & Magee 1948"),
bb_squeeze_breakout ("Bollinger 1992 JoF"), macdh ("BB extreme = 高確率反転"),
sr_channel_reversal ("Osler 2000"), squeeze.py ("BLL 1992 JoF")

**失敗の構造**:
- ソースコードコメントに**学術論文を引用**しているが、引用論文の前提条件 (時間軸/資産/サンプル) と実装が大きく乖離:
  - Moskowitz 2012 の momentum は **月次・資産横断** (FX 5m とは無関係)
  - Murphy 1999 の EMA dynamic S/R は **日足以上の chart pattern** (5m EMA21 は別物)
  - Bollinger 1992 の squeeze は **日足統計** (5m squeeze は単なる低ボラ局面)
- 引用は「設計者が読んだ論文」のリストであって、戦略自体の有効性証明ではない.
- → コメントに学術引用があると、**未検証のまま「これは堅実な戦略」と錯覚**してしまう確認バイアス装置.
- 実際の検証 (本 R&D 解剖) では全 NO.

---

## 3. ema_trend_scalp が N=680 でも勝てない構造的理由 (詳細)

複数の TAP を**重畳した最悪のケース**:

1. **TAP-1 (中間帯フィルター)** — BBPB 0.25-0.75 + RSI 30-65 でフィルター通過率 ~50% → N=680 を稼ぐ
2. **TAP-3 (反転 candle)** — 陽線確認で 50% カット → 通過後の N は無作為サンプリングと変わらない
3. **TAP-4 (摩擦死)** — TP=ATR×1.8, SL=ATR×1.0, USD/JPY 摩擦 1.6p で実 RR=0.83
4. **TAP-5 (score 膨張)** — 6 ボーナス加算で confidence 70-85 だが predictive ~0
5. **プルバック zone 過大** — `EMA21 ± ATR×1.0` ≈ トレンド中の 60-70% bar が該当 = フィルタ価値ゼロ

→ 結果: N 大量 (680) だが各 trade は **random + ε** で WR 17.8%, EV-1.47. 摩擦累積で月間 -1,000pip 級の損失機械. **N が増えるほど損が増える** = 悪夢の戦略.

---

## 4. 新戦略開発チェックリスト (5 項目, 1 つでも該当 = 即破棄)

新戦略の `evaluate()` を実装する前に、以下のいずれかに該当しないか確認:

### ✅ Check 1: 「中間帯フィルター」を含むか
- BB%B が 0.20-0.80 の範囲を許容するか
- RSI/Stoch が 30-70 の中間帯を許容するか
- → **YES なら破棄**: 中間帯はエッジゼロ領域. 既存戦略が陣取っている extreme 帯のみ狙え.

### ✅ Check 2: 「N-bar candle/MACD pattern」に依存するか
- 3 bar 以上の連続条件 (`x_prev2 < x_prev < x` 等) を含むか
- 包み足/たくり足/ピンバー等の candle pattern を主軸にするか
- → **YES なら破棄**: ランダムウォークで偶発的に大量発生. lookback overfit 確定.

### ✅ Check 3: 「直前 candle 方向」を単独確認に使うか
- `if entry <= open_price: return None` (BUY 時陽線確認) 等の単独条件
- → **YES なら破棄**: 5m bar の Open/Close は次の 5m と無相関. フィルタ価値ゼロ.

### ✅ Check 4: TP/SL 比が 摩擦圧倒できるか
- 数式チェック: `(TP_atr_mult × ATR_5m) - 摩擦RT` ≥ `(SL_atr_mult × ATR_5m) + 摩擦RT × 1.0`
- USD/JPY: ATR=4p, 摩擦=1.6p なら **TP_mult ≥ 2.5, SL_mult ≤ 0.7** が最低条件
- → **これを満たさないなら破棄**: 名目 RR で錯覚せず、摩擦込みの実 RR で評価.

### ✅ Check 5: Score ボーナス加算が独立変数か
- ADX/EMA順列/DI方向 のような相関オシレーターを別ボーナスで加算していないか
- MACD-H 値とその差分を別ボーナスにしていないか
- → **YES なら破棄**: 強相関オシレーターの加算は confidence を膨張させて誤った高 conf を生む.

---

## 5. 検証手順 (新戦略 deploy 前必須)

新戦略が上記 5 チェックを通過後も、**実 Live deploy には以下の N=30 ガード**:

1. Sentinel (0.01lot) で Shadow 蓄積 N≥30
2. **med MFE > 摩擦 × 2** を検証 (USD/JPY なら med MFE > 3.2p)
3. 全 27 cell (Pair × Session × Regime) で局所 EV>0 cell が **3 個以上**存在
4. 全条件未達の場合は `_FORCE_DEMOTED` 即追加 ([[lesson-dead-strategy-pattern-2026-04-25]] DEAD パターン)

これで R&D サイクルを **実装前に止める** (= R&D疲労を防ぐ).

---

## 6. 関連

- [[rd-target-rescue-anatomy-2026-04-25]] — 7 戦略の解剖根拠
- [[lesson-dead-strategy-pattern-2026-04-25]] — DEAD 戦略の判定基準
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] — bb_squeeze BT で得た補完
- [[lesson-reactive-changes]] — 反射的改修禁止
- [[external-audit-2026-04-24]] — 新 Phase 凍結方針 (本 lesson と整合)
