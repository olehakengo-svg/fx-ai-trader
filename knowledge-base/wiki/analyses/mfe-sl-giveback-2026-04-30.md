# MFE → SL Give-back Forensic Report

- 生成 UTC: `20260430T110849Z`
- DB: `/Users/jg-n-012/test/fx-ai-trader/demo_trades.db` / window: 直近 30 日
- 除外: XAU (memory: feedback_exclude_xau)
- 不変条件: LIVE/Shadow 分離 / mafe_* 実測ベース / Bonferroni α=0.0125

## エグゼクティブサマリー
- 全体 N=474 (CLOSED, 非XAU)
- **LIVE (is_shadow=0)**: N=36, SL_HIT=11, TP_HIT=14, 高MFE→SL N=1 (2.8%)
  - SL_HIT 平均 mfe_r=0.192, avg giveback_r=1.631
- **Shadow (is_shadow=1)**: N=438, SL_HIT=213, TP_HIT=101, 高MFE→SL N=21 (4.8%)
  - SL_HIT 平均 mfe_r=0.255, avg giveback_r=1.572

## タグ定義
| タグ | 条件 | 推定原因 |
|---|---|---|
| G1 | mfe_r ≥ 0.8 ∧ pnl_r ≤ −0.8 | BE 閾値到達したのに BE 不発 (`_entry_atr` 喪失 or 閾値ハードコード) |
| G2 | mfe_r ≥ 0.8 ∧ −0.2 ≤ pnl_r ≤ 0.5 | BE 発火 → 反転 → BE 撤退 (trail 移行できず) |
| G3 | mfe_r ≥ 1.5 ∧ tp_progress < 0.7 | Tier2 trail 発火後も give back (trail 幅広すぎ) |
| G4 | tp_progress ≥ 0.8 ∧ SL_HIT | TP 寸前反転 (TP 距離が広すぎ) |

## LIVE (is_shadow=0)

### ペア別
| pair | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL | giveback_r |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| USD_JPY | 31 | 10 | 13 | 1 | 3.2% | 0.006 | 0.18 | 1.66 |
| GBP_USD | 4 | 1 | 0 | 0 | 0.0% | 0.000 | 0.31 | 1.31 |
| EUR_USD | 1 | 0 | 1 | 0 | 0.0% | 0.000 | 0.00 | 0.00 |

### 戦略別 (entry_type, family)
| entry_type | fam | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| bb_rsi_reversion | MR | 22 | 6 | 14 | 1 | 4.5% | 0.008 | 0.20 |
| mtf_reversal_confluence | MR | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| turtle_soup | MR | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| vol_surge_detector | BO | 1 | 1 | 0 | 0 | 0.0% | 0.000 | 0.03 |
| trend_rebound | MR | 2 | 1 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| dt_sr_channel_reversal | MR | 1 | 1 | 0 | 0 | 0.0% | 0.000 | 0.31 |
| vol_momentum_scalp | TF | 4 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| streak_reversal | MR | 1 | 1 | 0 | 0 | 0.0% | 0.000 | 0.47 |
| session_time_bias | SE | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| doji_breakout | UNKNOWN | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| vix_carry_unwind | SE | 1 | 1 | 0 | 0 | 0.0% | 0.000 | 0.10 |

### 時間帯別 (session)
| session | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |
|---|--:|--:|--:|--:|--:|--:|--:|
| Tokyo | 12 | 3 | 7 | 1 | 8.3% | 0.015 | 0.56 |
| London | 21 | 6 | 7 | 0 | 0.0% | 0.000 | 0.07 |
| NY | 3 | 2 | 0 | 0 | 0.0% | 0.000 | 0.01 |

### Top cell 一覧 (N≥10, sorted by LB95)
| cell (pair / type / sess / dir) | fam | N | SL | hMFE_SL | LB95 | avg mfe_r | giveback_r | tags |
|---|---|--:|--:|--:|--:|--:|--:|---|

### 個別 高MFE→SL トレード (mfe_r ≥ 0.8, top 30 by mfe_r)
| trade_id | pair | type | sess | dir | mfe_r | tp_prog | pnl_r | tags |
|---|---|---|---|---|--:|--:|--:|---|
| `020920a5-53a` | USD_JPY | bb_rsi_reversion | Tokyo | BUY | 1.20 | 0.67 | -1.03 | G1 |

### 対応策 (cell-level recommendations)
- N または LB95 の閾値を満たす cell なし

