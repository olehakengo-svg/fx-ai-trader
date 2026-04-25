# Phase 5 Extended: S4-S9 Pure-Edge Portfolio (2026-04-25, **LOCKED**)

> **Pre-reg LOCK 確定 (2026-04-25)** — data look 前. S1-S3 ([[phase5-pure-edge-portfolio-2026-04-25]]) の補完.
> 9 戦略全体で「相場の全事象」を直交カバー.

## 0. 設計原則 (S1-S3 と共通)

- TAP-1〜6 完全排除 ([[lesson-toxic-anti-patterns-2026-04-25]] Gate -1)
- 各戦略 1 物理仮説、binary signal、score=1.0 固定
- オシレーター中間帯参照禁止 (極限値のみ許容)
- RR は摩擦圧倒可能な強制下限を持つ

---

## 1. S4: Pure Divergence (モメンタム枯渇)

### 第一原理
価格 new HH/LL × オシレーター内部エネルギー減衰 = トレンド終焉の構造的シグナル.

### 条件 (binary)

```python
class PureDivergence:
    name = "pure_divergence"
    mode = "scalp"  # 5m

    DIVERGENCE_LOOKBACK = 30      # 30 bar swing 探索
    RSI_OVERBOUGHT = 80           # 極限のみ参照 (TAP-1 回避)
    RSI_OVERSOLD = 20
    SL_ATR_MULT = 0.8
    MIN_RR_HARD = 2.0

    def evaluate(self, ctx):
        # Detect 直近 swing
        recent = ctx.df.iloc[-self.DIVERGENCE_LOOKBACK:]
        swing_high_idx = recent["High"].idxmax()
        swing_low_idx = recent["Low"].idxmin()

        bar = ctx.df.iloc[-1]
        cur_high = float(bar["High"])
        cur_low = float(bar["Low"])
        cur_rsi = ctx.rsi5

        # BEARISH divergence: 価格 new HH AND RSI が前回 swing high より低い
        # かつ RSI が overbought 帯 (極限のみ)
        prev_swing_high = float(recent.loc[swing_high_idx, "High"])
        prev_swing_rsi_high = float(ctx.df.loc[swing_high_idx, "rsi5"]) if "rsi5" in ctx.df.columns else None
        if (cur_high > prev_swing_high
                and prev_swing_rsi_high is not None
                and cur_rsi < prev_swing_rsi_high
                and cur_rsi >= self.RSI_OVERBOUGHT):  # ← 極限値のみ
            sl = cur_high + self.SL_ATR_MULT * ctx.atr7
            tp_dist = (cur_high - prev_swing_high) * self.MIN_RR_HARD * 2
            tp = ctx.entry - tp_dist
            return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                             reasons=[f"bearish div: HH={cur_high:.5f}>{prev_swing_high:.5f} "
                                      f"RSI={cur_rsi:.1f}<{prev_swing_rsi_high:.1f} (overbought)"],
                             entry_type=self.name, score=1.0)

        # BULLISH divergence: mirror
        prev_swing_low = float(recent.loc[swing_low_idx, "Low"])
        prev_swing_rsi_low = float(ctx.df.loc[swing_low_idx, "rsi5"]) if "rsi5" in ctx.df.columns else None
        if (cur_low < prev_swing_low
                and prev_swing_rsi_low is not None
                and cur_rsi > prev_swing_rsi_low
                and cur_rsi <= self.RSI_OVERSOLD):  # ← 極限値のみ
            sl = cur_low - self.SL_ATR_MULT * ctx.atr7
            tp_dist = (prev_swing_low - cur_low) * self.MIN_RR_HARD * 2
            tp = ctx.entry + tp_dist
            return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                             reasons=[...],
                             entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: RSI は極限値 (≤20 / ≥80) でのみ参照 = 中間帯使用ゼロ (TAP-1 OK). 単独
オシレーター + 価格 swing のみ (TAP-5 OK). Score 加算なし.

---

## 2. S5: VWAP / HTF Defense (機関投資家の防衛線)

### 第一原理
強トレンド中、大口は VWAP / HTF EMA で買い支え/売り叩き.「最初の深い押し目」での
タッチ&反発はトレンド継続シグナル.

### 条件 (binary)

```python
class VWAPHTFDefense:
    name = "vwap_htf_defense"
    mode = "scalp"  # 5m, ただし HTF (1H) EMA 参照

    PULLBACK_MIN_ATR = 1.5          # 直近 swing から最低 1.5 ATR の押し目
    DEFENSE_TOUCH_ATR = 0.2         # 防衛線±0.2ATR 以内 touch
    EMA_HTF_PERIOD = 50             # 1H EMA50 (= ~2 day baseline)
    SL_ATR_MULT = 0.8
    MIN_RR_HARD = 2.5

    def evaluate(self, ctx):
        # HTF EMA50 (from htf_cache 経由)
        htf = ctx.htf_cache.get("htf", {})
        ema_htf = htf.get("ema50_1h")
        vwap = ctx.df["vwap"].iloc[-1] if "vwap" in ctx.df.columns else None
        if ema_htf is None or vwap is None:
            return None

        # Trend confirmation (binary, EMA9 vs EMA21 vs EMA50, all aligned)
        trend_up = ctx.ema9 > ctx.ema21 > ctx.ema50
        trend_down = ctx.ema9 < ctx.ema21 < ctx.ema50
        if not (trend_up or trend_down):
            return None

        # Pullback depth check (binary, swing から最低 1.5ATR)
        recent_high = ctx.df["High"].iloc[-30:].max()
        recent_low = ctx.df["Low"].iloc[-30:].min()
        pullback_dist = (recent_high - ctx.entry) if trend_up else (ctx.entry - recent_low)
        if pullback_dist < self.PULLBACK_MIN_ATR * ctx.atr7:
            return None  # 浅い押しは S5 対象外

        # Defense touch (VWAP or HTF EMA に ±0.2 ATR 以内)
        touch_vwap = abs(ctx.entry - vwap) < self.DEFENSE_TOUCH_ATR * ctx.atr7
        touch_ema = abs(ctx.entry - ema_htf) < self.DEFENSE_TOUCH_ATR * ctx.atr7
        if not (touch_vwap or touch_ema):
            return None

        # 反発確認: 直前 bar が touch、当該 bar が away (price action)
        prev_low = float(ctx.df.iloc[-2]["Low"])
        prev_high = float(ctx.df.iloc[-2]["High"])
        defense_line = vwap if touch_vwap else ema_htf

        if trend_up and prev_low <= defense_line and ctx.entry > defense_line:
            sl = min(prev_low, ctx.entry - self.SL_ATR_MULT * ctx.atr7)
            tp = ctx.entry + self.MIN_RR_HARD * (ctx.entry - sl)
            return Candidate("BUY", confidence=72, sl=sl, tp=tp,
                             reasons=[f"VWAP/HTF defense bounce (trend up, touch+reject)"],
                             entry_type=self.name, score=1.0)

        if trend_down and prev_high >= defense_line and ctx.entry < defense_line:
            sl = max(prev_high, ctx.entry + self.SL_ATR_MULT * ctx.atr7)
            tp = ctx.entry - self.MIN_RR_HARD * (sl - ctx.entry)
            return Candidate("SELL", confidence=72, sl=sl, tp=tp,
                             reasons=[...],
                             entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: オシレーター完全不使用 (EMA は trend confirmation のみ, score 加算なし).
深い押し条件で binary フィルタ (中間帯回避).

---

## 3. S6: Value Area Reversion (構造的レンジ)

### 第一原理
Volume Profile (Time at Price) の Value Area (70%) を逸脱した価格は POC (最頻値)
へ引き戻される. 時刻非依存の高勝率エッジ.

### 条件 (binary)

```python
class ValueAreaReversion:
    name = "value_area_reversion"
    mode = "scalp"  # 5m

    VP_LOOKBACK_HOURS = 6           # 直近 6h = 72 bar の価格滞留
    VP_BUCKETS = 30                 # 価格を 30 bucket に量子化
    VA_PERCENTILE = 0.85            # Value Area = TPC 上位 85% (極限的逸脱)
    SL_ATR_MULT = 0.5
    TP_TO_POC_RATIO = 0.6           # TP は POC までの 60%
    MIN_RR_HARD = 2.0

    def evaluate(self, ctx):
        recent = ctx.df.iloc[-self.VP_LOOKBACK_HOURS * 12:]   # 5m × 12 = 1h
        if len(recent) < self.VP_LOOKBACK_HOURS * 12:
            return None

        # Volume Profile build (TPO approximation, time at each price bucket)
        prices = recent["Close"].values
        lo, hi = prices.min(), prices.max()
        if hi - lo <= 0:
            return None
        bucket_size = (hi - lo) / self.VP_BUCKETS
        tpo = [0] * self.VP_BUCKETS
        for p in prices:
            idx = min(int((p - lo) / bucket_size), self.VP_BUCKETS - 1)
            tpo[idx] += 1

        # POC (最頻値 bucket)
        poc_idx = max(range(self.VP_BUCKETS), key=lambda i: tpo[i])
        poc = lo + (poc_idx + 0.5) * bucket_size

        # Value Area: TPO 累積 85% に達するまで POC から外側に拡張
        sorted_idxs = sorted(range(self.VP_BUCKETS), key=lambda i: -tpo[i])
        cumsum = 0
        total = sum(tpo)
        in_va = set()
        for i in sorted_idxs:
            in_va.add(i)
            cumsum += tpo[i]
            if cumsum / total >= self.VA_PERCENTILE:
                break
        va_high = lo + (max(in_va) + 1) * bucket_size
        va_low = lo + min(in_va) * bucket_size

        # 現在価格が VA 外に逸脱したか (binary)
        if va_low <= ctx.entry <= va_high:
            return None  # VA 内 = 発火なし

        # 内側回帰の確認 (前 bar は更に外, 当該 bar は VA に近づく)
        prev_close = float(ctx.df.iloc[-2]["Close"])

        if ctx.entry > va_high and ctx.entry < prev_close:
            # 上に逸脱 → 下方向 (POC へ) 戻り
            sl = float(ctx.df["High"].iloc[-3:].max()) + self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry - self.TP_TO_POC_RATIO * (ctx.entry - poc)
            return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                             reasons=[f"VA reversion (>{va_high:.5f} → POC={poc:.5f})"],
                             entry_type=self.name, score=1.0)

        if ctx.entry < va_low and ctx.entry > prev_close:
            sl = float(ctx.df["Low"].iloc[-3:].min()) - self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry + self.TP_TO_POC_RATIO * (poc - ctx.entry)
            return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                             reasons=[...],
                             entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: オシレーター完全不使用. Volume Profile という独立物理量のみ.

---

## 4. S7: Opening Range Breakout (セッション初動)

### 第一原理
London/NY open 直後の Asia レンジ突破 + Tick Volume 急増 = 1 日の方向決定的シグナル.

### 条件 (binary)

```python
class OpeningRangeBreakout:
    name = "opening_range_breakout"
    mode = "scalp"  # 5m

    OPEN_WINDOWS_UTC = [
        (7, 0, 8, 30),    # London open (Asia レンジ突破期待)
        (13, 0, 14, 30),  # NY open (London 引継ぎ)
    ]
    ASIA_RANGE_HOURS = 6              # 直前 6h = Tokyo session
    VOLUME_SPIKE_RATIO = 3.0          # 過去 50 bar 平均 Volume の 3倍
    SL_ATR_MULT = 0.8
    MIN_RR_HARD = 2.0

    def evaluate(self, ctx):
        bar_time = ctx.bar_time
        # Time gate (binary)
        if not self._in_open_window(bar_time):
            return None

        # Asia レンジ計算
        asia_bars = ctx.df.iloc[-self.ASIA_RANGE_HOURS * 12: -1]
        asia_high = float(asia_bars["High"].max())
        asia_low = float(asia_bars["Low"].min())

        # Volume spike (binary)
        cur_vol = float(ctx.df["Volume"].iloc[-1]) if "Volume" in ctx.df.columns else 0
        avg_vol = float(ctx.df["Volume"].iloc[-50:-1].mean()) if "Volume" in ctx.df.columns else 1
        if cur_vol < avg_vol * self.VOLUME_SPIKE_RATIO:
            return None

        bar_close = ctx.entry

        # 突破確認 (binary)
        if bar_close > asia_high:
            sl = asia_high - self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry + self.MIN_RR_HARD * (ctx.entry - sl)
            return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                             reasons=[f"ORB UP (Asia high {asia_high:.5f}) + vol×{cur_vol/avg_vol:.1f}"],
                             entry_type=self.name, score=1.0)

        if bar_close < asia_low:
            sl = asia_low + self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry - self.MIN_RR_HARD * (sl - ctx.entry)
            return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                             reasons=[...],
                             entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: 時刻 + range break + volume の 3 binary 条件のみ. オシレーター不使用.

