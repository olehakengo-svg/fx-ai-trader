# Lesson: 救済不能 (DEAD) 戦略の特徴 — fib_reversal / macdh_reversal (2026-04-25)

## 起こったこと

R&D 解剖 ([[rd-target-rescue-anatomy-2026-04-25]]) で N≥100 級の負EV 戦略 7つを
3 アプローチ (RR再構築 / Time Decay / 極限フィルター) で救済可能性評価.

そのうち **fib_reversal** と **macdh_reversal** は全アプローチで救済不能 (DEAD) と判定:

| 戦略 | N | EV | A: RR | B: Time | C: Cell | 結論 |
|---|---|---|---|---|---|---|
| fib_reversal | 269 | -0.59 | NO | NO (cum_EV 最大 -0.59) | **0 cells** | **DEAD** |
| macdh_reversal | 134 | -1.13 | NO | NO (cum_EV 最大 -1.13) | **0 cells** | **DEAD** |

(参考) 救済可能だった戦略:
- bb_squeeze_breakout: Approach C で 1 cell (USD_JPY × London × TBEAR), 後 BT で REJECT
- sr_channel_reversal / engulfing_bb / stoch_trend_pullback: Approach C で 3 cells

## DEAD 戦略の共通特徴 (パターン抽出)

### 1. **MFE 中央値が極端に低い** (med MFE < 1pip)

| 戦略 | med MFE | 達成可能 RR | 必要 RR (BE) |
|---|---|---|---|
| fib_reversal | 0.60 | 0.14 | 3.72 |
| macdh_reversal | **0.00** | **0.00** | **6.88** |

→ 「TPに届く前に折り返す trade が大半」= 順張りでも逆張りでも edge が即時消滅.

macdh_reversal は **med MFE = 0.00** = 半数以上の trade が **エントリー直後に逆行**.

### 2. **Pair × Session × Regime の全 27 cell で EV>0 が 0 個**

通常の戦略は最低でも 1-3 cell で局所 EV+ が見つかる (生存者バイアス込みでも).
DEAD 戦略はそれすら無い = **特定条件でも edge が立たない構造**.

### 3. **Time Decay が機能しない**

他の救済対象戦略は hold≥20m bin で EV+ 転換するが (生存者バイアス込み):
- engulfing_bb: hold 10-20m EV+0.46
- stoch_trend_pullback: hold 20-40m EV+2.56

DEAD 戦略は全 hold ビンで EV<0 (cum_EV 累積も負):
- fib_reversal: hold 20-40m bin EV+2.46 (生存者ベース) but cum_EV 最終 -0.59
- macdh_reversal: hold 20-40m bin EV+2.27 but cum_EV 最終 -1.13

→ 早期負けの累積 (>2pip 損) が後半勝ちでカバーできない.

## 教訓

### 1. DEAD パターン認識の ROI が高い

DEAD 戦略は早期に判定できる軽量チェック (RR 必要値 > 5 + cell 救済 0) で **3 アプローチ
回す前に絞り込み可能**. 計算コストの大幅削減.

### 2. DEAD 戦略は `_FORCE_DEMOTED` の最有力候補

Live N の継続蓄積でも **構造的に edge が出ない** ことが BT で示されているため、
Shadow 維持コストすら無駄. 完全停止 (`_FORCE_DEMOTED`) が合理的.

### 3. 戦略追加時の DEAD 早期発見ガード

新戦略追加時に **N=30 到達時点**で以下の自動チェックを推奨:
- med MFE < 1pip → 警告
- 必要 RR > 5 → 警告
- 全 cell EV<0 → 即時 Shadow 強制

これは [[lesson-reactive-changes]] と整合する規律 (新戦略の即時 deploy 禁止).

### 4. macdh の特殊性

macdh_reversal は **med MFE = 0.00** という極端値で、これは MACD ヒストグラム反転
シグナルが**lookback バイアス**で過適合していた可能性を示唆. 過去の MACD reversal は
事後的に意味付けられるが、リアルタイムでは予測力ゼロ.

## 推奨アクション (本セッションでは未実施 — 次セッション)

1. `_FORCE_DEMOTED` への追加 (commit 別途, time_floor BT 完了後の統合判断と一括)
2. 戦略 README ([[fib-reversal]], [[macdh-reversal]]) に "DEAD: forced demoted at 2026-04-XX" 注記
3. lesson 起案後の振り返り — N=269/134 もある戦略でも構造病理は救えないという事実を index.md に明記

## 関連

- [[rd-target-rescue-anatomy-2026-04-25]] (本 lesson の根拠)
- [[bb-squeeze-rescue-result-2026-04-25]] (DEAD ではないが REJECT)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (DEAD でない戦略の救済幻想)
- [[lesson-reactive-changes]] (戦略改廃の規律)
- [[external-audit-2026-04-24]] (構造病理の優先対処と整合)
