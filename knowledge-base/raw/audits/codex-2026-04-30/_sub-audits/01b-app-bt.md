# Sub 1b: app.py BT 起動・実行パス

## Scope
- `app.py:4611-4914` BT helpers (`_get_dxy_trend_for_bt`, `_bt_classify_session`, `_bt_spread`, `_bt_get_slippage`)
- `app.py:4916-5277` `run_backtest`
- `app.py:5278-5336` `_check_trend_changed_and_clear_bt`
- `app.py:5337-5984` `run_scalp_backtest`
- `app.py:5985-7041` `run_daytrade_backtest` / `run_1h_backtest`
- `app.py:7042-7302` `run_swing_backtest`
- `app.py:10295-10492` `run_strategy_evaluation`
- `app.py:11104-11247` `api_backtest` / `_save_bt_to_kb`
- `app.py:11248-11434` `_evaluate_bt_for_promotion` / `_run_bt_by_mode`
- `app.py:11436-11905` `api_bt_pipeline_batch` / `_run_chunked_scalp_bt` / `api_backtest_long`

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `app.py:11788-11805` | `api_backtest_long` の汎用チャンク BT は各チャンクで `_bt_func(... lookback_days=_cdays)` を呼ぶだけで、期間をずらしていない。120日を30日チャンクで回すと「直近30日」を4回足し込む。古い期間は未評価、最新期間は多重計上される。 | チャンク境界を `from/to` で指定せず、通常 BT 関数の「直近N日」APIをそのまま反復使用している。 | `fetch_ohlcv_range()` 方式で各チャンクの絶対期間を切る。少なくとも `_run_chunked_generic_bt` も `_run_chunked_scalp_bt` と同じ期間指定取得に統一する。 |
| 2 | Sev2 | `app.py:5405-5412`, `app.py:6057-6064`, `app.py:7092-7099` | Scalp/DT/Swing BT は `get_master_bias(symbol)` を 1 回だけ取得し、その“現在の” Layer1 を全ヒストリカル期間へ固定注入している。これは look-ahead contamination。 | `htf_cache["layer1"]` に時点同期ではない live 現在値を入れている。`_compute_bt_htf_bias()` は時点同期だが Layer1 だけ同期していない。 | BT 用 Layer1 をバー時点再構築する。最低でも `_get_dxy_trend_for_bt()` 相当の bar-synchronous proxy に差し替え、現在時点の `get_master_bias()` を BT に持ち込まない。 |
| 3 | Sev2 | `app.py:4804-4882`, `app.py:4785-4801` | BT friction は `friction_model_v2` と同じ前提を使っていない。`_bt_spread()` は `_SESSION_MULTIPLIER` だけを流用し、`friction_for()` の `mode` 補正・`hour_utc` 補正を無視する。さらに `_bt_classify_session()` は live 境界と不一致。 | 実装が `friction_model_v2.friction_for()` に統合されておらず、BT 側で独自 hour bucket を再実装している。`get_session_info()` の UTC 境界 (`app.py:604-630`) ともズレる。 | BT entry/exit friction を `friction_for(pair, mode, session, hour_utc)` ベースへ一本化する。`_bt_classify_session()` の 00-02, 07-09, 17-21 UTC 境界も live と一致させる。 |
| 4 | Sev2 | `app.py:5073-5075`, `app.py:5185-5189` | `run_backtest()` だけ旧式で、エントリー時 half-spread しか引かず、slippage と exit friction を一切計上しない。他の BT runner と比べて系統的に楽観。 | standard BT が v2 friction 統合前の旧ロジックのまま残っている。 | `run_backtest()` も `_bt_get_slippage()` と exit friction を使う。少なくとも round-trip で `spread + 2*slippage` を反映する。 |
| 5 | Sev2 | `app.py:11183-11189` | `_save_bt_to_kb()` は `entry_breakdown` を dict ではなく list 前提で走査しており、通常の BT 結果（dict）で `entry.get(...)` が落ちる。結果、KB 保存がサイレント失敗する。 | `run_*_backtest()` は `entry_breakdown` を dict で返す (`app.py:5258`, `5952`, `6595`, `7018`, `7286`) のに、保存側が型を誤解している。 | `for name, entry in (result.get("entry_breakdown") or {}).items():` に修正し、保存失敗を error-level で残す。 |
| 6 | Sev2 | `app.py:11248-11300` | 昇格判定が roadmap Gate と不整合。評価は `WR>=BEV+5pp`, `EV>0`, `N>=30`, `PF>1.0` のみで、Gate 2-4 の `Kelly`, `PnL>+50pip`, `ruin`, `DSR`, `N>=100/200` を見ない。 | `_evaluate_bt_for_promotion()` が独自の簡略ゲートを持ち、実際の phase gate (`app.py:13729-13732`) と別物になっている。 | 昇格評価を phase gate API と同じメトリクスに寄せる。少なくとも `Kelly`, `ruin_probability`, `DSR`, `PnL(pips)` を必須入力にし、roadmap gate をそのまま判定する。 |
| 7 | Sev2 | `app.py:11596-11733` | `_run_chunked_scalp_bt()` はチャンクを新しい順に `all_trades.extend()` しており、DD/WF が逆時系列で計算される。加えて集計 PnL が `exit_friction_m` を無視し、通常 scalp BT より楽観。 | 時系列ソートなしで集計している上、`_pnl_t()` が base BT の `_sc_pnl()` と別実装。 | `entry_time` で全 trade を昇順ソートしてから DD/WF を計算し、PnL 関数も `exit_friction_m` を含めて base BT と共通化する。 |

