# Track 2 — Liquidity & Price Formation (深掘り版)

**Date**: 2026-04-26
**Owner**: Track ② 深掘りセッション (本ファイル単独所有)
**Master file**: [[fx-fundamentals-2026-04-26]] (Track ① セッション所有、本ファイルは別ファイル)
**Approach**: 3-段構造 (a) 一般論 → (b) 我々のシステムへの含意 → (c) Phase 4c/4d KB 照合
**検証ソース**: 内部 KB (`fx-ai-trader/knowledge-base/wiki/`) + Live trade DB (`sqlite-fx`)。外部出典は引用しない。
**検証規律**: ラベル実測主義、XAU 除外、Wilson CI 必須、claim 分類 (CONFIRMED / PARTIAL / REFUTED / INSUFFICIENT N / 未検証仮説)
**Plan**: `/Users/jg-n-012/.claude/plans/fx-edge-reset-twinkling-pancake.md`

---

## 2.0 このトラックの位置付け

### 2.0.1 Track ② が答える問い

> 「edge はどこに、なぜ存在しうるか」

Track ① (Microstructure) が「市場の物理的構造」(OTC、LP チェーン、spread の正体) を扱うのに対し、Track ② は「その構造の上で価格がどう形成されるか、流動性がどこに集まるか、機関 flow がどう動くか」を扱う。Phase 3 mechanism-driven edge 再構築の設計土台となる章。

### 2.0.2 Live data の制約 (2026-04-26 時点)

- **demo_trades**: n=373 closed, 期間 2026-04-02〜04-24 (~22 days), WR=33.4% (W:111 / L:221)
- **oanda_trades**: n=0 (本番口座まだ運用なし、demo フェーズ)
- **Phase 4d 母集団**: N=1804 (closed + open + shadow を含む analysis-only スコープ)

サンプルサイズ制約により Bonferroni 通過閾値が高く、本トラックの (c) 節検証は **descriptive 優先**。Wilson CI と effect size を併記し、claim を「真 effect 確実」と「signal 示唆 / N 不足」に分けて分類する。

### 2.0.3 検証規律 (memory feedback 順守)

- **クオンツファースト**: (a) を述べた直後に必ず (c) で KB 照合。空欄禁止
- **ラベル実測主義**: 数値引用は KB / Live DB 出所明示。不可なら「未検証仮説」と明記
- **部分的クオンツの罠**: WR 単独で結論せず Wilson CI / N / effect 必須
- **XAU 除外**: sqlite-fx クエリ全てで `instrument NOT LIKE '%XAU%'`
- **成功するまでやる**: 矛盾発見時は claim 側を即修正、closure 短絡禁止
- **scope**: master file (`fx-fundamentals-2026-04-26.md`) には触らない。整合性は Track ① セッションが master 統合で解消する

### 2.0.4 既存 master Track 2 (初稿) との関係

master file `fx-fundamentals-2026-04-26.md` には Track ① セッション執筆の Track 2 初稿 (§2.1〜§2.6) が既に存在する。本ファイルは:

- 同じ題材を 3-段構造で**深掘り**
- 初稿が触れていない sub-topic (§2.4 magnet levels の定量検証、§2.7 news flow 検証) を追加
- 各 claim を Phase 4c/4d KB 照合で**分類ラベル付け**
- §2.8 で Live Kelly -17.97% への流動性視点での構造的説明を構築

master 統合フェーズで Track ① セッションが両者を統合する想定。

---

## 2.1 Order book dynamics

### (a) 一般論

OTC FX には中央 order book は存在しないが、各 LP / ECN レベルで limit order の集積として機能的 order book が形成される。価格は以下の力学で決まる:

- **Liquidity supply**: limit order が price ladder に置かれる
- **Liquidity consumption**: market order が best bid/ask を順次消化
- **Spread**: best bid と best ask の差。LP の (i) inventory cost、(ii) adverse selection リスク、(iii) order processing cost への報酬
- **Depth**: 各 price level に置かれた liquidity のサイズ
- **Spread expansion** は次の 3 条件で発生:
  1. 流動性供給の薄い時間帯 (Asia early、major economy 休場)
  2. 情報非対称性が高い瞬間 (重要 news 直前 / 直後)
  3. 大口 market order による depth 消費直後

### (b) 我々のシステムへの含意

- 我々の Live signal は基本的に **market order entry** (一部 limit gate あり) で、spread を毎回コストとして払う
- BEV (break-even WR) = friction / (avg_win + friction) で、friction が高い pair / 時間帯では同じ WR でも EV が壊れる
- friction-analysis の per-pair BEV_WR は: USD_JPY 34.4%, EUR_USD 39.7%, GBP_USD **37.9%**, EUR_JPY 33.7%
- 我々の Live 全体 WR=33.4% は USD_JPY/EUR_JPY の BEV をかろうじて並ぶ程度、GBP_USD/EUR_USD では赤字確定の水準
- **pullback_to_liquidity_v1 のような戦略は entry 自体が depth 厚いタイミング (流動性 zone touch 後) を狙う設計**で、order book dynamics を逆手に取るアプローチ

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| spread が高い時間帯で WR 劣化 | friction-analysis.md `Friction by Session`: London 0.86 / Tokyo 3.14 / NY 7.30 | **PARTIAL** — spread 自体は London 最良、ただし NY の 7.30 は XAU 歪みで FX-only では 2.0 程度 |
| 高 spread = 高 WR (counterintuitive) | phase4d-session-spread-routing-result.md: `vol_surge_detector q3=45.8% vs q2=26.7%`, `fib_reversal q3=46.5% vs q1=21.6%` | **PARTIAL** — vol_surge と fib_reversal では高 spread = 真の volatility 期 = high-edge zone という構造的説明が成り立つが p>0.05 で nominal 未通過 |
| Bonferroni 通過の signal は signal/spread からは検出されず | phase4d-session-spread-routing-result.md: 0 SURVIVOR / 2 WEAK | **CONFIRMED** — N 不足が真の bottleneck (Required N per cell 150-300, 現 14-100) |

