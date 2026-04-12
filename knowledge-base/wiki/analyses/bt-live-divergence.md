# BT vs Live Divergence — 包括的クオンツ分析

## 1. モード別の構造的乖離

### DT(15m) vs Scalp(1m) — 摩擦構造が全く異なる

```
              BT EV      Live EV    乖離方向    摩擦/ATR
DT USD_JPY:  -0.000      N/A(混合)  ≈一致      6.7%
DT EUR_USD:  +0.440      N/A        BT楽観?    5.5%
DT GBP_USD:  +0.372      N/A        BT楽観?    8.2%
Scalp JPY:   -0.288      -1.29*     Live悪化   36.3%  ← 5.4倍
Scalp EUR:   -0.120      N/A(混合)  不明       30.6%
Scalp GBP:   -0.714      N/A        壊滅的     48.7%

* bb_rsi Live EV = -40.0pip / 79trades = -0.51pip/trade (ATR=5pip → -0.102 ATR)
```

**根本的発見: DTとScalpで摩擦構造が5.4倍異なるのに、BTの摩擦モデルが同一の定数を使用。**

---

## 2. 戦略別BT vs Live乖離マトリクス

### BT正EV → Live正EV（一致：信頼できる戦略）

| 戦略 | BT WR | BT EV | Live WR | Live N | 乖離 | 判定 |
|------|-------|-------|---------|--------|------|------|
| vol_momentum_scalp | 66.7% | +0.387 | 80.0% | 10 | **Liveが上回る** | ★★★★★ |
| vol_surge_detector | 53.8% | -0.826* | 53.8% | 13 | WR一致 | ★★★ |
| dt_sr_channel_reversal | 60.0% | +0.115 | 100% | 2 | Liveが上回る(N小) | ★★★ |
| stoch_trend_pullback | 60.0% | -0.426* | 34.8% | 23 | **Live劣化** | ★★ |

*BT EVはUSD_JPYのみ。Live EVは全ペア混合。

### BT正EV → Live負EV（乖離：BTモデルの楽観バイアス）

| 戦略 | BT WR(JPY) | BT EV | Live WR | Live N | 乖離幅 | 原因仮説 |
|------|-----------|-------|---------|--------|--------|---------|
| **bb_rsi_reversion** | **52.4%** | **-0.522** | **36.7%** | **79** | **-16pp** | 摩擦+SR+TP短縮 |
| fib_reversal | 72.7% | +0.066 | 37.1% | 35 | **-36pp** | Fib精度+v8.3前データ |
| dt_bb_rsi_mr | 64.2% | +0.156 | 42.9% | 14 | **-21pp** | RANGE判定差+摩擦 |
| orb_trap | 100% | +1.443 | 50.0% | 2 | **-50pp** | N=2判断不能 |

### BT負EV → Live負EV（一致：正しくFORCE_DEMOTED）

| 戦略 | BT EV | Live WR | Live N | 判定 |
|------|-------|---------|--------|------|
| sr_break_retest | -0.461(JPY) | 0.0% | 3 | FORCE_DEMOTED正解 |
| sr_channel_reversal | -0.813(JPY) | 0.0% | 5 | FORCE_DEMOTED正解 |
| macdh_reversal | -1.607(JPY) | 20.0% | 5 | FORCE_DEMOTED正解 |
| engulfing_bb | +0.892(JPY)* | 16.7% | 6 | *BT正だがLive壊滅 |

---

## 3. BTの6つの構造的楽観バイアス（定量的分解）

### バイアス①: Entry Price（推定 -2〜4pp WR）

```
BT: entry = df.iloc[i+1]["Open"] + spread/2 + slippage
    = 完璧な次足始値 + 固定コスト

Live: entry = OANDA real-time ask/bid
    = 変動スプレッド + OANDA処理遅延(0.02-0.05s) + fill品質

差異:
  BT: 150.000 + 0.25 + 0.40 = 150.650 (確定的)
  Live: 150.000 → ask=150.003 → fill=150.005 → 実効spread 0.50pip変動
  
影響:
  Scalp(SL=3-5pip): 0.5pip差 = SLの10-17% → WR -3〜5pp
  DT(SL=12-20pip): 0.5pip差 = SLの2.5-4% → WR -0.5〜1pp
```

