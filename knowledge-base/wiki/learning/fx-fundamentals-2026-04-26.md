# FX Fundamentals — 改めて学び直し (2026-04-26)

**Date**: 2026-04-26 開始
**Trigger**: ユーザー「FXの基本を改めて勉強しよう」(Edge Reset Phase 1.7 後)
**Approach**: Hybrid (KB 章立て + 各章を Live data / KB で検証)
**Phase**: Track 1+2 を深く、Track 3-5 は要点 (本セッション) → 次セッションで深化

## 目次

- [Track 1: Market Microstructure](#track-1-market-microstructure)
- [Track 2: Liquidity & Price Formation](#track-2-liquidity--price-formation)
- [Track 3: Quant Edge の本質](#track-3-quant-edge-の本質)
- [Track 4: Session × Pair 特性](#track-4-session--pair-特性)
- [Track 5: Risk Management](#track-5-risk-management)

---

## Track 1: Market Microstructure

### 1.1 FX 市場は OTC (Over-the-Counter) — 中央取引所がない

- 株式 (NYSE/Nasdaq) は中央集権的 order book + 取引所マッチング
- FX は **数百の銀行 / dealer / ECN が分散**して bilateral に取引
- 「USD/JPY = 150.123」という単一価格は存在せず、**LP ごとに微妙に異なる quote**
- 我々が見る Live price は broker (OANDA) の aggregated best bid/ask

### 1.2 流動性チェーン (上→下)

```
Tier 1 インターバンク (10 行程度)
    JP Morgan / Citi / Deutsche / UBS / HSBC / Goldman Sachs / Barclays / RBS / BNP / Credit Suisse
    ↓
Tier 2 Prime Broker (PB)
    hedge fund や大口 fund に Tier 1 アクセスを提供
    ↓
Tier 3 Liquidity Provider (LP)
    Retail broker に流動性供給、spread 報酬
    ↓
Retail Broker (OANDA / IG / FXCM ...)
    リテール顧客向け markup spread
    ↓
我々 (End user)
```

各層で **spread が markup** される。リテール spread = wholesale spread + broker margin。

### 1.3 Bid / Ask Spread の正体

Spread は単純な broker の利益ではなく、**Liquidity Provider の risk premium**:

- LP は限られた在庫で逆 selection (informed trader の餌食) リスクを取る
- 流動性が薄い時間帯 (Asia early) や news 前後は in-flow flow が読めない → spread 拡大
- 主要 pair (USDJPY, EURUSD) は flow 厚い → spread 狭い (0.5-0.7 pip)
- Cross pair (GBPUSD など) は flow 薄い → spread 広い (1.3+ pip)
- Exotic pair (TRY/USD など) は flow 極薄 → spread 数十 pip

### 1.4 我々の Live data での検証 — friction-analysis.md

| Pair | Spread | Slippage | RT Friction | 解釈 |
|---|---|---|---|---|
| USD_JPY | 0.7 | 0.5 | 2.14 | Tier 1 で最も流動性厚い (BOJ + Fed flow) |
| EUR_USD | 0.7 | 0.5 | 2.00 | 世界最大の通貨対 (40% of FX volume) |
| GBP_USD | 1.3 | 1.0 | **4.53** | 流動性 USDJPY/EURUSD の半分以下、volatility 高め |
| EUR_JPY | 1.0 | 0.5 | 2.50 | Cross pair、流動性 major の 60% |
| GBP_JPY | 1.5 | 0.8 | 3.50 | "Beast" — 流動性中だが volatility 極端 |

**重要な気づき**: GBP_USD の 4.53pip RT friction は、戦略の edge が +5pip/trade を超えなければ Live で負ける。
我々の Phase 5 BT で「6/9 DEAD」となった戦略の多くは、edge が friction を超えなかった可能性が高い。

### 1.5 Slippage 発生機序

Market order を出した瞬間に何が起きているか:

1. Broker の OMS が order を LP に flush
2. LP の order book で best ask (買い) / best bid (売り) を消化
3. Order が大きい / vol 不足 / news 直後 → 複数 levels から fill = avg price 悪化
4. Filled price - Quoted price = Slippage

リテールでの典型値:
- 平常時: 0.3-0.5 pip slippage (best case)
- News 直後 (30 sec): 5-10 pip slippage
- Asia early (00-02 UTC): 1-2 pip (流動性 dead)
- Stop loss 大量発動時: 10+ pip (連鎖反応)

### 1.6 我々の Kelly -17.97% の structural 説明

Live N=259 で WR 39.0%, EV -0.83 pip/trade。これを microstructure 視点で分解:

```
Trade economics:
  Average win:       +X pip (TP hit 時)
  Average loss:      -Y pip (SL hit 時)
  RT friction:        2.0-4.5 pip (pair による)
  Net EV per trade = WR × X - (1-WR) × Y - friction

  我々の Live (FX-only):
    WR = 39.0%
    Average win - friction = +α
    Average loss + friction = -β  (friction は loss 側で実質拡大)
    Net = 0.39 × α - 0.61 × β  =  -0.83 pip
```

**結論**: friction が「win 側を縮め、loss 側を拡げる」構造を作っている。
edge = α + β > friction × 1.5 程度ないと、Wilson lower bound 50% を超えても Live で負ける。

### 1.7 教訓 (Track 1)

- Spread は broker の利益ではなく LP の risk premium。流動性の薄い時間/pair で必然的に拡大
- リテールの friction 2-4pip は数学的事実。edge がそれを超えなければ負ける
- Phase 1.7 で実装した `friction_model_v2.friction_for()` は **この microstructure を反映**した cost lookup
- → Phase 3 BT は必ず `friction_for()` 経由で cost 計算 (一律 BT_COST=1.0 は使わない)

---

## Track 2: Liquidity & Price Formation

### 2.1 価格は誰が動かしているか

| 主体 | 比率 | 性質 |
|---|---|---|
| インターバンク flow | ~50% | 機関の hedging、position adjustment |
| HFT / Algo (LP, 専業) | ~30% | tick-by-tick price discovery、market making |
| Hedge fund / asset manager | ~15% | 中長期 carry, macro trade |
| Central bank intervention | <5% (但し離散的) | BOJ / SNB など、瞬間的に巨大 |
| Retail | <5% | 我々を含む |

**重要**: 我々 (retail) の order flow は価格にほぼ影響しない。
我々は **他の参加者の flow に反応する立場**。
edge を作るには「機関の flow が予測可能になる構造的状況」を捕捉する必要。

### 2.2 流動性供給と消費

```
Limit Order (供給):
  「150.000 で 1M 買う」(まだ約定していない)
  → 他の市場参加者の market order と match される受け皿
  → 価格を動かさず、単に order book に置かれる

Market Order (消費):
  「すぐ売る、市場価格で」
  → Order book 上の best bid (limit order) を即座に消費
  → 消費した分 spread が拡がるか、次の level まで価格が動く
```

**Liquidity zone の形成**:
- 心理的 round number (00, 50) → limit orders 集中
- Daily / Weekly high/low → stop loss orders 集中
- Fibonacci 38.2 / 61.8 → 機関 algo の limit orders
- Session high/low → 短期 stop loss orders

### 2.3 Stop Hunt / Liquidity Sweep のメカニズム

機関 algo が retail / weak hand stops を狙う典型 pattern:

```
状況: USD/JPY 150.000 直下に多くの BUY stop loss が集中している
       (= retail SELL position の多くが 150.000 を SL に置いている)

Step 1: 大手 algo が order book を観察、stop cluster を「発見」
Step 2: 軽く 150.020 まで push (50-100M 程度の market BUY)
Step 3: 150.000 の BUY stops が連鎖発動 (retail forced cover)
Step 4: 流動性吸収 → 大手 algo は 150.020-050 で SELL position 構築
Step 5: 価格は元の 149.900 付近に戻る (retail は SL hit で損失確定)
```

**これが Phase 3 pre-reg `pullback_to_liquidity_v1` の標的**。
Stop hunt 後の rejection (下髭 40%+) は流動性吸収完了の signal。

### 2.4 News Flow vs Technical Flow

| 項目 | News Flow | Technical Flow |
|---|---|---|
| 発生原因 | FOMC, CPI, NFP, intervention | Order book imbalance, technical level touch |
| Vol 反応 | 瞬間的に 5-10× 拡大 (1-30 sec) | 通常 1-2× |
| Predictability | 反応方向は predictable、overshoot は predictable | 流動性 zone なら predictable |
| Trade window | News + 30sec 〜 5min | News window 外 |
| 戦略との接続 | News-vol expansion 戦略 (Phase 3 候補) | TF / MR / BR の主戦場 |

**重要**: News window 30min 前後は **technical analysis が無効化される**ため、entry 禁止が望ましい。

### 2.5 我々の戦略への接続 (mechanism thesis 確認)

#### `pullback_to_liquidity_v1` (TF, Phase 3 pre-reg LOCK)

> Mechanism: HTF trend が確立した方向に対し、M15 swing low/high への pullback 局面では
> 流動性供給により価格が再加速する。

Track 2 の言葉で再記述:
- HTF trend = インターバンク flow が一方向に偏っている (大手機関の hedging direction)
- M15 swing low/high = retail の利食い + 反対方向の stop cluster (流動性 zone)
- Pullback touch = 流動性消費イベント
- Rejection (下髭 40%+) = 流動性吸収完了、機関 flow 再開
→ Stop hunt の構造を逆手に取って便乗

→ **VALID mechanism thesis** (`strategy-mechanism-audit-2026-04-26.md` で VALID 判定済 orb_trap と同類)。

#### `asia_range_fade_v1` (MR, Phase 3 pre-reg LOCK)

> Mechanism: アジア時間 (02-06 UTC) の低 vol 環境で形成された range の high/low touch は、
> 構造的に流動性吸収後に range 中央へ回帰する。

Track 2 の言葉で再記述:
- アジア時間 = インターバンク flow が低い (London/NY 銀行が出席前)
- 低 vol = trend formation flow が弱い、range 形成 dominance
- Range high/low touch = 短期 retail / weak algo による overshoot
- Touch + rejection = LP が touch 後に逆方向 limit orders で吸収
- 中央回帰 = 構造的な MR 性質

→ **VALID mechanism thesis** (流動性メカニズムが明示的)。

### 2.6 教訓 (Track 2)

- 価格は機関の flow で動く。retail が edge を持つのは「機関 flow が予測可能な瞬間」のみ
- Liquidity zone (round numbers / swing high-low / Fib) で機関 flow が反応
- Stop hunt は **構造**であり、捕捉できれば edge になる (`pullback_to_liquidity_v1` の根拠)
- News window は technical analysis 無効、原則 entry 禁止
- 既存戦略の多くが「中間帯 RSI/Stoch + AND」(TAP-1) は **流動性 zone 不在** で edge 構造的にない

---

## Track 3: Quant Edge の本質 (要点)

### 3.1 Edge の 3 分類

| 種類 | 内容 | 我々が取れるか |
|---|---|---|
| **Information edge** | 他より早く / 正確に情報を得る | ❌ 機関のみ (Bloomberg terminal, prime broker info) |
| **Structural edge** | 市場構造 (carry, MR in low vol, stop hunt) を活用 | ✅ 主戦場 — `pullback_to_liquidity_v1`, `asia_range_fade_v1` |
| **Risk premium** | 不快なリスクを取る対価 (vol selling, gold in crisis) | ⚠️ 部分的 — vol selling は急変で破滅、gold は v8.4 で停止済 |

→ 我々は **Structural edge のみ** を狙うべき。ここが Phase 3 設計の核。

### 3.2 BT 楽観バイアス 6 因子 (`bt-live-divergence.md` ベース)

1. Entry price: BT は次足 open + 固定 cost / Live は変動 spread
2. Spread model: 固定値 / Live は session 変動 (Asia +50%, news +500%)
3. Signal_Reverse 再計算遅延: BT 3bar=180s / Live 30s
4. HTF データ取得: M5→resample / Live は別 source
5. Fill 品質 + SL hunt 対策
6. Label bias (BB_MID, BREAKEVEN, MTF alignment)

**結論**: BT で +0.5 pip/trade EV → Live で 0 〜 -0.5 pip/trade に低下しうる。
mechanism thesis なき戦略は BT 楽観バイアスで「見せかけの edge」が出るだけ。

### 3.3 Survivorship Bias

「365 日 BT で勝った戦略を選ぶ」 = 過去最適化 = HARKing
→ Phase 1.7 の pre-reg LOCK は本日付で閾値固定して post-hoc 変更禁止 = 構造的に防止

### 3.4 教訓 (Track 3)

- Information edge は諦める (機関の領分)
- Structural edge のみ。mechanism thesis 必須
- BT 楽観バイアスは avoidable な部分 (friction model v2) と avoidless な部分がある
- pre-reg LOCK で HARKing 防止

---

## Track 4: Session × Pair 特性 (要点、`friction_model_v2` ベース)

### 4.1 セッション

| Session | UTC | 特性 | Friction multiplier |
|---|---|---|---|
| Sydney | 21-00 | 流動性最低 | 1.60 |
| Asia early | 00-02 | 流動性 dead zone | 1.55 |
| Tokyo | 02-07 | Asia 主要 | 1.45 |
| London open | 07-12 | London 銀行参加 | 1.00 (基準) |
| Overlap LN-NY | 12-16 | 流動性最大 | 0.85 |
| NY | 14-21 | NY 主要、close 前 vol | 1.20 |

### 4.2 ペア種別

- **Major (USD ペア)**: USDJPY, EURUSD, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD — 流動性厚い
- **Minor / Cross**: EURJPY, GBPJPY, EURGBP — 流動性中、cross 計算で spread 拡大
- **Exotic**: USDTRY, USDZAR など — リテールでは扱わない

### 4.3 Carry trade

- 高金利通貨 (AUD, NZD, EM) を買い、低金利通貨 (JPY, CHF) を売る
- Swap rate (rollover interest) で利益確定
- 危機時に急逆転 (LTCM 1998, 2007 sub-prime, 2020 COVID)
- 我々の戦略では明示的に取らない (1-6h hold が多く swap 影響軽微)

### 4.4 教訓 (Track 4)

- Asia 早朝 / Sydney は entry 禁止 (流動性 dead)
- Overlap LN-NY (12-16 UTC) が最も edge 出やすい時間帯
- Major pair (USDJPY, EURUSD) で friction 最小 → Phase 3 BT の primary

---

## Track 5: Risk Management (深化版 — Track ④ imperative-wozniak セッション執筆)

> **執筆セッション**: `fx-edge-reset-imperative-wozniak.md` (本日 2026-04-26 PM)
> **Live data 出所**: ローカル `demo_trades.db` (2026-04-02 〜 2026-04-24, 22.5日間, 16.57 trades/day)
> **scope**: FX のみ (XAU除外, `feedback_exclude_xau.md` 適用), N=373 closed trades (LIVE+SHADOW)
> **計算ソース**: `modules/risk_analytics.py` (kelly_fraction, monte_carlo_ruin, calculate_var_cvar, strategy_correlation)
> **位置付け**: Track ① (microstructure) と Track ② (liquidity) が「edge はどこに / なぜあるか」を扱うのに対し、Track ④ は「edge があったとして何 lot で運用し、DD をどう制御するか」を扱う

---

### 5.1 Kelly Criterion — 数式・歴史・我々の Live 実測

#### (a) 一般論
Kelly (1956) は対数効用最大化問題の解として `f* = (p×b - q) / b` を導出した。

```
p = win rate, q = 1-p, b = avg_win / avg_loss
f* > 0 ⇔ edge = p×b - q > 0
```

**重要な前提**: edge ≤ 0 のとき Kelly は **正の解を持たない** (fraction は 0 以下に張り付く)。`risk_analytics.py:208` の `full_kelly = max(0.0, full_kelly)` がこの clipping を実装。

#### (b) 我々の Live 実測 (FX, N=373, XAU除外)

```
全 FX 集約:
  N=373, WR=30.3% (Wilson95% [25.9%, 35.1%])
  avg_win  = +12.84 pip
  avg_loss = -7.53 pip → b = 1.705
  edge = p×b - q = 0.303 × 1.705 - 0.697 = -0.1807
  full_kelly = max(0, -18.07%) = 0%   ← clipping
  half_kelly = 0%, quarter_kelly = 0%
```

→ 既存ノート末尾と memory `feedback_partial_quant_trap.md` で参照される **「Live Kelly -17.97%」は edge 値 -0.1807 ≈ -18.07% に対応**。Kelly fraction 自体は clipping により 0% で、**lot を「Kelly に従って」減らすことすら不可能** な領域にある。

> **数値整合性メモ** (ラベル実測主義 `feedback_label_empirical_audit.md`):
> 既存ノート §1.6 の `Live N=259, WR=39.0%, EV=-0.83 pip` は本セッション (2026-04-26 PM, demo_trades.db 直クエリ) では再現せず:
> - 現 DB の同条件 (FX, XAU除外, status=CLOSED) は **N=373, WR=30.3%, EV=-1.34 pip**
> - 任意の単一 `entry_time >= cutoff` でも N=259, WR=39.0% は再現不可 (試行: 04-08〜04-18 すべて WR<30%)
> - 推定原因: §1.6 執筆時点 (本日午前) のスナップショット差 + 4/24 までの直近 trades 追加で WR 悪化
> - 本 Track 5 の数値は **直 DB クエリ (ローカル `demo_trades.db`, 2026-04-02〜04-24)** に基づく実測値。§1.6 の数値が古い可能性が高いが、本セッションは Track 5 の scope のため §1.6 修正は別セッション (Track ① 担当 curried-ritchie / valiant-dahl) に委譲。

**Sub-segment 別 Kelly edge** (XAU除外):

| Segment | N | WR (Wilson95) | b | edge | Kelly Full |
|---|---|---|---|---|---|
| LIVE only (is_shadow=0) | 36 | 50.0% [34.5, 65.5] | 1.023 | +0.0117 | 1.14% |
| SHADOW only (is_shadow=1) | 337 | 28.2% [23.7, 33.2] | 1.779 | -0.2166 | **0%** (clip) |
| USD_JPY (全) | 194 | 36.6% [30.1, 43.6] | 1.531 | -0.0738 | **0%** |
| EUR_USD (全) | 91 | 17.6% [11.1, 26.7] | 3.656 | -0.1814 | **0%** |
| GBP_USD (全) | 76 | 32.9% [23.4, 44.1] | 1.164 | -0.2880 | **0%** |
| EUR_JPY (全) | 9 | 11.1% [2.0, 43.5] | 2.025 | -0.6639 | **0%** (N不足) |

**示唆**:
- LIVE only の N=36 は Wilson 下限 34.5% が Bonferroni を通る臨界以下 (`feedback_partial_quant_trap.md` 参照)。**positive Kelly に見えるのは N 過少のノイズ**。
- SHADOW (N=337) が「真の戦略期待値」に近い。edge -21.66% は GBP_USD の friction 4.53pip (`friction-analysis.md`) を吸収できていない構造を反映。
- EUR_USD は b=3.656 と odds が大きいが WR=17.6% で edge 負。「稀に大勝、多くは小負け」型は Kelly では不利。

#### (c) Phase 4d-II / friction-analysis との照合
- friction-analysis: GBP_USD RT friction = 4.53pip → 上の per-pair edge -28.80% は 「GBP_USD 平均敗北 -11.69pip / 平均勝利 +13.61pip / WR 32.9%」 と無矛盾 (friction が EV のおおよそ 4 pip 分を持っていく)。
- Phase 4d-II nature pooling (memory obs 81): primary 全 NULL → 戦略レベルで positive Kelly が出るセル不在。本節の per-pair Kelly が全て負である事実と整合。

---

### 5.2 Kelly Half / Quarter — 数学的根拠と我々への適用

#### (a) 一般論
Full Kelly は **対数効用最大化** だが「期待 vol が極端に高い」「分布の尾を過大評価する」問題があり、実務では Half (1/2) や Quarter (1/4) を採用する。代表的な性質 (Thorp 2006; MacLean, Thorp & Ziemba 2010):

| Sizing | Growth rate | std of growth | Median DD | 破産確率 (尾) |
|---|---|---|---|---|
| Full Kelly (f*) | 100% | 100% | 1× baseline | 高 |
| Half Kelly (f*/2) | **75%** | **50%** | **0.5×** | 大幅低下 |
| Quarter Kelly (f*/4) | 44% | 25% | 0.25× | ほぼゼロ |

→ Half Kelly は「成長率を 25% だけ犠牲にして、std と DD を半減」させる構造。

#### (b) 我々への適用 (`risk_analytics.py:209-210`)
production はデフォルトで `recommendation = "half_kelly"` を返す (L219)。`compute_risk_dashboard` 経由で `/api/risk/dashboard` に乗る。

しかし **Kelly が clipping で 0% である現状では Half/Quarter は無意味** (0 の半分も 0)。意味を持つのは「edge を作って Kelly > 0 になった後」。

#### (c) Sustainability チェック
仮に Phase 3 で edge=+10% (Kelly Full=10%) を構築できた場合の Half Kelly 適用:
- Full Kelly: 1 trade あたり資金の 10% を risk
- Half Kelly: 5%
- 1000pip 資本 → 1trade あたり 50pip までの loss 許容
- 平均 loss 7.53pip (現状) → 6.6 trades 連続負けで Half Kelly DD limit に到達

→ **edge を作るのが先決**。Kelly Half は「edge ありき」のツール。

---

### 5.3 Sharpe / Sortino / DSR (多重検定考慮)

#### (a) 一般論
- **Sharpe** (Sharpe 1966): `(mean_return - rf) / std_return`、業界標準。年率化は `× √N_periods_per_year`。
- **Sortino** (Sortino & Price 1994): 分母を **downside-only std** に置換。上振れ vol を penalty しない、より「実損リスク」志向。
- **DSR (Deflated Sharpe Ratio)** (Bailey & Lopez de Prado 2014): 多重検定 (HARKing) を考慮した補正版。M 個の戦略を試して最良を選んだ場合、観測 Sharpe を `√(2 ln(M)/N)` 程度割引く必要。

#### (b) 我々の Live 実測 (FX, N=373)

```
Per-trade metrics (FX, XAU除外, N=373):
  mean_pnl = -1.34 pip
  std_pnl  = 18.27 pip
  downside_std = 14.92 pip (loss-only)

Sharpe (per-trade) = -1.34 / 18.27 = -0.0733
Sortino (per-trade) = -1.34 / 14.92 = -0.0898

年率化 (16.57 trades/day × 252 trade days = 4175 trades/year):
  Annualized Sharpe = -0.0733 × √4175 ≈ -4.74
  Annualized Sortino = -0.0898 × √4175 ≈ -5.81
```

**警告**: per-trade Sharpe を √N で年率化する慣行は **trade 間 IID 仮定**に依存。我々の戦略は同時刻に複数 mode が発火しうるため、daily-resampled Sharpe の方が保守的。

**戦略別 Sharpe (per-trade)**:

| Strategy mode | N | EV (pip) | std | Sharpe/trade |
|---|---|---|---|---|
| `scalp` | 93 | +3.77 | 16.38 | **+0.230** ✅ |
| `scalp_eur` | 58 | +1.12 | 18.20 | +0.061 |
| `scalp_5m_gbp` | 37 | -1.12 | 7.42 | -0.151 |
| `scalp_5m` | 34 | -2.11 | 4.30 | -0.491 |
| `scalp_5m_eur` | 21 | -1.54 | 3.81 | -0.405 |
| `daytrade` | 64 | -5.89 | 19.45 | -0.303 |
| `daytrade_gbpusd` | 39 | -5.50 | 35.10 | -0.157 |
| `daytrade_eur` | 11 | -7.30 | 6.98 | -1.046 |

→ **`scalp` (USD_JPY) のみ正の Sharpe (+0.230/trade)**、年率換算 +14.9 (ただし N=93 で DSR 補正前)。他 8 戦略は全て負 Sharpe。

#### (c) DSR 補正での生存検定
試行戦略数 M = 9 (本表の 9 modes), N = 93 (scalp の N) の場合:
```
Haircut ≈ √(2 ln(9) / 93) = √(0.0473) = 0.217 (per-trade Sharpe)
scalp 観測 Sharpe = 0.230
DSR-adjusted Sharpe = 0.230 - 0.217 = 0.013 (≈ 0)
```

→ **scalp の Sharpe は M=9 の多重検定を考慮するとほぼ消滅**。`feedback_partial_quant_trap.md` の警告 (PF だけ見る → Bonferroni を通過しない) と同じ構造。Track ⑤ (mellow-sky) の Survivorship bias 議論と接続。

---

### 5.4 Drawdown — 実測 + Monte Carlo

#### (a) 一般論
- **Maximum DD**: 観測 equity curve の peak-to-trough 最大下落 (pip 絶対値 or %)
- **Recovery time**: Max DD から peak まで戻るのに要した bar/trade 数
- **Pain index**: 全期間での平均 DD (DD 累積積分 / 期間)
- **Monte Carlo DD**: 過去 PnL から bootstrap resample → 多数の equity curve を生成 → DD 分布を観察

`risk_analytics.py:73 monte_carlo_ruin` がこれを実装 (10,000 paths × 500 trades, replace=True, seed=42)。

#### (b) 我々の Live 実測 (initial=1000pip, ruin=50% DD)

**実測 (現データの sequential equity curve, N=373)**:
- Realized Max DD = **965.5 pip** (= 開始資本の 96.5% — 既に ruin 寸前)

**Monte Carlo (10,000 paths, 500-trade horizon, seed=42)**:

| Segment | Ruin prob | Median Max DD | Worst-99% DD |
|---|---|---|---|
| ALL FX (N=373) | **85.5%** | 820 pip | 1703 pip |
| LIVE only (N=36) | 86.1% | 820 pip | 2258 pip |
| SHADOW (N=337) | 89.9% | 853 pip | 1585 pip |
| USD_JPY (N=194) | 57.4% | 547 pip | 1255 pip |
| EUR_USD (N=91) | 53.2% | 517 pip | 1018 pip |
| GBP_USD (N=76) | **99.6%** | 1762 pip | 3109 pip |
| EUR_JPY (N=9) | 100% | 3016 pip | 3509 pip |

**示唆**:
- 戦略 portfolio 全体で **次 500 trade の ruin 確率 85.5%**。これは「lot を半分にする」程度では救えない (Kelly clipping 領域だから)
- GBP_USD 単独で MC ruin 99.6%。`friction-analysis.md` で「GBP_USD は limit-only 強制」と既に対処されているが、それでも残存 friction 4.53pip が edge 不在で一方的損失化
- USD_JPY が最も健全 (ruin prob 57.4%) だが、それでも positive ではない

#### (c) Phase 5 BT との照合
Phase 5 BT (Phase4d-II 結果, memory obs 80-81): primary 全 NULL、BREAKOUT joint WEAK、survivor=0。本節の MC ruin 85.5% と整合 — **戦略 portfolio に inherent edge 不在 → 将来 PnL の bootstrap 分布も負方向に重心**。

---

### 5.5 Correlation Matrix と "False Diversification"

#### (a) 一般論
9 戦略 × 5 pair の portfolio で見かけ上は分散しているが、**戦略間 PnL correlation が高ければ実効自由度は低下** する。Markowitz (1952) の portfolio variance 公式:

```
σ_portfolio² = Σ wᵢ²σᵢ² + 2 Σ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
```

→ ρ→1 で分散効果消失、ρ→-1 で分散効果最大、ρ=0 で √N 削減。

#### (b) 我々の Live 実測 (`risk_analytics.strategy_correlation`, modes with N≥10)

|corr|≥0.3 を flag した結果 (5 ペアのみ flagged, 残り 31 ペア低 correlation):

| Pair | corr | direction |
|---|---|---|
| daytrade × daytrade_gbpusd | **-0.344** | negative |
| daytrade_eur × daytrade_gbpusd | +0.313 | positive |
| daytrade_eur × scalp_5m | +0.304 | positive |
| daytrade_eur × scalp_5m_eur | -0.457 | negative |
| daytrade_gbpusd × scalp_eur | **-0.751** | negative |

**示唆**:
- 36 pair のうち 31 pair (86%) で |corr|<0.3 → **戦略間は概ね uncorrelated**
- 2 pair で moderate negative correlation (daytrade_gbpusd × scalp_eur = -0.75) → 構造的 hedge
- これは **edge があれば** 良いニュース (実効自由度が高い → DD を抑制できる)
- **edge がなければ** 単に「異なる戦略で別々に負ける」だけ — 現状

#### (c) lessons / Phase 4 との照合
- `lesson-toxic-anti-patterns-2026-04-25.md` (TAP-1/2/3): 中間帯 RSI/Stoch + AND は edge 構造的に不在 → correlation と無関係に portfolio 負
- Phase 4d nature pooling (obs 81): BREAKOUT 性戦略 joint WEAK → correlation matrix を見るより前に、戦略個々の edge が課題

---

### 5.6 月利 100% (¥454,816/月) 目標の sustainability 数学

#### (a) 必要条件の分解
複利前提で 1 ヶ月 +100%、年率 +1200%。これを達成する Sharpe / Kelly の数学:

```
Annual return target = 12.0 (1200%)
Annual std (assuming target Sharpe S):
  return / std = S → std = 12.0 / S

例: S=3 (機関 hedge fund 一流) → annual std = 4.0 (400%)
    S=5 (極めて稀) → annual std = 2.4 (240%)
    S=2 (現実的) → annual std = 6.0 (600%) — 月で破産しうる
```

→ **S ≥ 5 が事実上必須** (S=2 では std が大きすぎ、Kelly Half でも DD 制御不能)。

#### (b) Live 実測との gap
現状 (FX, N=373):
- Annualized Sharpe = -4.74
- Required Sharpe = +5.0
- **Gap = +9.74 (Sharpe 単位)** ≒ 「正負反転 + 業界トップ層へ」
- Kelly edge: 現状 -18.07% → 目標 +20% (Kelly Full)、**gap = +38pp**

これは「微調整」では到達不能。`mtf-rustling-candle` 計画 (memory obs 76) の Track B closure と R2 suppress/boost が示すように **戦略生成構造そのものの再設計** (Phase 3) が必要。

#### (c) sustainability の前提条件 (要 Phase 3 で達成)
1. **Kelly Full ≥ +10%** (Half で +5%) — edge p×b - q ≥ 0.10
2. **WR ≥ 50%** または **b ≥ 2.0** — どちらか (両方なら理想)
3. **Trade frequency**: 現状 16.57/day × 22.5日 = 373 trades は十分。問題は edge
4. **Per-trade friction ≤ 1pip** (現状 USD_JPY 2.14pip, GBP_USD 4.53pip) — Track ① で議論

→ 1-2 が **Phase 3 mechanism-driven edge re-build** の主目標。3-4 は Phase 1-2 で実装済 (`friction_model_v2.py`, R2 routing)。

---

### 5.7 Risk Premium と Tail Risk — 我々が **取らない** べき edge

#### (a) Edge 三分類 (Track ⑤ mellow-sky でも扱われる予定)
- **Information edge**: 機関の領分、retail 不可
- **Structural edge**: 流動性 zone, stop hunt, MR in low vol → **我々の主戦場**
- **Risk premium**: vol selling, carry, crisis insurance — 平時に小利、危機で巨損

#### (b) Risk premium 戦略の歴史的 tail event
| 戦略 | 平時 | Crisis | 結果 |
|---|---|---|---|
| Carry trade (AUD/JPY long) | +5%/year swap | -30% in 1 day (2008) | LTCM 1998, COVID 2020 |
| Vol selling (FX option short) | +1pip/day theta | -100pip in 30sec (2015 SNB) | Tail crash |
| Mean reversion in trend | + small | trend で死亡 | 2020 USD/JPY 大円安 |

#### (c) 我々の戦略は risk premium を取っているか?
- `scalp_*` (5m / 1m): hold time < 1h → swap rate 影響軽微、tail vol exposure は短時間限定
- `daytrade_*` (1h / 15m): hold time 1-6h → tail event 中の DD risk あり
- BUT: **explicitly に risk premium を取る戦略は無い** (vol selling や crisis hedge は実装外)

→ 現状は「risk premium を意図せず受け取り」「edge は構造的不在」という最悪パターン。Phase 3 では **Structural edge のみ** を狙うべき (`pullback_to_liquidity_v1`, `asia_range_fade_v1` の方向)。

---

### 5.8 Live Kelly -17.97% の Track ④ 視点総括 — 5.1-5.7 統合

#### Risk Mgmt 視点での失敗構造

```
Track ① (microstructure):  friction が edge を上回る
Track ② (liquidity):       liquidity zone を活用していない (TAP-1/2/3)
                              ↓
Track ④ (本 Track):        edge ≤ 0 → Kelly clip 0
                              ↓
            lot 縮小は EV 改善せず (-1.34 pip/trade のまま)
                              ↓
            MC ruin 85.5% (500-trade horizon, 50% DD)
                              ↓
         Sharpe -4.74 (annualized) — 全戦略中 1 つ (scalp) のみ正
                              ↓
            DSR 補正で scalp Sharpe ≈ 0 — 多重検定で消える
```

#### 数学的にやってはいけないこと
1. **lot を上げて挽回**: edge<0 で lot↑ は破産確率↑のみ
2. **lot を半分にして "Half Kelly 風"**: Kelly が clip 0 なので意味なし、損失速度が半減するだけ
3. **戦略を増やして分散**: correlation 既に低い (86% pair で |r|<0.3)、増やしても負 EV を分散するだけ
4. **過去の勝ち戦略 (scalp) に集中**: DSR 補正で Sharpe ≈ 0、N 不足で false positive リスク

#### 数学的に唯一許される行動 = **Phase 3 の実行**
- mechanism-driven edge を 1 つでも構築 (`pullback_to_liquidity_v1` or `asia_range_fade_v1`)
- それが Wilson 95% 下限で Kelly > 0 を示すまで lot 増設禁止
- pre-reg LOCK で HARKing を防止 (Phase 1.7 で済)
- friction_model_v2 で cost-adjusted EV を BT で測定 (Phase 1.7 で済)

#### 月利 100% gap の最終定量
| 項目 | 現状 (Live) | 目標 (月利 100%) | Gap |
|---|---|---|---|
| WR | 30.3% | ≥50% | +20pp |
| EV/trade | -1.34 pip | ≥+0.5 pip | +1.84 pip |
| Kelly edge | -18.07% | ≥+10% | +28pp |
| Sharpe (annual) | -4.74 | ≥+5.0 | **+9.74** |
| MC ruin (500-trade) | 85.5% | <5% | -80pp |

→ どの metric も「微調整」レンジを越えている。**Phase 3 の戦略生成構造そのものの再設計**が必要 (memory obs 76: mtf-rustling-candle Section 9-11 の R2 suppress/boost authorization と同方向)。

#### 残課題 (次セッション以降に持ち越し)
本セッションで **未消化** な深化候補:
1. **portfolio_kelly** (`risk_analytics.py:758`) を使った per-strategy lot allocation の optimization (現状 lot 固定)
2. Daily-resampled Sharpe の実測 (per-trade Sharpe の独立性仮定の妥当性検証)
3. `compute_risk_dashboard` (`risk_analytics.py:409`) の Render 本番 API (`/api/risk/dashboard`) 出力との照合 (本セッションはローカル DB のみ)
4. tail risk の explicit シミュレーション (3-σ event での DD 分布)
5. R2 suppress/boost (memory obs 77) 適用後の Kelly 再計算 (Phase 3 完了後)

→ いずれも **Phase 3 完了後に再 audit** すべき。本 Track の現時点での結論は変わらない: **edge を作る前に risk metric を最適化しても無意味**。

---

## 総括: Edge Reset プロジェクトとの接続

| Track | 我々の Phase との直結 |
|---|---|
| 1 Microstructure | `friction_model_v2.py` (Phase 1.7) の根拠 |
| 2 Liquidity | `pre-reg-pullback-to-liquidity-v1` / `pre-reg-asia-range-fade-v1` (Phase 1.7) の mechanism |
| 3 Quant Edge | `strategy-mechanism-audit-2026-04-26.md` (Phase 1.7) の判定基準 |
| 4 Session × Pair | `friction_model_v2.py` の session/mode multiplier の数値根拠 |
| 5 Risk Management | Kelly clip 0% / MC ruin 85.5% / 月利100% gap +9.74 Sharpe (深化版で定量化, imperative-wozniak セッション) |

→ 本学習ノートは Phase 1.7 までの実装の **理論的基礎** を体系化したもの。
新規実装はないが、今後の意思決定 (Phase 1.5 _POLICY tuning, Phase 3 BT, ...) で常時参照可能。

## 次セッション以降の深化候補

- Track 1: Order book depth の実測 (OANDA depth API)
- Track 2: Round number での WR を Live data で実測 (USDJPY 150.000 等)
- Track 3: 365日 BT 結果に対し friction v2 で再シミュレーション
- Track 4: Session × pair × strategy の 3D WR matrix (`empirical_validator.aggregate_3d`)
- Track 5: ✅ MC DD simulator 実装済 (5.4) / 残: portfolio_kelly per-strategy lot allocation, daily-resampled Sharpe, Render `/api/risk/dashboard` 照合, tail-event simulation, R2 適用後 Kelly 再計算 — 詳細は §5.8 末尾

## References

### 我々のプロジェクト KB
- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]] — meta-lesson
- [[strategy-mechanism-audit-2026-04-26]] — Track 3 の判定枠組み
- [[pre-reg-pullback-to-liquidity-v1-2026-04-26]] — Track 2 mechanism 適用例
- [[pre-reg-asia-range-fade-v1-2026-04-26]] — Track 2 mechanism 適用例
- [[friction-analysis]] — Track 1, 4 の数値根拠
- [[bt-live-divergence]] — Track 3 の 6 因子
- [[lesson-toxic-anti-patterns-2026-04-25]] — TAP-1/2/3 の定義

### 関連 commit (本日)
- `51b8cd2` Phase 0 — MTF disable
- `72f1583` Phase 1 Task 1+2 — OANDA HTF + apply_policy plumbing
- `435f1ec` Phase 1.7 — Empirical Validator + Friction v2 + Audit + Pre-reg LOCK

### 学術引用 (本ノート参照分)
- Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum"
- Lo & MacKinlay (1988) "Stock Market Prices Do Not Follow Random Walks"
- Kelly Jr (1956) "A New Interpretation of Information Rate" (Kelly criterion 原典)
- Sharpe (1966) "Mutual Fund Performance"
- Sortino & Price (1994) "Performance Measurement in a Downside Risk Framework"
- Thorp (2006) "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market"
- MacLean, Thorp & Ziemba (2010) "The Kelly Capital Growth Investment Criterion"
- Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio" (DSR — 多重検定補正)
- Markowitz (1952) "Portfolio Selection" (correlation 分散効果)
