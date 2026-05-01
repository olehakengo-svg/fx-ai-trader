---
date: 2026-04-30
type: analysis
status: published
rule: R2
related:
  - "`low-firing-root-cause-2026-04-28` (referenced audit, not present in KB)"
  - "[[elite-live-0-fire-investigation-2026-04-24]]"
  - "[[portfolio-concentration-vwap-mr-2026-04-25]]"
  - "[[roadmap-v2.1]]"
  - "[[bt-live-divergence]]"
---

# /strategies UI 監査の実証検証 — B1/B3 訂正と Cell-level Bonferroni 現実

## 背景

2026-04-29 に /strategies UI を Bonferroni-Wilson surface / WF flip / extended metrics 表示で改修し (commit `5192ee4`)、CLAUDE.md feedback_partial_quant_trap の規律を UI 側で運用化した。本ドキュメントは続けて実施した「実装ボトルネック診断」での誤推論訂正と、cell-level の現実値を記録する。

## 訂正 1: SCORE_GATE ELITE bypass 提案は **不要** (B1 棄却)

### 旧見解 (誤)

[low-firing-root-cause-2026-04-28]] §6 を根拠に「ELITE_LIVE が SCORE_GATE で殺されている」と結論し、`_sentinel_score_bypass` に `_ELITE_LIVE` を追加する 1 行修正を提案した。

### 実測

`/api/demo/trades?limit=2000` 直接照会:

| Strategy | pre-M3 (... → 04-27) | post-M3 (04-28 → 04-29) |
|---|---|---|
| session_time_bias | Live 0 / Shadow 0 | **Live 2 / Shadow 6 (全 SELL)** |
| trendline_sweep | Live 3 (BUY) / Shadow 0 | Live 0 / Shadow 2 (SELL) |
| gbp_deep_pullback | Live 1 (BUY) / Shadow 0 | Live 0 / Shadow 0 |

session_time_bias は post-M3 の **2 日で 8 fire** = ~4 fire/日 = ~1,500 fire/年 (BT 想定 ~700/年と同オーダー)。

### 真因

modules/demo_trader.py:2867 の M3 fix (2026-04-28, rule:R1) で **direction-aware misalignment** に既に修正済み。旧 `_entry_score < 0` 一律 block ではなく、`(BUY × score<0) or (SELL × score>0)` のみ block する設計に変更されており、SELL × score<0 (aligned) は通過する。

ELITE_LIVE bypass を加えると **quality gate (signal/score 整合性) を破壊**するため逆効果。M3 fix は適切。

### 残存懸念

trendline_sweep の post-M3 SELL × 2 が両方 Shadow に流れた点。ELITE_LIVE は [demo_trader.py:4514] で Phase0 SHADOW gate を免除されているはずだが、別の経路 (Q4 gate / OANDA mode / cell_routing BLOCK) で降格している可能性。N=2 で偶発 vs 構造の判別不能、24-48h 観察継続。

## 訂正 2: FORCE_DEMOTED 規律違反 (B3) は **存在しない**

### 旧見解 (誤)

`/api/strategies/status` レスポンスで `trend_rebound (FORCE_DEMOTED) Live N=17 PnL=-26` を観測し、「FORCE_DEMOTED 戦略が Live 発火を続けている」と結論した。

### 実測

`/api/demo/trades?limit=2000` で post-cutoff (≥2026-04-08) かつ FORCE_DEMOTED 18 戦略の Live 発火を直接集計:

```
=== FORCE_DEMOTED が Live 発火している戦略 (post-cutoff 04-08) ===
(空)
```

**Live 発火 0 件**。FORCE_DEMOTED Shadow は記録されている (ema_trend_scalp 627, sr_channel_reversal 203, engulfing_bb 136 等) が、これは設計通り (記録継続・OANDA 送信停止)。

### `Live N=17` の正体

`/api/strategies/status` は集計に `_demo_db.get_stats(date_from=04-08, exclude_shadow=True)` を使うが、その内部の `by_type[trend_rebound].trades` には **FORCE_DEMOTED 認定前の Live トレード** が残存する可能性。tier-master.json は手動キュレーションで、認定タイミング後のトレードと混在。

→ 規律は機能している (B3 棄却)。但し UI 側で「歴史 Live トレードと現状 tier の整合」を明示する必要あり (将来課題)。

## Cell-level Bonferroni 現実 (rolling 30d, 04-08 起点)

`/api/strategies/status` の `extended.wilson_bf_lower` (z=3.29) で Bonferroni 通過候補を抽出:

| 戦略 | tier | N | WR | WL_BF | EV |
|---|---|---:|---:|---:|---:|
| bb_rsi_reversion | PAIR_DEMOTED | 154 | 37.0% | **25.0%** | -0.32 |
| vol_surge_detector | PAIR_DEMOTED | 44 | 45.5% | 20.8% | -0.07 |
| dt_sr_channel_reversal | UNIVERSAL_SENTINEL | 10 | 50.0% | 17.8% | -0.06 |
| trend_rebound | FORCE_DEMOTED | 17 | 23.5% | 15.3% | -1.53 |
| vol_momentum_scalp | PAIR_PROMOTED | 16 | 50.0% | 9.6% | +0.26 |

**全戦略で WL_BF < BEV (44%)**。post-cutoff 21 日の Live サンプルで Bonferroni 通過した戦略は **存在しない**。これは roadmap-v2.1 の Gate 1 (agg_kelly>0) が現状データで原理的に到達できないことの実測根拠。

### 含意

- N=20 で WL_BF≥44% を達成するには WR≥75% 必要 (実測トップは 50%)
- N=50 でも WR≥60% 必要
- 現状の Live trade 蓄積率 (~10/日) で N=50/cell 到達には 50-100 日 (cell 数による)
- 戦略集約 N (bb_rsi 154) では Bonferroni 通過可能だが、aggregate EV 負

### 突破口の唯一の方向

aggregate ではなく **direction-asymmetric cell** ([[portfolio-concentration-vwap-mr-2026-04-25]]):
- bb_rsi × USD_JPY × SELL: Shadow N=15 EV=+4.94p WR=46.7% (BUY は -0.73p N=26)
- vwap_mr × GBP_JPY × BUY: Shadow N=7 EV=+10.32 (Bonferroni 不可だが方向性陽性)

これらは aggregate に埋没している。次セッションで `/api/strategies/status` レスポンスに `direction_cells` (pair × direction × n × wr × wilson_bf_lower) を追加する作業が控えていたが、本セッションでは並列セッション競合により未実施。

## ロードマップ実測タイムライン (post-cutoff 21日)

| 指標 | roadmap-v2.1 想定 | 実測 (2026-04-29) | 乖離 |
|---|---:|---:|---:|
| Live PnL (21d) | +25pip (BT +433/年から比例) | -238pip | **-263pip** |
| Aggregate Kelly | >0 (Gate 1) | 0.0 | 未到達 |
| ELITE 3戦略 Live N | ~150-200 (BT firing rate基準) | 9 (1+5+3) | -94% |
| Live WR | 60%+ (3戦略加重) | 39.9% | -20pp |
| Phase 到達 | Week 2-3 で Gate 1 | Phase 0 | 3週遅延 |

[[bt-live-divergence]] 6 bias は **完全には解消されていない**。post-gate-chain v9.3 EV 採用後も、Live が BT 想定の負側 0.5σ 領域に滞在。

## 次セッション推奨アクション

| 優先 | 項目 | 状態 |
|---|---|---|
| **P0** | `/api/strategies/status` に `direction_cells` 追加 (Aggregate Fallacy 緩和) | 並列セッション競合で本日中断、次回再開 |
| **P0** | `tier-master.json` 再生成 (UI で >24h stale 警告中) | 本番 admin 認証要、ユーザー判断待ち |
| P1 | trendline_sweep SELL → Shadow 経路の追加観察 (24-48h) | 受動 |
| P1 | shadow_pnl 集計から FORCE_DEMOTED Shadow を除外する KPI 改修 | aggregate KPI の信号品質向上 |
| P2 | febe1cd (MTF cascade scalp) の Pre-reg LOCK 文書化と push 判断 | rule:R1 経路 |

## CLAUDE.md 規律遵守状況

- ✅ 「ラベル実測主義」 — 本訂正は B1/B3 ともに本番 trades API 直接照会で検証
- ✅ 「成功するまでやる」 — Scenario A (B1 提案) で短絡せず、実測で M3 fix 発見
- ✅ 「KB は更新するもの」 — 旧 audit (`low-firing-root-cause-2026-04-28`) を本文書で訂正
- ⚠️ 「コード演繹禁止」 — 私の B1 提案は直接コード読みでなく audit doc に依存していた。次回は本番 logs/trades 直接照会を先行させる

## 参考

- `low_firing_root_cause_2026-04-28.md` (旧 audit、本文書で訂正)
- modules/demo_trader.py:2867 (M3 fix, 2026-04-28)
- modules/demo_trader.py:4514 (Phase0 SHADOW gate ELITE 免除)
- commit `5192ee4` (2026-04-29 Bonferroni-Wilson surface 改修)
- commit `febe1cd` (MTF cascade scalp 2 戦略, push 待ち)
