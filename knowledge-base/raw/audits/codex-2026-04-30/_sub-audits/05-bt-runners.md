# Sub 5: BT ランナー正当性監査

## Scope
ルート直下の `_bt_*.py` を全件確認。実際に検出された対象は 23 本でした。
重点監査:
`_bt_regime_cascade_scalp_vec.py`, `_bt_regime_cascade_scalp.py`, `_bt_mtf_cascade_scalp_vec.py`, `_bt_mtf_cascade_scalp.py`, `_bt_v595_audit.py`, `_bt_v70_dt_eur_gbp.py`, `_bt_v70_dt_jpy.py`, `_bt_v70_eur.py`, `_bt_v70_jpy.py`, `_bt_baseline_comparison.py`, `_bt_multipair_bbrsi.py`, `_bt_h004_h005.py`, `_bt_h004_h005_stf.py`, `_bt_h004_relax_h005_jpy.py`, `_bt_threshold_proximity.py`, `_bt_dt_hourly.py`, `_bt_hourly_analysis.py`, `_bt_hourly_eur.py`, `_bt_eurjpy_filtered.py`, `_bt_profile_runner.py`, `_bt_all_strategies_sanity.py`, `_bt_1h_dmb.py`, `_bt_1h_ksb.py`

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `_bt_multipair_bbrsi.py:441-459` | `MAX_HOLD` 到達時は `_last_close` で WIN/LOSS だけ判定しているのに、PnL は常に `tp_dist` / `sl_dist` 全額で計上。EXPIRED 相当の部分利確/部分損失が full TP/SL に化ける。 | exit price を保持せず、binary outcome の後で固定距離を当てている。 | timeout/BE/trailing は `exit_px` を記録し、`(exit_px - ep) * pip_mult` で計上。 |
| 2 | Sev1 | `_bt_eurjpy_filtered.py:282-298` | 同型。時間切れを `_last_close` で判定するが、PnL は full `tp_dist` / `sl_dist`。non-TP/SL exit の損益が歪む。 | outcome と PnL の経路が分離。 | row 1 と同じ修正。 |
| 3 | Sev1 | `_bt_1h_dmb.py:254-277` | BE/Trailing で `_current_sl` 益出し終了した trade でも、`outcome=="WIN"` なら full `tp_dist` を計上。timeout でも full TP/SL 計上。 | 実際の exit level を無視して binary outcome だけで pips を決めている。 | `_exit_pnl` / `_last_close` をそのまま pips 換算し、`tp_dist` を使わない。 |
| 4 | Sev1 | `_bt_1h_ksb.py:263-289` | row 3 と同型。BE/Trailing/timeout が full TP/SL に丸められる。 | 同上。 | 同上。 |
| 5 | Sev2 | `_bt_v595_audit.py:406-434` | `expected_value` を pair/TF/mode を跨いでそのまま加重平均し `portfolio_ev_avg` を作っている。1ATR の意味が scalp 5m / DT 15m / 1H で異なるため、ポートフォリオ EV が単位汚染される。 | 異種 ATR 単位を同一次元として集約。 | 先に pips か currency に正規化してから集約。 |
| 6 | Sev2 | `_bt_v595_audit.py:626-650` | 最終承認ロジックが roadmap Gate 条件ではなく、`portfolio_ev_avg > 0.1` と `monthly_pips > 500` など独自閾値で PASS/FAIL を出す。Gate 3/4 の PF, N, 破産確率, DSR を見ていない。 | 監査スクリプト内の簡略 gate が roadmap と乖離。 | roadmap-v2.1 の Gate 1-4 条件に揃える。 |
| 7 | Sev2 | `_bt_all_strategies_sanity.py:9-14`, `_bt_all_strategies_sanity.py:83-88`, `_bt_all_strategies_sanity.py:137-152` | script 自身が「friction/gates なし」「raw edge」と明記しているのに、Wilson/BEV pass 数を出すため、live-equivalent と誤読すると optimistic contamination を起こす。 | production-parity を持たない harness を pass/fail 風に見せている。 | 出力に `NOT LIVE-EQUIVALENT` を強制付与し、pass 判定を削除するか別名に分離。 |
| 8 | Sev2 | `_bt_hourly_analysis.py:59-84`, `_bt_v70_eur.py:148-169`, `_bt_v70_dt_jpy.py:51-69` | pips 集計が近似/再構成ベースで、固定 ATR や `tp_m`/`sl_m` を使っており、actual exit friction・signal_reverse・partial exits を反映しない。時間帯/戦略比較を誤誘導しうる。 | analysis script が execution path を再計算している。 | `trade_log` の実測価格差または app 側の確定 PnL をそのまま使う。 |
| 9 | Sev3 | `_bt_v595_audit.py:686-687`, `_bt_h004_h005.py:248-249`, `_bt_h004_h005_stf.py:100-101`, `_bt_h004_relax_h005_jpy.py:104-105`, `_bt_baseline_comparison.py:73-77` | 出力ファイル名が固定で、並列実行時に結果を上書きする。 | timestamp / UUID / lock なし。 | 既定出力を timestamp 化し、`--out` 未指定時でも衝突しないようにする。 |
| 10 | Sev3 | `_bt_profile_runner.py:102-124` | 既定 `.prof` 名は秒粒度。同秒・同引数の 2 プロセス起動、または同じ `--out` 指定で衝突する。 | output path 一意性保証なし。 | PID/uuid を suffix 追加、既存ファイル存在時は fail-fast。 |

