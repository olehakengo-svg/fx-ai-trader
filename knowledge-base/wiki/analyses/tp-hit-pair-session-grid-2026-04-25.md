# TP-hit Pair × Session Grid — 勝利条件の数学的分析 (2026-04-25)

## TL;DR

post-cutoff 17 日 (2026-04-08〜04-24) の closed N=2,494 (Live+Shadow, ex-XAU/BREAKEVEN/WEEKEND) を **pair × session bucket × side** で 36 cells に分解し、TP-hit を抽出。**構造的勝利条件は満たされていない**:

- 全 16 cells (N≥50) で **BEV_TP% > actual_TP%** — どの cell も R:R 構造に対する TP-rate が不足
- Per-pair の摩擦調整 BEV gap: **USD_JPY -10.4pp / EUR_USD -12.0pp / GBP_USD -15.8pp / GBP_JPY -18.9pp / EUR_JPY -39.9pp** (全マイナス)
- Bonferroni (α_cell=1.85e-3) を通過する正方向 cell は **USD_JPY × NY-overlap × SELL のみ** (TP=33.9%, p=1.85e-3) だが EV=-0.35p で BEV 未達
- 唯一の hour-level 強 cell: **USD_JPY × hr19 UTC × BUY** (TP=44.8%, EV=+3.29p, N=29, NY-late)
- **Phase 3 stopping rule / Phase 4 新戦略設計判断の主要材料**: 現ポートフォリオは構造的に positive expectancy を持たない (TP-hit 軸での検証)

## 1. データ窓・フィルター

| 項目 | 値 |
|---|---|
| 取得元 | `GET /api/demo/trades?status=closed` (paginated 4 page, 3,296 records) |
| 取得時刻 | 2026-04-25 13:07 UTC |
| Window | post-cutoff broad: `exit_time >= 2026-04-08T00:00:00` |
| 除外 | `outcome=BREAKEVEN`, `close_reason=WEEKEND_CLOSE`, `instrument contains 'XAU'` |
| TP-hit 定義 | `close_reason ∈ {TP_HIT, OANDA_SL_TP} AND outcome='WIN'` |
| Universe N | **2,494** (TP-hit=624, baseline 25.02%) |
| Live/Shadow 分布 | Live ~270 / Shadow ~2,224 (post-04-08 broad) |

> Cutoff 選定: post-04-16 narrow では Live N=19 で cell-level 検証が不能。broad 04-08 (post Patch C 直後の clean window) を選択。Live trades は ELITE_LIVE / PAIR_PROMOTED 通過後のため selection effect が混入する点に注意 (§8)。

## 2. 勝利条件の数学的定式化

trade 単位 EV を 3 outcome に分解:

```
EV(p) = TP_rate × R_win × R_unit
      + SL_rate × R_loss × R_unit
      + Other_rate × E_other(p)
      - friction(p)
```

R_unit = 1R = SL pip 距離。`other` は TIME_DECAY_EXIT / SIGNAL_REVERSE / MAX_HOLD_TIME 等。

**簡易 BEV (other を SL_rate に統合)**:
```
TP_rate_BEV = |mean_loss| / (mean_win + |mean_loss|)
```

R:R = mean_win / |mean_loss|. 観測値 R:R ≈ 1.5〜2.0 → BEV_TP% ≈ 33〜40%。

**勝利条件 3 要素** (cell が "winner" と判定される必要十分):
1. TP-rate ≥ BEV_TP% (R:R 構造との整合)
2. 摩擦控除後 mean EV > 0
3. Live × Shadow 同符号 (Live 単独の curve fit でない)

## 3. ベースライン

### Per-pair baseline (post-04-08 closed)

| Pair | N | TP_count | TP_rate | mean_EV | friction | BEV_TP% | margin |
|---|---:|---:|---:|---:|---:|---:|---:|
| USD_JPY | 1,375 | 373 | 27.1% | -0.99p | 2.14p | 37.5% | **-10.4pp** ✗ |
| EUR_USD | 578 | 150 | 26.0% | -1.16p | 2.00p | 38.0% | **-12.0pp** ✗ |
| GBP_USD | 436 | 90 | 20.6% | -2.11p | 4.53p | 36.5% | **-15.8pp** ✗ |
| EUR_JPY | 82 | 7 | 8.5% | -7.74p | 2.50p | 48.4% | **-39.9pp** ✗ |
| GBP_JPY | 22 | 4 | 18.2% | -1.92p | 3.00p | 37.1% | -18.9pp ✗ |

→ **5/5 pair で BEV gap がマイナス**。最も摩擦の薄い USD_JPY ですら 10.4pp 不足。

### Per-session-bucket baseline (UTC)

