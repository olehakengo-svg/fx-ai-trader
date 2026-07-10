# WS3 探索2周目 — 新軸診断スキャン (rule:R3、純研究)

- 生成: 2026-07-10T06:38:07.341880+00:00 / pre-reg DRAFT: [[ws3-round2-explore-prereg-2026-07-10]] §2 (branch `research/h4-level-edge`) の候補生成手続きを機械実行
- 再現: `tools/ws3_round2_scan.py` (集計・除外・選抜) / `tools/ws3_round2_prep_eurgbp.py` (EUR_GBP データ準備) / `tools/ws3_mfe_scan.py --split-direction` (新フラグ、デフォルト OFF で既存挙動不変)
- Status: **診断集計のみ — promote 判定ではない**。live/shadow/本番変更なし
- 選抜規則: N≥30 ∧ (ratio_h24≥1.3 ∪ 持続型(ratio_h96≥1.3 ∧ h96>h24)), m≤10 (primary ratio 降順), ratio = median(MFE)/median(MAE)

## (i) 走査した軸と母集団の定義

**軸 (round-1 の補集合のみ)**:
- **(a) 方向分割**: entry_type × pair × sig (BUY/SELL) — round-1 は方向プールだった
- **(b) 未走査ペア**: production shadow 母集団のうち round-1 h24 表に現れなかったペア = **EUR_GBP のみ**
- **(c) h24/h96 両 horizon**: 持続型 (h96 で増幅) の拾い上げ — round-1 の h24 主表から漏れたセル

**母集団**:
1. **round-1 entries**: `.ws3_mfe_scan_checkpoint.json` (commit 604dcc4f、N=6,995、6 pairs、探索窓 2025-07-08〜2026-06-07、診断窓 2026-06-07〜 除外済) を**そのまま使用** — 再BTせず checkpoint を流用することで探索窓の同一性を構成的に保証。検証: checkpoint から pooled 118 セルの全統計量 (mfe_p50/p75/p90, p_mfe_ge15/20, mae_p50 × 5 horizons) を再計算し `ws3_mfe_scan_2026_07.json` と**完全一致 (mismatch 0/118)**、round-1 診断表の ratio (1.81 / 1.65 / 1.38→1.94 / 1.29→2.05) も一致
2. **production shadow 母集団ペアの機械列挙**: `modules/demo_trader.py` MODE_CONFIG の `signal_fn=compute_daytrade_signal ∧ tf=15m ∧ auto_start=True` → {USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP}。本番 `/api/demo/trades` 直近 2,001 行の DT-15m mode×instrument 分布 {EUR_GBP:78, EUR_JPY:170, EUR_USD:304, GBP_JPY:176, GBP_USD:426, USD_JPY:297} とも一致確認 (2026-07-10)。round-1 h24 表との差分 = **EUR_GBP のみ**
3. **EUR_GBP データ**: `tools/ws3_round2_prep_eurgbp.py` — 既存 12y parquet slice 20,430 行 + Massive API 追加取得 4,179 行 (2026-05-05〜2026-07-08、`modules.data.fetch_ohlcv_massive` = `tools/fetch_massive_data.py` と同一経路) = 24,609 行。窓 **[2025-07-08T03:45Z, 2026-07-08T03:45Z]** = round-1 入力 EUR_JPY parquet tail と同一境界 (loader は tail−365d 窓のため窓開始が round-1 と一致)。**OOS 行 0 / >3d gap 0**。この parquet 差し替えは worktree 一時的 (コミットは元の 12y 版を維持)

**軸(b) の結果 — EUR_GBP は候補到達不能**:
`BT_MODE=1 NO_AUTOSTART=1 BT_REQUIRE_MASSIVE_CACHE=1 tools/ws3_mfe_scan.py --pairs EUR_GBP --split-direction --out-suffix _round2_eurgbp` を完走 (1,269s) したが、BT baseline は engine の最小サンプルガードに抵触: **「サンプル数不足（20トレード未満）」→ entries=0** (`ws3_mfe_scan_2026_07_round2_eurgbp.json`)。EUR_GBP の 15m DT シグナルは HTF Hard Block で大半が block → shadow rescue 経路 (BT ではトレード化されない) であり、365d で執行ベース 20 トレード未満。**全セルが選抜下限 N≥30 に到達不能 — 軸(b) からの候補ゼロは構造的必然**。データ取得の問題ではない (Massive 取得は成功)

**対象外の記録** (§2(b) 機械列挙の残余):
- **XAU_USD**: `daytrade_xau` auto_start=False (v6.6 停止) = 非稼働 + Massive 対象外規約 → 対象外
- **AUD_JPY**: production 15m DT mode は無いが round-1 母集団に含まれる → 軸(a)/(c) で走査 (新ペアではない)
- **rnb_usdjpy**: 別 signal 系統 (compute_rnb_signal) — compute_daytrade_signal 母集団外
- **データ取得不能で除外したペア: なし**

**遮断の遵守**:
- OOS 窓 (2024-07-07〜2025-07-07) のデータ・統計に非接触 (EUR_GBP parquet 準備は時刻 slice のみ、OOS 行の書き出し・統計計算ゼロ)
- stage-2 排他領域 (`tools/ws3_stage2_barrier_sim.py` / `raw/bt-results/ws3_stage2_*`) 非接触 — 本スキャンの設計・選抜は stage-2 の結果を一切参照していない
- BE/Trail は MFE/MAE 計測に関与しない (forward scan、round-1 と同一エンジン)

