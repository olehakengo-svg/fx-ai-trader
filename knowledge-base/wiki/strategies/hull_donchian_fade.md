# hull_donchian_fade — EUR_USD M15 圧縮ゲート二重確認フェード

- **Status**: LIVE 意図的例外 (env gate, 固定 5000u lot) — 2026-06-12 投入
- **Mode**: daytrade_eur (EUR_USD 15m)
- **Type**: MR (compression-gated breakout fade)
- **起源セッション**: TV「Hull Suite + Donchian Trend Ribbon を1mで勝てる方法」(2026-06-10..12)
- **検証 repo**: `/Users/jg-n-012/test/hull-donchian-1m-validation/` (commit 4d38084+)
- **Memory**: `project_hull_donchian_fade_15m_2026_06_12`

## 思想

1m momentum (Hull色flip ∧ Donchianブレイク同方向) は THESIS_INVALID — 3ペア全ホライズンで
forward return 負。**ブレイクは継続せず反転する**。fade (完全逆張り) に方向エッジが実在するが
1m では spread が edge を食う (gross +0.5p < spread 0.6-1.2p)。15m で edge が spread の壁を超える。

**深掘りの核心** (train 2014-2022 探索 → holdout 2022-2026 untouched 一発 confirm):
- 唯一 transfer した構造 = **チャネル圧縮時のみ張る** (width/ATR14 ≤ 3.8558 = train-q33 凍結)。
  広いチャネル = トレンド進行中で fade は轢かれる (GBP London LONG -2.78p が象徴)。
- exit = **Donchian basis (中央線) 回帰**。タイト ATR ストップは MR 破壊
  ([[feedback_ma_filter_breaks_mr]] と同族)。災害 SL=4xATR は noise の外。
- GBP_USD は width ルール不 transfer (holdout で reject) — **EUR_USD 単体**。

## 凍結スペック (再最適化禁止)

| param | value | 由来 |
|---|---|---|
| HMA length | 55 | Hull Suite デフォルト (pre-reg) |
| Donchian length | 20 | 同上 |
| width/ATR 上限 | 3.8558 | train-q33 (2014-2022) |
| ATR | 14, SMA of TR | 検証エンジン同一 |
| TP | entry-bar Donchian basis | MR 自然 exit |
| SL | 4 × ATR14 | 災害ストップ (3/4/5 の中央、最適化なし) |
| max_hold | 96 bars (24h) | バックストップ |
| entry | fadeS: close>upper[1] ∧ Hull bull → SELL / fadeL: 鏡像 → BUY | 二重確認の逆張り |

## 検証サマリ (spread 0.6p 控除済)

| 窓 | N | WR | net EV | PF | p |
|---|---|---|---|---|---|
| Holdout 2022-2026 (動的basis exit) | 2,133 | 0.692 | +0.903p | 1.156 | 0.0146 (BH-FDR m=2 生存) |
| **Holdout 忠実度BT (本番メカニクス)** | 1,833 | **0.780** | **+1.342p** | **1.191** | 0.0005 |
| 同上 LONG / SHORT | — | — | +1.05p / +1.57p | — | 両side正 |
| TV 独立再現 (OANDA feed 365d) | 292 | 0.685 | — | 1.167 | — |

既知の弱点 cell: **SHORT × macro-UP (trailing 90d)** = holdout EV -0.10p (フラット、出血ではない)。

限定事項: (a) width ルールは train 6セル探索からの事後選択を holdout で confirm した
in-sample 寄り判定、真の OOS は LIVE 実測のみ。(b) holdout はこの 1 回で焼却済み、
今後この窓での再 tuning 禁止。(c) スワップ未モデル (中央値保有 ~5h)。

## LIVE 例外 (User 判断 2026-06-12, rule:R1 override)

Kalman D7 / carry_dip / ZZ v60 と同型。**Codex はレビューのみ、実装は Claude 直接**
([[feedback_codex_as_review_layer_2026_06_05]])。

- env `HULL_DONCHIAN_FADE_LIVE_ENABLE=1` でのみ LIVE 転送 (default OFF = shadow-safe)
- 固定 5000u lot 強制 (cascade 非依存; 2026-06-12 user 指示で 1000→5000)
- `_SHIELD_EUR_DT_WHITELIST` 登録 (daytrade_eur は `_OANDA_MODE_BLOCKED` — ZZ v60 silent-drop 事故の再発防止)

### Pre-reg 撤退条件 (どれか成立 → 即実行、後出し変更禁止)

1. **Live N≥10 ∧ net EV < 0** → demote (Rule 2 即断)
2. **Live N≥30 ∧ (WR < 55% ∨ PF < 1.0)** → demote
3. **SHORT × macro-UP cell が N≥30 ∧ EV < -0.5p** → SHORT 側のみ lot 0.5x
   (SIZE lever、SKIP はしない — [[feedback_size_lever_beats_skip_filter]])
4. 既存 CB (日次 -30pip) / DD ゲート無条件優先

### 期待値 (boots from holdout ledger)

- 発火 ~40 trades/月 (フル稼働時) — 5000u (≈$0.5/pip) では月次 PnL は小さい (実 fill 分布の蓄積が目的)
- sizing 拡大は Live N≥30 通過後に別途判断 (0.25x Kelly ≈ 月利 1.8% / maxDD 22% が参考点)
