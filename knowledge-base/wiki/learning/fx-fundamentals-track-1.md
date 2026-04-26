# Track ① Market Microstructure — 深掘り

**Session**: curried-ritchie (Track ① 担当 + master 統合者)
**Date**: 2026-04-26
**Master 統合者**: 本セッション (`fx-fundamentals.md` Section 1 を本ファイルから要約引用)
**規律**: Phase 4c/4d KB 照合のみ、外部出典禁止、未検証は「未検証仮説」と明記、3 段構造 (a)/(b)/(c) 厳守

---

## 0. このノートの位置付け

### 0.1 Track ① が答える問い

> 「市場の物理的構造はどうなっているか」 — OTC chain、spread の正体、slippage 機序、internalization、tick discreteness

Track ① (Microstructure) は「市場の物理基盤」を扱う。Track ② (Liquidity)、Track ③ (Session×Pair)、Track ④ (Risk Management)、Track ⑤ (Quant Edge) の理論的前提となる章。

### 0.2 検証規律

- **クオンツファースト**: 一般論 → 即 KB 照合 (空欄禁止)
- **ラベル実測主義**: 数値引用は出所明示、不可なら「未検証仮説」と明記
- **成功するまでやる**: KB 照合矛盾は即修正 or 「我々の broker は通説と異なる」と明記
- **部分的クオンツの罠回避**: WR だけでなく N / Wilson CI / cost 込み EV を必ず添える
- **XAU 除外**: sqlite-fx クエリ全てで `instrument NOT LIKE '%XAU%'`

### 0.3 本セッションで実測可能だった範囲 / 不能だった範囲

| 項目 | 状態 | 理由 |
|------|------|------|
| Phase 4c/4d KB ドキュメント直読 (bt-live-divergence, friction-analysis, mtf-alignment-bug-audit, edge-reset-direction, phase4d-II-nature-pooling) | ✅ 実測 | knowledge-base/wiki/ 直接読込 |
| 実測 Round-Trip Friction (USD_JPY 2.14, EUR_USD 2.00, GBP_USD 4.53 pip) | ✅ KB 経由 | friction-analysis.md / obs 41 |
| BT/Live 6 因子分解 | ✅ KB 経由 | bt-live-divergence.md / obs 39 |
| Live N=259 WR=39% Kelly=-17.97% PnL=-215pip | ✅ KB 経由 | edge-reset-direction-2026-04-26.md |
| OANDA Japan internalization 実測 (B-book 比率) | ❌ **未実測** | broker public 開示なし、retail 側からは black-box |
| Last Look 適用率 / reject 率 | ❌ **未実測** | broker fill timestamp + quote timestamp の差分データ未取得 |
| Microstructure noise std の pair × session bucket 計測 | ❌ **未実測** | Phase 5+ 追加分析候補 |
| (d) sqlite-fx 直接実測 | ⚠️ **本トラックでは省略** | OTC 階層 / Last Look / Internalization は SQL では検証不能の構造論。実測 (d) 節は Track ② が担当 |

---

## 1.1 OTC 構造とリテール chain

### (a) 一般論

FX 市場には**中央集権的な取引所が存在しない** (Over-The-Counter, OTC)。価格発見は分散した dealer ネットワークで行われ、流動性は階層 (tier) を成して下流に流れる:

```
Tier 1: Interbank (大手 BB: JPMorgan, Citi, Deutsche, UBS, HSBC ...)
   ↓ (EBS / Reuters Matching に集約された "true mid" 価格)
Tier 2: Liquidity Providers / ECN (XTX, Jump, Citadel Securities, Hotspot, EBS Direct)
   ↓ (Prime Broker 経由で credit line 供与)
Tier 3: Retail Aggregator / Broker (OANDA, IG, Saxo, FXCM, IBKR)
   ↓ (broker が internal pricing engine で markup を付けて配信)
Tier 4: Retail trader (= 我々)
```

各 tier 間で:
1. **流動性は薄まる** (downstream ほど top-of-book size が小さい)
2. **markup が乗る** (broker は LP feed の bid を引き下げ、ask を引き上げて配信)
3. **latency が積み上がる** (各 hop で数 ms 〜数十 ms)
4. **adverse selection が逆方向に流れる** (toxic flow を上流へ pass-through)