## 候補リスト (選抜規則適用後)

| # | cell | axis | 型 | N | ratio h24 | ratio h96 | primary |
|---|---|---|---|---|---|---|---|
| 1 | sr_fib_confluence×GBP_USD×SELL | a (方向分割) | 持続 | 95 | 1.176 | 1.656 | h96 |
| 2 | vol_spike_mr×USD_JPY×BUY | a (方向分割) | 減衰 | 39 | 1.49 | 1.375 | h24 |
| 3 | sr_fib_confluence×EUR_USD×SELL | a (方向分割) | 持続 | 99 | 1.356 | 1.487 | h96 |
| 4 | vsg_jpy_reversal×GBP_JPY×SELL | a (方向分割) | 減衰 | 106 | 1.482 | 1.226 | h24 |
| 5 | turtle_soup×GBP_USD | c (round-1 pooled 持続型) | 持続 | 40 | 0.911 | 1.413 | h96 |
| 6 | dt_sr_channel_reversal×GBP_USD×SELL | a (方向分割) | 持続 | 36 | 0.971 | 1.401 | h96 |
| 7 | dt_sr_channel_reversal×GBP_JPY×BUY | a (方向分割) | 持続 | 77 | 0.968 | 1.327 | h96 |
| 8 | sr_fib_confluence×AUD_JPY×SELL | a (方向分割) | 減衰 | 119 | 1.317 | 1.187 | h24 |

