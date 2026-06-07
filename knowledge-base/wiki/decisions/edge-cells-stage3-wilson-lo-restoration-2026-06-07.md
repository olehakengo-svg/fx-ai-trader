# Edge-Cell Stage-3 Wilson_lo Restoration to Bonferroni-Correct 0.55 (2026-06-07)

## Status

**rule:R3** (Immediate — 算数破綻 / 構造バグ、365d BT スキップ可)
**Supersedes**: [edge-cells-stage3-live-promote-2026-05-26.md](./edge-cells-stage3-live-promote-2026-05-26.md) (Wilson_lo ≥ 0.30 緩和の selection bias 受容方針)
**Phase**: 4.5 architectural review (loss surge → recovery → root-cause iteration の終結)
**LOCK timestamp**: 2026-06-07 (awaiting user sign-off)

## TL;DR

2026-05-26 LOCK で **selection bias 受容**として Wilson_lo を 0.55 (Bonferroni m≈480, α=1.04e-4) から **0.30 へ緩和**、撤退条件 (watchdog) で吸収する仮説で 12 cell を Stage-3 直行 LIVE 化した。**12 trading days で 5/12 cell (42%) が損失 disable**、watchdog が Bearer auth bug で自動執行不能、累積 -38,215 JPY (STOP_LOSS のみ集計)。**仮説 (撤退条件で吸収) は実証で否決**。Wilson_lo 復帰 + 残存 cell の Bonferroni-correct 再判定が systemic fix。

## Empirical evidence (2026-05-26 → 2026-06-07 = 12 trading days)

### 12-cell post-mortem

| # | Cell | 元 Wlo | Live N | 結果 | Disable 理由 |
|---|---|:---:|:---:|:---:|---|
| E1 | dt_bb_rsi_mr/ASN/SELL | 0.77 | 16 | 🔴 OFF 06-04 | Shadow N=16 WR=37.5% Wlo=0.18 vs pre-reg 100%/0.77, 完全崩壊 |
| E2 | session_time_bias/EUR_USD/LDN/exempt | 0.46 | ≥9 | 🔴 OFF 06-07 | 4/4 post-recovery SL EUR_USD SELL LDN, MR-in-trend |
| E3 | dt_bb_rsi_mr/EUR_USD/SELL | 0.44 | 1+ | 🔴 OFF 06-07 | 06-04 10:15 SL during LDN, same MR family |
| E4 | bb_rsi_reversion/NY/SELL | 0.44 | 20 | 🔴 OFF 06-04 | Live N=20 WR=35% EV=-0.84p Wlo=0.18 (pre 0.44) 全 LOCK 撤退 trigger 破綻 |
| E5 | dt_bb_rsi_mr/GBP_USD/SELL | 0.43 | 0 | ✅ ON | (未 fill) |
| E6 | rsk_gbpjpy_reversion/GBP_JPY/BUY | 0.39 | 0 | ✅ ON | (未 fill) |
| E7 | dt_bb_rsi_mr/GBP_USD/ASN | 0.39 | 0 | ✅ ON | (未 fill) |
| E8 | session_time_bias/EUR_USD/LDN | 0.37 | 8 | 🔴 OFF 06-04 | Live N=8 EV=-3.51p / Shadow N=8 EV=-5.24p 両 negative |
| E9 | orb_trap/GBP_USD/SELL | 0.36 | 0 | ✅ ON | (未 fill、cfd-trader P3W1 で +5.81/N=22 sanity 別途) |
| E10 | wick_imbalance_reversion/GBP_USD/no_go | 0.34 | 1+ | ✅ ON | 06-01 LDN fill 1 件 caveat |
| E11 | dt_bb_rsi_mr/NY/SELL | 0.33 | 0 | ✅ ON | (未 fill、MR family family-risk あり) |
| E12 | sr_anti_hunt_bounce/EUR_JPY | 0.31 | 1+ | ✅ ON | E12 caveat: demo_trades meta loss `[[project_sr_anti_hunt_demo_trades_meta_loss_2026_06_03]]` |

**5/12 cell (42%) が 12 日で disable。残 7 cell も 5 cell が fill ゼロ = empirical evidence なし**。実質的に **edge を実証したのは E10 (1 件) と E12 (1 件) のみ** — N=2 で empirical edge を主張できる cell はない。

### Loss attribution (7d 直近)

- session_time_bias 系: -3,390 JPY (24 fills, WR 42%)
- bb_rsi_reversion: -1,474 JPY (18 fills, WR 33%)
- 上記 2 戦略 = MR family が 86% fill / 91% loss
- 全体 7d net: **-5,343 JPY / -58.4 pip / WR 40.8%**
- 全期間 (2026-04-08 → 2026-06-07) Live net: **-26,160 JPY / -342.9 pip / WR 39.1%**
- STOP_LOSS 件数: 385/493 = **78% trades が SL hit**

### Structural pattern (3 つの確証)

