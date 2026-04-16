# なぜretailスキャルピングは負けるのか — 構造的分析と勝ち筋の探索

**作成日**: 2026-04-17
**目的**: Micro-scalp 戦略群が負ける根本原因を特定し、retail で勝てる方法論を体系化

## エグゼクティブ・サマリー

**結論の先出し:**
1. Retail scalping の負けは **5つの構造的要因** の積であり、個別最適化では反転しない
2. 勝ち筋は **「同じ土俵で戦わない」** こと — 時間軸・情報源・戦略タイプを Tier 1 参加者と差別化
3. 現在の micro-scalp 路線は、**構造的な敗戦フィールド** で戦っている
4. 具体的推奨: データ駆動型エッジ探索 (systematic discovery) への移行

---

## Part 1: なぜ負けるのか — 5つの構造的要因

### 要因1: 情報非対称性の階層 (Information Asymmetry Hierarchy)

| 階層 | 参加者 | 情報源 | 遅延 | 我々の位置 |
|---|---|---|---|---|
| Tier 1 | Prop/HFT | Direct feed, L2 order book, tick-by-tick | <1ms | — |
| Tier 2 | Institutional | Bilateral quotes, algo desks, dark pools | 1-10ms | — |
| Tier 3 | Semi-pro | Vendor feed, L1 + partial L2 | 10-100ms | — |
| **Tier 4** | **Retail (我々)** | **BBO only, 1-sec aggregated, public feed** | **150-500ms** | **✓** |

**帰結**: Tier 1 が使う指標 (tick volume spike, OFI) を **同じロジックで追う** と、
必ず後手。彼らは既にエグジット済みの位置にエントリーしている。

**数値化**: HFT がスパイクを検知 → ポジション → 利確まで通常 50-200ms。
我々が Python で検知 → OANDA 発注 → 約定 まで 300-500ms。
**HFT が利確した直後の price に我々がエントリー** することになる。

---

### 要因2: 市場構造の非対称性 (Market Structure Asymmetry)

#### Spread Asymmetry
- Retail: flat 0.8-1.5 pips spread (broker margin 込み)
- HFT: maker rebate により **実質 negative spread** (取引所から支払いを受ける)
- 同じ売買でも、HFT は -0.2 pips, retail は +1.0 pips → **1.2 pips / trade の構造コスト**

#### Liquidity Provider vs Taker
- HFT = liquidity provider, adverse selection で選ばれる方向にのみ約定
- Retail = liquidity taker, 常に **不利な価格で約定**
- Kyle (1985) モデル: informed trader は uninformed trader を必ず搾取する

#### Payment for Order Flow (PFOF)
- Retail 注文は broker → HFT に売られる
- HFT は「retail が買う前」に前裁きする (front-running 的構造)
- **TVSM の "2秒遅らせてエントリー" は既に HFT に露見している**

---

### 要因3: 損失の算術的必然性 (Mathematical Headwinds)

#### コスト負担率の逆算
| 戦略タイプ | 平均TP | 往復コスト | コスト負担率 |
|---|---|---|---|
| HFT (prop) | 0.5 pips | -0.4 pips (rebate) | **−80%** (利益) |
| HFT (retail-sim) | 1 pip | 1.1 pips | **110%** (構造損失) |
| Scalping (本件) | 8 pips | 2.1 pips | **26%** |
| Daytrade (既存) | 30 pips | 1.5 pips | **5%** |
| Swing | 100 pips | 1.5 pips | **1.5%** |

**スキャルピングは構造的に 25%以上のハンデを背負う**。
同じ WR なら、TP が大きい戦略ほど有利。

#### Break-even WR の悪化
- R:R = 2.0 の戦略: 損益分岐 WR = 33.3%
- コスト込み R:R = 1.5 (実際はコストで縮む): 損益分岐 WR = 40%
- 平均的な retail はコスト考慮後に BE-WR を 5-10% 押し上げられる
- これが **「勝率50%を超えているのに資産が減る」** 主因

---

### 要因4: 選択バイアスと認知歪み (Selection Bias)

#### 実証研究のコンセンサス
- **Barber & Odean (2000)** "Trading Is Hazardous to Your Wealth"
  → 積極的にtradeするほどリターンが悪化 (手数料効果)
- **Chague, De-Losso, Giovannetti (2020)** "Day Trading for a Living?"
  → ブラジルretail day trader の **97%が損失**、0.9%のみ最低賃金以上
- **Barber et al. (2014)** Taiwan day traders
  → 上位1%のみ persistent に勝ち、下位は cost で破綻

#### 情報バイアス
- SNS / YouTube / ブログで見る「scalping で勝った」は survivor
- 100人中1人だけ勝ち、その1人が発信 → 勝率50%に見える
- **事前確率**: retail scalping で年次 positive EV を達成する確率 ≈ 1-3%

---