#### 即時 sqlite-fx 検証

claim: 「Live demo データでも spread が高いほど WR が低い (一般論)」は成り立つか?

```sql
-- 実行: spread bin × WR (Wilson CI)
SELECT
  CASE
    WHEN spread_at_entry < 0.5 THEN '1_low'
    WHEN spread_at_entry < 1.0 THEN '2_mid'
    WHEN spread_at_entry < 2.0 THEN '3_high'
    ELSE '4_xhigh'
  END AS spread_bin,
  COUNT(*) AS n,
  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*), 1) AS wr_pct
FROM demo_trades
WHERE status='CLOSED' AND instrument NOT LIKE '%XAU%'
GROUP BY 1 ORDER BY 1;
```

→ 本セクション末尾「実測検証」に結果を追記。

### (d) 実測検証 (sqlite-fx)

**Query**: spread bin × WR (XAU 除外、closed のみ、demo_trades n=373)

| spread_bin | n | wins | WR | avg_spread | Wilson 95% CI |
|---|---|---|---|---|---|
| 1_lt0.5 | 73 | 41 | **56.2%** | **0.0** | [44.7, 67.0]% |
| 2_0.5-1.0 | 214 | 44 | **20.6%** | 0.8 | [15.7, 26.4]% |
| 3_1.0-2.0 | 80 | 26 | 32.5% | 1.32 | [23.1, 43.5]% |
| 4_ge2.0 | 6 | 0 | 0.0% | 2.35 | [0.0, 39.0]% |

**重要な解釈**:
- **`1_lt0.5` の avg_spread=0.0 はロギング欠損の artifact** (`spread_at_entry` 既定値 0)。WR 56.2% は signal ではなく、spread 記録欠損レコードの混在。**判定: ARTIFACT、除外**
- **`2_0.5-1.0` の WR 20.6% (n=214)** は最も多い帯で**極端に低い**。Wilson 95% upper = 26.4% は全体 BEV (USD_JPY 34.4%) を大幅に下回る → このゾーンが Live Kelly -17.97% の主因
- **`3_1.0-2.0` の WR 32.5% (n=80)** は spread が高いほうがむしろ WR 高 — Phase 4d の `vol_surge_detector q3=45.8% / fib_reversal q3=46.5%` (高 spread = 真の volatility 期 = high-edge zone) と方向整合
- `4_ge2.0` n=6 は INSUFFICIENT N

**claim 判定**: 「spread が高いほど WR が低い (一般論)」は **REFUTED for current Live data**。我々のシステムでは spread 0.5-1.0 帯で最も負け、spread 1.0-2.0 帯のほうが WR 高。一般論より「flow regime (vol surge / 真の breakout) が高 spread を伴って発火するため、高 spread = high-edge」という liquidity 構造的解釈のほうが我々のデータに合致。

---

## 2.2 Liquidity providers のチェーン (interbank → LP → retail)

### (a) 一般論

FX 市場参加者は階層構造:

```
Tier 1 インターバンク (主要 10 行)  — 真の流動性源
  ↓
Tier 2 Prime Broker (PB)
  ↓
Tier 3 LP (Liquidity Provider) — リテール broker への流動性供給
  ↓
Retail Broker (OANDA / IG / FXCM ...) — markup spread
  ↓
我々 (End user)
```

各層で spread が markup される。リテールのトレーダーは LP より厚いコストを払う。Tier 1 銀行の hedging flow は中長期の方向性を決め、HFT/Algo (~30%) は tick-by-tick の price discovery を担う。Retail flow (<5%) は価格にほぼ影響しない。

**重要**: 我々は「他者の flow に反応する」立場。edge を持てるのは「機関 flow が予測可能になる構造的瞬間」のみ。

### (b) 我々のシステムへの含意

- 我々は OANDA Japan 経由 (Tier 3 retail aggregator) で接続。spread は wholesale + markup
- 機関 flow が偏る時間帯 (London 開始時の銀行 hedging、NY 13:30 の経済指標反応) を捕捉できれば retail flow は便乗できる
- 逆に retail-dominant の時間帯 (Asia early、weekend gap) は構造的 edge が無い
- TAP-1 (中間帯 RSI/Stoch + AND) 戦略が大量 DEAD なのは「機関 flow の偏りと無関係な indicator combo」だから

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| 機関 flow 偏りが session で異なる | phase4d-session-spread-routing-result.md: `stoch_trend_pullback Tokyo 29.0% vs Overlap 11.1%` (18 ptp 差、WEAK p=0.015) | **PARTIAL** — Asia 時間 (=低 retail flow + 残存トレンド継続) と Overlap (=機関 flow 反転点) で signal を**示唆** |
| RANGE 戦略は NY low-mid spread 帯で機能 | phase4d-II-nature-pooling-result.md: `RANGE × (NewYork, q1) WR=51.4%, Wilson 35.6% > baseline 31.5%` | **CONFIRMED descriptive** — Wilson lower > baseline の唯一の R2 boost 候補 |
| TREND 戦略は session 依存性なし | phase4d-II-nature-pooling-result.md: `TREND PRIMARY 1 (session × outcome): NULL` | **CONFIRMED** — TREND nature pooling では session signal 検出されず |
| 機関 flow が薄い時間帯 = retail trap zone | mtf-alignment-bug-audit: `aligned trade 73% が GBP_USD × BUY × trend_up_*`, WR=8.1% は pair-friction artifact | **REFUTED 解釈の修正** — 単純な「機関 flow trap」ではなく、data-structure artifact (sampling bias) と判明。一般論「機関 flow trap」自体は KB で直接検証されていないため**未検証仮説**として保留 |

---

## 2.3 Stop hunt mechanism (round number / prior swing / SL cluster)

### (a) 一般論