## 2. Structural Issues
1. **BT セッション分類が live UTC と一致していない** — `app.py:4785-4801` は `Tokyo=02-07`, `London=07-13`, `NY=13-22`、一方 live `get_session_info()` は `Tokyo=00-09`, `London=08-17`, `NY=13-22`, `Tokyo×London=07-09` (`app.py:604-630`)。特に 00-02, 07-09, 17-21 UTC の friction routing が別物になる。 — session 判定を 1 箇所に集約すべき。  
2. **長期 BT の境界 warm-up 設計が不完全** — scalp は `MIN_BARS=200` (`app.py:5425`, `5447`)・DT は `MIN_BARS=200/100` (`app.py:6076-6078`) を各チャンク先頭で毎回捨てるが、チャンク overlap がないため境界近傍シグナルを恒常的に取りこぼす。 — chunk に warm-up overlap を付け、集計時に overlap 領域だけ dedupe するべき。  
3. **`run_strategy_evaluation()` の baseline は live friction と非整合** — ランダム baseline は `_bt_spread()` の entry half-spread のみで、slippage/exit friction を見ない (`app.py:10339-10343`)。自戦略 BT は friction 込みなのに、比較対象が軽コスト化している。 — baseline も同じ friction accounting に統一すべき。  
4. **Scoped lines 内では pip_mult バグの同型は未検出** — 本スコープの PnL は価格差×`pip_mult` ではなく ATR-multiple (`actual_sl_m`, `tp_m`, `exit_friction_m`) ベースで計算されている (`app.py:5829-5833`, `6503-6508`, `6942-6947`, `7217-7222`, `11818-11827`)。obs 642-643 のベクトル化バグ署名はここには見当たらない。  

## 4. Roadmap Alignment
- 現状の BT パスは **Gate 進行を過大評価** しやすい。特に friction v2 未統合 (`app.py:4804-4882`, `5073-5075`, `5185-5189`) と current-bias 注入 (`app.py:5405-5412`, `6057-6064`, `7092-7099`) は EV/Kelly を水増しし、Gate 1-2 の判定を汚染する。
- 律速要因は `Kelly` と `DSR` 以前に **BT fidelity**。`_evaluate_bt_for_promotion()` が roadmap gate を見ていない (`app.py:11248-11300`) ため、Gate 2 未達でも“PROMOTE to LIVE”が出る。
- 加速施策は 3 点に集約される。
  1. friction を `friction_for()` へ統一
  2. Layer1 を bar-synchronous 化
  3. long/chunk BT の期間 slicing を修正
- これをやらない限り、N を積んでも “間違った BT が速く回る” だけで roadmap の証拠能力が上がらない。

## 5. Top 3 Action Items (impact 順)
1. `api_backtest_long` の generic chunk 実装を期間指定方式へ置換 — Impact: 二重計上/履歴欠落を即解消、長期BTの数値が初めて信頼可能になる — Confidence: high
2. BT friction を `friction_for()` ベースへ統一し、`run_backtest()` を旧式コスト計上から外す — Impact: BT-Live 乖離縮小、Gate/Kelly の誤判定抑制 — Confidence: high
3. `get_master_bias()` の current snapshot 注入を廃止し、BT Layer1 を bar-synchronous proxy に差し替える — Impact: ルックアヘッド汚染を除去、OOS妥当性が大幅改善 — Confidence: high

## 6. Out-of-Scope Findings (オプション)
- live と BT の同一プロセス競合（obs 628）は、実際の修正本体が `app.py:14089-14104` にあり、現在は `RENDER` 明示時のみ autostart する極性反転ゲートになっている。今回のスコープ内には再汚染ロジックは見当たらなかった。
