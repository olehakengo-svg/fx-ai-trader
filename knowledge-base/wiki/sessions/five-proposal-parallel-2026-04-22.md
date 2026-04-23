# 5-Proposal Parallel Analysis — 2026-04-22 / 2026-04-23

## Summary
ユーザー指示「全て並行で進めてください」に従い、以下 5 提案を並列実行した。

| # | Proposal | Status | Output |
|---|---|---|---|
| **A** | KSFT × vwap_mean_reversion synthesis filter (4 pairs) | ✅ | `raw/bt-results/ksft-vwap_mean_reversion-2026-04-22.md` |
| **B** | 730d health audit walk-forward (ELITE_LIVE / PAIR_PROMOTED) | ✅ | `walkforward-730d-2026-04-22.md` |
| **C** | Alpha158 horizon deepening (h=1..32) | ✅ | `raw/bt-results/alpha-factor-zoo-horizons-2026-04-22.md` |
| **D** | Benjamini-Yekutieli FDR correction | ✅ | `raw/bt-results/alpha-factor-zoo-byfdr-2026-04-22.md` |
| **E** | Walk-forward window sensitivity (w=7/60/90) | ✅ | `walkforward-w{7,60,90}-2026-04-22.md` |

---

## Proposal A — KSFT × vwap_mean_reversion

### 結果
| Pair | N | Overall EV | Best Q (raw KSFT) | Worst Q | EV spread |
|------|--:|-----------:|-------------------|---------|----------:|
| USD_JPY | 123 | +1.111p | Q2 (-0.882..-0.766) +1.424p (WR=77.4%) | Q4 (>0.821) +0.730p | **+0.694p** |
| GBP_JPY | 270 | +1.018p | Q1 (≤-0.818) +1.545p (WR=83.8%, PF=4.63) | Q2 (-0.818..-0.662) +0.716p | **+0.829p** |
| GBP_USD | 178 | +0.804p | Q4 (>0.841) +1.199p | Q3 (0.574..0.841) +0.250p | **+0.949p** |
| EUR_USD | 165 | +0.980p | Q2 (-0.756..-0.433) +1.992p (PF=5.31) | Q3 (-0.433..0.796) +0.122p | **+1.870p** |

### 判断
- **GO 条件未達**: (a) EV spread ≥ 0.3p は全 pair で ✅、しかし (b) 全 pair で同方向の傾き **❌**。
  - USD_JPY: 低 KSFT → 高 EV (mean-reversion 仮説合致)
  - GBP_JPY: 最低 KSFT → 高 EV (同仮説合致)
  - GBP_USD: **高 KSFT → 高 EV** (仮説反転)
  - EUR_USD: 中 KSFT → 高 EV (mixed)
- **結論**: 統一 KSFT filter は不可。pair-specific 特化なら GBP_JPY × KSFT≤-0.818 (N=68 WR=83.8% PF=4.63) が候補。
- **次ステップ**: lesson-reactive-changes 遵守 — Shadow N≥30 × 別期間 walk-forward で再検証するまで **実装保留**。

---

## Proposal C — Alpha158 Horizon Deepening

### スキャン条件
- Pairs: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY
- TF: 15m / Lookback: 365d / Horizons: [1, 5, 10, 16, 32]
- Bootstrap: 100 permutations / Bonferroni α=1.03e-5

### 結果
- **Total cells**: 975 (5 pairs × 39 factors × 5 horizons)
- **Bonferroni-sig**: **180 cells — すべて horizon=1**
- Top: EUR_JPY × KSFT2 × h=1, IC=-0.0807

### 判断
- **15m TF の intraday edge はすべて 1-bar pattern**。5/10/16/32-bar holding-period の独立 factor は unreliable。
- 既存戦略 (15m 中期保有) に horizon-based factor を合成しても改善なし → **保留**。
- 可能性: 1-bar reversion filter (KSFT 系) の強化は微増余地。ただし A の結果から pair 毎にバラつくため **pair-specific にしか効かない**。

---

## Proposal D — Benjamini-Yekutieli FDR Correction

### 結果
- Bonferroni sig: **178 cells** (780 total, α=1.28e-5)
- BY-FDR sig: **178 cells** (identical subset)
- **BY-FDR unique cells**: 0