| Bucket (UTC) | N | TP_rate | mean_EV |
|---|---:|---:|---:|
| Tokyo (00-06) | 396 | 22.7% | -1.94p |
| London (06-12) | 857 | 25.1% | -1.33p |
| NY-overlap (12-17) | 971 | **26.5%** | -1.49p |
| NY-late (17-24) | 270 | 23.0% | -1.00p |

NY-overlap が最高 TP-rate だが、いずれも baseline 25% 周辺で session 軸単独では弱い。

## 4. Cell グリッド (Pair × Session × Side, N≥50)

| Pair | Bucket | Side | N | TP% | R_win | R_loss | R:R | BEV_TP% | EV(p) | 判定 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| USD_JPY | NY-overlap | SELL | 230 | **33.9%** | +1.69 | -0.99 | 1.71 | 36.9% | -0.35 | NEAR-BEV |
| USD_JPY | London | SELL | 206 | 31.1% | +1.88 | -0.96 | 1.95 | 33.9% | -0.54 | NEAR-BEV |
| USD_JPY | NY-overlap | BUY | 218 | 25.7% | +1.51 | -0.99 | 1.53 | 39.6% | -1.51 | NEGATIVE |
| USD_JPY | London | BUY | 186 | 25.8% | +1.64 | -0.98 | 1.67 | 37.5% | -1.18 | NEGATIVE |
| USD_JPY | Tokyo | BUY | 166 | 27.1% | +1.40 | -0.88 | 1.58 | 38.7% | -0.52 | NEGATIVE |
| USD_JPY | Tokyo | SELL | 160 | 23.1% | +1.54 | -0.92 | 1.68 | 37.3% | -1.85 | NEGATIVE |
| EUR_USD | NY-overlap | BUY | 173 | 27.2% | +1.43 | -0.90 | 1.59 | 38.7% | -1.38 | NEGATIVE |
| EUR_USD | London | BUY | 151 | 29.1% | +1.57 | -0.93 | 1.69 | 37.2% | -0.89 | NEGATIVE |
| EUR_USD | NY-overlap | SELL | 141 | 27.0% | +1.80 | -1.00 | 1.80 | 35.7% | -0.82 | NEGATIVE |
| USD_JPY | NY-late | BUY | 118 | 24.6% | +1.45 | -0.90 | 1.61 | 38.3% | -0.65 | NEGATIVE |
| EUR_USD | London | SELL | 113 | 18.6% | +1.54 | -0.92 | 1.67 | 37.4% | -1.59 | NEGATIVE |
| GBP_USD | London | BUY | 107 | 23.4% | +2.07 | -0.89 | 2.33 | 30.0% | -1.18 | NEGATIVE |
| GBP_USD | NY-overlap | BUY | 100 | 20.0% | +1.85 | -0.90 | 2.05 | 32.8% | -2.71 | NEGATIVE |
| USD_JPY | NY-late | SELL | 91 | 17.6% | +1.64 | -0.89 | 1.84 | 35.2% | -1.76 | NEGATIVE |
| GBP_USD | London | SELL | 65 | 12.3% | +1.52 | -0.96 | 1.59 | 38.6% | -3.15 | NEGATIVE |
| GBP_USD | NY-overlap | SELL | 64 | 23.4% | +1.27 | -0.88 | 1.44 | 41.0% | -2.54 | NEGATIVE |

**全 16 cells で BEV_TP% > actual_TP%** — 16/16 NEGATIVE/NEAR-BEV。最も惜しい:
- USD_JPY × London × SELL: 31.1% vs BEV 33.9% (gap -2.8pp、small loss)
- USD_JPY × NY-overlap × SELL: 33.9% vs BEV 36.9% (gap -3.0pp、small loss)

両方とも **USD_JPY SELL** 系。これは hour-level (§6) でも一貫。

### N=20-50 帯 (低 N でも positive EV を示す cells)

| Pair | Bucket | Side | N | TP% | EV(p) | 注 |
|---|---|---|---:|---:|---:|---|
| GBP_USD | NY-late | SELL | 32 | 31.2% | **+0.32** | only positive EV cell N≥30 |
| GBP_USD | NY-late | BUY | 20 | 30.0% | **+0.70** | N small but encouraging |

GBP_USD × NY-late 双方向で positive — 監視候補。

## 5. Bonferroni-corrected 仮説検定

M = 27 (eligible cells N≥30), α_cell = 0.05 / 27 = **1.85e-3**.
Z-test: H0: TP-rate = baseline 25.02%, H1: ≠.

