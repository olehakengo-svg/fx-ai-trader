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

## Track 5: Risk Management (要点)

### 5.1 Kelly Criterion

```
Kelly fraction f* = (p × b - q) / b
  p = win rate
  q = 1 - p (loss rate)
  b = avg win / avg loss

例: WR=55%, avg win/avg loss = 1.5
  f* = (0.55 × 1.5 - 0.45) / 1.5 = 0.25 = 25%
```

### 5.2 Kelly Half ルール (我々の運用)

実用的に Kelly の 1/2 で運用:
- DD 半分以下に
- volatility of returns 半分以下に
- ただし期待 growth は 75% (Kelly Full の)

我々の Live Kelly = **-17.97%** は **負 EV**。lot を 0.5× してもさらに損失加速する数学。
→ Live lot 増設は Kelly > 0 が前提条件。

### 5.3 Sharpe / Sortino / Maximum DD

- Sharpe = (annual return - risk-free) / annual std → Quant の業界標準
- Sortino = Sharpe の downside std 版 → 上振れ vol を penalty しない
- Maximum DD = peak から trough の最大下落率
- Monte Carlo DD = ランダムサンプルでの DD 分布 → "worst case" 推定

### 5.4 月利 100% 目標 (¥454,816/月) の数学

```
複利前提:
  1 年で 12 倍 = 月利 100% × 12 = 1200%/年 (年利)
  Sharpe ≈ 5+ (極めて aggressive、機関 hedge fund も到達困難)

必要条件:
  - WR > 55%
  - Risk:Reward > 2:1
  - Trade frequency 100+/day (lot 微小)
  - DD < 30% を Kelly Half で達成
  - Slippage / spread / friction を吸収できる edge

→ 達成困難だが不可能ではない。Kelly が +20%/trade レベル必要 (現在 -17.97%)。
```

### 5.5 教訓 (Track 5)

- Kelly < 0 で lot 増設は数学的に破滅
- Kelly Half ルールは sustainable な lot 増加の標準
- 月利 100% は Kelly +20%/trade 級の edge が必須 (現在は逆方向)
- Phase 3 で edge を構築できれば Kelly Half を経由して目標到達可能

---

## 総括: Edge Reset プロジェクトとの接続

| Track | 我々の Phase との直結 |
|---|---|
| 1 Microstructure | `friction_model_v2.py` (Phase 1.7) の根拠 |
| 2 Liquidity | `pre-reg-pullback-to-liquidity-v1` / `pre-reg-asia-range-fade-v1` (Phase 1.7) の mechanism |
| 3 Quant Edge | `strategy-mechanism-audit-2026-04-26.md` (Phase 1.7) の判定基準 |
| 4 Session × Pair | `friction_model_v2.py` の session/mode multiplier の数値根拠 |
| 5 Risk Management | Kelly Half / Live Kelly -17.97% の数学的解釈 |

→ 本学習ノートは Phase 1.7 までの実装の **理論的基礎** を体系化したもの。
新規実装はないが、今後の意思決定 (Phase 1.5 _POLICY tuning, Phase 3 BT, ...) で常時参照可能。

## 次セッション以降の深化候補

- Track 1: Order book depth の実測 (OANDA depth API)
- Track 2: Round number での WR を Live data で実測 (USDJPY 150.000 等)
- Track 3: 365日 BT 結果に対し friction v2 で再シミュレーション
- Track 4: Session × pair × strategy の 3D WR matrix (`empirical_validator.aggregate_3d`)
- Track 5: Monte Carlo DD simulator 構築

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