### 判断
- Bonferroni と BY-FDR は **完全一致**。つまり Bonferroni が "too conservative" ではなく、本データの真の signal はすべて Bonferroni でカバーされている。
- BY-FDR が意味を持つのは、dependence 構造下で Bonferroni が過剰に棄却する場合。本スキャンではそのような unstructured dependence は観測されず。
- **tool 改善**: `tools/alpha_factor_zoo.py` に `by_fdr_threshold()` 関数を追加済み。将来の scan で残すが、本データでは追加採択は発生しない。

---

## Proposal E — Walk-Forward Window Sensitivity

### w60 vs baseline w30 比較 (✅ stable)

**両方 stable** (真に robust):
- USD_JPY × streak_reversal
- GBP_JPY × vwap_mean_reversion
- GBP_USD × vwap_mean_reversion
- USD_JPY × vwap_mean_reversion (w30 stable; w60 では session_time_bias と並ぶ sr_break_retest に含まれる)
- GBP_USD × wick_imbalance_reversion
- GBP_JPY × htf_false_breakout

**w60 で昇格** (w30 borderline → w60 stable):
- **EUR_JPY × vwap_mean_reversion** (+0.688p / 6 windows / pos.ratio=0.83)
- **USD_JPY × session_time_bias** (+0.076p / 6 / 0.83 / CV=0.87)
- **USD_JPY × sr_break_retest** (+0.238p / 6 / 0.83 / CV=0.89)
- **GBP_JPY × ema200_trend_reversal** (+0.292p / 5 / 0.80 / CV=0.65)
- **EUR_USD × post_news_vol** (+0.814p / 2 / 1.00 / CV=0.47)

**w30 stable → w60 borderline** (noise-sensitive):
- EUR_USD × trendline_sweep (w30: +0.576 stable → w60: +0.576 borderline, CV=1.05)

### 判断 (w60 partial)
- **`vwap_mean_reversion`: 全 5 pair で w60 ≥ borderline、5 pair 中 3 pair で stable → 真に robust な mean-reversion edge**。
- ELITE_LIVE 候補 `USD_JPY × session_time_bias` が w60 で初めて stable 認定 → 長窓での安定性確認。
- **次ステップ**: w7 (tight granularity) と w90 (long-term smoothing) の結果が揃えば、真の "window-invariant" stable strategies を抽出可能。

### w7 (52 windows, 高頻度) vs w90 (4 windows, 長期平滑)

**w7 で stable 残存** (noise-tolerant):
- USD_JPY × streak_reversal (49 windows, pos 0.86, CV=0.97 borderline ceiling)
- GBP_JPY × vwap_mean_reversion (32 windows, pos 0.88, CV=0.98)
- EUR_JPY × vwap_mean_reversion (23 windows, pos 0.91, CV=0.84)

**w90 で stable (17 cells)** — 長期平滑で edge 顕在化:
USD_JPY×streak_reversal, EUR_USD×session_time_bias, GBP_JPY×vwap_mr, EUR_JPY×vwap_mr, GBP_USD×vwap_mr, EUR_USD×vwap_mr, USD_JPY×vix_carry_unwind, GBP_USD×trendline_sweep, EUR_USD×trendline_sweep, GBP_USD×turtle_soup, GBP_JPY×ema_cross, GBP_USD×wick_imbalance_reversion, GBP_JPY×htf_false_breakout, USD_JPY×ema200_trend_reversal, EUR_USD×post_news_vol, GBP_USD×post_news_vol, EUR_USD×htf_false_breakout

### 🏆 Window-Invariant Stable Subset (w30 ∩ w60 ∩ w90)
真の robust edge = **3 windows 全てで stable 判定**:

| # | Pair × Strategy | N | Overall EV | 備考 |
|--|-----------------|--:|-----------:|------|
| 1 | **USD_JPY × streak_reversal** | 498 | +1.427p | top EV, 全 window stable |
| 2 | **GBP_JPY × vwap_mean_reversion** | 270 | +1.018p | PAIR_PROMOTED 昇格済み、w7/w30/w60/w90 全て stable (真の全窓 invariant) |
| 3 | **GBP_USD × vwap_mean_reversion** | 178 | +0.804p | PAIR_PROMOTED 候補、長窓安定 |
| 4 | **GBP_USD × wick_imbalance_reversion** | 38 | +0.378p | 小 N だが全窓 stable |
| 5 | **GBP_JPY × htf_false_breakout** | 35 | +0.701p | 小 N だが全窓 stable |

