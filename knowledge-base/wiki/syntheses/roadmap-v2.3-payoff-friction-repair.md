# ロードマップ v2.3: 決済非対称と摩擦の是正 — 負エッジ確定局面からの構造回復

> **⚠️ DRAFT — user レビューで正式化。** それまで autopilot は本 draft の **R2/R3 項目のみ実行可**、**R1 項目は user 承認後**。目標 (月利21.6% 数学的上限への段階接近、user 承認 2026-06-12) は不変 — 本 draft が変えるのは作業計画のみ。

**作成日**: 2026-07-06 (handoff タスク `fx-roadmap-v23-handoff` タスク2)
**旧版**: [[roadmap-v2.2-win-conversion]] (2026-06-12、全12項目クローズ済み PR #44-#50)
**根拠**: 2026-07-06 本番実測 (Render production API、clean live `oanda_trade_id != ''` N=92 / clean shadow N=2,466 / risk dashboard / OANDA status)

---

## v2.2 からの前提変更 (なぜ v2.3 が必要か)

v2.2 は全12項目をクローズした (止血セル停止・T5 JPYキャップ執行・T8 forensic・T10/T11 KILL・pre-reg 監視自動化・autopilot 稼働)。しかし **30d clean live は改善せず悪化**した。以下は 2026-07-06 実測 (全12,290件取得、30d 窓 = 06-06〜07-06、XAU除外・dedup除外):

1. **clean live 30d = N=92 / −242.6 pip / WR 55.4% / EV −2.64/t** — v2.2 起点 (N=84 / −37.9p) から **6.4×悪化**。W23 以降 (6月後半) に再悪化、W20-21 の一時プラス転換は持続せず。
2. **負けの真因が特定変更された = 決済非対称 (payoff 0.27) + 摩擦**:
   - avg_win **+2.40p** / avg_loss **−8.90p** → **payoff ratio 0.27**。勝ちを早利確し負けを引っ張る非対称。close_reason は 92 件中 83 件が SL_HIT / OANDA_SL_TP。
   - 摩擦 **366.2 pip (3.98/t)**。摩擦除去後の gross は **+123.6p** = 摩擦が符号を反転させている。avg_win +2.4p は摩擦 3.98p に食われて即マイナス。
   - **どの entry_type も「摩擦調整後 EV が正」にならない限り live 転送に耐えない**、が定量的結論。
3. **統計的に有意な負エッジが確定 (Rule 2 該当)** — Kelly edge=−0.296 / rec_fraction=0.0、DSR haircut=100% (n_trials=14 で有意性なし)、defensive_mode 発動・lot 0.2x。「傾向」でなく「確定した現状評価」。
4. **shadow N は飽和、しかし一様に負** — clean shadow 30d N=2,466、稼働 20 entry_type が **全て N≥30 到達済み**、かつ閉足 EV はほぼ全戦略 **< −0.5** (降格候補域)。
   - → **v2.2 のボトルネック定義「クリーン N の蓄積速度」は superseded**。現局面は「データ不足」ではなく「**蓄積したデータが一様に負を示し、正EVセルが不在**」。蓄積速度はもはや律速でない (KB更新提案 — 下記「ボトルネック」参照)。
5. **実口座 NAV = 278,905 JPY / 累積 pl = −80,216 JPY (初期比 約 −22%)**。ダッシュボード表示 DD=99.3% は `eq_peak=16.9` の極小分母アーティファクト ([[fable5-system-audit-2026-07-02]] P1-5 確定)。v2.3 の監視 DD は実口座 NAV(JPY) 基準に統一する。

## コンセプト: 「決済構造を診断し、負け経路を細粒度で止め、clean-N 整合性を回復し、エッジ要因解析を継続する」

```
診断: payoff 0.27 の構造解明 (なぜ勝ち+2.4/負け−8.9 か) — TP早利確 vs SL遠置き vs slippage非対称の分離
止血: 負け live セルを ペア×戦略×方向 粒度で R2 停止 (blanket pause は原則1に反する = しない)
整合: clean-N を汚染/死にゲートから守る (Fable5 Phase B: P1-3 / P1-9 / P1-2)
横断: エッジ要因解析シリーズ継続 — 「高WR×負EV」群 (payoff 改善の効果が最大) を N降順で
```

**KPI (30d rolling, clean live `oanda_trade_id != ''`, dedup除外, XAU除外) — v2.2 定義の現在値 + v2.3 追補**

| KPI | v2.2 定義 | 2026-07-06 実測 | v2.3 での扱い |
|---|---|---|---|
| M1 | clean live 30d PnL > 0 | **−242.6p (未達)** | 存置。ただし payoff 是正なしでは構造的に到達不能 |
| M2 | 負けクラスタ (counter-USD MR + 薄商い) 寄与 > −10p | **union N=25 / −42.8p** (全損の 18%) | 存置。残 82% は別クラスタ = 決済非対称が主 |
| M3 | clean live N≥30 セルを 3 個 | **0 個** (最大 trendline_sweep GBP_USD BUY N=13) | 存置。live N は依然薄い (shadow とは別問題) |
| M4 | 月利トレンド | 持続的プラス転換なし (W20-21 一時+ → W23以降 −) | 存置 |
| **M5 (新)** | — | payoff ratio **0.27** | **v2.3 中核 KPI**: payoff → 摩擦分岐点 (avg_loss 前提で ≳0.5) 超へ |
| **M6 (新)** | — | 摩擦調整 EV = gross−friction、生存セル 0 | **昇格ゲート**: セル単位で摩擦調整後 EV>0 を live 転送の必要条件に |
| **DD 監視** | 表示 DD% | 表示 99.3% = 分母産物 / 実 NAV −22% | 実口座 NAV(JPY) 基準へ統一 (表示 DD% は監視 KPI から除外) |

---

## WS1: 止血 — 負け live セルの細粒度停止 (Rule 2, 今週)

**原則1 (攻める) / 原則4 (攻撃は最大の防御) に従い blanket live pause はしない。** defensive lot 0.2x + Kelly 0.0 は既に全体を最小化済み。真因は特定セルの負けなので **ペア×戦略×方向 粒度で止血** する (lesson: 集計は相殺する)。

| # | 項目 | Rule | 状態 | 採用/棄却条件 |
|---|---|---|---|---|
| T1 | **GBP_USD live 出血セルの forensic + R2 demote** — GBP_USD live は N=38 / mean −3.42 / **−129.9p (全損の 53%)**。ただし instrument 集計 = 複数戦略混在。cell (戦略×dir) 粒度で分解し、N≥10 ∧ EV<0 ∧ Wilson_lo<BEV のセルを `SHADOW_DEMOTED_CELLS` へ (code pin) | R2 | **draft: autopilot 実行可 (R2)** | cell 単位 EV≥0 or N<10 なら据置。ELITE_LIVE [[trendline-sweep]] GBP_USD が該当する場合は BT (EV+0.599) との live 乖離を先に forensic |
| T2 | **live 決済非対称の緊急 mitigation 評価** — payoff 0.27 の即効 lever があるか (例: OANDA 側 SL/TP 幅の摩擦調整、trailing 無効化) を診断。**パラメータ変更は R1 なので draft では診断のみ、実装は user 承認後** | R1 (実装) / R3 (診断) | draft: 診断のみ autopilot 可 | WS-Diag T3 の結論待ち |

## WS-Diag: 決済非対称の構造診断 (Rule 3 診断 → Rule 1 実装、v2.3 中核)

payoff 0.27 は v2.3 の最重要問題。**診断は R3 (analyses/ に数値根拠を文書化)、TP/SL 等のパラメータ変更は R1 (365d BT/Live N≥30 + Bonferroni + pre-reg LOCK)。カーブフィッティング禁止 — TV Pine を eval canon とし (MEMORY `feedback_tv_edge_discovery_loop`)、Python BT の payoff/WR は BE/Trail 水増し (MEMORY `project_be_trail_inflates_python_bt_wr`) を必ず ablation してから読む。**

| # | 項目 | Rule | 状態 |
|---|---|---|---|
| T3 | **payoff 0.27 の要因分解** — 勝ち +2.4 / 負け −8.9 の非対称を (a) TP 早利確 (b) SL 遠置き (c) slippage 非対称 (d) close_reason 分布 (SL_HIT 83/92) に分離。clean live N=92 + 対応 shadow で MFE/MAE 分布を実測。**「なぜ realized R:R が戦略 target R:R を大きく下回るか」** を確定 | R3 (診断) | draft: autopilot 可 |
| T4 | **摩擦調整 EV マップ** — 稼働 20 entry_type × pair × dir を gross EV − per-pair friction (friction-analysis.md) で再評価し、摩擦調整後に正の候補が存在するか網羅。M6 の母集団確定 | R3 | draft: autopilot 可 |

## WS2: 昇格候補 N蓄積・繰越 (v2.2 繰越, Rule 1 正順)

| # | 項目 | 統計条件 | 状態 |
|---|---|---|---|
| T5 | **orb_trap GBP_USD SELL (E9) N蓄積** (v2.2 T6 繰越) | clean N≥30 → H1 ∧ WF 3-fold ∧ Bonferroni(m=116) 再評価。N 以外通過済 (WR.783/PF13.6/Wilson.581/Kelly.725) | E9 継続稼働。触らない |
| T6 | **sweep_reversion_eurgbp_late (EUR_GBP) DEFER 決定点** (v2.2 T8 繰越) | HTF-rescued shadow N≥10 → EV 判定 (R1) / 2026-09-30 に N<5 → retire (R2)。**復帰の追加前提 = order 層 12-bar min-spacing 実装** (検証 estimand との一致、[[t8-week1-gate-breach-2026-07-06]] forensic #3) | pre-reg 監視済 (registry `t8-sweep-defer-decision`)。触らない |
| T7 | **hull_donchian_fade (EUR_USD) ゲート① 再評価** (v2.2 T8 繰越) | shadow 実測 1.5/週 vs 期待 13.3/週 = 下側割れ見込み。頻度 band 割れ確定なら sweep と同じ retire 経路。ゲート④(改) は 2026-07-06 発効済み ([[t8-week1-gate-breach-2026-07-06]]) | pre-reg 監視済 (registry `t8-hull-shadow-freq`) |
| T8 | **carry dip v3 dormant 監視** (v2.2 T7 繰越) | ceiling 159.50 レジーム前提崩壊の dormant-by-design。復帰 = D1 close<159.50 (registry `t5-jpy-cap-restore-price` に相乗り) | 監視のみ。QUALBAR telemetry 本番稼働済 |
| T9 | **kalman_d7 発火監視** (v2.2 T9 繰越) | 3 variant 合算 vs BT 期待 3.9/週。分子ゼロ継続なら Render ログ QUALBAR (分母) と突合 | pre-reg 監視済 (registry `t9-kalman-d7-fire-info`) |

## WS3: エッジ要因解析シリーズ継続 (司令塔直轄)

Edge Factor Audit #1-#6 (2026-06-12) + T10 bb_rsi KILL (2026-07-02) で高N shadow 戦略は一巡。**次候補は N 単純降順でなく「高WR × 負EV」群を優先** — エントリーは効いているが決済/摩擦で殺されている典型で、WS-Diag の payoff 改善が最も効く母集団。falsified 済みシリーズ (H4 level / channel / sweep&reclaim horizontal / mtf SELL / bb_rsi / T11 counter-USD) の再試行禁止。

| # | 候補 | clean shadow 実測 | 分析主眼 | Rule |
|---|---|---|---|---|
| T10 | **gbp_deep_pullback** | WR 72% / EV −1.39 | 高WR×負EV の筆頭。pullback エントリーのエッジ有無を IC で分離し、payoff/摩擦 kill か entry 劣化か判定 | R1 (促進時) / R3 (診断) |
| T11 | **sr_anti_hunt_bounce** | WR 63% / EV −4.49 | SR family の唯一の survivor (anti-hunt thesis、他 SR は audit KILL 済)。EV −4.49 は payoff/摩擦か、それとも thesis 劣化か。斜めTL固有の liquidity-hunt エッジ (MEMORY `project_sweep_reclaim_horizontal_falsified`) との整合確認 | R1 / R3 |
| — | (flag) **trendline_sweep 乖離** | live/shadow WR 63% / EV −1.60 vs BT EV +0.599〜+0.927 | ELITE_LIVE 唯一戦略の live 実測が BT を大きく下回る。WS1 T1 と統合して forensic | — |

## WS4: clean-N 整合性・品質ゲート (Fable5 監査 Phase B, R3 構造fix)

**clean N 蓄積が最優先 → その N を汚染/死にゲートから守るのが最も寄与度が高い。** 以下は全て診断済み構造バグ (R3、365d BT 不要)。autopilot 実行可。詳細: [[fable5-system-audit-2026-07-02]]。

| # | 項目 | Rule | 寄与 |
|---|---|---|---|
| T12 | **P1-3: stale SHADOW_MIGRATION ブロック削除** — `demo_db.py:473-533` が restart 毎に現役セル (dt_bb_rsi_mr E1/E3/E5/E7/E11, bb_squeeze_breakout) を is_shadow=0→1 再汚染。後継 backfill が存在するため削除で対応 | R3 | **clean live/shadow 分離を直接汚染**。最優先 |
| T13 | **P1-9: 死にゲート `_kelly_block` 修正** — `_get_strategy_kelly_clean` が clip 済み full_kelly を返し `_shadow_promotion_decision` の負値判定が構造的不発 (60652ac1 と同型)。`full_kelly_raw` 化 | R3 | **昇格経路そのものが機能不全**。正EVセル出現時に昇格できない |
| T14 | **P1-2/2b: BE/Trail ablation を scalp/1H×2 へ展開 + fut_close tie-break** — daytrade のみ ablation guard 済、他3エンジンに +20pp 水増し残存。fut_close tie-break は4エンジン全部 | R3 | **昇格判断が使う EV/WR の水増し源**。WS-Diag の payoff 実測とも直結 |
| T15 | **P1-7/P1-8/P1-6 (低優先)** — CI paths filter 撤廃 + hip1 job 化 + dev.agent.yaml 訂正 / scalp QUALIFIED_TYPES drift 検査 / 再送ガード共通化 | R3 | 品質ゲート穴。順次 |

## 棄却・据置 (このロードマップで追わない)

- **blanket live pause** — 原則1 (攻める) に反する。止血は WS1 の細粒度停止で行う
- **falsified 済みシリーズの再試行** — H4 level / channel / sweep&reclaim horizontal / mtf SELL / bb_rsi / T11 counter-USD (MEMORY 参照)
- **shadow 発火の停止** — 原則3 (Shadow は UTC 固定で削らない)。N 飽和でも Bonferroni power のため継続
- **multi-bar cooldown の order 層実装** — sweep (T6) 復帰時のみ必要。現状 code pin OFF のため保留
- **P2/P3 群** (Fable5) — 衛生項目。WS4 の後、寄与度順に

## ボトルネック (v2.2 から更新提案)

**v2.2 の「クリーン N の蓄積速度」は superseded。** shadow N は飽和 (20 entry_type 全 N≥30) し、律速ではなくなった。**v2.3 の真のボトルネック = 「正の摩擦調整 EV を持つセルの不在」** — 蓄積したデータが一様に負を示し (payoff 0.27 / 摩擦 366.2p が gross を反転)、昇格母集団が存在しない。

したがって寄与度の優先順位は:
1. **決済非対称の診断 → 是正** (WS-Diag / WS1 T2) — payoff 0.27 が全 KPI の律速。ただし実装は R1 (BT水増し ablation + TV canon + pre-reg)
2. **負け live の細粒度止血** (WS1 T1) — NAV 実損の即時抑制、R2
3. **clean-N 整合性の回復** (WS4) — 正EVセルが出現したとき昇格経路が機能する前提条件、R3
4. **エッジ要因解析継続** (WS3) — 高WR×負EV 群から payoff 改善余地を探索

**この draft は user レビュー後に正式化。** それまで autopilot は R2/R3 項目 (WS1 T1, WS-Diag, WS4 全, WS2 監視系) を実行してよい。R1 項目 (WS1 T2 実装, WS-Diag T3 由来のパラメータ変更, WS3 の促進) は user 承認後。

---

## 検証ログ (2026-07-07 独立再計測)

commit 前に別セッションが production API から新規スナップショット (12,325 行、`tools/render_trades_snapshot.py`) を取得し再導出:

- **clean live 30d (06-06〜07-06)**: N=92 / −242.6p / WR 55.4% / EV −2.64 / avg_win +2.40 / avg_loss −8.90 (payoff 0.27) — **本 draft の中核数値を完全再現** ✅
- **shadow 30d raw**: N=3,281 (稼働上位 ~22 entry_type が N≥30) — 本文の N=2,466 は dedup 後系の値とみられ集計キー未照合 (raw/dedup いずれでも「飽和・一様に負」の結論は不変)。T4 着手時に dedup キーを [[t8-week1-gate-breach-2026-07-06]] forensic #3 の estimand 定義と揃えて確定させること
- **shadow 戦略集計で正 EV は 3 本のみ**: vix_carry_unwind (+0.96, N=60) / sr_fib_confluence (+1.44, N=49) / vol_spike_mr (+1.31, N=31) — いずれも T4 摩擦調整 EV マップの最優先評価対象 (M6 母集団の初期候補)