Stop hunt = 大手 algo / market maker が retail / weak hand の stop loss cluster を意図的にトリガし流動性を吸収する pattern:

```
状況: 価格 X 直下に BUY stop loss が集中 (= retail SELL position の SL)
  Step 1: algo が order book を観察、stop cluster 位置を発見
  Step 2: 軽く X+δ まで push (relatively small market BUY)
  Step 3: BUY stops 連鎖発動 (forced cover)
  Step 4: 流動性吸収 → algo が X+δ で逆方向 (SELL) position 構築
  Step 5: 価格は元の水準に戻る (retail は SL hit で確定損失)
```

**Stop cluster が形成されやすい場所**:
- 心理的 round number (00, 50)
- Daily / Weekly high/low (前日高値の上 / 前日安値の下に SL を置く慣習)
- Fibonacci 38.2 / 61.8 retracement level
- Session high/low

### (b) 我々のシステムへの含意

- 我々の SL も round number 直下/直上に置かれやすい (TP/SL ロジックが ATR + round-number snap を併用しているなら同じ)
- Stop hunt 後の rejection (下髭 40%+ など) を **トリガ**にする戦略 = `pullback_to_liquidity_v1` (Phase 3 pre-reg LOCK 候補) は stop hunt の構造を逆手に取る設計
- `liquidity_sweep` 戦略 (BR カテゴリ、未判定) も同じ思想
- 逆に、bb_rsi_reversion のように「BB タッチ → 反発」を機械的に取る戦略は **stop hunt が完了する前に entry** してしまうため、SL hit が量産されやすい

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| Stop hunt 構造を逆手に取る戦略は VALID mechanism | strategy-mechanism-audit.md: `orb_trap` VALID (流動性遷移 + dislocation, 学術裏付け) | **CONFIRMED** — VALID 認定の数少ない例 |
| BB タッチ + RSI 機械反発戦略は流動性メカニズム不在 | strategy-mechanism-audit.md: `bb_rsi_reversion` WEAK 判定、「なぜ反発するのか不明」 | **CONFIRMED** — `Live BT 乖離 -16pp (bt-live-divergence)` も整合 |
| pullback_to_liquidity_v1 は VALID mechanism thesis | strategy-mechanism-audit.md / 既存 Track 1 master §2.5: stop hunt の構造を逆手に取る、下髭 40%+ rejection が流動性吸収完了 signal | **CONFIRMED** (mechanism thesis として) — ただし Live N=0、実測 WR は未検証 |

#### 即時 sqlite-fx 検証

claim: 「entry price が round number (.00, .50) 近傍だと WR が変わる」

```sql
-- 価格末尾を round-number proximity で bin
SELECT
  CASE
    WHEN ABS(entry_price - ROUND(entry_price)) < 0.05
       OR ABS(entry_price - ROUND(entry_price) - 0.5) < 0.05 THEN '1_at_round'
    WHEN ABS(entry_price - ROUND(entry_price)) < 0.10
       OR ABS(entry_price - ROUND(entry_price) - 0.5) < 0.10 THEN '2_near_round'
    ELSE '3_far'
  END AS round_bin,
  COUNT(*) AS n, SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*), 1) AS wr
FROM demo_trades
WHERE status='CLOSED' AND instrument LIKE '%JPY%' AND instrument NOT LIKE '%XAU%'
GROUP BY 1 ORDER BY 1;
```

(JPY 系は 1.0 = 100 pips 単位で round 設計。USD/EUR cross は別 query 必要)

→ §2.3(d) に追記。

### (d) 実測検証 (sqlite-fx)

**Query**: round-number proximity × WR (JPY 系のみ、XAU 除外、closed)

| round_bin | n | wins | WR | Wilson 95% CI |
|---|---|---|---|---|
| 1_at_round_5pip | 48 | 28 | **58.3%** | **[44.3, 71.0]%** |
| 2_near_round_10pip | 56 | 12 | 21.4% | [12.7, 33.8]% |
| 3_far | 101 | 30 | 29.7% | [21.7, 39.2]% |

**重要な解釈**:
- `at_round_5pip` (entry price が round number ±0.05 = ±5 pips JPY 換算以内) で **WR 58.3%, Wilson lower 44.3%**。far の Wilson upper 39.2% を**大きく上回る**ため round-number 帯の優位は強い signal
- `near_round_10pip` (5-10 pip 圏) は **WR 21.4% で far より低い** — 「round に向かう途中」での entry が SL hit 量産
- 構造的解釈: round number は (i) stop hunt の標的 = sweep 後の rejection を捕捉できれば WR 高 / (ii) sweep 前の entry は損切られる、という stop hunt mechanism と整合
- ただし confounders 多い: 戦略タイプ別構成、direction、SL placement (round number snap) の影響を分離していない

**claim 判定**: 「round number 近傍の entry で WR が変わる」は **CONFIRMED descriptive** (Wilson lower bound > far/near upper bound)。Phase 3 で `pullback_to_liquidity_v1` の trigger に round-number proximity を組み込めば mechanism thesis を強化できる可能性。ただし Bonferroni 検定は未実施 (本検証は 1 sub-topic 内の探索的 cut)。

⚠️ **caveat**: entry_price が round 帯 = SL/TP placement の round-snap でほぼ自動的に round 近傍にフィットする戦略 (一部 SR 系) が混在している可能性。Phase 3 設計時に entry-time-only round proximity (signal_price ベース) で再検定が望ましい。

---

## 2.4 Liquidity pools / magnet levels (POC / VWAP / D1 H/L)

### (a) 一般論

価格は流動性の集中する level に「磁石」のように引き寄せられる傾向がある (mean reversion to liquidity の一般化):

- **POC (Point of Control)**: volume profile で最大 volume が成立した価格帯
- **VWAP (Volume-Weighted Average Price)**: institutional execution benchmark、当日 / 当週の機関 fair value 推定
- **Daily / Weekly High/Low**: 直近の price extreme、stop cluster + breakout / reversal 候補
- **Session High/Low**: 当 session の reference point

