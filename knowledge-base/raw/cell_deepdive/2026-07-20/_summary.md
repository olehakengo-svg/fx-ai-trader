# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-07-20

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しないため、前週までと同一の ad-hoc 再実装 (`_run_deepdive_2026_07_20.py`, `cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` オプションは非対応 (regime / hour_bin / mode 軸なし、cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD, HTTP 200 / 40MB)。ローカル demo_trades.db は STALE (memory rule 準拠)。`?limit=100000` 明示必須 (無指定だと 50 件のみ返る)
- **Window**: 365d 指定、実データ span 2026-04-02 → 2026-07-20 (約 16 週)
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 13,525 / target raw 574 / dedup 除外 340 / non-WL 除外 16 / **clean N = 218** / m_global v2 = 2, v3 = 0

## PAIR_PROMOTED Candidates

**1 件** (前 3 週は 0 件)。Gate = N≥20 ∧ Wilson_lo>0.50 ∧ p_bonf<0.05 を初めて全通過するセルが出現。

| # | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EUR_JPY | (集約) | (集約) | (集約) | (集約) | BUY | 35 | 74.3% | **0.579** | +5.01 | 2.66 | **0.0081** | 0.463 | ✅ |

戦略 = `sr_anti_hunt_bounce`。session/hour_bin/regime/mode は本ツール未分解のため集約値。

### ⚠️ 昇格クロスの品質監査 (Rule 1 前段)

3 ゲートを形式上全通過したが、**crossing は単日 hot-streak に駆動されており統計的独立性が疑わしい**。生データ検証結果:

- 前週 (07-12) N=26 WR65.4% (17W) Wilson_lo 0.462 / p_bonf 0.233 → 今週 N=35 WR74.3% (26W)。**+9 trade が 9勝0敗**
- この 9 勝は時間集中: **6 勝が 2026-07-17 の単日**、8 勝が 07-15→07-17 の 3 日窓に集中。Wilson/binomial は独立試行前提だが、同一ペア・近接時刻の bounce は高相関 → 有意性 (p_bonf 0.0081) は過大評価の疑い (memory: 時間コホート整合 / MASSIVE MR は OANDA クロス確認必須)
- 勝ち pip は 1.7–3.1p が大半 (最大 10.5p が 1 本)。**micro bounce-scalp = friction 感応度が高い**。EV は勝ち数増でも +5.58→+5.01 と微減 = 新規勝ちは薄利。低ボラ JPY クロスの bar-bounce が約定不能微細構造である前例あり (EUR_GBP z-MR 幻エッジ)
- 全 35 件が **is_shadow=1** (Live 約定 0)。spread/slippage 未検証

## Eligible cells (N≥20, v2)

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 35 | 74.3% | 0.579 | +5.01 | 2.66 | 0.0081 | 0.463 | ✅ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 27 | 48.1% | 0.307 | −5.32 | 0.38 | 1.0 | 0 | ❌ |

v3 (＋session) eligible = 0 (どの session×pair×dir も N<20)。

## 前週比 (2026-07-12 → 2026-07-20)

| strategy | clean_N | ΔN | WR | EV_net | PF | 前週PF |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 137 | +18 | 52.6% | −2.18 | 0.62 | 0.57 ↑ |
| sr_liquidity_grab | 1 | 0 | — | — | — | — |
| cpd_divergence | 0 | 0 | — | — | — | — |
| vdr_jpy | 16 | +4 | 81.2% | +8.59 | 5.32 | 4.67 ↑ |
| vsg_jpy_reversal | 36 | +1 | 69.4% | +1.74 | 1.40 | 1.39 → |
| rsk_gbpjpy_reversion | 23 | +2 | 43.5% | −5.26 | 0.41 | 0.37 ↑ |
| mqe_gbpusd_fix | 5 | 0 | 60.0% | +6.76 | 2.48 | 2.48 (停滞) |

合計 clean N: 193 → 218 (**+25/週**、前週 +9 から加速)。増加の 18/25 は sr_anti_hunt_bounce (07-15→07-17 の発火スパイク由来)。

## Notable

- **sr_anti_hunt_bounce | EUR_JPY | BUY が初の 3 ゲート通過** — ただし上記の通り単日クラスタ駆動。同戦略 aggregate は依然 PF0.62 / EV−2.18 の net-negative で、GBP_JPY BUY (N=27 PF0.38 EV−5.32) が相殺主因。相殺構造は不変
- **vdr_jpy | 戦略集計** N=16 WR81.2% Wilson_lo 0.570 EV+8.59 PF5.32 wf ✅ — 戦略集計レベルで Wilson_lo>0.50 を維持し pip も厚い (micro-scalp でない) 最も健全なエッジ。ただし cell 単位 (USD_JPY BUY 中心) はまだ N<20 で eligible 未達。発火レート改善で 4-6 週後に候補化見込み
- **vsg_jpy_reversal** 戦略集計 N=36 WR69.4% Wilson_lo 0.531。cell 単位 EUR_JPY SELL は依然 N<20 停滞
- **停滞警告 (継続)**: cpd_divergence 16 週連続 0 発火 / mqe_gbpusd_fix clean N=5 で 4 週連続増加ゼロ (raw 87 の 94% が dedup/non-WL 除外) / sr_liquidity_grab raw 2・clean 1 で実質死蔵。signal 発火経路調査を別タスク化すべき段階 (継続提言)

## 判定

**候補 1 件出現 → Pre-reg LOCK は推奨。ただし即時 Live フルロット昇格は非推奨、cross-check ゲートを条件化。**

推奨アクション:
1. **Pre-reg LOCK (Rule 1 開始)**: `sr_anti_hunt_bounce | EUR_JPY | BUY` の仮説 (N=35 WR74.3% Wilson_lo0.579 p_bonf0.0081 PF2.66 kelly0.463) を凍結し pre-reg doc 起票。LOCK 自体は shadow 監査なので実害なし
2. **昇格保留条件 (Live 移行前に要充足)**: (a) 07-17 クラスタを除いた de-clustered / 日次集約ベースでも Wilson_lo>0.50 を維持するか再検証、(b) 次週 run で追加 N がクラスタ外に分散して蓄積し WR が持続するか (persistence)、(c) micro bounce の spread/slippage 耐性を OANDA 実約定 or fidelity BT でクロス確認 (memory: MASSIVE MR は OANDA クロス確認必須)。3 条件通過で初めて Rule 1 フルロット昇格を検討
3. **KB 更新**: 本 candidate 出現を `wiki/audit-index.md` 経由で strategies/sr_anti_hunt_bounce カードに反映
4. その他 6 戦略は依然 N 不足で shadow 蓄積継続。cpd/mqe/sr_liquidity_grab の発火枯渇は別タスク化提言 (継続)
