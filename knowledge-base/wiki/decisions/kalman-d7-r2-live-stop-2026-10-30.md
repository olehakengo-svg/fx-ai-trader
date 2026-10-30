# kalman_d7 R2 live stop — pre-reg ゲート (LIVE N≥10 ∧ EV<0) 成立で live 停止 (2026-10-30、rule:R2、autopilot 執行)

**Status**: ✅ 執行 (code + tests + KB 同一 PR)。**判定**: registry `t9-kalman-d7-live-n10-ev-check` (`live_count_decision`、`n_decide` 10、prefix `kalman_d7` × USD_JPY × since 2026-08-09) が N=12 で TRIGGERED、pre-registered 条件「LIVE N≥10 到達で EV<0 → live 停止 (R2)」が**両基準 (demo gross / broker realized) で成立**。
**親決裁**: [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] 追記 (option B、退避条件「Live N≥10 達成時点 EV<0 → 0.1× へ自動降格」) → [[kalman-d7-minlot-carveout-prereg-2026-09-01]] 🔒 LOCKED (user 承認 2026-09-01) §R2 が「**LIVE N≥10 到達で EV<0 → live 停止 (R2)**、撤退は env `KALMAN_D7_LIVE_ENABLE=0` のみで即時」に確定 (1000u 固定契約と「0.1×」は両立しないため)。[[kalman-d7-carveout-postfill-packet-2026-09-17]] §3 (DRAFT) も同文。
**動機**: データ駆動 (registry の機械判定 + 10-29 wiki-daily 12:00Z 再実行が N=10 到達・EV<0 を記録、本 run で fill #12 を確認)。感情的要素なし。**Rule 2 (Fast & Reactive)** = 損失停止・降格は N=10 で即断可、autopilot 単独で執行可 (CLAUDE.md 判断プロトコル)。

## 1. 母集団と readout (本番 `/api/demo/trades?limit=5000`、2026-10-30T01:5xZ、窓は 08-04 まで遡る = since 08-09 を完全被覆)

母集団 = `entry_type` 前方一致 `kalman_d7` ∧ `instrument` USD_JPY ∧ `entry_time ≥ 2026-08-09` ∧ `oanda_trade_id` 非空 ∧ `is_shadow` 0 ∧ `dedup_violation != 1` ∧ CLOSED。shadow は数えない ([[feedback_live_vs_shadow_strict_separation]])。broker 列は OANDA `/api/oanda/transactions` の決済 `ORDER_FILL.pl` (JPY、financing 0)。

| # | fill | entry (UTC) | variant | exit | demo pips | broker ¥ | 出典 |
|---|---|---|---|---|---|---|---|
| 1 | #859468 | 09-10 17:00 | po_dn_flip | 21:05 `OANDA_SL_TP` | +8.2 | +91 | [[kalman-d7-minlot-carveout-prereg-2026-09-01]] 09-17 追記 |
| 2 | #893181 | 09-22 19:59 | po_dn_flip | 20:53 `SIGNAL_REVERSE` | −4.5 | −245 (2 本合算) | [[2026-09-24]] |
| 3 | #893189 | 09-24 03:37 | po_dn_flip | 04:35 `SL_HIT` | −20.0 | (上に含む) | [[2026-09-24]] |
| 4 | #950042 | 10-02 00:20 | po_dn_flip | 02:04 `OANDA_SL_TP` (BE) | +0.8 | +6 | [[2026-10-02]] |
| 5 | #957198 | 10-02 19:09 | ema75_break | 21:45 `WEEKEND_CLOSE` (demo) / 日曜 SL (broker) | +3.0 | **−147** (符号反転) | [[kalman-d7-ema75-break]] |
| 6 | #1027829 | 10-05 03:01 | po_dn_flip | 05:14 `OANDA_SL_TP` (BE) | +0.5 | +6 | [[2026-10-05]] |
| 7 | #1098462 | 10-08 07:01 | po_dn_flip | 10:20 `OANDA_SL_TP` (BE) | +0.8 | +8 | [[2026-10-13]] |
| 8 | #1208876 | 10-09 08:31 | po_dn_flip | 08:57 `SL_HIT` | −20.0 | −201 | [[2026-10-13]] |
| 9 | #1211263 | 10-09 09:16 | po_dn_flip | 17:16 `MAX_HOLD_TIME` | +5.1 | +56 | [[2026-10-13]] |
| 10 | #1254177 | 10-14 10:01 | po_dn_flip | 12:30 trail `OANDA_SL_TP` | +15.6 | +157 | [[2026-10-15]] |
| 11 | #1346976 | 10-29 10:16 | po_dn_flip | 11:02 `SL_HIT` (BE+1.1) | +0.8 | +11 | [[2026-10-29]] 12:00Z |
| 12 | #1346985 | 10-29 18:52 | po_dn_flip | 20:01 `SL_HIT` (ON_FILL SL 157.862) | **−10.8** | **−105** | 本 run (tx 1346984–1346990) |

| 指標 | demo (gross `pnl_pips`) | broker realized (JPY → pip、1000u USD_JPY ≈ ¥10/pip) |
|---|---|---|
| N (prefix 合算) | **12** (po_dn 11 / ema75 1 / trail_atr 0) | 12 |
| Σ | **−20.5p** | **−¥363 ≈ −36.3p** |
| EV | **−1.71p / trade** | **−¥30.3 ≈ −3.0p / trade** |
| WR | 66.7% (8W / 4L) | 58.3% (7W / 5L、#957198 が符号反転) |
| Wilson lower (95%) | 0.39 | 0.32 |
| avg win / avg loss | +4.35p / −13.8p (payoff 0.32) | — |
| po_dn_flip 単独 (N=11) | Σ −23.5p / **EV −2.14p** | Σ −¥216 / **≈ −2.0p** |

**4 基準 (demo / broker × prefix / po_dn 単独) 全て EV<0。** estimand 未凍結 (postfill packet §3 は DRAFT、registry message「承認前に N=10 へ到達した場合は判定を保留し user 再決裁」) は、両 estimand で符号が一致する本件では判定に影響しない — D11 両基準併記 ([[integrated-decision-packet-d1-d12-2026-09-22]] §8-12、10-20 / 10-29) と同じ扱い。gross/net の差 (−1.71 vs −3.0p) は #957198 の週末 `MARKET_HALTED` 符号反転 (demo +3.0 / broker −14.7p) が主因で、estimand 凍結の必要性自体は不変 (再 live 化 R1 で凍結する)。

**付帯条件**: 「連続 3 SL (3 variant 合算) → 即時 user review」は不成立 (直近 3 決済 = +15.6 / +0.8 / −10.8)。

## 2. 敵対的検査 (Rule 2 なので採用規律の 3 点検査は不要だが、判定の頑健性を記録する)

- **外れ値感度**: 最大損失 #1208876 −20.0p を除くと demo Σ −0.5p / N=11 = **−0.05p** (なお負)。最大 2 損失 (#893189 / #1208876) を除くと +19.5p / 10 = +1.95p に反転する。⇒ 判定は 2 トレードに依存するが、(a) pre-reg 条件に外れ値除外は無く事後除外は look-ahead、(b) SL −20p は本戦略の ON_FILL SL 設計値 (1.5×ATR → SR clamp 20.0p) であり tail ではなく設計どおりの損失、(c) broker 基準は 2 本除外でも −¥363+201+... = 依然 −¥17 ≈ 負。Rule 2 は「負の点推定で早期停止」を事前に約束した設計 — 停止後に shadow で N を積む方が clean-N 整合 (roadmap v2.3「整合」) に適う。
- **統計的注記**: N=12 で EV −1.71p の SE ≈ 3p (sd ≈ 10.4p)。有意性の主張ではない。**pre-reg R2 ゲートは低検出力で止める設計**であり、「エッジが無い」の falsification ではなく「live で積み増す根拠が無い」の判定。
- **BT 形状との乖離 (記録)**: BT は WR 23.9% / W/L 12.3× (payoff 型)、live は WR 66.7% / payoff 0.32 (BE 返し型) — exit 仕様非同期 ([[kalman-d7-live-exit-disposition-packet-2026-10-07]]: 8h cap + BE/trail overlay で winner ride が構造的に不可能) の実測。live 12 本の最大 favorable は 27.2p (#1254177) で宣言 TP 5×ATR (≈ +30〜39p) に 1 本も届かず。⇒ 停止の原因仮説は「exit 仕様が BT の payoff を再現できない」であって「entry シグナルが死んだ」ではない。再 live 化 R1 は exit 仕様 (a) 宣言復元 と同時に審議する ([[kalman-d7-live-exit-disposition-user-decision]] 11-29)。
- **estimand 不変性**: §1 の 4 基準表のとおり。

## 3. 執行内容 (code / tests / KB 同一 PR、rule:R2)

- **code** (`modules/demo_trader.py`): class attr `_KALMAN_D7_R2_LIVE_STOP = True` を新設、`_kalman_d7_live_eligible` の先頭で True なら False を返す (env `KALMAN_D7_LIVE_ENABLE` の評価より前)。これは LOCK 09-01 §R2 の撤退経路「env 0 で即時」と**同じ gate を閉じる**: `_resolve_tier` は `KALMAN_D7_LIVE` を返さず UNIVERSAL_SENTINEL の shadow 経路へ落ちる (shadow 蓄積継続 = 原則 3)。
- **なぜ env でなく code pin か**: Render env は autopilot から変更不可 (`storm-guard-enforce-execution-window` と同じ classifier [Production Deploy] 拒否、通算 7 回)。code pin は PR / CI / review gate を通り、観測面 (`/api/demo/live-enable-flags` `code_pins.KALMAN_D7_R2_LIVE_STOP`) を持つ。env 側は触らない (user が env を 0 にしても二重で無害)。
- **触らないもの**: 1000u 固定契約 (`KALMAN_D7_MIN_UNITS`)、`_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` 所属、`_KALMAN_D7_LIVE_OVERRIDE`、シグナル / SL / TP / 発火条件、LIVE_PROMOTE_LOSERS。ps carve-out demote (10-10) では bypass set からも除去したが、本件は LOCK 09-01 が撤退経路を「env gate のみ」と凍結しており、bypass 所属は LOCK の凍結事項 (「eligible ∧ units≤1000」の二条件で gate 側は live 不適格に自動追従) のため非接触とした。
- **observability** (`app.py` `/api/demo/live-enable-flags`): `code_pins.KALMAN_D7_R2_LIVE_STOP` を追加 (既存 lever の形は不変)。
- **tests**: `tests/test_kalman_d7_r2_live_stop_2026_10_30.py` 13 pin (pin True / env lever ON でも 3 variant live 不適格 / pin 解除で env gate 復帰 (再 live 化の到達性) / source 順序 pin→env / `_resolve_tier` が KALMAN_D7_LIVE を返さない / endpoint 観測面 / LOCK 09-01 lot 契約不変)。既存 `test_kalman_d7_minlot_carveout.py` 12 pin は green のまま (lot 側非接触の証拠)。registry の resolve に伴い、実 registry を読む 4 pin を更新 (`tests/test_cell_deepdive_lock_redaction.py` ×3: kalman entry は redaction 母集団外 = 執行済み LOCK は outcome look を凍結しない (PR #324 の反転規則)、prefix 保持の性質は entry の写しを active 化して pin / `tests/test_prereg_trigger_watch.py` 配線 pin: resolved 2026-10-30 ∧ resolution に R2、写しを active 化して prefix 配線を検査 = D11 pin と同じ手法)。
- **registry**: `t9-kalman-d7-live-n10-ev-check` → `resolved: 2026-10-30` (resolution に §1 の数値)。`kalman-d7-live-exit-disposition-user-decision` (11-29) message に「(c) 相当の状態が先に成立、返答は再 live 化 R1 + exit 仕様として読む」を追記。`t9-kalman-d7-fire-info` に「10-30 deploy 以降 shadow 分子が再び有効」を追記。
- **deploy**: PR merge → Render auto-deploy (code 変更 = 再起動)。執行窓 §3.2 (a) (open live 0 ∧ 直近 H1 bar に live-eligible なし) を merge 直前に再確認する。`storm_guard` in-process 状態は再起動で消失する (7 例目、open 0 で無害)。

## 4. 再 live 化の条件 (R1、user 決裁)

- 本 pin を False に戻す PR + LOCK 09-01 の再審 (estimand = broker realized net の凍結を**先に**行う、postfill packet §3)。
- exit 仕様 (a) 宣言復元 [TV canon 再走が前提] / (b) 現状維持 の決裁と同時 ([[kalman-d7-live-exit-disposition-user-decision]])。(b) のまま再 live 化する根拠は本 readout に無い (同じ exit 仕様で N=12 EV<0)。
- shadow 側: 10-30 deploy 以降の kalman_d7* shadow 行 (UNIVERSAL_SENTINEL) で `t9-kalman-d7-fire-info` (3.9/週) を再読。shadow で N≥30 ∧ EV>0 が立っても **Rule 1** (365d BT or Live N≥30 + Bonferroni) が必要。

## 5. 関連

- [[kalman-d7-po-dn-flip]] / [[kalman-d7-ema75-break]] / [[kalman-d7-trail-atr]] (Status 更新)
- [[ps-carveout-pool-r2-demote-2026-10-10]] (同型の R2 執行前例) / [[lesson-asymmetric-agility-2026-04-25]]
- [[2026-10-30-session]]
