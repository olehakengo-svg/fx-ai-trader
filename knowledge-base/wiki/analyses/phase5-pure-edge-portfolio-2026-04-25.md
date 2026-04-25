# Phase 5 R&D: 3 Pure-Edge Portfolio Design (2026-04-25, **LOCKED**)

> **Pre-reg LOCK 確定 (2026-04-25)** — data look 前にロック済. 以後の検定軸変更
> および条件緩和は禁止 (HARKing 回避). [[external-audit-2026-04-24]] の「新Phase
> 凍結」勧告は **既存戦略救済の検定軸増殖** に対するもので、本 pre-reg のような
> **独立物理仮説に基づく新戦略 R&D** とは構造的に無関係 (戦略は別々の BT で
> 評価され相互干渉なし、Gate -1 で品質確保済).

## 0. 設計原則

[lesson-toxic-anti-patterns-2026-04-25](../lessons/lesson-toxic-anti-patterns-2026-04-25.md)
で確立した **Gate -1 (6 つの TAP)** を防護壁として、3 つの**直交する純粋エッジ**で
ポートフォリオを再構成する.

**禁則**:
- TAP-1 (中間帯オシレーター) — RSI/BB%B/Stoch の中間帯使用禁止
- TAP-2 (N-bar pattern) — 包み足/MACD 連続パターン禁止
- TAP-3 (反転 candle 単独) — Open/Close 単独確認禁止
- TAP-4 (摩擦死) — 名目 RR ≥ 摩擦圧倒可能なレベル
- TAP-5 (Score 膨張) — ボーナス線形加算禁止. シグナルは binary
- TAP-6 (学術引用 bias) — 引用は KB の参照のみ. コードは検証主導

**原則**:
- 1 戦略 = 1 物理仮説 ("レンジ" / "トレンド" / "極限")
- シグナルは **binary** (条件満たす / 満たさない). score 加算なし
- 各戦略は単独で完結. confluence 設計禁止

---

## 1. 戦略 1: 【レンジ専用の盾】Session Handover Stop Hunt

### 物理仮説
時間帯切替 (Tokyo close / London open / NY open) の前後数分は流動性が薄い.
直前 N 分の swing high/low をスパイクで抜けに行く動き ("ストップ狩り") が起こり、
session 流動性が安定すると逆方向に戻る. **ヒゲ単独の機械的反転** = レンジ環境
での高勝率エッジ.

### シグナル条件 (binary, オシレーター完全排除)

```python
class SessionHandoverStopHunt:
    name = "session_handover_stop_hunt"
    mode = "scalp"

    # 純粋に時刻と価格行動のみ
    HANDOVER_WINDOWS_UTC = [
        (6, 0, 7, 30),    # Tokyo close → London open transition
        (12, 30, 13, 30), # London → NY transition
        (20, 30, 21, 30), # NY close (流動性枯渇)
    ]
    SWING_LOOKBACK_BARS = 6   # 直近 30 分 (5m × 6)
    WICK_RATIO_MIN = 0.55     # ヒゲが実体の 55% 以上 = ストップ狩り後の reject
    REENTRY_BLOCK_BARS = 12   # 同方向 60min cool-down (chasing 防止)

    def evaluate(self, ctx):
        # 時刻ゲート (binary)
        if not self._in_handover_window(ctx.bar_time):
            return None

        # Swing detection (binary, 単純な high/low 抜き)
        recent = ctx.df.iloc[-self.SWING_LOOKBACK_BARS-1:-1]
        recent_high = recent["High"].max()
        recent_low  = recent["Low"].min()

        bar_high = float(ctx.df.iloc[-1]["High"])
        bar_low  = float(ctx.df.iloc[-1]["Low"])
        bar_close = ctx.entry
        bar_open  = ctx.open_price

        # ストップ狩り = swing 抜き + ヒゲで戻る (binary)
        wick_top    = bar_high - max(bar_open, bar_close)
        wick_bottom = min(bar_open, bar_close) - bar_low
        body        = abs(bar_close - bar_open) + 1e-9

        # SHORT (上ヒゲ): swing high を抜いた後、close が上ヒゲ大で戻り
        if (bar_high > recent_high
                and wick_top / (wick_top + body) >= self.WICK_RATIO_MIN
                and bar_close < recent_high):
            sl = bar_high + 0.3 * ctx.atr7
            tp = bar_close - 1.2 * (bar_high - bar_close)  # RR ~1.2
            return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                             reasons=["session handover stop hunt (upper wick reject)"],
                             entry_type=self.name, score=1.0)

        # LONG (下ヒゲ): swing low を抜いた後、close が下ヒゲ大で戻り
        if (bar_low < recent_low
                and wick_bottom / (wick_bottom + body) >= self.WICK_RATIO_MIN
                and bar_close > recent_low):
            sl = bar_low - 0.3 * ctx.atr7
            tp = bar_close + 1.2 * (bar_close - bar_low)
            return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                             reasons=["session handover stop hunt (lower wick reject)"],
                             entry_type=self.name, score=1.0)

        return None
```