**Scalpは10倍影響を受ける。** これが「同じ戦略でもScalpだけLive劣化が大きい」理由の第1因子。

### バイアス②: Spread Model — 固定 vs 変動（推定 -3〜5pp WR）

```
BT _BT_SPREAD (固定):
  USD_JPY: 0.5pip (片道0.25)
  EUR_USD: 0.4pip
  GBP_USD: 0.9pip

Live実測 (session別):
  USD_JPY London: 0.3pip / Tokyo: 0.6pip / Asia early: 1.0pip
  EUR_USD London: 0.2pip / Tokyo: 0.5pip / Asia early: 0.8pip
  GBP_USD London: 0.6pip / Tokyo: 1.0pip / Asia early: 1.5-2.0pip

問題:
  BT = 全時間帯で平均値。しかしLiveトレードの25%がAsia early(高spread)で発火。
  Asia earlyでは実効spreadがBTの2-3倍 → SLに到達しやすい → WR低下

  bb_rsi scalp:
    BT spread: 0.5pip固定 × 全トレード
    Live spread加重平均: 0.5 × 0.5(London) + 0.8 × 0.25(Tokyo) + 1.0 × 0.25(Asia) = 0.7pip
    差分: +0.2pip/trade → SL 3pipの7% → WR -2〜3pp推定
```

### バイアス③: SIGNAL_REVERSE再計算間隔（推定 -3〜8pp WR）

```
BT: _SR_RECHECK_SC = 3 bars (scalp 1m = 180s周期)
    min_hold = 5 bars (300s)
    → SR検出まで最大180-540sの遅延

Live: 30s周期で全ポジションをスキャン
    min_hold = 300s (同一)
    → min_hold超えた瞬間にSR検出 → 30s以内にclose

影響メカニズム:
  BT bar 1: エントリー → 5bar hold
  BT bar 5: hold解除。しかしSR recheckは bar 6 (next 3-bar cycle)
  BT bar 6: SR検出 → bar 6 close価格で決済 (420s後)
  
  Live: 300s hold解除 → 次の30s tickでSR検出 → 即close (310s後)
  
  時間差: BT 420s vs Live 310s = 110s余分に保有
  
  bb_rsiの場合:
    110s余分保有 × ATR(1m)=5pip × 方向不利確率50% = 2.5pipの追加損失リスク
    → RR比が0.5pip分悪化 → WR -3〜5pp

DT(15m)の場合:
    SR再計算は3bar=45min周期 vs Live 30s
    → 影響は小さい(15m足の動きはゆっくり) → WR -0.5〜1pp
```

**Scalpで最大-8pp、DTで-1pp。この差がScalpの劣化が大きい第2の理由。**

### バイアス④: TP/SL構造の差異（推定 -2〜5pp）

```
BT SL計算:
  sl_dist = tp_dist / MIN_RR (RR逆算)
  例: TP=ATR×2.2=11pip, MIN_RR=1.2 → SL=9.2pip

Live SL計算:
  sl = nearest_SR_level - ATR×0.3 (SR技術的位置)
  例: SR=3.5pip下 → SL=3.5+ATR×0.3=5.0pip
  
  差: BT SL=9.2pip vs Live SL=5.0pip → Live SLは4.2pip狭い → SL hit率上昇

Live TP(RANGE regime):
  v6.5 BB_mid Override: TP = min(BB_mid, ATR×1.2)
  BT: BB_mid Override未実装 → TP=ATR×2.2のまま

  結果: Live TPが短縮されているが、BT TPは長いまま
  → BT: TP到達時に大きな利益 (レアだが大勝ち)
  → Live: BB_mid到達で早期利確 (頻繁だが小勝ち)
  → WR差はないがPF差が発生 → 間接的にWR -1〜2pp
```

