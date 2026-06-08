# D1 Time-Series Momentum Basket — pre-reg BT verdict (2026-06-08)

**Verdict: NULL** (primary 12m, net). 投入しない。
**Rule**: R1 | **Pre-reg**: `.ai/plans/claude/20260608-2040-d1-tsmom-basket-pre-reg-bt.md`
**実装**: `tools/tsmom_basket_bt.py` (Claude 一次実装) | **結果**: `raw/bt-results/tsmom_basket_2026_06_08.json`

## データ
- 8 pair 固定 (EUR_USD/USD_JPY/GBP_USD/AUD_USD/USD_CAD/USD_CHF/NZD_USD/EUR_JPY)
- D1 MASSIVE、2016-04-18 → 2026-06-08、3310 bars、trading-day completeness 100%
- (Phase 0 で `fetch_massive_data.py` に `1d` TF サポート追加、8 pair backfill 済)

## 結果 (net、friction 1.0pip/turnover)

| L | Sharpe g/n | Ann(net) | maxDD | t(net) | p_bonf (m=4) | 月次WR Wilson_lo |
|---|---|---|---|---|---|---|
| 1m | -0.36/-0.39 | -1.8% | -23.3% | -1.40 | 0.65 | 0.347 |
| 3m | -0.17/-0.18 | -0.9% | -19.4% | -0.65 | 1.00 | 0.347 |
| 6m | -0.52/-0.53 | -2.5% | -31.6% | -1.91 | 0.22 | 0.316 |
| **12m (primary)** | **-0.01/-0.02** | **-0.2%** | **-10.9%** | **-0.07** | **1.00** | 0.378 |

WF (12m net, 3 folds): fold1 (2016-19) **−** / fold2 (2019-23) + / fold3 (2023-26) +。**3/3 不成立**。

判定ゲート: `p_bonf < 0.05 ∧ WF 3/3 + ∧ Sharpe > 0` → **全滅**。

## なぜ NULL か (実装健全性確認済)

silent bug ではない (sanity: avg gross exposure 0.918、long/short 均衡 ~12k each、flat はウォームアップ273日のみ)。ペア別 ann gross 寄与は全て極小・符号混在で合計 **−0.0005** = **gross ですらエッジ無し**。これは [[project_cell_edge_deep_audit_2026_06_08]] の「gross EV≈0」と同じ景色が高 TF risk-premia でも出たことを意味する。

2つの構造要因 (本サンプル固有):
1. **2016-2026 は documented TSMOM-hostile regime** — 2010年代以降 FX trend premium は圧縮 (中銀緩和・低ボラ・レンジ)。古典的 TSMOM プレミアムは主に 2008 以前。10年は単一レジーム寄り。
2. **USD 集中** — net USD エクスポージャが gross の **54%**。8 pair 中 6 が USD pair のため「分散バスケット」の実体が単一 USD 方向ベットに縮退。真の分散には cross-rate が要る。

## 再検証角度 (別セッション、post-hoc rescue にしない)

本 pre-reg は NULL で**確定・クローズ**。以下は新規 pre-reg として別途立てる候補 ([[feedback_success_until_achieved]]: closure 短絡せず深掘りは別セッション):
- **v2: cross-rate 込みバスケット** で USD 集中を解く (EUR_GBP/AUD_JPY/GBP_JPY 等を追加し USD net を中立化)
- **長期履歴** (2016 以前を別ソースで遡れるか) で regime バイアス検証
- **excess-return ベース** (carry 控除後) の純 momentum

これらは「結果が悪かったから条件を変える」探索ではなく、**事前に弱点を特定した構造仮説**。実行は本 NULL の確定後に独立 pre-reg で。

## 関連
- [[project_risk_premia_pivot_2026_06_08]] — 3脈 pivot のうち本命だったが NULL
- [[project_w3_5_s3_pair_pool_fdr_queued]] — 同様に「再現バグ無し、棄却は本物」の前例
