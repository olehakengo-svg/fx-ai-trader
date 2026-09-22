# Tokyo Nakane Momentum

## Overview
- **Entry Type**: `tokyo_nakane_momentum`
- **Category**: Session / TF
- **Timeframe**: DT 15m
- **Status**: SHADOW (not in any promotion/demotion list)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
LIVE fills: **none** (never reached the live send path; not in `pair_promoted` / `elite_live`)

## Shadow Observation (2026-09-21, [[2026-09-21]])
First substantive shadow sample. Cumulative closed **n=9 / −96.0 pip / WR 33.3%** (2026-09-17 ×1, 2026-09-21 ×8).

| 観測 | 実測 (audit 1500 行窓 = 08-28〜09-21) |
|---|---|
| 総発火 | **16** (08-31 ×4 / 09-01 ×1 / 09-02 ×2 / 09-17 ×1 / **09-21 ×8**) |
| 発火時刻 | **全 16 本が UTC 01 時台 (15) / 02 時台 (1)** |
| 方向 | **16 / 16 すべて BUY — SELL は一度も出ていない** |
| 対象 | EUR_JPY / USD_JPY / AUD_JPY (JPY クロスのみ) |

✅ **どちらも設計と整合し、欠陥ではない**: 上記 Signal Logic の Tokyo fixing (00:55 UTC) 前後という記述に UTC 01–02 時台は合致する。また JPY クロスの BUY = **JPY 売り**であり、仲値に向けた実需の構造的 JPY 売りを取る設計なら片側化は当然の帰結。

🔴 **ただし統計上は重大 — n を独立標本として扱ってはならない**: 2026-09-21 の 8 本は **01:01:20〜02:00:23 の 59 分以内**に 3 通貨ペアへ同時発火した**全 BUY** であり、実質「JPY 売り」1 ベットの 8 重複である。内訳も前半 5 本が全敗 (−23.2 / −13.6 / −22.8 / −17.2 / −17.0)、後半 3 本が全勝 (+1.3 / +1.7 / +7.4) と**時刻で綺麗に二分**され、独立試行ではなく **JPY の方向が途中で転換した 1 イベント**として読むのが正しい。昇格審査に入る際は **クラスタ性を N から割り引く前処理が必須** ([[feedback_partial_quant_trap]])。

⚠️ 勝ち 3 本はいずれも `close_reason` = **`SL_HIT`** = 既知のラベル破綻 ([[project_carrydip_sl_contract_and_slhit_label_2026_08_05]])。本戦略の決済理由集計に `close_reason` を使わないこと。

⚪ `strategy_status` (2026-09-21): `promotion` **pending** / `promo_n` **0** / `enabled` **true** / `blacklisted` **false** / category `daytrade`。shadow 行は promo 母数に入らない設計のため `promo_n` 0 は正常。

## Signal Logic
Tokyo session Nakane (midrate fixing) momentum strategy. Trades directional momentum around the Tokyo fixing time (09:55 JST / UTC 00:55), capturing institutional order flows related to the daily midrate fixing. JPY-focused strategy leveraging Tokyo-specific microstructure.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[2026-09-21]] — 初のまとまった shadow 標本とクラスタ性の指摘
- [[feedback_partial_quant_trap]] — N の独立性を割り引く必要
