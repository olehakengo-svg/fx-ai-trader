# BT ハーネス整合破綻の R3 調査 — phantom-loss 記帳と BE/Trail default 反転 (2026-08-05)

**Status**: ✅ 原因確定 + 修正 deploy (rule:R3)
**Trigger**: [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] §BT — 同一ハーネス (production daytrade BT path + strategy-only compute patch) が sr_anti_hunt_bounce×EUR_JPY で 05-05: N=139 WR=84.9% EV=+2.95 → 08-05: N=82 WR=0.0% EV_R=−8.30 に反転。365d 窓は約 9 ヶ月重複しており regime では説明不能。

## 1. 結論 (原因は 2 層 + 増幅器 1 つ)

| 層 | 内容 | 該当コード |
|---|---|---|
| **反転の直接原因** | commit `d87d5b6c` (2026-05-15) が `_BT_ABLATE_BE_TRAIL` default を True に反転 (TV-aligned)。05-05 run は旧 default (BE/Trail ON)、08-05 run は新 default (OFF)。**app.py の変更であり市場の変化ではない** | app.py `run_daytrade_backtest` `_BT_OPTIMISTIC` / `_BT_ABLATE_BE_TRAIL` |
| **WR 84.9% 側の虚構** | BE/Trail ON 時、+0.8ATR 到達で BE 発動 → その後の SL touch を **WIN, tp_m=0.6×TP距離** として計上。TP≈10ATR の本戦略では 1 勝 = 架空 +6R 級。既知の +20pp inflation (MEMORY `project_be_trail_inflates_python_bt_wr`) の極端例 | 同 BE/Trail WIN 分岐 |
| **WR 0.0% / −8.3R 側の虚構 (phantom-loss)** | BE/Trail OFF でも **Time-decay SL tightening** (MAX_HOLD×0.5=12bar 経過 + 含み益で SL→entry) は生きている。この疑似ストップ退出 (実損≈0) を、`actual_sl_m` が「fut_close が**元の** SL を超えた時のみ設定」のため **planned sl_m のフル損失として記帳** | 旧 LOSS 記帳分岐 (今回修正) |
| **増幅器: SL 再計算** | sr_anti_hunt は `_DT_PRESERVE_SLTP` 非対象 → BT は戦略 SL (P90 49pip+0.5ATR≈53pip) を**破棄**し SL = QH 前 TP距離/1.2 を再計算。TP≈100-140pip (RR2.0×anti-hunt SL) なので **sl_m = 6.5〜11 ATR**。phantom-loss 1 件 = −6.5〜−11R | app.py MIN_RR_DT=1.2 分岐 |

## 2. 実証 (trade-level dump、180d 窓 A/B — 修正前ハーネス)

同一エントリー母集団 (第 1 トレード 2026-01-30 05:00 が両モードで同一) に対し:

| モード | N | WR | EV_R | 内訳 |
|---|---|---|---|---|
| ABLATED (現 default = 08-05 と同条件) | 28 | **0.0%** | **−8.43** | 全 28 件 LOSS、`actual_sl_m: null` (=planned sl_m 6.5〜11.1 で記帳)、bars_held **12〜17 に集中** = decay 閾値 12bar 直後 |
| OPTIMISTIC (旧 default = 05-05 と同条件) | 46 | **76.1%** | **+1.48** | WIN 35 件は tp_m 2.3〜4.4 = BE/Trail の 0.6×TP credit。TP 実到達はほぼゼロ |

- sl 内部整合の確認: trade#1 の sl_dist=1.348 = QH 前 tp_dist 1.617/1.2 (表示 tp 1.375 は QH ×0.85 後) — SL 再計算経路の実証
- N 差 (46 vs 28): ablated は BE/Trail 退出が消えるため MAX_HOLD 内に TP/SL 未到達のトレードが **記録されず脱落** (survivorship、§5-c)
- 05-05 → 08-05 の関数全 diff 精査: このセルに作用する変更は `d87d5b6c` のみ (cache_key 拡張 / exit-repair hook / max_hold time-exit / SR weighted dict 化は全て no-op)

## 3. どちらが本番 demo_trader に忠実か → **どちらも忠実ではない**

本番 live の実挙動 (modules/demo_trader.py):
- **ATR×0.8 BE (SL→建値+spread) + ATR×1.5→trail ATR×0.5 は現在も稼働中** (code-close されたのは MFE BE_LOCK A/B のみ。ATR-BE/trail とは別物)
- live は戦略 SL を保存して送信 (app.py `_dt_best.sl` 流用。TP は SR snap / RR1.3 リライトの可能性あり)
- live の BE 退出の実現損益は **≈0 − friction** — 「+0.6×TP」でも「−planned SL」でもない

