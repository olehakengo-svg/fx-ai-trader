# Lesson: 5m Pure Edge の構造的失敗 — 6/9 DEAD + 3/9 N抑制 SURVIVOR 兆候 (2026-04-25)

## 背景

Phase 5 R&D で 9 純粋エッジ戦略を [Gate -1 (TAP)](lesson-toxic-anti-patterns-2026-04-25.md)
完全排除で設計し、各々を独立 pre-reg LOCK + Bonferroni 補正 + 365日 BT で検定.

**結果: 6/9 DEAD + 3/9 SURVIVOR 兆候 (N不足で Bonferroni 不通)**

## 9 戦略 BT 結果 (108 cells 検定)

| # | 戦略 | カテゴリ | N | WR | EV | Verdict |
|---|---|---|---|---|---|---|
| S1 | Session Handover | レンジ盾 | 1023-1908 | 28-40% | -2.9〜-4.5 | **DEAD** |
| S2 | Vol Compression | トレンド剣 | 1779-14335 | 2-4% | -2.8〜-3.1 | **DEAD** |
| S3 | Z-Exhaustion | カウンター | 85-326 | 10-19% | -0.6〜-9.2 | **DEAD** |
| S4 | Pure Divergence | カウンター | 113-581 | 27-33% | -2.1〜-4.8 | **DEAD** |
| **S5** | VWAP Defense C03 | トレンド剣 | **5** | **60%** | **+4.69** | **N不足 SURVIVOR 兆候** |
| S6 | VA Reversion | レンジ盾 | 381-848 | 33-35% | -1.4〜-1.7 | **DEAD** |
| **S7** | ORB | トレンド剣 | **0-5** | **60-100%** | **+23〜+82** | **N不足 SURVIVOR 兆候** |
| S8 | FVG | カウンター | 42-880 | 25-34% | -1.3〜-7.6 | **DEAD** |
| **S9** | VSA C09 | カウンター | **26** | **57.7%** | **+4.00** | **N不足 SURVIVOR 兆候** |

## 構造的失敗の物理的原因

### 1. DEAD 6 戦略の共通パターン: false positive 海

DEAD 戦略は全て **N が異常に大きい** (113-14335件). 5m bar level で binary 閾値 trigger
が**過剰発火**し、大半は random walk noise の偶発的越え:

- S2 Compression: BB 抜き = 大半が wick による瞬間越えで実体は band 内に戻る
- S4 Divergence: RSI 極限+swing div = 偶発パターン
- S6 VA Reversion: VA 外への逸脱は大半が短期 noise
- S8 FVG: 3-bar gap 形成は random walk で偶発的に発生

p_welch = 0.0000 で**統計的に損失方向で有意** = ノイズではなく構造的負 EV.

### 2. SURVIVOR 兆候 3 cluster の共通点: **N≤30 の極限値 AND 結合**

| Cluster | 条件 | 物理的意味 |
|---|---|---|
| S5 C03 | EUR/USD × pullback 1.5ATR × **VWAP+EMA50_HTF BOTH touch** | 機関大口 二重防衛線 |
| S7 ORB | GBP系 × 時刻 + Asia range break + **vol×2.5** | macro flow + 時刻 + 流動性 急増 |
| S9 C09 | USD/JPY × **vol×3 + body<0.3** | Wyckoff absorption 二重 extreme |

→ **「3 binary 条件以上の AND 結合 + 物理的極限値」**で N が抑制されると Edge 兆候.

## 直感の罠 — Mean Revert/Breakout 仮説の連続否定

3 戦略で**仮説の方向が逆**だったことが p_welch=0.0000 (損失方向有意) で証明:

| 戦略 | 仮説 (逆張り/順張り) | 実態 |
|---|---|---|
| S1 Handover | session wick reject = mean revert | swing 抜き後は **継続トレンド** |
| S2 Compression | squeeze 抜き = breakout | 大半が **false breakout で reversion** |
| S3 Exhaustion | z>3σ = mean revert | **トレンドの加速** (continuation) |