## 2. Structural Issues
1. `pip_mult` 横展開チェックは感度 OK。`_bt_regime_cascade_scalp_vec.py` は共通ハーネス依存で、`modules/bt_vec_harness.py:382-403` に「original _bt_regime_cascade_scalp_vec.py bug」と修正済み実装が明記されていた。現行 `_bt_*.py` 側では、既知の「non-JPY EXPIRED 100x 過小」と「`if pip_mult` truthy 分岐」同型は再発していない。
2. bespoke friction が live と乖離。`_bt_eurjpy_filtered.py:29-34`, `_bt_multipair_bbrsi.py:31-160`, `_bt_1h_dmb.py:177-178`, `_bt_1h_ksb.py:183-184`, `_bt_h004_h005.py:214-225` は `friction_model_v2` を呼ばず固定 spread / friction を持つ。BT-Live divergence の温床。
3. vectorized aggregation 順は runner 側では概ね健全。共通 harness は `sort_values("ts")` 後に `merge_asof` しており、順序依存の露骨な `groupby/cumsum` バグは今回のスコープでは未検出。根拠: `modules/bt_vec_harness.py:458-477`。
4. 乱数シード問題は runner 側では未検出。`_bt_*.py` 内に `random` / `np.random` / `seed` 呼び出しは見当たらず、再現性の主要リスクは RNG ではなく「固定でない出力名」「production-parity 不足」「外部データ更新」。
5. `_bt_baseline_comparison.py` の baseline 定義は弱い。`_bt_baseline_comparison.py:30-77` は commit hash / friction model / data cutoff を保存しないため、`before/after` が同条件比較として残らない。
6. v7.0 系の `Promo` 表示は roadmap gate と別物。`_bt_v70_dt_jpy.py:97-108`, `_bt_v70_dt_eur_gbp.py:115-129`, `_bt_v70_jpy.py:102-109`, `_bt_v70_eur.py:474-480` は `promotion_candidate` を表示するが、実体は app 側 `ev > 1.0 and total >= 10` だけ (`app.py:5905-5906`, `app.py:6555-6558`)。roadmap Gate 2-4 の Kelly / PF / N / DSR / ruin とは整合しない。
7. `_bt_profile_runner.py` 自体に data race は見えないが、obs 613 の「2 プロセス並行」前提では output collision だけ未防御。メモリリークを示す runner-local state は見当たらない。

## 3. Losing Edge Analysis
該当時のみ:
- `v595` の aggregate EV 判定は単位汚染のため、負けエッジ分析の前提値として信用できない。
- `_bt_all_strategies_sanity.py` は raw edge 用であり、負け帰属に使うと friction 過小評価バイアスを混入する。

## 4. Roadmap Alignment
- 最大の阻害要因は、`_bt_v595_audit.py` が roadmap Gate ではなく独自承認ロジックを出している点。
- 次点は bespoke friction 群。live が `friction_model_v2` ベースなのに、custom BT が固定 spread を使うため、Kelly/PF/DSR 改善判断を誤る。
- 加速施策は 3 つ。custom runner の exit PnL 算数修正、friction を `friction_model_v2` へ統一、gate 判定を roadmap 条件へ一本化。

## 5. Top 3 Action Items
1. `_bt_multipair_bbrsi.py`, `_bt_eurjpy_filtered.py`, `_bt_1h_dmb.py`, `_bt_1h_ksb.py` の exit PnL を `exit_px` ベースへ修正する。Impact: 誤PnL是正で EV/PF/Kelly の一次汚染を除去。 Confidence: high
2. `_bt_v595_audit.py` の portfolio EV 集約と最終 gate を pips/currency 正規化 + roadmap Gate 1-4 に差し替える。 Impact: 昇格/据置判断の誤判定を防ぐ。 Confidence: high
3. bespoke friction runner を `friction_model_v2` へ寄せる。 Impact: BT-Live 乖離縮小、Scalp 改善施策の評価精度向上。 Confidence: med

## 6. Out-of-Scope Findings
- 既知の `_bt_regime_cascade_scalp_vec.py` `pip_mult` バグ自体は、現時点では共通 harness 側で修正済みと読める。今回の横展開では、同一の truthy/falsy 判定ミスは他 runner に見つからなかった。
- 監査結果は保存していません。現セッションは read-only sandbox です。