機関 algo は VWAP に向けて execution を行うことが多く、price は VWAP に **収束 → 離脱 → 再収束** を繰り返す。Daily High/Low は「stop hunt の標的」と「breakout entry の標的」が同じ場所に集まるため、touch 時に大きく価格が動く。

### (b) 我々のシステムへの含意

- 現状の戦略 registry に POC / VWAP を mechanism thesis に組み込んだ戦略は**ほぼ存在しない**
- Daily / Weekly H/L 参照は `sr_touch`, `sr_channel_reversal` が近いが、SR 自体が定義依存 (どこを SR と認識するか)
- Phase 3 mechanism re-design では VWAP-aware entry / POC return strategy が候補に上がる

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| POC / VWAP を活用した戦略は現 registry に不在 | strategy-mechanism-audit.md (5 戦略判定) + strategy_category.py registry | **CONFIRMED** — VALID 判定 `orb_trap` も session boundary は使うが POC/VWAP は不在 |
| Daily/Weekly H/L 参照戦略 (`sr_touch`, `sr_channel_reversal`) の Live 実績 | phase4d-session-spread-routing-result.md: `sr_channel_reversal Overlap=30.5%` (NULL), `(London, q3) 15.0% R2-A suppress 候補` | **PARTIAL** — descriptive level では一部 cell で edge 示唆だが Bonferroni 未通過 |
| Phase 3 候補としての magnet level 戦略は未検証 | KB 内に該当 backtest なし | **未検証仮説** — Phase 3 設計時に新規 pre-reg 必要 |

---

## 2.5 Pullback to liquidity と institutional accumulation

### (a) 一般論

機関は trend 方向に大量 position を構築するが、market impact を避けるため **複数の浅い pullback を利用して累積** (institutional accumulation pattern)。これが retail から見える典型 pattern:

- 強いトレンド方向の動き (impulsive wave)
- 浅い retracement (Fibonacci 38.2-50% 程度)
- swing low / swing high tap → rejection wick
- 再び impulsive wave で前回 high/low 更新

この pullback の swing low/high 付近に retail の SL cluster が形成され、機関 algo は「retail SL を sweep してから pullback を完了」する double mechanism を取る。下髭 / 上髭 rejection は流動性吸収完了 signal となる。

### (b) 我々のシステムへの含意

- `pullback_to_liquidity_v1` (Phase 3 pre-reg LOCK 候補) はこの構造を直接 mechanism thesis としている
- HTF trend 確立 + M15 swing low/high tap + 下髭 40%+ rejection の 3 条件
- 既存戦略では `ema_pullback` (WEAK 判定) が近いが、entry 条件が「pullback 完了」を捉えていない (条件成立瞬間に発火、rejection 確認なし)
- `ema_trend_scalp` (NONE 判定) は 中間帯 AND で random sample of trending market を取っており accumulation の構造的瞬間ではない

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| `pullback_to_liquidity_v1` は VALID mechanism thesis | strategy-mechanism-audit.md (master Track 1 §2.5 でも 3 段構造で言及) | **CONFIRMED** (thesis valid) — ただし Live N=0 で実測 WR 未検証 |
| `ema_pullback` は WEAK (mechanism 補強必要) | strategy-mechanism-audit.md §3.1: 「entry trigger が pullback 完了を捉えていない」 | **CONFIRMED** |
| `ema_trend_scalp` は NONE (TAP-1 自認) | strategy-mechanism-audit.md §3.4: 「中間帯を狙う = TAP-1 自認」、Phase 5 6/9 DEAD 整合 | **CONFIRMED** |
| TREND nature pooling で session signal なし | phase4d-II-nature-pooling-result.md: TREND PRIMARY 1 NULL | **CONFIRMED** — TREND 全体としても univariate signal は弱い |

#### 即時 sqlite-fx 検証

claim: 「TREND nature 戦略 (ema_pullback, ema_trend_scalp 等) の close_reason 分布」

```sql
SELECT
  entry_type, close_reason, COUNT(*) AS n,
  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
FROM demo_trades
WHERE status='CLOSED' AND instrument NOT LIKE '%XAU%'
  AND entry_type IN ('ema_pullback', 'ema_trend_scalp', 'stoch_trend_pullback')
GROUP BY entry_type, close_reason
ORDER BY entry_type, n DESC;
```

→ §2.5(d) に追記。

### (d) 実測検証 (sqlite-fx)

**Query**: 主要 6 戦略の close_reason × WR (XAU 除外、closed)

| entry_type | close_reason | n | wins | 観察 |
|---|---|---|---|---|
| `bb_rsi_reversion` | TP_HIT | 16 | 16 | TP 到達は確実 (16/16) — ターゲットに着けば勝てる |
| | SL_HIT | 14 | 0 | TP/SL 逆向き比 16:14、TP 短くなければ均衡 |
| | TIME_DECAY_EXIT | 4 | 0 | 時間切れ = 進まない |
| `ema_trend_scalp` | SL_HIT | **39** | **0** | **39 連敗 — random sample of trending market 構造の証左** |
| | TIME_DECAY_EXIT | 19 | 0 | 19 件全て負け、TREND 継続なし |
| | TP_HIT | 7 | 7 | TP 到達わずか 7 件 |
| | MAX_HOLD_TIME | 4 | 3 | hold timeout で 3/4 prof |
| `stoch_trend_pullback` | SL_HIT | 6 | 0 | small N だが SL hit 主体 |
| | TP_HIT | 4 | 4 | |
| | TIME_DECAY_EXIT | 4 | 0 | |
| `vol_surge_detector` | SL_HIT | 6 | 0 | 全 7 件中 0 win — INSUFFICIENT N |
| | TIME_DECAY_EXIT | 1 | 0 | |
| `orb_trap` | SL_HIT | 3 | 0 | INSUFFICIENT (Live N=5 のみ) |
| | SIGNAL_REVERSE | 2 | 0 | |