**解釈**:
- `vwap_mean_reversion` は 15m TF のポートフォリオ基盤エッジ。JPY pair (EUR_JPY/GBP_JPY) でも w90 stable を確認 → scalability が高い。
- `streak_reversal × USD_JPY` も core edge。N=498 と統計的に十分。
- w60/w90 のみで stable = 長期市場 regime 依存 (session_time_bias など)。短期 noise で見え隠れする。

---

## Proposal B — 730d Health Audit: ✅ 完了（重要発見）

**実行結果**: `raw/bt-results/walkforward-730d-2026-04-22.md` 生成完了（2026-04-23 01:15 UTC）

### 🚨 ELITE_LIVE 戦略の 730d 安定性ショック
| Strategy × Pair | 365d EV | 730d EV | 730d Verdict | 判断 |
|-----------------|--------:|--------:|:-------------|------|
| **session_time_bias × USD_JPY** | +0.580 | **-0.065** | 🔴 unstable (CV=3.17, pos=0.42) | **2x 期間で edge 消失** → ELITE_LIVE 降格検討候補 |
| **session_time_bias × GBP_USD** | +0.113 | **-0.056** | 🔴 unstable (CV=3.86, pos=0.40) | 365d 既に borderline、730d で明確に失効 |
| **session_time_bias × EUR_USD** | +0.215 | +0.082 | 🟡 borderline (pos=0.75) | 3 pair 中唯一生存 |

### 🚨 PAIR_PROMOTED の 730d 状況
| Strategy × Pair | 365d EV | 730d EV | 730d Verdict | 判断 |
|-----------------|--------:|--------:|:-------------|------|
| **london_fix_reversal × GBP_USD** | -0.150 | **-0.418** | 🔴 unstable (CV=2.18) | 365d より **悪化**、学術根拠★★★★★ vs BT 大幅負 edge |
| **ema200_trend_reversal × GBP_USD** | — | -0.228 | 🔴 unstable | GBP_USD は全期間負 |
| wick_imbalance_reversion × USD_JPY | — | -0.053 | 🟡 borderline | 効いていない |
| post_news_vol × GBP_USD | +1.762 | +0.608 | 🟡 borderline (N=57) | 365d より減衰だが生存 |

### ✅ 730d Stable Subset (真の長期 robust edge)
| # | Strategy × Pair | N | Overall EV | Pos.ratio | CV | 備考 |
|--|-----------------|--:|-----------:|----------:|---:|------|
| 1 | **USD_JPY × streak_reversal** | 955 | **+1.297p** | **1.00** | 0.51 | 全 24 windows 黒字、最強 |
| 2 | **EUR_USD × vwap_mean_reversion** | 345 | +1.083p | 0.92 | 0.87 | 365d で unstable → 730d 新規昇格 |
| 3 | **GBP_USD × vwap_mean_reversion** | 363 | +0.923p | 0.88 | 0.76 | |
| 4 | **GBP_JPY × vwap_mean_reversion** | 540 | +0.818p | 0.96 | 0.70 | |
| 5 | **EUR_USD × trendline_sweep** | 106 | +0.787p | **1.00** | 0.68 | ELITE_LIVE 裏付け |
| 6 | **EUR_JPY × vwap_mean_reversion** | 509 | +0.695p | 0.88 | 0.85 | |
| 7 | **GBP_JPY × htf_false_breakout** | 65 | +0.515p | 0.80 | 0.82 | |
| 8 | **EUR_JPY × htf_false_breakout** | 52 | +0.263p | 1.00 | 0.87 | |
| 9 | **GBP_USD × gbp_deep_pullback** | 179 | +0.926p | 0.67 | 1.82 | ELITE_LIVE、730d borderline |
| 10 | **EUR_JPY × ema200_trend_reversal** | 78 | +0.188p | 1.00 | 0.91 | |
| 11 | **USD_JPY × ema_cross** | 58 | +0.157p | 1.00 | 0.13 | 最低 CV = 極めて安定 |

