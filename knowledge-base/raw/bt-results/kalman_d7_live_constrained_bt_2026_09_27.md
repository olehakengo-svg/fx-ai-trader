# kalman_d7_po_dn_flip — live 制約付き BT (Python port、診断専用) 2026-09-27

- data: `/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m.parquet` (Massive USD_JPY M15、TV 側は OANDA feed = ベンダー差あり)
- window: 2025-07-01 → 2026-05-19 23:59:59 (warmup 2025-04-01), bars in window = 21842
- friction: 2.14 pip / trade (USD_JPY RT)。WR / PF / EV は **net** (摩擦後)。harness 比較のみ **TV コスト基準** (commission 0.002%×2 ≈ 0.6p + slippage 1 tick) — canon の数字は TV strategy() のコストを含む
- `winner ≤8h` は **壁時計 hold_sec ≤ 28,800s** (live C1 と同基準。bars 数ではない — 週末跨ぎの bar は壁時計と乖離する)
- ラベル: 走 0 = 宣言 BT 再現 (2 変種) / 走 0′〜4 = **C0 近似 + intrabar 順序近似** / 走 5 = **C6 近似 (参考値)**
- window 内 raw entry signal = 92 (po_up_start 712)。1 建玉制 (Pine pyramiding=0) なので N は exit 長で変わる

> 🔴 **HARNESS 未検証**: 走 0 のどの変種も canon (N=46 / WR 23.91% / PF 3.866 / avg winner bars 458) を ±10% で再現しない。task 文書「走 0 が現行 BT を再現できないまま制約付きの数字を出さない」に従い、**以下の全数値は引用禁止 — packet に載せるのは分解の順位・向き・exit 種別の構造のみ**。要因: (1) v17 canon Pine がリポジトリに無い (TV slot は 2026-05-21 上書き、TV は本セッションで接続不可) → flip exit の定義は推定、(2) データが Massive (TV は OANDA feed)、(3) EMA 初期化 / percentile 実装差。

## Harness 検証 (走 0 vs canon N=46 / WR 23.91% / PF 3.866 / avg winner bars 458、±10%)

| 走 0 変種 | 指標 | canon | port | ok |
|---|---|---|---|---|
| walk0_flip_canon | n | 46 | 60 | ❌ |
| walk0_flip_canon | wr | 0.2391 | 0.1833 | ❌ |
| walk0_flip_canon | pf | 3.8660 | 2.1723 | ❌ |
| walk0_flip_canon | avg_win_bars | 458 | 372.8182 | ❌ |
| walk0_flip_canon | **all** | | | ❌ |
| walk0_tp5_decl | n | 46 | 74 | ❌ |
| walk0_tp5_decl | wr | 0.2391 | 0.2973 | ❌ |
| walk0_tp5_decl | pf | 3.8660 | 1.4489 | ❌ |
| walk0_tp5_decl | avg_win_bars | 458 | 37.0000 | ❌ |
| walk0_tp5_decl | **all** | | | ❌ |

### flip exit 定義の識別 (canon Pine 不在のため。entry / SL 1.5×ATR / 480 cap は固定、TV コスト基準)

| flip 定義 | 説明 | N | WR (tv) | PF (tv) | avg win bars | EV tv p/t | payoff (net) | exits | harness |
|---|---|---|---|---|---|---|---|---|---|
| perfect_dn | EMA200 > EMA75 > EMA25 (完全下順) — 既定 | 60 | 18.3% | 2.17 | 373 | 15.09 | 8.74 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 | ❌ |
| not_perfect_up | perfect_up が偽になる (close < EMA25 含む) | 92 | 20.7% | 0.89 | 26 | -0.71 | 3.92 | PO_DN_FLIP 78, SL_HIT 14 | ❌ |
| close_lt_ema75 | close < EMA75 | 77 | 23.4% | 2.20 | 107 | 10.90 | 6.27 | PO_DN_FLIP 50, SL_HIT 27 | ❌ |
| close_lt_ema200 | close < EMA200 | 65 | 21.5% | 2.45 | 243 | 16.70 | 8.01 | SL_HIT 39, PO_DN_FLIP 26 | ❌ |
| ema25_lt_ema75 | EMA25 < EMA75 | 67 | 22.4% | 2.74 | 252 | 20.84 | 8.57 | SL_HIT 49, PO_DN_FLIP 18 | ❌ |

