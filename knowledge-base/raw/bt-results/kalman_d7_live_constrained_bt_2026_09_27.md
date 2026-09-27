# kalman_d7_po_dn_flip — live 制約付き BT (Python port、診断専用) 2026-09-27

- data: `/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m.parquet` (Massive USD_JPY M15、TV 側は OANDA feed = ベンダー差あり)
- window: 2025-07-01 → 2026-05-19 23:59:59 (warmup 2025-04-01), bars in window = 21842
- friction: 2.14 pip / trade (USD_JPY RT、spread + slippage 込み) を **slippage 無しの水準差**から引く。WR / PF / EV は **net** (摩擦後)。harness 比較のみ **TV 基準** (slippage 1 tick + commission 0.002%×2、PF は equity 10% 逐次サイジングの cash)
- C2 (金曜 21:45Z クローズ) は **冬時間 = 21:45 bar open で執行 / 夏時間 = 閉場後なので日曜初 bar open で fill (`WEEKEND_CLOSE_SUNDAY_FILL`、週末ギャップ込み)**
- `winner ≤8h` は **壁時計 hold_sec ≤ 28,800s** (live C1 と同基準。bars 数ではない — 週末跨ぎの bar は壁時計と乖離する)
- ラベル: 走 0 = 宣言 BT 再現 (2 変種) / 走 0′〜4 = **C0 近似 + intrabar 順序近似** / 走 5 = **C6 近似 (参考値)**
- window 内 raw entry signal = 92 (po_up_start 712)。1 建玉制 (Pine pyramiding=0) なので N は exit 長で変わる

> 🔴 **HARNESS 未検証**: 走 0 の既定 2 変種も flip 定義の識別候補 5 つも canon (N=46 / WR 23.91% / PF 3.866 / avg winner bars 458) を ±10% で再現しない。task 文書「走 0 が現行 BT を再現できないまま制約付きの数字を出さない」に従い、**以下の全数値は引用禁止 — packet に載せるのは分解の順位・向き・exit 種別の構造のみ**。要因: (1) v17 canon Pine がリポジトリに無い (TV slot は 2026-05-21 上書き、TV は本セッションで接続不可) → flip exit の定義は推定、(2) データが Massive (TV は OANDA feed)、(3) EMA 初期化 / percentile 実装差。

## Harness 検証 (走 0 vs canon N=46 / WR 23.91% / PF 3.866 / avg winner bars 458、±10%)

| 走 0 変種 | 指標 | canon | port | ok |
|---|---|---|---|---|
| walk0_flip_canon | n | 46 | 60 | ❌ |
| walk0_flip_canon | wr | 0.2391 | 0.1833 | ❌ |
| walk0_flip_canon | pf | 3.8660 | 1.9872 | ❌ |
| walk0_flip_canon | avg_win_bars | 458 | 372.8182 | ❌ |
| walk0_flip_canon | **all** | | | ❌ |
| walk0_tp5_decl | n | 46 | 74 | ❌ |
| walk0_tp5_decl | wr | 0.2391 | 0.2973 | ❌ |
| walk0_tp5_decl | pf | 3.8660 | 1.4885 | ❌ |
| walk0_tp5_decl | avg_win_bars | 458 | 37.0000 | ❌ |
| walk0_tp5_decl | **all** | | | ❌ |

### flip exit 定義の識別 (canon Pine 不在のため。entry / SL 1.5×ATR / 480 cap は固定、TV コスト基準)

| flip 定義 | 説明 | N | WR (tv) | PF (tv) | avg win bars | EV tv p/t | payoff (net) | exits | harness |
|---|---|---|---|---|---|---|---|---|---|
| perfect_dn | EMA200 > EMA75 > EMA25 (完全下順) — 既定 | 60 | 18.3% | 1.99 | 373 | 13.66 | 8.03 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 | ❌ |
| not_perfect_up | perfect_up が偽になる (close < EMA25 含む) | 92 | 20.7% | 0.78 | 26 | -1.63 | 3.58 | PO_DN_FLIP 78, SL_HIT 14 | ❌ |
| close_lt_ema75 | close < EMA75 | 77 | 23.4% | 2.00 | 107 | 9.80 | 5.75 | PO_DN_FLIP 50, SL_HIT 27 | ❌ |
| close_lt_ema200 | close < EMA200 | 65 | 21.5% | 2.25 | 243 | 15.39 | 7.35 | SL_HIT 39, PO_DN_FLIP 26 | ❌ |
| ema25_lt_ema75 | EMA25 < EMA75 | 67 | 22.4% | 2.52 | 252 | 19.57 | 7.90 | SL_HIT 49, PO_DN_FLIP 18 | ❌ |

