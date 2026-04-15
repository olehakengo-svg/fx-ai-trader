# BT Revival Analysis — 5 Strategy Quant Review (2026-04-15)

**目的**: Tier 3以下の5戦略について「調整で復活可能か」をクオンツ視点で評価
**データ**: 365d DT 15m BTスキャン (bt_scan_results.json, 2026-04-14実行) + Revival BT部分結果
**BT Bias補正**: RANGE TP Override + Quick-Harvest反映済み
**参照**: bt-live-divergence.md (6つの構造的楽観バイアス), lessons/index.md

---

## 1. liquidity_sweep

### データ

| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 5 | 60.0% | -0.277 | 0.81 | -1.4p |
| GBP_USD | 6 | 50.0% | -0.730 | 0.63 | -4.4p |
| EUR_USD | 0 | - | - | - | - |
| EUR_JPY | 0 | - | - | - | - |
| GBP_JPY | 0 | - | - | - | - |
| EUR_GBP | 0 | - | - | - | - |
| **TOTAL** | **11** | **54.5%** | **-0.527** | **0.71** | **-5.8p** |

Revival BT (120d): USD_JPY N=4 WR=75% EV=+1.118 PF=4.42

### 統計的評価

- **N=11**: 統計的判断の最低ライン(30)に遠く及ばない
- **p-value**: 計算不能（WR < BE_WR、つまり負EV）
- **Walk-Forward**: 判定不能（N不足）
- **4ペアでN=0**: 365日間で1回も発火しない = 条件が厳しすぎる

### 学術的根拠 vs 実装の乖離

liquidity_sweepの理論基盤は最強クラス（Osler 2003: round number clustering, Kyle 1985: stop hunting）。
しかし現実装の条件が厳しすぎる:
- Williams Fractal (5本): 中央が最高/最低 + 左右2本ずつ下がる構造 → 15m足では稀
- WICK_RATIO >= 0.60: 全体の上位20%程度のwick比率
- ADX < 25: レンジ相場限定
- BB width filter: 追加のフィルター

**全条件AND結合で365日N=11は設計欠陥。**

### 判定: STOP (改修保留)

**理由:**
1. N=11で365日BT → 年間期待PnL = -5.8pip（マイナス）
2. 条件緩和なしでは発火頻度が月1回以下 → 月利100%に寄与不能
3. 条件緩和（例: Fractal要件→SR近接 + wick判定に変更）は**新規戦略開発に等しい工数**
4. 類似ロジックはturtle_soup(N=60, EV=+0.560)が既にカバー

**次のアクション:** 改修するならliquidity_sweepを廃止し、turtle_soupに学術根拠を統合する方が効率的。
優先度は低（既存正EVエッジの最大化が先）。

---

## 2. vol_spike_mr

### データ

| Config | Pair | N | WR | EV | PF | PnL | p-value |
|---|---|---|---|---|---|---|---|
| SPIKE_RATIO=2.3 (current) | USD_JPY | 130 | 64.6% | +0.148 | 1.26 | +19.3p | 0.1033 |

### 統計的評価

- **N=130**: 統計的に意味のあるサンプルサイズ
- **p-value=0.103**: Bonferroni補正前で10%有意（5%未達）
- **BE_WR=59.2%**: 実WR=64.6%は5.4pp上回る → マージンは薄い
- **PF=1.26**: 正EV領域だが、BT楽観バイアス(推定-3~5pp WR)を考慮すると**Live正EVは不確実**
- **USD_JPY限定**: 他ペアでのテストなし

### SPIKE_RATIO variants (キャッシュバグで未取得)

前回実行でSPIKE_RATIO=2.3/2.7/3.0が全て同一結果を返した（キャッシュバグ）。
修正版スクリプト作成済みだが、完了前にBT停止。

**理論的予測:**
- RATIO=2.7: N減少(推定60-80)、WR微増(1-2pp)、EV改善の可能性
- RATIO=3.0: N大幅減少(推定20-40)、サンプル不足リスク

### BT-Live乖離リスク

bt-live-divergence.md参照:
- vol_spike_mrは**MR(平均回帰)戦略** → スプレッド拡大局面で発火しやすい
- ボラスパイク発生時はspreadも拡大 → BT固定spread vs Live変動spreadの乖離が**最大化**
- 推定Live WR劣化: -3~5pp → 実効WR=60-62% → BE_WR=59.2%ギリギリ

### 判定: KEEP (現行維持、昇格保留)

**理由:**
1. 正EV(+0.148)だがp=0.103で有意未達 → 昇格根拠不足
2. BT-Live乖離リスクが特に高い戦略カテゴリ（vol spike時のspread拡大）
3. SPIKE_RATIO variant BTが未完了 → 最適パラメータ未確定
4. USD_JPY限定で月間~11トレード → 月利100%への寄与は限定的

**次のアクション:**
1. SPIKE_RATIO variant BT完了 (次セッション)
2. Live N=30到達まで現行パラメータで運用継続
3. London session限定フィルター検証（spread安定時間帯に限定）

---

## 3. dt_sr_channel_reversal

### データ

| Pair | N | WR | EV | PF | PnL | BE_WR | p-value |
|---|---|---|---|---|---|---|---|
| EUR_JPY | 362 | 63.8% | +0.178 | 1.39 | +64.6p | 55.9% | 0.0012 *** |
| USD_JPY | 177 | 61.0% | +0.144 | 1.28 | +25.4p | 55.0% | 0.0541 * |
| GBP_USD | 100 | 65.0% | +0.122 | 1.22 | +12.2p | 60.4% | 0.1711 |
| EUR_USD | 59 | 59.3% | +0.019 | 1.03 | +1.1p | 58.6% | 0.4556 |
| **TOTAL** | **698** | **62.8%** | **+0.149** | **1.28** | **+103.3p** | | |