## 走 0〜5 — bar 内順序仮定 = `adverse_first` (既定・保守側)

| 走 | N | WR | Wilson lo | PF (net) | EV net p/t | Σ net p | avg win p | avg loss p | payoff | winner ≤8h | winner hold bars med (p25–p75) | loser hold bars med | exit 種別 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| walk0_flip_canon | 60 | 18.3% | 10.6% | 1.96 | 13.57 | 814.0 | 151.0 | -17.3 | 8.74 | 0% | 330 (294–466) | 9 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 |
| walk0_tp5_decl | 74 | 29.7% | 20.5% | 1.28 | 3.44 | 254.2 | 52.3 | -17.2 | 3.03 | 45% | 30 (15–52) | 6 | SL_HIT 52, TP_HIT 22 |
| walk0p_C0 | 80 | 21.2% | 13.7% | 0.96 | -0.37 | -30.0 | 46.1 | -12.9 | 3.57 | 65% | 18 (15–30) | 4 | SL_HIT 63, TP_HIT 17 |
| walk1_C0+C1 | 81 | 27.2% | 18.7% | 1.15 | 1.57 | 127.1 | 43.3 | -14.0 | 3.09 | 86% | 26 (15–33) | 4 | SL_HIT 56, MAX_HOLD_TIME 14, TP_HIT 11 |
| walk2_+C2 | 81 | 27.2% | 18.7% | 0.99 | -0.10 | -7.9 | 32.9 | -12.4 | 2.65 | 95% | 25 (14–33) | 3 | SL_HIT 56, TP_HIT 11, MAX_HOLD_TIME 10, WEEKEND_CLOSE 4 |
| walk3_+C3C4 | 85 | 24.7% | 16.8% | 0.63 | -2.69 | -228.8 | 18.8 | -9.7 | 1.93 | 95% | 6 (4–7) | 4 | SL_HIT 46, TRAIL 17, BE 17, WEEKEND_CLOSE 3, TP_HIT 1, MAX_HOLD_TIME 1 |
| walk4_+C5 | 85 | 24.7% | 16.8% | 0.63 | -2.69 | -228.8 | 18.8 | -9.7 | 1.93 | 95% | 6 (4–7) | 4 | SL_HIT 46, TRAIL 17, BE 17, WEEKEND_CLOSE 3, TP_HIT 1, MAX_HOLD_TIME 1 |
| walk5_+C6approx | 92 | 20.7% | 13.6% | 0.64 | -2.19 | -201.2 | 18.6 | -7.6 | 2.45 | 95% | 5 (4–6) | 2 | SIGNAL_REVERSE_APPROX 32, SL_HIT 25, TRAIL 15, BE 15, WEEKEND_CLOSE 3, TP_HIT 1, MAX_HOLD_TIME 1 |

winner / loser 別 exit 種別:

| 走 | winners | losers |
|---|---|---|
| walk0_flip_canon | PO_DN_FLIP 8, CANON_CAP_480 3 | SL_HIT 48, PO_DN_FLIP 1 |
| walk0_tp5_decl | TP_HIT 22 | SL_HIT 52 |
| walk0p_C0 | TP_HIT 17 | SL_HIT 63 |
| walk1_C0+C1 | MAX_HOLD_TIME 11, TP_HIT 11 | SL_HIT 56, MAX_HOLD_TIME 3 |
| walk2_+C2 | TP_HIT 11, MAX_HOLD_TIME 9, WEEKEND_CLOSE 2 | SL_HIT 56, WEEKEND_CLOSE 2, MAX_HOLD_TIME 1 |
| walk3_+C3C4 | TRAIL 17, WEEKEND_CLOSE 2, TP_HIT 1, MAX_HOLD_TIME 1 | SL_HIT 46, BE 17, WEEKEND_CLOSE 1 |
| walk4_+C5 | TRAIL 17, WEEKEND_CLOSE 2, TP_HIT 1, MAX_HOLD_TIME 1 | SL_HIT 46, BE 17, WEEKEND_CLOSE 1 |
| walk5_+C6approx | TRAIL 15, WEEKEND_CLOSE 2, TP_HIT 1, MAX_HOLD_TIME 1 | SIGNAL_REVERSE_APPROX 32, SL_HIT 25, BE 15, WEEKEND_CLOSE 1 |