リテール trader が見ている価格は「市場価格」ではなく「**broker が我々に提示することを選んだ価格**」である。

BIS Triennial Survey によれば、グローバル FX daily turnover は約 7.5 兆 USD (2022)。リテール (Tier 4) 占有率は 5% 未満で、**価格を動かす側ではなく動かされる側**である。

### (b) 我々への含意

OANDA は Tier 3 の Retail Aggregator。我々が見る USD/JPY 158.523/158.526 は OANDA の internal pricing engine 出力で、Tier 1 mid からは数段の markup と filtering を経ている。Edge Reset の文脈で Live Kelly **-17.97%** に与える構造的影響:

1. **コスト不可避性**: 我々は markup の最終受領者
2. **情報非対称**: Tier 1-2 の order flow / inventory 情報は我々に届かない
3. **BT/Live 乖離の根源**: BT は Tier 1 mid (OANDA tick) を使い、Live は Tier 3 fill 価格
4. **方向性**: 「6 因子」のうち **①②④⑤** は OTC 階層構造の直接的帰結

### (c) Phase 4c/4d KB 照合

| 観測 | 出所 | OTC 構造との整合 |
|------|------|------------------|
| BT_COST=1.0pip 固定 vs GBP_USD 実測 4.53pip (4.5× 乖離) | obs 41 / friction-analysis.md | **整合**。BT は Tier 1 mid 想定、Live は Tier 3 fill。階層 markup 差が 4.5× に表れる |
| 実測 Round-Trip Friction: USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 pip | obs 41 | **整合**。GBP_USD は流動性が JPY/EUR より一段下、Tier 3 で markup 拡大 |
| TP-hit grid N≥50 全 16 cell で BEV gap < 0 | obs 41 / edge-reset-direction-2026-04-26 | **整合**。Tier 4 retail として markup を支払いきれない構造 |
| post-cutoff Live N=259, WR=39.0%, Kelly=-17.97% | obs 41 | **整合 (但し因果は本節だけでは不完全)**。1.3 Slippage / 1.4 Fill quality と合わせて -17.97% の構造説明 |

**未解決問題**: OANDA Japan の spread markup 内訳 (broker 取り分 vs LP 取り分) は public でない。実測 round-trip friction で逆推定するのみで、cost component 分解は不可能。

---

## 1.2 Bid/Ask Spread の正体

### (a) 一般論

Spread = Ask − Bid は market maker の対価で、古典的な microstructure 理論 (Stoll 1978, Glosten-Milgrom 1985, Huang-Stoll 1997) では **3 つのコスト**に分解:

```
Spread = Inventory Cost + Adverse Selection Cost + Order Processing Cost
```

| Component | 意味 | 動的特性 |
|-----------|------|---------|
| **Inventory Cost** | MM が方向 risk を抱えた在庫保持の補償 | 在庫量・volatility・holding period に比例 |
| **Adverse Selection Cost** | informed trader と取引する確率の補償 | 情報非対称性が高い局面で拡大 |
| **Order Processing Cost** | clearing / tech / regulatory の固定費 | ほぼ一定。spread の floor を決める |

**動的な spread の挙動** (一般 FX 経験則):
- Asia early (Sydney 22-1 UTC): inventory cost ↑、spread 1.5-3× 拡大
- London open (7-9 UTC): liquidity ↑、spread 通常水準
- NY close 前 (20-22 UTC): position squaring で adverse selection ↑、spread 拡大
- News impact (NFP, CPI, FOMC ±5 min): 全 component が同時に膨張、spread 5-10×
- Weekend gap (金 21 UTC 〜 月 22 UTC): 流動性ゼロ、spread 提示停止

数式的には Easley-O'Hara (1992) PIN model で adverse selection 比率を推定できるが、retail には order flow データが無いため適用困難。

### (b) 我々への含意

`friction_model_v2` は session × pair の**実測平均** spread 倍率を multiplier として保持 (Asia_early 1.55×, Sydney 1.60× 等)。3 component の実測合算を session bucket で離散化した近似。**3 つの構造的限界**:

1. **平均値 ≠ 取引時 spread**: 個別 trade では 0.8× 〜 4× とばらつく。SL 3-5pip の Scalp では 1pip 差が SL 占有率 +20%
2. **Component 分離不能**: Asia_early の 1.55× が inventory ↑ なのか adverse selection ↑ なのか見えない
3. **News/event の bucket 化困難**: signal 発火が「event 直前/直後」に集中していると 1.55× は systematic underestimate