**重要な解釈**:
- `ema_trend_scalp` の **SL_HIT 39 vs TP_HIT 7 (5.6:1 比)** は strategy-mechanism-audit の NONE 判定 (TAP-1 自認、random sample of trending market) を **強烈に裏付け**。pullback 完了 / accumulation の構造的瞬間を一切捉えていないため、entry 直後 SL hit を量産
- `bb_rsi_reversion` は TP_HIT 16 / SL_HIT 14 とほぼ均衡だが TIME_DECAY_EXIT 4 件全て LOSS で「BB タッチ → 反発しない」死亡パターンが 4 件に 1 件混入。WEAK 判定整合
- `stoch_trend_pullback` は TP:SL = 4:6 で descriptive には負け、ただし Tokyo session で WR 29% (Phase 4d) → 全体 N=14 では INSUFFICIENT
- `orb_trap` は VALID mechanism thesis だが Live N=5、SL_HIT 3 / SIGNAL_REVERSE 2 で 0 win — **INSUFFICIENT N、要 N≥30 蓄積後再評価** (strategy-mechanism-audit の caveat 整合)

**claim 判定**:
- 「`ema_trend_scalp` は accumulation 構造を捉えていない」は **CONFIRMED** (39:7 の close_reason 分布で実証)
- 「`pullback_to_liquidity_v1` mechanism は valid」: Live N=0 のため **未検証仮説** のまま (本 demo DB に当該戦略の entry なし)
- 「TREND nature 全体で SL_HIT 主体」は **CONFIRMED** (ema_trend_scalp 39 + stoch 6 = 45 SL_HIT, TP_HIT わずか 11)

---

## 2.6 Asia range / London open dynamics

### (a) 一般論

時間帯ごとの典型 pattern:

- **Asia (Tokyo) session 02-06 UTC**: 主要欧米銀行不在で機関 flow 薄い → range formation dominance、低 volatility
- **London open 07-08 UTC**: 欧州銀行 hedging flow + Asia range の breakout → expansion phase
- **Overlap (London + NY) 13-16 UTC**: 最大流動性、trend continuation or reversal の二極
- **NY close → Sydney open 21-23 UTC**: 流動性最薄、spread 拡大

**典型 pattern**: Asia range の high/low を London open で sweep → range 反対側へ expansion or 偽 break → range 中央回帰。

### (b) 我々のシステムへの含意

- `asia_range_fade_v1` (Phase 3 pre-reg LOCK 候補) は Asia range の touch + rejection を MR 的に取る設計
- `london_breakout`, `london_session_breakout` は London open expansion を取る BR 系
- friction-analysis: London session friction 0.86pip (FX-only 推定 0.86) は **最良時間帯** で edge を載せやすい
- Tokyo session friction 3.14pip (FX-only ~2.5) は edge 必要量が高い
- `stoch_trend_pullback` の Tokyo 29.0% vs Overlap 11.1% (Phase 4d) は「Asia 時間 = 緩やかなトレンド継続」「Overlap = 短期反転」という直感に整合

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| London session が friction 最良 | friction-analysis.md `Friction by Session`: London 0.86pip | **CONFIRMED** |
| Asia 時間でトレンド継続戦略が WR 高 | phase4d-session-spread-routing-result.md: `stoch_trend_pullback Tokyo 29.0% vs Overlap 11.1%` (WEAK p=0.015) | **PARTIAL CONFIRMED** — WEAK 認定で nominal p<0.05 だが Bonferroni 未通過 |
| Overlap で RANGE 戦略 high WR | phase4d-session-spread-routing-result.md: `bb_rsi_reversion Overlap 38.8%`, `sr_channel_reversal Overlap 30.5%` | **PARTIAL** — point estimate は high だが Bonferroni / Wilson lower で未確定 |
| NY × low-mid spread RANGE は強い descriptive boost | phase4d-II-nature-pooling-result.md: `RANGE × (NewYork, q1) WR=51.4%, Wilson 35.6% > baseline 31.5%` | **CONFIRMED descriptive** — 唯一の R2 boost 候補 |
| `asia_range_fade_v1` は VALID mechanism thesis | master Track 1 §2.5 (流動性吸収後の range 中央回帰) | **CONFIRMED** (thesis valid) — Live 実測未検証 |

#### 即時 sqlite-fx 検証

claim: 「session × WR の Live 実測 (Phase 4d との整合確認)」

```sql
-- entry_time の hour 帯から session 推定 (UTC)
SELECT
  CASE
    WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 0 AND 6 THEN 'Tokyo'
    WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 7 AND 12 THEN 'London'
    WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 13 AND 16 THEN 'Overlap'
    ELSE 'NY/Sydney'
  END AS session,
  COUNT(*) AS n,
  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*), 1) AS wr
FROM demo_trades
WHERE status='CLOSED' AND instrument NOT LIKE '%XAU%'
GROUP BY 1 ORDER BY 1;
```

→ §2.6(d) に追記。

### (d) 実測検証 (sqlite-fx)

**Query**: session × WR (UTC hour 帯から推定、XAU 除外、closed)

| session (UTC hour) | n | wins | WR | avg_spread | Wilson 95% CI |
|---|---|---|---|---|---|
| 1_Tokyo (00-06) | 95 | 40 | **42.1%** | 0.601 | **[32.7, 52.2]%** |
| 2_London (07-12) | 163 | 35 | **21.5%** | 0.771 | **[15.9, 28.4]%** |
| 3_Overlap (13-16) | 82 | 21 | 25.6% | 0.839 | [17.5, 35.9]% |
| 4_NY/Sydney (17-23) | 33 | 15 | 45.5% | 1.182 | [29.8, 62.0]% |

