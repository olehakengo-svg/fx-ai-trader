# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-07-12

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しないため、前週 (2026-07-09) と同一の ad-hoc 再実装 (`_run_deepdive_2026_07_12.py`, `cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` オプションは非対応 (regime 軸なし、cell = entry_type × pair × direction [v2] / + session [v3])。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD)。ローカル demo_trades.db は STALE (memory rule 準拠)。⚠️ **今週の変更**: 無指定だと API が 50 件しか返さなくなった (デフォルト limit 導入)。`?limit=100000` で全 12,860 件取得。次回以降 limit 明示必須
- **Window**: 365d 指定、実データ span 2026-04-02 → 2026-07-10 (約 14 週)
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 12,860 / target raw 534 / dedup 除外 325 / non-WL 除外 16 / **clean N = 193** / m_global v2 = 2, v3 = 0

## PAIR_PROMOTED Candidates

**0 件** (前週・前々週も 0 件)。Gate = N≥20 ∧ Wilson_lo>0.50 ∧ p_bonf<0.05。

## Eligible cells (N≥20, v2)

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 26 | 65.4% | 0.462 | +5.58 | 2.37 | 0.233 | 0.378 | ✅ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 27 | 48.1% | 0.307 | −5.32 | 0.38 | 1.0 | 0 | ❌ |

## 前週比 (2026-07-09 → 2026-07-12)

| strategy | clean_N | ΔN | WR | EV_net | PF | 前週PF |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 119 | +5 | 46.2% | −2.83 | 0.57 | 0.58 → |
| sr_liquidity_grab | 1 | 0 | — | — | — | — |
| cpd_divergence | 0 | 0 | — | — | — | — |
| vdr_jpy | 12 | +1 | 75.0% | +9.72 | 4.67 | 4.61 ↑ |
| vsg_jpy_reversal | 35 | +2 | 68.6% | +1.72 | 1.39 | 1.70 ↓ |
| rsk_gbpjpy_reversion | 21 | +1 | 38.1% | −6.14 | 0.37 | 0.41 ↓ |
| mqe_gbpusd_fix | 5 | 0 | 60.0% | +6.76 | 2.48 | 2.48 (停滞) |

合計 clean N: 184 → 193 (+9/週)。蓄積ペースは前週 (+11) からやや鈍化。

## Notable (near-miss, N<20 informational)

- **vsg_jpy_reversal 戦略集計** N=35 WR68.6% **Wilson_lo 0.520** (前週 0.558 から低下、依然 >0.50)。ただし cell 単位の EUR_JPY SELL は **N=15 で前週から増加ゼロ** (Wilson_lo 0.480, wf ✅) — 戦略の +2 は別セルへ流入。先週「次のマイルストーン」とした EUR_JPY SELL N≥20 到達は今週も未達、WR も 72.7%→68.6% で希釈方向
- **sr_anti_hunt_bounce | EUR_JPY | BUY** N=24→**26** に成長、WR 62.5%→65.4% で **p_bonf 0.441→0.233 に改善**。PF2.37 wf ✅ で 7 戦略中もっとも promotion に近いセル。ただし依然 Wilson_lo 0.462 (<0.50) ∧ p_bonf 0.233 (>0.05) で二重未達。同戦略の GBP_JPY BUY (N=27 PF0.38) が aggregate 負け (PF0.57) の主因で相殺構造は不変
- **vdr_jpy | USD_JPY | BUY** N=8→9 WR77.8% EV+13.5p PF6.18 wf ✅ — 発火レート ~1/週、N≥20 は約 3 ヶ月先。単セルとしては最強エッジだが N 決定的不足
- **停滞警告**: mqe_gbpusd_fix clean N=5 で **3 週連続増加ゼロ** (raw 87 のうち dedup/non-WL で 94% 除外)。cpd_divergence は依然 **0 発火** (14 週連続) — signal 発火経路の未解決課題継続。sr_liquidity_grab も raw 2 / clean 1 で実質死蔵

## 判定

**依然 N 不足、shadow 蓄積継続中。** promotion 判断アクションなし。今週の注目点は 3 つ:
1. sr_anti_hunt_bounce EUR_JPY BUY の p_bonf が 0.441→0.233 と着実改善中 (N 蓄積で有意性が育つ健全パターン)。次週 N≥30 到達で監視格上げ候補
2. vsg_jpy_reversal EUR_JPY SELL が 2 週連続 N=15 停滞 + WR 希釈 — 先週の第一マイルストーン仮説はやや後退
3. cpd_divergence / mqe_gbpusd_fix / sr_liquidity_grab の 3 戦略は発火枯渇で shadow 蓄積が事実上停止 → signal 発火経路調査を別タスク化すべき段階