---

## 5. S8: Fair Value Gap (FVG / Imbalance)

### 第一原理
3-bar 急激値動きで形成される **bar1 と bar3 の重なりがない隙間 (Imbalance)** は、
後で再テスト (mean revert toward gap) される引力を持つ.

### 条件 (binary)

```python
class FairValueGap:
    name = "fair_value_gap"
    mode = "scalp"  # 5m

    GAP_MIN_ATR_MULT = 0.5            # 隙間幅が 0.5 ATR 以上 (極限のみ)
    REENTRY_LOOKBACK_BARS = 50        # 直近 50 bar 内の FVG を track
    SL_ATR_MULT = 0.5
    MIN_RR_HARD = 2.0

    def evaluate(self, ctx):
        # FVG 検出: bar[i-2], bar[i-1], bar[i] の関係
        # Bullish FVG: bar[i-2].High < bar[i].Low (ギャップ上)
        # Bearish FVG: bar[i-2].Low > bar[i].High (ギャップ下)
        df = ctx.df

        # 直近 N bar の FVG リスト
        for j in range(max(2, len(df) - self.REENTRY_LOOKBACK_BARS), len(df) - 1):
            bar2_high = float(df["High"].iloc[j-2])
            bar2_low = float(df["Low"].iloc[j-2])
            bar0_high = float(df["High"].iloc[j])
            bar0_low = float(df["Low"].iloc[j])
            atr_at_j = float(df["atr7"].iloc[j])

            # Bullish FVG (上方向 imbalance)
            if bar2_high < bar0_low:
                gap = bar0_low - bar2_high
                if gap < self.GAP_MIN_ATR_MULT * atr_at_j:
                    continue
                # 当該 bar が gap zone に touch したか
                cur_low = float(df["Low"].iloc[-1])
                cur_close = float(df["Close"].iloc[-1])
                cur_open = float(df["Open"].iloc[-1])
                if cur_low <= bar0_low and cur_close > cur_open and cur_close > bar2_high:
                    sl = bar2_high - self.SL_ATR_MULT * ctx.atr7
                    tp = ctx.entry + self.MIN_RR_HARD * (ctx.entry - sl)
                    return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                                     reasons=[f"FVG fill (bullish gap {bar2_high:.5f}-{bar0_low:.5f})"],
                                     entry_type=self.name, score=1.0)
            # Bearish FVG (mirror)
            if bar2_low > bar0_high:
                gap = bar2_low - bar0_high
                if gap < self.GAP_MIN_ATR_MULT * atr_at_j:
                    continue
                cur_high = float(df["High"].iloc[-1])
                cur_close = float(df["Close"].iloc[-1])
                cur_open = float(df["Open"].iloc[-1])
                if cur_high >= bar0_high and cur_close < cur_open and cur_close < bar2_low:
                    sl = bar2_low + self.SL_ATR_MULT * ctx.atr7
                    tp = ctx.entry - self.MIN_RR_HARD * (sl - ctx.entry)
                    return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                                     reasons=[...],
                                     entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: 純粋な price action geometry のみ. オシレーター不使用.

---

## 6. S9: Volume Spread Anomaly (大口の吸収)

### 第一原理
Volume が異常高 + Body 異常小 = 大口指値で価格が固定 = absorption (吸収).
吸収方向 = 大口の建玉方向 → 反対方向にエントリー (吸収後の反発).

### 条件 (binary)

```python
class VolumeSpreadAnomaly:
    name = "volume_spread_anomaly"
    mode = "scalp"  # 5m

    VOLUME_SPIKE_MIN = 3.0             # 過去 50 bar 平均の 3 倍
    BODY_RATIO_MAX = 0.5               # ボディが過去 50 bar 平均の 0.5 倍以下
    LOOKBACK = 50
    SL_ATR_MULT = 0.6
    MIN_RR_HARD = 2.0

    def evaluate(self, ctx):
        df = ctx.df
        if "Volume" not in df.columns or len(df) < self.LOOKBACK + 1:
            return None

        cur_vol = float(df["Volume"].iloc[-1])
        cur_body = abs(float(df["Close"].iloc[-1]) - float(df["Open"].iloc[-1]))
        cur_high = float(df["High"].iloc[-1])
        cur_low = float(df["Low"].iloc[-1])
        cur_close = float(df["Close"].iloc[-1])

        avg_vol = float(df["Volume"].iloc[-self.LOOKBACK - 1: -1].mean())
        avg_body = abs(df["Close"].iloc[-self.LOOKBACK - 1: -1] - df["Open"].iloc[-self.LOOKBACK - 1: -1]).mean()

        # 矛盾検出 (binary)
        if cur_vol < self.VOLUME_SPIKE_MIN * avg_vol:
            return None
        if cur_body > self.BODY_RATIO_MAX * avg_body:
            return None

        # 吸収方向判定: bar 内で価格は range が広いはず (大口が両側に吸収)
        # 終値の位置で direction 推定
        bar_range = cur_high - cur_low
        if bar_range <= 0:
            return None
        close_pos = (cur_close - cur_low) / bar_range
        if close_pos > 0.7:
            # Bottom absorption → 上方向への反発
            sl = cur_low - self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry + self.MIN_RR_HARD * (ctx.entry - sl)
            return Candidate("BUY", confidence=70, sl=sl, tp=tp,
                             reasons=[f"VSA absorption bottom (vol×{cur_vol/avg_vol:.1f}, body{cur_body/avg_body:.2f}x)"],
                             entry_type=self.name, score=1.0)
        if close_pos < 0.3:
            sl = cur_high + self.SL_ATR_MULT * ctx.atr7
            tp = ctx.entry - self.MIN_RR_HARD * (sl - ctx.entry)
            return Candidate("SELL", confidence=70, sl=sl, tp=tp,
                             reasons=[...],
                             entry_type=self.name, score=1.0)

        return None
