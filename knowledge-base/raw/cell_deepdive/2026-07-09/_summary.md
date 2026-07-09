# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-07-09

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しないため、前週 (2026-07-02) と同一の ad-hoc 再実装 (`_run_deepdive_2026_07_09.py`, `cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` オプションは非対応 (regime 軸なし、cell = entry_type × pair × direction [v2] / + session [v3])。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades` (PROD)。ローカル demo_trades.db は STALE (memory rule 準拠)
- **Window**: 365d 指定、実データ span 2026-04-02 → 2026-07-09 (約 14 週)
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 12,634 / target raw 521 / dedup 除外 321 / non-WL 除外 16 / **clean N = 184** / m_global v2 = 2, v3 = 0

## PAIR_PROMOTED Candidates

**0 件** (前週も 0 件)。Gate = N≥20 ∧ Wilson_lo>0.50 ∧ p_bonf<0.05。

## Eligible cells (N≥20, v2)

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 24 | 62.5% | 0.427 | +5.85 | 2.33 | 0.441 | 0.357 | ✅ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 25 | 52.0% | 0.335 | −4.63 | 0.44 | 1.0 | 0 | ❌ |

## 前週比 (2026-07-02 → 2026-07-09)

| strategy | clean_N | ΔN | WR | EV_net | PF | 前週PF |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 114 | +3 | 46.5% | −2.72 | 0.58 | 0.66 ↓ |
| sr_liquidity_grab | 1 | 0 | — | — | — | — |
| cpd_divergence | 0 | 0 | — | — | — | — |
| vdr_jpy | 11 | +1 | 72.7% | +10.44 | 4.61 | 7.72 |
| vsg_jpy_reversal | 33 | +3 | 72.7% | +2.71 | 1.70 | 1.65 ↑ |
| rsk_gbpjpy_reversion | 20 | +4 | 40.0% | −5.51 | 0.41 | 0.39 |
| mqe_gbpusd_fix | 5 | 0 | 60.0% | +6.76 | 2.48 | 2.48 (停滞) |

合計 clean N: 173 → 184 (+11/週)。

## Notable (near-miss, N<20 informational)

- **vsg_jpy_reversal 戦略集計** N=33 WR72.7% **Wilson_lo 0.558** (>0.50!) PF1.70 — 戦略レベルでは promotion 水準到達。ただし cell 単位では EUR_JPY SELL N=15 (Wilson_lo 0.480, p_bonf 0.141, wf ✅) が最良で N 不足。あと ~2-3 週の蓄積で N≥20 到達見込み → 本 audit の第一注目セル
- **vdr_jpy | USD_JPY | BUY** N=8 WR75% EV+14.9p PF6.1 wf ✅ — 発火レート低 (~1/週)、N≥20 は 3 ヶ月先
- **sr_anti_hunt_bounce | EUR_JPY | BUY** N=24 wf ✅ PF2.33 だが p_bonf 0.441 で有意性遠い。同戦略の GBP_JPY BUY は悪化中 (PF 0.44) — aggregate 負けの主因
- **停滞警告**: mqe_gbpusd_fix clean N=5 で 2 週連続増加ゼロ (raw 87 のうち dedup/non-WL で 94% 除外)。cpd_divergence は依然 0 発火 — signal 発火経路の未解決課題継続

## 判定

**依然 N 不足、shadow 蓄積継続中。** promotion 判断アクションなし。vsg_jpy_reversal EUR_JPY SELL の N≥20 到達が次のマイルストーン。
