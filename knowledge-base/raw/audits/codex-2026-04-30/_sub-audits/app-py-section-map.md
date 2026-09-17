# app.py Section Map (14,108 lines)

Sub 1a/1b/1c に渡す行範囲の確定マップ。
Codex には `awk 'NR>=START && NR<=END' app.py` 等で渡す。

## Sub 1a: Live Trading Path (signal compute + trader)

### 1a-1: Signal computation core
- L 1177-1222 `rule_signal`
- L 1223-1378 `get_htf_bias` / `get_htf_bias_daytrade`
- L 1507-1620 `detect_fake_breakout` / `detect_liquidity_zones`
- L 1621-1898 `compute_signal`
- L 1899-2054 `get_daily_weekly_direction` / `get_news_sentiment`

### 1a-2: Strategy signal compute
- L 2055-3458 `compute_daytrade_signal`
- L 3459-4037 `compute_1h_zone_signal`
- L 4038-4196 `compute_rnb_signal`
- L 4197-4308 `compute_hourly_signal`
- L 4364-4610 `compute_swing_signal`
- L 7496-7618 `compute_session_signal`
- L 8222-9449 `compute_scalp_signal` / v2 / v1_legacy

### 1a-3: Live runtime
- L 7619-7742 `detect_market_regime`
- L 7743-7958 `extract_ml_features` / `train_ml_model`
- L 7959-8221 `get_ml_confidence` / `compute_layer2_score` / `compute_layer3_score`
- L 14025-14106 `_auto_start_trader` / `__main__`

### 1a-4: Helpers
- L 32-100 price helpers
- L 235-413 `record_trade_result` / `compute_kpi`
- L 414-499 `is_trade_prohibited`
- L 500-635 `get_master_bias` / `get_session_info`
- L 636-792 `mtf_confluence` / SR / channel / parallel_channel
- L 793-906 `calc_sl_tp_v3` / momentum / vol_force
- L 907-1176 `institutional_flow_score` / `fetch_jp10y` / `fundamental_score`
- L 1379-1506 COT helpers / `fetch_cot_data`

**Total**: 約 9,200 行 → さらに分割推奨だが Codex に分割マニフェストごと渡す形でも可

## Sub 1b: BT Path

- L 4611-4914 BT helpers (`_get_dxy_trend_for_bt`, `_bt_classify_session`, `_bt_spread`, `_bt_get_slippage`)
- L 4916-5277 `run_backtest`
- L 5278-5336 `_check_trend_changed_and_clear_bt`
- L 5337-5984 `run_scalp_backtest`
- L 5985-7041 `run_daytrade_backtest`
- L 7042-7302 `run_swing_backtest`
- L 6629-7041 `run_1h_backtest`
- L 10295-10492 `run_strategy_evaluation`
- L 11104-11160 `api_backtest`
- L 11161-11247 `_save_bt_to_kb`
- L 11248-11320 `_evaluate_bt_for_promotion`
- L 11304-11434 `_run_bt_by_mode`
- L 11436-11583 `api_bt_pipeline_batch`
- L 11585-11741 `_run_chunked_scalp_bt`
- L 11742-11905 `api_backtest_long`

**Total**: 約 4,400 行

## Sub 1c: Web/API Path

- L 1-31 imports
- L 100-230 auth, before/after, cache, perf load/save
- L 381-413 calendar (shared)
- L 9450-9516 news AI / page routes / `_wilson_lower`
- L 9517-9639 strategy metrics helpers
- L 9640-9919 `api_strategies_status` / `api_admin_regenerate_tier_master`
- L 9919-10078 `api_performance` / `api_record_performance` / `api_layer_status` / `api_regime_status`
- L 10079-10293 `api_hmm_*` / `api_signal` / `api_day_plan` / `api_chart`
- L 10493-10692 `api_evaluation` / analyst memory
- L 10693-11102 `run_historical_pattern_analysis` / `api_pattern_analysis` / `api_analyst_opinion` / `api_ml_train`
- L 11321-11434 `api_bt_pipeline`
- L 11906-12330 `api_strategy_mode` ... `api_price`
- L 12334-12420 `healthz`, demo status/logs/start/stop
- L 12421-12500 `api_demo_close_trade` / `api_oanda_accounts`
- L 12504-13189 全 oanda 系 routes
- L 13190-13580 chart-data / demo/* / sentinel / factors / equity / params / learning / rules / daily-review / algo-changes
- L 13580-13620 emergency / db/backup
- L 13621-13863 risk_dashboard / phase_gate / scalp_bt_lab / consolidation
- L 13855-14024 portfolio / risk_slippage

**Total**: 約 4,500 行
