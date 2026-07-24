# sweep_reversion_eurgbp_late

- **Status**: **R2 STOP (live code pin) + shadow rescue 稼働中** — 2026-07-06 T8 ゲート①抵触で `_SWEEP_REVERSION_EURGBP_LIVE_ENABLE = False` code pin (demo_trader.py:8763、env では覆せない、[[t8-week1-gate-breach-2026-07-06]])。旧 Status「LIVE (R1 意図的例外, 06-12, env=1)」は 07-06 以降 stale だったため 2026-07-24 訂正
- **復帰条件 (T8 決定書)**: P-S1(a) HTF exemption の user R1 決裁 + order 層 12-bar min-spacing 実装。決裁トリガ = rescued shadow **unique バー N≥10** (2026-07-24 時点 unique N=8 / row N=14、row EV +2.13p / unique EV +2.48p、WR 71-75%)。⚠️ shadow exit は pre-reg estimand (time-stop/±ATR) と乖離 (SIGNAL_REVERSE/BE-trail 痕跡) のため、shadow EV は entry 符号確認まで — 復権判定に無修正流用しない
- **Mode**: daytrade_eurgbp (15m) / **Pair**: EUR_GBP only / **Direction**: BUY only
- **Lot**: 1000u 固定 (MIN lot)

> ⚠️ **2026-07-02 zero-fire 診断**: 登録 (06-12) 以降 shadow 含め発火 0 の根本原因は **v9.1 HTF Hard Block (app.py:2609)**。本番同一フィード (Massive 15m) + 本番 evaluate() で 06-12 以降 4 回 emit していたが (06-15/06-25/06-30/07-01 いずれも 21:00-21:15 UTC)、逆張り BUY は発火瞬間が構造的に htf=bear のため候補リスト段階で全排除され、shadow 記録・side-channel より前に silent drop。12y grid pre-reg は HTF gate なしで検証されており BT/本番統一違反。P-S1(b) shadow 退避は 2026-07-03 実装済み (live 送信ゼロのまま shadow N 蓄積再開、[HTF_BLOCK_SHADOW_RESCUE] タグ付き)。live exemption P-S1(a) は user 決裁待ちで、蓄積 shadow N が判断材料。
> 詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §3


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