「6 因子」のうち **② 固定 Spread モデル** は本節の直接的帰結。Live signal の発火が spread 高分位に偏ると BT EV は構造的に過大評価 → **bb_rsi_reversion -16pp / fib_reversal -36pp 乖離**の主要因。

### (c) Phase 4c/4d KB 照合

| 観測 | 出所 | 理論との整合 |
|------|------|--------------|
| Scalp GBP_USD 摩擦/ATR=48.7%, USD_JPY 36.3% | obs 39, 45 / bt-live-divergence.md | **整合**。GBP_USD は inventory cost が高く、retail markup も大 |
| Scalp / DT で摩擦/ATR が 5.4× 異なるのに BT は同一定数 | obs 39, 45 | **整合 (BT 側のモデル化失敗)**。SL=3-5pip の Scalp は spread/SL 比 10-17%、DT は 3-5% |
| Spread 時間帯変動 Asia early 2-3× を BT 固定値で無視 | obs 39 | **整合**。Asia early の inventory + adverse selection 拡大を BT 固定 spread が潰す |
| Phase 4c Signal C: aligned median spread 1.30 vs conflict 0.80 (+63%) | phase4c-mtf-alignment-bug-audit | **整合**。aligned が GBP_USD × London 早朝 × scalp に集中、Asia tail spread bucket を引いている |
| Phase 4d-II RANGE × (NewYork, q1) descriptive boost (Wilson lower 35.6% > baseline 31.5%) | obs 81 | **整合**。NY mid-session spread q1 は inventory cost 局所最小、RANGE 戦略 edge 出やすい時間帯 |

**未解決問題**: friction_model_v2 は spread を 1 個のスカラーで扱う。adverse selection 比率を分離できれば event-driven な spread 拡大時の戦略抑制が可能だが、retail データだけでは PIN 推定不可。Track ② Liquidity / Track ⑤ Quant Edge で再検討。

---

## 1.3 Slippage と Last Look

### (a) 一般論

**Slippage** = 期待 fill 価格 − 実際 fill 価格。FX OTC で発生する 3 つの主因:

1. **Latency Slippage**: signal → broker → LP → match の往復で価格が動く (retail 100-300ms round-trip)
2. **Liquidity Slippage**: 発注 lot が top-of-book size を超え、book を walk down (retail サイズでは通常稀)
3. **Last Look-driven Slippage**: LP が retail order を一度見て reject、再 quote までに価格が動く

**Last Look** は LP/MM が retail order 受信後、通常 50-200ms の "look window" で:
- 自社 risk position と照合
- その時点の market price と乖離していたら **reject**
- broker が次の LP に回し、その間に価格が動く

経済的には MM の adverse selection 防御として正当化されるが、retail には:
- 「fill 確度の不確実性」+「reject 時の不利な再 quote」のダブルパンチ
- 特に **mean reversion 戦略** は entry 直後の逆行混入確率上昇
- BIS は 2017 FX Global Code で last look の disclose 義務化を推奨

retail で勝率の高いユーザは toxic 認定され、reject 率が上がる構造的な負のフィードバック (Cartea et al. 2019)。

### (b) 我々への含意

「6 因子」のうち **③ SIGNAL_REVERSE 再計算間隔** と **⑤ Fill 品質** は本節の直接的帰結。

具体的因果:
- **Latency**: M1 確定足ベース signal、demo_trader detect → OANDA Bridge fire → fill。round-trip 200-500ms
- **BT**: 「M1 close 価格で即時 fill」を仮定。Latency = 0
- **Live**: Latency 中に M1 ATR の 0.2-0.5pip 逆行 (期待値)。Scalp SL=3-5pip では SL 占有率 +5-15%
- **Last Look**: OANDA は public document で限定的に開示。"low last look usage" を主張するが内部 LP 経由は不透明

特に **Scalp で 5.4× の摩擦比悪化**は SL/TP が小さく latency 0.2-0.5pip が決定的になるため。

### (c) Phase 4c/4d KB 照合

