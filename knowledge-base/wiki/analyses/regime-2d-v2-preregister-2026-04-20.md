# Regime 2D v2 Pre-Registration (2026-04-20)

**Status**: Pre-registered hypothesis document. **Analysis only** — no implementation proposed.
**Trigger**: Executed after `scripts/backfill_mtf_regime.py` applies retrospective MTF
regime labels to post-Cutoff trades.

## 0. Meta — なぜ pre-register か

Agent #3 の 2D 分析 ([[regime-strategy-2d-2026-04-20]]) は **Gate 通過ゼロ** で NO-OP.
主因は 4日 post-cutoff のサンプル小 + `trend_down_*` の coverage ゼロ. Backfill によって
Fidelity Cutoff (2026-04-16) 以降の 1,944 件に retrospective labels が付与されれば
cell N は 4-5倍化する見込み.

**しかし**: backfill 完了後に "データを見てから" gate / 閾値 / 仮説を決めると,
**data snooping / p-hacking バイアス** を不可避的に混入させる ([[lesson-reactive-changes]]).

Bailey & Lopez de Prado (2014) *"The Probability of Backtest Overfitting"* 流儀で,
**データを見る前に** 以下を確定させる:

1. 各戦略の期待 family 仮説 (TF/MR/BO/SE/RA)
2. regime × direction 非対称性の sign prediction
3. Gate 閾値 (N / ΔWR / α)
4. Significance test 手続き
5. IS/OOS 分割ルール
6. PASS / FAIL の読み替え

本文書が確定した後に `scripts/regime_2d_v2_rescan.py` を実行し, **結果が仮説と一致しなくても**
閾値や仮説を後付けで動かさないことをコミットする.

本文書は **仮説の documentation** であり, **実装提案ではない**.

---

## 1. 対象戦略リスト (43戦略)

`demo_trader.QUALIFIED_TYPES` + Tier Master (`tier-master.md`) に登録された全戦略.
[[tier-master]] と [[../../research/edge_discovery/strategy_family_map|strategy_family_map.py]]
からの機械的抽出 (2026-04-20 時点). XAU 専用戦略は除外 (user memory: XAU除外).

### 1.1 Family 分類 (expected base family)

`strategy_family_map.py::STRATEGY_FAMILY` + wiki/strategies 根拠に基づく期待分類.
"REGIME_ADAPTIVE" はすでに適用中の 2戦略 (bb_rsi_reversion, fib_reversal) を意味する.

