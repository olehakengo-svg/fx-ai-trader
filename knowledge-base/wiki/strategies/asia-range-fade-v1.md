# asia_range_fade_v1

## Status: Pre-reg LOCK Phase 3 候補 (2026-04-27 R-A 実装)

**Tier**: Phase 3 BT 検証待ち (validation 後 PAIR_PROMOTED 候補)
**Mode**: daytrade (M15)
**Category**: MR (Mean-Reversion Structural edge)
**Pre-reg LOCK**: 2026-04-26 (commit `34c404c` 時刻署名)

## Mechanism Thesis (LOCKED)

アジア時間 (UTC 02-06) の低 vol 環境で形成された range の high/low touch は、
構造的に流動性吸収後に range 中央へ回帰する傾向が高い。touch + rejection で fade entry。

**学術根拠**: Lo & MacKinlay (1988) "Stock Market Prices Do Not Follow Random Walks"

**因果方向**: 低 vol session → range 形成 → touch (overshoot) → liquidity 吸収 → 中央回帰

## Entry Conditions (LOCKED)

- **SESSION**: UTC hour ∈ [02, 06]
- **RANGE_FORMATION**:
  - 直近 24 bars (M15 × 6h) で range_size ≤ 1.5 × ATR
  - range_size ≥ 5 pip (極小範囲除外)
  - bars_in_range_pct ≥ 0.80 (24 bar の 80% 以上が range 内)
- **TOUCH**: BUY: low ≤ range_low × 1.0005, SELL: high ≥ range_high × 0.9995
- **REJECTION_CANDLE**: 下髭/上髭 比率 ≥ 0.4
- **RSI(14)**: BUY: ≤ 30, SELL: ≥ 70

**Forbidden**:
- ATR(14) > 8 pip (vol expansion = range invalid)
- 直近 4 bars 内に同方向 entry (重複防止)

## Exit Conditions (LOCKED)

- **TP**: range center または entry ± 0.7 × range_size, 近い方
- **SL**: range_low - 0.5 × ATR (BUY) / range_high + 0.5 × ATR (SELL)
- **Time stop**: London open (07:00 UTC)

## Validation Requirements (LOCKED, 緩和不可)

- N ≥ 200 (Live + Shadow)
- Wilson 95% lower > 50%
- PF > 1.40 (MR は WR 高めを想定)
- EV > 0 (after Friction Model v2 Tokyo session cost)
- 5-fold WFA: 各 fold WR > 50% AND PF > 1.0
- Bonferroni α=0.005

## Source

- `strategies/daytrade/asia_range_fade_v1.py`
- `knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md`

## Related

- [[strategy-mechanism-audit-2026-04-26]] — TAP-1/2/3 不含確認
- [[pullback-to-liquidity-v1]] — 兄弟 pre-reg (TF side)
- [[phase3-bt-pre-reg-lock]] — Phase 3 BT K=7 universe 内
