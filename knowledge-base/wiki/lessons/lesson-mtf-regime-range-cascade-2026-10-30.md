# Lesson: range regime の MR は 6 ヶ月後も構造的に負け — `mtf_regime_range_cascade_scalp` 再評価 (2026-10-30)

**発見日**: 2026-10-30 | **rule**: R1 (再評価、昇格側は Slow & Strict) | **判定**: **REJECT — `enabled = False` 継続** | **次回 checkpoint**: 2027-04-30
**元監査**: [[regime-cascade-empirical-redesign-2026-04-30]] / `audit/2026-04-30/silent-strategies-preflight.md` (PR #7, Phase 6 で本再評価を予約) | **戦略カード**: [[mtf-regime-range-cascade-scalp]] | **cell 全表**: `knowledge-base/raw/audits/mtf-range-cascade-reeval-cells-2026-10-30.md`

---

## 問い

2026-04-30 に demo_trades.db (N=462) の実測で `enabled = False` にした range-regime MR cascade は、6 ヶ月の regime 変化で edge が再出現したか。
Pre-registered 閾値 (scheduled task 本文): **Wilson_BF_lower ≥ 0.50 AND N ≥ 50 なら `enabled = True` を提案**、未達なら本ページを書いて 6 ヶ月後に再評価。

## 元監査のデータ (2026-04-30, demo_trades.db N=462, 2026-04-02〜04-29)

| 戦略 × range_tight | N | WR% | Wilson_lo | EV (pips) |
|---|---:|---:|---:|---:|
| bb_rsi_reversion (継承元) | 8 | **12.5** | 2.24% | -3.74 |
| engulfing_bb | 5 | 20.0 | 3.62% | -0.86 |
| sr_channel_reversal | 10 | **0.0** | 0.00% | -3.20 |
| range_tight 集約 (全戦略) | 121 | 25.6 | — | -2.74 |

当時の判定は Rule 3 (算数破綻寄り): N=5〜10 で Wilson_lo がほぼ 0 のため 365 日 BT を待たず停止。

## 今回の再評価データ (production 180d, 2026-05-04〜10-30)

**一次ソース**: Render 本番 `/api/demo/trades?status=closed` を全ページ取得 (15,375 closed rows)。ローカル `demo_trades.db` は 2026-09-14 で停止しており使用不可 (MEMORY `feedback_check_orphan_local_app` 系の罠: 一次ソースは常に Render API)。
**フィルタ**: outcome ∈ {WIN, LOSS} / XAU 除外 / `dedup_violation` 除外 (2,408 行 = 16.7% が重複フラグ、MEMORY `project_r2_audit_dedup_contamination_2026_06_08` の「dedup 未除外で N 水増し」再発防止) → **N = 12,025**。is_shadow = 1 が 98.4%。
**戦略本体の発火**: **0 件** (enabled=False なので当然)。よって元監査と同じ代理指標 = **継承元 3 戦略 × range regime** を cell とする。

### 1. Pre-registered 継承 cell (m = 6 で Bonferroni、全 pair)

| entry_type | regime | N | WR% | Wilson95 lo | **Wilson_BF lo** | EV pips | PF |
|---|---|---:|---:|---:|---:|---:|---:|
| bb_rsi_reversion | range_tight | 32 | 28.1 | 15.6% | **12.6%** | -1.30 | 0.55 |
| engulfing_bb | range_tight | 43 | 32.6 | 20.5% | **17.3%** | -1.73 | 0.44 |
| sr_channel_reversal | range_tight | 107 | 35.5 | 27.1% | **24.5%** | -1.33 | 0.56 |
| bb_rsi_reversion | range_wide | 32 | 31.2 | 18.0% | **14.7%** | -1.45 | 0.45 |
| engulfing_bb | range_wide | 74 | 28.4 | 19.4% | **16.9%** | -1.92 | 0.41 |
| sr_channel_reversal | range_wide | 82 | 35.4 | 25.9% | **23.1%** | -1.36 | 0.56 |

**6 cell 全て Wilson_BF_lower 12〜25% で閾値 50% の半分以下、EV 全負、PF 0.41〜0.56。** N は 4 月の 5〜10 から 32〜107 へ増えたので「small-sample で見えなかった edge」説は棄却された (N 増で WR は 12.5%→28.1%、0%→35.5% と回帰したが、依然 BEV 以下)。

### 2. 戦略の pair universe (USD_JPY / EUR_USD) に限定した pooled 継承 cell

| cell | N | WR% | Wilson95 lo | Wilson_BF lo (m=6) | EV | PF |
|---|---:|---:|---:|---:|---:|---:|
| 継承 3 戦略 × range_tight × {USD_JPY, EUR_USD} | 19 | 36.8 | 19.1% | 15.1% | -0.74 | 0.80 |
| 継承 3 戦略 × range_wide × {USD_JPY, EUR_USD} | 40 | 32.5 | 20.1% | 16.9% | -1.49 | 0.46 |
| 継承 3 戦略 × range (any) × {USD_JPY, EUR_USD} | 59 | 33.9 | 23.1% | 20.1% | -1.25 | 0.59 |

EUR_USD × range_tight は N=0 (半年間一度も発火せず)。pair を絞っても結論は同じ。

### 3. 対照: 同じ戦略の non-range regime

| entry_type | RANGE (any) | NON-RANGE |
|---|---|---|
| bb_rsi_reversion | N=64 WR=29.7% EV=-1.37 PF=0.50 | N=63 WR=**49.2%** EV=+0.20 PF=1.10 |
| engulfing_bb | N=117 WR=29.9% EV=-1.85 PF=0.42 | N=329 WR=36.8% EV=-1.04 PF=0.56 |
| sr_channel_reversal | N=189 WR=35.4% EV=-1.34 PF=0.56 | N=51 WR=23.5% EV=-0.96 PF=0.64 |

bb_rsi_reversion は range で WR が **約 20pp 低い** (4 月の「range で MR は負け、trend_up_weak で MR が best」の方向性と整合)。sr_channel_reversal は逆方向だが両方負け。「range regime は MR の味方」仮説は半年分のデータでも再現されない。

### 4. 月次 drift (継承 3 戦略 × range、全 pair)

| 月 | N | WR% | EV | PF |
|---|---:|---:|---:|---:|
| 2026-05 | 144 | 25.0 | -1.88 | 0.49 |
| 2026-06 | 192 | 37.5 | -1.37 | 0.48 |
| 2026-07 | 23 | 43.5 | -0.19 | 0.92 |
| 2026-08 | 11 | 27.3 | -1.78 | 0.50 |
| 2026-09, 10 | 0 | — | — | — |

7 月の WR 43.5% は N=23 かつ PF<1 でノイズ域。**8 月以降は継承 3 戦略が FORCE_DEMOTED / PAIR_DEMOTED で発火自体が止まっており** (`/api/strategies/status` 30d rolling: 3 戦略とも shadow N=0)、代理指標の供給源が枯れている。これは次回 (2027-04-30) の再評価の構造的制約になる (下記「次回への引き継ぎ」)。

### 5. MR-type 全体 × range (参考、閾値判定には使わない)

`strategy_type = "MR"` 全 29 戦略 × range_tight: N=759 WR=45.7% Wilson95 lo=42.2% EV=-2.16 PF=0.47 / × range_wide: N=870 WR=44.9% EV=-1.20 PF=0.70。cell 全表 (m=114) で閾値を満たした cell は **0 / 114**。range regime そのものが MR に有利な場所ではない。

## 閾値判定

| 条件 | 結果 |
|---|---|
| Wilson_BF_lower ≥ 0.50 | **FAIL** (最大 24.5%、sr_channel_reversal × range_tight) |
| N ≥ 50 | 6 cell 中 3 cell で PASS (N=107 / 74 / 82) — N は十分、edge が無い |
| Bonferroni 有意な正 edge | **無し** (m=6 でも m=114 でも 0 survivor) |

→ **`enabled = False` を継続。PR は開かない (再 enable 側の変更なし)。**

## 構造的発見 (再 enable する前に必ず直すもの)

1. **`REGIME_RANGE` は `no_go` の alias**: `modules/regime_classifier.py` の v2 binary 化で `REGIME_RANGE = REGIME_NO_GO` となった。本戦略の default path は `classify_15m(m15) != REGIME_RANGE` で reject するので、**`enabled = True` にすると「moderate_trend 以外の全バー」で Layer 1 を通過**する = range 検出ではなく trend の補集合。再 enable するなら `_range_cohort()` (REDESIGN_V2 path、ADX<18 を range と定義) か実 range classifier に差し替えが前提。
2. **ローカル 1m parquet cache は stale**: `data/cache/massive/USD_JPY_1m.parquet` は 2026-05-01、`EUR_USD_1m.parquet` は 2026-04-15 で止まっている。`_bt_all_strategies_sanity.py --days 180` は「cache 末尾から 180 日」なので、**2025-11〜2026-05 の BT** になり、再評価期間 (2026-05〜10) をカバーしない。「BT は MASSIVE cache 必須」(MEMORY `feedback_bt_must_use_massive`) の前提 (cache が最新) が崩れている。
3. **parquet timestamp 精度の不一致**: `*_1h.parquet` が `datetime64[ms, UTC]`、1m/5m/15m が `[ns, UTC]` で `VecBacktestRunner` の `merge_asof` が `MergeError` で落ちる (2026-07-29 gap-fill / refreeze 以降の退行と推定)。本再評価では wrapper 側で index を `[ns]` に cast して回避。harness 本体の修正は別 issue。
4. **代理指標の供給が止まっている**: 継承 3 戦略が demote され 8 月以降発火ゼロ。次回の再評価で「N 不足」になるのは edge の有無ではなく観測装置の停止であり、「監査 = 設計の正誤、N 不足は別問題」(MEMORY `feedback_audit_purpose_design_not_n`) の通り N 不足を re-enable の根拠にしてはならない。

## Sanity BT (180d, `VecBacktestRunner`, `enabled` 強制 True)

`_bt_all_strategies_sanity.py` は `enabled=False` を skip するため、同じ `VecBacktestRunner` + `HtfFeatureSpec` を wrapper から呼び `enabled` を強制 True にして実行 (1h parquet の `[ms]`→`[ns]` cast 込み)。raw: `knowledge-base/raw/bt-results/mtf-range-cascade-reeval-180d-2026-10-30.json`。
**窓は cache 末尾基準** (発見 2): USD_JPY = 2025-11-02〜2026-05-01、EUR_USD = 2025-10-17〜2026-04-15。再評価期間 (2026-05〜10) は含まれない。

| path | symbol | N | WR% | Wilson95 lo | EV pips | PF | avg win / loss |
|---|---|---:|---:|---:|---:|---:|---|
| default (`REGIME_RANGE`=no_go alias = trend 補集合) | USD_JPY | 324 | 16.7 | 13.0% | -1.43 | 0.56 | — |
| default | EUR_USD | 338 | 17.8 | 14.1% | -0.98 | 0.64 | — |
| REDESIGN_V2 (`_range_cohort` ∈ {range_wide, moderate_trend}) | USD_JPY | 240 | 22.5 | 17.7% | -0.62 | 0.81 | — |
| REDESIGN_V2 | EUR_USD | 222 | 17.1 | 12.7% | -1.26 | 0.57 | — |
| 参考: default, 30d | USD_JPY | 57 | 19.3 | 11.1% | -0.84 | 0.72 | +11.2 / -3.7 |

BT でも 4 cell 全て WR < 25%、PF < 0.85、EV 負。R:R 3.0 設計なので BEV WR ≈ 25% + friction だが、実 WR はその下。production の代理 cell (WR 28〜36%) より BT の方が悪いのは、本戦略の Layer 2/3 (M5 exhaustion + bb_rsi 条件) が継承元より発火を絞った結果、負け側だけが残る典型 ([[complex-gate-edge-destruction-pattern-2026-05-03]] と同型)。production 代理指標と BT の両方が同じ符号 = **閾値判定は sanity BT でも覆らない**。

## 教訓

**6 ヶ月・N 10 倍で再評価しても range × MR は Wilson_BF 12〜25% / PF < 0.6 のまま: 「regime が変われば edge が戻る」は実測で否定された。再評価の価値は結論ではなく、(a) 代理指標の供給源が demote で枯れた、(b) `REGIME_RANGE` alias で「range 条件」自体がコード上消滅した、という観測装置側の劣化を見つけたことにある。再評価タスクは「戦略の edge」と「それを測る装置が生きているか」を別々に判定せよ。**

## 次回への引き継ぎ (2027-04-30)

- scheduled task `mtf-regime-range-cascade-reevaluation-2027-04-30` (fireAt 2027-04-30T10:00+09:00) の作成は **本 run では承認が得られず未作成** (automated run は scheduler の write を承認できない)。user が `/schedule` または `mcp__scheduled-tasks__create_scheduled_task` で作成すること。prompt 案は本ページ末尾。
- 次回の判定材料: (1) 継承 3 戦略が復活していれば同じ 6 cell、(2) 復活していなければ **本戦略自身を Shadow-only (`SHADOW_ALWAYS` / is_shadow=1) で一定期間発火させて N を作る**方が、代理指標を待つより正しい (shadow-first: Shadow が真の estimator、MEMORY `feedback_shadow_first_quant_architecture`)。ただしその前に発見 1 の gate 修正が必須。
- 閾値は据え置き: Wilson_BF_lower ≥ 0.50 AND N ≥ 50 (Bonferroni m = 6)。

### 次回 task prompt 案

```
Re-evaluate mtf_regime_range_cascade_scalp (fx-ai-trader) — checkpoint #2.
1. Confirm enabled=False and whether REGIME_RANGE==REGIME_NO_GO alias still exists.
2. Pull 180d closed trades from https://fx-ai-trader.onrender.com/api/demo/trades?status=closed (paginate, limit=1000).
   Filter outcome in {WIN,LOSS}, exclude XAU, exclude dedup_violation; keep is_shadow separate.
3. Cells: {bb_rsi_reversion, sr_channel_reversal, engulfing_bb} x {range_tight, range_wide}; Wilson95 + Wilson_BF (m=6) lower, EV, PF.
4. If Wilson_BF_lower>=0.50 AND N>=50: fix the REGIME_RANGE gate, propose enabled=True, open PR + KB lesson.
   Else: write knowledge-base/wiki/lessons/lesson-mtf-regime-range-cascade-2027-04-30.md citing the 2026-04-30 audit
   and lesson-mtf-regime-range-cascade-2026-10-30.md, docs-only PR, schedule 2027-10-30.
Do not re-enable without Bonferroni-significant evidence. LIVE impact zero (SCALP_SENTINEL -> is_shadow=1 first).
```

## 手続き記録 (automated run、user 不在での判断)

- 本番 API は無認証 GET のみ使用。DB / 本番状態への write は無し。
- repo main は座礁状態 (ローカル main ahead 3 / behind 471、staged 未コミット wiki 多数) のため触らず、`origin/main` (12cc8b3d7) から worktree `.worktrees/range-cascade-reeval-1030` / branch `docs/mtf-range-cascade-reeval-2026-10-30` を切って docs-only で commit。
- コード (`strategies/scalp/mtf_regime_range_cascade_scalp.py`) は無変更。`enabled = False` を実ファイルで確認済み (2026-10-30)。
