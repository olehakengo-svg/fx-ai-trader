# pullback_to_liquidity_v1

## Status: Pre-reg LOCK Phase 3 候補 (2026-04-27 R-A 実装)

**Tier**: Phase 3 BT 検証待ち (validation 後 PAIR_PROMOTED 候補)
**Mode**: daytrade (M15)
**Category**: TF (Trend-Following Structural edge)
**Pre-reg LOCK**: 2026-04-26 (commit `34c404c` 時刻署名)

## Mechanism Thesis (LOCKED)

HTF (H4) trend が確立した方向に対し、M15 swing low/high への pullback 局面では
流動性供給により価格が再加速する。pullback 完了 + rejection で entry。

**学術根拠**: Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum"

**因果方向**: HTF trend → 短期 pullback → liquidity zone touch → rejection → trend resume

## Entry Conditions (LOCKED)

- **HTF_BIAS**: ctx.htf.get("agreement") in {"bull", "bear"}
- **M15 Swing**: 直近 20 bars 内の swing low/high (≥ 5 bar 前)
- **LIQUIDITY_TOUCH**: current low/high が swing ± 5pip (0.001 tolerance)
- **REJECTION_CANDLE**: 下髭/上髭 比率 ≥ 0.4
- **VOLUME_CONFIRMATION**: 現足 volume ≥ 1.2 × avg(20)

**Forbidden**:
- HTF agreement = "mixed" / "neutral"
- ATR(14) < 5 pip
- Asia_early session (UTC [00, 02])

## Exit Conditions (LOCKED)

- **TP**: entry ± 2.0 × ATR(14)
- **SL**: entry ∓ 1.0 × ATR(14)
- **Time stop**: 24 bars (M15 × 6h)

## Validation Requirements (LOCKED, 緩和不可)

- N ≥ 200 (Live + Shadow)
- Wilson 95% lower > 50%
- PF > 1.30
- EV > 0 (after Friction Model v2)
- 5-fold WFA: 各 fold WR > 50% AND PF > 1.0
- Bonferroni α=0.005 (m=10 想定)

## Source

- `strategies/daytrade/pullback_to_liquidity_v1.py`
- `knowledge-base/wiki/decisions/pre-reg-pullback-to-liquidity-v1-2026-04-26.md`

## Related

- [[strategy-mechanism-audit-2026-04-26]] — TAP-1/2/3 不含確認
- [[asia-range-fade-v1]] — 兄弟 pre-reg (MR side)
- [[phase3-bt-pre-reg-lock]] — Phase 3 BT K=7 universe 内