### バイアス⑤: Quick-Harvest（OANDAのTP短縮、推定 -1〜3pp）

```
BT: TP = 戦略計算値そのまま
Live (OANDA): TP = 戦略TP × 0.85 (Quick-Harvest)

影響:
  TP=11pip(BT) vs TP=9.35pip(Live)
  → TP到達確率は増加(良い) だが利益額が-15%(悪い)
  → PF低下 → 間接WR影響 -1pp
  
  ただしv6.8で0.70→0.85に緩和済み。v6.5 RANGE MRはbypass済み。
  現在の影響は限定的。
```

### バイアス⑥: Instant Death検出精度（推定 -2〜4pp）

```
BT: bar-level判定 (bar Close / High / Low)
  → SLにwickがタッチしたが Closeは内側 → BT: 生存
  → 実際にはSL注文が約定済み → Live: SL_HIT

Live: OANDA real-time tick → SL注文は即時約定
  → wick depth = ATR×0.1以上でSL hit判定

MAFE統計:
  Live LOSS 90.6%がMFE=0 (一度も順行せず)
  BT: 同等のMFE=0率を再現できているか不明
  
  BT bar-level:
    High=entry+2pip, Low=entry-4pip, Close=entry-3pip
    SL=entry-3.5pip → Close(-3)はSL内側 → BT: 生存
    しかしLow(-4)がSL(-3.5)を突破 → Live: SL_HIT
    
  BT wick判定:
    _sl_genuine_threshold = ATR×0.1 = 0.5pip
    wick depth = |Low - SL| = |-4 - (-3.5)| = 0.5pip ≥ 0.5 → SL hit
    → この場合BTも正しく検出
    
  問題: threshold=ATR×0.1は適切か？
    Live OANDA: SL注文は価格がSL水準に到達した瞬間に約定
    BTの0.1 ATR threshold: 0.5pipの「余裕」を許容 → 一部のギリギリSL hitを見逃す
```

---

## 4. DT(15m)特有の乖離要因

### DTE競合モード（v6.7、推定 -5〜12pp for specific strategies）

```
BT:
  DaytradeEngine = fallback-only (main signal==WAIT時のみ)
  → sr_fib_confluenceが非WAITなら、DTEは評価されない
  
Live (v6.7以降):
  DTE = 常に評価。score比較でmain signalを上書き可能
  → sr_fib_confluenceの score=2.0 vs gbp_deep_pullback score=3.5
  → DTE勝利 → sr_fib_confluenceの信号がgbp_deep_pullbackに置換
  
影響:
  sr_fib_confluence: BT WR=64.3% → Live WR=28.9% (36pp乖離)
  この36ppの一部(推定10-15pp)はDTE競合による信号置換が原因
  
  Live: sr_fib_confluenceが発火するはずのタイミングで
        DTE(gbp_deep_pullback等)が勝利 → entry_typeが変わる
        → sr_fib_confluenceのN減少 + 残ったトレードは弱いscore
        → WR低下
```

### RANGE TF Block（v6.7 D1、DTのみ影響）

```
BT: _DT_TREND_STRATEGIES のRANGEブロックは実装済み（app.py DT_QUALIFIED同期）
Live: demo_trader.py D1で同一ブロック

乖離: 小（ロジック同一）。ただしレジーム判定自体の精度差:
  BT: detect_market_regime(df) — 完全なDF
  Live: detect_market_regime(df) — リアルタイム部分DF (最新バーが未確定)
  → レジーム判定の1-bar遅延がLiveで発生 → TF戦略がRANGE初期に発火する可能性
```

### TREND_BULL MR免除（v8.1、DTのみ）

