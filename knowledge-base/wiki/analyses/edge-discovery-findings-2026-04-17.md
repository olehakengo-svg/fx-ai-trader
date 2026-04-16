# Edge Discovery — 初期findings (demo_trades.db 115件)

**作成日**: 2026-04-17
**データ**: ローカル demo_trades.db (N=115 closed trades)
**免責**: N が小さく統計的有意性は弱い。本番Render データでの再分析が必要。
**それでも**: 方向性の示唆として極めて価値あり。

## 全体スタッツ
- Closed N=115, Wins=52, **WR=45.2%**
- Total PnL=**+214.5 pips**, Avg=+1.87p, **PF=1.39**
- Avg hold=2.3h

→ **平均は悪くないが、条件別に分解すると勝ち負けが極端に分かれる**

---

## 発見1: 戦略別 — 4つの ELITE と 6つの捨てるべき戦略

### ELITE pockets (捨ててはいけない)
| 戦略 | N | WR | Avg | Total | PF |
|---|---|---|---|---|---|
| **fib_reversal** | 28 | **82%** | +11.78p | **+329.9p** | **5.12** |
| bb_rsi_reversion | 22 | 64% | +8.74p | +192.3p | **6.97** |
| dt_bb_rsi_mr | 3 | 100% | +10.90p | +32.7p | ∞ |
| vol_momentum_scalp | 4 | 50% | +4.30p | +17.2p | 15.33 |

**fib_reversal + bb_rsi_reversion だけで +522.2 pips** = 全利益の **243%**
（= つまり他の戦略が -300p ほど消している）

### 捨てるべき戦略 (構造的損失)
| 戦略 | N | WR | Avg | Total |
|---|---|---|---|---|
| ema_trend_scalp | 7 | 14% | -1.79p | -12.5p |
| macdh_reversal | 4 | 25% | -2.58p | -10.3p |
| sr_channel_reversal | 7 | 14% | -3.04p | -21.3p |
| bb_squeeze_breakout | 4 | 0% | -3.25p | -13.0p |
| engulfing_bb | 5 | 0% | -3.48p | -17.4p |
| **session_time_bias** | 3 | **0%** | **-12.37p** | **-37.1p** |

→ これらを **即 FORCE_DEMOTED** (OANDA送信禁止、Shadowのみ) にするだけで +110p の改善

---

## 発見2: 時間帯別 — Tokyo session が圧倒的

| Session (UTC) | N | WR | Avg | Total | PF |
|---|---|---|---|---|---|
| **tokyo (0-6)** | 45 | **67%** | **+6.13p** | **+276.0p** | **4.09** |
| london_morn (7-11) | 62 | 34% | +0.32p | +20.0p | 1.05 |
| london_ny_overlap (12-16) | 7 | 14% | -10.81p | -75.7p | 0.12 |

**Tokyo session だけで全利益の 129%** (他セッションで -61.5p 消化中)

### クオンツ解釈
1. **Tokyo session が勝つ理由の仮説**:
   - 日本市場主体 → USD/JPY のニュースdrift が予測しやすい
   - HFTの流動性提供が欧米時間より薄く、retailが "pick pennies" しやすい
   - 経済指標が少なく、ノイズが少ない
2. **London/NY overlap で負ける理由の仮説**:
   - 最高流動性帯 → HFTの支配領域
   - 指標発表のvol spike で retail SL が刈られる
   - Spread が実は狭い時間帯 = 競合激化で retail エッジ消失

---

## 発見3: 通貨ペア別 — GBP_USD が構造的敗者

| Pair | N | WR | Avg | Total | PF |
|---|---|---|---|---|---|
| **USD_JPY** | 85 | 54% | +4.13p | +350.8p | 2.42 |
| EUR_USD | 14 | 29% | +6.57p | +92.0p | 2.81 |
| **GBP_USD** | 16 | **12%** | **-14.27p** | **-228.3p** | **0.12** |

**GBP_USD は全戦略合計でマイナス**。ペア自体がこのシステムと不適合。

### 推奨アクション
- GBP_USD を全戦略で OANDA 送信停止（Shadow継続のみ）
- USD_JPY に capital 集中
- EUR_USD は WR 低いが avg 大きい → 様子見継続

---

## 発見4: 時間軸 (tf) 別 — 1m が勝ち、5m/15m が負け