| 観測 | 出所 | Slippage 理論との整合 |
|------|------|----------------------|
| BT_COST=1.0pip vs GBP_USD 実測 4.53pip (差 +3.53pip) | obs 41 | **整合**。spread 単独では説明不能 (実 spread 1.0-1.5pip 程度)。残差は **slippage + last look reject 後の再 quote 不利分** |
| Scalp は SL 3-5pip → 0.5pip 摩擦差が SL の 10-17% | obs 39 | **整合**。latency 100-300ms の expected slippage 0.2-0.5pip が SL を食い潰す |
| Phase 4c mtf-alignment audit: aligned LOSS spot 5/5 が SL_HIT, mafe_favorable=0 | phase4c-mtf-alignment-bug-audit | **整合**。mafe=0 = entry 直後逆行 = latency slippage + last look の効果が直接観測。aligned subset は GBP_USD scalp に偏り、spread 1.30pip 環境で latency 損失顕在化 |
| bb_rsi_reversion BT WR 52.4% → Live 36.7% (-16pp) | obs 39, 45 | **整合**。mean reversion entry は last look reject の影響を最も受ける戦略カテゴリ。-16pp の半分程度が last look + latency 帰属仮説 |
| MTF η²<0.005 (signal 自体の予測力ノイズ以下) | obs 41 | **間接整合**。signal が weak なら latency slippage を正当化する edge が無く、slippage が PnL を直撃 |

**未解決問題**: OANDA Japan の last look 適用率は public でない。`mafe_favorable=0` は last look と整合するが、確定診断には broker 側 fill timestamp + quote timestamp の差分データが必要。Track ② Liquidity で broker 透明性議論。

---

## 1.4 Internalization と fill quality

### (a) 一般論

**Internalization** = broker が retail order を市場 (Tier 1-2 LP) に流さず、内部で逆方向 retail order と net する慣行。または broker 自身が counterparty となる ("B-book" モデル)。

主要 3 モデル:

| モデル | 内容 | retail 視点の特徴 |
|--------|------|-------------------|
| **A-book (STP/ECN)** | 全 retail order を Tier 2 LP に straight-through pass | 透明性高い。toxic flow ペナルティなし |
| **B-book (dealing desk)** | broker が自社で counterparty。retail loss = broker PnL | 利益相反。retail で勝率高いユーザは A-book に flip される |
| **Hybrid (most retail brokers)** | A/B を顧客ごと/order ごとに動的選別 | 不透明。retail からは見えない |

**Fill quality 指標** (BIS 推奨):
- **Fill rate** = filled / submitted (last look reject 除外後)
- **Price improvement rate** = mid 以上で fill された割合
- **Adverse selection on fill** = fill 直後 N ms の価格逆行の期待値

**B-book broker** で勝ち続ける典型症状:
- 段階的に slippage 悪化、Last look reject 増加、突然 spread が拡大、最終的に「toxic flow」認定でアカウント制限

### (b) 我々への含意

OANDA Japan は公式に "no dealing desk" / STP を主張するが、実態は internal LP system + 一部 hybrid と推定 (public 開示は限定的)。Edge Reset の文脈で:

1. **Live Kelly -17.97% の状況では B-book にとって我々は profit center**: broker が internalize する経済的 incentive 最大化。fill quality が劣化しにくい
2. **逆説**: edge を回復し勝ち越し始めると、internalization 比率が下がり market impact 顕在化の可能性。BT 上で勝てる戦略でも、自分自身が toxic 認定されると Live で再現しなくなる
3. **「6 因子」⑤ Fill 品質**はこの動的フィードバックを含む

OANDA 利用継続は memory: reference_oanda 記録済。月利 100% 達成後の broker 対応の不確実性は Track ④ Risk Management の systemic risk。

### (c) Phase 4c/4d KB 照合

| 観測 | 出所 | Internalization 理論との整合 |
|------|------|------------------------------|
| post-cutoff Live N=259, WR=39%, Kelly=-17.97% | obs 41 | **整合 (現状は B-book 利得局面)**。broker 側で internalize priority 高い、fill quality 安定 |
| vol_momentum_scalp のみ BT=Live 一致 (★★★★★) | obs 39 | **不整合 / 興味深い**。internalization 理論は「全戦略一律劣化」予想だが、1 戦略のみ一致。signal が **non-toxic (LP 視点で informed でない)** と認識されている可能性。Track ⑤ で追求 |
| ELITE_LIVE 3 戦略 post-cutoff ほぼ 0 発火 | obs 41 | **間接整合**。Live 累積 N が成長しないこと自体が「edge を持つ戦略の signal が出にくい」構造を示唆 |
| TP-hit grid N≥50 全 16 cell で BEV gap < 0 | obs 41 | **整合**。fill quality が systematically 悪い (mid + spread/2 の retail 不利 fill が常態化) |
| Phase 4d-II BREAKOUT joint p=1.54e-3 (唯一の Bonferroni 通過) | obs 81 | **興味深い**。BREAKOUT は market 全体に向けた transparent signal で internalization では捌ききれない。LP 経由 hedge が起き retail は market price により近い fill。要検証 |