```
BT: v8.1ロジックがBTに反映されているか不明
    app.py compute_daytrade_signal → DT_QUALIFIED に依存
    TREND_BULL判定はcompute_daytrade_signal内ではなくdemo_trader.py内
    
Live: demo_trader.py L2468-2483 で TREND_BULL + not _is_mr_entry → block
    
乖離:
  BT: TREND_BULLでもTF戦略が発火 → BT WR低下(TREND_BULL WR=15%)
  Live: TREND_BULLでTF戦略ブロック → Live WRはブロック分だけ改善
  → この場合 **LiveがBTより良い** はず
  
  しかし実際は Live WR < BT WR → TREND_BULLブロック以外の要因が支配的
```

---

## 5. ペア別の乖離構造

### USD_JPY — 最もBT/Live一致度が高い

```
DT BT: 285t WR=59.6% EV=-0.000 PF=1.00
Live (post-cut混合): bb_rsi N=79 WR=36.7%, stoch N=23 WR=34.8%

乖離分析:
  DT: BT EV≈0 → Liveで小幅負 → 一致度高い
  Scalp: BT EV=-0.288 → Live bb_rsi WR=36.7% → BTも負 → 方向一致
  
  USD_JPYはBT摩擦モデルが最も現実に近い（スプレッド0.5pip固定 ≈ Live平均0.6pip）
```

### EUR_USD — BTが最も楽観的

```
DT BT: 199t WR=69.8% EV=+0.440 PF=1.63 Sharpe=3.629 ★★★★★
Live: dt_bb_rsi_mr N=14 WR=42.9% (DT唯一の有意なN)

乖離リスク:
  BT Sharpe=3.629は極めて高い → 過適合の可能性
  session_time_bias BT WR=76.9% → Live N=0 → 検証不能
  htf_false_breakout BT WR=100% → Live N=0 → 検証不能
  
  EUR_USDのBTが特に楽観的な理由:
    1. BT摩擦 = EUR固定値(0.4pip) vs Live = London 0.2pip / Asia 0.8pip → 分散が大きい
    2. EUR_USDはBTデータ期間に強い上昇トレンド → session_time_bias(SELL EUR)が過剰適合
    3. htf_false_breakout WR=100%はN小の偽陽性典型例
```

### GBP_USD — BT高PFだがフラッシュクラッシュリスク未反映

```
DT BT: 269t WR=68.0% EV=+0.372 PF=1.49 Sharpe=2.997 ★★★★
Live: orb_trap N=2 WR=50% (唯一のPAIR_PROMOTED DT)

乖離リスク:
  1. BT 55日間にフラッシュクラッシュイベントなし → テールリスク未反映
  2. gbp_deep_pullback BT WR=100% → Live N=0 → 完全未検証
  3. GBPのBT Sharpe=2.997は「平穏な55日」の産物
  
  もし55日間にGBPフラッシュクラッシュ(2016年型-9%, 2022年型-4.5%)が
  含まれていたら、Sharpeは大幅に低下するはず
```

---

## 6. 最も深刻な乖離の根本原因

### BTモデルの「6つの構造的楽観バイアス」影響度まとめ

| バイアス | Scalp影響 | DT影響 | 修正難易度 |
|---------|----------|--------|----------|
| ① Entry Price (固定 vs リアルタイム) | **-3〜5pp** | -0.5〜1pp | 低 |
| ② Spread Model (固定 vs 変動) | **-3〜5pp** | -1〜2pp | **中（最優先）** |
| ③ SR再計算間隔 (3bar vs 30s) | **-3〜8pp** | -0.5〜1pp | 低 |
| ④ TP/SL構造差 (RR逆算 vs SR技術) | -2〜3pp | -2〜3pp | 中 |
| ⑤ Quick-Harvest (BT無し vs Live 0.85x) | -1〜2pp | -1〜2pp | 低 |
| ⑥ Instant Death検出 (bar vs tick) | **-2〜4pp** | -0.5〜1pp | 高 |
| **合計** | **-14〜27pp** | **-5.5〜10pp** | |

**Scalpの乖離(14-27pp)がDT(5.5-10pp)の2-3倍大きい理由は、バイアス①②③⑥がSL/ATR比に比例するから。**