## Shadow (is_shadow=1)

### ペア別
| pair | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL | giveback_r |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| USD_JPY | 197 | 97 | 52 | 12 | 6.1% | 0.035 | 0.31 | 1.93 |
| EUR_USD | 95 | 51 | 10 | 6 | 6.3% | 0.029 | 0.21 | 1.25 |
| GBP_JPY | 15 | 11 | 1 | 1 | 6.7% | 0.012 | 0.30 | 1.37 |
| GBP_USD | 109 | 46 | 33 | 2 | 1.8% | 0.005 | 0.18 | 1.28 |
| EUR_JPY | 20 | 8 | 5 | 0 | 0.0% | 0.000 | 0.19 | 1.22 |
| EUR_GBP | 2 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 | 0.00 |

### 戦略別 (entry_type, family)
| entry_type | fam | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| doji_breakout | UNKNOWN | 4 | 3 | 0 | 3 | 75.0% | 0.301 | 2.00 |
| inducement_ob | UNKNOWN | 1 | 1 | 0 | 1 | 100.0% | 0.207 | 0.93 |
| sr_channel_reversal | MR | 28 | 20 | 0 | 4 | 14.3% | 0.057 | 0.34 |
| sr_break_retest | TF | 22 | 16 | 4 | 3 | 13.6% | 0.047 | 0.33 |
| ema_cross | MR | 6 | 2 | 3 | 1 | 16.7% | 0.030 | 0.75 |
| post_news_vol | UNKNOWN | 7 | 4 | 0 | 1 | 14.3% | 0.026 | 0.58 |
| engulfing_bb | TF | 23 | 12 | 5 | 2 | 8.7% | 0.024 | 0.24 |
| sr_fib_confluence | MR | 33 | 16 | 5 | 2 | 6.1% | 0.017 | 0.34 |
| vol_surge_detector | BO | 12 | 7 | 1 | 1 | 8.3% | 0.015 | 0.23 |
| stoch_trend_pullback | TF | 17 | 6 | 4 | 1 | 5.9% | 0.010 | 0.24 |
| ema_trend_scalp | TF | 88 | 47 | 14 | 2 | 2.3% | 0.006 | 0.20 |
| h1_fib_reversal | MR | 3 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| fib_reversal | MR | 49 | 12 | 30 | 0 | 0.0% | 0.000 | 0.10 |
| macdh_reversal | TF | 9 | 5 | 2 | 0 | 0.0% | 0.000 | 0.12 |
| bb_squeeze_breakout | BO | 17 | 11 | 0 | 0 | 0.0% | 0.000 | 0.10 |
| orb_trap | MR | 5 | 3 | 0 | 0 | 0.0% | 0.000 | 0.04 |
| dual_sr_bounce | MR | 3 | 1 | 1 | 0 | 0.0% | 0.000 | 0.09 |
| dt_sr_channel_reversal | MR | 16 | 4 | 1 | 0 | 0.0% | 0.000 | 0.24 |
| donchian_momentum_breakout | TF | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| xs_momentum | TF | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| dt_fib_reversal | MR | 10 | 4 | 3 | 0 | 0.0% | 0.000 | 0.10 |
| dt_bb_rsi_mr | MR | 17 | 6 | 10 | 0 | 0.0% | 0.000 | 0.12 |
| session_time_bias | SE | 2 | 1 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| ema200_trend_reversal | UNKNOWN | 17 | 9 | 5 | 0 | 0.0% | 0.000 | 0.10 |
| v_reversal | UNKNOWN | 1 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| bb_rsi_reversion | MR | 14 | 10 | 2 | 0 | 0.0% | 0.000 | 0.16 |
| eurgbp_daily_mr | UNKNOWN | 2 | 0 | 0 | 0 | 0.0% | 0.000 | 0.00 |
| intraday_seasonality | UNKNOWN | 6 | 1 | 4 | 0 | 0.0% | 0.000 | 0.11 |
| trend_rebound | MR | 2 | 1 | 1 | 0 | 0.0% | 0.000 | 0.00 |
| vol_spike_mr | UNKNOWN | 10 | 5 | 3 | 0 | 0.0% | 0.000 | 0.23 |
| squeeze_release_momentum | UNKNOWN | 3 | 2 | 1 | 0 | 0.0% | 0.000 | 0.29 |
| liquidity_sweep | UNKNOWN | 1 | 1 | 0 | 0 | 0.0% | 0.000 | 0.11 |
| vol_momentum_scalp | TF | 3 | 1 | 1 | 0 | 0.0% | 0.000 | 0.30 |
| wick_imbalance_reversion | MR | 5 | 2 | 1 | 0 | 0.0% | 0.000 | 0.33 |

