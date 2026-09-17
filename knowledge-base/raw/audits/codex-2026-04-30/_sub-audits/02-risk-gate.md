# Sub 02: リスク / ゲート / 統計層

## Scope
`modules/prime_gate.py`, `modules/spread_gate.py`, `modules/friction_model_v2.py`, `modules/regime_classifier.py`, `modules/hmm_regime.py`, `modules/confidence_v2.py`, `modules/confidence_q4_gate.py`, `modules/risk_analytics.py`, `modules/cell_routing.py`, `modules/bev_table.py`, `modules/strategy_category.py`, `modules/vpin.py`, `modules/htf_data_source.py`, `modules/stats_utils.py`

補助確認のみ: `modules/demo_trader.py`, `app.py`, `knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv`

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev2 | `modules/hmm_regime.py:236` | Baum-Welch の遷移行列更新が数式的に誤っており、`A` 推定が歪む。`log_xi` 正規化に `P(O)` ではなく `alpha[:-1,i]+beta[:-1,i]` の時系列和を使っているため、状態遷移確率が正しい EM 更新になっていない。 | `xi_t(i,j)` の分母実装ミス。`modules/hmm_regime.py:241-247` が Bailey/Hamilton 系の標準更新式から外れている。 | `xi_t` を各 `t` ごとに `alpha_t(i)+logA_ij+logB_{t+1,j}+beta_{t+1,j}-log_ll` で計算し、`A[i,j]=sum_t xi_t(i,j)/sum_t gamma_t(i)` に置換。修正まで HMM を heuristic-only に落とすのが安全。 |
| 2 | Sev2 | `modules/risk_analytics.py:459` | Gate 3/4 の DSR 判定が不信頼。`compute_risk_dashboard()` は per-trade `mean/std` をそのまま Sharpe として `deflated_sharpe_ratio()` に渡すが、DSR 側 doc は annualized Sharpe 前提。しきい値 `DSR>0.80/0.95` と比較不能。さらに `haircut` も `modules/stats_utils.py:498-501` で意味が反転している。 | Sharpe のスケール定義が統一されていない。DSR 実装と呼び出し側の契約不一致。 | Sharpe 定義を「trade-based」か「daily annualized」に一本化し、DSR doc/threshold も同じ単位に合わせる。`haircut` は `threshold>=observed` なら 100% luck 扱いに修正。 |
| 3 | Sev2 | `modules/spread_gate.py:85` | Layer 0 が「quoted spread 異常」を見る設計なのに、実際は live quote ではなく `friction_for()` の静的テーブル値だけを見ている。異常 widening を検知できず、live friction と一致しない。 | `spread_gate` が `modules/friction_model_v2.py:197-204` の固定 `spread_pips` を quoted spread と誤用している。 | 実際の entry quote/BBO か直近 bar の spread series を入力に含め、`friction_for()` は baseline として別扱いに分離。 |
| 4 | Sev2 | `modules/bev_table.py:23` | BEV が三重定義で不整合。`bev_table` は `USDJPY daytrade=0.38 / scalp=0.44`、一方 `friction_model_v2` は `USD_JPY bev_wr=0.344` を返す (`modules/friction_model_v2.py:29`)。Wilson/BEV ゲート判定が呼び出し箇所で変わりうる。 | BEV の単一ソースがなく、pair-only と pair×mode が混在。 | BEV を 1 つの helper に集約し、pair×mode×RR 前提を明示。既存呼び出しは全てその helper 経由に統一。 |
| 5 | Sev2 | `modules/cell_routing.py:78` | cell routing は実質無効。runtime key は `"{regime}__{vol}__{session}"` 前提だが、呼び出し側は `modules/demo_trader.py:6290` で `None` を返す stub、かつ `routing_table.json` は `edges_count: 0`。さらに監査 CSV は `entry_type,instrument,session` 粒度のみで cell 定義も不一致。 | runtime cell producer 未実装 + manifest 空 + 集計粒度不整合。 | `cell3d` 生成を実装し、`06a-cell-stats.csv:1` も `entry_type × pair × session × regime` に再生成。未実装の間は Gate 判断に使わないと明記。 |

## 2. Structural Issues
1. ゲート直列順は要求どおりではない。実配線は `SCORE_GATE` が先行し (`modules/demo_trader.py:2904`)、その後に `PRIME` (`modules/demo_trader.py:4304`) と `Q4` (`modules/demo_trader.py:4518`) が来る。`spread_gate` と `regime_classifier` は call site がなく、`prime -> spread -> q4 -> regime` の AND 連鎖は未成立。
2. `PRIME` と `Q4` の衝突自体は確認できなかった。`Q4` は `_is_shadow=True` を立て (`modules/demo_trader.py:4518-4523`)、その後の PRIME override は `not _is_shadow` 条件付き (`modules/demo_trader.py:4532`) なので、Q4 が優先される。
3. HMM の未来リークは現行 predict 経路では見当たらない。`predict_proba()` は与えられた returns の forward filter のみを使い (`modules/hmm_regime.py:298-324`)、HTF 側も `complete=False` を drop している (`modules/htf_data_source.py:99-101`)。ただし fit は同一 120d 窓を丸ごと使うため、研究用途では walk-forward 再学習にしない限り in-sample 汚染が残る (`modules/demo_trader.py:642-668`)。
4. `htf_data_source` の M15 features はリークしていない。`ema_slope`, `range_20`, `hurst_64`, `atr15` はいずれも最後の完了バー以前のみで計算されている (`modules/htf_data_source.py:281-317`)。
5. `vpin.py` は live で一度も発火しない。呼び出し箇所が無く、さらに `scipy.stats.norm` 依存が追加されている (`modules/vpin.py:36`)。現状の発火頻度は 0。
6. `app.py` の Wilson 実装は標準式で妥当 (`app.py:9517`)。問題は式そのものより、Wilson/BEV/ Kelly が複数箇所に分散している統治不全。

## 3. Losing Edge Analysis
該当あり。コード上の主因は `friction` 過小/別定義、`DSR` 尺度不整合、`Layer 0/1/cell` 未配線。特に scalp 側は `spread_gate` が live spread を見ていないため、摩擦起因の負 edge を防げていない。

## 4. Roadmap Alignment
- Gate 進行を阻害している主因は、`DSR` と `BEV/Wilson` の判定基準が一貫していないこと、そして Layer 0/1/cell の実装が runtime で効いていないこと。
- 律速はこのスコープでは `Kelly/DSR/Wilson` の信頼性不足。DD そのものより「ゲート判定の数値定義」が崩れている。
- 加速策は 1) BEV/Wilson/DSR の単一実装化、2) spread/regime/cell の配線完了、3) HMM EM 修正または一時停止。これをやらない限り Gate 2-4 の通過判定は監査不能。

## 5. Top 3 Action Items
1. DSR と Sharpe の単位系を統一し Gate 3/4 を再定義する — Impact: roadmap 判定の信頼性回復 — Confidence: high
2. `spread_gate` を live quote 入力付きで本番配線し、`regime_classifier` も Layer 1 に実接続する — Impact: scalp の摩擦起因損失を直接削減 — Confidence: high
3. HMM の遷移更新式を修正するか、修正まで heuristic fallback に固定する — Impact: regime overlay の誤判定削減 — Confidence: med

## 6. Out-of-Scope Findings
- `modules/demo_trader.py:3457-3544` に静的時間/ペア block がまだ多数残っており、CLAUDE.md の「静的時間ブロック禁止」と整合していない。
- `modules/demo_trader.py:6270-6284` は `cell_routing` を fail-open で飲み込むため、将来 manifest を入れても silent no-op になりやすい。