Scalp SL=3-5pip → 0.5pipの差がSLの10-17%
DT SL=12-20pip → 0.5pipの差がSLの2.5-4%

### 「BTを信じていいか」の判断基準

```
信頼度 = f(乖離リスク)

DT戦略 (乖離5.5-10pp):
  BT WR=70% → Live推定 WR=60-65% → まだ正EVの可能性高い
  BT WR=55% → Live推定 WR=45-50% → BEV付近で危険
  → DT BT WR>60%なら信頼してよい

Scalp戦略 (乖離14-27pp):
  BT WR=70% → Live推定 WR=43-56% → BEV_WR(34%)は超えるが薄い
  BT WR=60% → Live推定 WR=33-46% → BEV付近で危険
  → Scalp BT WR>70%のみ信頼可能。それ以下は摩擦負けリスク
```

---

## 7. 乖離を踏まえた戦略ポートフォリオの再評価

### DT戦略（BT乖離5.5-10ppを加味）

| 戦略 | BT WR | 乖離補正WR | BEV_WR | 判定 |
|------|-------|----------|--------|------|
| session_time_bias EUR | 76.9% | **67-71%** | 34% | ★★★★★ 確実に正EV |
| htf_false_breakout EUR | 100% | **90-95%** | 34% | ★★★★ ただしN小注意 |
| orb_trap JPY | 100% | **90-95%** | 34% | ★★★★ ただしN小注意 |
| session_time_bias JPY | 70.8% | **61-65%** | 34% | ★★★★ 正EV |
| gbp_deep_pullback GBP | 100% | **90-95%** | 38% | ★★★★ ただしN小注意 |
| london_fix_reversal GBP | 75.0% | **65-70%** | 38% | ★★★ 正EV |
| xs_momentum EUR | 69.0% | **59-64%** | 34% | ★★★ 正EV |
| dt_bb_rsi_mr JPY | 64.2% | **54-59%** | 34% | ★★ 薄いエッジ |
| sr_fib_confluence EUR | 72.0% | **62-67%** | 34% | ★★★ ただし本番36pp乖離あり |

### Scalp戦略（BT乖離14-27ppを加味）

| 戦略 | BT WR(JPY) | 乖離補正WR | BEV_WR | 判定 |
|------|-----------|----------|--------|------|
| vol_momentum JPY | 66.7% | **40-53%** | 34% | ★★ 辛うじて正EV |
| fib_reversal JPY | 72.7% | **46-59%** | 34% | ★★ 不確実 |
| bb_rsi JPY | 52.4% | **25-38%** | 34% | **✗ BEV以下の可能性** |
| bb_rsi EUR | 83.3% | **56-69%** | 40% | ★★★ EURなら正EV |

---

## 8. BTモデルv3への改善ロードマップ

```
現在 (Friction Model v2):
  固定spread + 固定slippage + wick判定 + SR 3bar周期

Friction Model v3 (提案):
  Phase A: Dynamic Spread (時間帯×ペア → 可変spread)    ← 最大インパクト
  Phase B: SR 1bar周期化 (180s → 60s scalp, 900s DT)   ← Scalp改善
  Phase C: RANGE TP Override移植 (v6.5 BB_mid)          ← DT改善  
  Phase D: Quick-Harvest反映 (TP × 0.85)               ← 全体改善
  Phase E: DTE競合モード反映 (v6.7)                     ← sr_fib乖離修正

期待効果:
  v2 乖離: Scalp -14〜27pp, DT -5.5〜10pp
  v3 乖離: Scalp -5〜10pp, DT -2〜4pp (推定)
  → BT結果の信頼性が3倍向上
```

## Related
- [[friction-analysis]]
- [[bb-rsi-reversion]]
- [[lessons/index]] — lesson-bt-endpoint-hardcoded
- [[changelog]] — v6.5 Range Exit, v6.7 DTE Competition, v8.3 Confirmation Candle