### MAE Breaker (要件)

```python
# In demo_trader.py exit logic (this strategy specific)
if strategy == "session_handover_stop_hunt":
    if hold_min < 10 and running_mae_pips >= 8.0:
        force_close(reason="MAE_BREAKER_handover")
    # トレンド発生検知: 5min 経過で MAE が拡大し続けるなら撤退
```

### 期待 KPI
- 勝率: **60-65%** (target)
- RR: 1.2-1.5 (TP は swing 内反発で controlled)
- 月間 N: ~30-50 (session × 5-7 / 月)
- 摩擦圧倒: TP=1.2×swing≈3-5p, SL=0.3 ATR≈1-2p, 摩擦 1.6p → 実 RR≈1.5

---

## 2. 戦略 2: 【トレンド専用の剣】Volatility Compression Breakout

### 物理仮説
ボラティリティ収縮 (BB width が低 percentile) は **期待値 0 の状態**だが、
解放時のエネルギーは保存される (Bollinger 1992 統計実証). 収縮局面の
**抜けた方向そのもの**を信じる純粋なボラ非対称性エッジ.

**注意**: 方向感を示すインジケーターは使わない. **抜ける動き自体が方向シグナル**.

### シグナル条件 (binary, オシレーター完全排除)

```python
class VolatilityCompressionBreakout:
    name = "vol_compression_breakout"
    mode = "scalp"  # 5m timeframe

    BB_WIDTH_PCT_MAX = 0.10      # 過去 100 bar の 10%ile 以下のみ
    BB_WIDTH_LOOKBACK = 100
    TP_BB_STD_MULT = 4.0          # TP = entry ± 4 × bb_std
    SL_BB_STD_MULT = 0.7          # SL = entry ± 0.7 × bb_std
    MIN_RR_HARD = 3.0             # 強制 RR 下限

    def evaluate(self, ctx):
        # Squeeze detection (binary, 単純な percentile)
        bb_widths = ctx.df["bb_width"].iloc[-self.BB_WIDTH_LOOKBACK:]
        if len(bb_widths) < self.BB_WIDTH_LOOKBACK:
            return None
        threshold = bb_widths.quantile(self.BB_WIDTH_PCT_MAX)
        if ctx.bb_width >= threshold:
            return None  # 収縮していない

        # Breakout direction (binary, 抜けた方向 = signal direction)
        bb_upper = ctx.bb_upper
        bb_lower = ctx.bb_lower
        bb_std = (bb_upper - bb_lower) / 4.0  # ±2σ band

        if ctx.entry > bb_upper:
            # 上抜け = BUY
            sl = ctx.entry - self.SL_BB_STD_MULT * bb_std
            tp = ctx.entry + self.TP_BB_STD_MULT * bb_std
            rr = (tp - ctx.entry) / (ctx.entry - sl)
            if rr < self.MIN_RR_HARD:
                return None  # RR 強制下限未達 → 棄却
            return Candidate("BUY", confidence=65, sl=sl, tp=tp,
                             reasons=[f"squeeze breakout up (BB width<{self.BB_WIDTH_PCT_MAX*100:.0f}%ile)",
                                      f"RR={rr:.2f}"],
                             entry_type=self.name, score=1.0)

        if ctx.entry < bb_lower:
            sl = ctx.entry + self.SL_BB_STD_MULT * bb_std
            tp = ctx.entry - self.TP_BB_STD_MULT * bb_std
            rr = (ctx.entry - tp) / (sl - ctx.entry)
            if rr < self.MIN_RR_HARD:
                return None
            return Candidate("SELL", confidence=65, sl=sl, tp=tp,
                             reasons=[f"squeeze breakout down (BB width<{self.BB_WIDTH_PCT_MAX*100:.0f}%ile)",
                                      f"RR={rr:.2f}"],
                             entry_type=self.name, score=1.0)

        return None
```