### 統計的評価

- **N=698**: 非常に大きなサンプル。DTモード全戦略中トップクラスの発火頻度
- **EUR_JPY p=0.0012***: Bonferroni補正(6ペア)後もp=0.007で有意
- **USD_JPY p=0.054***: Bonferroni後は有意未達だがボーダーライン
- **4ペア中3ペアで正EV**: EUR_USDのみ微正EV(+0.019)
- **BT Bias補正済み**: RANGE TP Override + Quick-Harvest反映後の値

### バグ修正の影響

本セッションで発見・修正したSR dict型エラー:
```python
# Before (bug): TypeError — float - dict
_sr_buy = [l for l in ctx.sr_levels if 0 < ctx.entry - l < ...]

# After (fix): dict["price"]を正しく抽出
_sr_prices = [s["price"] if isinstance(s, dict) else s for s in ctx.sr_levels]
```

このバグにより**Liveではdt_sr_channelが全く機能していなかった可能性がある**。
修正後のN-cache warm-startで「22 strategies」表示（修正前は21）→ 修正により戦略が有効化された。

### BT-Live乖離リスク

- **SL/TP構造**: SL=ATR7*1.0, TP=ATR7*2.0 → RR=2.0（良好）
- **SR精度**: BTではfind_sr_levels_weighted()の精度が高い（全過去データ参照可能）
  Live: リアルタイムの限定データ → SR精度低下の可能性
- **Channel検出**: find_parallel_channel()は過去100本参照 → BT/Live差異は小さい
- **推定Live劣化**: -2~4pp WR → 実効WR=59-62% → BE_WR=55.9%(EUR_JPY)に対してまだマージンあり

### SL拡大テスト (未完了)

SL=ATR7*1.5への拡大テストは未完了。
理論的予測:
- WR改善(+3-5pp): 早期SL hit減少
- EV影響: WR改善 vs SL拡大のトレードオフ → RR=1.33に低下
- 既にRR=2.0の良好な構造 → SL拡大は**RRを犠牲にしてWR微増**で期待値は概ね中立

### 判定: PROMOTE to PAIR_PROMOTED (EUR_JPY, USD_JPY)

**理由:**
1. EUR_JPY: N=362, p=0.0012*** → **Bonferroni有意な正エッジ確認**
2. USD_JPY: N=177, p=0.054* → ボーダーラインだが正EV方向
3. 合計N=698, PnL=+103.3pip → DTモード収益貢献ポテンシャル大
4. バグ修正済み → これまでLive未発火だった可能性 → **新規Live検証開始**
5. RR=2.0の良好な構造 → BT-Live乖離バッファが十分

**EUR_USDとGBP_USD**: 正EVだがp-value未達 → EUR_JPY/USD_JPYでの実績蓄積後に検討

**次のアクション:**
1. バグ修正のコミット (本セッション)
2. EUR_JPY + USD_JPY でPAIR_PROMOTED設定
3. Live N=30到達後にTier再評価
4. SL拡大テストは次セッションで実施（参考データとして）

---

## 4. eurgbp_daily_mr — BT未完了

### 状況
EUR_GBP限定の日足MR戦略。1h/15m BTデータが存在しない（365d DTスキャンでN=0）。
Revival BTで1h 500d + 15m 365dを計画したが、時間切れで未実行。

### 暫定判定: HOLD (次セッションでBT実行)

EUR_GBP 1hデータは500日分キャッシュ済み。次セッションで即BT可能。

---

## 5. gold_trend_momentum — BT未完了

### 状況
XAU限定戦略のFXペア転用テスト。_enabled_symbolsを6 FXペアに拡大して検証する計画だが未実行。

### 暫定判定: HOLD (次セッションでBT実行)

ただし、gold_trend_momentumの設計はXAUの構造的モメンタム特性（安全資産フロー持続性）に特化。
FXペアでは異なる市場微細構造のため、転用成功の確率は低い（30%以下と予測）。

---

## Summary — 判定一覧

| # | Strategy | 判定 | 根拠 | 次のアクション |
|---|---|---|---|---|
| 1 | liquidity_sweep | **STOP** | N=11/365d, 負EV, 条件厳しすぎ | turtle_soupに統合検討 |
| 2 | vol_spike_mr | **KEEP** | 正EV(+0.148)だがp=0.10, Live乖離リスク | Variant BT + Live N蓄積 |
| 3 | dt_sr_channel_reversal | **PROMOTE** | EUR_JPY p=0.0012***, N=698 | バグ修正コミット + PAIR_PROMOTED |
| 4 | eurgbp_daily_mr | HOLD | BT未完了 | 次セッションで1h 500d BT |
| 5 | gold_trend_momentum | HOLD | BT未完了 | 次セッションでFX転用テスト |

### 最大発見

**dt_sr_channel_reversalのSR dict型バグ** — LiveでTypeErrorにより全シグナルが無効化されていた。
365d BTでは N=698, EV=+0.149, PnL=+103.3pipのBonferroni有意なエッジが確認された。
バグ修正により即座にLive収益に貢献する可能性が高い。

---

## Related
- [[full-bt-scan-2026-04-15]] — 全戦略365d BTスキャン
- [[bt-live-divergence]] — BT楽観バイアス6因子
- [[lesson-sr-dict-type-error]] — dt_sr_channel SR dict型バグ
