# Edge Factor Audit 2026-06-12 — #2 bb_rsi_reversion (+ dt_bb_rsi_mr pre-reg)

Edge 別 N 降順要因解析シリーズ第 2 弾。データ母集団は
[[edge-factor-audit-2026-06-12-ema-trend-scalp]] と同一
(Render 本番 closed 9,779 → clean 7,875、dedup_violation 19% 除外、LIVE/Shadow 分離)。

## Verdict: 🟠 統合退役 (rule:R2) — scalp 版退役、家族代表は dt_bb_rsi_mr

#1 (シグナル＝ノイズ) と異なり、**思想 (BB+RSI MR) は gross で生きている。
負けの全要因は friction とジオメトリの不整合** — W4-EDA「思想は正、設計が誤」の
最純粋例。修理形 (TPを伸ばす) は dt_bb_rsi_mr として既に存在するため、
scalp 版の存続理由がない。

## 同族比較 (決定的証拠)

| | bb_rsi_reversion (scalp) | dt_bb_rsi_mr (DT 15m) |
|---|---|---|
| N (clean) | 780 (LIVE 243 / SH 537) | 120 (LIVE 15 / SH 105) |
| median TP / SL | 5.2p / 3.6p | 10.9p / 8.3p |
| median 保有 | **8 分** | 29 分 |
| friction / TP | **24.7%** | **10.8%** |
| BE-WR vs 実測 WR | 40.9% vs 35.4% ❌ | 43.1% vs 47.5% ✅ |
| net EV | −0.21 (LIVE) / −0.94 (SH) | **+1.72** (SH, PF 1.61, Wilson .383) |
| gross EV | +0.50 / +0.61 | +1.37 / +2.82 |
| 敗者 MAFE fav 中央値 | 0.0p | 1.4p |

同一思想で TP 5p→11p にしただけで friction 比 25%→11%、エッジが friction の上に出る。
2026-06-08 Cell-Edge 監査の「真因は friction (gross≈0)」をエッジ単位で再現。

## 退役根拠 (修理せず殺す理由)

1. 🔴 **算数**: gross +0.5p < friction 1.2-1.5p。TP 延長修理 = dt_bb_rsi_mr の複製
2. 🔴 **フィルタ修理は本戦略で実証済みの罠**: H1 EMA200 整合追加で Kelly 0.43→0
   ([[feedback_ma_filter_breaks_mr]] の当事者)
3. 🔴 **12y MASSIVE BT REJECT** (2026-06-11, USD_JPY 提案版 PF 0.66)
4. 🟠 **封じ込め 3 段がすべて漏れた**: E4 disable (06-04) → USD_CHF hourly 22 件漏れ
   → pair whitelist (06-08, ただし env 一発バイパス可) → 正式退役の不在が真因
5. 🟠 唯一の net 正セル EUR_USD BUY (+0.40, N=73) は Wilson_lo 0.318 < BE-WR 0.409 で
   非有意。dt_bb_rsi_mr 側 EUR_USD BUY (+2.22) が思想を引き継ぐ

実装: `SHADOW_RETIRED_STRATEGIES` に追加 (#1 で新設した仕組み)。既存防御
(whitelist / per-cell registry / OANDA_TRIP) は残置 — 多層は維持、最終層を不可逆化。

## dt_bb_rsi_mr 育成 pre-reg (Rule 1 用、本日 LOCK)

**現状**: Shadow 30d N=56 / net +1.40 / PF 1.55 で健全蓄積中。pooled N=105
Wilson_lo=0.383 — H1 Gate (≥0.40) まで未達。

**Pre-registered promotion 審査条件** (到達前の昇格議論を禁止する LOCK):
1. **トリガー**: Shadow clean (dedup_violation=0, XAU 除外) pooled N ≥ 165
   かつ Wilson_lo ≥ 0.40 (現 WR 47.6% 維持なら N≈165 で到達、見込み 1〜1.5 ヶ月)
2. **審査バトリー**: PF / Wilson / WF 3-fold / Bonferroni (m = 審査時 active 戦略数) /
   Kelly — [[feedback_partial_quant_trap]] フルセット
3. **セル処置は SKIP でなく SIZE** ([[feedback_size_lever_beats_skip_filter]]):
   - GBP_USD BUY (N=27, EV −1.16, PF 0.76) → lot 0.5x
   - 08-11 UTC bucket (N=22, gross −1.46 で唯一 gross 負) → lot 0.5x
   - 他セル 1.0x。SKIP/filter 追加は禁止 (罠 2 件の実証済みパターン)
4. **月次整合**: 2026-06 が N=16 EV −1.11 と凹み中 — 審査時に直近 30d EV>0 を要求
   ([[feedback_cohort_time_check]])
5. 審査は手動トリガー、結果は本ファイルに追記

## シリーズ進捗

| # | edge | N | verdict |
|---|---|---|---|
| 1 | ema_trend_scalp | 1,117 | 🔴 KILL (ノイズ+friction) |
| 2 | bb_rsi_reversion | 780 | 🟠 統合退役 (friction、思想は dt_bb_rsi_mr へ) |
| 次 | fib_reversal | 638 | — |

以降: sr_channel_reversal 584 → sr_fib_confluence 428 → session_time_bias 399。