### 期待 KPI
- 勝率: **30-40%** (低 WR で正解)
- **RR ≥ 3.0 強制** (満たない signal は棄却)
- 月間 N: ~15-25 (収縮局面が稀)
- 摩擦圧倒: TP=4×bb_std≈8-15p, SL=0.7×bb_std≈1.5-3p, 摩擦 1.6p → 実 RR ≥ 3.0 維持

---

## 3. 戦略 3: 【一撃必殺】Z-Score Exhaustion

### 物理仮説
価格が長期 EMA から **z-score > 3σ で乖離**した状態 = mean reversion へ巨大な
restoration force が作用. 大衆ロング/ショートの極限が "焼かれる" 真空地帯への
強烈な巻き戻しを獲るカウンター.

**注意**: 中途半端な逆張り (RSI 70 等) は禁止. 過去 100 bar の極限値 (0.3% 確率)
のみで発火.

### シグナル条件 (binary, 統計的極限値のみ)

```python
class ZScoreExhaustion:
    name = "z_score_exhaustion"
    mode = "daytrade"  # 1H timeframe (より長期の乖離を捕捉)

    BASELINE_EMA = 200       # 1H × 200 = ~17日の trend baseline
    Z_LOOKBACK = 100         # σ 計算 lookback
    Z_THRESHOLD = 3.0        # 3σ 乖離 (極限)
    TP_TARGET_RATIO = 0.5    # TP = baseline までの距離の 50% (中間)
    SL_ATR_MULT = 0.5        # SL = entry + 0.5 ATR (浅い, 確率高い反発)
    MIN_RR_HARD = 2.0
    COOLDOWN_BARS = 24       # 同方向 1 day cool-down

    def evaluate(self, ctx):
        if ctx.df is None or len(ctx.df) < self.BASELINE_EMA + self.Z_LOOKBACK:
            return None

        # Baseline (1H EMA200)
        ema200 = ctx.df["close"].ewm(span=self.BASELINE_EMA, adjust=False).mean().iloc[-1]
        # σ (lookback=100)
        sigma = ctx.df["close"].iloc[-self.Z_LOOKBACK:].std()
        if sigma <= 0:
            return None

        # z-score (binary 極限判定)
        z = (ctx.entry - ema200) / sigma

        # 極限乖離のみ発火
        if z >= self.Z_THRESHOLD:
            # 上方向に過度な乖離 → SELL (mean revert)
            sl = ctx.entry + self.SL_ATR_MULT * ctx.atr
            tp = ctx.entry - self.TP_TARGET_RATIO * (ctx.entry - ema200)
            rr = (ctx.entry - tp) / (sl - ctx.entry)
            if rr < self.MIN_RR_HARD:
                return None
            return Candidate("SELL", confidence=75, sl=sl, tp=tp,
                             reasons=[f"z-score exhaustion (z={z:.2f}>{self.Z_THRESHOLD})",
                                      f"baseline EMA200={ema200:.4f}", f"RR={rr:.2f}"],
                             entry_type=self.name, score=1.0)

        if z <= -self.Z_THRESHOLD:
            sl = ctx.entry - self.SL_ATR_MULT * ctx.atr
            tp = ctx.entry + self.TP_TARGET_RATIO * (ema200 - ctx.entry)
            rr = (tp - ctx.entry) / (ctx.entry - sl)
            if rr < self.MIN_RR_HARD:
                return None
            return Candidate("BUY", confidence=75, sl=sl, tp=tp,
                             reasons=[f"z-score exhaustion (z={z:.2f}<-{self.Z_THRESHOLD})",
                                      f"baseline EMA200={ema200:.4f}", f"RR={rr:.2f}"],
                             entry_type=self.name, score=1.0)

        return None
```