限界分解 (走 0′ に overlay を単独で載せる、順序 = `adverse_first`):

| 構成 | N | WR | PF (net) | EV net p/t | Σ net p | winner ≤8h | exit 種別 |
|---|---|---|---|---|---|---|---|
| marg_C1_only | 81 | 27.2% | 1.15 | 1.57 | 127.1 | 86% | SL_HIT 56, MAX_HOLD_TIME 14, TP_HIT 11 |
| marg_C2_only | 80 | 21.2% | 0.90 | -0.95 | -75.7 | 76% | SL_HIT 61, TP_HIT 15, WEEKEND_CLOSE 4 |
| marg_C3C4_only | 85 | 22.4% | 0.60 | -3.03 | -257.5 | 95% | SL_HIT 48, TRAIL 18, BE 18, TP_HIT 1 |
| marg_C5_only | 84 | 20.2% | 0.90 | -1.03 | -86.3 | 76% | SL_HIT 58, TP_HIT 17, TIME_DECAY_EXIT 9 |
| marg_C6approx_only | 92 | 10.9% | 0.68 | -2.41 | -221.3 | 80% | SIGNAL_REVERSE_APPROX 49, SL_HIT 33, TP_HIT 10 |
| walk4b_C0+C1+C2+C5_noC3C4 | 84 | 26.2% | 1.03 | 0.27 | 22.9 | 95% | SL_HIT 56, TP_HIT 13, MAX_HOLD_TIME 7, TIME_DECAY_EXIT 4, WEEKEND_CLOSE 4 |

## 走 0〜5 — bar 内順序仮定 = `favorable_first` (感度)

| 走 | N | WR | Wilson lo | PF (net) | EV net p/t | Σ net p | avg win p | avg loss p | payoff | winner ≤8h | winner hold bars med (p25–p75) | loser hold bars med | exit 種別 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| walk0_flip_canon | 60 | 18.3% | 10.6% | 1.96 | 13.57 | 814.0 | 151.0 | -17.3 | 8.74 | 0% | 330 (294–466) | 9 | SL_HIT 48, PO_DN_FLIP 9, CANON_CAP_480 3 |
| walk0_tp5_decl | 74 | 31.1% | 21.7% | 1.35 | 4.20 | 310.4 | 51.8 | -17.3 | 3.00 | 48% | 28 (14–52) | 5 | SL_HIT 51, TP_HIT 23 |
| walk0p_C0 | 80 | 22.5% | 14.7% | 1.02 | 0.21 | 17.1 | 45.4 | -12.9 | 3.52 | 67% | 17 (12–29) | 4 | SL_HIT 62, TP_HIT 18 |
| walk1_C0+C1 | 81 | 28.4% | 19.7% | 1.21 | 2.15 | 174.2 | 43.0 | -14.0 | 3.06 | 87% | 24 (13–33) | 4 | SL_HIT 55, MAX_HOLD_TIME 14, TP_HIT 12 |
| walk2_+C2 | 81 | 28.4% | 19.7% | 1.05 | 0.48 | 39.2 | 33.0 | -12.4 | 2.66 | 96% | 23 (12–33) | 3 | SL_HIT 55, TP_HIT 12, MAX_HOLD_TIME 10, WEEKEND_CLOSE 4 |
| walk3_+C3C4 | 85 | 14.1% | 8.3% | 0.20 | -5.95 | -505.7 | 10.9 | -8.7 | 1.25 | 92% | 4 (3–6) | 3 | SL_HIT 46, BE 26, TRAIL 11, WEEKEND_CLOSE 1, MAX_HOLD_TIME 1 |
| walk4_+C5 | 85 | 14.1% | 8.3% | 0.20 | -5.95 | -505.7 | 10.9 | -8.7 | 1.25 | 92% | 4 (3–6) | 3 | SL_HIT 46, BE 26, TRAIL 11, WEEKEND_CLOSE 1, MAX_HOLD_TIME 1 |
| walk5_+C6approx | 92 | 10.9% | 6.0% | 0.19 | -4.98 | -457.9 | 11.0 | -6.9 | 1.59 | 90% | 4 (3–6) | 2 | SIGNAL_REVERSE_APPROX 32, SL_HIT 25, BE 24, TRAIL 9, WEEKEND_CLOSE 1, MAX_HOLD_TIME 1 |

