---
date: 2026-04-30
phase: Phase C-2 — bt-vec-harness sanity sweep (Level 2 raw)
status: report
source: raw/bt-results/all_strategies_sanity_20260430_151117.json
runner: _bt_all_strategies_sanity.py
days: 90
pairs: [USDJPY=X, EURUSD=X]
n_strategies: 76
n_cells: 152
n_errored: 0
n_zero_fire: 83
n_fired: 69
total_wall_secs: 8367
related:
  - "[[all-strategies-sanity-2026-04-30]]"
  - "[[bt-vec-harness-level3-2026-04-30]]"
  - "[[claude-harness-design]]"
  - master plan: `~/.claude/plans/bt-serialized-willow.md`
---

# All-Strategies Harness Sanity — 90日 raw edge

## 位置づけ
**raw な数字** (production の score gate / SR / layer / regime 抜き) を取るための sanity sweep。
本番 Tier 判定とは別軸の指標として並置する。

- **Harness 側で空辞書注入**: `ctx.layer0/1/2/3 = {}`, `ctx.sr_levels = []`, `ctx.regime = {}`, `ctx.session = {}`
- **Friction 抜き**: spread / hour_mult なし。harness EV は live より楽観的
- **EXPIRED 清算**: harness は `last_close` で決済 (production MAX_HOLD と一致しているか別 cross-check 必要)
- **HtfFeatureSpec 共通最大**: M15 (RSI/Hurst/range_20)、M5 (RSI divergence flags)、H1 forward-fill 全部入り

KB は更新するもの — このページの数字は live 数字を**否定する根拠ではなく**、戦略パラメータ自体に edge があるかの sanity チェック用。

## サマリ
| 区分 | 数 | 内訳 |
|---|---:|---|
| 全戦略 (class-based) | 76 | 76 × 2 pairs = 152 cells |
| **Errored** | 0 | 全戦略が import / evaluate 完走 |
| **Zero-fire (両ペア)** | 35 戦略 | layer/regime/sr 依存 + JPY/XAU 専用 + session タイミング |
| **Zero-fire (片ペア)** | 13 cells | ペア依存 (JPY 系 / EUR 系) |
| **Fired** | 69 cells | N≥1 で発火 |
| **Wilson_lo ≥ 40% (BEV floor)** | 7 cells | うち N≥30 通過 |

## Top — N≥30 で EV>0 の cell

| Strategy | Pair | N | WR% | Wlo% | EV (pip) | PF | Kelly% | 備考 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **trend_rebound** | USDJPY=X | 148 | 49.3 | 41.4 | **+0.52** | 1.231 | 9.24 | Wlo=41.4 ≥ BEV floor |
| **session_time_bias** | EURUSD=X | 504 | 45.2 | 41.0 | +0.17 | 1.058 | 2.48 | Wlo=41.0 ≥ BEV floor |
| **dt_bb_rsi_mr** | EURUSD=X | 1068 | 46.2 | 43.2 | +0.15 | 1.071 | 3.06 | Wlo=43.2 ≥ BEV floor |
| **htf_false_breakout** | EURUSD=X | 549 | 47.5 | 43.4 | +0.09 | 1.038 | 1.58 | Wlo=43.4 ≥ BEV floor |
| **macdh_reversal** | USDJPY=X | 228 | 42.1 | 35.9 | +0.39 | 1.203 | 7.09 | N 中規模、PF 良好 |
| trend_rebound | EURUSD=X | 81 | 45.7 | 35.3 | +0.29 | 1.13 | 5.25 | 両ペア +EV |
| mtf_reversal_confluence | USDJPY=X | 136 | 31.6 | 24.4 | +0.47 | 1.39 | 8.86 | PF 1.39 高い、Wlo 弱め |
| tokyo_nakane_momentum | USDJPY=X | 36 | 44.4 | 29.5 | +0.47 | 1.238 | 8.56 | N=36 小サンプル要保留 |
| post_news_vol | EURUSD=X | 87 | 33.3 | 24.3 | +0.63 | 1.098 | 0.00 | 厚い tail、Kelly=0 |
| london_ny_swing | EURUSD=X | 37 | 37.8 | 24.1 | +0.82 | 1.275 | 8.16 | N=37 小サンプル |
| orb_trap | USDJPY=X | 38 | 50.0 | 34.9 | +1.27 | 1.273 | 10.72 | N=38 小サンプル |
| vol_spike_mr | USDJPY=X | 783 | 32.1 | 28.9 | +0.17 | 1.104 | 3.63 | 大 N、PF やや改善 |
| engulfing_bb | USDJPY=X | 809 | 40.7 | 37.3 | +0.01 | 1.006 | 0.24 | break-even |
| ema_trend_scalp | USDJPY=X | 1713 | 36.9 | 34.6 | +0.01 | 1.005 | 0.20 | 大 N、break-even |

## BEV pass (Wilson_lo ≥ 40%)
標準 95% Wilson 信頼下限が BEV floor 40% を超える cell:

```
htf_false_breakout    EURUSD=X  N= 549  WR=47.5%  Wlo=43.4%  EV=+0.09p  PF=1.038  K=1.58%
dt_bb_rsi_mr          EURUSD=X  N=1068  WR=46.2%  Wlo=43.2%  EV=+0.15p  PF=1.071  K=3.06%
gotobi_fix            USDJPY=X  N=  50  WR=56.0%  Wlo=42.3%  EV=-1.38p  PF=0.83   K=0%   ← WR↑ but RR negative
trend_rebound         USDJPY=X  N= 148  WR=49.3%  Wlo=41.4%  EV=+0.52p  PF=1.231  K=9.24%
session_time_bias     EURUSD=X  N= 504  WR=45.2%  Wlo=41.0%  EV=+0.17p  PF=1.058  K=2.48%
dt_bb_rsi_mr          USDJPY=X  N=1029  WR=43.2%  Wlo=40.2%  EV=-0.26p  PF=0.902  K=0%   ← USDJPY only
htf_false_breakout    USDJPY=X  N= 574  WR=44.2%  Wlo=40.2%  EV=-0.04p  PF=0.982  K=0%   ← USDJPY only
```

**Bonferroni 補正**: m=152 cells、α=0.05/152=3.3e-4。標準 Wilson は z=1.96 を使うので Bonferroni-strict ではない。N=1000+ の cell (`dt_bb_rsi_mr`, `bb_rsi_reversion`, `engulfing_bb`, `ema_trend_scalp`) は Wilson_lo の信頼性が高い — top 5 の中で **N≥500 かつ EV>0** は `session_time_bias EURUSD` と `dt_bb_rsi_mr EURUSD` と `htf_false_breakout EURUSD` の **3 cell のみ**。

`gotobi_fix USDJPY` は WR=56% / Wlo=42.3% と高いが EV=-1.38p — 平均 win より平均 loss が大きい RR 設計の問題。win/loss ratio を見直せば +EV 化の可能性。

## Worst — N≥30 で EV<<0 の cell (要パラメータ見直し or 削除候補)

```
mtf_counter_trend_scalp  EURUSD=X  N=  34  WR=23.5%  Wlo=12.4%  EV=-2.30p  PF=0.382
post_news_vol            USDJPY=X  N= 241  WR=31.1%  Wlo=25.6%  EV=-1.65p  PF=0.773  ← EURUSD は +0.63p、ペア依存
gotobi_fix               USDJPY=X  N=  50  WR=56.0%  Wlo=42.3%  EV=-1.38p  PF=0.83   ← 上記と同じ、RR バグ
bb_squeeze_breakout      USDJPY=X  N= 453  WR=20.3%  Wlo=16.9%  EV=-1.18p  PF=0.637
bb_squeeze_breakout      EURUSD=X  N= 425  WR=22.8%  Wlo=19.1%  EV=-0.79p  PF=0.728
vix_carry_unwind         USDJPY=X  N= 311  WR=30.9%  Wlo=26.0%  EV=-0.75p  PF=0.873
xs_momentum              USDJPY=X  N= 473  WR=38.3%  Wlo=34.0%  EV=-0.73p  PF=0.815
donchian_momentum_break. EURUSD=X  N= 732  WR=28.1%  Wlo=25.0%  EV=-0.71p  PF=0.806
sr_break_retest          USDJPY=X  N=1289  WR=22.4%  Wlo=20.2%  EV=-0.66p  PF=0.702  ← 大 N で robust に negative
vol_surge_detector       EURUSD=X  N= 357  WR=29.7%  Wlo=25.2%  EV=-0.65p  PF=0.715
```

`sr_break_retest USDJPY` (N=1289) は **harness で 1300 trades 取って WR=22%、PF=0.70** — エッジが構造的に欠如。production 側で Tier 上位の場合、score gate がフィルターしているだけで **戦略パラメータ自体には raw edge がない**ことを示唆。

## Bb_rsi_reversion (現 ELITE_LIVE) — KB 整合チェック

```
bb_rsi_reversion  USDJPY=X  N=1706  WR=29.8%  Wlo=27.6%  EV=-0.13p  PF=0.95   K=0%
bb_rsi_reversion  EURUSD=X  N=1191  WR=33.6%  Wlo=31.0%  EV=-0.08p  PF=0.96   K=0%
```

- harness raw: 両ペアで EV slightly negative、WR=30/34%
- live KB: "5日間で-34.1pip" 急速悪化 (obs 639)
- **整合性**: harness raw が break-even 近辺 → live で score gate を通過した cell が現在 negative regime に入っている可能性。**raw に edge がほぼ無いなら、score gate がいくら filter しても EV は 0 ± noise**。Tier 見直し対象。

## Zero-fire 戦略 (両ペア N=0) — Level 3 待ち

35 戦略 / 76 = 46% が harness 上で完全沈黙。原因類型:

### A. Layer/SR/Regime 依存 (production gate-driven)
- `mtf_regime_range_cascade_scalp` (regime classifier 必須)
- `sr_anti_hunt_bounce` (sr_levels=4 refs)
- `sr_channel_reversal` (3 refs)
- `sr_fib_confluence`, `sr_liquidity_grab`, `inducement_ob`, `dt_sr_channel_reversal`
- `hmm_regime_filter`, `cpd_divergence`

### B. ペア / 銘柄依存 (USDJPY/EURUSD 範囲外)
- `gold_pips_hunter`, `gold_trend_momentum`, `gold_vol_break` (XAU 専用)
- `gbp_deep_pullback`, `mqe_gbpusd_fix`, `eurgbp_daily_mr`, `pd_eurjpy_h20_bbpb3_sell`
- `rsk_gbpjpy_reversion`, `vsg_jpy_reversal`, `jpy_basket_trend`, `vdr_jpy`
- `tokyo_range_breakout_up`

### C. Session / 時間帯依存
- `london_breakout`, `london_close_reversal`, `london_fix_reversal`, `london_session_breakout`, `london_shrapnel`
- `asia_range_fade_v1`
- `gotobi_fix` (USDJPY 50 件、EURUSD 0 件 — partial)
- `intraday_seasonality`, `session_vol_expansion`

### D. その他 (内部 gate きつい)
- `pullback_to_liquidity_v1`, `liquidity_sweep`, `turtle_soup`, `trendline_sweep`, `squeeze_release_momentum`
- `ema_cross`, `ema_ribbon_ride`

**Level 3 (harness production parity 拡張) の入力**:
A グループは layer / sr / regime を harness に注入すれば発火する見込み。B/C グループはペア展開 / 時間帯ロジック側の修正が必要。D は戦略パラメータ見直し。

## クオンツ的解釈

### 1. raw vs gated の差分
- **harness raw EV>0** かつ live で gate を通っている戦略 → **score gate が valid に効いている** 証拠
- **harness raw EV<0** で live でも negative → 戦略パラメータ問題 (例: `bb_rsi_reversion`)
- **harness raw EV<0** で live で +EV → score gate が抑制している意味あり、ただし live N が gate 後に十分かを確認

### 2. 候補 — Phase D チューニング baseline
N≥100 かつ raw EV>0 かつ Wlo>=35%:
- `trend_rebound USDJPY` (N=148, EV+0.52, Wlo=41.4) — 両ペア +EV、最有力
- `session_time_bias EURUSD` (N=504, EV+0.17, Wlo=41.0)
- `dt_bb_rsi_mr EURUSD` (N=1068, EV+0.15, Wlo=43.2)
- `htf_false_breakout EURUSD` (N=549, EV+0.09, Wlo=43.4)
- `macdh_reversal USDJPY` (N=228, EV+0.39, Wlo=35.9)

これらは **既に raw で edge が見えている** ので、production の score gate / SR layer を加えれば更に良くなる可能性。Phase D で TP/SL ratio や RR を tune する候補。

### 3. ペアによる edge の濃淡
- USDJPY 強: trend_rebound, macdh_reversal, mtf_reversal_confluence, vol_spike_mr, orb_trap
- EURUSD 強: session_time_bias, dt_bb_rsi_mr, htf_false_breakout, london_ny_swing, post_news_vol
- 両ペア +EV: trend_rebound, dt_bb_rsi_mr (USDJPY は negative だが EURUSD で +)、macdh_reversal、ema_trend_scalp (break-even)

### 4. Aggregate Fallacy 注意
全戦略合計の "76戦略中 14 cell が +EV" という集計は **戦略選別後の最終 win cell 数**であり、各 cell は独立に評価が必要。Bonferroni m=152 で Wilson_lo を再計算すると pass 数は更に減る。

## 次のアクション

1. **Level 3 (harness parity 拡張)**: layer / sr_levels / regime を harness に注入できる差分を別 spawn で実装。35 zero-fire 戦略のうち Layer A グループの発火を確認
2. **Phase D 候補リスト確定**: top-5 raw +EV 戦略を Bonferroni 補正後の Wilson_lo で再評価、Live shadow 投入優先順位を確定
3. **Worst 戦略の処理**: `sr_break_retest` (N=1289 で robustly negative)、`bb_squeeze_breakout` (両ペア negative)、`xs_momentum`、`vix_carry_unwind` は production Tier を再確認、Demote 候補
4. **bb_rsi_reversion**: harness raw が両ペア slightly negative なので、live 急速悪化 (obs 639) と整合する可能性高。Tier 見直しを検討

## Limitations
- spread/friction なし → live EV は本ページの値より lower
- max_hold_bars=240 / window_bars=100 / cooldown=30 / burn_in=240 (harness default、production と差分の可能性あり)
- HtfFeatureSpec 共通最大 — 戦略個別の M5/M15 フィールド読み込み差は影響しないが、戦略によっては未使用フィールドが evaluate を変える可能性は除外できない
- Bonferroni m=152 strict 評価は別途 Phase D で実施