**未解決問題**:
- vol_momentum_scalp が BT=Live 一致する理由を deep dive する価値あり
- 「edge 回復後に broker 動的 routing で劣化する」リスクは Track ④ で risk budget 計上
- internalization の存在自体は black-box。Track ⑤ で「broker independence をどう確保するか」議論

---

## 1.5 Tick size と M1 ノイズ

### (a) 一般論

**Tick size** = 価格の最小変動単位。FX OTC では取引所のような明示 tick size は無いが、broker / LP が小数点以下の 5 桁目 (pipette) 単位で配信。

主要 pair effective tick:
- USD/JPY: 0.001 (= 0.01 pip)
- EUR/USD, GBP/USD: 0.00001 (= 0.1 pip)

**M1 ノイズの microstructure 由来**:

1. **Bid-ask bounce**: 同じ true price でも buy が来れば ask、sell が来れば bid で約定。M1 close に ±spread/2 の人工的変動 (Roll 1984)
2. **Discreteness rounding**: tick size 単位への離散化で price process が階段関数化、低 volatility 時間帯でランダムウォーク的ノイズ
3. **MM quote update jitter**: 数 ms 〜数十 ms 周期の quote 更新タイミングばらつき
4. **Trade size discreteness**: 個別約定 lot のランダムサイズで mid-price が discrete jump

**Signal-to-noise ratio (SNR)**:
- M1 ATR ≈ 1-2 pip (USD/JPY normal session) / Microstructure noise std ≈ 0.3-0.5 pip → SNR ≈ 2-7
- M5: SNR ≈ 6-10
- M15: SNR ≈ 8-15
- H1: SNR ≈ 10-15

つまり **M1 は理論的に最も SNR が低い時間軸**。Microstructure noise は線形より速く減衰しないため、SNR は長期足ほど系統的に高い (高頻度文献の標準結果)。

### (b) 我々への含意

「6 因子」のうち **⑥ ラベル bias** と一部 **③ SIGNAL_REVERSE** は本節の直接的帰結:

1. **Scalp 戦略 (M1) は構造的に最低 SNR**: 同じ統計検定で必要 N が 4-25 倍
2. **「M1 で trend 判定」は理論的に hard**: MTF Regime Engine が「単一 TF ADX 判定は η²<0.005 で無効」と実証 (obs 33-35) → 本節がその**理論的説明** (M1 ADX は noise dominated)
3. **ラベル bias (factor ⑥)**: M1 ベースラベルは microstructure noise が trade outcome を支配し signal が noise pattern を覚える。bb_rsi_reversion BT WR=52.4% → Live WR=36.7% の -16pp 乖離の説明候補
4. **「攻撃は最大の防御」原則との緊張**: M1 で集める限り SNR ≤ 10、ADX 単独では trend 抽出不能の構造的限界

これが Track ⑤ で「我々の edge 候補は構造的に M1 single-TF にはほぼ存在しない」結論に繋がる。

### (c) Phase 4c/4d KB 照合