### 時間帯別 (session)
| session | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |
|---|--:|--:|--:|--:|--:|--:|--:|
| Tokyo | 129 | 56 | 43 | 9 | 7.0% | 0.037 | 0.30 |
| NY | 126 | 63 | 30 | 6 | 4.8% | 0.022 | 0.27 |
| London | 183 | 94 | 28 | 6 | 3.3% | 0.015 | 0.22 |

### Top cell 一覧 (N≥10, sorted by LB95)
| cell (pair / type / sess / dir) | fam | N | SL | hMFE_SL | LB95 | avg mfe_r | giveback_r | tags |
|---|---|--:|--:|--:|--:|--:|--:|---|
| USD_JPY / fib_reversal / Tokyo / SELL | MR | 20 | 2 | 0 | 0.000 | 0.07 | 1.29 | G0=2 |
| GBP_USD / ema_trend_scalp / London / SELL | TF | 10 | 6 | 0 | 0.000 | 0.28 | 1.36 | G0=6 |
| EUR_USD / ema_trend_scalp / London / SELL | TF | 13 | 6 | 0 | 0.000 | 0.14 | 1.17 | G0=6 |
| GBP_USD / ema_trend_scalp / London / BUY | TF | 12 | 5 | 0 | 0.000 | 0.00 | 1.05 | G0=5 |

### 個別 高MFE→SL トレード (mfe_r ≥ 0.8, top 30 by mfe_r)
| trade_id | pair | type | sess | dir | mfe_r | tp_prog | pnl_r | tags |
|---|---|---|---|---|--:|--:|--:|---|
| `dd640679-bb3` | USD_JPY | doji_breakout | NY | BUY | 2.64 | 0.25 | -3.02 | G1,G3 |
| `f0927986-fe5` | EUR_USD | ema_trend_scalp | NY | BUY | 2.05 | 0.74 | -1.05 | G1 |
| `ec2bd5c4-b8c` | USD_JPY | doji_breakout | NY | BUY | 2.03 | 0.59 | -1.11 | G1,G3 |
| `94c6a785-da3` | USD_JPY | post_news_vol | Tokyo | SELL | 1.97 | 0.50 | -1.00 | G1,G3 |
| `5faaf43b-e00` | GBP_JPY | ema_cross | London | BUY | 1.50 | 0.83 | -1.05 | G1,G4 |
| `507afd6e-051` | USD_JPY | engulfing_bb | London | BUY | 1.35 | 0.40 | -1.11 | G1 |
| `f08d87a4-f46` | USD_JPY | doji_breakout | Tokyo | SELL | 1.33 | 0.55 | -1.00 | G1 |
| `516aec89-e4d` | EUR_USD | sr_channel_reversal | London | SELL | 1.29 | 0.74 | -1.00 | G1 |
| `49adbc60-b39` | USD_JPY | sr_break_retest | Tokyo | BUY | 1.28 | 0.99 | -3.26 | G1,G4 |
| `0a7b6b42-175` | USD_JPY | sr_break_retest | Tokyo | BUY | 1.12 | 0.59 | -5.87 | G1 |
| `2f218940-ff3` | EUR_USD | sr_fib_confluence | NY | BUY | 1.03 | 0.49 | -1.07 | G1 |
| `d882d383-4f5` | GBP_USD | vol_surge_detector | Tokyo | BUY | 0.98 | 0.41 | -1.10 | G1 |
| `c2325280-8da` | USD_JPY | engulfing_bb | Tokyo | BUY | 0.98 | 0.41 | -1.05 | G1 |
| `c4447cc0-6c2` | USD_JPY | sr_channel_reversal | Tokyo | BUY | 0.93 | 0.56 | -1.33 | G1 |
| `a886f0f2-d71` | USD_JPY | inducement_ob | London | BUY | 0.93 | 0.39 | -1.00 | G1 |
| `e2c10036-8b0` | GBP_USD | ema_trend_scalp | NY | BUY | 0.89 | 0.43 | -1.07 | G1 |
| `3aec31e1-297` | EUR_USD | sr_channel_reversal | London | SELL | 0.86 | 0.37 | -1.03 | G1 |
| `9a8f0e88-850` | EUR_USD | sr_fib_confluence | London | SELL | 0.86 | 0.37 | -1.00 | G1 |
| `c172aded-6f2` | USD_JPY | stoch_trend_pullback | Tokyo | SELL | 0.83 | 0.45 | -2.07 | G1 |
| `c310a458-b6e` | EUR_USD | sr_channel_reversal | NY | BUY | 0.81 | 0.45 | -1.03 | G1 |
| `1a60a0b7-afd` | USD_JPY | sr_break_retest | Tokyo | SELL | 0.80 | 0.75 | -1.06 | G1 |