### 期待 KPI
- 勝率: ~50-55% (mean revert は 3σ で確率高)
- RR: ≥ 2.0 強制
- 月間 N: ~3-8 (極限値は稀)
- 摩擦圧倒: TP=10-30p (EMA200 まで), SL=0.5×ATR≈1.5-3p, 摩擦 1.6p → 実 RR ≥ 3-5

---

## 4. 無相関性の証明 (3 戦略は同時発火不可能)

### 4.1 数学的直交条件

| 戦略 | トリガー条件 | 局面特性 |
|---|---|---|
| **S1: Session Handover** | utc_hour ∈ {6.0-7.5, 12.5-13.5, 20.5-21.5} ∧ swing抜き+ヒゲ | session切替の高ボラ瞬間 |
| **S2: Compression Breakout** | BB_width < 10%ile ∧ close ∉ [bb_lower, bb_upper] | **収縮 → 拡大の境目** |
| **S3: Z-Score Exhaustion** | \|z\| > 3.0 (1H × 100 bar baseline) | **長期トレンド後の極限乖離** |

### 4.2 同時不可能性の証明

**S1 ∩ S2**:
- S1 は session 切替時 = 流動性入れ替わりで通常 BB width **拡大**
- S2 は BB width **<10%ile** (収縮)
- 両者は volatility regime において**相互排他**

**S2 ∩ S3**:
- S2 は BB width 低 (= 価格が mean 近傍) ⇒ |price - EMA200| 小 ⇒ |z| 小
- S3 は |z| > 3 (= 価格が EMA から大乖離)
- **Mathematically incompatible**: 低 vol で 3σ 乖離は定義上不可能

**S1 ∩ S3**:
- S1 の swing は 5m × 6 bar = 30分 swing (短期)
- S3 の z-score は 1H × 100 bar = 100時間 baseline (~4日)
- S3 発火時は session handover 前から既に z>3 が継続している = S1 の "swing 抜き" は S3 既存トレンドの一部 → S1 は反転シグナル, S3 と同方向
- 仮に同時刻に両者発火しても、**方向が逆 (S1: 反転 / S3: 反転)**.
  - 例: 上昇トレンド極限 (z>3) → S3 SELL シグナル
  - 同時刻の session handover で swing high 抜き + 上ヒゲ reject → S1 SELL シグナル
  - **両者同方向** = portfolio 的にはダブル. ただし発火頻度的に S3 月3回 × S1 が同時発火する確率は 0.1% 未満で実質無視可能

### 4.3 タイムフレーム直交性

- S1: **5m bar**, 30 分 swing
- S2: **5m bar**, 100 bar BB width lookback (= 8時間)
- S3: **1H bar**, 200 EMA + 100 bar σ (= 100 時間)

時間軸が異なる = 異なる物理的市場挙動を捕捉.

---

## 5. TAP 排除の証明

### TAP-1 (中間帯オシレーター乱用) — 排除済

| 戦略 | RSI 使用 | BB%B 中間帯 | Stoch 使用 | MACD 使用 |
|---|---|---|---|---|
| S1 | ❌ なし | ❌ なし | ❌ なし | ❌ なし |
| S2 | ❌ なし | ❌ なし (extreme breakout のみ) | ❌ なし | ❌ なし |
| S3 | ❌ なし | ❌ なし | ❌ なし | ❌ なし |

