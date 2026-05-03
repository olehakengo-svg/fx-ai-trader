# S3 (CFTC TFF Dealer Change-of-Position) — 完全棄却決定 2026-05-03

## Verdict: REJECT (Scenario C)

W3-5 Pair-Pool BH FDR BT (12.3 年, 6 pair, m=6, q=0.10) で **全 pair で BH FDR-significant 0 件 + matrix v1 §2 B+ 帯通過 0 件**。Wave 4 で予定していた extreme decile cohort sanity も USDJPY で **PF=0.80, Kelly=-0.12, p=0.66** と reject。S3 戦略の復活経路は完全に閉鎖。

## Rule

R1 (Slow & Strict, 棄却判定 — 採用方向ではないが pre-reg LOCK 経由の reject なので Rule 1 として記録)

## 判定 evidence (詳細)

| Pair | N | PF | Wilson_lo | Sharpe | Kelly | p-value | BH q (m=6) |
|---|---|---|---|---|---|---|---|
| USDJPY | 393 | 1.162 | 46.22% | 0.39 | 0.071 | 0.140 | 0.842 |
| USDCAD | 410 | 1.115 | 44.70% | 0.30 | 0.051 | 0.199 | 0.595 |
| EURUSD | 357 | 1.087 | 45.26% | 0.23 | 0.040 | 0.273 | 0.546 |
| GBPUSD | 400 | 1.053 | 44.63% | 0.14 | 0.025 | 0.354 | 0.531 |
| NZDUSD | 381 | 0.937 | 42.80% | -0.18 | -0.032 | 0.687 | 0.825 |
| USDCHF | 352 | 0.835 | 43.40% | -0.49 | -0.096 | 0.898 | 0.898 |

- **BH FDR (q=0.10, m=6) 通過**: 0 pairs
- **Matrix v1 §2 B+ 帯通過**: 0 pairs
- **Null bootstrap PASS**: False (全 6 pair)
- **Wave 1 regression**: PASS (PF dev 3.56%, Wilson dev 1.67%) → 実装バグではない
- **Regime concentration flags**: 全 pair empty → 単一年集中の overfitting でもない

## 経緯 (Wave 1 → Wave 2 → Wave 3)

- **Wave 1** (2026-05-03 W1, `project_s3_cot_dealer_bt_2026_05_03`): USDJPY 単独 literal で PF=1.21, Wilson lo=0.470 → B-marginal verdict, Bonferroni m=224 で reject
- **Wave 2** (`s3-s5-combined-bt-2026-05-03.md`): S3×S5 HMM 結合 BT abandon (`feedback_hmm_gate_same_trap` 罠で edge 消滅), S5 は Wave 3 保留, S3 limited cohort variants は Wave 3 hand-off
- **Wave 3 (本決定)**: pair-pool BH FDR (m=6 で Bonferroni m=224 より緩めた cherry-pick 防御) でも全 reject + extreme decile sanity も reject

## ロードマップ反映

- catalog §F-1 (Wave 1 review document, `wiki/learning/codex-review-wave1-2026-05-03.md`) のステータス: **B-marginal hold → REJECT (Wave 3 pair-pool FDR で全棄却)**
- S3 の Shadow promote 候補ステータス: **削除**
- `wiki/index.md` / `wiki/tier-master.md`: S3 関連戦略 (s3_cot_dealer 等) は Tier Master に未登録 (Shadow promote 前段階で停止) のため変更不要

## 学習事項 (`wiki/lessons/` 候補)

- **Wave 1 単独 pair PF=1.21 は cherry-pick 由来**: 224 試行 (EarnForex の試行全数) を母集団とすると、6 pair pool に拡げただけで signal が消える。Wave 1 では Bonferroni m=224 で B-marginal だったが、実は **m=6 の BH FDR でも reject** だった (USDJPY p=0.14, BH q=0.84)
- **EarnForex 公開実証 (literal Dealer change-of-position) は post-2014 で decay 確定**: Wave 1 reference 文献は 2014 以前データの可能性、現代の market microstructure (HFT/algorithmic dealer rebalancing) では同シグナルは alpha を持たない
- **inversion clause vs literal の議論は moot**: Wave 1 で literal が正しい方向と確定したが (`project_s3_cot_literal_no_inversion`)、結局 literal でも edge なしのため、方向論争は今後 S3 復活案件が出ない限り言及不要

## 危険操作 / 安全性

- Live/Shadow/OANDA データ非参照 (BT only, `live_separation="bt_only"`)
- 本番 DB / `.env` / OANDA secret 非接触
- Wave 1 reference docs は親 `/Users/jg-n-012/test/wiki/learning/` 配下にあるが、本決定は fx-ai-trader 内 BT 結果のみで判断 (locale 不一致は data prep の課題で、判定そのものに影響なし)

## Hand-off

- **dexter FX Phase 0 cot_report ツール** (`/Users/jg-n-012/dexter test/`) は本タスクで実戦投入され、Socrata API 経由で 6 pair × 643 weekly rows の完走を確認 (**fetcher として動作 OK**)。fx-ai-trader 本体への統合判断は別議題 — S3 alpha 棄却とは独立に **macro context 取得ツール** としての価値がある可能性 (例: positioning extremes の risk monitoring)
- Wave 4 では S3 系統に時間を割かず、別 alpha source (S6+ または scalp 枝再活性化) に集中

## 関連

- 親プラン: `find-out-way-of-fizzy-patterson.md`
- Wave 1: `wiki/learning/s3-cot-dealer-bt-2026-05-03.md`
- Wave 2: `wiki/learning/s3-s5-combined-bt-2026-05-03.md`
- Wave 3 BT: `knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.{json,md}`
- Wave 3 learning: `wiki/learning/s3-pair-pool-fdr-bt-2026-05-03.md`
- dexter サイドカー: `project_dexter_fx_phase0_2026_05_03`
