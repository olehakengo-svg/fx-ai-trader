# PASS → live 実装 → 実約定 の変換ファネル監査ノート (文書のみ、2026-09-20)

規律: 文書読解のみ。価格データ・DB への計算ゼロ。clean live = `oanda_trade_id != ''`。数値は全て出所併記。
KB ルート = `/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/` (以下 `wiki/`)。MEMORY ルート = `/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test-fx-ai-trader/memory/`。

---

## 0. 結論 (1 段落)

変換は**単一の段で壊れているのではなく、全段で桁落ちしている**。上流 (仮説→OOS PASS) は 79 family → 1 PASS (base rate 4%)。PASS→live 化は 1/1 だが、live 化→実約定は **0/3 イベント** で「PASS→live PnL 変換係数」はプロジェクト開始以来一度も測定されていない (meta-audit funnel-2 CONFIRMED)。中流の内部セルでは、シグナル→select_best 勝者までは期待レートどおり (hull 7.9/週 vs 期待 7.61/週) だが、**勝者バー→trade 行が 1/18 = 5.6%** (`_tick_entry` ガード 6 系統の合算、order 層は無実)。ps 席は design 34 → 観測 7 (capture 20.6%)、closed-bar 基準では 3〜6%、3 席は 0/17 で残余 ~100% が「測っていない」(HourlyEngine に C1 計装ゼロ、09-11 まで)。LIVE 約定は 124 セル/30d (5 月) → 3 セル/30d、LIVE 資格 family の発生 ~1 件/週。摩擦側では shadow gross ですら net+ が 1/39 type・3/89 cell、唯一の net+ type は live で負。lot 階段は L0 1000u 固定で、wg 級セルは disaster SL 150p が binding → L1 5000u が実効上限 (+0.46%/月 < M2 の 0.5%)。**律速は「エッジ密度 × 執行契約の構造欠陥 × 観測基盤の write-only」の積であり、どれか 1 つを直しても time-to-M2 は動かない。**

---

## 1. 変換ファネル — 段別実測比率

### 1.1 マクロ段 (family → PASS → live → 約定)