## 走 0〜5 — bar 内順序仮定 = `adverse_first` (既定・保守側)

| 走 | N | WR | Wilson lo | PF (net) | EV net p/t | Σ net p | avg win p | avg loss p | payoff | winner ≤8h | winner hold bars med (p25–p75) | loser hold bars med | exit 種別 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| walk0_flip_canon | 60 | 18.3% | 10.6% | 1.80 | 12.34 | 740.6 | 151.2 | -18.8 | 8.03 | 0% | 330 (294–466) | 9 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 |
| walk0_tp5_decl | 74 | 29.7% | 20.5% | 1.34 | 4.50 | 332.7 | 59.3 | -18.7 | 3.17 | 45% | 30 (15–52) | 6 | SL_HIT 52, TP_HIT 22 |
| walk0p_C0 | 80 | 21.2% | 13.7% | 1.06 | 0.67 | 53.3 | 55.8 | -14.2 | 3.93 | 65% | 18 (15–30) | 4 | SL_HIT 63, TP_HIT 17 |
| walk1_C0+C1 | 81 | 27.2% | 18.7% | 1.17 | 1.75 | 141.8 | 43.5 | -13.8 | 3.15 | 86% | 26 (15–33) | 4 | SL_HIT 58, TP_HIT 13, MAX_HOLD_TIME 10 |
| walk2_+C2 | 81 | 27.2% | 18.7% | 1.13 | 1.34 | 108.8 | 42.0 | -13.8 | 3.04 | 91% | 25 (15–33) | 4 | SL_HIT 58, TP_HIT 12, MAX_HOLD_TIME 9, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk3_+C3C4 | 85 | 23.5% | 15.8% | 0.54 | -3.83 | -325.9 | 19.1 | -10.9 | 1.75 | 95% | 6 (4–7) | 4 | SL_HIT 47, BE 18, TRAIL 17, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk4_+C5 | 85 | 23.5% | 15.8% | 0.54 | -3.83 | -325.9 | 19.1 | -10.9 | 1.75 | 95% | 6 (4–7) | 4 | SL_HIT 47, BE 18, TRAIL 17, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk5_+C6approx | 92 | 19.6% | 12.7% | 0.53 | -3.22 | -296.5 | 18.9 | -8.6 | 2.20 | 94% | 5 (4–6) | 2 | SIGNAL_REVERSE_APPROX 32, SL_HIT 26, BE 16, TRAIL 15, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |

winner / loser 別 exit 種別:

| 走 | winners | losers |
|---|---|---|
| walk0_flip_canon | PO_DN_FLIP 8, CANON_CAP_480 3 | SL_HIT 48, PO_DN_FLIP 1 |
| walk0_tp5_decl | TP_HIT 22 | SL_HIT 52 |
| walk0p_C0 | TP_HIT 17 | SL_HIT 63 |
| walk1_C0+C1 | TP_HIT 13, MAX_HOLD_TIME 9 | SL_HIT 58, MAX_HOLD_TIME 1 |
| walk2_+C2 | TP_HIT 12, MAX_HOLD_TIME 8, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 58, MAX_HOLD_TIME 1 |
| walk3_+C3C4 | TRAIL 17, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 47, BE 18 |
| walk4_+C5 | TRAIL 17, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 47, BE 18 |
| walk5_+C6approx | TRAIL 15, TP_HIT 1, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 | SIGNAL_REVERSE_APPROX 32, SL_HIT 26, BE 16 |

限界分解 (走 0′ に overlay を単独で載せる、順序 = `adverse_first`):

| 構成 | N | WR | PF (net) | EV net p/t | Σ net p | winner ≤8h | exit 種別 |
|---|---|---|---|---|---|---|---|
| marg_C1_only | 81 | 27.2% | 1.17 | 1.75 | 141.8 | 86% | SL_HIT 58, TP_HIT 13, MAX_HOLD_TIME 10 |
| marg_C2_only | 80 | 22.5% | 1.06 | 0.67 | 53.4 | 67% | SL_HIT 62, TP_HIT 16, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| marg_C3C4_only | 85 | 22.4% | 0.56 | -3.84 | -326.0 | 95% | SL_HIT 48, BE 18, TRAIL 17, TP_HIT 2 |
| marg_C5_only | 84 | 20.2% | 1.15 | 1.50 | 125.6 | 76% | SL_HIT 57, TP_HIT 17, TIME_DECAY_EXIT 10 |
| marg_C6approx_only | 92 | 10.9% | 0.62 | -3.19 | -293.9 | 80% | SIGNAL_REVERSE_APPROX 49, SL_HIT 33, TP_HIT 10 |
| walk4b_C0+C1+C2+C5_noC3C4 | 84 | 26.2% | 1.18 | 1.75 | 147.2 | 91% | SL_HIT 57, TP_HIT 14, MAX_HOLD_TIME 6, TIME_DECAY_EXIT 5, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |

## 走 0〜5 — bar 内順序仮定 = `favorable_first` (感度)

| 走 | N | WR | Wilson lo | PF (net) | EV net p/t | Σ net p | avg win p | avg loss p | payoff | winner ≤8h | winner hold bars med (p25–p75) | loser hold bars med | exit 種別 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| walk0_flip_canon | 60 | 18.3% | 10.6% | 1.80 | 12.34 | 740.6 | 151.2 | -18.8 | 8.03 | 0% | 330 (294–466) | 9 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 |
| walk0_tp5_decl | 74 | 31.1% | 21.7% | 1.41 | 5.25 | 388.8 | 58.5 | -18.8 | 3.12 | 48% | 28 (14–52) | 6 | SL_HIT 51, TP_HIT 23 |
| walk0p_C0 | 80 | 22.5% | 14.7% | 1.11 | 1.25 | 100.3 | 54.7 | -14.3 | 3.84 | 67% | 17 (12–29) | 4 | SL_HIT 62, TP_HIT 18 |
| walk1_C0+C1 | 81 | 28.4% | 19.7% | 1.24 | 2.33 | 188.8 | 43.1 | -13.8 | 3.11 | 87% | 24 (13–33) | 4 | SL_HIT 57, TP_HIT 14, MAX_HOLD_TIME 10 |
| walk2_+C2 | 81 | 28.4% | 19.7% | 1.19 | 1.92 | 155.8 | 41.7 | -13.8 | 3.01 | 91% | 23 (13–33) | 4 | SL_HIT 57, TP_HIT 13, MAX_HOLD_TIME 9, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk3_+C3C4 | 85 | 14.1% | 8.3% | 0.21 | -5.87 | -499.2 | 11.1 | -8.7 | 1.28 | 92% | 4 (3–6) | 3 | SL_HIT 47, BE 26, TRAIL 11, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk4_+C5 | 85 | 14.1% | 8.3% | 0.21 | -5.87 | -499.2 | 11.1 | -8.7 | 1.28 | 92% | 4 (3–6) | 3 | SL_HIT 47, BE 26, TRAIL 11, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| walk5_+C6approx | 92 | 10.9% | 6.0% | 0.20 | -4.89 | -449.6 | 11.2 | -6.8 | 1.63 | 90% | 4 (3–6) | 2 | SIGNAL_REVERSE_APPROX 32, SL_HIT 26, BE 24, TRAIL 9, WEEKEND_CLOSE_SUNDAY_FILL 1 |

winner / loser 別 exit 種別:

| 走 | winners | losers |
|---|---|---|
| walk0_flip_canon | PO_DN_FLIP 8, CANON_CAP_480 3 | SL_HIT 48, PO_DN_FLIP 1 |
| walk0_tp5_decl | TP_HIT 23 | SL_HIT 51 |
| walk0p_C0 | TP_HIT 18 | SL_HIT 62 |
| walk1_C0+C1 | TP_HIT 14, MAX_HOLD_TIME 9 | SL_HIT 57, MAX_HOLD_TIME 1 |
| walk2_+C2 | TP_HIT 13, MAX_HOLD_TIME 8, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 57, MAX_HOLD_TIME 1 |
| walk3_+C3C4 | TRAIL 11, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 47, BE 26 |
| walk4_+C5 | TRAIL 11, WEEKEND_CLOSE_SUNDAY_FILL 1 | SL_HIT 47, BE 26 |
| walk5_+C6approx | TRAIL 9, WEEKEND_CLOSE_SUNDAY_FILL 1 | SIGNAL_REVERSE_APPROX 32, SL_HIT 26, BE 24 |

限界分解 (走 0′ に overlay を単独で載せる、順序 = `favorable_first`):