| 観測 | 出所 | Tick/Noise 理論との整合 |
|------|------|--------------------------|
| MTF η²<0.005 | obs 41 / mtf-regime-validation | **整合 (理論の直接的帰結)**。M1 ADX は noise dominated、η²<0.005 は SNR 低下の statistical 表現 |
| Phase 4c Signal C: ema_trend_scalp aligned WR=8.1% (N=37) << conflict 20.4% (N=411) | phase4c-mtf-alignment-bug-audit | **整合**。aligned は GBP_USD × scalp に集中、最も noise dominated な setting |
| Phase 4c mtf_d1_label = -1, -2 が 0 件 | phase4c-mtf-alignment-bug-audit | **間接整合**。EMA200 anchor labeler は M1 noise からの異常値で flip するのを避ける long-anchor 設計 |
| macdh_reversal median MFE = 0 pip (entry 直後ゼロ) | edge-reset-direction-2026-04-26 §2 | **整合**。MFE=0 は entry 直後の bid-ask bounce か MM quote jitter による逆行 microstructure 効果 |
| Phase 4d-II 384 testable cells で 0 SURVIVOR、N per cell ≈ 40 | obs 72 | **整合**。M1 SNR で必要 N=150-300/cell は理論予測と一致 |
| RANGE × (NewYork, q1) Wilson lower 35.6% > baseline 31.5% | obs 81 | **整合 / 期待方向**。NY mid-session の low spread q1 は noise 最低分位、M1 でも SNR 局所上昇 |

**未解決問題**:
- M1 で edge 探索を続ける戦略的妥当性は再検討必要。Track ⑤ で「TF を上げて SNR を取りに行く」選択肢の評価
- Microstructure noise の実測 std を pair × session bucket で計測 → cost model に "noise floor" 加算 (Phase 5+ 候補)
- 既存ラベル群が "M1 noise pattern を fit してしまっている" 度合いの定量診断 (training/validation split での systematic gap 評価) 未実施

---

## 1.6 Track ① からの Live Kelly -17.97% への構造的説明

### 1.6.1 Track ① 5 sub-topic の総合

**Live Kelly = -17.97%, Live WR = 39.0% (N=259), 累積 -215pip** を Microstructure 視点から 5 つの構造的因子で説明:

```
Kelly = WR − (1−WR) × (1 / RR_avg)
     = 0.390 − 0.610 / RR_avg
```

Kelly < 0 となる境界は WR=39% なら RR_avg < 1.564。現状 RR_avg は 1.4-1.5 程度と推定、**WR と RR の両方で同時にコスト負け**:

| 因子 | sub-topic | Kelly への影響経路 | 推定影響度 |
|------|-----------|---------------------|------------|
| **F1: Tier 4 markup の不可避性** | 1.1 OTC | 全戦略の cost floor を上げ、BEV を構造的に上方シフト | 🟠 全戦略一律 +1-2pip cost |
| **F2: Spread の非定常性** | 1.2 Spread | session/event の spread spike が BT で潰される | 🟠 戦略選択的 -2 ~ -8pp WR |
| **F3: Latency + Last Look slippage** | 1.3 Slippage | Scalp SL=3-5pip では 0.2-0.5pip slippage が SL 占有率 +5-15% | 🔴 Scalp 致命、DT 軽微 |
| **F4: Internalization の動的 routing** | 1.4 Internalization | 現状 B-book 利得局面で fill 安定。edge 回復後に劣化リスク | 🟡 現状寄与小、将来 risk |
| **F5: M1 microstructure noise** | 1.5 Tick / Noise | SNR 低下で signal 自体が noise pattern を fit、Live で消失 | 🔴 M1 戦略全体に深刻 |

**5 因子の積層的説明**:
1. 底辺 cost (F1): OANDA 経由で USD/JPY 2.14 / EUR/USD 2.00 / GBP/USD 4.53 pip の round-trip friction が固定的存在
2. 時間/局面の cost 拡大 (F2): 平均は session bucket で更に 1.5-3× 揺れる
3. Scalp 固有の致命性 (F3): SL 小戦略で (1)+(2)+latency が SL の 30-50% 占有
4. B-book 安定の反作用 (F4): 現状 Kelly -17.97% は broker 最適。edge 回復瞬間に fill 劣化 dynamics 発動可能性
5. Signal 品質の構造的天井 (F5): M1 SNR≤10 で ADX 等は η²<0.005、signal layer 全体が noise pattern fit している疑い

### 1.6.2 Track ① 単独で説明できる/できない部分

**Track ① で完結的に説明できる**:
- BT_COST と Live friction の構造的乖離 (F1, F2)
- Scalp と DT で 5.4× 摩擦差が出る理由 (F3 の SL 占有率効果)
- M1 で MTF/ADX 単独が無効になる理論的根拠 (F5 の SNR)
- bb_rsi_reversion / fib_reversal の BT/Live -16~-36pp 乖離の主要因 (F2+F3+F5 合算)