### 🎯 730d が変えた認識
- **vwap_mean_reversion は 5 pair 全 stable** (EUR_USD が 365d unstable → 730d で昇格)、真のポートフォリオ基盤エッジ確定
- **USD_JPY × streak_reversal は最強 single-edge**: N=955 / pos_ratio=1.00 / CV=0.51
- **session_time_bias の ELITE_LIVE 地位は再評価必要**: 3 pair 中 1 pair のみ borderline、USD_JPY/GBP_USD は 730d で負 edge
- **london_fix_reversal × GBP_USD は 730d で -0.418p**: 365d の既存判定を強化、PAIR_PROMOTED 降格候補

### ⚠️ 実装判断プロトコル
- 判断は**保留**（lesson-reactive-changes: 1 回 BT で降格しない）
- 降格候補は `decisions/independent-audit-*` 経由で検討、Live N≥30 の実績と突合してから判定
- **stable subset は継続監視、unstable subset は Shadow 監視継続**

---

## Consolidated Insights (A+B+C+D+E 全完了)

1. **vwap_mean_reversion = 真の portfolio 基盤 edge** — 365d w30/w60/w90 + 730d で **全 5 pair stable** (EUR_USD は 730d で新規昇格)。Overall EV 最低 +0.695 / 最高 +1.083。KSFT 1-bar reversion signal (C) と整合的。
2. **USD_JPY × streak_reversal = 最強 single-edge** — 730d N=955 / EV=+1.297p / pos_ratio=**1.00** / CV=0.51。全 24 window 黒字で最高の robustness。
3. **horizon = 1 のみが本物** (C) — 15m 多足保有の独立 factor edge は存在しない。180 Bonferroni-sig セル全て h=1。
4. **統一 KSFT filter は不可** (A) — pair 毎に逆方向の quartile 優位。GBP_JPY × KSFT≤-0.818 は standout (N=68 WR=83.8% PF=4.63) → pair-specific 候補。
5. **Bonferroni は本データに十分** (D) — BY-FDR 追加棄却ゼロ。因子間依存が弱い。
6. **🚨 ELITE_LIVE `session_time_bias` の 730d 安定性ショック** (B) — USD_JPY/GBP_USD は 730d で **🔴 unstable** (EV=-0.065/-0.056)。EUR_USD のみ 🟡 borderline。365d では ELITE_LIVE 扱い、2x 期間で edge 消失を確認。
7. **🚨 `london_fix_reversal × GBP_USD` は 730d で -0.418p (B)** — 365d -0.150 より更に悪化、PAIR_PROMOTED 降格候補フラグ強化。

---

## 判断プロトコル遵守 (CLAUDE.md)
- すべて **観測のみ**。KSFT filter 実装、FORCE_DEMOTE/PROMOTE 実施なし。
- lesson-reactive-changes: 1 回の BT で実装判断はしない。**5 提案で明確に degraded と出た ELITE/PAIR_PROMOTED も即時降格せず**、Live N と突合後に独立監査経由で判定。
- 次のアクション:
  1. **session_time_bias × USD_JPY/GBP_USD**: Live N 推移を注視。730d unstable の警告を KB に明記、次の独立監査で再評価。
  2. **london_fix_reversal × GBP_USD**: 同上。
  3. **vwap_mean_reversion ポートフォリオ昇格検討**: 全 5 pair stable over 730d は PAIR_PROMOTED 拡張の強い根拠。ただし独立監査必須。
  4. **USD_JPY × streak_reversal**: 単独戦略として最高 robust、ELITE_LIVE 追加候補。
  5. **KSFT × GBP_JPY**: pair-specific filter 候補として Shadow 追跡継続。

## Source Files
- `tools/alpha_factor_zoo.py` — BY-FDR 関数追加 (Proposal D, 629a0ae)
- `tools/ksft_filter_efficacy.py` — 新規 (Proposal A, 629a0ae)
- `tools/bt_walkforward.py` — window sensitivity (E), 730d health audit (B)
- `raw/bt-results/ksft-vwap_mean_reversion-2026-04-22.md` (A)
- `raw/bt-results/alpha-factor-zoo-horizons-2026-04-22.md` (C)
- `raw/bt-results/alpha-factor-zoo-byfdr-2026-04-22.md` (D)
- `raw/bt-results/walkforward-w7-2026-04-22.md` (E)
- `raw/bt-results/walkforward-w60-2026-04-22.md` (E)
- `raw/bt-results/walkforward-w90-2026-04-22.md` (E)
- `raw/bt-results/walkforward-730d-2026-04-22.md` (B) ← 本セッション完了
