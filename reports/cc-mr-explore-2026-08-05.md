# #21 commodity_cross_range_mr — explore verdict: ❌ FAIL (2026-08-05)

**pre-reg**: `knowledge-base/wiki/decisions/cc-mr-explore-prereg-2026-08-05.md` (凍結 `1913f958`、pass-1 `1b4ece1b`)
**敵対的検証**: `knowledge-base/raw/analysis/wave6-cc-mr-adversarial-verification-2026-08-05.md` (GO-WITH-CONDITIONS 21 条 — 全消化)
**raw**: `knowledge-base/raw/bt-results/cc-mr/` (pass-1/pass-2 JSON + events CSV + manifest + crosscheck)
**OOS 2022+ 非接触のまま封印** (シグナル計算ゼロ)。

## verdict サマリ

**FAIL — gate C (primary) + gate D (stressed-net) の同時不通過。** 「方向は合うが弱い」slow-MR 死型家系の **4 例目** (ppp IC+0.113 p=0.129 / quote-spread −0.24σ p=0.32 / round-number +6.3p p=0.117 / **cc-mr +3.96p p=0.266**)。負の prior が正確に的中した、正直にゲートされた kill。

| gate | 結果 | 判定 |
|---|---|---|
| A headroom | MFE5 p50 = AUD_NZD **51.0p** / AUD_CAD **62.4p** / NZD_CAD **78.2p** (必要 38.0/37.0/39.0) | ✅ 3/3 生存 |
| B power | events **255** / blocks **140** (floor 120/50)、MDE 再計算 **14.5p** (robust σ_5d 実測 ~93p) | ✅ |
| C primary | pooled mean fade net5d = **+3.96p**、2-ISO-週 block sign-flip 10k (seed 20260805) 片側 **p = 0.266** | ❌ |
| D stressed-net | net − RT − swap = **−3.71p (adverse m)** / −3.11 (point) / **−2.59 (favorable 端でも負)** | ❌ |
| E 集中 | max block share **3.5%** | ✅ |
| F 一貫性 | 年次符号 **6/8** + LOYO **8/8** 正。2014-15 デシンク副窓 mean **−5.6p** (2014 単年 **−22.6p** = regime-kill prior 実証) | ✅ |
| G coherence | per-pair 符号 2/3 (AUD_NZD +7.9 / NZD_CAD +9.0 / AUD_CAD **−4.6**)。サイド kill 不発 (L +1.8p n=149 / S +7.0p n=106) | ✅ |
| knife-edge | 実行なし (全 gate PASS 時のみの規定) | — |

## 診断 (非拘束)

- **Spearman IC(z, fwd5d)**: AUD_NZD **−0.128** / AUD_CAD −0.062 / NZD_CAD −0.088 — 方向は MR 整合、家系典型の弱さ。**L-d 裁定の IC-first 字義履行はこれで discharge** (選択不使用)。
- **skip 版 (live-feasibility)**: n=198、mean **+6.4p** — 全 onset 測定 (+3.96p) より見かけが良い。**条件 11 (skip 禁止) が阻止した PASS 方向バイアスの実測例**として記録。
- overlap share 25.5% / 同週 co-fire 25.7% / MAE5 p50 68.9p / D1 close-to-close mean: AUD_NZD +5.2 / AUD_CAD −2.6 / NZD_CAD +7.3。
- **合成 RW null 較正 (post-freeze 追加・開示済み・実データ非接触)**: driftless GBM 400 sims で mean fade net5 = **−0.87p ± 0.53 (SE)** — エスティメータに端点選択バイアスなし (委譲元 wave-6 セッションの検査観点、seed 99920260805)。観測 +3.96p は実効果だが小さすぎる。
- **条件 8 照合**: OANDA 独立 D1 (NY17 align) の AUD_NZD onset = **87 = pass-1 87 (偏差 0.0%)** — D1 再構築/シグナル系統の妥当性確認。
- **markup 追加データ点**: 2026-08-05 の OANDA financing 実測 (委譲セッション提供、read-only) implied m ≈ 1.08-1.09%/yr — 凍結較正値 (point 1.075-1.155 / adverse 1.65-1.73) と整合。gate D は favorable 端でも負のため markup 較正は verdict 非支配的。

## 解釈

raw エッジ +3.96p は (i) MDE 14.5p の約 1/4、(ii) 摩擦+swap 実コスト (RT 3.7-3.9p + fade-SHORT swap drag ~1-3p/イベント) 未満。最良ペア NZD_CAD (+9.0p) 単体でも per-pair claim は §5 恒久禁止であり、家系サイズの効果は設計どおり構造的に FAIL する (意図された retail-viability filter)。2014 年 −22.6p は RBA/RBNZ デシンク regime-kill の事前警告どおり — OOS (2022-24 デシンク主体) に進んでいれば同型の死に方をした公算が高い。

## クローズ範囲 (pre-reg §9 / 条件 20 — 事前凍結どおり発効)

**「slow location-anchor (mean / percentile / regression) band fade × multi-day × AUD_NZD/AUD_CAD/NZD_CAD、全 anchor 着せ替えを含む — variant B (H1 range-percentile + D1 trend veto) を明示的に含む」を FAIL クローズ。** B の復活経路 = 新 family + 事前差分節 + 新規敵対的検証のみ。再試行・着せ替え禁止。

## 残置インフラ

- 3 クロス 1h parquet の被覆修復 (2013-01-13 起点) + ベンダー穴 backfill (+2,177 行) + `tools/cc_mr_gap_backfill.py` — 恒久データ基盤。
- `tools/cc_mr_explore.py` — NY17 D1 再構築 + evening-grid entry + 2-ISO-週 block permutation ハーネス (将来の D1 系 explore に流用可)。
- cc-g0-rt 日次 financing sampler (Render cron) は稼働継続 — 将来 family の swap 較正基盤。