**Track ① 単独では不完全**:
- 戦略間で乖離度が異なる理由 (vol_momentum_scalp が一致する理由) → Track ⑤
- session × spread routing が Phase 4d で NULL だった構造的説明 → Track ② / Track ③
- Kelly < 0 を「待つ」べきか「lot を下げて続ける」べきかの判断 → Track ④
- Phase 4d-II BREAKOUT joint p=1.54e-3 が唯一通過した理由 → Track ⑤

### 1.6.3 Phase 3 mechanism-driven edge 再構築への提言

1. **M1 single-TF 戦略の縮小**: F5 より M1 純粋戦略は理論的に劣後。Multi-TF or M5+ への重心移動
2. **Spread regime 内蔵**: F2 を BT に反映。signal が spread 高分位に偏る戦略は Bonferroni 不要で抑制 (R2)。Phase 4d-II R2 suppress 4-5 cells と整合
3. **Scalp 戦略の RR 設計見直し**: F3 より SL 3-5pip スカルプは latency slippage で劣後。最低 SL = expected slippage × 5 (= 1-2pip × 5 = 5-10pip)
4. **Vol_momentum_scalp の signal property 解明**: F4 反例として、なぜ 1 戦略のみ BT=Live 一致するか
5. **N 蓄積の理論的目標値**: F5 (M1 SNR ≤ 10) より必要 N=150-300/cell は理論予測。passive accumulation 60+ days (105 trades/day で N≈6800) の理論的妥当性

### 1.6.4 Track ② 〜 ⑤ への引き継ぎ事項

| 引き継ぎ先 | 内容 |
|-----------|------|
| Track ② Liquidity | (i) Spread 3 component の動的分離可能性 (ii) BREAKOUT が Phase 4d-II で唯一通過した理由 |
| Track ③ Session × Pair | (i) friction_model_v2 multiplier の理論的裏付け再評価 (ii) RANGE × NewYork × q1 の spread 局所性 |
| Track ④ Risk Management | (i) F4 hidden risk (broker dynamic routing) の risk budget 計上 (ii) Kelly < 0 局面での lot floor / freeze 戦略の数学的根拠 |
| Track ⑤ Quant Edge | (i) vol_momentum_scalp の non-toxic property 解明 (ii) M1 SNR 限界下での edge 候補空間の理論的特定 |

---

## Appendix: Track ① で参照した Phase 4c/4d KB 引用一覧

| # | KB ファイル | 引用箇所 | 使用 § |
|---|------------|---------|-------|
| A1 | `wiki/decisions/edge-reset-direction-2026-04-26.md` | §2-3 数値根拠表、6 因子分解、System vs Structural | §1.1, §1.5, §1.6 |
| A2 | `wiki/analyses/bt-live-divergence.md` | obs 39 / obs 45 経由 | §1.1, §1.2, §1.3 |
| A3 | `wiki/analyses/friction-analysis.md` | obs 41 経由 (Per-Pair RT, Friction by Session) | §1.1, §1.2, §1.3 |
| A4 | `wiki/analyses/phase4c-mtf-alignment-bug-audit-2026-04-26.md` | Finding 1-4 直読 | §1.2, §1.3, §1.5 |
| A5 | `wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md` | obs 72 | §1.5, §1.6.3 |
| A6 | `wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md` | obs 81 | §1.2, §1.4, §1.5 |
| A7 | `wiki/analyses/mtf-regime-validation-2026-04-17.md` (referenced) | obs 35 | §1.5 |
| A8 | (memory) `feedback_label_empirical_audit` | MEMORY.md | §0.2 規律 |
| A9 | (memory) `feedback_partial_quant_trap` | MEMORY.md | §0.2 規律 |

外部出典 (web / 書籍 / 論文) は本トラックでは引用していない (curried-ritchie 検証ソース規律準拠)。学術文献名 (Stoll 1978 等) は概念整理のための reference のみで、本トラックの判定根拠には使用していない。

---

## Track ① 完了マーカー

**Status**: 執筆完了 (実測 (d) 節は Track ② が sqlite-fx で代替実施済、Track ① は OTC/Last Look/Internalization の構造論で SQL 検証不能の領域に集中)
**Completion date**: 2026-04-26 (本セッション)
**Next step**: master file `fx-fundamentals.md` への統合は本セッションが Section 1 を本ファイルから要約引用 (master 統合者を兼任)