### 対応策 (cell-level recommendations)
- N または LB95 の閾値を満たす cell なし

## グローバル構造所見 (cross-cell)
- 高MFE→SL トレード総数 (Live+Shadow): **22**
- タグ分布 (高MFE→SL のみ): {'G1': 22, 'G3': 3, 'G4': 2}
- **G1 (BE-Skip) 支配率 = 100%** — BE 発火閾値到達後そのまま SL に至るトレードが支配的

### ペア × 退出理由 × MFE 分布
| pair | close_reason | N | avg mfe_r | max mfe_r | avg tp_progress |
|---|---|--:|--:|--:|--:|
| EUR_JPY | TP_HIT | 5 | 1.75 | 1.87 | 1.04 |
| EUR_JPY | TIME_DECAY_EXIT | 7 | 0.65 | 1.49 | 0.42 |
| EUR_JPY | SL_HIT | 8 | 0.19 | 0.66 | 0.08 |
| EUR_USD | TP_HIT | 11 | 5.48 | 45.1 | 3.21 |
| EUR_USD | SL_HIT | 51 | 0.21 | 2.05 | 0.1 |
| EUR_USD | MAX_HOLD_TIME | 7 | 0.71 | 1.48 | 0.34 |
| EUR_USD | TIME_DECAY_EXIT | 22 | 0.58 | 1.38 | 0.33 |
| EUR_USD | SIGNAL_REVERSE | 5 | 0.35 | 1.13 | 0.2 |
| GBP_JPY | SL_HIT | 11 | 0.3 | 1.5 | 0.14 |
| GBP_USD | TP_HIT | 33 | 1.92 | 5.36 | 1.1 |
| GBP_USD | MAX_HOLD_TIME | 4 | 1.5 | 2.57 | 0.65 |
| GBP_USD | TIME_DECAY_EXIT | 17 | 0.55 | 1.22 | 0.34 |
| GBP_USD | SIGNAL_REVERSE | 11 | 0.21 | 1.08 | 0.12 |
| GBP_USD | SL_HIT | 47 | 0.18 | 0.98 | 0.08 |
| USD_JPY | TP_HIT | 65 | 2.07 | 20.92 | 1.11 |
| USD_JPY | MAX_HOLD_TIME | 15 | 1.09 | 2.95 | 0.51 |
| USD_JPY | SL_HIT | 107 | 0.3 | 2.64 | 0.14 |
| USD_JPY | TIME_DECAY_EXIT | 32 | 0.68 | 2.24 | 0.34 |
| USD_JPY | SIGNAL_REVERSE | 8 | 0.1 | 0.53 | 0.05 |