winner / loser 別 exit 種別:

| 走 | winners | losers |
|---|---|---|
| walk0_flip_canon | PO_DN_FLIP 8, CANON_CAP_480 3 | SL_HIT 48, PO_DN_FLIP 1 |
| walk0_tp5_decl | TP_HIT 23 | SL_HIT 51 |
| walk0p_C0 | TP_HIT 18 | SL_HIT 62 |
| walk1_C0+C1 | TP_HIT 12, MAX_HOLD_TIME 11 | SL_HIT 55, MAX_HOLD_TIME 3 |
| walk2_+C2 | TP_HIT 12, MAX_HOLD_TIME 9, WEEKEND_CLOSE 2 | SL_HIT 55, WEEKEND_CLOSE 2, MAX_HOLD_TIME 1 |
| walk3_+C3C4 | TRAIL 11, MAX_HOLD_TIME 1 | SL_HIT 46, BE 26, WEEKEND_CLOSE 1 |
| walk4_+C5 | TRAIL 11, MAX_HOLD_TIME 1 | SL_HIT 46, BE 26, WEEKEND_CLOSE 1 |
| walk5_+C6approx | TRAIL 9, MAX_HOLD_TIME 1 | SIGNAL_REVERSE_APPROX 32, SL_HIT 25, BE 24, WEEKEND_CLOSE 1 |

限界分解 (走 0′ に overlay を単独で載せる、順序 = `favorable_first`):

| 構成 | N | WR | PF (net) | EV net p/t | Σ net p | winner ≤8h | exit 種別 |
|---|---|---|---|---|---|---|---|
| marg_C1_only | 81 | 28.4% | 1.21 | 2.15 | 174.2 | 87% | SL_HIT 55, MAX_HOLD_TIME 14, TP_HIT 12 |
| marg_C2_only | 80 | 22.5% | 0.96 | -0.36 | -28.6 | 78% | SL_HIT 60, TP_HIT 16, WEEKEND_CLOSE 4 |
| marg_C3C4_only | 85 | 12.9% | 0.20 | -6.20 | -526.9 | 100% | SL_HIT 48, BE 26, TRAIL 11 |
| marg_C5_only | 84 | 21.4% | 0.95 | -0.47 | -39.2 | 78% | SL_HIT 57, TP_HIT 18, TIME_DECAY_EXIT 9 |
| marg_C6approx_only | 92 | 12.0% | 0.74 | -1.89 | -174.2 | 82% | SIGNAL_REVERSE_APPROX 49, SL_HIT 32, TP_HIT 11 |
| walk4b_C0+C1+C2+C5_noC3C4 | 84 | 27.4% | 1.10 | 0.83 | 70.0 | 96% | SL_HIT 55, TP_HIT 14, MAX_HOLD_TIME 7, TIME_DECAY_EXIT 4, WEEKEND_CLOSE 4 |

## C0 感度 (BT 側 what-if、走 0′〜4 を再集計。live 実測率は marker 付き live N 蓄積後に差し替え)

### 順序仮定 = `adverse_first`