| 構成 | N | WR | PF (net) | EV net p/t | Σ net p | winner ≤8h | exit 種別 |
|---|---|---|---|---|---|---|---|
| marg_C1_only | 81 | 28.4% | 1.24 | 2.33 | 188.8 | 87% | SL_HIT 57, TP_HIT 14, MAX_HOLD_TIME 10 |
| marg_C2_only | 80 | 23.8% | 1.12 | 1.25 | 100.4 | 68% | SL_HIT 61, TP_HIT 17, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |
| marg_C3C4_only | 85 | 12.9% | 0.20 | -6.26 | -532.3 | 100% | SL_HIT 48, BE 26, TRAIL 11 |
| marg_C5_only | 84 | 21.4% | 1.21 | 2.06 | 172.6 | 78% | SL_HIT 56, TP_HIT 18, TIME_DECAY_EXIT 10 |
| marg_C6approx_only | 92 | 12.0% | 0.67 | -2.68 | -246.9 | 82% | SIGNAL_REVERSE_APPROX 49, SL_HIT 32, TP_HIT 11 |
| walk4b_C0+C1+C2+C5_noC3C4 | 84 | 27.4% | 1.24 | 2.31 | 194.2 | 91% | SL_HIT 56, TP_HIT 15, MAX_HOLD_TIME 6, TIME_DECAY_EXIT 5, WEEKEND_CLOSE 1, WEEKEND_CLOSE_SUNDAY_FILL 1 |

## C0 感度 (BT 側 what-if、走 0′〜4 を再集計。live 実測率は marker 付き live N 蓄積後に差し替え)

### 順序仮定 = `adverse_first`

| what-if | 走 | N | WR | PF | EV net | Σ net | winner ≤8h | SL 分岐 | flags |
|---|---|---|---|---|---|---|---|---|---|
| base | walk0p_C0 | 80 | 21.2% | 1.06 | 0.67 | 53.3 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk1_C0+C1 | 81 | 27.2% | 1.17 | 1.75 | 141.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk2_+C2 | 81 | 27.2% | 1.13 | 1.34 | 108.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| base | walk4_+C5 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk0p_C0 | 80 | 21.2% | 1.06 | 0.67 | 53.3 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk1_C0+C1 | 81 | 27.2% | 1.17 | 1.75 | 141.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk2_+C2 | 81 | 27.2% | 1.13 | 1.34 | 108.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk4_+C5 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| ii_sr_priority | walk0p_C0 | 68 | 33.8% | 1.34 | 4.39 | 298.3 | 52% | {'sr': 67, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 32, 'lowliq': 22, 'rn': 10} |
| ii_sr_priority | walk1_C0+C1 | 73 | 38.4% | 1.21 | 2.47 | 180.3 | 89% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk2_+C2 | 73 | 38.4% | 1.20 | 2.30 | 167.6 | 93% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk3_+C3C4 | 77 | 29.9% | 0.59 | -3.85 | -296.1 | 96% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| ii_sr_priority | walk4_+C5 | 77 | 29.9% | 0.61 | -3.50 | -269.5 | 96% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| iii_no_clamp | walk0p_C0 | 80 | 21.2% | 1.06 | 0.67 | 53.3 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk1_C0+C1 | 81 | 27.2% | 1.17 | 1.75 | 141.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk2_+C2 | 81 | 27.2% | 1.13 | 1.34 | 108.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iii_no_clamp | walk4_+C5 | 85 | 23.5% | 0.54 | -3.83 | -325.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iv_no_lowliq | walk0p_C0 | 80 | 21.2% | 1.11 | 1.21 | 97.0 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk1_C0+C1 | 81 | 27.2% | 1.24 | 2.26 | 182.7 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk2_+C2 | 81 | 27.2% | 1.19 | 1.85 | 149.7 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk3_+C3C4 | 85 | 23.5% | 0.55 | -3.60 | -306.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk4_+C5 | 85 | 23.5% | 0.55 | -3.60 | -306.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| v_mtf_1p3 | walk0p_C0 | 80 | 20.0% | 1.25 | 2.87 | 229.5 | 44% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk1_C0+C1 | 81 | 27.2% | 1.27 | 2.73 | 220.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk2_+C2 | 81 | 27.2% | 1.23 | 2.32 | 187.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.84 | -326.2 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| v_mtf_1p3 | walk4_+C5 | 85 | 23.5% | 0.54 | -3.84 | -326.2 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vi_no_rn | walk0p_C0 | 80 | 21.2% | 1.08 | 0.85 | 68.3 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk1_C0+C1 | 81 | 27.2% | 1.20 | 1.94 | 156.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk2_+C2 | 81 | 27.2% | 1.15 | 1.53 | 123.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.86 | -328.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vi_no_rn | walk4_+C5 | 85 | 23.5% | 0.54 | -3.86 | -328.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vii_no_broker_tp | walk0p_C0 | 80 | 20.0% | 1.15 | 1.72 | 137.8 | 50% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk1_C0+C1 | 81 | 27.2% | 1.21 | 2.14 | 173.6 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk2_+C2 | 81 | 27.2% | 1.17 | 1.74 | 140.6 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk3_+C3C4 | 85 | 23.5% | 0.54 | -3.84 | -326.2 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vii_no_broker_tp | walk4_+C5 | 85 | 23.5% | 0.54 | -3.84 | -326.2 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |

### 順序仮定 = `favorable_first`

| what-if | 走 | N | WR | PF | EV net | Σ net | winner ≤8h | SL 分岐 | flags |
|---|---|---|---|---|---|---|---|---|---|
| base | walk0p_C0 | 80 | 22.5% | 1.11 | 1.25 | 100.3 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk1_C0+C1 | 81 | 28.4% | 1.24 | 2.33 | 188.8 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk2_+C2 | 81 | 28.4% | 1.19 | 1.92 | 155.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| base | walk4_+C5 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk0p_C0 | 80 | 22.5% | 1.11 | 1.25 | 100.3 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk1_C0+C1 | 81 | 28.4% | 1.24 | 2.33 | 188.8 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk2_+C2 | 81 | 28.4% | 1.19 | 1.92 | 155.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk4_+C5 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| ii_sr_priority | walk0p_C0 | 68 | 35.3% | 1.40 | 5.10 | 346.8 | 54% | {'sr': 67, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 32, 'lowliq': 22, 'rn': 10} |
| ii_sr_priority | walk1_C0+C1 | 73 | 39.7% | 1.27 | 3.13 | 228.8 | 90% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk2_+C2 | 73 | 39.7% | 1.26 | 2.96 | 216.1 | 93% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk3_+C3C4 | 77 | 14.3% | 0.19 | -6.78 | -522.2 | 91% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| ii_sr_priority | walk4_+C5 | 77 | 14.3% | 0.20 | -6.44 | -495.6 | 91% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| iii_no_clamp | walk0p_C0 | 80 | 22.5% | 1.11 | 1.25 | 100.3 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk1_C0+C1 | 81 | 28.4% | 1.24 | 2.33 | 188.8 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk2_+C2 | 81 | 28.4% | 1.19 | 1.92 | 155.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iii_no_clamp | walk4_+C5 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iv_no_lowliq | walk0p_C0 | 80 | 22.5% | 1.17 | 1.78 | 142.3 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk1_C0+C1 | 81 | 28.4% | 1.30 | 2.81 | 228.0 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk2_+C2 | 81 | 28.4% | 1.26 | 2.41 | 195.0 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk3_+C3C4 | 85 | 14.1% | 0.22 | -5.64 | -479.3 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk4_+C5 | 85 | 14.1% | 0.22 | -5.64 | -479.3 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| v_mtf_1p3 | walk0p_C0 | 80 | 20.0% | 1.25 | 2.87 | 229.5 | 44% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk1_C0+C1 | 81 | 27.2% | 1.27 | 2.73 | 220.8 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk2_+C2 | 81 | 27.2% | 1.23 | 2.32 | 187.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| v_mtf_1p3 | walk4_+C5 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vi_no_rn | walk0p_C0 | 80 | 22.5% | 1.13 | 1.44 | 115.3 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk1_C0+C1 | 81 | 28.4% | 1.26 | 2.52 | 203.8 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk2_+C2 | 81 | 28.4% | 1.22 | 2.11 | 170.8 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.90 | -501.3 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vi_no_rn | walk4_+C5 | 85 | 14.1% | 0.21 | -5.90 | -501.3 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vii_no_broker_tp | walk0p_C0 | 80 | 21.2% | 1.21 | 2.39 | 191.3 | 53% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk1_C0+C1 | 81 | 28.4% | 1.28 | 2.80 | 227.1 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk2_+C2 | 81 | 28.4% | 1.24 | 2.40 | 194.1 | 91% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vii_no_broker_tp | walk4_+C5 | 85 | 14.1% | 0.21 | -5.87 | -499.2 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