**5m FX では「直感的 mean revert / breakout」は機能しない**. 統計的 noise を pattern と
誤認する人間の認知バイアス (apophenia).

## Time-Floor の悪化定量証明

[time-floor-meta-rescue 35 cells](time-floor-meta-rescue-2026-04-25.md) で 7 戦略の
hold floor を 0/5/10/20/30 分で検定:

| 戦略 | floor=0 EV | floor=30 EV | MAE!% (30) |
|---|---|---|---|
| ema_trend_scalp | -3.55 | **-4.44** | 16.3% |
| fib_reversal | -3.03 | **-4.01** | 16.5% |
| stoch_pullback | -2.99 | **-3.96** | 17.5% |
| bb_squeeze | -4.39 | **-5.24** | 14.3% |

→ 全 7 戦略で hold 増加で EV 悪化, MAE_BREAKER 14-17% (=20分耐えられず吹き飛び).
[lesson-survivor-bias-mae-breaker](lesson-survivor-bias-mae-breaker-2026-04-25.md) の
事前懸念が**完全実証**.

## 教訓

### 1. 5m FX で Edge を作るには「N 抑制」が必須

ROI の高い戦略設計の鉄則:
- **3 binary 条件以上を AND 結合** (S5 BOTH touch, S7 時刻+range+vol, S9 vol+body)
- **各条件は物理的極限値** (vol×3 など, 普段ほぼ発火しない)
- 月間 N ≤ 5-10 で良い (高 RR で年間 PnL を補完)

### 2. 直感的「mean revert / breakout」は罠

- p_welch = 0.0000 で**損失方向有意** = 構造的に逆方向のエッジが存在する可能性
- 直感 = 訓練データ (人間の経験) のバイアス, 5m FX の真の物理は別

### 3. Time-Floor は逆効果

- hold floor を増やすと EV 悪化
- pre-reg 時の **MAE_CATASTROPHIC_PIPS=15 防衛コード**で生存者バイアス検出可能
- 「20分耐えれば勝てる」は**集計バイアス**で、実態は耐えられない

### 4. 「広く撒く」設計は禁忌

- N が大量 (>500) なら戦略を疑え
- false positive 海は Bonferroni で守れない (大量 sample で偶発的勝ちが出るが平均 EV は負)

## Phase 5 の実用的成果

### 副次仮説候補 3 cluster (HARKing 慎重に, 次セッション LOCK 検討)

1. **S7 ORB** (GBP系 × 時刻 + vol×2.5)
2. **S9 VSA** (USD/JPY × vol×3 + body<0.3)
3. **S5 VWAP BOTH** (EUR/USD × VWAP+EMA50_HTF 両方 touch)

これらは **2年データ拡張 + 関連 PAIR 拡張**で N≥20-30 確保した独立 pre-reg LOCK で
再検定すべき. **本日の data look 後の仮説調整は HARKing 違反**, 次セッションで data-look-blind LOCK.

### Phase 5 凍結勧告

S4-S9 の主軸 4 戦略 (S5/S6/S7/S8) を pre-reg LOCK したが、**6/9 DEAD という結果**を
受け、Phase 5 全体の追加 pre-reg は**最低 1 ヶ月凍結**を推奨:

- 「Pure Edge」概念自体の限界が露呈
- 次の試行は「N 抑制 AND 結合パターン」の詳細解明から
- 独立検定済み 3 SURVIVOR 兆候を生かす方向

## 関連
- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1 / TAP)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (MAE Breaker 実証)
- [[lesson-dead-strategy-pattern-2026-04-25]] (DEAD パターン)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1 適用)
- [[phase5-pure-edge-portfolio-2026-04-25]] (S1-S3)
- [[phase5-extended-s4-s9-2026-04-25]] (S4-S9)
- [[phase5-9d-edge-matrix-2026-04-25]] (PAIR×Session 統合)