1. **TV ≠ MASSIVE**: 同日 (2026-06-07) の独立 BT で確証
   - sr_fib V3: TV PF=1.194/1.29 (10mo) → Codex PF=0.76/0.65 (12y)
   - Kalman D7 v18e: TV PF=1.04-1.61 (10mo) → Codex PF=0.68-0.86 (12y)、全 pair WFO 0/3 FAIL
   - TV 短期 sample は **favorable local window** で promotion 判断材料にできない

2. **WR 維持 / PF 反転** = small wins, large losses pattern (R:R 紙上のみ)
   - session_time_bias 7d: WR 42%、TP 到達率 **2.0%** (1/49)、R:R 1.95 紙上、実効 R:R ≈ 0.1
   - Kalman D7 v18e 12y: WR 62-68%、PF 0.67-0.86 (全 pair PF<1)
   - 出口設計 (TP/trailing) が prod regime に未整合

3. **Architectural signal**: 2 週で 13+ bypass / revival / override / hot-fix commit
   - Kalman D7 LIVE / LIVE_PROMOTE_LOSERS / shadow-dedup bypass / OANDA_FORCE_FLAT_UNITS / count-gate bypass / E1-E12 manual disable × 2 / GBP_USD revival
   - watchdog Bearer bug 1 ヶ月 silent (2026-05-26 → 2026-06-07)
   - **Stage-3 LIVE Promote 機構そのものが drift を生む構造**

## Statistical case for Wilson_lo = 0.55

元 LOCK doc の Source data (LOCK 母集団):
- 期間: 2026-05-06 → 2026-05-26 (20 days), N=1,795 shadow trades
- Bonferroni m ≈ 480 (12 cells × 軸組合せ ≈ 40)
- α=0.05 / 480 = **1.04e-4**
- 必要 Wilson_lo: **0.55** (Bonferroni-correct)
- 元 LOCK 採用値: **0.30** (緩和、selection bias は撤退条件で吸収)

12 日実証:
- Bonferroni-correct 0.55 を満たす cell: **0/12** (最高 E1 の 0.77 だが 100% WR は post-hoc selection の典型、Live 実 N=16 で WR=37.5% に崩壊)
- 0.40-0.55 範囲: **3 cell** (E2/E3/E4)、全て disable 済
- 0.30-0.40 範囲: **8 cell**、うち disable 1 (E8)、未 fill 5、caveat 付き active 2 (E10/E12)
- 0.30 未満: 0 (LOCK 母集団から除外済)

→ **Wilson_lo 0.30 緩和は実証で支持されない**。0.55 復帰 + 個別承認制が systemic fix。

## Decision

### 1. **Wilson_lo 閾値を 0.55 (Bonferroni-correct) に復帰**

```python
# modules/edge_cell_promote.py (proposed)
WILSON_LO_THRESHOLD = 0.55  # Bonferroni m=480, α=1.04e-4 (was 0.30)
```

新規 Stage-3 LIVE promotion は **Wilson_lo ≥ 0.55** を必須要件にする。

### 2. **残 7 cell の Bonferroni-correct 再判定**

現状 stage=1 の cell (E5/E6/E7/E9/E10/E11/E12) は **次回 reconciliation までは stage=1 維持** (即時 disable しない、未 fill cell の preemptive disable は memory `[[feedback_audit_purpose_design_not_n]]` 違反)。

ただし以下 2 件は notice 付き:
- **E11** (dt_bb_rsi_mr NY SELL): MR family、disabled E4/E1 と同 pattern。**Live N=1 fill 観測時点で stage=0 自動切替** を pre-reg LOCK
- **E5** (dt_bb_rsi_mr GBP_USD SELL): 同上、**Live N=1 fill で stage=0**

### 3. **watchdog 修復 (commit 8cf5ecc6 で着手済)**

- `tools/edge_cell_watchdog.py` の Bearer auth bug 修正済
- `render.yaml` に `API_AUTH_TOKEN: sync: false` 追加済
- **POST-DEPLOY ACTION REQUIRED**: user が Render dashboard で `API_AUTH_TOKEN` を設定 (crn-d8aontgg4nts73dajpa0)
- 設定完了後、watchdog は新 Wilson_lo=0.55 thresholds で自動執行 (15 分毎)

### 4. **既存 intentional exceptions の継続判断**

以下の exception は新 Wilson_lo=0.55 基準でも特例として継続するか否か **個別判断必要**:

| Exception | 現状 | 新基準下の判定 | 推奨 |
|---|---|---|---|
| Kalman D7 v15/v18f/v18e LIVE (USDJPY M15) | LIVE 0.5x lot | 12y MASSIVE PF=0.861, WFO 0/3 FAIL | **user 判断: 継続 or 停止** |
| vix_carry_unwind USDJPY 1.0x (Overlap pilot) | LIVE 1.0x lot | memory `[[project_vix_carry_1x_intentional_exception_2026_05_21]]` | **継続** (Rule 1 未充足だが pre-reg 撤退条件あり) |
| ZZ Pivot v60 + SizeReduce (EURUSD M15) | LIVE 1.0x/0.5x SizeLever | TV 1y OOS PF 1.222→1.294、WFO 3/3 directional | **継続** (SizeLever 仕組み実証済) |

