# Edge Factor Audit 2026-06-12 — #1 ema_trend_scalp

Edge 別 N 降順要因解析シリーズの第 1 弾。データ: Render 本番 `/api/demo/trades`
closed 9,779 件 (2026-04-02〜06-12) → XAU 25 件 + dedup_violation 1,883 件 (19%)
除外後の clean 7,875 件。LIVE 885 / SHADOW 6,990 分離。

## Verdict: 🔴 KILL (恒久退役) — rule:R2

**Recommendation**: Shadow 含め全ペア発火停止 (`SHADOW_RETIRED_STRATEGIES` 新設)。
2026-05-15 redesign スレッド (aligned×BUY×GBP_USD) も同時クローズ。

## 対象 N

| population | N | WR | EV/t | PF |
|---|---|---|---|---|
| clean 全体 | **1,117** | 19.2% | −1.39 | 0.52 |
| LIVE (is_shadow=0) | 16 | 37.5% | −0.15 | 0.93 |
| SHADOW | 1,101 | 19.0% | −1.41 | 0.52 |

## 要因分解 (なぜ勝てないか)

### 🔴 1. 全 8 セル均一負け — 救済セルなし

| pair × dir | N | WR | EV | PF |
|---|---|---|---|---|
| USD_JPY BUY | 282 | 22.7% | −1.19 | 0.60 |
| USD_JPY SELL | 241 | 18.3% | −1.53 | 0.54 |
| EUR_USD BUY | 193 | 16.6% | −1.42 | 0.44 |
| EUR_USD SELL | 132 | 27.3% | −0.52 | 0.77 |
| GBP_USD BUY | 131 | 18.3% | −1.48 | 0.56 |
| GBP_USD SELL | 83 | 15.7% | −2.20 | 0.39 |
| **USD_CHF BUY** | 40 | **5.0%** | −2.69 | **0.03** |
| **USD_CHF SELL** | 15 | **0.0%** | −1.95 | **0.00** |

SIZE lever ([[feedback_size_lever_beats_skip_filter]] 原則) は「勝ちセルが存在する」
前提の道具であり、ここでは適用対象なし。

### 🔴 2. 幾何学的に詰み — TP/SL 2.03 で BE-WR 33.1% vs 実測 19.2%
median SL=4.0p / TP=8.1p。エントリーシグナルがこのジオメトリで要求される
予測力を持たない。

### 🔴 3. エントリー自体に予測力なし (MAFE 実測)
敗者 902 件の favorable excursion **中央値 0.5p**。エントリー直後にほぼ即逆行。
+2p 到達した敗者は 28.7% のみ → **TP 短縮でも救済不可** (avgW が friction 1.75p を
下回る)。[[feedback_spread_basis_for_mafe]] 準拠で entry_price 基準。

### 🔴 4. 反転 (inverse) も不成立
gross EV ≈ +0.33 ≒ 0 (シグナル＝ノイズ)。反転後 gross ≈ −0.33 で friction に沈む。
**1m/5m scalp で SL 4p に対し friction 1.75p (SL の 44%)** という構造が根本敗因。

### 🟠 5. 加速劣化 + 退役後の漏れ
- 月次 WR: 2026-04 20.8% → 05 16.1% → 06 **6.5%** (PF 0.05)
- per-cell registry (2026-05-08) で EUR/GBP/JPY は停止済みだったが、
  **Phase B-1 HourlyEngine slot `daytrade_1h_usdchf` から USD_CHF が漏れ続けた**:
  直近 30d N=55 (全件 USD_CHF 1h)、WR 3.6%、47/55 が TIME_DECAY_EXIT。
  これが本日時点の唯一の発火源 = 全データ中最悪セル。

## 2026-05-15 redesign スレッドのクローズ判定
aligned×BUY×GBP_USD (N=10, WR=50%, EV=+2.16) は:
1. GBP_USD shadow が 05-08 registry 投入で発火停止済み → N≥30 蓄積経路が既に死亡
2. 本監査 GBP_USD BUY 全体 N=131 WR 18.3% PF 0.56 — 母集団は均一負け
3. N=10 の sub-cell は W3-3 と同型の post-hoc selection ([[project_w3_3_s4_connors_raschke_queued]])

→ **redesign 棄却**。ETS_REDESIGN_V3 env flag は default OFF のまま死蔵 (削除は別途)。

## 思想の救済条件 (将来再挑戦する場合のみ)
「EMA トレンド押し目」思想は W4-EDA「思想は正、設計が誤」分類。再挑戦条件:
- friction が SL の 10% 未満になる TF (H1+, SL 20p+) で **新戦略として** Rule 1 フルゲート
- MA/HMM gate 後付けは不可 ([[feedback_ma_filter_breaks_mr]] / [[feedback_hmm_gate_same_trap]])

## 実装 (同コミット)
- `modules/shadow_demote_registry.py`: `SHADOW_RETIRED_STRATEGIES` 新設 (戦略単位の
  全ペア恒久退役、将来ペア追加にも閉)。`is_shadow_demoted()` が優先評価。
- LIVE 側は v9.2 FORCE_DEMOTED 済みのため変更なし。
- tests: `test_shadow_demote_registry.py` に retirement 検証 3 ケース追加。

## シリーズ全体の敗因 3 パターン (overview)
| パターン | 定義 | 該当 (N 降順) |
|---|---|---|
| A. friction 負け | gross EV ≈ 0〜+1、friction 1.5〜2.4p が edge を食う | ema_trend_scalp, sr_channel_reversal, bb_rsi_reversion, fib_reversal, engulfing_bb, session_time_bias, vol_surge_detector |
| B. 設計破綻 | gross EV すら負 | sr_fib_confluence (−1.18), xs_momentum (−0.43), sr_break_retest (−0.27), trendline_sweep (−1.96), vol_momentum_scalp |
| C. 生存 | net EV > 0 | dt_bb_rsi_mr (N=105 +1.72 PF1.61 Wilson.383), ob_retest (N=67 +1.07), orb_trap (30d N=21 +3.10), sr_anti_hunt_bounce (30d +0.57), donchian (+0.09) |

次回: #2 `bb_rsi_reversion` (N=780, LIVE 最大 N=243, friction 負けの典型)。
