# 作戦立案ガードレール（Strategy Planner 注入用）

> このファイルは `scripts/daily_report.py` の `run_strategy_planner` が毎回プロンプトに注入する。
> 目的: 日次レポート生成器が「過去に何十回出して実行しなかった案／実測で棄却済みの案」を
> 記憶なく再生産するループを断ち切る。**編集はコード変更不要** — ここを直せば翌レポートに反映される。
> 監査根拠: `wiki/audit-index.md` ↔ Claude MEMORY `project_*` / `feedback_*`。
> 最終更新: 2026-06-08（8週間・40 pre_tokyo・約118提案の俯瞰レビューに基づく）

---

## A. 実測で棄却済みのパターン（再提案しないこと）

以下は過去に繰り返し提案され、実測またはKBで棄却済み。**同型の案を出す場合は「なぜ過去の棄却が今回当てはまらないか」を1文で明示**できない限り提案禁止。

1. **MR戦略にレジーム/トレンド/レンジフィルタを追加する**（過去 ~14回提案）
   - 実証: bb_rsi系MRにH1 EMA200整合フィルタ → **LIVE edgeがBTで消滅（Kelly 0.43→0）**（`feedback_ma_filter_breaks_mr`）
   - 実証: HMM regime gateでconventional rule適用 → **edge消滅（USDJPY +478p→-4p）**（`feedback_hmm_gate_same_trap`）
   - 教訓: フィルタはentry timingをずらしcompoundingを壊す。loser zone対処は **SKIPでなくSIZE lever（lot半減）** が正（`feedback_size_lever_beats_skip_filter`、ZZ v60で PF+5.9%/WF3/3 実証）

2. **session_time_bias の延命/再設計/TP-SLリバランス**（過去 ~13回提案）
   - 実測: E2/E4/E8（session_time_bias系）が直近7d fillsの87%・純損失の110%を占め、**2026-06-04にCB発動でstage=0 disable済み**（`project_oanda_loss_surge_2026_06_03`）
   - ΔWR +54.2pp（BT87.5% vs Live33.3%）は典型的BTオーバーフィット署名。**BT WRに合わせ直す再設計はshadow-first違反**（`feedback_shadow_first_quant_architecture`）
   - 答えは凍結/降格。延命提案は出さない。

3. **GBP_JPYブレイクアウト/モメンタム新規戦略**（過去 ~12回提案、実行ゼロ）
   - 全ペアRANGING下でBreakout/Momentumは構造的に不利（レポート自身が毎回明記）
   - W4-EDA: breakout/momentum系の **91%が「思想は正、設計が誤」**（`project_w4_eda_complete_2026_05_05`）
   - 提案するなら新規でなく「TRENDING遷移トリガー（ATR%ile≥60 持続）でwatchlist昇格」の1行に留める。

4. **GO基準が WR/EV/N のみ（部分クオンツの罠）**
   - WR≥55%等の緩い基準は Wilson下限/Bonferroni/WF で落ちる戦略を素通しさせる（`feedback_partial_quant_trap`）
   - 実測: orb_trapは Wilson.581/Bonf.420/Kelly.725/WF3-3 を満たして **N<30だけで保留**（`project_tp_hit_12cell_portfolio_2026_06_05`）
   - **GO基準には必ず Wilson_lo / Bonferroni(m=活戦略数) / WF≥3fold / Kelly を含める。**

---

## B. 既存shadow在庫（新規発明より先に消化すべきエッジ）

新しいMR/reversal戦略を「発明」する前に、以下の検証済み在庫の消化を優先提案すること。

- **price_shock reversion**: 227 SHADOW_CANDIDATE発見済み、EUR_GBP H1 WR72%/Wilson0.66、AUDJPY H4でQiita完全再現（`project_price_shock_reproduction_success_2026_05_15`）。新規MR発明はこれに劣後。
- **TP-HIT 12-cell portfolio**: orb_trap|GBP_USD|SELL が WR.783/PF13.6 で N≥30 待ち（`project_tp_hit_12cell_portfolio_2026_06_05`）。shadow継続が正順。
- **CAD-1 Channel Auto-Discovery**: 水平チャネル自動発掘パイプライン（`project_cad1_2026_05_05`）。"channel boundary reversal"系の新規案はこれと重複。

---

## C. インフラ/データ品質が未解決の間は戦略提案より配管修復を優先

「シグナルがOANDAに届かない／N蓄積が汚染されている」構造問題が未解決の場合、**新戦略・再設計より配管修復を高優先で提案**すること。実測の既知バグ:

- `same_price_0pip`（daytrade_eur で 200件超/日）= データフィード重複バグ
- `shadow_tracking` skip / alpha_snapshot 100%空 / pyarrow欠損でconfluence engine ImportError（`project_sr_anti_hunt_demo_trades_meta_loss_2026_06_03`）
- `/api/oanda/stats` range無視（today/7d/30d 全て同値固定）（`project_oanda_stats_range_ignored_2026_05_18`）

> 累計サンプル（N=8等）自体がこれら配管バグの産物。**汚染データ上の戦略提案は評価不能**であることを明記する。