| TF | N | WR | Avg | Total | PF |
|---|---|---|---|---|---|
| **1m** | 70 | **63%** | **+7.48p** | **+523.3p** | **4.50** |
| 5m | 20 | 5% | -3.45p | -69.1p | 0.05 |
| 15m | 21 | 33% | -10.21p | -214.4p | 0.31 |
| 1h | 4 | 0% | -6.33p | -25.3p | 0.00 |

**1m が全利益の 244%**、5m/15m/1h が -308p で食い潰している。

### クオンツ解釈
- **1m は daytrade ではなく "semi-scalp"** (tokyoセッション中の短期)
- **fib_reversal (ELITE)** が主に 1m で発火している → この組合せが真のエッジ
- 15m/5m は中途半端な tf: HFTには遅いが、retail のtrend follow には早い
- 1h は sample 不足 (N=4) だが WR=0% は警告

---

## 発見5: 曜日バイアス

| Weekday | N | WR | Avg | Total |
|---|---|---|---|---|
| **水 (2)** | 63 | **59%** | +2.66p | +167.4p |
| 火 (1) | 29 | 17% | +1.62p | +47.0p |
| 木 (3) | 18 | 50% | +0.39p | +7.1p |
| 月 (0) | 5 | 20% | -1.40p | -7.0p |
| 金 (4) | — | — | — | — |

**水曜が圧倒的**。火曜は WR 低いが大勝で黒字維持。月曜は少ないが負け傾向。

---

## 発見6: 「最強の組合せ」の推定

データ量不足で cross-tab を厳密に取れないが、
上記の勝ち条件を重ねると:

### Hypothetical Gold Pocket
```
条件: tokyo session × USD_JPY × 1m × fib_reversal | bb_rsi_reversion
```

Top 5 勝ちトレードの分布 (要確認) が上記条件にほぼ一致していると推定される。
本仮説を検証するため、次に Render 本番データで cross-tab 分析を実施すべし。

---

## Action Plan (優先度順)

### Tier S (即実施、Live改善)
1. **捨てるべき6戦略を FORCE_DEMOTED へ**
   - ema_trend_scalp, macdh_reversal, sr_channel_reversal
   - bb_squeeze_breakout, engulfing_bb, session_time_bias
   - 期待効果: +100〜200 pips 改善
2. **GBP_USD を Shadow専用へ**
   - 全戦略で OANDA 送信停止
   - 期待効果: -228p の構造的損失を止血
3. **London_NY_overlap の取引抑制**
   - 12-16 UTC は FORCE_DEMOTED か confidence閾値上げ
   - 期待効果: -76p の浪費止血

### Tier A (1週間以内)
4. **fib_reversal + bb_rsi_reversion を深掘り**
   - これら2戦略のパラメータ・条件を詳細分析
   - どの市場条件で最も勝つか cross-tab
5. **Tokyo session 専用戦略を新設検討**
   - 既存 ELITE 戦略を Tokyo 時間に限定するだけで PF 4+ が実現
6. **本番 Render データで analytics 再実行**
   - `demo_trades.db` のローカル N=115 → 本番 N=500+ で有意性確認

### Tier B (中期)
7. **時間帯 × 戦略の cross-tab 自動化**
   - `trade_log_analyzer.cross_tab()` を定期実行
   - 週次で edge pocket drift を監視
8. **新戦略の構築基準を変更**
   - 「仮説先行」→ **「edge discovery で pocket発見 → 戦略化」**
9. **Walk-forward validation の標準化**
   - 新戦略昇格前に必須化

---

## 本データの限界

1. **N=115** は統計的に不十分
   - 戦略別で N=3-28、信頼区間広い
   - 本番データ (500+) での再検証必須
2. **期間バイアス**: 2週間程度のデータで市場レジーム1種類
3. **XAU 除外済み** だが他の選択バイアス未補正
4. **Live 成績ではなく demo** の可能性

それでも **方向性の示唆** として、約 +300〜500p の改善余地を示唆している。

---

## 関連ファイル
- 分析ツール: `research/edge_discovery/trade_log_analyzer.py`
- 実行ログ: `/tmp/trade_analysis.txt`
- 姉妹分析: `why-retail-scalping-loses.md`
- フレームワーク: `research/edge_discovery/`