### 高MFE 非TP・非SL exit (50件)
「含み益あったが TP 取れず時間/シグナルで撤退」 — give back の隠れた母集団
| trade_id | pair | type | reason | mfe_r | tp_prog | pnl_r |
|---|---|---|---|--:|--:|--:|
| `9595a54f-05a` | USD_JPY | doji_breakout | MAX_HOLD_TIME | 2.95 | 0.84 | 2.16 |
| `1e2e3485-6ff` | GBP_USD | ema_trend_scalp | MAX_HOLD_TIME | 2.57 | 0.96 | 1.89 |
| `1759b797-03d` | USD_JPY | vol_spike_mr | TIME_DECAY_EXIT | 2.24 | 0.76 | -0.02 |
| `5bc05c62-df4` | USD_JPY | ema_trend_scalp | TIME_DECAY_EXIT | 2.04 | 0.95 | -0.13 |
| `f61ce9bc-fde` | USD_JPY | sr_fib_confluence | MAX_HOLD_TIME | 1.91 | 0.78 | 1.7 |
| `36788da7-048` | GBP_USD | engulfing_bb | MAX_HOLD_TIME | 1.8 | 0.76 | 1.07 |
| `9259306d-108` | USD_JPY | stoch_trend_pullback | MAX_HOLD_TIME | 1.78 | 0.83 | 0.78 |
| `3dab4627-922` | GBP_USD | sr_break_retest | WEEKEND_CLOSE | 1.77 | 0.86 | 0.48 |
| `d18956e3-ae1` | USD_JPY | vol_surge_detector | MAX_HOLD_TIME | 1.68 | 0.87 | 1.03 |
| `47a88633-a7d` | GBP_USD | ema200_trend_reversal | MAX_HOLD_TIME | 1.62 | 0.9 | 0.91 |
| `79f79420-2d8` | USD_JPY | stoch_trend_pullback | MAX_HOLD_TIME | 1.53 | 0.77 | 0.13 |
| `91f4eb36-53c` | EUR_JPY | dt_fib_reversal | TIME_DECAY_EXIT | 1.49 | 0.9 | -0.01 |
| `71d31b0e-547` | EUR_USD | ema_trend_scalp | MAX_HOLD_TIME | 1.48 | 0.52 | 1.29 |
| `e1b905dd-0b4` | USD_JPY | bb_rsi_reversion | TIME_DECAY_EXIT | 1.47 | 0.52 | -0.2 |
| `52a5908b-adc` | USD_JPY | stoch_trend_pullback | TIME_DECAY_EXIT | 1.46 | 0.89 | -0.08 |
| `a7f05c48-950` | EUR_USD | ema_trend_scalp | TIME_DECAY_EXIT | 1.38 | 0.47 | -0.29 |
| `992ed423-a66` | USD_JPY | ema_trend_scalp | MAX_HOLD_TIME | 1.33 | 0.74 | 0.33 |
| `094fa4c3-120` | USD_JPY | sr_fib_confluence | MAX_HOLD_TIME | 1.31 | 0.67 | 1.03 |
| `9a919aed-d20` | EUR_USD | engulfing_bb | TIME_DECAY_EXIT | 1.27 | 0.55 | -0.02 |
| `395d19bd-c46` | EUR_USD | bb_squeeze_breakout | MAX_HOLD_TIME | 1.23 | 0.46 | 0.8 |
| `bf6bdcd1-096` | GBP_USD | ema_trend_scalp | TIME_DECAY_EXIT | 1.22 | 0.45 | -0.07 |
| `3b0f18e2-808` | GBP_JPY | wick_imbalance_reversion | TIME_DECAY_EXIT | 1.21 | 0.46 | -0.09 |
| `59a2ba01-25a` | USD_JPY | ema_trend_scalp | TIME_DECAY_EXIT | 1.19 | 0.56 | -0.03 |
| `5555b2a4-eda` | GBP_USD | ema_trend_scalp | TIME_DECAY_EXIT | 1.15 | 0.41 | -0.1 |
| `c681e854-27a` | USD_JPY | sr_channel_reversal | TIME_DECAY_EXIT | 1.15 | 0.64 | -0.57 |

### 構造的優先順位付き対応策 (ユーザー判断のための提示)
1. **[R3] BE 発火失敗の構造的バグ調査 (`_entry_atr` 喪失 + OANDA mirror revert)**
   - 根拠: 高MFE→SL の 100% が G1 タグ。pnl_r ≤ -0.8 着地は BE が一度も適用されていない証拠。原因候補: (a) `_entry_atr` がプロセス再起動でロストし fallback ATR がトレード実 ATR と乖離、(b) `modify_sl_sync` が shadow trade で False を返し SL が revert (modules/demo_trader.py:1758-1760)
   - 適用箇所: `modules/demo_trader.py:1706-1755 + 1758`
   - 期待効果: shadow trade で modify_sl_sync をスキップ + entry_atr を trades 表に永続化 → BE 発火が in-memory 状態に依存しなくなる
2. **[R2] Tier2 trail 幅の短縮 (ATR×0.5 → ATR×0.3)**
   - 根拠: G3 タグ 14%: mfe_r ≥ 1.5 到達後も give back。trail 幅 ATR×0.5 が広すぎて反転で容易に SL される
   - 適用箇所: `modules/demo_trader.py:1737 (`_ts_trail = _entry_atr_be * 0.5`)`
   - 期待効果: trail SL 損益保護 +30〜50% 推定 (要 BT 確認)

## 不変条件チェック
- live_shadow_separated: True
- xau_excluded: True
- code_deduction_avoided: all metrics from mafe_* SQL fields
- spread_basis: entry_price ベースの sl_dist 距離で正規化