つまり:
- 05-05 (optimistic): **機構は live に近い** (BE/trail あり) **が会計が楽観虚構** (BE 退出→+0.6×TP)
- 08-05 (ablated): **会計も機構も悲観虚構** (BE/trail 無し + BE 相当退出→−フル sl_m)
- 真実はその間: このセルの意味のある判定は **TV Pine canon か shadow live N** でのみ可能 (KB 規律 Live > TV > Python BT の再確認)

## 4. 修正 (この commit、rule:R3)

**LOSS 記帳を実効ストップ基準に変更** — daytrade / scalp 両エンジン:
- gap-through 判定を `sl` (planned) → `_dt_current_sl` / `_current_sl` (実効) に変更
- gap なし退出でも `actual_sl_m = |ep − 実効stop| / ATR` を**必ず**設定 (planned sl_m への silent fallback を排除)
- `time_exit_*` は sl_m を実測距離へ rebase 済みのため対象外、`signal_reverse` も従来通り対象外
- 併発バグ修正: tools/sr_anti_hunt_bounce_shadow_bt.py `_pnl_r` の `or 1.0` falsy ガードが**正当な actual_sl_m=0.0 を 1.0 に coerce** (None ガードは `is None` で行うこと — 教訓「0 は falsy」)
- 回帰 pin: `tests/test_effective_stop_loss_booking.py` (AST 構造、4 tests)。全 suite 2521 passed
- 修正後 180d 再実行 (実測): ablated EV_R **−8.43 → −0.605** (N=28 / WR 0% は不変 — decay 退出は −friction 級 LOSS のままが正しく、残る負値は gap-through 実損と signal_reverse −4.1R)。optimistic 側は EV_R +3.50 — WIN credit 虚構は不変 (legacy 比較モード、default 到達不能)

非対象エンジン: `run_backtest`(1H) は default で `_current_sl` 不動 (BE gate 済み + decay 無し) のため非発現、`run_1h_backtest` は既に close-based 記帳。

## 5. 修正**しない**ことにした既知の乖離 (将来の R1 インフラ課題として記録)

a. **ablated BT の WR は wide-TP 戦略で構造的に ≈0** — TP≈10ATR は MAX_HOLD=24bar 内に到達せず、BE/trail WIN も無いため、勝ち経路が signal_reverse しかない。**wilson_lo > BEV 型の R1 ゲートを ablated daytrade BT に適用できるのは TP ≲ 2ATR 級の geometry のみ**。wide-TP 戦略の cell BT 判定は TV Pine / shadow live を使うこと
b. **SL 再計算 (TP/1.2) と live (戦略 SL 保存) の乖離** — `_DT_PRESERVE_SLTP` 拡張は per-strategy の検証が必要 (R1 級)
c. **TP/SL 未到達トレードの無記帳脱落** (survivorship) — live は必ずいつか決済される
d. **optimistic モードの 0.6×TP WIN credit** — legacy 比較専用、default 到達不能のため放置

## 6. 過去 verdict への影響監査

- **08-05 cell BT (raw/bt-results/sr-anti-hunt-eurjpy-cell-bt-2026-08-05.json)**: gate FAIL の結論は維持 (forward 枠転換済み) だが、**EV_R=−8.30 という数値は今後一切引用禁止** (phantom-loss 産物)。WR 0% も §5-a により evidence 能力なし
- **05-05 shadow-redesign-v2 BT**: WR84.9%/EV+2.95 は optimistic 虚構。当時の用途は shadow 昇格判定のみ (RECOMMEND_SHADOW) で live 判断には未使用 — [[audit-past-verdicts]] 恒久指示の実例として追記対象
- **d87d5b6c 以降の daytrade/scalp BT 全般**: decay 退出を含む LOSS の EV は sl_m に比例して過大悲観。**構成間の相対比較** (exit-repair grid 等、同一記帳規則下) は方向性有効だが、**絶対 EV の gate 判定**は本修正後の再計測が必要
- forward 枠 `sr-anti-hunt-eurjpy-buy-forward-confirm` (fresh N≥40) は**影響なし** — shadow 実データ基準であり BT 非依存

## 7. 教訓

- **BT の R 単位記帳 (tp_m/sl_m) は「exit が計画 TP/SL で起きる」仮定に立つ。動的 stop (BE/trail/decay) を導入した時点で、記帳は実効 stop / 実現価格基準に更新しなければならない** — 機構だけ足して会計を放置すると、geometry 次第で ±10R 級の虚構が生まれる
- ハーネス flag の default 反転 (d87d5b6c) は**過去 BT 結果との比較可能性を切断する**。反転後に「同じスクリプトの再実行」で乖離を見たら、まず flag regime を疑う (`BT_OPTIMISTIC=1` で旧 regime 再現可能)
- 平均損失が SL 設計 (R=1) から大きく外れたら (今回 8.6R)、単位・会計の破綻シグナル (WR 0% や 100% と同格の red flag)

関連: [[divergence-ablation-2026-05-14]] / [[be-trail-ablation-all-engines-2026-07-09]] / [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] / MEMORY `project_be_trail_inflates_python_bt_wr`
