# Aggregate Kelly Decomposition Corrigendum — 2026-05-03 (rev 2)

**Date**: 2026-05-03
**Rule**: R3 (構造バグ訂正、即時)
**Status**: SUPERSEDES `aggregate-kelly-decomposition-2026-05-03.md` の数値部分
**Trigger**: ユーザー指示「LIVEとshadowは必ず切り分けて roadmap の設計もしてください、shadow はデータ蓄積用なので」

## Bottom Line

旧 doc の `Live N=29 (oanda_trade_id != '')` は **誤った数値**。実際の post-cutoff TRUE_LIVE bucket は **N=371 (incl BE) / 346 (WIN/LOSS)**。N=29 は `mode='daytrade'` のみのサブセットで、scalp 各 mode (合計 290 件) が脱落していた。

訂正後は cell-level Bonferroni-powered demote が **可能** になる。surgical demote 経路は閉じていない。

## Filter Ladder Audit (Render API direct, 2026-05-03)

| 段階 | フィルタ | N |
|---|---|---:|
| Render API total | `/api/demo/trades?limit=100000` | 4,872 |
| + CLOSED + WIN/LOSS/BE + ¬XAU | | 4,847 |
| + ¬EUR_GBP | | 4,836 |
| + post-cutoff (`entry_time >= 2026-04-08`) | | 4,330 |
| + Bucket 3-split | TRUE_LIVE / FLAG_DRIFT / SHADOW | 371 / 140 / 3,819 |

### Bucket 3-split (post-cutoff, ¬XAU ¬EUR_GBP)

| bucket | 定義 | N | WR | EV | PnL |
|---|---|---:|---:|---:|---:|
| **1. TRUE_LIVE** | `is_shadow=0 AND oanda_trade_id != ''` | **371** | 39.89% | -0.686 | -254.6 |
| 2. FLAG_DRIFT | `is_shadow=0 AND (oanda_trade_id IS NULL OR = '')` | 140 | 32.86% | -0.946 | -132.4 |
| 3. SHADOW | `is_shadow=1` | 3,819 | 23.72% | -1.305 | -4,985.6 |

`gate-progression-audit-2026-05-03.md` の N=917 は (a) cutoff 未指定 (b) bucket 1 + 2 混合 で構成された数値。R2 demote 判断には使えない。

### N=29 の正体

旧 doc の N=29 は `aggregate_kelly_decomposition_audit.py` 経由で生成されたが、ツール出力 N=346 (WIN/LOSS、TRUE_LIVE) と doc 記載 N=29 に大幅な差。snapshot DB の mode breakdown 検査で `mode='daytrade'` の TRUE_LIVE post-cutoff = 29 と一致 → **mode フィルタが doc 化のどこかで暗黙適用された**。記載者の意図的な subset か post-hoc バグかは未確定。SSOT は **N=346 (WIN/LOSS) または N=371 (incl BE)** に確定する。

## 真の Live Strategy × Pair 出血ランキング (TRUE_LIVE, N≥5)

| 戦略 × ペア | N | WR | EV/trade | PnL | Wilson lo | Tier |
|---|---:|---:|---:|---:|---:|---|
| `vwap_mean_reversion` × GBP_USD | 5 | 20.0% | -11.62 | **-58.1** | 3.6% | FORCE_DEMOTED ✓ |
| `vix_carry_unwind` × USD_JPY | 7 | 28.6% | -6.04 | **-42.3** | 8.2% | PAIR_PROMOTED ⚠️ |
| `sr_channel_reversal` × USD_JPY | 22 | 22.7% | -1.40 | -30.8 | 10.1% | UNIVERSAL_SENTINEL |
| `bb_rsi_reversion` × USD_JPY | 58 | 39.7% | -0.52 | -29.9 | 28.1% | PAIR_DEMOTED 該当ペア? |
| `session_time_bias` × GBP_USD | 7 | 28.6% | -4.00 | **-28.0** | 8.2% | **ELITE_LIVE ⚠️⚠️** |
| `bb_squeeze_breakout` × USD_JPY | 9 | 33.3% | -1.40 | -12.6 | 12.1% | PAIR_PROMOTED ⚠️ |
| `bb_rsi_reversion` × EUR_USD | 12 | 25.0% | -0.97 | -11.6 | 8.9% | PAIR_DEMOTED 該当ペア? |
| `vol_surge_detector` × USD_JPY | 26 | 46.2% | -0.36 | -9.4 | 28.8% | SCALP_SENTINEL |
| `engulfing_bb` × USD_JPY | 9 | 33.3% | -0.83 | -7.5 | 12.1% | PAIR_DEMOTED 該当ペア |
| `engulfing_bb` × EUR_USD | 6 | 16.7% | -0.98 | -5.9 | 3.0% | PAIR_DEMOTED 該当ペア |

