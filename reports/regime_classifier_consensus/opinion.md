# Regime Classifier Consensus Opinion

## Verdict

**推奨: A — 現行 dow_regime tagging task は Shadow 観測として進める。ただし Phase B2.5 17 proposals は仮説であり、Live 昇格や v2 置換の根拠にはしない。**

理由は単純で、v2 と Dow は同じものを測っていない。v2 は M15 の narrow binary fire-gate、Dow は H1 の broad context tag であり、B2.5 の 5,617 BT trades では v2 `moderate_trend` が 805 件、`no_go` が 4812 件だった。Dow の 17 proposals は「classifier artifact」と断定するほど弱くはないが、「教科書値が v2 を上書きできる」と言えるほど検証済みでもない。

## Q1: 17 proposals の信頼性

信頼度は **Shadow hypothesis として中、promotion evidence として低**。B2.5 は N=5617 と大きい一方、BT 合成・single path・family coverage 34/66 の selection がある。17 proposals のうち v2 binary replay でも candidate 条件を満たした行は 24 / 34 gate-row。これは Dow の数値が完全な幻ではない一方、v2 と独立に再現したとも言えない。

## Q2: 実測根拠比較

v2 再現クエリでは N>=30 cell は 7 件だけで、`trend_up_weak` は `bb_rsi_reversion` N=142 WR=52.1% EV=+0.249 と正、`trend_down_strong`/`uncertain` は負寄りだった。一方、B2.5 は N=5,617 で proposal の見かけは強いが、Live 実測ではなく MASSIVE BT である。量は B2.5、外部妥当性は v2 production snapshot が上。結論として、**B2.5 は探索、v2 は安全側 prior** と扱うべき。

## Q3: 補完設計の妥当性

`dow_regime` と `v2_regime` の両方を tag して後で prediction power を比較する設計は **健全**。ただし条件はある。Dow tag を即 gate として universal に使わず、`entry_type × dow_regime × v2_regime` で Shadow N>=30 を積み、同一期間・同一 execution path で EV/PF/Wilson を比較すること。ad hoc hedge ではなく、competing predictors の forward test として扱えば妥当。

## Q4: 推奨行動

**A を選択**。Dow tagging は止めない。理由は 17 proposals に十分な探索価値があり、Shadow なら downside が限定されるため。ただし Phase E は「Dow classifier 勝利」ではなく「Dow-derived hypotheses の Shadow-first validation」と明記する。B は v2 の小標本 prior を過大評価、C は今ここで合成 classifier を設計すると二重に overfit、D は探索価値を捨てすぎ。

## Key Evidence

- v2 live snapshot query output: `reports/regime_classifier_consensus/v2_recalibration.csv`
- H1 Dow vs M15 v2 matrix: `reports/regime_classifier_consensus/dow_vs_mtf_crosstab.csv`
- 17 proposals v2 replay: `reports/regime_classifier_consensus/v2_replay_17_proposals.csv`
- v2 thresholds used: ADX 18.0-25.0, Hurst 0.75-0.95, nonzero EMA slope.

## Crosstab Counts

| dow_regime | moderate_trend | no_go |
| --- | --- | --- |
| CHOP | 481 | 2808 |
| RANGING | 226 | 934 |
| TRENDING | 98 | 1070 |

## Risk

最大リスクは B2.5 が `app.run_daytrade_backtest` path 固有の BT artifact で、production runtime と発火 universe が違うこと。次点は v2 snapshot が Live N=462 起点で、古いラベル・戦略 mix・期間依存の prior にすぎないこと。従って、どちらも単独 SSOT にしてはいけない。
