# SFT-1 Research Summary — structural-flow literal BT

Date: 2026-05-04
Scope: research-only Wave 1. No `strategies/**`, `demo_trader.py`, or `app.py` implementation was changed.

## Verdict Table

| Strategy | Status | Scenario | N | Wilson_lo | PF | Bonf p | Kelly | Max DD pip | Null boot p | Single-year concentration | 2x spread Wilson_lo | 2023-04..2026-04 N / Wilson_lo |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| month_end_usd_rebalance_short | BLOCKED_DATA | BLOCKED | 156 | 0.391360 | 0.813952 | 1.000000 | 0.000000 | 501.2 | 0.823000 | 78.16% | 0.336127 | 49 / 0.432702 |
| tokyo_fix_955_jpy_demand | OK | C | 2948 | 0.425841 | 0.713587 | 1.000000 | 0.000000 | 6637.6 | 1.000000 | 13.58% | 0.364579 | 753 / 0.413694 |
| quarter_end_jpy_repat | OK | D | 23 | 0.156038 | 0.475610 | 1.000000 | 0.000000 | 816.2 | 0.907000 | 44.20% | 0.125484 | 6 / 0.187613 |

## Notes

- SFT-A is blocked for the required pooled 12y test because `EUR_USD_5m.parquet` and `GBP_USD_5m.parquet` only cover 2025-10-14 .. 2026-04-15. USDJPY-only partial evidence is not enough for the primary cell.
- SFT-B ran on 12y USDJPY M5 with Japanese business-day calendar fallback. Literal 9:55 JST demand failed PF/Wilson/Bonferroni/bootstrap axes.
- SFT-C ran on 12y USDJPY M5 with intervention-date exclusion. N=23 remains too thin and negative; no-exclusion sensitivity is in JSON.
- NSG-1 is marked `DEFERRED` in each report because its implementation task is separate/in-flight; these reports should be re-read after NSG-1 acceptance if any candidate is reconsidered.

## Wave 2 Boundary

Wave 2 implementation is out of scope for this task. Claude Code should read these verdict reports and decide separately whether to launch any implementation task; current evidence does not justify direct Wave 2 start.

---

## Claude 司令塔 verdict (2026-05-05)

**REJECT 全 3 候補。Wave 2 起動なし。**

理由:
- **SFT-B (tokyo_fix_955_jpy_demand)**: N=2948 と十分な sample で Scenario C confirm。PF=0.71 (損失方向)、Wilson_lo=0.43 (BEV 未達)、null bootstrap p=1.000。これは**本物の no-edge** であり data 不足ではない。
- **SFT-C (quarter_end_jpy_repat)**: N=23 + Wilson_lo=0.156 + Single-year concentration 44.20% で evidence-thin AND negative。介入除外後も改善せず。
- **SFT-A (month_end_usd_rebalance_short)**: 12y MASSIVE EUR_USD/GBP_USD 拡張前は BLOCKED。但し USDJPY 単独 N=156 partial で Wilson_lo=0.39 / PF=0.81 / single-year 78.16% concentration → 既に negative direction。データ拡張で改善する見込みなし (single-year concentration が高すぎ)。

**結論**:
- Qiita 記事②の「構造的制約」エッジ (月末リバランス / fix flow / 期末リパトリ) は **HFT に取られている説が実証**。現代の流動性下では生存していない。
- 3 候補すべて catalog **§academic only 降格**。新 tier `Structural Flow` の `tier-master.md` 追加は撤回。
- Wave 2 (実装着手) は永続的 NO-GO。再評価の trigger は: (a) 新 calendar event 仮説、または (b) 流動性構造の質的変化 (例: 中央銀行政策大転換) のみ。
- データ拡張 (MASSIVE EUR_USD/GBP_USD 12y) は別目的 (VFO-1 Task B 拡張、他戦略 BT) のために有用だが、SFT-1 の re-run は不要。

**Memory link**: `project_qiita_gap_analysis_2026_05_04.md` に SFT-1 REJECT verdict 反映済。
