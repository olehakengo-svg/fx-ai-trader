---
date: 2026-05-03
task: 20260503-1840-tier1-live-edge-audit
verdict: NEEDS_MORE_EVIDENCE (Tier 1 cell N不足) / **ROUTING_ANOMALY exposed** (新発見)
rule: R2
gate: Gate 0 (生存) — Tier 1 promotion 経路自体に構造問題発覚
---

# Tier 1 LIVE Edge Audit — Routing Anomaly Discovery

## Verdict (Codex deliverable)

**ACCEPT** — 仕様通り 5 Tier 1 / PAIR_PROMOTED cell を Live/OANDA filter で計測、Bonferroni m=5 (α'=0.010) 適用。

## Verdict (H4 Tier 1 edge 検証)

**NEEDS_MORE_EVIDENCE** — 5 cell 全てで Live/OANDA N<30 (合計 7 件)、統計検定不能。

## 想定外発見 — ELITE_LIVE 発火率 0.5%

| cell | BT N (180-365日想定) | Live/OANDA N | 発火率 |
|---|---:|---:|---:|
| gbp_deep_pullback × GBP_USD | 77 | 3 | 3.9% |
| trendline_sweep × GBP_USD | 134 | 4 | 3.0% |
| session_time_bias × USD_JPY | 157 | 0 | 0.0% |
| session_time_bias × EUR_USD | 566 | 0 | 0.0% |
| xs_momentum × USD_JPY | 342 | 0 | 0.0% |
| **計** | **1276** | **7** | **0.5%** |

## Aggregate landscape

| bucket | N | WR | EV | raw Kelly |
|---|---:|---:|---:|---:|
| 全 Live/OANDA | 736 | 38.86% | -0.81 | -0.1854 |
| Tier 1 target 5 cells | **7** | 57.14% | -2.46 | -0.8190 |
| 非 Tier 1 OANDA 行 | **729** | 38.68% | -0.80 | -0.1810 |

→ **OANDA で 736 件約定中、Tier 1 target は僅か 7 件 (0.95%)**。残り 729 件は非 Tier 1 戦略が OANDA pathway に流入している。

## Root cause 仮説

1. **Routing eligibility lag**: `tier-master.md` で ELITE_LIVE 表記でも、`app.py:_phase_gate` / OANDA bridge dispatch logic が他条件で発火を阻害
2. **Cell granularity mismatch**: Tier 1 promotion は (strategy × pair) で行ったが、実際の signal 発火は hour bucket / regime / VIX 等の追加条件依存
3. **Shadow→Live promotion gap**: Shadow 段階では発火しているが Live promotion (= OANDA bridge 通過) で gate が落としている
4. **過去 BT N の cohort 異質**: 365日 BT N=566 (session_time_bias EURUSD) は集計時のもので、現状の市場 regime では発火条件不成立

## Roadmap impact

**Tier 1 promotion システム自体への信頼性危機**:
- ELITE_LIVE 認証された 5 cell (4 戦略) のうち 3 cell が現実 OANDA で発火不在
- 月利100% ロードマップ v2.1 の前提 (ELITE_LIVE 3戦略で +433pip/年) は **構造的に成立不能**
- 現実の OANDA 損失 (-720p/30日) は非 Tier 1 戦略由来 → "ELITE" 認証無関係に Live は劣化中

## Risks

- Codex sandbox curl 失敗 → `/tmp/live-trades-20260503.json` (17:26 mirror) 使用、最新 Render API でない
- Live N<30 で本 audit からは Tier 1 edge の真贋を統計的に証明不能

## Next task — Path A (immediate, routing 解明)

**`shadow-live-oanda-pathway-audit-2026-05-03`**:
- ELITE_LIVE 5 cell が `is_shadow=1` (Shadow) で発火している件数 vs `is_shadow=0 oanda_trade_id != ''` (OANDA約定) 件数を時系列比較
- `app.py:_phase_gate` / `_dispatch_to_oanda` / `oanda_bridge` の各 stage で各 cell の trade が drop している点を特定
- `live_ng_cells` SQLite の影響、Spread/SL Gate / Aggregate Kelly Gate / MC ruin Gate の同時発動有無を確認

## Next task — Path B (parallel, BT-Live divergence RCA)

`bt-live-divergence-systematic-audit-2026-05-03`:
- N が積み上がっている **非 Tier 1 戦略 729 件** を対象に BT 期待値と Live 実測の divergence パターンを系統分析
- memory `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` の 6 楽観バイアス監査を `wiki/analyses/bt-live-divergence.md` 通りに展開
- 最終的に「現状の摩擦モデル / regime / cohort で BT promote 基準は信頼可能か」を判定

両 path は disjoint scope で並列可能。Path A が一次的 (routing が壊れていれば BT は無関係)、Path B が二次的 (routing 健全でも BT-Live 楽観バイアスがあれば月利目標到達不能)。
