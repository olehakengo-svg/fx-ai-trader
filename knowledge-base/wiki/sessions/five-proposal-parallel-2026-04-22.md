# 5-Proposal Parallel Analysis — 2026-04-22 / 2026-04-23

## Summary
ユーザー指示「全て並行で進めてください」に従い、以下 5 提案を並列実行した。

| # | Proposal | Status | Output |
|---|---|---|---|
| **A** | KSFT × vwap_mean_reversion synthesis filter (4 pairs) | ✅ | `raw/bt-results/ksft-vwap_mean_reversion-2026-04-22.md` |
| **B** | 730d health audit walk-forward (ELITE_LIVE / PAIR_PROMOTED) | 🕐 running | `walkforward-730d-2026-04-22.md` (pending) |
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

## Proposal B — 730d Health Audit: 🕐 pending

想定対象: `session_time_bias × GBP_USD`, `london_fix_reversal × GBP_USD`, `wick_imbalance_reversion × USD_JPY`, ELITE_LIVE 全体の 2x データ安定性確認。

---

## Consolidated Insights (A+C+D+partial E)

1. **vwap_mean_reversion = 最強 edge** — w30/w60 両方で全 4 pair stable ~ borderline、Overall EV すべて +0.688 以上。KSFT 1-bar reversion signal (C) と整合的。
2. **horizon = 1 のみが本物** — 15m 多足保有の独立 factor edge は存在しない (C)。
3. **統一 KSFT filter は不可** (A) — pair 毎に逆方向の quartile 優位。ただし GBP_JPY × KSFT≤-0.818 は standout (N=68 WR=83.8% PF=4.63)。
4. **Bonferroni は本データに十分** (D) — BY-FDR 追加棄却ゼロ。因子間依存が弱い。
5. **window sensitivity: w60 で昇格する戦略あり** (E partial) — session_time_bias × USD_JPY, ema200_trend_reversal × GBP_JPY 等。長窓で安定性が顕在化するのは market regime の長期的性質を反映。

---

## 判断プロトコル遵守 (CLAUDE.md)
- すべて **観測のみ**。KSFT filter 実装、FORCE_DEMOTE/PROMOTE 実施なし。
- lesson-reactive-changes: 1 回の BT で実装判断はしない。
- 次のアクション: B / E-w7 / E-w90 完了を待ち、window-invariant stable subset を抽出する。実装は Live N≥30 経由。

## Source Files
- `tools/alpha_factor_zoo.py` — BY-FDR 関数追加 (Proposal D)
- `tools/ksft_filter_efficacy.py` — 新規 (Proposal A)
- `tools/bt_walkforward.py` — window sensitivity (E)
- `raw/bt-results/ksft-vwap_mean_reversion-2026-04-22.md`
- `raw/bt-results/alpha-factor-zoo-horizons-2026-04-22.md`
- `raw/bt-results/alpha-factor-zoo-byfdr-2026-04-22.md`
- `raw/bt-results/walkforward-w60-2026-04-22.md`