| Cell | TP% | z | p | Bonferroni 通過 |
|---|---:|---:|---:|:---:|
| USD_JPY × NY-overlap × SELL | 33.9% | +3.11 | 1.85e-3 | **★ ✅ ジャストパス** |
| USD_JPY × London × SELL | 31.1% | +2.00 | 4.5e-2 | ✗ |
| EUR_USD × London × BUY | 29.1% | +1.17 | 2.4e-1 | ✗ |
| EUR_JPY × London × BUY | 5.0% | -2.07 | 3.9e-2 | ✗ (negative) |
| GBP_USD × London × SELL | 12.3% | -2.37 | 1.8e-2 | ✗ (negative) |

唯一の Bonferroni 通過 cell **USD_JPY × NY-overlap × SELL** ですら EV=-0.35p で **BEV 未達**。**TP-rate が高くても R:R が不足する** 構造。

## 6. Hour-by-hour Heatmap (USD_JPY, N≥10)

| UTC | side | N | TP% | EV(p) | flag |
|---:|:---|---:|---:|---:|:---|
| 0 | SELL | 33 | 39.4% | -0.18 | ★ |
| 8 | BUY | 31 | 35.5% | +0.05 | ★ |
| 8 | SELL | 28 | 39.3% | +0.83 | ★ |
| 11 | SELL | 33 | 39.4% | -0.35 | ★ |
| 12 | SELL | 50 | 34.0% | **+0.53** | ▲ |
| 13 | SELL | 61 | 42.6% | **+0.58** | ★★ |
| 14 | BUY | 45 | 37.8% | -0.91 | ★ |
| 15 | SELL | 41 | 41.5% | -0.26 | ★ |
| **19** | **BUY** | 29 | **44.8%** | **+3.29** | ★★ |

**強 cell**:
- **hr19 × BUY** (NY-late open): TP=44.8%, EV=+3.29p — 唯一 N≥20 で EV > +1p
- **hr13 × SELL** (NY-open): TP=42.6%, EV=+0.58p, N=61 — 統計力あり
- **hr12 × SELL** (London-NY pivot): TP=34.0%, EV=+0.53p, N=50

**弱 cell**:
- hr18 × SELL: TP=4.5%, EV=-3.74p (London close 直後の SELL は危険)
- hr20 × BUY: TP=7.7%, EV=-5.66p (流動性低下時間帯)

→ Hour-level での edge は存在するが、N が cell ごとに 20-60 程度で **Bonferroni (M=24×2=48 cell, α=1e-3) の閾値到達は Wilson 95%CI 観点で構造的に困難**。

## 7. Live × Shadow Calibration (FLIP pattern 検出)

post-04-08 broad で Live と Shadow が **逆符号** の cell:

| Cell | Live: N / TP% / EV | Shadow: N / TP% / EV | 判定 |
|---|---|---|---|
| USD_JPY × London × BUY | 24 / 45.8% / **+1.45p** | 162 / 22.8% / -1.57p | FLIP |
| USD_JPY × London × SELL | 36 / 47.2% / +0.26p | 170 / 27.6% / -0.71p | FLIP |
| USD_JPY × NY-overlap × SELL | 26 / 57.7% / **+1.16p** | 204 / 30.9% / -0.54p | FLIP |
| USD_JPY × Tokyo × BUY | 23 / 47.8% / +0.12p | 143 / 23.8% / -0.62p | FLIP |
| EUR_USD × NY-overlap × BUY | 11 / 54.5% / **+2.15p** | 162 / 25.3% / -1.62p | FLIP |

**全 5 FLIP cell で Live が正、Shadow が負** — ELITE_LIVE / PAIR_PROMOTED filter が selection effect として機能している証拠 (Live は entry gate を通過した精鋭)。但し:

- N_live が 11〜36 と small → curve fit リスク残存
- Live と Shadow は **同じ entry conditions ではない** (Live は demoted 戦略を含まない、cooldown 等の filter pass) → 厳密には paired comparison ではない
- Calibration test として使うのは粗い指標。pre-reg で Live 単独の Wilson lower 限界を gate にする方が rigorous

## 8. 限界・注意点

1. **Window が短い**: 17 日 N=2,494 は cell 別に分解すると `pair × hour × side` で N<30 になる cell 多数 → Bonferroni 不到達
2. **Selection bias**: Live は ELITE/PAIR_PROMOTED filter 通過後。Shadow は降格・FORCE_DEMOTED 戦略の trades。同じ universe の 2 群比較ではない
3. **Shadow contamination**: shadow 経路に bug 由来の偏った trade が混入する既知リスク ([[lesson-shadow-contamination]])
4. **R_win/R_loss 推定の不安定性**: cell ごとに WIN/LOSS の N が limited → R 平均値の SE が大きい
5. **Aggregate misleading**: per-strategy 集計を per-pair に統合すると direction asymmetric な戦略 (例: bb_squeeze_breakout) の符号が混ざる ([[lesson-confounding-in-pooled-metrics-2026-04-23]])
6. **Time bucket の粗さ**: 4 session 区切は WW3 の DST 切替・公的 release 時刻 (NFP 13:30 UTC, ECB 12:15 UTC 等) を均質化する → finer hour-level (§6) の方が edge を可視化

