# sweep_reversion_eurgbp_late

- **Status**: LIVE (rule:R1 意図的例外, user 判断 2026-06-12, env `SWEEP_REVERSION_EURGBP_LIVE_ENABLE=1`)
- **Mode**: daytrade_eurgbp (15m) / **Pair**: EUR_GBP only / **Direction**: BUY only
- **Lot**: 1000u 固定 (MIN lot)

## Thesis

21-24 UTC (LATE) は EUR_GBP の最薄商い時間。直近 96 bars の swing low を一瞬割って
同バーで reclaim する low-sweep = thin market での stop 狩り。Asia/London の流動性
回帰とともに ~12h で平均回帰する。

## Evidence

12y-first grid scan (m=1,728, Bonferroni only gate) の**唯一の生存 cell**:
- N=543 / WR 59.7% / mean +6.22p (net 1.5p spread) / t=4.46 (z_bonf=4.02)
- WFO 3-fold 全正 (+4.98/+5.30/+8.37)、年次 11/13 正
- 反証 3/3 通過 (vs 無条件 LATE BUY 3倍 / spread 3.5p 耐性 / データ密度均一)
- ⚠️ エッジは 2021-2026 集中 (直近 regime のエッジ)

詳細: [[sweep-reversion-eurgbp-late-live-2026-06-12]] (decision LOCK) /
`bt-results/sweep-reversion-grid-scan-12y.md` / memory `project_sweep_reversion_grid_survivor_2026_06_12`

## Rules

- Entry: closed bar h∈[21,24) UTC ∧ low < swing_lo(96) − 0.05×ATR14 ∧ close > swing_lo
- Exit: time-stop 48 bars (12h) 一次 / SL −4×ATR / TP +6×ATR (tail-cap)
- Dedup: per-bar + 12-bar cooldown
- 期待発火: 3-4 回/月

## Withdrawal (pre-reg)

Live N≥10 EV<0 / N≥20 WR<42% / 累積DD>100p / regime反転証拠 / 30日 fire 0→forensic

## History

- 2026-06-12: 発見 (research scan) → 同日 productionize → LIVE 投入 (Claude 実装, Codex review)