| # | strategy | family | Tier (2026-04-20) | 根拠 |
|---|---|---|---|---|
| 1 | ema_trend_scalp | TF | FORCE_DEMOTED | strategy_family_map §TF (順張り EMA スキャルプ) |
| 2 | xs_momentum | TF | PAIR_PROMOTED×EUR_USD,GBP_USD | cross-sectional currency momentum (Menkhoff 2012) |
| 3 | vol_momentum_scalp | TF | PAIR_PROMOTED×EUR_JPY | ADX+OBV+VWAP 順張り |
| 4 | stoch_trend_pullback | TF | FORCE_DEMOTED | Stoch トレンドプルバック |
| 5 | donchian_momentum_breakout | TF | Phase0 | Donchian 上抜けブレイク |
| 6 | sr_break_retest | TF | FORCE_DEMOTED | SR ブレイク&リテスト順張り |
| 7 | macdh_reversal | TF | FORCE_DEMOTED | P0 2026-04-17 re-classified (MR→TF) |
| 8 | engulfing_bb | TF | FORCE_DEMOTED | P0 2026-04-17 re-classified (MR→TF) |
| 9 | gbp_deep_pullback | TF | ELITE_LIVE | wiki: "TF (Trend Following)", pullback continuation |
| 10 | trendline_sweep | TF | ELITE_LIVE | wiki: "SMC/TF", stop-hunt → trend continuation |
| 11 | session_time_bias | SE | ELITE_LIVE | 自国時間帯通貨減価 (Breedon & Ranaldo 2013) — regime-agnostic |
| 12 | london_fix_reversal | SE | Phase0 / PAIR_DEMOTED×USD_JPY | Fix event-driven (Krohn 2024) |
| 13 | vix_carry_unwind | SE | PAIR_PROMOTED×USD_JPY | VIX macro event (Brunnermeier 2009) |
| 14 | bb_rsi_reversion | **RA** (MR default) | SCALP_SENTINEL + PAIR_DEMOTED(全4) | REGIME_ADAPTIVE: tu=TF, td=MR |
| 15 | fib_reversal | **RA** (MR default) | FORCE_DEMOTED | REGIME_ADAPTIVE: tu=MR, td=TF |
| 16 | h1_fib_reversal | MR | (inline) | MR variant on H1 |
| 17 | dt_bb_rsi_mr | MR | UNIVERSAL_SENTINEL + PAIR_DEMOTED×EUR_USD | DT版 BB+RSI MR |
| 18 | dt_fib_reversal | MR | UNIVERSAL_SENTINEL + PAIR_PROMOTED×GBP_USD | DT版 Fib MR |
| 19 | dt_sr_channel_reversal | MR | UNIVERSAL_SENTINEL | DT版 SR channel MR |
| 20 | sr_channel_reversal | MR | FORCE_DEMOTED | SR 反発 |
| 21 | dual_sr_bounce | MR | — (removed v9.1) | — (exclude from analysis) |
| 22 | streak_reversal | MR | Phase0 | 3-5 連続足反転 |
| 23 | turtle_soup | MR | Phase0 | Liquidity Grab Reversal |
| 24 | mtf_reversal_confluence | MR | Phase0 | MTF RSI+MACD 反転 |
| 25 | sr_fib_confluence | MR | FORCE_DEMOTED | SR+Fib 合流反発 |
| 26 | trend_rebound | MR | UNIVERSAL_SENTINEL | トレンドリバウンド (fade) |
| 27 | orb_trap | MR | FORCE_DEMOTED | ORB Fakeout Reversal |
| 28 | ema_cross | MR | FORCE_DEMOTED + PAIR_DEMOTED×USD_JPY | P0 2026-04-17 re-classified (TF→MR) |
| 29 | vwap_mean_reversion | MR | PAIR_PROMOTED×4ペア | VWAP 2σ reversion |
| 30 | wick_imbalance_reversion | MR | PAIR_PROMOTED×GBP_USD | Wick imbalance fade (Osler 2003) |
| 31 | bb_squeeze_breakout | BO | FORCE_DEMOTED | BB スクイーズ後ブレイクアウト |
| 32 | vol_surge_detector | BO | SCALP_SENTINEL + PAIR_DEMOTED | 出来高急増ブレイク |
| 33 | doji_breakout | BO (pending) | UNIVERSAL_SENTINEL + PAIR_PROMOTED×2 | 3連続 doji → break (pending P0) |
| 34 | post_news_vol | BO (pending) | UNIVERSAL_SENTINEL + PAIR_PROMOTED×2, PAIR_DEMOTED×USD_JPY | 指標後ボラブレイク (pending P0) |
| 35 | squeeze_release_momentum | BO (pending) | UNIVERSAL_SENTINEL + PAIR_PROMOTED×EUR_USD | BBスクイーズ解放 (pending P0) |
| 36 | ema_pullback | TF | — (inline) | EMA プルバック反発 |
| 37 | ema200_trend_reversal | MR | UNIVERSAL_SENTINEL + PAIR_DEMOTED×USD_JPY | EMA200 反転 |
| 38 | eurgbp_daily_mr | MR | UNIVERSAL_SENTINEL | EUR/GBP 日足 MR |
| 39 | v_reversal | MR | UNIVERSAL_SENTINEL | V字反転 |
| 40 | three_bar_reversal | MR | Phase0 | 三本足反転 |
| 41 | vol_spike_mr | MR | UNIVERSAL_SENTINEL | Vol Spike MR (BT JPY PF=1.92) |
| 42 | ny_close_reversal | SE | (inline) | UTC 20-22 directional bias — session-time |
| 43 | intraday_seasonality | SE | FORCE_DEMOTED | 日中リターン季節性 (Breedon & Ranaldo 2013) |

**総計**: 43. うち **RA (既存)**: 2 / **TF**: 11 / **MR**: 19 / **BO**: 6 / **SE**: 5. Pending 3戦略は BO tentative.

---

## 2. Pre-registered asymmetry hypotheses

### 2.1 Family 別期待方向性 (sign prediction, ex-ante)

`strategy_family_map.strategy_aware_alignment()` の既存 rule に基づく期待.