## 9. 戦略的含意 (Phase 3 / Phase 4 への材料)

**A. 現ポートフォリオは構造的に positive expectancy を持たない**:
- 全 16 cells (N≥50) で BEV gap がマイナス
- Per-pair で全 5 pair が BEV gap -10pp 以上
- Bonferroni 通過 cell ですら EV=-0.35p
- これは [[cell-level-scan-2026-04-23]] Scenario A (全 240 cells で GO=0/CANDIDATE=0) と整合

**B. Edge の片鱗が見える hour cells**:
- USD_JPY × hr19 × BUY (NY-late open): EV=+3.29p N=29 — pre-reg LOCK 候補だが N<20 月単位
- USD_JPY × hr13/hr12 × SELL: EV +0.5p 程度 — fragile, single-strategy 寄与の可能性高い
- GBP_USD × NY-late × BUY/SELL: 双方向で正だが N=20-32

**C. ELITE_LIVE filter の selection effect は機能している**:
- 5 FLIP cell で Live が +0.12〜+2.15p の正 EV
- これは ELITE entry gate が「市場条件で edge ある trade」を選別している tentative 証拠
- 但し N_live が small で post-cutoff 17 日のデータ。今後 Live N が 100+ 蓄積したら再検証すべき

**D. R:R 改善の余地**:
- 全 cell で R:R ≈ 1.5〜2.0 → BEV_TP% ≈ 33〜40%
- TP-rate 改善 (filter 厳格化) より **R:R 拡大** (TP 距離拡大 / SL 距離縮小) の方が効果大
- 但し SL 縮小は勝率を下げるので、TP 距離拡大 (mean_win 増) が候補
- これは MAFE Dynamic Exit が狙った方向 (loss magnitude 圧縮) の **正反対** — gain magnitude 拡大が今回の math 結果からの示唆
- 但し pre-reg LOCK なしでこれを実装すると HARKing → 別件で pre-reg 設計が必要

## 10. 推奨アクション

**今セッション**: 実装変更ゼロ (read-only 分析)。本 doc を Phase 3 stopping rule / Phase 4 新戦略設計の材料として KB 永続化。

**次セッション以降の判断材料**:
1. **USD_JPY × hr19 × BUY** を session-time-bias 戦略の current window と照合 ([[session-time-bias]] PAIR_SESSION_MAP では USD_JPY → TOKYO/BUY 設定で hr19 はカバー外 → "NY-late BUY edge" は別戦略候補)
2. **GBP_USD × NY-late** 双方向 small-positive を継続監視 (Shadow N≥30 蓄積後に再検証)
3. **R:R 拡大方向の戦略改修** を Phase 4 候補として記録 (mean_win 増加のメカニズム — TP 距離 ATR-relative 拡大 / 部分利確 OFF / トレーリング SL 等)
4. **Live N 蓄積待ち**: post-04-16 narrow Live N=19 → N≥100 で FLIP pattern を再検定

## 11. References

- [[handover-tp-hit-quant-analysis-2026-04-21]] — 全期間 TP-hit 分析 (107 条件)、本分析の前駆
- [[spread-at-entry-confounding-2026-04-23]] — 本分析でも pair confounding を意識
- [[score-predictive-power-2026-04-23]] — score 軸での noise 確認
- [[cell-level-scan-2026-04-23]] — 240-cell Scenario A 確定
- [[mafe-dynamic-exit-result-2026-04-24]] — loss magnitude 圧縮機構 (本分析は逆方向 R 拡大を示唆)
- [[lesson-confounding-in-pooled-metrics-2026-04-23]]
- [[lesson-preregistration-gate-mechanism-mismatch]] — gate-機構整合 (R:R 改善型なら mean_win Wilson upper を gate に)
- [[friction-analysis]] — per-pair friction 値
- [[portfolio-concentration-vwap-mr-2026-04-25]] — 同日の cell-level 分析
- [[bb-squeeze-breakout]] — direction-asymmetric edge 例

## 12. Source

- Data: `GET /api/demo/trades?status=closed` (paginated 4 page, ts=2026-04-25 13:07 UTC, total 3,296 records)
- Analysis: inline Python (Wilson CI + Z-test + Bonferroni + R:R math)
- 出力 cell 数: 36 grid + 21 N≥10 detail + 27 hour-level USD_JPY