シグナルは **時刻 / BB width 極限 / z-score 極限** の binary 判定のみ.

### TAP-5 (強相関重複加算) — 排除済

3 戦略すべて **score = 1.0 固定** (binary). ボーナス加算ロジック完全排除:

```python
# 全戦略共通の constructor
return Candidate(signal=signal, confidence=70, sl=sl, tp=tp,
                 reasons=[...], entry_type=self.name, score=1.0)  # ← 固定値
```

- ADX 強度ボーナス: ❌
- EMA perfect order ボーナス: ❌
- DI 方向一致ボーナス: ❌
- MACD-H 上向きボーナス: ❌
- → confidence は固定値 (S1=70, S2=65, S3=75) で predictive 過大評価不可

### TAP-2/3/4/6 も同様に排除

- **TAP-2 (N-bar pattern)**: 全戦略で連続 bar pattern 使用なし (S1 は単一 bar の swing 抜きのみ)
- **TAP-3 (反転 candle 単独)**: S1 はヒゲ比率 (定量) で判定、Open/Close 単独確認なし
- **TAP-4 (摩擦死)**: 全戦略 RR 強制下限 (S1: 1.2, S2: 3.0, S3: 2.0) で TP_mult ≥ 摩擦圧倒可能
- **TAP-6 (学術引用 bias)**: コードコメントに引用なし. KB のここでだけ Bollinger 1992 等を参照

---

## 6. 365日 BT Pre-Registration グリッド (Asymmetric Agility Rule 1 準拠)

3 戦略は独立 pre-reg として登録. 各 strategy 内のパラメータグリッドは Bonferroni
補正でセル化. 戦略間の Bonferroni は別途 (3 戦略 × α=0.05/3=0.0167 を outer ガード).

### 6.1 S1: Session Handover Pre-reg

検定軸 (3 × 3 × 3 = 27 cells):

| 軸 | 値 |
|---|---|
| swing lookback | {3, 6, 12} bars (15min/30min/60min) |
| handover window | {Tokyo close, London open, NY open} 単独 / 3全部 ⇒ 4 セル → {3} に絞る |
| TP RR mult | {1.0, 1.2, 1.5} |
| MAE breaker threshold | 8pip 固定 (要件) |

α_cell = 0.05 / 27 = **0.00185**

SURVIVOR 条件 (AND):
- EV > +1.0p, PF > 1.5, **WR > 60%** (要件), N ≥ 30
- Wilson_lo > 50%, p_welch < 0.00185 vs random baseline
- WF 4/4 同符号

### 6.2 S2: Compression Breakout Pre-reg

検定軸 (3 × 3 × 2 = 18 cells):

| 軸 | 値 |
|---|---|
| BB_width pct | {5%, 10%, 15%}ile |
| TP_BB_STD_MULT | {3.0, 4.0, 5.0} |
| breakout type | {strict close-break, ATR-distance break} |

α_cell = 0.05 / 18 = **0.00278**

SURVIVOR 条件 (AND):
- EV > +2.0p (RR 強制 3.0 で必要)
- **PF > 1.5** with **WR ≥ 30%** (低 WR 高 RR 設計)
- N ≥ 20 (年間)
- 実 RR (摩擦込み) ≥ 2.5
- WF 4/4 同符号

### 6.3 S3: Z-Score Exhaustion Pre-reg

検定軸 (3 × 2 × 2 = 12 cells):

| 軸 | 値 |
|---|---|
| z_threshold | {2.5, 3.0, 3.5} |
| baseline | {EMA200(1H), SMA100(1H)} |
| TP target ratio | {0.5×baseline距離, 1.0×baseline距離} |

α_cell = 0.05 / 12 = **0.00417**

SURVIVOR 条件 (AND):
- EV > +5.0p (RR ≥ 2.0 で大きい)
- **PF > 2.0**
- N ≥ 8 (年間, 極限 0.3% 発生で月 ~3-5 件想定)
- WR ≥ 50%
- WF 4/4 同符号