### 要因5: 時間的非対称性 (Temporal Asymmetry)

#### Tail event の supply vs consume
- **HFT は tail を supply する** (limit order を widespread に置き、急変動で埋まる利益を得る)
- **Scalper は tail を consume する** (stop hunts で狩られる)
- 両者は **同じ値動きから反対の損益** を得る zero-sum 関係

#### Volatility smile の罠
```
小さい値動き (0.5-2 pips): HFT が取る (我々には届かない)
中間 (2-8 pips):         HFT と retail が競合 (cost負けする)
大きい (8-20 pips):      retail の TP 届くがSLも拡大、WRは維持困難
極大 (20+ pips):         retail が巻き込まれる (news spike で SL)
```

**8 pips TP は「HFT が取り切った後の残り物」か「news spike で狩られる」**
の2択になりがち。

---

## Part 2: どうすれば勝てる方法が見つかるか

### 原則: 同じ土俵で戦わない

**Tier 1 が興味を持たない場所** = retail の潜在的エッジ領域

| 次元 | Tier 1 が嫌う条件 | Retail が活用できる |
|---|---|---|
| 時間軸 | >1h の予測 (モデル不安定) | 日足/週足スイング |
| 頻度 | 1ヶ月 N<10 の戦略 | 月数回の高確度trade |
| データ | public slow data | COT, ETF flow, fundamental |
| ペア | illiquid minor cross | AUD/NZD, EUR/GBP などの micro-pair |
| イベント | 予測困難な地政学 | 予定されたイベント drift |

### アプローチA: 構造的エッジの発見 (Structural Edge)

#### A-1. 時間帯集中戦略
**仮説**: HFT は 24/7 稼働するが、retail は時間を選べる。
特定時間帯（流動性の境界、セッション移行）に WR 偏差があるか。

- 東京→ロンドン移行 (15:00-17:00 JST): ボラ+40%, spread変化
- ロンドン→NY移行 (21:00-23:00 JST): 最高流動性
- NYクローズ (05:00-07:00 JST): ボラ低下、gap形成

**検証法**: 既存データを時間帯別に分割し、各時間帯の WR / EV を計測。
有意に外れる slot を発見できれば戦略化。

#### A-2. イベント駆動戦略
**仮説**: 指標発表直後の価格反応は非線形で、"surprise" の方向に数分間のdrift。

- NFP, CPI, FOMC 発表 ±30分
- 「予想 vs 実測」の乖離率と価格反応の相関
- Drift は retail にも間に合う (HFT は瞬間反応、retail は 5-30 秒遅れでも間に合う)

**実証**: Andersen et al. (2003) "Real-time price discovery"

#### A-3. Mean Reversion at Scale
**仮説**: 日足以上のスケールでは MR が HFT にとって capacity不足で残っている。

- Bollinger Band 2σ touch + RSI extreme → 3-5日保有
- 既存の MR 戦略を 1h 足で強化し、hold を延長
- TP を 30-100 pips に拡張、コスト負担率を 5%以下に

---

### アプローチB: データ駆動のエッジ探索 (Systematic Discovery)

**現在のアプローチの欠陥**: 仮説 → 実装 → BT の順。
仮説が弱いと全BTが無駄になる。

**推奨アプローチ**: データ分析 → パターン発見 → 仮説構築 → BT

#### B-1. Conditional Return Analysis
全 1h バーのリターン分布を、以下の条件で分割:
- 過去N時間のボラティリティ (ATR percentile)
- 時間帯 (hour of day)
- 曜日
- 連続N本陽線/陰線後
- Tick volume percentile

→ 条件付き E[R] と std[R] の heatmap 作成
→ (条件付き EV > コスト) かつ (N ≥ 30) の cell を戦略化候補に

#### B-2. Regime-Conditional Performance
VIX / DXY / 前日ATR などをマクロ変数として:
- VIX percentile × DXY方向 × pair × hour の 4次元 heatmap
- 既存戦略の WR/EV を各レジームで計測
- **特定レジームで PF > 1.5 の pocket** を発見

既存 `macro-data-analysis-protocol.md` に準拠、拡張。

#### B-3. Survivor Pattern Mining
過去のトレードログを分析し、勝ちトレードのクラスタリング:
- kNN / DBSCAN でエントリー時の市場状態ベクトル（ATR, RSI, MACD, hour, vol）をクラスタリング
- 勝ちクラスタの中心と定性的特徴を抽出
- ルールベース化して未来適用

---

### アプローチC: 低頻度・高確度への転換

#### C-1. Scalping 放棄、Swing 強化
現状リソースを:
- ❌ Micro-scalp 3戦略 (TVSM/VBP/OFIMR)
- ✅ 既存 daytrade 戦略の強化 (atr_regime_break, session_bias, etc.)
- ✅ 新規 swing 戦略 (multi-day hold, 50-200 pips TP)