```

**TAP 排除**: 純粋な volume × body geometry. オシレーター不使用.

---

## 7. 9 戦略の無相関性証明 (8C2 = 28 ペア排他)

### 7.1 Trigger 直交マトリクス

| | 主トリガー | 局面特性 | TF |
|---|---|---|---|
| S1 Handover | utc_hour ∈ {特定時刻} ∧ swing wick | session 切替高 vol | 5m |
| S2 Compression | BB_width <10%ile ∧ breakout | squeeze 低 vol → 拡大 | 5m |
| S3 Exhaustion | \|z\|>3σ vs EMA200(1H) | 長期トレンド極限 | 1H |
| **S4 Divergence** | 価格 new HH/LL ∧ RSI **極限値** divergent | trend 終焉 swing | 5m |
| **S5 VWAP Defense** | 強 trend ∧ 深い押し ∧ VWAP/HTF EMA touch | trend 中盤 押し戻り | 5m+1H |
| **S6 VA Reversion** | 価格 ∉ Value Area (85%) ∧ 内側回帰 | range 構造的偏在 | 5m |
| **S7 ORB** | utc_hour ∈ {open} ∧ Asia range break ∧ vol×3 | session 開始爆発 | 5m |
| **S8 FVG** | 3-bar gap ≥ 0.5 ATR ∧ pullback fill | 急激 imbalance fill | 5m |
| **S9 VSA Absorption** | vol ≥ 3x ∧ body ≤ 0.5x | 大口指値 absorption | 5m |

### 7.2 ペア排他証明 (主要なもの)

**S2 ∩ S4**: S2 は squeeze (低 vol → breakout), S4 は trend 終焉 swing (高 vol).
S4 発火時 BB width は通常 mid-high 帯, S2 の <10%ile 条件と矛盾.

**S2 ∩ S5**: S5 は強 trend 中の押し戻り (= breakout 後の継続局面). S2 は breakout
発生瞬間. **時系列順** (S2 → S5) で同時刻発火不可能.

**S2 ∩ S7**: S2 (squeeze 後 breakout) と S7 (ORB) は両方 breakout だが:
- S2: BB width <10%ile (= 数日の squeeze)
- S7: Asia range break (= 数時間の range)
- + S7 は時刻条件 (open ±90分) で限定 → S2 が同時刻発火する場合も volume×3 条件で
  S7 が優先 (S2 はオシレーター無関係なので両方発火可能性, ただし**方向は同じ**で
  ポートフォリオ的に重複 → 1 シグナル統合 OK)

**S5 ∩ S6**: S5 は trend (EMA 整列), S6 は range (VA 構造). **trend ⊕ range** で
排他. ema9>21>50 と Value Area 偏在は局面として同時不可能.

**S7 ∩ S8**: S7 は急激 breakout 直後, S8 は急激値動きで形成された gap の **再テスト**
(= breakout から数 bar 後). 時系列順で別シグナル.

**S8 ∩ S9**: S8 は急激値動き (gap 形成 = body 大), S9 は body 極小. **body size**
で完全排他.

**S9 ∩ S2**: S9 は high vol + low body, S2 breakout は high vol + high body. body
size で排他.

**S4 ∩ S6**: S4 は trend 終焉 swing, S6 は range 構造.
- S4 trigger 時: 価格 new HH/LL = swing 拡張中 = range 偏在は 起こりやすいが、
- S4 は RSI 極限 (≤20 / ≥80) を要求, S6 は RSI 不問. 両方発火しても direction が
  同じ (HH 拡張 → SELL) なら portfolio 一致.

**S3 ∩ 他**: S3 は 1H bar = 5m とタイムフレーム異 → 他 5m 戦略と直接衝突なし
(発火タイミング異).

### 7.3 タイムフレーム直交

```
1H bar:    S3 (z>3σ vs 1H EMA200)
5m+1H mix: S5 (5m action + 1H EMA50 reference)
5m bar:    S1 / S2 / S4 / S6 / S7 / S8 / S9
```

5m 戦略 7 個は同一 TF だが、トリガー条件で排他 (上記 7.2).

### 7.4 Volume 軸での排他

| 戦略 | Volume 条件 |
|---|---|
| S7 ORB | Volume × 3 以上 (spike 必須) |
| S9 VSA | Volume × 3 以上 + body 小 |
| S2 Compression | Volume 不問 (BB width のみ) |
| S5 Defense | Volume 不問 |
| 他 | Volume 不問 |

S7 ∩ S9: 両方 vol×3 だが S7 は body 大 (range break) / S9 は body 小. 排他.

---

## 8. TAP 排除証明 (S4-S9)

| TAP | S4 | S5 | S6 | S7 | S8 | S9 |
|---|---|---|---|---|---|---|
| 1: 中間帯 RSI/BB%B | ❌ (極限値 ≤20/≥80 のみ) | ❌ なし | ❌ なし | ❌ なし | ❌ なし | ❌ なし |
| 2: N-bar pattern | ❌ (single swing) | ❌ なし | ❌ なし | ❌ なし | 3-bar geometry のみ (= imbalance 定義) | ❌ なし |
| 3: 反転 candle 単独 | ❌ なし | 反発確認 (binary geometry) | 内側回帰 (binary) | ❌ なし | gap 定義の一部 | ❌ なし |
| 4: 摩擦死 | RR≥2.0 | RR≥2.5 | RR≥2.0 | RR≥2.0 | RR≥2.0 | RR≥2.0 |
| 5: Score 膨張 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 |
| 6: 学術引用 bias | コメントなし | 〃 | 〃 | 〃 | 〃 | 〃 |

confidence は固定値 (S4=70, S5=72, S6=70, S7=70, S8=70, S9=70).

---

## 9. Pre-Registration 検定グリッド (有望 3 戦略 pick)

S1-S3 の BT が走行中なので、S4-S9 のうち**最も期待値が高い 3 戦略**を先行 pre-reg.

### 9.1 S5 VWAP/HTF Defense (最有望候補 #1)
**理由**: 機関投資家防衛線は明示的物理仮説. ELITE_LIVE 3 戦略 (gbp_deep_pullback 等)
の物理仮説に近い (=実証された方向性).

検定軸 (3 × 3 × 2 = 18 cells):
- pullback_min_atr: {1.0, 1.5, 2.0}
- defense_touch_atr: {0.15, 0.20, 0.30}
- defense_line: {VWAP, HTF_EMA50}

α_cell = 0.05/18 = **0.00278**

SURVIVOR (AND): EV>+1.5p, PF>1.5, WR≥45%, N≥30, Wlo>40%, p<0.00278, WF 4/4

### 9.2 S7 Opening Range Breakout (最有望候補 #2)
**理由**: 時刻 + range break + volume の 3 条件で false positive 抑制. 物理的に
1 日 1-2 回しか発火しない高純度.

検定軸 (3 × 2 × 3 = 18 cells):
- volume_spike_ratio: {2.0, 3.0, 4.0}
- open_window: {London_only, NY_only, both}
- asia_range_hours: {4, 6, 8}

α_cell = 0.05/18 = **0.00278**

SURVIVOR (AND): EV>+2.0p (RR≥2.0 で大), PF>1.5, WR≥40%, N≥20, p<0.00278, WF 4/4

### 9.3 S8 Fair Value Gap (最有望候補 #3)
**理由**: ICT/SMC コミュニティで実証多数, 純粋 geometry で TAP 排除完璧.

検定軸 (3 × 3 × 2 = 18 cells):
- gap_min_atr_mult: {0.3, 0.5, 0.7}
- reentry_lookback: {30, 50, 100}
- fill_pct: {full_fill, partial_50%}

α_cell = 0.05/18 = **0.00278**

SURVIVOR (AND): EV>+1.5p, PF>1.5, WR≥45%, N≥30, p<0.00278, WF 4/4

### 9.4 S4/S6/S9 (Secondary, S5/S7/S8 の BT 結果次第で起案)

S4 (Divergence), S6 (VA Reversion), S9 (VSA) は**第二波**として 5/3 以降に Pre-reg
LOCK 検討 (S1-S3 + S5/S7/S8 の結果統合判断).

### 9.5 9 戦略合算検定 (ポートフォリオ完成後)

各戦略 SURVIVOR 後の合算検証:
- 月次合算 EV > +1.0p / trade
- ポートフォリオ Kelly > 0.05
- 単一戦略 N 占有率 < 30% (集中リスク)
- **ペア発火相関 < 0.1** (直交性の事後検証)

---

## 10. 実装タイムライン (BT-First)

| 日付 | アクション |
|---|---|
| 2026-04-25 (LOCK) | S4-S9 pre-reg LOCK + S5/S7/S8 を主軸検定対象に確定 |
| 2026-04-26〜28 | S5/S7/S8 BT harness 実装 + 365日 BT 実行 |
| 2026-04-29 | SURVIVOR 判定 |
| 2026-04-30〜 | S4/S6/S9 Pre-reg + BT (主軸 BT 結果見て調整) |
| 2026-05-07 | Phase 1 holdout 並走 |

## 11. メモリ整合性

- [部分的クオンツの罠]: 全戦略 PF/Wilson_lo/p_welch/WF/MAE_BREAKER 完備 ✅
- [ラベル実測主義]: BT 365日実測のみで判定 ✅
- [成功するまでやる]: REJECT でも secondary 副次仮説で深掘り継続 ✅
- [XAU除外]: 全 BT で XAU 除外 ✅
- [Asymmetric Agility Rule 1]: 新エッジ主張 = pre-reg LOCK + Bonferroni 完備 ✅

## 12. 参照

- [[phase5-pure-edge-portfolio-2026-04-25]] (S1-S3)
- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1 適用)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (MAE Breaker 実装)