| what-if | 走 | N | WR | PF | EV net | Σ net | winner ≤8h | SL 分岐 | flags |
|---|---|---|---|---|---|---|---|---|---|
| base | walk0p_C0 | 80 | 21.2% | 0.96 | -0.37 | -30.0 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk1_C0+C1 | 81 | 27.2% | 1.15 | 1.57 | 127.1 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk2_+C2 | 81 | 27.2% | 0.99 | -0.10 | -7.9 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk3_+C3C4 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| base | walk4_+C5 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk0p_C0 | 80 | 21.2% | 0.96 | -0.37 | -30.0 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk1_C0+C1 | 81 | 27.2% | 1.15 | 1.57 | 127.1 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk2_+C2 | 81 | 27.2% | 0.99 | -0.10 | -7.9 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk3_+C3C4 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk4_+C5 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| ii_sr_priority | walk0p_C0 | 68 | 33.8% | 1.25 | 2.98 | 202.5 | 52% | {'sr': 67, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 32, 'lowliq': 22, 'rn': 10} |
| ii_sr_priority | walk1_C0+C1 | 73 | 38.4% | 1.19 | 2.29 | 166.9 | 89% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk2_+C2 | 73 | 38.4% | 1.05 | 0.56 | 40.8 | 96% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk3_+C3C4 | 77 | 31.2% | 0.68 | -2.63 | -202.2 | 96% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| ii_sr_priority | walk4_+C5 | 77 | 31.2% | 0.71 | -2.28 | -175.6 | 96% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| iii_no_clamp | walk0p_C0 | 80 | 21.2% | 0.96 | -0.37 | -30.0 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk1_C0+C1 | 81 | 27.2% | 1.15 | 1.57 | 127.1 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk2_+C2 | 81 | 27.2% | 0.99 | -0.10 | -7.9 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk3_+C3C4 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iii_no_clamp | walk4_+C5 | 85 | 24.7% | 0.63 | -2.69 | -228.8 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iv_no_lowliq | walk0p_C0 | 80 | 21.2% | 1.02 | 0.17 | 13.3 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk1_C0+C1 | 81 | 27.2% | 1.21 | 2.07 | 168.0 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk2_+C2 | 81 | 27.2% | 1.03 | 0.28 | 22.9 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk3_+C3C4 | 85 | 24.7% | 0.64 | -2.58 | -219.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk4_+C5 | 85 | 24.7% | 0.64 | -2.58 | -219.0 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| v_mtf_1p3 | walk0p_C0 | 80 | 20.0% | 1.20 | 2.06 | 164.9 | 44% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk1_C0+C1 | 81 | 27.2% | 1.25 | 2.54 | 205.7 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk2_+C2 | 81 | 27.2% | 1.10 | 0.87 | 70.7 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk3_+C3C4 | 85 | 24.7% | 0.64 | -2.66 | -225.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| v_mtf_1p3 | walk4_+C5 | 85 | 24.7% | 0.64 | -2.66 | -225.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vi_no_rn | walk0p_C0 | 80 | 21.2% | 0.98 | -0.19 | -15.0 | 65% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk1_C0+C1 | 81 | 27.2% | 1.18 | 1.75 | 142.1 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk2_+C2 | 81 | 27.2% | 1.01 | 0.09 | 7.1 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk3_+C3C4 | 85 | 24.7% | 0.63 | -2.72 | -230.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vi_no_rn | walk4_+C5 | 85 | 24.7% | 0.63 | -2.72 | -230.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vii_no_broker_tp | walk0p_C0 | 80 | 20.0% | 1.08 | 0.84 | 67.5 | 50% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk1_C0+C1 | 81 | 27.2% | 1.19 | 1.96 | 158.6 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk2_+C2 | 81 | 27.2% | 1.03 | 0.29 | 23.6 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk3_+C3C4 | 85 | 24.7% | 0.64 | -2.66 | -225.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vii_no_broker_tp | walk4_+C5 | 85 | 24.7% | 0.64 | -2.66 | -225.9 | 95% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |

### 順序仮定 = `favorable_first`