| Family | trend_up_weak | trend_up_strong | trend_down_weak | trend_down_strong | range_tight | range_wide |
|---|---|---|---|---|---|---|
| **TF** | BUY aligned | BUY aligned (non-JPY: conflict, exhaustion expected) | SELL aligned | SELL aligned | conflict (両方向) | conflict |
| **MR** | SELL aligned (fade up) | SELL aligned (fade, JPY例外: SELL=conflict) | BUY aligned (fade down) | BUY aligned (fade) | BOTH aligned | BOTH aligned |
| **BO** | BUY aligned | BUY aligned | SELL aligned | SELL aligned | conflict | BOTH aligned |
| **SE** | neutral | neutral | neutral | neutral | neutral | neutral |
| **RA (bb_rsi)** | BUY>SELL (TF) | BUY>SELL (TF) | BUY>SELL (MR fade) | BUY>SELL (MR fade) | BOTH (MR default) | BOTH (MR default) |
| **RA (fib)** | SELL>BUY (MR fade) | SELL>BUY (MR fade) | SELL>BUY (TF) | SELL>BUY (TF) | BOTH (MR default) | BOTH (MR default) |

### 2.2 各戦略の predicted direction-asymmetry sign (regime 別)

凡例:
- `+` : predicted BUY WR > SELL WR (ΔWR = WR_BUY − WR_SELL > 0)
- `−` : predicted SELL WR > BUY WR (ΔWR < 0)
- `0` : no directional asymmetry expected (range で family=MR / SE family)

| strategy | tu_weak | tu_strong | td_weak | td_strong | range_tight | range_wide |
|---|---|---|---|---|---|---|
| ema_trend_scalp | + | +* | − | − | 0 | 0 |
| xs_momentum | + | +* | − | − | 0 | 0 |
| vol_momentum_scalp | + | +* | − | − | 0 | 0 |
| stoch_trend_pullback | + | +* | − | − | 0 | 0 |
| donchian_momentum_breakout | + | +* | − | − | 0 | 0 |
| sr_break_retest | + | +* | − | − | 0 | 0 |
| macdh_reversal | + | +* | − | − | 0 | 0 |
| engulfing_bb | + | +* | − | − | 0 | 0 |
| gbp_deep_pullback | + | +* | − | − | 0 | 0 |
| trendline_sweep | + | +* | − | − | 0 | 0 |
| ema_pullback | + | +* | − | − | 0 | 0 |
| session_time_bias | 0 | 0 | 0 | 0 | 0 | 0 |
| london_fix_reversal | 0 | 0 | 0 | 0 | 0 | 0 |
| vix_carry_unwind | 0 | 0 | 0 | 0 | 0 | 0 |
| ny_close_reversal | 0 | 0 | 0 | 0 | 0 | 0 |
| intraday_seasonality | 0 | 0 | 0 | 0 | 0 | 0 |
| bb_rsi_reversion (RA) | + | + | + | + | 0 | 0 |
| fib_reversal (RA) | − | − | − | − | 0 | 0 |
| h1_fib_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| dt_bb_rsi_mr | − | −(JPY:0) | + | + | 0 | 0 |
| dt_fib_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| dt_sr_channel_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| sr_channel_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| streak_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| turtle_soup | − | −(JPY:0) | + | + | 0 | 0 |
| mtf_reversal_confluence | − | −(JPY:0) | + | + | 0 | 0 |
| sr_fib_confluence | − | −(JPY:0) | + | + | 0 | 0 |
| trend_rebound | − | −(JPY:0) | + | + | 0 | 0 |
| orb_trap | − | −(JPY:0) | + | + | 0 | 0 |
| ema_cross | − | −(JPY:0) | + | + | 0 | 0 |
| vwap_mean_reversion | − | −(JPY:0) | + | + | 0 | 0 |
| wick_imbalance_reversion | − | −(JPY:0) | + | + | 0 | 0 |
| ema200_trend_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| eurgbp_daily_mr | − | −(JPY:0) | + | + | 0 | 0 |
| v_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| three_bar_reversal | − | −(JPY:0) | + | + | 0 | 0 |
| vol_spike_mr | − | −(JPY:0) | + | + | 0 | 0 |
| bb_squeeze_breakout | + | + | − | − | 0 | BOTH (range_wide family=BO) |
| vol_surge_detector | + | + | − | − | 0 | BOTH |
| doji_breakout (BO?) | + | + | − | − | 0 | BOTH |
| post_news_vol (BO?) | + | + | − | − | 0 | BOTH |
| squeeze_release_momentum (BO?) | + | + | − | − | 0 | BOTH |

`*` = non-JPY `trend_up_strong` は TF exhaustion で conflict (BUY=conflict, SELL=neutral). 観測 WR の
sign が予測と一致することは保証されない (family rule の conflict 判定が bypass しない limit).

### 2.3 Regime-adaptive 新規候補の仮説 (pre-register only)

**新規 REGIME_ADAPTIVE 追加候補** (backfill 後に N≥50/cell が見込まれる戦略):