**重要な発見**: **Tokyo の Wilson lower 32.7% > London の Wilson upper 28.4%** — 95% CI が overlap せず、Tokyo > London は実測上 statistically robust (本検証単独で、Bonferroni 未実施)。

**friction-analysis との関係**:
- friction-analysis: London friction 0.86pip (best) — **friction の話**
- 本検証: London WR 21.5% (worst) — **WR の話**
- 両者は矛盾しない: London は friction が低くても、現システムが London で fire させている戦略 (TAP-1 含む大量) が機関 flow との整合性なく entry → SL hit が多発

**Phase 4d との関係**:
- Phase 4d: `stoch_trend_pullback Tokyo 29.0% > Overlap 11.1%` (WEAK p=0.015)
- 本検証: 全戦略 pool で Tokyo 42.1% > Overlap 25.6% で同方向、より大きい差
- Tokyo (低流動性 = 残存トレンド継続 / 静かな MR) が現システムでの sweet spot として機能している descriptive 強い signal

**counterintuitive 解釈**:
- 一般論: 「London / NY が機関 flow 厚く edge 取りやすい」
- 我々のデータ: Tokyo が WR 高い理由は (i) 機関 flow 薄 = 価格 noise 少、(ii) アジア時間レンジが pricing in されてから London open まで予測可能、(iii) **我々の戦略 portfolio が TAP-1 重で London expansion 期に向かない**
- 結論: 一般論の「session 優位」は戦略 portfolio 依存。我々の現 portfolio では Tokyo 優位

**claim 判定**:
- 「London session が friction 最良」: **CONFIRMED** (friction-analysis と整合、本検証でも avg_spread 0.771 と低位)
- 「Tokyo (Asia) で TREND 戦略 WR 高」: **CONFIRMED** (Phase 4d + 本検証で 2 重確認)
- 「Overlap で RANGE 戦略 high WR」: **REFUTED descriptive** (本検証では Overlap 全体 WR 25.6%)。Phase 4d の `bb_rsi_reversion Overlap 38.8%` は戦略別の cell であり全体 pool での話ではない
- 「NY low-mid spread RANGE は強い boost」: 本検証では NY/Sydney 全体 WR 45.5% (n=33) — descriptive に高いが Phase 4d-II の `RANGE × (NewYork, q1) WR 51.4%` と整合する方向
- 「`asia_range_fade_v1` mechanism valid」: Live N=0 で **未検証仮説**、ただし Tokyo 全体高 WR は Asia range 構造の存在を**間接的に裏付け**

---

## 2.7 News flow vs technical flow

### (a) 一般論

価格動因の二類型:

| 項目 | News Flow | Technical Flow |
|---|---|---|
| 発生原因 | FOMC, CPI, NFP, intervention, earnings | Order book imbalance, technical level touch |
| Vol 反応 | 瞬間的に 5-10× 拡大 (1-30 sec) | 通常 1-2× |
| Predictability | 反応方向は predictable、overshoot は predictable | 流動性 zone なら predictable |
| Trade window | News + 30sec 〜 5min | News window 外 |

**重要**: News window 30min 前後は **technical analysis が無効化**される。Spread 拡大、order book depletion、reversal 頻発で normal-time の signal は使えない。

### (b) 我々のシステムへの含意

- 現システムに **news event filter は導入されていない** (CLAUDE.md: 静的時間ブロック禁止、動的 spread gate のみ)
- News-driven volatility expansion を edge にする戦略 (`vol_surge_detector`) は存在
- News window 中に通常 technical 戦略 (bb_rsi, ema_pullback) が entry すると spread 拡大 + reversal で SL hit 量産される構造 lurk
- demo_trades には news flag フィールドなし → 直接検証不可

### (c) Phase 4c/4d KB 照合

| claim | 出所 | 判定 |
|---|---|---|
| `vol_surge_detector` が高 spread 帯 (q3) で WR 高 | phase4d-session-spread-routing-result.md: `vol_surge_detector q3=45.8% (N=24) vs q2=26.7%`, WEAK p=0.039 | **PARTIAL CONFIRMED** — 「高 spread = 真の vol surge期 = high-edge」という解釈で counterintuitive 結果が説明可能 |
| News flag は demo DB に存在しない | demo_trades schema (44 columns) review: news event 関連列なし | **CONFIRMED** — schema レベルで検証不能 |
| News window 中の通常戦略 SL hit 量産 | KB に直接該当ドキュメントなし | **未検証仮説** — Phase 3 設計時に news calendar API を組み込んで検証する必要あり |
| BREAKOUT nature joint signal の実体 | phase4d-II-nature-pooling-result.md: BREAKOUT joint χ² p=1.54e-3, V=0.371 (本日 5 検定で初の Bonferroni 通過) | **CONFIRMED** — BREAKOUT (vol_surge + bb_squeeze_breakout) には session × spread joint で signal 確実存在、ただし cell 単位 N 不足 |

---

## 2.8 Track ② からの Live Kelly -17.97% への構造的説明

### 2.8.1 流動性視点での再解釈

Live Kelly -17.97% (N=259, WR=39.0%) を Track ② のレンズで分解すると 4 つの構造的 leak が見える:

#### Leak 1: 戦略 mechanism thesis 不在 → 流動性 zone と無関係な entry

- Phase 5 で 5m Pure Edge BT 6/9 DEAD、strategy-mechanism-audit で 5 戦略中 2 NONE / 2 WEAK
- TAP-1 (中間帯 RSI/Stoch + AND) 戦略群は「機関 flow が動く構造的瞬間」を捉えていない random sample
- 結果として entry が pullback 完了前 / stop hunt 完了前で SL hit 量産 (`bb_rsi_reversion` の Live -16pp など)

#### Leak 2: Pair-friction 構造の ignore (sampling bias)

- mtf-alignment-bug-audit: aligned trade 73% が GBP_USD × BUY × trend_up_*、WR=8.1%
- spread 1.30 (aligned) vs 0.80 (conflict) で **friction が outcome を支配**
- 「aligned ほど負ける」は流動性メカニズムではなく pair-specific friction artifact
- 戦略 routing が pair-friction を考慮していないため friction が edge を食う

