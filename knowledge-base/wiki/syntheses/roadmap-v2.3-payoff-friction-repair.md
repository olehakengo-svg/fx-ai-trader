# ロードマップ v2.3: 決済非対称と摩擦の是正 — 負エッジ確定局面からの構造回復

> **✅ 正式版 (user 承認 2026-07-07「進めていいよ」)。** autopilot は R2/R3 項目を実行可。**R1 項目は個別に Rule 1 手続き (365d BT + Bonferroni + Pre-reg LOCK + user 最終承認) を経て執行** — ロードマップ正式化は計画の承認であり、個別 R1 レバーの包括承認ではない。目標 (月利21.6% 数学的上限への段階接近、user 承認 2026-06-12) は不変。

**作成日**: 2026-07-06 (handoff タスク `fx-roadmap-v23-handoff` タスク2) / **正式化**: 2026-07-07 (T3 診断確定の訂正込み)
**旧版**: [[roadmap-v2.2-win-conversion]] (2026-06-12、全12項目クローズ済み PR #44-#50)
**根拠**: 2026-07-06 本番実測 (Render production API、clean live `oanda_trade_id != ''` N=92 / clean shadow N=2,466 / risk dashboard / OANDA status) + **2026-07-07 T3 要因分解 [[payoff-asymmetry-diagnosis-2026-07-07]] (敵対的検証済)**

---

## v2.2 からの前提変更 (なぜ v2.3 が必要か)

v2.2 は全12項目をクローズした (止血セル停止・T5 JPYキャップ執行・T8 forensic・T10/T11 KILL・pre-reg 監視自動化・autopilot 稼働)。しかし **30d clean live は改善せず悪化**した。以下は 2026-07-06 実測 (全12,290件取得、30d 窓 = 06-06〜07-06、XAU除外・dedup除外):

1. **clean live 30d = N=92 / −242.6 pip / WR 55.4% / EV −2.64/t** — v2.2 起点 (N=84 / −37.9p) から **6.4×悪化**。W23 以降 (6月後半) に再悪化、W20-21 の一時プラス転換は持続せず。
2. **負けの真因が特定変更された = 決済非対称 (payoff 0.27) + 摩擦** — ⚠️ **2026-07-07 T3 診断で以下のとおり訂正・精密化** ([[payoff-asymmetry-diagnosis-2026-07-07]]):
   - avg_win **+2.40p** / avg_loss **−8.75p** → **payoff ratio 0.274**。恒等式 **0.274 = 設計 R:R 2.667 × 勝ち側 capture 0.0944 ÷ 負け側 realize 0.9185** — 非対称は設計でなく **100% 勝ち側 exit 執行**で発生。①設計 TP (25.4p) が実走 MFE (5.2p) の約5倍 = TP 到達 3/93 ②trail/BE 返上 142.5p/30d。**「負けを引っ張る」は棄却** (loss realize 0.92 = 設計比むしろ改善方向)。
   - 摩擦: draft 当初の **366.2p は dashboard 合成値で実測比 3.06 倍過大**。実測 friction ∈ **[120.6 (実測フロア), 294.6 (per-pair 理論)] p/30d**、gross の符号反転はモデル依存 (フロアでは gross も −124.4p)。**摩擦非対称 (「負けだけ滑る」) は棄却** (17.7p = net 損失の 7%)。ただし対称摩擦の水準効果は大 (スクラッチ勝ち med +1.8p ≈ spread 1.30p)。
   - **どの entry_type も「摩擦調整後 EV が正」にならない限り live 転送に耐えない**、の定量的結論は全摩擦モデルで不変。exit 微調整では黒字化不能 (両レバー完璧でも −77.6p) — 修理は「TP/SL を実走距離 (MFE 帯 4-6p) に整合させる」か「20p 走るシグナルへ張り替える」かの構造選択 (→ WS-Diag T2 の pre-reg)。
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
| T1 | **GBP_USD live 出血セルの forensic + R2 demote** | R2 | ✅ **執行済 2026-07-07 (PR #56)**: wick_imbalance_reversion×GBP_USD を `_PAIR_DEMOTED` へ (N=12 EV−3.91 −46.9p、Wilson_lo 19.3%<BEV 37.9%、pin 3 tests)。**vix_carry_unwind×USD_JPY×SELL (N=10 EV−1.90) は R2 基準該当だが user 承認済み Overlap pilot 契約と衝突 → pilot 継続裁定 (2026-07-07 user「進めていいよ」)** — 再評価 checkpoint = live N≥20 or 2026-08-31 (registry `vix-sell-pilot-recheck`)。trendline_sweep は WR 68.4% BT 整合 / payoff 0.15 → demote 保留・MTF ゲート異常の別調査へ ([[payoff-asymmetry-diagnosis-2026-07-07]] §7) | 完了 (forensic 継続分は T-MTF) |
| T2 | **live 決済非対称の是正 — TP/SL 実走距離整合の R1 パイプライン** — pre-reg LOCK: [[exit-repair-tp-sl-prereg-2026-07-07]] (grid 9 combos、BE/Trail ablation、診断窓除外、BH-FDR q=0.10) | R1 | ❌ **FAIL クローズ 2026-07-08 (H0 採択、期日 07-21 の 13 日前倒し)** — 全 9 構成 p=1.0 / WF 0/3 / EV 負 (最良 tp0.4×sl0.6 で −2.96 p/t、baseline −6.64 から +3.67 改善もレバー不足)。ナイフエッジ3点検査済 (メカニズムは診断通り作動 = 構造的 FAIL)。感度 run (pre-#58 code) も同結論。詳細 = pre-reg §8 verdict | **FAIL 確定 → §4 規定分岐により WS3 シグナル張り替えへ全振り (下記 WS3 改訂)** |
| T-MTF | **(新規) MTF 抑制タグ付き live 発注の構造調査** — trendline_sweep 大負け4発が「4H+1D 不一致→抑制中」タグ付きで OANDA 発注。MTF ゲートの LIVE 転送 block 可否を engine 側で特定 | R3 | 🔄 調査中 (別セッション、spawn_task 2026-07-07) | バイパス確定なら R3 構造 fix |

## WS-Diag: 決済非対称の構造診断 (Rule 3 診断 → Rule 1 実装、v2.3 中核)

payoff 0.27 は v2.3 の最重要問題。**診断は R3 (analyses/ に数値根拠を文書化)、TP/SL 等のパラメータ変更は R1 (365d BT/Live N≥30 + Bonferroni + pre-reg LOCK)。カーブフィッティング禁止 — TV Pine を eval canon とし (MEMORY `feedback_tv_edge_discovery_loop`)、Python BT の payoff/WR は BE/Trail 水増し (MEMORY `project_be_trail_inflates_python_bt_wr`) を必ず ablation してから読む。**

| # | 項目 | Rule | 状態 |
|---|---|---|---|
| T3 | **payoff 0.27 の要因分解** | R3 (診断) | ✅ **CLOSED 2026-07-07** — [[payoff-asymmetry-diagnosis-2026-07-07]] (9-agent workflow、4サブ分析敵対的検証済)。(a) 早利確 = 主因 (log share 103.7%、2層: TP 5倍過大 + trail 返上 142.5p) / (b) SL 遠置き・負け引っ張り = **棄却** / (c) slippage 非対称 = **棄却** (7%) / (d) close_reason = (a) の機構的実体。WR 54.8% は BE/trail アーティファクト (BT +20pp 水増しの live 鏡像)。counterfactual: 両レバー完璧でも −77.6p |
| T4 | **摩擦調整 EV マップ** ✅ **完了 2026-07-07** ([[friction-adjusted-ev-map-2026-07-07]]) — 稼働 39 entry_type × pair × dir を gross EV − per-pair friction で網羅。estimand = deduped (bar_ts key、再emit inflation ~19% 除去、「3,281 vs 2,466」= 診断窓 slice と確定)。**結果: net+ は 1/39 type・3/89 cell のみ (楽観 shadow ですら)。唯一の net+ = vix_carry_unwind×USD_JPY×SELL は live 負 (−1.22〜−1.90p) — BE/Trail 水増しで shadow net+ は live に伝わらない。** draft の「shadow 正EV 3本」は小N/窓依存で、全母集団 deduped では sr_fib_confluence が深赤 (−3.00, N=411) に訂正。現行母集団に live viable な正セル不在を確定 | R3 | ✅ 完了 |

## WS2: 昇格候補 N蓄積・繰越 (v2.2 繰越, Rule 1 正順)

| # | 項目 | 統計条件 | 状態 |
|---|---|---|---|
| T5 | **orb_trap GBP_USD SELL (E9) N蓄積** (v2.2 T6 繰越) | clean N≥30 → H1 ∧ WF 3-fold ∧ Bonferroni(m=116) 再評価。N 以外通過済 (WR.783/PF13.6/Wilson.581/Kelly.725) | E9 継続稼働。触らない |
| T6 | **sweep_reversion_eurgbp_late (EUR_GBP) DEFER 決定点** (v2.2 T8 繰越) | HTF-rescued shadow N≥10 → EV 判定 (R1) / 2026-09-30 に N<5 → retire (R2)。**復帰の追加前提 = order 層 12-bar min-spacing 実装** (検証 estimand との一致、[[t8-week1-gate-breach-2026-07-06]] forensic #3) | pre-reg 監視済 (registry `t8-sweep-defer-decision`)。触らない |
| T7 | **hull_donchian_fade (EUR_USD) ゲート① 再評価** (v2.2 T8 繰越) | shadow 実測 1.5/週 vs 期待 13.3/週 = 下側割れ見込み。頻度 band 割れ確定なら sweep と同じ retire 経路。ゲート④(改) は 2026-07-06 発効済み ([[t8-week1-gate-breach-2026-07-06]]) | pre-reg 監視済 (registry `t8-hull-shadow-freq`) |
| T8 | **carry dip v3 dormant 監視** (v2.2 T7 繰越) | ceiling 159.50 レジーム前提崩壊の dormant-by-design。復帰 = D1 close<159.50 (registry `t5-jpy-cap-restore-price` に相乗り) | 監視のみ。QUALBAR telemetry 本番稼働済 |
| T9 | **kalman_d7 発火監視** (v2.2 T9 繰越) | 3 variant 合算 vs BT 期待 3.9/週。分子ゼロ継続なら Render ログ QUALBAR (分母) と突合 | pre-reg 監視済 (registry `t9-kalman-d7-fire-info`) |

## WS3: シグナル張り替え — v2.3 の主戦線 (2026-07-08 T2 FAIL により全振り確定、司令塔直轄)

**T2 exit-repair FAIL (pre-reg §8) により、pre-reg §4 の固定分岐が発動: 「5p しか走らない場所で exit を直す」経路は棄却され、「20p 走る場所へ entry を張り替える」ことが黒字化の唯一の経路。** T4 マップ ([[friction-adjusted-ev-map-2026-07-07]]) も現行母集団に live viable な正セル不在を確定済みで、両輪の結論が一致。

WS3 の設計原則 (**2026-07-08 MFE 分布診断 [[ws3-mfe-distribution-2026-07-08]] で改訂**):
- **選抜基準 = 「MFE/MAE 方向性非対称 + horizon 持続性」** — MFE 絶対量は豊富 (h24 で p50 15-30p、live 診断の「5p」は exit 打ち切りアーティファクトと確定) だが、母集団の MFE/MAE 比は中央値 0.88 = 方向性なし。**希少資源は非対称 (ratio≥1.3 は 7/79 cells のみ)** であり、「20p 走る場所」でなく「シグナル方向に偏って走る場所」を探す
- 候補テール (探索標本由来、promote 禁止・次期 pre-reg の検証対象): 減衰型 = htf_false_breakout×EUR_JPY (1.81) / trendline_sweep×EUR_USD (1.65) / dt_sr_channel×EUR_USD (1.55) 等、**持続型 (h96 で増幅) = lin_reg_channel×EUR_USD (1.38→1.94) / dt_fib_reversal×USD_JPY (1.29→2.05)**。保有設計は2型で逆
- 手続き: 次の R1 pre-reg で (a) TV Pine canon 再現 (b) 診断窓と重ならない期間の OOS ratio 再計測 (c) 多重性補正 (d) barrier 設計 — カーブフィッティング禁止・falsified 6系統の再試行禁止は不変。dt_sr_channel×EUR_JPY (grid 近接セル) は ratio 1.13 で単独候補としては弱いと判定材料更新

Edge Factor Audit #1-#6 (2026-06-12) + T10 bb_rsi KILL (2026-07-02) で高N shadow 戦略は一巡。**次候補は N 単純降順でなく「高WR × 負EV」群を優先** — エントリーは効いているが決済/摩擦で殺されている典型。falsified 済みシリーズ (H4 level / channel / sweep&reclaim horizontal / mtf SELL / bb_rsi / T11 counter-USD) の再試行禁止。

| # | 候補 | clean shadow 実測 | 分析主眼 | Rule |
|---|---|---|---|---|
| T10 | **gbp_deep_pullback** | WR 72% / EV −1.39 | 高WR×負EV の筆頭。pullback エントリーのエッジ有無を IC で分離し、payoff/摩擦 kill か entry 劣化か判定 | R1 (促進時) / R3 (診断) |
| T11 | **sr_anti_hunt_bounce** | WR 63% / EV −4.49 | SR family の唯一の survivor (anti-hunt thesis、他 SR は audit KILL 済)。EV −4.49 は payoff/摩擦か、それとも thesis 劣化か。斜めTL固有の liquidity-hunt エッジ (MEMORY `project_sweep_reclaim_horizontal_falsified`) との整合確認 | R1 / R3 |
| — | (flag) **trendline_sweep 乖離** | live/shadow WR 63% / EV −1.60 vs BT EV +0.599〜+0.927 | ELITE_LIVE 唯一戦略の live 実測が BT を大きく下回る。WS1 T1 と統合して forensic | — |

## WS4: clean-N 整合性・品質ゲート (Fable5 監査 Phase B, R3 構造fix)

**clean N 蓄積が最優先 → その N を汚染/死にゲートから守るのが最も寄与度が高い。** 以下は全て診断済み構造バグ (R3、365d BT 不要)。autopilot 実行可。詳細: [[fable5-system-audit-2026-07-02]]。

| # | 項目 | Rule | 寄与 |
|---|---|---|---|
| T12 | **P1-3: stale SHADOW_MIGRATION ブロック削除** ✅ **完了 2026-07-07 (PR #59)** — `demo_db.py` restart 毎の現役セル (dt_bb_rsi_mr, bb_squeeze_breakout) 再汚染を削除。後継 backfill + FLAG_DRIFT (UNSAFE 検知) が正しい後継。回帰テスト同梱 | R3 | ✅ 完了 |
| T13 | **P1-9: 死にゲート `_kelly_block` 修正** ✅ **完了 2026-07-07 (PR #59)** — `_get_strategy_kelly_clean(raw=True)` 追加で負値判定 2 経路が発火。実弾サイジングは clip 維持で不変。回帰テスト同梱 | R3 | ✅ 完了 |
| T14 | **P1-2/2b: BE/Trail ablation を scalp/1H×2 へ展開 + fut_close tie-break** ✅ **完了 2026-07-09 (branch fix/t14-be-trail-ablation-all-engines)** — ablation default (TV-aligned OFF、`BT_OPTIMISTIC=1` で復元) を `run_backtest`/`run_scalp_backtest`/`run_1h_backtest` へ展開 + cache key 反映。fut_close tie-break は検証の結果 4 エンジン既装 (swing は保守的 SL 優先) — 回帰テストで pin。⚠️ 3 エンジンの旧 BT 結果 JSON は非互換 (再計測要)。回帰テスト同梱 | R3 | ✅ 完了 |
| T15 | **P1-7/P1-8/P1-6 (低優先)** — CI paths filter 撤廃 + hip1 job 化 + dev.agent.yaml 訂正 / scalp QUALIFIED_TYPES drift 検査 / 再送ガード共通化 | R3 | 品質ゲート穴。順次 |

## 棄却・据置 (このロードマップで追わない)

- **blanket live pause** — 原則1 (攻める) に反する。止血は WS1 の細粒度停止で行う
- **falsified 済みシリーズの再試行** — H4 level / channel / sweep&reclaim horizontal / mtf SELL / bb_rsi / T11 counter-USD (MEMORY 参照)
- **shadow 発火の停止** — 原則3 (Shadow は UTC 固定で削らない)。N 飽和でも Bonferroni power のため継続
- **multi-bar cooldown の order 層実装** — sweep (T6) 復帰時のみ必要。現状 code pin OFF のため保留
- **P2/P3 群** (Fable5) — 衛生項目。WS4 の後、寄与度順に

## ボトルネック (v2.2 から更新提案)

**v2.2 の「クリーン N の蓄積速度」は superseded (2026-07-07 正式化で確定)。** shadow N は飽和 (20 entry_type 全 N≥30) し、律速ではなくなった。**v2.3 の真のボトルネック = 「正の摩擦調整 EV を持つセルの不在」** — 蓄積したデータが一様に負を示し (payoff 0.27、主因 = 勝ち側 exit 執行の崩壊 + 対称摩擦 [120.6, 294.6]p の水準効果)、昇格母集団が存在しない。

したがって寄与度の優先順位 (**2026-07-08 T2 verdict 後の現在地**):
1. **WS3 シグナル張り替え** — v2.3 の主戦線に昇格 (T2 FAIL の §4 固定分岐)。MFE 分布ベースの R3 診断から開始 (WS3 節の設計原則参照)
2. **clean-N 整合性の回復** (WS4 = Fable5 Phase B) — **P1-3/P1-9 ✅ 完了 (PR #59, 2026-07-07)**。残 = P1-2 (BE/Trail ablation を scalp/1H×2 へ展開)。R3
3. ~~決済非対称の是正 (WS-Diag T2)~~ — ❌ **FAIL クローズ 2026-07-08** (pre-reg §8。exit 側レバーは仮説空間ごと閉鎖 — 再試行禁止)
4. ~~摩擦調整 EV マップ (WS-Diag T4)~~ — ✅ 完了 (2026-07-07)。net+ セル不在を確定

**正式版 (2026-07-07 / T2 verdict 反映 2026-07-08)。** autopilot は R2/R3 項目を実行可。R1 項目は個別に Rule 1 手続き + user 最終承認。

---

## 検証ログ (2026-07-07 独立再計測)

commit 前に別セッションが production API から新規スナップショット (12,325 行、`tools/render_trades_snapshot.py`) を取得し再導出:

- **clean live 30d (06-06〜07-06)**: N=92 / −242.6p / WR 55.4% / EV −2.64 / avg_win +2.40 / avg_loss −8.90 (payoff 0.27) — **本 draft の中核数値を完全再現** ✅
- **shadow 30d raw**: N=3,281 (稼働上位 ~22 entry_type が N≥30)。**estimand 確定 (T4, 2026-07-07)**: 「3,281 vs 2,466」= 診断窓 shadow の再emit inflation (~19%)。dedup key = `(entry_type, instrument, direction, bar_ts)` ([[t8-week1-gate-breach-2026-07-06]] forensic #3 の order 層 estimand と整合) で診断窓 3,332→2,686。全母集団 (all post-cutoff) は 10,648→8,667 (−18.6%)。raw/dedup いずれでも「飽和・一様に負」の結論は不変
- **~~shadow 正 EV 3 本~~ → 訂正 (T4, [[friction-adjusted-ev-map-2026-07-07]])**: draft の 3 本 (vix_carry/sr_fib/vol_spike) は小N/窓依存。全母集団 deduped + friction 控除では **net+ は vix_carry_unwind のみ (1/39)**、sr_fib_confluence は −3.00 (N=411) と深赤に反転。しかも vix_carry の net+ は **shadow 限定で live は負** (BE/Trail 水増し) — live viable な正セルは母集団に不在