| what-if | 走 | N | WR | PF | EV net | Σ net | winner ≤8h | SL 分岐 | flags |
|---|---|---|---|---|---|---|---|---|---|
| base | walk0p_C0 | 80 | 22.5% | 1.02 | 0.21 | 17.1 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk1_C0+C1 | 81 | 28.4% | 1.21 | 2.15 | 174.2 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk2_+C2 | 81 | 28.4% | 1.05 | 0.48 | 39.2 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| base | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| base | walk4_+C5 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk0p_C0 | 80 | 22.5% | 1.02 | 0.21 | 17.1 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk1_C0+C1 | 81 | 28.4% | 1.21 | 2.15 | 174.2 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk2_+C2 | 81 | 28.4% | 1.05 | 0.48 | 39.2 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| i_atr_only | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| i_atr_only | walk4_+C5 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| ii_sr_priority | walk0p_C0 | 68 | 35.3% | 1.32 | 3.69 | 251.1 | 54% | {'sr': 67, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 32, 'lowliq': 22, 'rn': 10} |
| ii_sr_priority | walk1_C0+C1 | 73 | 39.7% | 1.25 | 2.95 | 215.5 | 90% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk2_+C2 | 73 | 39.7% | 1.12 | 1.22 | 89.4 | 97% | {'sr': 72, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 34, 'lowliq': 25, 'rn': 10} |
| ii_sr_priority | walk3_+C3C4 | 77 | 14.3% | 0.18 | -7.00 | -538.9 | 91% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| ii_sr_priority | walk4_+C5 | 77 | 14.3% | 0.19 | -6.65 | -512.3 | 91% | {'sr': 76, 'atr_rrlow': 1} | {'clamp_min': 3, 'clamp_max': 35, 'lowliq': 26, 'rn': 11} |
| iii_no_clamp | walk0p_C0 | 80 | 22.5% | 1.02 | 0.21 | 17.1 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk1_C0+C1 | 81 | 28.4% | 1.21 | 2.15 | 174.2 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk2_+C2 | 81 | 28.4% | 1.05 | 0.48 | 39.2 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| iii_no_clamp | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iii_no_clamp | walk4_+C5 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| iv_no_lowliq | walk0p_C0 | 80 | 22.5% | 1.08 | 0.73 | 58.7 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk1_C0+C1 | 81 | 28.4% | 1.28 | 2.63 | 213.4 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk2_+C2 | 81 | 28.4% | 1.10 | 0.84 | 68.3 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk3_+C3C4 | 85 | 14.1% | 0.21 | -5.83 | -495.9 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| iv_no_lowliq | walk4_+C5 | 85 | 14.1% | 0.21 | -5.83 | -495.9 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 0, 'rn': 5} |
| v_mtf_1p3 | walk0p_C0 | 80 | 20.0% | 1.20 | 2.06 | 164.9 | 44% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk1_C0+C1 | 81 | 27.2% | 1.25 | 2.54 | 205.7 | 86% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk2_+C2 | 81 | 27.2% | 1.10 | 0.87 | 70.7 | 95% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| v_mtf_1p3 | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| v_mtf_1p3 | walk4_+C5 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vi_no_rn | walk0p_C0 | 80 | 22.5% | 1.04 | 0.40 | 32.1 | 67% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk1_C0+C1 | 81 | 28.4% | 1.24 | 2.34 | 189.2 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk2_+C2 | 81 | 28.4% | 1.08 | 0.67 | 54.2 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 0} |
| vi_no_rn | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.97 | -507.8 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vi_no_rn | walk4_+C5 | 85 | 14.1% | 0.20 | -5.97 | -507.8 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 0} |
| vii_no_broker_tp | walk0p_C0 | 80 | 21.2% | 1.15 | 1.51 | 121.1 | 53% | {'atr': 80} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk1_C0+C1 | 81 | 28.4% | 1.26 | 2.62 | 212.2 | 87% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk2_+C2 | 81 | 28.4% | 1.11 | 0.95 | 77.2 | 96% | {'atr': 81} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 26, 'rn': 6} |
| vii_no_broker_tp | walk3_+C3C4 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
| vii_no_broker_tp | walk4_+C5 | 85 | 14.1% | 0.20 | -5.95 | -505.7 | 92% | {'atr': 85} | {'clamp_min': 0, 'clamp_max': 0, 'lowliq': 27, 'rn': 6} |
