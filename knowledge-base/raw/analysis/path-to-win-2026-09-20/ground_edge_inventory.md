# Ground truth: clean live エッジ在庫と負けの構造 (2026-09-20 文書監査、価格/DB 計算ゼロ)

定義: clean live = `oanda_trade_id != ''` ∧ `dedup_violation != 1` ∧ 非XAU ∧ CLOSED (is_shadow=0 単独は不可)。
KB ルート = `/Users/jg-n-012/test/fx-ai-trader/knowledge-base/` (以下 `wiki/` `raw/` は相対)。MEMORY = `/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test-fx-ai-trader/memory/`。

---

## 0. 結論 (3 行)

1. **「摩擦控除後に正 EV を出した clean live セル」は、Rule 1 級 (N≥30) では歴史上 0 本。** 唯一の候補 `usdjpy_carry_dip_accumulator×USD_JPY×BUY` は demo book で N=14 / +103.0p だが、broker ledger 突合 7/11 本の合計は **≈ −41.1p で符号が逆**、残 4 本未突合 (`wiki/strategies/usdjpy_carry_dip_accumulator.md` §(6))。
2. **今 live で動いている経路 = min-lot 1000u bypass の 12 セル** (carry_dip×1 + price_shock_rev×5 + weekend_gap_fade×3 + kalman_d7×3 type/USD_JPY)。それ以外の PAIR_PROMOTED 21 エントリは agg-Kelly gate (−0.327、09-11T13:04Z から凍結) で全滅。直近 30d の live 約定は 4 セル・N=14〜17 で、**最終 live fill は 2026-09-11T11:02:36Z (#893161)**、09-18 時点で 7.45 日 stale。
3. 負けの構造は **(a) 勝ち側 exit 執行の崩壊 (payoff 0.274、gap の 103.7% が勝ち側) + (b) 対称摩擦の水準効果 (30d friction が gross の 33.5 倍)** で確定。「負けを引っ張る」「負けだけ滑る」「方向バイアス」は棄却済み。exit 修理 (T2) は FAIL でクローズ、価格モダリティのシグナル張り替えも 3 周 FAIL、base rate 4%。

---

## 1. 歴史上の「正 EV clean live」候補の全数と処分

| セル / 群 | 期間・窓 | N | pips / EV | 摩擦後か | 処分 | 出所 |
|---|---|---|---|---|---|---|
| `usdjpy_carry_dip_accumulator×USD_JPY×BUY` | 2026-08-14〜09-11 累積 | **14** (demo) | **+103.0p / EV +7.36** (as-reported WR 57.1%) | live pnl は fill 価格に摩擦内蔵 (=net 相当) | 🔴 broker ledger 突合 7/11 = **≈−41.1p 符号逆**。#709598 は demo +11.6 vs broker −14.1 (25.7p 反転、halted-exit)。broker-corrected +78.4 は「導出値・未監査」。SL 契約 150p → 実発注 9.8–28.5p (11/11)、TP ~65p 固定 (宣言 80p)、BE trail が 80p TP 経路を毎回閉じる。storm 5/11 fill | `wiki/strategies/usdjpy_carry_dip_accumulator.md` 表 + §(4)(5)(6) |
| `vix_carry_unwind×USD_JPY×SELL` | shadow net+ 唯一 (+1.86p, N=58) | live 26 | **live −46.9p / PF 0.66** (30d −1.90p) | shadow は BE/Trail 水増し | PAIR_DEMOTED 2026-08-03 (R2)。「shadow net+ は live に伝わらない」の実証例 | `wiki/analyses/friction-adjusted-ev-map-2026-07-07.md` §4 / `wiki/strategies/vix-carry-unwind.md` |
| `bb_rsi_reversion×USD_JPY×SELL` | 累積 (cutoff 04-08〜) | 44 | **EV +0.29p** / w_lo 0.36 | live 実現 pips | rederivation literal (EV>0) のみ該当。**休眠** (直近 30d 発火 0、R2 停止系 / T10 KILL)。M1_STRONG_CELL (EV≥+1.0) は不成立 | `wiki/analyses/m1-strong-definition-implementation-2026-09-10.md` §3 |
| `bb_rsi_reversion` 診断窓 11 件 | 2026-06-07〜07-08 | 11 | EV +0.82 (capture 0.387) | — | **全件 watchdog DECREMENT 再武装バグ E4 漏出** (KILL 済み戦略)。根拠に使えない | `wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md` §3 |
| `orb_trap` | 累積 | 4 | +23.2p | — | **FORCE_DEMOTED** (365d BT 全ペア負 EV)。N=4 | `raw/trade-logs/2026-09-16.md` L181 / `wiki/strategies/orb-trap.md` |
| `post_news_vol` / `ema_pullback` | 累積 | 2 / 2 | +19.0 / +17.8 | — | FORCE_DEMOTED、N=2 | `raw/trade-logs/2026-09-16.md` L181 |
| `kalman_d7_po_dn_flip×USD_JPY×BUY` | 2026-09-10 初 fill | **1** | +8.2p demo / **+9.1p (¥91) broker** | broker realized | 4h04m SL 決済 (BT edge は ~115h winner ride 依存) → **N=1、判断禁止**。storm 4 (33,675 tx) 誘発 | `wiki/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md` §0 / `wiki/strategies/kalman-d7-po-dn-flip.md` |
| JPY 系 MR 勝ち群 | 2026-05-13〜06-12 の 30d | — | **+44p** (book N=84 / −37.9p の内数) | — | 160 介入キャップ整合。T5 JPY cap (lot 0.5x) 発動 06-18。群であってセルではない | `wiki/syntheses/roadmap-v2.2-win-conversion.md` L14 |
| W20–21 一時プラス転換 | 2026-05 後半 | — | — | — | 持続せず W23 以降再悪化 | `wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md` L17 |
| **weekend_gap_fade (pooled EUR_USD/USD_JPY/AUD_USD)** | OOS 2022–2026 | **177** pair-events | **gross +15.60p/event、stressed-net(3×RT) +9.04p、実測 RT でも +7.90p、p<1e-4** | **BT/OOS の摩擦後** (live ではない) | **プロジェクト唯一の OOS 確定 PASS だが live 約定通算 0** (下 §2) | MEMORY `project_weekend_gap_fade_live_2026_07_25.md` / `wiki/strategies/weekend-gap-fade.md` 根拠表 |

**摩擦調整 EV マップ (2026-07-07, T4)**: 稼働 39 entry_type / 89 セル (deduped shadow N≥30) で **net+ は 1/39 type・3/89 セル**、しかも唯一の net+ (vix) は live 負 → **「現行母集団に live viable な正セル不在」を確定** (`wiki/analyses/friction-adjusted-ev-map-2026-07-07.md` §1/§5)。
**M1_STRONG_CELL (N≥30 ∧ EV≥+1.0 ∧ Wilson_lo>0) = 0 / 117 セル** (2026-09-10 本番実測、`wiki/analyses/m1-strong-definition-implementation-2026-09-10.md` §3)。

---

## 2. 「OOS PASS だが live 約定ゼロ」— weekend_gap_fade

- 検証チェーン: explore 2014–2021 → pre-reg LOCK → OOS 一発 2022–2026 **arm B 全ゲート PASS** (N=177、gross +15.60p、stressed-net +9.04p、knife-edge 4/4) → 日曜 spread 12 週末実測 (実測 RT でも +7.90p) → user 承認 option (b) 直接 live MIN lot 2026-07-24、PR #117 (MEMORY `project_weekend_gap_fade_live_2026_07_25.md`)。
- 執行: 1000u 固定、+4h horizon、disaster SL 150p、spread cap 10.0p、G1 (slippage rolling6 >+2.0p) / G2 (N=12 cum <−60p) で恒久停止。月次期待 +22〜26p、σ≈63p。
- **live fill = 0 / 3 qualifying イベント** (`wiki/strategies/weekend-gap-fade.md` イベントログ):
  - 07-26 USD_JPY: `_is_xau_inst` UnboundLocalError (2026-04-10 から chronic、3.5 ヶ月 preserve 型 live 送信を殺していた) → 無タグ shadow −22.8p。分母に入れない (インフラ障害)。MEMORY `project_preserve_bug_fixed_10cells_live_2026_07_28.md`
  - 08-02 USD_JPY gap −22.5p: 送信正常 → tx 549258 `ORDER_CANCEL reason=MARKET_HALTED` (21:01:27.9Z、order と同 ms)。shadow counterfactual は disaster_sl −182.7p (fill 失敗が偶然 ≈−¥1,800 回避)
  - 09-06 USD_JPY: tx 837792 → 837793 `MARKET_HALTED`。halt 解除 21:04:58Z 実測。機構確定 = エンジン発火 21:01 < OANDA 実開場 21:04–05 (48/48 週末) → 旧契約の fill 率は構造的 ~0%
  - 09-10 執行契約 AMENDMENT (B) 発効 (R1、user 承認): 実開場確認後送信 / +15 分打ち切り / adverse drift >+8.0p 放棄 / halt-race 限定再送 1 回。実効 EV ≈ +4.75p/event、fill 成立率見積 点 ~94% / 保守 ~75%
  - 09-13: `weekend_gap_exec_abandon(ABANDONED_DRIFT, drift=+41.00p)` = 設計どおり放棄、fill なし (`raw/trade-logs/2026-09-16.md` L241)
  - **凍結境界**: 改定後最初の 2 qualifying イベントで 2 連続 fill 不成立 → 執行モダリティ再審 (R1)。
- **F2 falsification (メタ監査)**: **2026-12-31 までに live 執行 N=0 なら「PASS→live PnL 変換は未実証」と正式認定**、以後の全 PASS の価値を執行実証まで割引 (`wiki/decisions/process-meta-audit-2026-09-07.md` L184、registry `project-falsification-f2-wg-live-conversion`)。
- **base rate**: 家族級 verdict ~25 件 (補正分母 26–35) 中 OOS 確定 PASS **1 件 = 4.0% [Wilson 95% 0.7–19.5%]**。探索→OOS 生存 0/15〜17 系統 (同 L26/L43)。
- viability-2 訂正版: **wg 級 1 本では M2 に届かない** — disaster SL 150p binding で実効上限 L1=5000u → +0.46%/月 < 0.5%、M2 定義自体が 2 セル要求 (同 L106/L203)。

---

## 3. 現在の live ロースタと 30d 成績

### 3.1 live 経路 (構造)
- **agg-Kelly gate は恒久負** (−0.315〜−0.374、母集団 = cutoff 2026-04-16 以降の clean live 累積)。8 月以降 live 経路 = **min-lot 1000u bypass 9 セル** (carry_dip×1 + price_shock_rev×5 + weekend_gap_fade×3) (`wiki/analyses/live-frequency-and-oanda-status-survival-2026-09-01.md` Part 2)。09-01 LOCK (PR #218) で kalman_d7 3 type/USD_JPY を bypass に追加 → 初 fill 09-10 (`wiki/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md` §0/§2.1)。
- 09-11T13:04Z 以降 `agg_kelly=-0.327` で凍結、blocked は xs_momentum_rsi / dt_bb_rsi_mr / vsg_jpy_reversal (`raw/trade-logs/2026-09-18.md` L68)。
- tier-master (2026-09-17 08:45Z): ELITE_LIVE 0 / PAIR_PROMOTED 21 エントリ / FORCE_DEMOTED 20 / PAIR_DEMOTED 41 (`wiki/tier-master.md`)。
- 退役: `sweep_reversion_eurgbp_late` は 2026-09-17 Option C retire (estimand 監査: gross spaced +2.92p → net −3.33p 符号反転、spread 前提 ≤3.5p 充足 0/10、cap 救済集合空) (`wiki/analyses/ps1a-trigger-estimand-audit-2026-09-16.md`)。`vix_carry_unwind` は 08-03 demote。
- 月次 LIVE 件数: **6 月 92 → 7 月 28 → 8 月 13 → 9 月 (09-01 時点) 0** (`live-frequency-...-2026-09-01.md` Part 2)。LIVE 発火セル 124 (2026-05-01 窓) → 3 (2026-09-04 窓) — 88.7% は停止機構で帰属済み、停止 83 セルの anchor 窓 = **N=609 / −469.8p** (MEMORY `project_roster_attrition_attribution_2026_09_06.md`)。

### 3.2 直近 30d clean live (M1 弱定義、`tools/m1_clean_live_monitor.py` estimand)
| anchor | N | sum | EV | verdict | 出所 |
|---|---|---|---|---|---|
| 2026-07-06 | 92 | −242.6p | −2.64 | — | `wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md` L17 |
| 2026-08-02 | 11 | −177.5 | −16.14 | — | `wiki/analyses/m1-kpi-readout-and-mechanical-flip-2026-09-04.md` §3 |
| 2026-09-01 | 13 | +94.3 | +7.25 | MECHANICAL_FLIP (07-31 −123.2p の窓外脱落のみ) | 同 §4 |
| 2026-09-04 | 15 | **+19.8** | +1.32 | MET_UNDERPOWERED: bootstrap CI [−217.6, +241.2] / P(sum≤0)=0.426 / 1 件抜くと符号消滅 4 件 | 同 §5 |
| **2026-09-10** | **17** | **−85.0** | **−5.00** (WR 47.1%) | **NOT_MET**、P(sum≤0)=0.817、MECHANICAL_FLIP (08-09 carry_dip +63.7p の脱落) | `wiki/analyses/m1-strong-definition-implementation-2026-09-10.md` §3 |

⚠️ 09-10 以降の M1 monitor 値は KB 文書に未記録 (Tier A cron → Discord のみ)。以下は `/api/risk/dashboard` 30d rolling (estimand が clean live 厳格定義と一致するか未確認):
- **2026-09-16**: n=15、gross=net=alpha **−9.8p** だが `friction 65.7` (4.38/t×15) が未控除 → **真の 30d net ≈ −75.5p**。sleeve: USD_JPY n=9 / **+54.4** ・ AUD_JPY n=2 / **−57.4** ・ EUR_GBP n=4 / **−6.8**。09-14→09-16 の「改善 +23.4」は新規 0 / aged-out 2 の窓算術 (`raw/trade-logs/2026-09-16.md` L199–215)
- **2026-09-18**: n=14、gross **+1.9** / friction **63.6** (4.54/t) = **摩擦が gross の 33.5 倍**。USD_JPY +66.1 (n=8) / EUR_GBP −6.8 (n=4) / AUD_JPY −57.4 (n=2)。Kelly edge −0.0666 / `recommended_fraction` 0.0 / DSR 0.1292 非有意 (`raw/trade-logs/2026-09-18.md` L168–181)
- 累積 (cutoff 04-08〜、`/api/demo/stats` live track): **N=587 / WR 43.8% / EV −1.12 / −658.4p**、09-14→09-18 の 4 run bit-flat = decided fill 0 (`raw/trade-logs/2026-09-18.md` L72–87)。⚠️ この N=587 が oanda_trade_id 厳格か is_shadow=0 かは文書上未確認。
- **最終 live fill = #893161 2026-09-11T11:02:36Z**。09-18T21:54Z で 7.45 日 / 市場オープン 130.0h vs 閾値 120h → `freshness_ui` 初の **stale** (`raw/trade-logs/2026-09-18.md` 発見 1)。09-12〜09-18 live fill 0 本。

### 3.3 直近 30d に live 約定を出したセル (4 セル)
| セル | 30d N | 30d pips | 累積 | 状態 | 出所 |
|---|---|---|---|---|---|
| `usdjpy_carry_dip_accumulator×USD_JPY×BUY` | 8–9 | +54.4〜+66.1 (USD_JPY sleeve、kalman 1 本を含む可能性) | N=14 / +103.0 (demo) / broker 7/11 ≈ −41.1 | LIVE 1000u。SL 契約破棄・BE trail・storm 未修理 (R3 決裁 08-05 から未決) | `usdjpy_carry_dip_accumulator.md` / `2026-09-18.md` |
| `price_shock_rev_aud_jpy_h1_long×AUD_JPY×BUY` | 2 | **−57.4** | **N=4 / −180.0 = −45p/本 = 累積 book 全損の 27.3%** | PAIR_PROMOTED / enabled、de-risk 4 run 連続 user 決裁待ち。BT N=426 WR 63.8% EV +32.25 と正面衝突。09-03 fill の bracket TP +1,088p / SL −130p は宣言 (12-bar horizon + −2×ATR) と不一致 | `wiki/strategies/price-shock-rev-aud-jpy-h1-long.md` / `2026-09-18.md` L89 |
| `price_shock_rev_eur_gbp_h1_long×EUR_GBP×BUY` | 4 | −6.8 | N≥3 / 0W3L (08-23) | PAIR_PROMOTED。BT N=239 WR 72.8% EV +55.81 vs live 0% | `wiki/strategies/price-shock-rev-eur-gbp-h1-long.md` |
| `kalman_d7_po_dn_flip×USD_JPY×BUY` | 1 | +8.2 (+9.1 broker) | N=1 | LIVE 1000u (09-01 LOCK)。R2: N≥10 で broker-net EV<0 → 停止、期日 2026-12-09 | `kalman-d7-carveout-postfill-packet-2026-09-17.md` §3 |

### 3.4 KPI 現在値
- **M1**: 弱定義 NOT_MET (09-10)。**M1_STRONG 全変種 未達** (`m1-strong-definition-implementation-2026-09-10.md` §3)。
- **M3a** (throughput): 累積 2/3 (休眠 bb_rsi SELL/BUY)、**稼働 0/3**。3 本目 ETA 2026-10-26 (carry_dip +11/30d 外挿)。3 セル体制の ETA ~14 ヶ月 (ps_eur_gbp 6.4 ヶ月 / ps_aud_jpy 13.8 ヶ月)。
- **M3b** (return): **−0.075%/月** vs 目標 +0.5% (M2)。現ペースで到達不能 (同 §3)。time-to-M2 中央シナリオ 2027-Q4〜2028、P(M2≤2027 末)≈15–25% (`process-meta-audit-2026-09-07.md` L106)。
- **NAV ¥275,516.83** (09-16〜09-18 不動) vs floor ¥262,000 (OANDA JP API 存続) 到達推定 2027-02〜04。broker `pl` −83,627 / base ¥359,109 → 実 DD **−23.3%** (表示 9.72% の 2.4 倍)。SVK keeper $520k/$500k 達成 → 10 月 GOLD 維持見込み (`2026-09-16.md` L209–227)。

---

## 4. 負けの構造 — 確定事項

### 4.1 payoff (確定、2026-07-07 T3、敵対的検証済)
- clean live 30d (06-07〜07-08) N=93 / −245.0p / WR 54.8% / avgW +2.40 / avgL −8.75 → **payoff 0.274**。
- **恒等式 0.274 = 設計 R:R 2.667 × 勝ち側 capture 0.0944 ÷ 負け側 realize 0.9185**。log gap の **103.7% が勝ち側**、負け側は −3.7% (改善方向)。
- 2 層: **follow-through 不足** (gap の 69.9%): winners MFE 5.18p vs 設計 TP 25.4p (約 5 倍)、TP 到達 **3/93 = 3.2%**。**trail/BE 返上** (33.9%): 未捕獲 **142.5p/30d**、全額 OANDA_SL_TP 出口 (N=38、med +1.8p / 保有 9 分)。
- WR 54.8% は BE/trail アーティファクト (<3p スクラッチ 46/51 勝 = gross win の 64%)。
- **両レバー完璧でも −77.6p** (分岐 payoff 0.824 未達) → exit 微調整では黒字化不能。
- 出所: `wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md` §1/§2/§4。

### 4.2 exit (確定)
- **T2 exit-repair R1 = FAIL クローズ 2026-07-08**: 全 9 構成 p=1.0 / WF 0/3、最良 tp0.4×sl0.6 で −2.96 p/t → **exit 側レバーは仮説空間ごと閉鎖・再試行禁止** (`roadmap-v2.3` L57/L136)。
- 「負けを引っ張る (SL 遠置き)」= **棄却**: loss realize 0.92、負け MFE med 0.1p、SL slip med +0.10p。BE 移動救済は楽観 +24.9 / 悲観 −47.1p で期待値負 (`payoff-asymmetry` §1-4/§4)。
- trail 除去の反実仮想 (pure SL/TP) は −2.53〜−4.98 p/t で実現より悪い → **trail 除去も解ではない**。
- shadow の estimand 断絶: 2026-06-03T07:58Z commit `ab7a4931` で shadow の BE/trail が dead code → 有効化、WR 26.3→51.5% / R:R 1.90→0.55 (`wiki/audit-index.md` L4、MEMORY `project_shadow_exit_regime_break_2026_06_03`)。
- **執行層の実装欠陥 (live 固有、2026-09 確定)**: carry_dip の SL は宣言 150p に対し 9.8–28.5p (n=11/11、TP は ~65p 固定) = ペイオフ幾何の反転 (R:R 0.53 → 2.28〜6.39)、BE trail が TP 経路を閉じる、trail storm 族 A/B (5/11 fill + kalman)、demo↔broker 符号反転 (halted-exit)、`attribution` friction 未控除 16 日 (`usdjpy_carry_dip_accumulator.md` §(4)(5) / `2026-09-16.md`)。

### 4.3 摩擦 (確定)
- **非対称摩擦 (「負けだけ滑る」) = 棄却** (17.7p/30d = net 損失の 7%)。
- **対称摩擦の水準効果は大**: friction ∈ **[120.6 (実測フロア 1.30/t), 294.6 (per-pair 理論 3.17/t)] p/30d**、gross ∈ [−124.4, +49.6]p → 符号反転はモデル依存。実測列 (N=94): spread_at_entry 1.16 / exit 1.47 / slippage 0.56p。pnl_pips は fill 価格に摩擦内蔵 (後付け控除は二重計上) (`payoff-asymmetry` §5 / `friction-adjusted-ev-map` §7)。
- 2026-09-18: 30d friction 63.6 vs gross +1.9 = **33.5 倍** (`2026-09-18.md` L181)。
- スクラッチ勝ち med +1.8p ≈ spread 1.30p → 勝ちが摩擦と同水準。

### 4.4 方向・ペア (確定分と限界)
- 06-07〜07-08 窓: pair×dir 全セグメント payoff **0.16–0.43 で一様に低い** = 構造的、特定ペア産物ではない。ただし pip 出血は **GBP_USD 集中 N=38 / −129.9p (53%)、理論 friction の 58%** (`payoff-asymmetry` §6)。
- 2026-06-12 (v2.2): 核 = EUR_USD SELL −49.7p (ECB 前底固め×LDN 朝 MR)、counter-USD MR −28p、NY 午後薄商い MR；勝ちは JPY 系 +44p (`roadmap-v2.2` L14)。T11「LDN 朝×counter-USD MR」クラス禁止仮説は R1 REJECT (敵対的検証で棄却、MEMORY)。
- trendline_sweep×GBP_USD: 出血 87% が UTC12–15 NY overlap、SELL avgLoss −17.70p 最悪、MTF mixed gate no-op (PR #58 修正) (`payoff-asymmetry` §7)。
- 現行 live ロースタは **全 LONG** (carry_dip / ps×5 / kalman)。AUD_JPY LONG (price_shock) が累積損失の 27.3%。方向単独の系統的検証は現母集団 (N=14〜17) では不可能。

### 4.5 供給側 (確定)
- WS3 シグナル張り替え: stage-1 PASS 2 セル (lfr×EUR_USD 1.43 / htf_fb×AUD_JPY 1.82) → stage-2 **PASS 0 / UNDERPOWERED** (lfr 9 構成全負)。round-3 cross-asset **OOS 8/8 符号反転**。**価格モダリティは内部 2 周 + 外部 1 周 = 3 周 FAIL で閉鎖** (`roadmap-v2.3` L83–100)。
- 唯一の主力供給ライン = E1 positioning (pre-reg LOCK、first look 2026-10-15、modal 予想 UNDERPOWERED)。P-10 LOCK 中 (outcome ジョイント計算禁止)。
- MFE 診断: h24 MFE p50 15–30p (豊富) だが MFE/MAE 比中央値 0.88 = 方向性なし、ratio≥1.3 は 7/79 セル (`roadmap-v2.3` L90)。「5p しか走らない」は exit 打ち切りアーティファクト。

---

## 5. 引用禁止・注意 (estimand)
- carry_dip の +103.0p を「正 EV 源」として引用する場合、broker 7/11 ≈ −41.1p (符号逆) と未突合 4 本を必ず併記。「clean = 差ゼロ」前提は #893161 (1.0p 差) で緩んだ。
- M1 弱定義の符号は往復とも MECHANICAL_FLIP で無内容 (09-04 +19.8 → 09-10 −85.0)。
- 「発火機会不足が独立の律速」は 09-06 帰属で部分否定 — 88.7% は意図的止血の帰結。D クラス旧解釈 (「本来出てはいけなかった発火」) は 09-10 棄却済み (MEMORY `project_roster_attrition_attribution_2026_09_06.md`)。
- shadow net+ セル (ob_retest×USD_JPY×BUY +0.99 / dt_sr_channel×USD_JPY×BUY +0.08) は live 未検証・promote 根拠にならない。
- 旧 anchor 21.6% / 20% は U1=(b) で除去済み (`wiki/decisions/u1-mission-redecision-2026-09-17.md`)。

## 6. 未解決 (open)
1. 09-10 以降の M1 monitor (clean live 厳格 estimand) の実値が KB に無い — risk dashboard n=14/15 は estimand 未確認。
2. carry_dip broker ledger 残 4/11 (#677931 / #681149 / #837978 / #847578) 未突合 → 唯一の「正 EV 源」の真の符号が未確定。
3. weekend_gap AMENDMENT B 後の初 fill (2 連続不成立で R1 再審)。F2 期限 2026-12-31。
4. price_shock_rev_aud_jpy_h1_long de-risk (user 決裁、4 run 連続未決) と bracket 不一致の診断。
5. carry_dip SL 契約破棄 / BE trail / storm guard 4 点セットの R3 (08-05 から未決)。kalman L1 昇格は guard 着地まで凍結。
6. M1_STRONG 変種の裁定 4 件 (user)。
7. `/api/demo/stats` N=587 系列が oanda_trade_id 厳格か is_shadow=0 かの確認。
8. E1 first look 2026-10-15 (P-10 LOCK 中、本タスクで一切計算せず)。