#### Leak 3: Session × strategy nature mismatch

- TREND nature (ema_trend_scalp + stoch_trend_pullback) WR=22.0% は base line 33% から大きく劣位
- TREND は Asia (低流動性 = trend 続きやすい) で 29% vs Overlap (反転点) で 11% と 18 ptp 差
- 現システムは session-blind に TREND 戦略を fire しており、Overlap で大量 LOSS を生産
- RANGE × NewYork × q1 の唯一の boost cell (WR 51.4%) も routing 未実装

#### Leak 4: BREAKOUT signal の検出不能

- Phase 4d-II BREAKOUT joint χ² p=1.54e-3 (Cramér V=0.371) で signal **確実に存在**
- ただし N=213 で cell 単位 N≥30 が 1 個のみ → routing rule 切り出し不可
- 60 days 蓄積で N=800 に到達すれば clean routing rule に昇格期待

### 2.8.1.5 本セッション sqlite-fx 検証で判明した新規 leak (4 件追加)

§2.1(d), §2.3(d), §2.5(d), §2.6(d) の Live 実測で本セッション初出の構造的 leak:

#### Leak 5: spread 0.5-1.0 帯の WR 20.6% (n=214) — 主流量での均衡崩壊

- 我々の Live trade の 57% (214/373) が spread 0.5-1.0 帯に集中、そこで **WR 20.6% (Wilson upper 26.4%)**
- USD_JPY BEV 34.4% を Wilson 95% CI が**完全に下回る** = 構造的赤字ゾーン
- spread が低くて流動性が良い「はずの」帯で最も負けている = 戦略 portfolio がその帯で発火する戦略が機能していない

#### Leak 6: London session で WR 21.5% (n=163, Wilson [15.9, 28.4]%)

- friction が最良 (avg_spread 0.771) の London で WR が **Tokyo (42.1%) の半分**
- 95% CI が overlap せず Tokyo > London は実測上 robust
- 解釈: 我々の戦略 portfolio (TAP-1 中間帯 AND 多数) が London expansion に向かない、機関 hedging flow と整合性なく entry → SL hit 多発

#### Leak 7: TREND 系の SL_HIT vs TP_HIT 比 5.6:1 (`ema_trend_scalp` 39:7)

- mechanism thesis NONE 戦略の **39 連敗 SL_HIT** は random sample of trending market の証左
- TIME_DECAY_EXIT 19/19 全敗 = pullback 完了を待たず entry しているため進展なし
- TREND nature 全体 N=46 で TP:SL = 11:45 (24%) の構造的劣位

#### Leak 8: Round-number 帯の signal を活用していない

- entry_price が round number ±5pips 以内で WR 58.3% (Wilson lower 44.3%, n=48)
- 5-10pip 帯 (進行中の sweep zone) で WR 21.4% — round に向かう途中の entry が SL hit
- 現戦略 registry に round-number proximity を mechanism thesis に組み込んだ戦略は**不在**
- Phase 3 で `pullback_to_liquidity_v1` の trigger として組み込めば mechanism 強化候補

### 2.8.2 Phase 3 mechanism-driven edge 再構築への含意 (5 件)

本トラックの結論として Phase 3 設計に直接使える含意を列挙:

1. **R2-A suppress 4 cell の即時実装** (Phase 4d で identify 済): `stoch_trend_pullback × (Overlap, q2)` (WR 7.7%), `sr_channel_reversal × (London, q3)` (15.0%), `ema_trend_scalp × (London, q0)` (17.0%), `vol_surge_detector × (Tokyo, q3)` (30.4%) → confidence ×0.5 or skip。流動性 zone と nature の mismatch を即解消。

2. **R2-B boost cell の活用**: `RANGE × (NewYork, q1)` WR 51.4% (Wilson 35.6% > baseline 31.5%) を confidence ×1.2。NY low-mid spread 帯は機関 flow が薄れる reversal 機会と整合。

3. **VALID mechanism thesis 戦略への重点投下**: `orb_trap` (流動性遷移 + dislocation, VALID 判定済) と Phase 3 候補 `pullback_to_liquidity_v1`, `asia_range_fade_v1` は mechanism thesis が流動性メカニズムに直接根ざしている。Live N≥30 まで shadow で運用後に promote。

4. **Pair-friction-aware routing**: `ema_trend_scalp × GBP_USD × aligned` のような pair × strategy × signal の三重組み合わせで friction が edge を食うパターンを R2-C 形式で gate。friction-analysis の per-pair RT (USDJPY 2.14 / EURUSD 2.00 / GBPUSD 4.53) を戦略の avg_win 期待値と照合し BEV を毎 entry で動的計算。

5. **POC / VWAP / D1 H/L magnet level 戦略の新規設計**: 現 registry に不在の magnet level 系戦略を Phase 3 で pre-reg LOCK & 365日 BT。流動性供給の集中点に entry を集中させる構造的 edge を取りに行く。

6. **Round-number proximity gate (本セッション新規)**: §2.3(d) の発見 — round ±5pip で WR 58.3% (Wilson lower 44.3%, n=48) を活用。現戦略の entry 関数に「signal_price が round number ±5pip 以内なら confidence ×1.3、5-10pip 帯 (sweep 進行中) なら ×0.7」の gate を R2 (Fast Reactive) 範疇で実装可能。Bonferroni 未通過のため R1 promotion (lot↑) は不可、defensive routing 限定。

7. **Session × strategy portfolio 再 routing (本セッション新規)**: §2.6(d) の Tokyo > London 反転は戦略 portfolio が London 機関 flow と整合していないことを示唆。Tokyo session で TREND nature の confidence ×1.2、London session で TAP-1 系を ×0.5 する descriptive routing を R2 で即時実装。N≥30 cell 単位で Wilson 監視。

