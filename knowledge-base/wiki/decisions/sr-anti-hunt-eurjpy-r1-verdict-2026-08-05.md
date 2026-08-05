# sr_anti_hunt_bounce × EUR_JPY R1 昇格判定: NO-GO → forward 確認 pre-reg 転換 (2026-08-05)

## Status
**VERDICT: R1 昇格 NO-GO (起案せず)** — live 変更なし。forward 確認枠 (registry `sr-anti-hunt-eurjpy-buy-forward-confirm`) へ転換。
副産物: **BT ハーネス整合破綻の発見 (R3 調査タスク発行)**。

## 経緯
[[quant-eval-2026-07-31]] §6 Next Action #3 (user「進めて」承認 2026-08-05) に基づく R1 パケット起案。
起案動機 = shadow 全数監査で WR vs BEV 二項検定 p=2.2e-11 (Bonferroni m=102 最有力)。

## 精査結果 — 起案動機の減衰 (3 並行ディスカバリ + 事前宣言ゲート BT)

### 1. shadow 証拠の再監査 (〜2026-08-05, N=71 = live 4 + shadow 67)
| 系列 | N | WR (Wilson lo) | EV | 備考 |
|---|---|---|---|---|
| shadow 全体 | 67 | 71.6% (59.9) | +4.07p | p(WR>BEV)=2.6e-10 |
| **shadow dedup_violation=0 のみ** | **44** | **65.9% (51.1)** | **+2.69p (t p≈0.094 = n.s.)** | 23/67 が同一分内重複 emit = 擬似反復 |
| live | 4 | 25.0% | −1.75p | shadow と符号逆 |

- **月次符号 +2/−3**: 累計 +272.4p のうち 2026-05 単月が +325.7p — **5月除外で残余 −53.3p** (一山型)
- 方向片側性 (BUY +329p / SELL −56.8p) と Tokyo 集中 (+299.6p) は再確認 — thesis 自体は生存
- **結論: 「WR>BEV」は dedup 後も Bonferroni 頑健、「EV>0」は独立 N 基準で未達**。促進判定は EV 軸 — WR 単独 PASS は 04-22 TP-hit 分析の「高 WR だが Kelly<0」型と同型

### 2. 365d cell-conditional BT (事前宣言ゲート: BUY N≥30 ∧ EV_R>0 ∧ Wilson_lo>33.7%)
`tools/sr_anti_hunt_eurjpy_cell_bt_2026_08_05.py` (2026-05-05 A/B ハーネスの strategy-only compute patch を流用、
production daytrade BT path、`raw/bt-results/sr-anti-hunt-eurjpy-cell-bt-2026-08-05.json`):

| run | N | wins | WR | EV_R |
|---|---|---|---|---|
| v2_off | 82 | **0** | **0.0%** | −8.30 |
| v2_on | 60 | 1 | 1.7% | −8.73 |

**⚠️ この数字は gate に使用しない — ハーネス整合破綻を検出**:
同一ハーネス・同一戦略コードの 2026-05-05 実行は EUR_JPY **N=139 WR=84.9% EV_R=+2.95 PF=3.52**。
365d 窓は約 9 ヶ月重複しており、84.9%→0.0% の反転は regime では説明不能 = **app.run_daytrade_backtest
側の 5〜8 月の変更 (exit overlay/BE_LOCK code-close/clamp 等) との機械的不整合**。平均損失 8.6R
(anti-hunt SL の ATR 倍率換算) も単位整合の破綻を示唆。→ 教訓「分析ツールは正しい出力が返ることを
検証してから使う」該当。**R3 調査タスク発行済み** (どちらの run が正か未確定 — 05-05 の 84.9% も
BE/trail 水増し (~20pp) + bt-live 乖離 (live 4月 N=8 WR25%) の疑いが既記録)。

### 3. KB 整合
- **ban なし** (falsified 6 系統に不含、T11 自身が estimand 区別を明文化)
- ただし **T11 R3 CLOSE (2026-07-11)** が記録済み: EUR_JPY は MFE/MAE pooled 非対称なし (BUY split h96 1.2 < 選抜床 1.3)。今回 NO-GO のため supersede 不要 — forward 枠 PASS 時に再訪
- shadow データ汚染 (メタ列 null) は still-open だが、outcome/pnl 整合は 67/67 一致を実測確認済み
- USD_JPY の N≥30 蓄積枠 (`ws3-t11-anti-hunt-usdjpy-recheck`) とは別セル・別枠

## 判定根拠 (Rule 1 要件との対照)
| R1 要件 | 状態 |
|---|---|
| 365d BT PASS | ❌ 評価不能 (ハーネス破綻、両方向の数字とも棄却) |
| or Live N≥30 | ❌ N=4 (かつ負) |
| Bonferroni | △ WR 軸のみ PASS、EV 軸は独立 N で n.s. |
| Pre-reg LOCK | (前提未達のため到達せず) |

**vix pilot (本日 demote 執行済み) の失敗構図 — 「shadow 正 + BT 正 + live 薄」で昇格→崩壊 — より
さらに弱い証拠での昇格は、同じ失敗の再生産である。**

## Forward 確認 pre-reg (本日 LOCK — セル定義の観測前凍結)
- **セル**: sr_anti_hunt_bounce × EUR_JPY × **BUY** (方向はここで凍結。Tokyo 条件は付けない —
  さらなる sub-cell 切りは vix Overlap の selective inference 前例により禁止)
- **母集団**: `dedup_violation=0` の shadow rows のみ (擬似反復除去)、**2026-08-05 以降の新規** (fresh OOS)
- **判定**: fresh N≥40 到達時に 1 回限り — ①EV>0 (片側 t, p<0.05) ∧ ②Wilson_lo(95%) > BEV+5pp=38.7%
  ∧ ③凍結後月次符号 ≥3/4。全通過で R1 パケット再起案 (その時点で BT ハーネス修復済みが前提)、
  不通過で本セルもクローズ
- **期限**: 2027-02-28 (未達なら stale レビュー)。それまで**本セル×outcome の中間再計算禁止 (P-10 型)**
- registry: `sr-anti-hunt-eurjpy-buy-forward-confirm`

## Related
- [[quant-eval-2026-07-31]] / [[ws3-t10-t11-entry-quality-diagnosis-2026-07-11]] / [[vix-pilot-early-demote-2026-08-03]]
- raw/bt-results/sr-anti-hunt-eurjpy-cell-bt-2026-08-05.json / bt-results/sr_anti_hunt_bounce-shadow-redesign-v2-2026-05-05.json (乖離ペア)