### 5. **Promotion criteria 更新 (LOCK)**

新 Stage-3 LIVE promotion 基準:

```yaml
required:
  wilson_lo: ">= 0.55"  # Bonferroni-correct (was 0.30)
  bt_pf: ">= 1.20"  # Codex MASSIVE 12y で確証 (TV BT は不可)
  wfo_pass: ">= 2/3 folds"  # temporal robustness
  bonferroni_m: explicit  # task spec に m と α_eff を明記
  data_source: MASSIVE 12y native parquet  # resample 不可、coverage_years >= 10.8

ramp_path:
  stage_0: Shadow accumulation (N>=30, no Live)
  stage_1: Micro-Live 1000 units (N>=10, 2 weeks)
  stage_2: Mid-Live 5000 units (N>=30, 1 month)
  stage_3: Full-Live 10000 units (N>=100, watchdog auto-demote 必須)

intentional_exceptions:
  approval: user_signed decision_doc
  watchdog: pre-reg withdrawal conditions REQUIRED
  isolation: lot_boost <= 0.5x for non-Bonferroni cases
```

### 6. **元 LOCK の Success criteria 評価 (2026-06-23 予定 → 早期評価)**

元 LOCK: 「2026-06-23 (LOCK + 4週) 時点で Active cells ≥ 6/12、Live cumulative ¥ > +¥30,000、Max DD < 5%」

中間評価 (2026-06-07、LOCK + 12d):
- Active cells: **7/12** (条件 ≥6 名目 PASS だが、5 cell は未 fill = empirical edge なし)
- Live cumulative: **-¥38,215** (条件 +¥30,000 に対し -¥68,215 乖離、絶対 FAIL)
- Max DD: 47.22%/65.20% (元 LOCK 想定の元本 DD 8% 超過、絶対 FAIL)

→ Success criteria **絶対 FAIL** が中間時点で確定。元 LOCK の "失敗時: 全 cell shadow 復帰" pathway は今すぐ発動が筋論だが、本 doc では **Wilson_lo 復帰 + 個別 cell 維持 (撤退 trigger 強化)** を中間策として採用。

## Implementation tasks

1. **`modules/edge_cell_promote.py`** — `WILSON_LO_THRESHOLD = 0.55` 定数追加、新規 cell 追加時の gate に使用
2. **`tools/edge_cell_watchdog.py`** — 既修正 (commit 8cf5ecc6)、新 Wilson_lo=0.55 thresholds で next-promote 候補を block する logic 追加
3. **`tools/promotion_gate.py` (新規)** — 新規 Stage-3 candidate の自動評価 (Wilson_lo, BT PF, WFO, Bonferroni m を一括チェック)
4. **`tests/test_promotion_gate.py`** — 6 cell 分の fixture で gate 動作テスト
5. **wiki/index.md / tier-master.md** — Stage-3 LOCK 表記を本 doc にリンク更新
6. **本 decision doc の link を memory `[[project_edge_cell_stage3_recovery_phase2_2026_06_07]]` に追記**

## Verification (success criteria, 2026-07-07 reconciliation)

- LOCK + 30 days 時点で:
  - 追加の cell disable 0 件 (5/12 disabled が安定)
  - Live cumulative ¥ > -¥45,000 (現 -¥38,215 から +¥7,000 以内の bleed 維持)
  - watchdog 自動 demote 動作 ≥ 1 件 (Bearer fix 動作確認)
  - 新規 Stage-3 promote 0 件 (Wilson_lo ≥ 0.55 を満たす cell 不在の予測)

達成条件 NG なら **全 active cell shadow 復帰 + Phase 5 (新 LIVE 制度設計)** へ。

## Linked memory / references

- [[project_oanda_loss_surge_2026_06_03]] — 1st loss surge
- [[project_edge_cell_stage3_recovery_phase2_2026_06_07]] — 2nd recovery (E2/E3 disable + GBP_USD revival 削除 + watchdog fix)
- [[feedback_partial_quant_trap]] — Wilson_lo の Bonferroni 補正必須性
- [[feedback_ma_filter_breaks_mr]] — MR in trend 罠の系統的再現
- [[feedback_codex_mock_test_trap]] — TV BT ≠ prod の TV 版確証
- [[feedback_shadow_first_quant_architecture]] — exception の意図的設計
- [edge-cells-stage3-live-promote-2026-05-26.md](./edge-cells-stage3-live-promote-2026-05-26.md) — SUPERSEDED 元
- [vix-carry-1x-exception-2026-05-21.md](./vix-carry-1x-exception-2026-05-21.md) — 継続 exception
- [pivot_detector_v2_5_live_exception_2026_05_26.md](./pivot_detector_v2_5_live_exception_2026_05_26.md) — 関連 exception

## Sign-off

- [ ] User approval: 2026-06-07 ____ UTC
- [ ] Implementation merged: ____
- [ ] watchdog API_AUTH_TOKEN set on Render dashboard: ____
- [ ] LOCK 発効: ____
- [ ] 30-day reconciliation target: 2026-07-07