**根拠**: コスト負担率の逆算 (上記Part1 要因3)
- Scalping: 26%
- Swing: 1.5%
→ **同じエッジ強度なら 17倍の収益性**

#### C-2. 位置サイジングの洗練
- Kelly Fraction の厳密適用（既存システムにあり）
- Volatility targeting (constant dollar risk)
- Correlation-aware portfolio (既存の相関分析を強化)

---

### アプローチD: 差別化データソース

| データ | 入手性 | retail活用例 |
|---|---|---|
| COT レポート | CFTC公開 (weekly) | Speculator positioning の extreme で逆張り |
| ETF フロー | Bloomberg/Reuters有料、YF無料一部 | USD/JPY × UUP ETF相関 |
| Central bank balance sheet | FRED, BoJ 公開 | 日次変化とJPY反応 |
| Google Trends | 無料API | Retail sentiment proxy |
| Options IV / skew | CBOE, broker | VIX 以外のFX implied vol |

これらは HFT が **時間軸的に活用できない** 情報源で、retail の潜在的エッジ領域。

---

## Part 3: 本システムへの具体的示唆

### 現状の評価 (クオンツ的)

| 戦略カテゴリ | 構造的勝算 | 現状 |
|---|---|---|
| Micro-scalp (TVSM/VBP/OFIMR) | **低** (構造的に不利) | 新規実装、検証保留 |
| Daytrade (既存18戦略) | **中** (コスト率5%) | Live 稼働、エッジ検証中 |
| Alpha 探索 (v9.1 新3戦略) | 中 | BT完了、Shadow蓄積中 |
| Swing (未実装) | **高** (コスト率1.5%) | **未開拓エッジ** |
| Event-driven (未実装) | **高** (時間差エッジ) | **未開拓エッジ** |

### 推奨ロードマップ

#### Phase 1 (即時): Scalping 路線の整理
- Micro-scalp 3戦略は Shadow 投入せず **研究アーカイブ** として保存
- 実装済みコスト診断フレームワークは **将来の検証基盤** として維持
- リソースを Phase 2 へ振り向け

#### Phase 2 (1-2週間): データ駆動エッジ探索
- **edge-discovery framework** を構築 (次項で実装)
- 既存 Live ログ + BT 結果 に対し Conditional Return Analysis を実行
- 有望 pocket を発見 → 仮説化 → 新戦略草案

#### Phase 3 (2-4週間): Swing戦略新設
- 1日〜1週間 hold の MR / Momentum 戦略を2-3本
- 既存 daytrade システムに `swing_*` として統合
- 月利 100% ロードマップへ直接寄与

#### Phase 4 (継続): Event-driven
- NFP / CPI / FOMC の公開 calendar を自動取得
- 発表±30分に限定した drift 戦略
- 低頻度 (月数回) だが高確度を狙う

---

## Part 4: 「勝てる方法を見つける」ためのツール要件

次セッションで実装する research framework の要件:

### R-1. Conditional Return Analyzer
```python
from research.edge_discovery import ConditionalReturnAnalyzer

analyzer = ConditionalReturnAnalyzer(
    bars=live_1h_bars,
    horizon_hours=[1, 4, 24],
    conditions=["hour", "weekday", "atr_percentile", "vix_level"],
)
heatmap = analyzer.compute()  # pandas DataFrame
pockets = analyzer.find_edge_pockets(min_n=30, min_pf=1.5)
```

### R-2. Regime Performance Decomposer
既存戦略の過去トレードを、マクロレジーム別に P&L 分解。
どのレジームで勝ち、どのレジームで負けるかを明示化。

### R-3. Event Drift Profiler
指標発表カレンダー ± T分のリターン分布を、指標種別 × surprise 方向別に分析。
有意な drift が存在する event を特定。

### R-4. Out-of-sample Robustness Checker
発見した pocket が、data split で再現するかを自動検証。
Purged K-fold, walk-forward, combinatorial CV などを標準装備。

---

## 結論 — クオンツ的最終見解

1. **Micro-scalp は構造的に不利**。個別パラメータ最適化では反転しない
2. **勝ち筋は Tier 1 が興味持たない場所**: 長時間軸、差別化データ、低頻度・高確度
3. **データ駆動のエッジ探索** への移行が本質的な解決策
4. **具体的優先順位**:
   - Scalping 深追い: 停止
   - Data-driven edge discovery framework: 新設
   - Swing / Event-driven: 新戦略として開発
   - 既存 daytrade: 継続強化

**「どうすれば勝てる方法が見つかるか」の最終答: systematic edge discovery の仕組みを作り、仮説先行から脱却する。**

## 関連ドキュメント
- 設計: `micro-scalp-design.md`
- 診断: `micro-scalp-diagnostic-2026-04-17.md`
- プロトコル: `macro-data-analysis-protocol.md`
- 次ステップ: `edge-discovery-framework.md` (今後作成)
