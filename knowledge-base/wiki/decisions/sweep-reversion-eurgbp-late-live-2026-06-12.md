# Sweep-Reversion EUR_GBP LATE — LIVE Direct (2026-06-12)

## Status

**rule:R1-EXCEPTION (intentional shadow-first exception, user judgment 2026-06-12)**
Same pattern as Kalman D7 / vix_carry / ZZ v60 / USDJPY carry dip (Path B)。
User 指示: 「LIVE本番でプロダクションに入ってください、claudeが実装し、レビューをcodexが行うこと」

## Evidence (12y-first — production コードより先に research scan で確認)

`tools/research_sweep_reversion_grid_12y.py` (commit 874bc2df):
m=1,728 cell grid、Bonferroni hard gate (α=2.89e-5, z=4.02) で**唯一の生存 cell**:

| 項目 | 値 |
|---|---|
| Cell | EUR_GBP 15m / L=96 / d=0.05×ATR / BUY (low-sweep) / H=48 / LATE (21-24 UTC) |
| N | 543 (12.4y native data) |
| WR | 59.7% |
| mean net pip | +6.22 (spread 1.5p 控除) |
| t-stat | 4.46 (> z_bonf 4.02) |
| WFO 3-fold | +4.98 / +5.30 / +8.37 (全 fold 正) |
| 年次 | 11/13 年プラス |

反証チェック 3/3 通過: (1) sweep 条件は無条件 LATE BUY の 3 倍エッジ (2) spread 3.5p 耐性
(3) データ密度均一 → 2021+ イベント急増は実 regime 変化。

**Top-10 の 8/10 が同 family** (隣接 L/d/H) = param 空間 robust、孤立 artifact でない。

## なぜ LIVE 直行か (例外の根拠)

- 発火頻度 ~44/年 ≈ 3-4/月 → shadow でも live でも N 蓄積速度は同一 (carry dip と同じ論理)
- MIN lot 1000u 固定で per-trade リスク ≈ SL 4×ATR ≈ 25p ≈ ¥450 (テール)
- 12y Bonferroni 生存は当 project で過去最強の事前証拠 (TP-HIT 12cell は全滅、これは通った)

## Implementation (LOCK)

- 戦略: `strategies/daytrade/sweep_reversion_eurgbp_late.py` (mode=daytrade_eurgbp, 15m)
- Entry: signal bar (closed) が UTC 21-24 時 ∧ low < swing_lo(96) − 0.05×ATR14 ∧ close > swing_lo → BUY
- Exit: time-stop 48 bars = 12h (`_ENTRY_TYPE_MAX_HOLD` = 43200s) が一次。
  SL = entry − 4×ATR / TP = entry + 6×ATR は tail-cap (research 分布保存のため広め)
- Dedup: per-bar + cooldown 12 bars (research scan と同一 gap)
- Lot: **1000u 固定** (`SWEEP_REVERSION_EURGBP_MIN_LOT`、carry dip と同型)
- LIVE 制御: env `SWEEP_REVERSION_EURGBP_LIVE_ENABLE=1` の時のみ、この 1 戦略・EUR_GBP 限定で
  SHADOW_MODE / Phase0 / `_OANDA_MODE_BLOCKED(daytrade_eurgbp)` を bypass
  (`_sweep_reversion_eurgbp_live_eligible`、tier=`SWEEP_REVERSION_EURGBP_LIVE`)。
  グローバル SHADOW_MODE / mode block は不変 (他戦略 live 化の暴発防止)
- Signal kill switch: env `SWEEP_REVERSION_EURGBP_ENABLE=0` で発火自体を停止 (rollback)

## Withdrawal triggers (pre-reg LOCK)

どれか成立 → env flag OFF (+必要なら enabled=False):

1. **Live N ≥ 10 で EV < 0** (実 spread/swap 込み) — watchdog 基準と同型
2. **Live N ≥ 20 で WR < 42%** (= 12y WR 59.7% × 0.7)
3. **累積 Live DD > 100 pip** (1000u で ¥1,800 相当)
4. **Regime 反転の構造証拠**: 年次更新で direct年がマイナス & research 再走で t < 2.0
5. 30 日間 fire 0 (期待 3-4/月) → 発火経路の故障調査 (kill でなく forensic)

## Review

- 実装: Claude (一次実装、`[[feedback_codex_as_review_layer_2026_06_05]]`)
- レビュー: Codex (user 指示により必須) — 本 commit の diff 全体を review、
  指摘は follow-up commit で反映

## Caveat (再掲)

- エッジは 2021-2026 に集中 (2014-2020 は薄く mixed)。「直近 5y regime のエッジ」
- spread 1.5p は仮定、LATE rollover (21-22 UTC) は spike しうる → 既存 dynamic Spread/SL Gate が防御
- 12h 保有 = overnight financing 跨ぎ (EUR_GBP swap 小)

## Linked

- memory: `[[project_sweep_reversion_grid_survivor_2026_06_12]]`
- research: `bt-results/sweep-reversion-grid-scan-12y.{json,md}`
- spec: `docs/superpowers/specs/2026-06-12-sweep-reversion-grid-scan-design.md`
- 同型例外: kalman_d7 / vix-carry-1x / zz-pivot-v60 / usdjpy-carry-dip