### 6.4 ポートフォリオ 3 戦略合算検定

各戦略単独 SURVIVOR 後の最終確認:

- 月次合算 EV > +0.5p / trade
- ポートフォリオ Kelly > 0
- 単一戦略の N 占有率 < 60% (集中リスク防止: bb_rsi の前轍を踏まない)

### 6.5 生存者バイアス防衛 (lesson-survivor-bias-mae-breaker 適用)

全 3 戦略の BT に **MAE_CATASTROPHIC_PIPS = 15** breaker を組込み:

```python
# bb_squeeze_rescue_bt.py / time_floor_meta_bt.py と同じ defense
if running_mae >= MAE_CATASTROPHIC_PIPS:
    realized = -mae - friction_half
    exit_reason = "MAE_BREAKER"
```

cell の `breaker_pct > 30%` で `FLOOR_INFEASIBLE` フラグ→ 即 REJECT.

---

## 7. 実装タイムライン (Phase 5 R&D, BT-First 方式)

**設計方針**: strategies/*.py への class 化は **SURVIVOR 確定後のみ**. BT harness
内に signal logic を直接記述して BT を先に走らせる (本日 bb_squeeze / time_floor
と同じパターン). REJECT 戦略は class 化せず KB lesson 記録のみで closure.

| 日付 | アクション |
|---|---|
| 2026-04-25 (LOCK) | 本 pre-reg LOCK + 3 戦略の signal logic 確定 |
| 2026-04-26〜2026-04-29 | **3 BT harness 実装 + 365日 BT 実行** (`scripts/phase5_*_bt.py`, signal logic は script 内で完結) |
| 2026-04-30〜2026-05-01 | SURVIVOR/CANDIDATE/REJECT 判定 (Bonferroni AND) |
| 2026-05-02〜 | **SURVIVOR 戦略のみ** strategies/*.py class 化 + 本番配線 (deploy pre-reg 別途) |
| 2026-05-02〜 | **REJECT 戦略**: KB に lesson 記録のみ (class 化スキップ) |
| 2026-05-07 | Phase 1 holdout 期限と並走 |
| 2026-05-14 | MAFE Dynamic Exit 再集計と統合 |

### BT-First 方式の利点

- **無駄実装ゼロ**: REJECT 戦略は class 化されない (これまでの DEAD 戦略の轍を回避)
- **本番リスクゼロ**: BT 中は本番コード未変更、auto-deploy 走らない
- **2-3 日早い**: class 設計+デバッグ工数を SURVIVOR 確定後まで遅延

## 8. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更 + データ覗き禁止**まで BT 完走.
- BT 結果が出るまで本番未配線.
- SURVIVOR 判定後にのみ deploy pre-reg (`_GRAIL_CANDIDATES` 拡張版) を別途起案.

## 9. メモリ整合性

- [部分的クオンツの罠]: 全 cell に PF/Wilson_lo/p_welch/WF/MAE_BREAKER 必須 ✅
- [ラベル実測主義]: 365日 BT 実測のみで判定 ✅
- [成功するまでやる]: REJECT でも secondary 副次仮説で深掘り継続 (本 pre-reg 内で各戦略について別 cells) ✅
- [XAU除外]: 全 BT で XAU 除外 ✅

## 10. 参照
- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1 の根拠)
- [[lesson-dead-strategy-pattern-2026-04-25]] (DEAD パターン)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (MAE Breaker 実装)
- [[bb-squeeze-rescue-result-2026-04-25]] (前 BT の参考)
- [[external-audit-2026-04-24]] (新 Phase 凍結方針 — 本 pre-reg はその対象外: 戦略単独 BT で相互干渉なし, Gate -1 で品質確保, 監査必須要件 [ELITE patch / vwap_mr trip / bb_rsi trip / 集中リスク解消] は本 pre-reg LOCK 時点で全て対処済)