| 段 | 実測 | 出所 |
|---|---|---|
| 仮説 family → OOS 確定 PASS | **~79 → 1** (base rate 4.0% [0.7–19.5%]) | `wiki/decisions/process-meta-audit-2026-09-07.md` L62, L105 |
| PASS → live 化 | 1/1 (weekend_gap_fade、2026-07-25 PR #117) | MEMORY `project_weekend_gap_fade_live_2026_07_25.md` |
| live 化 → clean live 約定 | **0/3 qualifying イベント** (G 分母 0/2 — 07-26 はインフラ障害)。変換係数 = 測定不能 (0/1) | `wiki/decisions/weekend-gap-execution-contract-r1-packet-2026-09-10.md` §1.1; meta-audit L27, L45 |
| live 収益化 | 0 | meta-audit L62 |

**0/3 の死因 (全て一次 tx で確定)**: ① 07-26 `_is_xau_inst` UnboundLocalError (送信前クラッシュ、04-10〜07-28 chronic) ② 08-02 tx 549257/549258 `MARKET_HALTED` ③ 09-06 tx 837792/837793 `MARKET_HALTED`。機構 = エンジン発火 Sun 21:01 UTC (MASSIVE forming bar) < OANDA 実開場 21:04–21:05 (直近 16 週末 × 3 ペア = **48/48** で初 M1 = 21:04、09-06 halt 解除 21:04:58.2Z 実測) → FOK 1 回・リトライ禁止契約では **fill 率 ≈ 0% が決定論的**。(packet §1.2)
- 修理: AMENDMENT (B) user 承認 + 実装 2026-09-10 — tradeable 確認後送信 / 打ち切り +15 分 / drift 放棄 +8.0p / halt-race 限定再送 1 回。見積り fill 成立率 点 ~94% / 保守 ~75%。estimand コスト = 繰下げ drift mean +3.15p → 実効 EV ≈ +4.75p/event (凍結 stressed-net +7.90p の ~60% 回収)。(packet §4–§5)
- **初回検証イベント 2026-09-13 の結果は読んだ KB (sessions 09-13/14/15、strategies/weekend-gap-fade.md、registry) に記録なし** — 09-15 session log は「kalman / weekend_gap の LIVE 約定通算ゼロ」を未解決のまま掲載。qualify 不成立か未記録かを判別できない (open question)。registry `weekend-gap-execution-amendment-g0prime` 期日 09-28、`project-falsification-f2-wg-live-conversion` 期日 12-31。
- 副次欠陥: cap 判定が halt 中 indicative quote (③ 記録 3.1p vs 実開場初バー 6.1p) — 改定 B で実 quote 化。error handler は halt cancel を `"OPEN buy ok but no tradeID"` と誤分類 (`wiki/strategies/weekend-gap-fade.md` L7、未修理の共通バグ)。

### 1.2 内部セル段 (候補 → シグナル → select_best → _tick_entry → order → 約定) — hull_donchian_fade × EUR_USD 15m (最も完全に分解された 1 例)

出所: `wiki/analyses/hull-fire-rate-funnel-2026-08-24.md` §3, §8

| # | 段 | 件数 | /週 | 減衰 |
|---|---|---|---|---|
| 1 | registry 期待 (signal-rate) | — | 13.30 | — |
| 2 | 凍結スペック offline replay (2026-05-01..08-23、16.3 週) | 205 | 12.59 | — |
| 3 | HTF Hard Block 通過後 | 153 | 9.39 | **−25.4%** (silent drop、counter に残らない) |
| 4 | 1-position 直列化 (実測 median hold 0.57h) | 124 | 7.61 | −19% |
| 5 | select_best 勝者バー (C1 デデュープ実測 08-26〜09-10) | 18/20 | **7.9** | 上流無傷 (期待 7.61 と一致) |
| 6 | **trade 行 (shadow 含む)** | **1/18** | — | **勝者バー生存率 5.6%** |
| 7 | clean live 約定 | 0 (hull は全 17 行 shadow) | — | live 意図的例外 |

- 第一死因 (帰属可能 13 本): **spread_guard 3 / same_price_5pip 3 / session_pair(EUR_USD_Tokyo) 3 / score_gate 2 / hedge_block 2** (+二次 score_gate 3、mtf_strong_bias 1)。4 本は Render ログ実効 retention ~2 週で帰属不能。(§8.2)
- **order 層は無実** — ガードチェーン通過の唯一 1 件 (09-01 08:15) は正常に row 化。(§8.3-1)
- 構造衝突: spread_guard (往復 spread/TP > 20%) に免除なし。EUR_USD spread 0.8p / TP 4.4–5.6p → **29–36% で常時閾値超え = spread 平常でも TP が近いだけで死ぬ**。score_gate は hull SELL 勝者バー 5 本中 4 本を殺す。(§8.3-3)
- shadow 蓄積も削られる: 09-04 08:15 は alpha_scan H8 で shadow 降格後に spread_guard hard block で行ゼロ。gate の shadow 分岐は静的 tier (`_is_shadow_eligible_full`) を見て動的 `_is_shadow` を見ない → hull は shadow 行として残る道がない。**4原則#3 (Shadow は削らない) との実在テンション**。(§8.3-4)
- 「未計装」の正体 = 計装はあったが永続面がない: in-memory `_block_counts` は再デプロイ毎ゼロ (実測 3.4 deploy/日)、Render ログ ~2 週。`gate_block_daily` (retention 90d) は 2026-09-11 稼働開始。(§8.4)
- 数え方の罠: C1 生行は 30s poll で **~52x inflation** (1 バーあたり polls 中央値 52)。bar_time は 08-24 まで live 行で全 NULL (call-site 欠落 4 例目)。(§7.2, §8.1)
- registry `t8-hull-shadow-freq` の 09-30 retire 判定 (shadow N<5) は誤帰属になる — 頻度 band 割れの実体は下流 gate による遮断。(§8.5)

### 1.3 内部セル段 — price_shock_rev 5 席 (HourlyEngine 経路)

出所: `wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md` §1, §2, §7, §8; `raw/audits/ps-seat-supply-verdict-2026-09-11.json`

| pair | design 期待 (closed-bar) | 観測 LIVE | 観測 shadow | unique | design bar 上 (緩/厳) | capture |
|---|---|---|---|---|---|---|
| EUR_GBP | 5 | 4 | 1 | 5 | 1/0 | 100% |
| AUD_JPY | 12 | 2 | 0 | 2 | 1/1 | 17% |
| NZD_JPY | 6 | 0 | 0 | 0 | 0 | 0% |
| EUR_AUD | 7 | 0 | 0 | 0 | 0 | 0% |
| USD_CAD | 4 | 0 | 0 | 0 | 0 | 0% |
| 計 | **34** | **6** | **1** | **7** | **2/1** | **20.6%** [Wilson 10.3–36.8%] → **REJECT** |

- 是正前 baseline 31% (design 48 / 観測 15、2026-05-18〜07-24)。PR #172 (席優先 select + feed 統一) 後に**低下**。§7(a) 予測「31%→~100%」不成立。
- **分子と分母が交わらない**: 観測 7 行のうち closed-bar design に一致 1 行 (緩めて 2)。逆向き design 34 → row 化 1〜2 = **closed-bar 基準の真の capture ~3〜6%**。原因 = live は forming bar 評価 (log_return / vol20 / vol_quintile が部分バー量)、昇格根拠の凍結 grid (12.3y MASSIVE、BH-FDR m=3744) は closed-bar 母集団 → **grid は live が建てている母集団を記述していない**。(§2; MEMORY `project_ps_capture_estimand_disjoint_2026_09_09.md`)
- 3 席 0/17 の §8 帰属: hedge_block **0 本** (搬送 mode が席のみで対向建玉経路なし = 構造的 bind 不能) / 再起動 blackout **~0.2 本** (3.4 deploy/日 × 上界 5 分 = 1.2%; 説明には wall-clock 84% 被覆 = 実測 70 倍が必要) / **残余 ~100% = 帰属不能 = 「測っていない」**: `_block_counts` 揮発 / `gate_block_daily` 09-11 開始 / **C1 `evaluated_candidates` は `_dt_engine` 経路のみ、`compute_hourly_signal` は `log_candidates` を呼んでいなかった** (本番 31d summary 48 戦略に `price_shock_rev_*` ゼロで確定)。(§8-1〜8-3; MEMORY `project_ps_seat_supply_verdict_reject_2026_09_11.md`)
- 09-11 に計装追加 (R3、deploy 後 17 分で `donchian_momentum_breakout` 7 行実測)。(A) 上流 / (B) 下流の判別は registry `ps-seat-supply-hourly-c1-coverage` **2026-09-25** 待ち。帰属が出るまで供給是正を重ねない。
- `ps-carveout-regate-post-172` (09-30、clean live N≥10 で EV 判定) は look 未消費。capture 20.6% では N≥10 到達困難 → 「供給側の別問題」分岐見込み。
- 親監査 (07-29) の構造バグ: HourlyEngine winner-take-all × score 非対称 (ps 1.0 固定 vs DMB/KSB 5.0+) → family 供給 design の ~31%、敗北候補は痕跡ゼロ (二重消滅)。(MEMORY `project_preserve_bug_fixed_10cells_live_2026_07_28.md`)

### 1.4 LIVE 約定スループット (全システム)

| 量 | 値 | 出所 |
|---|---|---|
| LIVE 発火セル /30d | **124 (2026-05 anchor) → 24 → 26 → 11 → 4 → 3** | `wiki/analyses/live-roster-attrition-2026-09-06.md` §1; `m1-kpi-readout-and-mechanical-flip-2026-09-04.md` |
| 帰属 | B_LIVE_STOPPED 83 セル (anchor N=609 / **−469.8p**) / C_SHADOW_DEMOTED 12 (N=54 / −52.4p) / D 15 (N=28 / −26.2p、Phase-0 gate 導入前の allow-by-default) / **E_PROMOTED_UNATTRIBUTED 14 (N=34 / −25.1p)** = 帰属済み **88.7%** | 同 §2; MEMORY `project_roster_attrition_attribution_2026_09_06.md` |
| E 14 が閉じない理由 | **セル単位の LIVE 転送 block 理由を永続化する系列が無い** (`block_counts` はモード × family 粒度 + 市場オープン時間のみ) = 読み手の粒度不足。原則 3 により昇格済みセルの LIVE ゼロは正常でありうる | 同 §3.1 |
| E を全開放しても | 転換率 100% 仮定でも M6 ゲート (摩擦調整 EV>0) に反する。E は M3 の律速ではない | 同 §4 |
| LIVE 資格 family の発生率 | **~1 件/週** (直近 8 日で 2 件、同期間 shadow 536 行) | MEMORY `project_live_fill_estimand_shadow_conflation_2026_09_03.md` |
| LIVE 約定ゼロ期間 | **133 市場オープン時間 (実時間 7.5 日、2026-08-26 14:59Z〜09-03)** — 9 検知器全て無音 | 同 |
| 検知器の母集団誤り | `live_n_stagnation` が読む 500 行窓の **99.8% が shadow** (501 行中 LIVE 1)、shadow 80–111 行/日で窓は 7.67 日しか遡れない | 同 |
| 現行 LIVE 資格ロースタ | 3 セル (carry_dip / ps_eur_gbp / ps_aud_jpy)。N=30 到達 2.3 / 6.4 / 13.8 ヶ月。weekend_gap・kalman_d7 は LIVE 約定通算ゼロ (kalman は 09-10 に初 fill #859468) → **M3 最短 ~14 ヶ月** | `m1-kpi-readout...-2026-09-04.md` §6; MEMORY `project_m1_mechanical_flip_reader_2026_09_04.md`; `wiki/decisions/kalman-d7-minlot-carveout-prereg-2026-09-01.md` L46 |
| M1 | N=15 / +19.8p = **MECHANICAL_FLIP** (07-31 −123.2p が窓落ち、新規寄与 0)。bootstrap 95% CI [−217.6, +241.2]、P(sum≤0)=0.426。**分母が縮むほど満たしやすい縮退 KPI** | MEMORY `project_m1_mechanical_flip_reader_2026_09_04.md` |
| time-to-M2 | 中央 **2027-Q4〜2028** (P(M2≤2027 末) ≈ 15–25%)。**wg 級 1 本では M2 に届かない** (L1 5000u → +0.46%/月 < 0.5%、M2 は 2 セル要求) | meta-audit L106 |

### 1.5 P-S1(a) sweep_reversion_eurgbp_late — 「研究エッジ → shadow 実測」の変換係数の実例

出所: `wiki/analyses/ps1a-trigger-estimand-audit-2026-09-16.md`; MEMORY `project_t8_week1_gate_breach.md`
- 研究 grid net +6.22 p/t (spread 1.5p 控除) ≈ gross +7.72。shadow 実測 gross (spaced N=8) **+2.92 = 研究エッジの 38%**、摩擦を揃えると **net −3.33 p/t** (WR net 25%、s_entry 平均 8.06p、bootstrap P(net EV>0)=0.0224)。
- 判定器は gross を読み閾値は net 校正 → 誤 `OPTION_B_EXECUTE`。**cap をいくら締めても net は負、breakeven 7.72p 未満に締めると母集団 N=0** = cap 救済集合は空。→ Option C retire (user 決裁 09-17)。
- 含意: 「指値・cap で摩擦を選ぶ」経路は、エッジが摩擦より薄いセルでは選択肢として存在しない。

---

## 2. 摩擦の実測値

| 項目 | 値 | 出所 |
|---|---|---|
| 理論 RT (spread+slippage×2) | USD_JPY **2.14p** / EUR_USD **2.00p** / GBP_USD **4.53p** (limit-only enforced) / EUR_JPY **2.50p** / EUR_GBP ~3.0p (構造的不可能、停止) / XAU_USD 217.5p (停止 v8.4) | `wiki/analyses/friction-analysis.md` |
| BEV_WR | USD_JPY 34.4% / EUR_USD 39.7% / GBP_USD 37.9% / EUR_JPY 33.7% / EUR_GBP 57.1% | 同 |
| セッション別 (FX-only 推定) | London ~0.86p / Tokyo ~2.5p / NY ~2.0p (Total 列は XAU 込みで歪み) | 同 |
| **実測列 (clean live 30d N=94、2026-07-07)** | spread_at_entry **1.16p** / spread_at_exit **1.47p** / slippage **0.56p**。exit spread > entry spread = server 側クローズの流動性劣化。実測フロア **1.30p/t** | `wiki/analyses/friction-adjusted-ev-map-2026-07-07.md` §7-2 |
| **摩擦モデルの較正状態** | **4.5 ヶ月無較正** (kb-14、期日 09-18)。即席実測は過小推定側 (**EUR_JPY spread 1.9x**)。再較正文書は読んだ範囲に存在しない | `wiki/decisions/blocker-refutation-2026-09-10.md` L66 |
| BT `_BT_SLIPPAGE` 更新 (2026-04-21) | USDJPY 0.4→0.5 / EURUSD 0.4→0.5 / GBPUSD 0.5→**1.0**。USD_JPY Scalp WR 57.4→55.3% (Live 方向) | `wiki/analyses/bt-live-divergence.md` header |
| BT→Live 乖離 (6 バイアス合計) | **Scalp −14〜27pp / DT −5.5〜10pp**。Entry price / 固定 spread / SR 再計算 3bar vs 30s / TP・SL 構造 / Quick-Harvest ×0.85 / Instant Death bar vs tick | 同 §3, §6 |
| 摩擦調整 EV マップ (deduped shadow N≥30、post-cutoff 8,667 行) | **net+ = 1/39 entry_type、3/89 セル**。唯一 net+ type vix_carry_unwind shadow +1.86p → **live N=20 net −1.22p (all) / −1.90p (30d)** = BE/Trail 水増しそのもの。「現行母集団に live viable な正セル不在」 | `friction-adjusted-ev-map-2026-07-07.md` §1, §3, §4 |
| shadow 再 emit inflation | raw 10,648 → deduped 8,667 (**18.6%**)。dedup key = (entry_type, instrument, direction, bar_ts) | 同 §2 |
| wg 実測 RT | L0 実測 RT 7.70p / 凍結 stressed-net +7.90p / 日曜 open drift mean +3.15p | `lot-ladder-template-2026-08.md` §5; wg packet §5.3 |
| kalman 初 fill | broker realized +9.1p / demo +8.2p (差 0.9p 未判定) | registry `t9-kalman-d7-live-n10-ev-check` |
| carry_dip ledger | 特定済 7/11 本 broker ≈ **−41.1 pip** vs demo book **+103.0 pip** (符号逆、4 本未特定は storm fill) / broker 補正 +78.4 未監査 | `wiki/strategies/usdjpy_carry_dip_accumulator.md` §(6) |

---

## 3. 執行手段 (limit-only / FOK / cap / Quick-Harvest)

| 手段 | 状態 | 出所 |
|---|---|---|
| limit-only | GBP_USD で enforced (`[LIMIT_PLACED]`/`[LIMIT_FILL]` ログ存在)。macdh Scalp GBP DEMOTED (WR 40% / EV −0.818) | `friction-analysis.md`; `wiki/analyses/system-reference.md` L16, L265 |
| 指値 GTD (wg) | pre-reg §2.2 で既却下 (adverse selection、fill 特性が estimand 外)。FOK→IOC も無効 (halt は注文タイプ以前) | wg packet §3 (C) 列 |
| FOK 1 回・max_attempts=1 | wg 旧契約。AMENDMENT (B) で halt-race 限定再送 1 回のみ追加 (計 2 送信上限) | wg packet §1.2, §4-4 |
| spread cap | wg 10.0p (fail-closed shadow)。ps1a では cap をどこに置いても net 負 (cap は選べる変数ではない) | wg packet §4; ps1a audit §3 |
| Quick-Harvest | OANDA TP = demo TP × 0.85 (v6.8、RANGE MR は bypass) — BT 未反映バイアス⑤ | `system-reference.md` L152; bt-live-divergence §3-⑤ |
| spread_guard | 往復 spread / TP > 20% で hard block、免除なし → 高 WR / 低 RR 契約 (hull TP 4.4–5.6p) は常時死亡 | hull funnel §8.3-3 |
| slippage 基準 | `slippage_signal_price_basis="entry_fill"` = 送信時 quote vs fill。再送時は再送直前 quote へ差し替え (初回固定だと drift +3.15p が G1 に混入し N=6 で恒久誤停止) | wg packet §3, §4-5 |
| SL/TP ブラケット (carry_dip) | **宣言 disaster SL 150p は 11/11 で一度も現れない**。as-placed SL 9.8–28.5p (mean 17.9p、CV 35%、ボラ連動) / TP ~65.5p 固定 (CV 5.6%)。as-placed R:R 2.28–6.39 vs 宣言 0.53。執行側は置かれた値を厳密遵守 (slippage ゼロ) → **欠陥は order construction 上流の SL 側**。R3 決裁 08-05 から未決 | `usdjpy_carry_dip_accumulator.md` §(4), §(5) |
| wg のブラケット | stopLossOnFill 154.452 vs 市場 ~156.0 = ~155p (設計どおり) → SL 切り詰めは carry_dip 固有 | `weekend-gap-fade.md` L9 |

---

## 4. ロット階段と exposure cap

出所: `wiki/analyses/lot-ladder-template-2026-08.md`; MEMORY `project_lot_ladder_template_frozen_2026_08_05.md`; `system-reference.md`; MEMORY `project_shortest_path_decision_2026_07_10.md`

- 階段: **L0 1,000u → L1 5,000u → L2 10,000u → L3 30,000u**。昇格 = 段ごと R1 + user 承認 (SLA 48h、飛び級禁止)。降格 = R2 自動 (D1 slippage rolling6 > +2.0p / D2 at-rung N12 < −60p / D3 disaster 1 発 −1 段・2 発 L0 / D4 合成 DD 4/6/8% NAV / D5 Wilson gate 割れ)。
- 入口 **G3 = live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster 0** → 起案権のみ。**Wilson gate N_required = 41 > 30** (WR55%/payoff1.5 級) = G3 到達 ≠ 増額。
- 推奨 lot = min(Kelly half / worst-case イベント損失 ≤2.5% NAV / セル DD ≤2% NAV / 証拠金 worst-case ≤40% NAV @25x / **exposure cap net 20,000u/通貨・同方向 3 件** (`modules/exposure_manager.py`))。
- **wg の binding = disaster SL 150p (Kelly ではない)**: U_cellDD ≈ 5,441u → **L1 5000u が実効上限 @NAV 326k**。L2 は NAV ≥600k or disaster SL 再設計 R1。3 ペア同時セルは L2+ で 20k cap 改定 R1 同梱必須。L3 は 4.2/4.4/4.5 三重違反。
- L0→L1 機会費用 ≈ +1,036 JPY/月 (+0.32% NAV)。**meta-audit: L1 で +0.46%/月 < M2 0.5%** → M2 には第 2 セルの PASS→live 変換が必須。
- 現行 code 側の他の cap: OANDA lot hard cap 10,000u / max open 4 + per-pair 1 / DD_LOT_TIERS 0.2x defensive (v8.9 DD 12.39%) / MC ruin gate >0.7 は force-live にも適用継続。
- **agg-Kelly gate 恒久閉鎖**: 母体は rolling でなく固定 cutoff 2026-04-16 の累積 (−0.2758)、新セル月 5〜8 件では反転不能 → **正 EV セルも per-cell carve-out (`edge_cell_force_live` / min-lot bypass ≤1000u) 無しでは live 発火ゼロ**。N<10 sentinel のみ素通り (shadow-only にしたい mode は明示 block 必須)。
- 現在の live 送信可能 = wg×3 + ps×5 (全 1000u sentinel、D-c-1 carve-out) + kalman_d7 min-lot carve-out (09-01) + carry_dip。dmb×2 は意図的に bypass 外。(MEMORY `project_preserve_bug_fixed_10cells_live_2026_07_28.md`)
- グローバル DD lever は carve-out セルの rung に乗算しない — 防御は §6 D4 が代替。

---

## 5. live 側の構造的障害 (発見済み・修理状態)

| # | 障害 | 定量 | 状態 | 出所 |
|---|---|---|---|---|
| S1 | engine 毎 tick (30s) 再構築 → strategy instance の dedup/cooldown が live で dead | shadow raw 再 emit ~19%。hull 同一バー ~55 行 | order 層 per-bar dedup 07-06 実装 (PR #49) | MEMORY `project_engine_reconstruction_live_dedup_dead.md`; friction-ev-map §2 |
| S2 | `_is_xau_inst` UnboundLocalError が preserve 型 live 送信を送信直前クラッシュ | **3.5 ヶ月 (04-10〜07-28)** | 修復 PR #119 + pin | MEMORY `project_preserve_bug_fixed_10cells_live_2026_07_28.md` |
| S3 | wg 開場前送信 → MARKET_HALTED 決定論 cancel | 0/3 イベント、48/48 週末で 21:04 開場 | AMENDMENT (B) 09-10 実装、初回検証結果 KB 未記録 | wg packet |
| S4 | 共有 trail/bracket 層の **SL replacement storm** | kalman #859468 **33,675 tx / 2h51m / 3.28 tx/s**。carry_dip 11 fill 中 **5 fill (45%、下限)** で storm。2 族 (同一価格ループ / 目標振動)。**trailing 単調性違反 2/2 戦略非依存** (BUY の SL が −8p / −1.2p 緩む = risk-increasing) | 4 ガード (累積 tx breaker / 冪等 / 単調性 / dead-band) 必要、未実装 | `usdjpy_carry_dip_accumulator.md` 09-11〜09-16 更新 |
| S5 | carry_dip ブラケット SL 契約破棄 (宣言 150p → 9.8–28.5p) | 11/11 | R3 未決 (08-05〜) | 同 §(4) |
| S6 | LIVE 約定検知器が shadow を数えていた | 7.5 日 LIVE ゼロを 9 検知器が見逃し。126 日 no-op → 「修復」後も母集団誤り | `check_live_fill_stagnation` (`oanda_trade_id` 行のみ、閾値 120 市場 h) PR #221 | MEMORY `project_live_fill_estimand_shadow_conflation_2026_09_03.md` |
| S7 | C1 `evaluated_candidates` 4 ヶ月 write-only + bar_time NULL + HourlyEngine 経路に call site 無し | 517,378 行 / 54 戦略が読まれず。ps 5 席は 09-11 まで一切記録なし | route 08-24 / bar_time 08-24 / hourly 09-11 | hull funnel §4, §7; ps remeasure §8-3 |
| S8 | block counter の永続面欠如 | in-memory 再デプロイ毎ゼロ (3.4 deploy/日)、Render ログ ~2 週。HTF Hard Block は counter に一切残らない silent drop | `gate_block_daily` 09-11 (retention 90d) | hull funnel §3.1, §8.4 |
| S9 | forming-bar (live) vs closed-bar (grid) の estimand 非交差 | ps closed-bar capture 3〜6% | P-1 (R3 計測) / P-2 (R1) 未着手 | ps remeasure §2, §6 |
| S10 | spread_guard × TP-近接契約の構造衝突、shadow 分岐が動的 shadow を見ない | hull 29–36% > 20% 常時 | gate 変更は R1/R2 別決裁 | hull funnel §8.3 |
| S11 | HourlyEngine winner-take-all × score 非対称 → 敗北候補は痕跡ゼロ | family 供給 ~31% (07-29) → 席優先 select 後 20.6% | PR #172 後も未改善、帰属 09-25 待ち | MEMORY preserve_bug; ps remeasure §7 |
| S12 | 実弾ガバナンス: 人間リリースゲート無し、keeper が emergency_kill 管轄外で 9 日稼働、主要インシデント QA 起点 **0/8** | — | 監査パケット起票のみ (G1–G6 未実施) | `wiki/decisions/live-governance-gap-audit-packet-2026-09-10.md` |
| S13 | 待ちを安全にする機構の無言故障 5 系統 (E1 ingest 停止 / prereg_trigger_watch 4 日クラッシュ = 33 トリガ全滅 / zn-cache 4/4 失敗 / rate-anchor 17/17 失敗 / carry-dip 証拠時限消滅) | — | 個別 P1–P22 執行中 | `blocker-refutation-2026-09-10.md` §1 |
| S14 | kalman 執行: `same_price_5pip` 衝突が pre-reg 想定外の第 3 gate、fire-info は 1/3 レート素通し | — | 未処置 | blocker-refutation §2 (t9-kalman 行、watching-legit-misc) |
| S15 | halt cancel を `"OPEN buy ok but no tradeID"` と誤分類する共通 error 分類バグ | — | 未修理 | `weekend-gap-fade.md` L7 |

---

## 6. 段別「殺している原因」の要約 (facts の骨格)

1. **family → PASS (4%)**: エッジ密度 < リテール摩擦 + 認定閾値。処理能力の問題ではない。
2. **PASS → live 約定 (0/3)**: 執行契約がデータソース (MASSIVE forming bar 21:01) と broker 開場 (21:04–05) の時間差を無視。修理済み、実証はまだ。
3. **シグナル → select_best (hull 12.59 → 7.9/週)**: HTF Hard Block −25.4% + 直列化 −19%。期待どおりで健全。
4. **select_best 勝者 → trade 行 (5.6%)**: `_tick_entry` ガード 6 系統の合算 (spread_guard / same_price / session_pair Tokyo / score_gate / hedge_block / mtf)。単一犯人なし。order 層は無実。
5. **design signal → row (ps 20.6%、closed-bar 3–6%)**: forming-bar estimand 非交差 + HourlyEngine 計装ゼロで残余帰属不能。
6. **row → clean live 約定**: agg-Kelly gate 恒久閉鎖 → carve-out セルのみ (1000u sentinel)。LIVE 資格 family ~1 件/週。
7. **約定 → 正 PnL**: shadow net+ 1/39 type・3/89 cell、唯一の候補は live で負。BE/Trail 水増し + 摩擦 4.5 ヶ月無較正。
8. **約定 → 契約どおりの exit**: 共有 trail 層の storm (45% 下限) + 単調性違反 + SL 契約破棄 (11/11) → realized が昇格根拠の estimand から逸脱。
9. **PnL → ロット成長**: G3 (N≥30) は 2.3〜13.8 ヶ月/セル、Wilson N_required 41、disaster SL 150p が L1 で binding → 1 セル L1 で +0.46%/月 < M2。

---

## 7. Open questions (本ノート時点、文書のみで解決不能)

1. weekend_gap 09-13 (改定後初イベント) の qualify / fill 結果が読んだ KB に無い。registry g0prime (09-28) で確認要。2 連続不成立なら執行モダリティ再審 (R1)。
2. ps 3 席残余の (A) 上流 / (B) 下流 判別 — `ps-seat-supply-hourly-c1-coverage` 2026-09-25。
3. 摩擦モデル再較正 (kb-14、期日 09-18) の実施記録が無い — 期日超過か未着手か。EUR_JPY 1.9x の含意で net EV マップは楽観側にさらに寄る可能性。
4. carry_dip SL ブラケット生成コードの root cause (R3、08-05 から未決) と ledger 4/11 未特定。storm 4 ガードの実装決裁。
5. hull spread_guard 免除 / shadow 分岐の動的 shadow 参照 — 4原則#3 との整合は R1/R2 別決裁。
6. E2_SILENT 4 セル (`SQUEEZE_REDESIGN_V2` env) の「意図的無効」vs「配線落ち」判別 — registry 10-06。
7. `live_fill_stagnation` 閾値 120h は n=15 較正 — 12-03 再較正。
8. F2 (12-31) までに PASS→live 変換係数を N≥1 で測れるか — wg 頻度 ~3.3 qualifying/月 × fill ~0.9 × cap skip 10–20% → N≈8–11 見込みだが、G1 08-31 評価では 4 週連続発火ゼロの実績あり (signal-rate と live-fill-rate の混同に注意)。
9. 実弾ガバナンス監査 G1–G6 (自己申告ゲート / 実弾コンポーネント台帳 / kill 到達性) は起票のみで未実施。