仮説 A (**TF 系**): `ema_trend_scalp` が `trend_up_strong` で反転非対称性 (Agent #3 の 4日観測で
SELL WR 30% > BUY 17%, 13pp gap 観測済) を示すなら, "strong_up exhaustion" は既存 family rule
が conflict 判定で処理済なので, **新規 REGIME_ADAPTIVE 追加の必要はない**. ただしこれを
pre-register しておくことで, backfill 後に逆転した場合の説明責任を残す.

仮説 B (**MR 系**): `sr_channel_reversal`, `trend_rebound`, `orb_trap` のうち, `trend_down_*`
で BUY WR < SELL WR (方向反転) が観測されれば, bb_rsi_reversion と同じ "downtrend で順張り化"
パターン. 3戦略 × 2 regime = 6 cell を Bonferroni 補正 (α=0.05/6≈0.0083).

仮説 C (**BO 系**): `bb_squeeze_breakout`, `vol_surge_detector` が `range_wide` で両方向 aligned
でありながら, `trend_*` で trend direction と一致する direction のみ aligned が有意かは未検証.
範囲: 2戦略 × 4 regime × 2 dir = 16 cell, 補正 α=0.05/16≈0.0031.

**いずれも backfill 後の実測を待って判定**. **仮説一致しない場合は REGIME_ADAPTIVE 追加しない**.

---

## 3. Gate 条件の事前固定 (pre-committed thresholds)

### 3.1 Cell N 最小要件

- **N ≥ 50 per (strategy, regime, direction) cell** — 厳格要件 (Phase E と同一)
- 緩和基準: N ≥ 30 per cell — 参考表示のみ, gate promotion には使わない

### 3.2 効果サイズ

- **ΔWR ≥ 10pp between regimes (同 direction)** — 主要 gate
- 方向非対称性: `|WR_BUY − WR_SELL| ≥ 10pp per regime` を補助指標とする

### 3.3 Multiple testing 補正

- **K_main = 43 strategies × 4 regime-pair comparisons = 172 tests** (ema_trend_scalp: tu×td, tu×range 等)
- 実際には cell N<50 で計算不能な比較を除外した有効 K を使う
- **Bonferroni α = 0.05 / K_effective**
- **K=172 を conservative な上限**とし, **α_strict = 0.05/172 ≈ 0.00029** を下回る p 値を要求
- 補助 (Holm-Bonferroni step-down) を報告するが, **promotion 判定は strict のみ**

### 3.4 Significance test 手続き