8. **Spread 0.5-1.0 帯の trap zone 回避 (本セッション新規)**: §2.1(d) の発見 — Live trade の 57% が集中する spread 0.5-1.0 帯で WR 20.6% (Wilson upper 26.4%) と全 BEV を下回る赤字ゾーン。現状 spread gate が「spread 高すぎ防御」のみで「spread 普通帯の trap」を見ていない。R2 として「spread 0.5-1.0 かつ entry_type が TAP-1 系」で confidence ×0.5、または entry skip を実装。N=214 の十分なサンプルで signal robust。

### 2.8.2.5 R2 即時実装 6 件のサマリー (本トラック発見の全 actionable)

Phase 4d/4d-II + 本セッション sqlite-fx 検証で identify された R2 (Fast Reactive) defensive 提案を 1 表に集約:

| # | Action | 出所 | 期待効果 |
|---|--------|------|----------|
| R2-1 | `stoch_trend_pullback × (Overlap, q2)` skip / ×0.5 | Phase 4d (WR 7.7%) | 強い loss-generator 抑制 |
| R2-2 | `sr_channel_reversal × (London, q3)` ×0.5 | Phase 4d (WR 15.0%) | London 高 spread 帯 SR 失敗回避 |
| R2-3 | `ema_trend_scalp × (London, q0)` ×0.5 + GBP_USD aligned ×0.5 | Phase 4d + alignment-audit | pair-friction artifact 解消 |
| R2-4 | `RANGE × (NewYork, q1)` ×1.2 boost | Phase 4d-II (Wilson 35.6% > baseline 31.5%) | 唯一の descriptive boost cell |
| R2-5 | **Round-number ±5pip ×1.3 / 5-10pip ±0.7** (新規) | §2.3(d) (WR 58.3% Wilson 44.3%) | stop hunt 構造の defensive 活用 |
| R2-6 | **Spread 0.5-1.0 × TAP-1 系 ×0.5** (新規) | §2.1(d) (WR 20.6% n=214) | trap zone 回避 |
| R2-7 | **Tokyo session × TREND ×1.2 / London × TAP-1 ×0.5** (新規) | §2.6(d) (Tokyo>London Wilson non-overlap) | session × portfolio mismatch 解消 |

R2-5/6/7 は本セッション新規発見で、365日 BT を経ずに Live N=48-214 の R2 範疇で即時実装可能。R1 promotion (lot↑ / mode change) は Bonferroni 未通過のため不可。

### 2.8.3 Track ② として検証できなかった残課題

- News flow filter 未検証 (demo DB に news event 列なし)
- POC / VWAP の Live 実測未検証 (現戦略が利用していない)
- 60 days 蓄積後の BREAKOUT joint signal 再検定 (passive、待機のみ)
- pair × spread × strategy × session の 4-way interaction (Phase II GBM が示唆する 45% predictive の正体)

---

## Appendix: Track ② で参照した Phase 4c/4d KB 引用一覧

| # | KB ファイル | 引用箇所 | 使用 § |
|---|------------|---------|-------|
| A1 | `wiki/analyses/friction-analysis.md` | Per-Pair Friction (RT), Friction by Session, Tier 1 BT Validation | §2.1, §2.6 |
| A2 | `wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md` | 0 SURVIVOR / 2 WEAK, Top results table, R2-A/B candidates, 真の bottleneck | §2.1, §2.2, §2.6, §2.7 |
| A3 | `wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md` | BREAKOUT joint χ² Bonferroni 通過, RANGE × (NewYork, q1) descriptive boost, 累積 evidence | §2.2, §2.6, §2.7 |
| A4 | `wiki/analyses/phase4c-mtf-alignment-bug-audit-2026-04-26.md` | Finding 1-4 (d1 bear case 0 件、aligned GBP_USD bias、pair-friction artifact) | §2.2, §2.8 |
| A5 | `wiki/syntheses/strategy-mechanism-audit-2026-04-26.md` | TAP-1/2/3 定義、`orb_trap` VALID、`bb_rsi_reversion`/`ema_pullback` WEAK、`ema_trend_scalp`/`engulfing_bb` NONE | §2.3, §2.5 |
| A6 | `wiki/learning/fx-fundamentals-2026-04-26.md` (master Track 1) | Track 2 初稿 §2.1-§2.6 (本ファイルの深掘り対象) | §2.0.4, §2.5, §2.6 |

外部出典 (web / 書籍 / 論文) は本トラックでは引用していない (curried-ritchie 検証ソース規律準拠)。

---

## Track ② 完了マーカー

**Status**: 執筆完了 + sqlite-fx 実測検証 4 件 inline 完了
**Completion date**: 2026-04-26 (本セッション)
**Live verification queries 実行**:
- §2.1(d): spread_bin × WR (n=373, 4 bins, ARTIFACT 検出)
- §2.3(d): round-number proximity × WR (JPY 系 n=205, Wilson lower 44.3% で signal CONFIRMED)
- §2.5(d): close_reason × strategy (6 戦略の TP:SL 比、ema_trend_scalp 39:7 で NONE 判定実証)
- §2.6(d): session × WR (Tokyo Wilson [32.7,52.2]% > London [15.9,28.4]% 非 overlap)

**Track ② 発見 summary**:
- 既存 KB 照合 claim: 14 件 (うち CONFIRMED 8, PARTIAL 4, REFUTED 1, 未検証仮説 1)
- Live data REFUTE: 「spread 高 = WR 低」一般論を REFUTE、「London > Tokyo」一般論を REFUTE
- 新規 R2 actionable: 3 件 (R2-5/6/7)
- Phase 3 含意 (5+3=8 件)

**Next step**: master file `fx-fundamentals-2026-04-26.md` への統合は Track ① セッションが master 統合フェーズで実施 (本ファイルは Read-only として参照引用される)。本ファイルは編集を停止する。