**観察ノート (記述のみ — この標本の数値を promote 根拠にすることは禁止)**:
- **sr_fib_confluence SELL が 3 ペア** (GBP_USD/EUR_USD/AUD_JPY) — 同一戦略の SELL 側に横断的な非対称。相関セルであり独立 8 検定ではない (OOS の BH-FDR は m=8 でやや保守側に働く)。メカニズム仮説として一貫性がある一方、共通ファクター (2025-26 の USD 方向レジーム) の可能性も OOS で判別される
- **持続型が 5/8** — round-1 候補 (減衰型 6/8) と対照的。方向分割・h96 軸は「トレンド持続を捉えるセル」を優先的に露出した
- **turtle_soup×GBP_USD (候補#5) の裁定**: turtle_soup は水平流動性 sweep 系と概念近接だが、falsified 6 系統の該当は研究ハーネス (`tools/sweep_reclaim_explore.py`、ライン接触→方向の別 estimand) であり、本セルは「本番 engine エントリー母集団の forward 非対称」。stage-1 での lin_reg_channel 裁定 (ws3-asymmetry-oos-prereg §2 注記) と同型の扱いで候補に残した — **pre-reg LOCK 時に親セッションが最終裁定すること** (除外なら m=7)
- 減衰型 3 セルの h24 ratio (1.32-1.49) は round-1 上位 (1.51-1.81) より低い — 上澄み既採取後の 2 周目として自然

## 全セル ratio 表 (N≥10)

### 方向分割セル (axis a)

| cell | N | MFE p50 (h24) | MAE p50 (h24) | ratio h24 | ratio h96 |
|---|---|---|---|---|---|
| sr_anti_hunt_bounce×USD_JPY×BUY | 13 | 25.5 | 12.8 | 1.992 | 1.588 |
| dt_fib_reversal×AUD_JPY×SELL | 16 | 31.2 | 15.8 | 1.975 | 1.461 |
| dt_fib_reversal×GBP_USD×BUY | 14 | 24.75 | 13.45 | 1.84 | 1.073 |
| turtle_soup×GBP_USD×BUY | 17 | 32.5 | 20.1 | 1.617 | 1.559 |
| dual_sr_bounce×GBP_USD×SELL | 21 | 22.4 | 14.0 | 1.6 | 1.871 |
| vol_spike_mr×USD_JPY×BUY | 39 | 29.2 | 19.6 | 1.49 | 1.375 |
| vsg_jpy_reversal×GBP_JPY×SELL | 106 | 35.2 | 23.75 | 1.482 | 1.226 |
| ema_cross×GBP_JPY×BUY | 13 | 33.0 | 23.3 | 1.416 | 1.544 |
| htf_false_breakout×GBP_USD×BUY | 16 | 26.45 | 19.0 | 1.392 | 1.014 |
| ema_cross×USD_JPY×BUY | 10 | 17.8 | 12.9 | 1.38 | 2.182 |
| sr_fib_confluence×EUR_USD×SELL | 99 | 18.3 | 13.5 | 1.356 | 1.487 |
| post_news_vol×GBP_USD×BUY | 10 | 25.95 | 19.45 | 1.334 | 1.023 |
| sr_fib_confluence×AUD_JPY×SELL | 119 | 24.5 | 18.6 | 1.317 | 1.187 |
| intraday_seasonality×EUR_JPY×SELL | 27 | 24.6 | 18.7 | 1.316 | 1.342 |
| dual_sr_bounce×AUD_JPY×SELL | 36 | 22.15 | 17.21 | 1.287 | 1.048 |
| trendline_sweep×GBP_USD×SELL | 39 | 22.5 | 17.5 | 1.286 | 1.27 |
| dt_sr_channel_reversal×USD_JPY×SELL | 47 | 26.3 | 20.8 | 1.264 | 0.657 |
| sr_fib_confluence×GBP_USD×BUY | 82 | 20.55 | 16.35 | 1.257 | 0.923 |
| dual_sr_bounce×EUR_USD×SELL | 12 | 17.5 | 14.0 | 1.25 | 1.607 |
| wick_imbalance_reversion×GBP_JPY×BUY | 87 | 29.6 | 24.4 | 1.213 | 1.09 |
| sr_break_retest×AUD_JPY×SELL | 40 | 22.2 | 18.45 | 1.203 | 0.976 |
| ema200_trend_reversal×GBP_USD×SELL | 17 | 19.1 | 15.9 | 1.201 | 0.733 |
| dt_sr_channel_reversal×EUR_JPY×BUY | 92 | 26.025 | 21.75 | 1.197 | 0.849 |
| dual_sr_bounce×GBP_JPY×BUY | 53 | 31.9 | 26.9 | 1.186 | 1.009 |
| sr_fib_confluence×GBP_USD×SELL | 95 | 22.0 | 18.7 | 1.176 | 1.656 |
| ema_cross×EUR_JPY×BUY | 14 | 22.55 | 19.3 | 1.168 | 1.515 |
| dt_fib_reversal×GBP_JPY×BUY | 33 | 32.63 | 28.5 | 1.145 | 1.047 |
| dt_sr_channel_reversal×AUD_JPY×SELL | 62 | 20.6 | 18.415 | 1.119 | 1.256 |
| dt_sr_channel_reversal×GBP_JPY×SELL | 55 | 32.2 | 29.1 | 1.107 | 0.787 |
| xs_momentum_rsi×USD_JPY×BUY | 34 | 16.9 | 15.35 | 1.101 | 0.965 |
| ema200_trend_reversal×EUR_JPY×BUY | 23 | 17.79 | 16.5 | 1.078 | 0.929 |
| sr_break_retest×EUR_JPY×BUY | 78 | 20.25 | 19.05 | 1.063 | 0.933 |
| wick_imbalance_reversion×EUR_USD×BUY | 16 | 15.9 | 15.15 | 1.05 | 1.565 |
| dt_fib_reversal×AUD_JPY×BUY | 45 | 21.4 | 20.4 | 1.049 | 1.112 |
| sr_break_retest×USD_JPY×SELL | 18 | 19.1 | 18.25 | 1.047 | 0.903 |
| vsg_jpy_reversal×EUR_JPY×SELL | 62 | 24.55 | 23.65 | 1.038 | 0.883 |
| xs_momentum×USD_JPY×SELL | 41 | 23.7 | 23.0 | 1.03 | 0.778 |
| session_time_bias×EUR_USD×SELL | 159 | 17.5 | 17.0 | 1.029 | 1.091 |
| wick_imbalance_reversion×AUD_JPY×BUY | 153 | 18.8 | 18.5 | 1.016 | 0.837 |
| vsg_jpy_reversal×EUR_JPY×BUY | 128 | 23.15 | 22.8 | 1.015 | 1.143 |
| dual_sr_bounce×EUR_JPY×SELL | 44 | 22.15 | 21.85 | 1.014 | 1.147 |
| gbp_deep_pullback×GBP_USD×SELL | 25 | 16.0 | 15.8 | 1.013 | 0.855 |
| streak_reversal×USD_JPY×BUY | 184 | 21.0 | 20.85 | 1.007 | 1.068 |
| sr_fib_confluence×GBP_JPY×SELL | 92 | 31.9 | 31.88 | 1.001 | 0.728 |
| intraday_seasonality×GBP_USD×BUY | 20 | 18.55 | 18.7 | 0.992 | 0.825 |
| sr_anti_hunt_bounce×GBP_JPY×BUY | 24 | 33.0 | 33.46 | 0.986 | 0.581 |
| intraday_seasonality×USD_JPY×BUY | 50 | 20.1 | 20.5 | 0.98 | 0.842 |
| sr_break_retest×AUD_JPY×BUY | 94 | 18.2 | 18.6 | 0.978 | 0.68 |
| doji_breakout×GBP_USD×BUY | 11 | 17.3 | 17.7 | 0.977 | 0.509 |
| dt_sr_channel_reversal×GBP_USD×SELL | 36 | 13.3 | 13.7 | 0.971 | 1.401 |
| dt_sr_channel_reversal×GBP_JPY×BUY | 77 | 27.3 | 28.2 | 0.968 | 1.327 |
| vsg_jpy_reversal×GBP_JPY×BUY | 218 | 30.25 | 31.83 | 0.95 | 1.026 |
| sr_fib_confluence×GBP_JPY×BUY | 93 | 30.5 | 32.3 | 0.944 | 1.062 |
| htf_false_breakout×GBP_JPY×BUY | 14 | 28.9 | 30.7 | 0.941 | 0.702 |
| sr_break_retest×USD_JPY×BUY | 31 | 15.4 | 16.4 | 0.939 | 0.958 |
| dt_sr_channel_reversal×EUR_JPY×SELL | 55 | 24.2 | 26.1 | 0.927 | 0.785 |
| sr_fib_confluence×USD_JPY×SELL | 57 | 18.7 | 20.7 | 0.903 | 0.478 |
| htf_false_breakout×GBP_USD×SELL | 15 | 14.4 | 16.0 | 0.9 | 1.277 |
| xs_momentum×EUR_USD×BUY | 102 | 15.25 | 17.1 | 0.892 | 1.086 |
| dual_sr_bounce×EUR_JPY×BUY | 57 | 21.6 | 24.3 | 0.889 | 0.948 |
| streak_reversal×USD_JPY×SELL | 118 | 22.05 | 24.85 | 0.887 | 0.922 |
| sr_fib_confluence×EUR_JPY×SELL | 96 | 24.4 | 27.6 | 0.884 | 0.658 |
| dual_sr_bounce×GBP_JPY×SELL | 44 | 28.75 | 32.9 | 0.874 | 0.552 |
| sr_anti_hunt_bounce×EUR_JPY×BUY | 24 | 19.3 | 22.15 | 0.871 | 1.2 |
| sr_break_retest×GBP_JPY×SELL | 43 | 32.0 | 36.8 | 0.87 | 1.101 |
| dt_fib_reversal×EUR_JPY×BUY | 32 | 20.2 | 23.5 | 0.86 | 0.776 |
| tokyo_range_breakout_up×USD_JPY×BUY | 17 | 15.0 | 17.5 | 0.857 | 1.048 |
| ema200_trend_reversal×GBP_JPY×BUY | 14 | 30.6 | 35.78 | 0.855 | 1.041 |
| london_fix_reversal×USD_JPY×BUY | 25 | 15.3 | 17.9 | 0.855 | 1.254 |
| post_news_vol×GBP_USD×SELL | 11 | 35.3 | 41.5 | 0.851 | 1.051 |
| vol_spike_mr×USD_JPY×SELL | 24 | 21.2 | 25.05 | 0.846 | 0.751 |
| xs_momentum×GBP_USD×SELL | 90 | 15.65 | 18.5 | 0.846 | 0.853 |
| ema200_trend_reversal×AUD_JPY×BUY | 22 | 19.4 | 23.05 | 0.842 | 1.212 |
| dual_sr_bounce×USD_JPY×SELL | 32 | 21.65 | 25.75 | 0.841 | 1.028 |
| wick_imbalance_reversion×GBP_USD×BUY | 43 | 19.2 | 22.9 | 0.838 | 1.259 |
| intraday_seasonality×AUD_JPY×SELL | 14 | 17.4 | 20.9 | 0.833 | 0.843 |
| doji_breakout×GBP_USD×SELL | 10 | 26.05 | 31.35 | 0.831 | 1.073 |
| pivot_detector_v2_5×EUR_USD×BUY | 14 | 13.55 | 16.4 | 0.826 | 1.271 |
| intraday_seasonality×EUR_JPY×BUY | 49 | 19.6 | 24.0 | 0.817 | 0.818 |
| vix_carry_unwind×USD_JPY×SELL | 77 | 25.9 | 31.9 | 0.812 | 0.527 |
| rsk_gbpjpy_reversion×GBP_JPY×BUY | 26 | 29.995 | 37.1 | 0.808 | 0.639 |
| intraday_seasonality×GBP_JPY×BUY | 60 | 24.8 | 30.775 | 0.806 | 0.771 |
| xs_momentum×EUR_USD×SELL | 101 | 12.8 | 16.0 | 0.8 | 1.003 |
| intraday_seasonality×GBP_JPY×SELL | 22 | 27.4 | 34.35 | 0.798 | 0.715 |
| sr_fib_confluence×EUR_JPY×BUY | 81 | 20.6 | 25.9 | 0.795 | 0.795 |
| sr_break_retest×GBP_JPY×BUY | 85 | 24.3 | 31.0 | 0.784 | 0.947 |
| london_fix_reversal×GBP_USD×BUY | 24 | 13.3 | 17.0 | 0.782 | 0.796 |
| sr_break_retest×EUR_JPY×SELL | 53 | 21.2 | 27.5 | 0.771 | 0.94 |
| dual_sr_bounce×EUR_USD×BUY | 15 | 14.1 | 18.5 | 0.762 | 0.741 |
| dt_fib_reversal×GBP_JPY×SELL | 12 | 21.62 | 29.13 | 0.742 | 0.241 |
| intraday_seasonality×AUD_JPY×BUY | 61 | 19.9 | 26.9 | 0.74 | 0.661 |
| xs_momentum×USD_JPY×BUY | 80 | 16.55 | 22.4 | 0.739 | 0.857 |
| dt_sr_channel_reversal×AUD_JPY×BUY | 100 | 19.835 | 27.2 | 0.729 | 0.663 |
| gbp_deep_pullback×GBP_USD×BUY | 31 | 15.8 | 21.7 | 0.728 | 0.862 |
| session_time_bias×GBP_USD×SELL | 185 | 19.8 | 27.6 | 0.717 | 0.797 |
| dual_sr_bounce×USD_JPY×BUY | 28 | 20.25 | 28.3 | 0.716 | 1.175 |
| orb_trap×GBP_USD×BUY | 22 | 13.35 | 18.75 | 0.712 | 0.872 |
| london_fix_reversal×GBP_USD×SELL | 17 | 14.0 | 19.7 | 0.711 | 1.032 |
| wick_imbalance_reversion×EUR_JPY×BUY | 63 | 20.1 | 28.7 | 0.7 | 0.795 |
| dual_sr_bounce×GBP_USD×BUY | 29 | 16.6 | 24.0 | 0.692 | 0.62 |
| sr_fib_confluence×AUD_JPY×BUY | 100 | 18.05 | 26.9 | 0.671 | 0.912 |
| xs_momentum_rsi×USD_JPY×SELL | 31 | 21.9 | 32.9 | 0.666 | 0.647 |
| xs_momentum×GBP_USD×BUY | 104 | 14.45 | 22.65 | 0.638 | 0.975 |
| turtle_soup×GBP_USD×SELL | 23 | 12.8 | 20.4 | 0.627 | 1.335 |
| htf_false_breakout×GBP_JPY×SELL | 15 | 27.0 | 43.1 | 0.626 | 0.667 |
| ema200_trend_reversal×GBP_JPY×SELL | 10 | 23.9 | 39.1 | 0.611 | 0.497 |
| sr_fib_confluence×USD_JPY×BUY | 51 | 18.4 | 31.2 | 0.59 | 0.519 |
| intraday_seasonality×EUR_USD×SELL | 10 | 12.3 | 20.9 | 0.589 | 0.665 |
| trendline_sweep×GBP_USD×BUY | 39 | 17.3 | 29.5 | 0.586 | 0.782 |
| dt_fib_reversal×GBP_USD×SELL | 12 | 14.95 | 25.6 | 0.584 | 0.83 |
| dt_sr_channel_reversal×GBP_USD×BUY | 43 | 10.4 | 17.9 | 0.581 | 1.008 |
| intraday_seasonality×GBP_USD×SELL | 22 | 16.2 | 28.2 | 0.574 | 0.741 |
| dt_fib_reversal×EUR_JPY×SELL | 27 | 15.0 | 28.16 | 0.533 | 0.693 |
| rsk_gbpjpy_reversion×GBP_JPY×SELL | 14 | 24.2 | 47.8 | 0.506 | 0.743 |
| dual_sr_bounce×AUD_JPY×BUY | 53 | 15.5 | 30.8 | 0.503 | 0.78 |
| dt_sr_channel_reversal×USD_JPY×BUY | 43 | 13.1 | 28.4 | 0.461 | 0.347 |
| zz_pivot_v60_sr×EUR_USD×SELL | 13 | 9.7 | 22.2 | 0.437 | 0.445 |
| london_fix_reversal×USD_JPY×SELL | 13 | 10.2 | 23.4 | 0.436 | 0.484 |
| ema200_trend_reversal×EUR_JPY×SELL | 12 | 8.25 | 19.2 | 0.43 | 0.443 |
| post_news_vol×EUR_USD×BUY | 14 | 9.5 | 22.4 | 0.424 | 0.533 |
| wick_imbalance_reversion×USD_JPY×BUY | 24 | 14.15 | 34.35 | 0.412 | 0.512 |
| dt_fib_reversal×EUR_USD×SELL | 14 | 13.35 | 33.15 | 0.403 | 0.84 |
| sr_fib_confluence×EUR_USD×BUY | 90 | 9.2 | 23.4 | 0.393 | 0.384 |
| ema_cross×AUD_JPY×BUY | 16 | 15.65 | 42.2 | 0.371 | 0.472 |
| orb_trap×EUR_USD×BUY | 17 | 6.5 | 19.1 | 0.34 | 0.18 |
| sr_break_retest×GBP_USD×SELL | 17 | 9.3 | 32.0 | 0.291 | 0.427 |
| post_news_vol×USD_JPY×BUY | 11 | 8.5 | 39.9 | 0.213 | 0.962 |
| sr_break_retest×GBP_USD×BUY | 15 | 2.8 | 40.6 | 0.069 | 0.341 |

### pooled セル (axis b/c)

| cell | N | MFE p50 (h24) | MAE p50 (h24) | ratio h24 | ratio h96 |
|---|---|---|---|---|---|
| london_ny_swing×EUR_USD | 10 | 18.05 | 8.25 | 2.188 | 4.718 |
| sr_anti_hunt_bounce×USD_JPY | 19 | 24.3 | 14.2 | 1.711 | 1.326 |
| ema200_trend_reversal×USD_JPY | 16 | 24.05 | 19.4 | 1.24 | 0.931 |
| ema_cross×GBP_JPY | 22 | 31.65 | 25.9 | 1.222 | 1.286 |
| dt_fib_reversal×AUD_JPY | 61 | 23.0 | 18.9 | 1.217 | 1.163 |
| wick_imbalance_reversion×GBP_JPY | 87 | 29.6 | 24.4 | 1.213 | 1.09 |
| vol_spike_mr×USD_JPY | 63 | 23.9 | 20.0 | 1.195 | 1.023 |
| sr_fib_confluence×GBP_USD | 177 | 21.7 | 18.3 | 1.186 | 1.256 |
| dt_fib_reversal×GBP_USD | 26 | 22.0 | 18.85 | 1.167 | 1.06 |
| post_news_vol×GBP_USD | 21 | 27.6 | 23.9 | 1.155 | 0.989 |
| dt_fib_reversal×GBP_JPY | 45 | 32.6 | 28.77 | 1.133 | 0.949 |
| dt_sr_channel_reversal×EUR_JPY | 147 | 25.1 | 22.2 | 1.131 | 0.867 |
| ema200_trend_reversal×AUD_JPY | 30 | 22.65 | 20.75 | 1.092 | 1.292 |
| ema200_trend_reversal×EUR_JPY | 35 | 17.73 | 16.5 | 1.075 | 0.859 |
| sr_anti_hunt_bounce×GBP_JPY | 32 | 32.55 | 30.4 | 1.071 | 0.536 |
| vsg_jpy_reversal×GBP_JPY | 324 | 30.84 | 28.95 | 1.065 | 1.067 |
| intraday_seasonality×EUR_JPY | 76 | 23.05 | 22.05 | 1.045 | 0.925 |
| vsg_jpy_reversal×EUR_JPY | 190 | 24.1 | 23.1 | 1.043 | 1.047 |
| intraday_seasonality×EUR_USD | 19 | 21.3 | 20.7 | 1.029 | 0.592 |
| session_time_bias×EUR_USD | 159 | 17.5 | 17.0 | 1.029 | 1.091 |
| ema_cross×USD_JPY | 18 | 20.3 | 20.1 | 1.01 | 0.781 |
| wick_imbalance_reversion×EUR_USD | 17 | 15.0 | 14.9 | 1.007 | 1.766 |
| wick_imbalance_reversion×AUD_JPY | 155 | 18.8 | 18.8 | 1.0 | 0.833 |
| sr_break_retest×AUD_JPY | 134 | 18.36 | 18.45 | 0.995 | 0.815 |
| sr_break_retest×USD_JPY | 49 | 17.3 | 17.4 | 0.994 | 0.958 |
| dt_sr_channel_reversal×GBP_JPY | 132 | 28.1 | 28.65 | 0.981 | 1.265 |
| sr_fib_confluence×GBP_JPY | 185 | 31.3 | 31.9 | 0.981 | 0.898 |
| streak_reversal×USD_JPY | 302 | 21.5 | 22.0 | 0.977 | 1.029 |
| dual_sr_bounce×GBP_JPY | 97 | 28.9 | 29.6 | 0.976 | 0.758 |
| htf_false_breakout×EUR_USD | 12 | 17.1 | 17.6 | 0.972 | 1.74 |
| ema_cross×EUR_JPY | 19 | 22.7 | 23.5 | 0.966 | 1.121 |
| sr_fib_confluence×AUD_JPY | 219 | 21.1 | 22.4 | 0.942 | 1.094 |
| sr_break_retest×EUR_JPY | 131 | 21.0 | 22.4 | 0.938 | 0.915 |
| dual_sr_bounce×EUR_JPY | 101 | 21.6 | 23.2 | 0.931 | 1.105 |
| htf_false_breakout×GBP_USD | 31 | 17.4 | 18.7 | 0.93 | 0.907 |
| turtle_soup×GBP_USD | 40 | 18.45 | 20.25 | 0.911 | 1.413 |
| sr_anti_hunt_bounce×EUR_JPY | 33 | 20.2 | 22.4 | 0.902 | 0.762 |
| xs_momentum_rsi×USD_JPY | 65 | 19.3 | 21.8 | 0.885 | 0.757 |
| dual_sr_bounce×AUD_JPY | 89 | 19.6 | 22.3 | 0.879 | 0.892 |
| dual_sr_bounce×EUR_USD | 27 | 14.8 | 16.9 | 0.876 | 0.969 |
| htf_false_breakout×GBP_JPY | 29 | 27.0 | 30.9 | 0.874 | 0.702 |
| tokyo_range_breakout_up×USD_JPY | 17 | 15.0 | 17.5 | 0.857 | 1.048 |
| gbp_deep_pullback×GBP_USD | 56 | 15.9 | 18.65 | 0.853 | 0.793 |
| dt_sr_channel_reversal×AUD_JPY | 162 | 19.835 | 23.4 | 0.848 | 0.833 |
| wick_imbalance_reversion×GBP_USD | 43 | 19.2 | 22.9 | 0.838 | 1.259 |
| sr_fib_confluence×EUR_JPY | 177 | 22.13 | 26.5 | 0.835 | 0.698 |
| intraday_seasonality×USD_JPY | 57 | 17.4 | 20.9 | 0.833 | 0.74 |
| dual_sr_bounce×USD_JPY | 60 | 21.35 | 25.75 | 0.829 | 1.121 |
| dual_sr_bounce×GBP_USD | 50 | 18.3 | 22.1 | 0.828 | 0.95 |
| pivot_detector_v2_5×EUR_USD | 14 | 13.55 | 16.4 | 0.826 | 1.271 |
| intraday_seasonality×GBP_JPY | 82 | 26.45 | 32.15 | 0.823 | 0.729 |
| vix_carry_unwind×USD_JPY | 77 | 25.9 | 31.9 | 0.812 | 0.527 |
| trendline_sweep×GBP_USD | 78 | 18.7 | 23.15 | 0.808 | 0.939 |
| london_fix_reversal×USD_JPY | 38 | 14.6 | 18.4 | 0.793 | 0.996 |
| sr_fib_confluence×EUR_USD | 189 | 15.1 | 19.1 | 0.791 | 0.873 |
| xs_momentum×EUR_USD | 203 | 13.4 | 17.0 | 0.788 | 1.017 |
| xs_momentum×USD_JPY | 121 | 17.7 | 22.6 | 0.783 | 0.818 |
| orb_trap×USD_JPY | 17 | 14.4 | 18.6 | 0.774 | 0.69 |
| ema200_trend_reversal×GBP_JPY | 24 | 28.65 | 37.23 | 0.77 | 0.68 |
| london_fix_reversal×GBP_USD | 41 | 13.3 | 17.3 | 0.769 | 0.939 |
| ema_cross×EUR_USD | 11 | 17.4 | 22.8 | 0.763 | 0.894 |
| sr_break_retest×GBP_JPY | 128 | 24.9 | 32.9 | 0.757 | 1.064 |
| adx_trend_continuation×EUR_USD | 12 | 20.3 | 27.15 | 0.748 | 0.374 |
| dt_sr_channel_reversal×GBP_USD | 79 | 11.2 | 15.1 | 0.742 | 1.173 |
| sr_fib_confluence×USD_JPY | 108 | 18.65 | 25.65 | 0.727 | 0.489 |
| xs_momentum×GBP_USD | 194 | 14.85 | 20.45 | 0.726 | 0.877 |
| doji_breakout×GBP_USD | 21 | 20.6 | 28.5 | 0.723 | 0.862 |
| intraday_seasonality×AUD_JPY | 75 | 18.7 | 26.0 | 0.719 | 0.606 |
| rsk_gbpjpy_reversion×GBP_JPY | 40 | 28.345 | 39.55 | 0.717 | 0.624 |
| session_time_bias×GBP_USD | 185 | 19.8 | 27.6 | 0.717 | 0.797 |
| orb_trap×GBP_USD | 30 | 13.35 | 18.75 | 0.712 | 0.943 |
| intraday_seasonality×GBP_USD | 42 | 16.3 | 22.95 | 0.71 | 0.74 |
| dt_fib_reversal×EUR_JPY | 59 | 18.9 | 26.8 | 0.705 | 0.693 |
| post_news_vol×EUR_USD | 18 | 14.35 | 20.45 | 0.702 | 0.973 |
| ema_cross×AUD_JPY | 23 | 19.8 | 29.2 | 0.678 | 0.505 |
| wick_imbalance_reversion×EUR_JPY | 64 | 19.5 | 28.75 | 0.678 | 0.755 |
| dt_sr_channel_reversal×USD_JPY | 90 | 18.55 | 27.4 | 0.677 | 0.585 |
| dt_fib_reversal×EUR_USD | 23 | 14.3 | 21.4 | 0.668 | 0.884 |
| zz_pivot_v60_sr×EUR_USD | 17 | 14.4 | 22.2 | 0.649 | 0.577 |
| ema200_trend_reversal×GBP_USD | 26 | 12.05 | 20.85 | 0.578 | 0.494 |
| sr_anti_hunt_bounce×EUR_USD | 10 | 11.4 | 19.8 | 0.576 | 0.609 |
| jpy_basket_trend×EUR_JPY | 15 | 12.7 | 24.7 | 0.514 | 1.103 |
| wick_imbalance_reversion×USD_JPY | 30 | 13.9 | 31.0 | 0.448 | 0.464 |
| htf_false_breakout×USD_JPY | 10 | 15.8 | 38.7 | 0.408 | 0.368 |
| squeeze_release_momentum×EUR_USD | 17 | 8.2 | 23.0 | 0.357 | 0.263 |
| post_news_vol×USD_JPY | 15 | 8.5 | 24.9 | 0.341 | 1.712 |
| orb_trap×EUR_USD | 26 | 6.85 | 20.8 | 0.329 | 0.266 |
| sr_break_retest×GBP_USD | 32 | 9.05 | 35.1 | 0.258 | 0.423 |
| ema_cross×GBP_USD | 11 | 6.6 | 41.2 | 0.16 | 0.256 |
| sr_anti_hunt_bounce×GBP_USD | 13 | 4.8 | 31.8 | 0.151 | 0.62 |

## 除外適用ログ

- stage-1 判定済み 8 セル (方向サブセル含め除外): htf_false_breakout×EUR_JPY, trendline_sweep×EUR_USD, dt_sr_channel_reversal×EUR_USD, london_fix_reversal×EUR_USD, htf_false_breakout×AUD_JPY, lin_reg_channel×EUR_USD, hull_donchian_fade×EUR_USD, dt_fib_reversal×USD_JPY
- channel (回帰±2σ/swing平行, project-channel-edge-falsified): 適用 → ['lin_reg_channel']
- 水平sweep&reclaim (project-sweep-reclaim-horizontal-falsified): 適用 → ['liquidity_sweep']
- bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可: 適用 → ['dt_bb_rsi_mr']
- H4 level (project-h4-level-edge-falsified): 非該当 (母集団に entry_type 不存在)
- mtf_regime_switch SELL (project-mtf-regime-switch-falsified): 非該当 (母集団に entry_type 不存在)
- T11 LDN朝×counter-USD MR (project-t11-ldn-counter-usd-falsified): 非該当 (母集団に entry_type 不存在)

除外された個別セル (N≥10):

| cell | N | ratio h24 | ratio h96 | 理由 |
|---|---|---|---|---|
| dt_bb_rsi_mr×EUR_USD | 56 | 1.037 | 0.896 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×GBP_USD | 113 | 0.868 | 1.0 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×USD_JPY | 134 | 0.78 | 0.602 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_fib_reversal×USD_JPY | 24 | 1.292 | 2.047 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| dt_sr_channel_reversal×EUR_USD | 25 | 1.549 | 1.175 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| htf_false_breakout×AUD_JPY | 27 | 1.39 | 1.019 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| htf_false_breakout×EUR_JPY | 24 | 1.81 | 0.901 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| hull_donchian_fade×EUR_USD | 46 | 1.297 | 0.97 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| lin_reg_channel×EUR_USD | 24 | 1.382 | 1.944 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| london_fix_reversal×EUR_USD | 36 | 1.511 | 1.242 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| trendline_sweep×EUR_USD | 45 | 1.65 | 0.818 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| dt_bb_rsi_mr×EUR_USD×BUY | 30 | 0.906 | 0.766 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×EUR_USD×SELL | 26 | 1.614 | 1.029 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×GBP_USD×BUY | 52 | 0.593 | 0.88 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×GBP_USD×SELL | 61 | 1.039 | 1.162 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×USD_JPY×BUY | 52 | 1.175 | 1.212 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_bb_rsi_mr×USD_JPY×SELL | 82 | 0.646 | 0.537 | falsified 系統: bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統 (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可 |
| dt_fib_reversal×USD_JPY×BUY | 16 | 2.032 | 2.474 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| dt_sr_channel_reversal×EUR_USD×BUY | 16 | 0.683 | 0.7 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| htf_false_breakout×AUD_JPY×BUY | 14 | 0.972 | 0.725 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| htf_false_breakout×AUD_JPY×SELL | 13 | 1.826 | 1.019 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| htf_false_breakout×EUR_JPY×BUY | 17 | 2.965 | 1.026 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| hull_donchian_fade×EUR_USD×BUY | 16 | 1.402 | 1.37 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| hull_donchian_fade×EUR_USD×SELL | 30 | 1.172 | 1.033 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| lin_reg_channel×EUR_USD×BUY | 11 | 3.554 | 3.352 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| lin_reg_channel×EUR_USD×SELL | 13 | 0.695 | 0.611 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| london_fix_reversal×EUR_USD×BUY | 20 | 1.189 | 1.059 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| london_fix_reversal×EUR_USD×SELL | 16 | 1.758 | 1.311 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |
| trendline_sweep×EUR_USD×SELL | 45 | 1.65 | 0.818 | stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2) |

## (v) pre-reg DRAFT §2b への追記提案 (親セッション用 — 本文書は pre-reg を直接編集しない)

> **⚠️ 2026-07-10 更新: 本節は pre-reg §2(ii) (first-touch EV スクリーン、スキャン結果観測前の a priori 改訂) の反映前の旧版。最終版の提案文は `ws3_round2_ev_screen_2026_07.md` §(v') を使用すること (通過 5/8、m=5、凍結 grid 込み)。以下は 1 次スクリーン時点の記録として保存。**

以下をそのまま `ws3-round2-explore-prereg-2026-07-10.md` の §2b として追記し、Status を 🔒 self-LOCK に更新することを提案する:

```markdown
## 2b. 候補セット (診断 2026-07-10 実行済み、m=8 — self-LOCK 対象、以後変更禁止)

診断: raw/bt-results/ws3_round2_scan_2026_07.{json,md} (§2 の選抜規則を機械適用:
N≥30 ∧ (ratio_h24≥1.3 ∪ 持続型(h96≥1.3 ∧ h96>h24))、m≤10 は非発動 (8≤10))

| # | cell | 軸 | 型 (固定) | 探索 ratio (h24→h96) | N | Primary horizon |
|---|---|---|---|---|---|---|
| 1 | sr_fib_confluence×GBP_USD×SELL | a | 持続 | 1.18→**1.66** | 95 | **h96** |
| 2 | vol_spike_mr×USD_JPY×BUY | a | 減衰 | **1.49**→1.38 | 39 | h24 |
| 3 | sr_fib_confluence×EUR_USD×SELL | a | 持続 | 1.36→**1.49** | 99 | **h96** |
| 4 | vsg_jpy_reversal×GBP_JPY×SELL | a | 減衰 | **1.48**→1.23 | 106 | h24 |
| 5 | turtle_soup×GBP_USD (pooled) | c | 持続 | 0.91→**1.41** | 40 | **h96** |
| 6 | dt_sr_channel_reversal×GBP_USD×SELL | a | 持続 | 0.97→**1.40** | 36 | **h96** |
| 7 | dt_sr_channel_reversal×GBP_JPY×BUY | a | 持続 | 0.97→**1.33** | 77 | **h96** |
| 8 | sr_fib_confluence×AUD_JPY×SELL | a | 減衰 | **1.32**→1.19 | 119 | h24 |

- 型と primary horizon は探索標本で固定 — OOS での horizon 選び直し禁止 (stage-1 と同一規律)
- 軸(b) 未走査ペア = EUR_GBP のみと機械確定したが、BT baseline が最小サンプルガード
  (<20 trades/365d) に抵触し entries=0 → 候補到達不能 (診断 md §(i) に記録)。
  よって本候補セットに新ペア由来セルは無い
- **裁定事項 (LOCK 前に確定)**: #5 turtle_soup×GBP_USD は水平 sweep 系と概念近接。
  診断 md の裁定 (stage-1 lin_reg_channel 前例と同型 = estimand 相違で候補維持) を
  採用するか、保守的に除外して m=7 とするかを LOCK 時に明記
- 除外の適用結果: stage-1 8 セル + 方向サブセル (12 cells N≥10) / dt_bb_rsi_mr 系統
  掃引 (9 cells) / lin_reg_channel / liquidity_sweep。H4 level・mtf_regime_switch
  SELL・T11 counter-USD は母集団に entry_type 不存在 (非該当)。trendline_sweep×
  EUR_USD は stage-1 #2 かつ §8.3(c) 経路限定として除外済み
- OOS 判定は §3 の通り (m=8 で BH-FDR q=0.10、point ratio≥1.2、OOS N≥30、
  型別 primary horizon 固定、ナイフエッジ3点検査)。OOS-1 窓 (2024-07-07〜2025-07-07)
  の再利用回数 = 2 回目 (round-1 の 8 セルと重複しない未判定セルのため有効)
```

**留意 (提案外の記述)**: 候補 8 のうち sr_fib_confluence×SELL が 3 ペアを占める — OOS PASS した場合も stage-2 では「同一戦略の SELL 側クラスタ」として barrier 設計を共通化するのが自然。dt_bb_rsi_mr の系統掃引 (bb_rsi falsified の保守的解釈で 9 セル除外、うち選抜規則を満たし得たセルは無し — 全セル ratio 表参照) に異議がある場合も LOCK 前に親セッションで裁定すること。