- **Fisher's exact test** (2×2: regime_A vs regime_B × win/loss, 同 direction 固定)
- 代替: two-proportion z-test (Welch's t-test for EV comparison)
- **両側検定** (片側検定は cherry-pick を誘発するので禁止)
- p 値生データを全て CSV 保存 (後日 FDR 再計算可能にする)

### 3.5 IS/OOS split

- **IS**: 2026-04-16 〜 2026-04-18 (backfill 適用後の最古 3日)
- **OOS**: 2026-04-19 以降 (未来サンプル + 新規 Live)
- **符号一致必須**: IS と OOS で `sign(WR_BUY − WR_SELL)` が一致しない cell は gate 不通過
- 現時点 (2026-04-20) の post-backfill サンプルでは OOS が 1-2日しかないため, **初回 rescan
  では "IS only" 報告とし, 符号のみ確認**. 10 日後の再実行で OOS 判定.

### 3.6 既存 REGIME_ADAPTIVE_FAMILY との差分評価

- **bb_rsi_reversion / fib_reversal は除外**して新規候補を抽出 (Phase E で mapping 済)
- 既存 mapping が **broken (符号逆転) していないか** を別途確認 (sanity check)

### 3.7 Pass / Fail 判定ロジック (pre-committed)

戦略 S が REGIME_ADAPTIVE **新規候補** として PASS する条件:

1. S ∉ {bb_rsi_reversion, fib_reversal} (既存除外)
2. S の少なくとも 2つの regime で N ≥ 50 per (S, regime, direction) cell
3. 2つの regime 間で `|ΔWR_same_direction| ≥ 10pp`
4. Fisher's exact p < α_strict (= 0.05/K_effective, 両側)
5. IS 内 N≥50 cell のみで仮説方向と符号一致

上記 **全て** を満たす戦略のみ候補リストに載る. **実装は人間判断** (本 pre-register では実装提案しない).

---

## 4. Post-backfill 実行手順

### 4.1 前提条件

- `scripts/backfill_mtf_regime.py --apply` 実行済 (Render DB に mtf_regime column populate)
- Render API 経由で最新 `/api/demo/trades?limit=5000&include_shadow=1&date_from=2026-04-16` を取得

### 4.2 実行コマンド

```bash
# 1. Snapshot trades from production API
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000&include_shadow=1&date_from=2026-04-16" > /tmp/trades_post_backfill.json

# 2. Run rescan script
python3 scripts/regime_2d_v2_rescan.py \
    --trades-json /tmp/trades_post_backfill.json \
    --output-dir /tmp/fx-regime-2d-v2 \
    --min-cell-n 50 \
    --alpha 0.05

# 3. Inspect outputs
ls /tmp/fx-regime-2d-v2/
# - matrix_all.csv            : 43 × 7 × 2 cell matrix
# - asymmetry_strict.csv      : N≥50 asymmetry ranking
# - hypothesis_check.csv      : predicted sign vs observed sign
# - gate_candidates.csv       : strategies passing §3.7 gate
# - summary.json              : aggregate counts
```

### 4.3 判定プロトコル

- `gate_candidates.csv` が空 → NO-OP, 実装なし, 次回 10日後に再走
- 空でない → **人間レビュー** (Agent 自動実装禁止, [[lesson-reactive-changes]] 遵守)
  - 候補 1つずつ wiki/strategies/{name}.md で機序仮説が立つか確認
  - 365日 BT で retrospective family-map A/B 検証 (研究 pipeline 既存)
  - 同意が得られれば `REGIME_ADAPTIVE_FAMILY` に追加 (別 task, 別 PR)

### 4.4 期待される sanity checks

以下は **必ず観測されるべき** ("もし観測されなければ backfill pipeline のバグ"):

- `bb_rsi_reversion × trend_up_*`: BUY WR > SELL WR (既存 mapping の根拠維持)
- `bb_rsi_reversion × trend_down_*`: BUY WR > SELL WR (既存 mapping の根拠維持)
- `fib_reversal × trend_up_*`: SELL WR > BUY WR
- `fib_reversal × trend_down_*`: SELL WR > BUY WR
- `session_time_bias`: 全 regime で ΔWR ≈ 0 (SE family predicted)

sanity check 失敗 → backfill pipeline の look-ahead バグを疑う, 分析中断.

---

## 5. 禁止事項 (pre-committed)

1. **閾値の事後調整禁止**: §3 の N=50 / ΔWR=10pp / α=0.05/K を backfill 結果を見て緩めない
2. **仮説の事後追加禁止**: §2 の sign prediction を backfill 後に "別の regime で観測された"
   パターンで上書きしない. 事後発見した asymmetry は別 task (将来 Phase) として扱う
3. **Cell 除外の事後正当化禁止**: cell N<50 で p<α になった場合でも「N 不足で未検証」扱い
4. **Data snooping for parameter tuning**: backfill 後の WR 分布を見て SL/TP 調整しない
5. **1日データでの実装**: gate 通過しても, サンプル期間 < 14 日の段階では実装禁止 ([[lesson-reactive-changes]])

---

## 6. Success criteria (for this pre-register)

- [x] 43戦略の family / regime × direction 仮説が明記 (§2.1, §2.2)
- [x] Gate 閾値 (N, ΔWR, α, K) が pre-commit (§3)
- [x] Post-backfill 実行手順が再現可能 (§4)
- [x] Pass/Fail 判定ロジックが機械化可能な形で記述 (§3.7)
- [x] 禁止事項が明示 (§5)

---

## 7. 参照

- [[regime-strategy-2d-2026-04-20]] — Agent #3 による NO-OP 初回スキャン
- [[mtf-regime-validation-2026-04-17]] — Phase A-E 経緯, Phase E REGIME_ADAPTIVE_FAMILY 実装
- [[bb-rsi-reversion]], [[fib-reversal]] — 既存 REGIME_ADAPTIVE 2戦略の根拠
- [[lesson-reactive-changes]], [[lesson-reactive-changes-repeat]] — 1日データ禁止
- [[lesson-orb-trap-bt-divergence]] — 60d→180d 符号反転事例
- [[tier-master]] — 戦略 Tier source of truth
- `research/edge_discovery/strategy_family_map.py` — `STRATEGY_FAMILY`, `REGIME_ADAPTIVE_FAMILY`
- Bailey D. & Lopez de Prado M. (2014) *The Probability of Backtest Overfitting*

---

## 8. Post-execution 記録 (backfill 後に追記)

Backfill + rescan 実行後に以下を追記する. **事前に空のまま commit** し, data snooping 回避.

```
- 実行日時:
- 入力 trades JSON path / N:
- rescan output dir:
- Gate 通過候補 (§3.7):
- Sanity check pass/fail (§4.4):
- 人間判断:
- 次アクション:
```