### Live で黒字 (旧 doc で誤って「主犯」扱いされた戦略)

| 戦略 | 旧 audit (混入) | TRUE_LIVE (集計) | 判定 |
|---|---|---|---|
| `fib_reversal` (合計) | N=97, EV=-0.44 | USD_JPY: N=13 PnL=-2.3 / EUR_USD: N=13 PnL=+2.6 → **net +0.3** | 主犯ではない |
| `vol_surge_detector` (合計) | N=47, EV=-0.19 | USD_JPY: -9.4 / EUR_USD: +11.6 → **net +2.2** | 主犯ではない |
| `macdh_reversal` | N=62, EV=-0.90 | Live N<5 → Insufficient | 判決保留 |
| `sr_fib_confluence` | N=36, EV=-1.78 | Live N<5 → Insufficient | 判決保留 |

## Tier 整合性異常 (再特定)

| 戦略 × ペア | Tier | Live PnL | 異常 |
|---|---|---:|---|
| `session_time_bias` × GBP_USD | **ELITE_LIVE** | -28.0 (N=7, EV=-4.00) | ELITE 階層が出血源、最優先で WATCH 格上げ |
| `vix_carry_unwind` × USD_JPY | **PAIR_PROMOTED** | -42.3 (N=7, EV=-6.04) | 365d BT EV=+0.506 と大幅乖離 |
| `bb_squeeze_breakout` × USD_JPY | **PAIR_PROMOTED** | -12.6 (N=9, EV=-1.40) | BT data 無し で promote、Live で出血 |
| `vwap_mean_reversion` × GBP_USD | **FORCE_DEMOTED** | -58.1 (N=5) | tier と整合 (既に止血中) |

## Decision (rule:R3)

1. **N=29 SSOT 訂正**: `wiki/index.md` System State の Live N=29 を `N=371 / 346` に書換。`oanda_trade_id != ''` を主条件に bucket 3-split 表示
2. **R2 候補リスト書き換え**: `1815-r2-strategy-instrument-counterfactual` の主犯6戦略を本 corrigendum の TRUE_LIVE × pair リスト (上の N≥5 出血表) に差し替え
3. **ELITE_LIVE 緊急 WATCH**: `session_time_bias × GBP_USD` を WATCH 格上げ、N=10 で再評価、N=15 で demote 判断
4. **PAIR_PROMOTED Live 検証**: `vix_carry_unwind × USD_JPY` / `bb_squeeze_breakout × USD_JPY` の BT-Live 乖離調査を別タスク化
5. **`is_shadow=0` 単独使用禁止 (memory feedback)**: `feedback_live_vs_shadow_strict_separation` 保存済み、以後の audit ツール実装は bucket 3-split を必須化

## Open Questions

- `gate-progression-audit-2026-05-03.md` の表 (bb_rsi_reversion N=324 EV=-0.15 等) は使い物にならない。再 audit 別タスクで TRUE_LIVE bucket only に書き直す
- `mode='daytrade'` フィルタが旧 doc に暗黙適用された経路の特定 — `aggregate_kelly_decomposition_audit.py` のロジックには明示的な mode フィルタは無い。doc 化時の手書き bug の可能性が高い
- `oanda_trade_id != ''` の prefix 検査では全 371 件が numeric (150360〜382563)、prefix bug は無し。本物の OANDA 約定 ID
- FLAG_DRIFT 140 件の write-path bug 根治 (`oanda-passthrough-gap-2026-05-03` extension)

## Related

- 旧版: `aggregate-kelly-decomposition-2026-05-03.md` (数値部分は本 corrigendum で SUPERSEDE)
- Tools:
  - `tools/aggregate_kelly_decomposition_audit.py` (要修正: bucket 3-split 出力 + mode breakdown 必須化)
  - `tools/render_trades_snapshot.py` (snapshot 生成、本日 17:26 取得)
- Lessons:
  - `feedback_live_vs_shadow_strict_separation` (memory)
  - "集計値は必ずセグメント分解する。平均値は嘘をつく"
  - "`oanda_trade_id IS NOT NULL` で集計する」が正しい live 判定"
- Source: Render API direct fetch 2026-05-03 18:30 JST
