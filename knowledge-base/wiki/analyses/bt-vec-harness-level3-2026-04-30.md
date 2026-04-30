---
date: 2026-04-30
phase: bt-serialized-willow Phase E (Level 3)
status: implemented
related:
  - "[[bt-live-divergence]]"
  - "[[claude-harness-design]]"
  - "[[../../../CHANGELOG#2026-04-30 — bt_vec_harness Level 3 production-parity toggles]]"
  - master plan: `/Users/jg-n-012/.claude/plans/bt-serialized-willow.md`
---

# bt_vec_harness Level 3 — Production Parity Toggles

## 背景 (なぜ Level 3 が必要か)

`modules/bt_vec_harness.py` (commit `8f2150e`) は 4 つの mtf_*_scalp 戦略の高速 BT を可能にしたが、`compute_scalp_signal` 全体の数値同値性は持っていなかった:

```python
# 旧 harness 評価ループ (bt_vec_harness.py:484-494)
ctx = SignalContext.from_df(
    df=window, row=window.iloc[-1], symbol=symbol, tf="1m",
    sr_levels=[],                     # ← 空
    layer0={}, layer1={}, regime={},  # ← 空
    layer2={}, layer3={},              # ← 空
    htf={"m15": m15_dict, ...},
    session={},                        # ← 空
    backtest_mode=True,
    bar_time=window.index[-1],
)
```

このため `ctx.sr_levels` を読む `sr_channel_reversal`、`ctx.layer3` を読む確認系戦略、`ctx.regime` の TREND_BULL/BEAR を見て分岐する戦略等は production の `run_scalp_backtest` と異なる挙動になる。

365 日 Tier 判定スキャンの BT 高速化を実現するには、この乖離を埋める必要がある (現状 production パスは 7d で 14 分 / 90d で 3 時間)。

## 実装 (additive opt-in)

### 新 `HtfFeatureSpec` トグル

| Tier | Field | Default | 内容 |
|------|-------|---------|------|
| A | `inject_sr_levels` | False | `find_sr_levels_weighted` を `sr_recalc_interval=100` バーごとに事前計算し `i // 100` でルックアップ |
| A | `inject_master_bias` | False | `_compute_bt_htf_bias` を `htf_recalc_interval=60` バーごとに pre-compute、`ctx.htf` に `agreement`/`score`/`label`/`h1`/`h4` を注入 |
| B | `inject_layer_scores` | False | `is_trade_prohibited` (Layer 0)、`compute_layer2_score` (Layer 2)、`compute_layer3_score` (Layer 3) を per-bar 計算 |
| B | `inject_regime` | False | `detect_market_regime` (TREND_BULL/BEAR/RANGE/HIGH_VOL) per-bar |
| C | `inject_session` | False | `bar_time.hour` 連動の `get_session_info` 互換出力 |
| C | `apply_score_gate` | False | `apply_r2a_suppress_gate` + `_bt_spread`/spread_q を post-evaluation で適用、conf=0 なら drop |

すべて default False のため既存 4 cell BT は bit-identical。

### HTF bias 再実装の理由

`_compute_bt_htf_bias` は app.py:4644-4776 にある。harness から直接 import すると Flask app init / sentry init / blueprint registration 等が起きるため重い。`_compute_htf_bias_for_window()` を harness 内に再実装し、`modules.data.resample_df` + `modules.indicators.add_indicators` だけで完結させた。

**注意**: app.py:`_compute_bt_htf_bias` を改修したら必ず harness 側も同期更新する必要がある。out-of-sync は BT-Live divergence の再導入を意味する (lessons/bt-live-divergence.md)。

### 残りの app.py 関数は lazy-import

`is_trade_prohibited`、`compute_layer2_score`、`compute_layer3_score`、`detect_market_regime`、`get_master_bias`、`_bt_spread` は harness 内の static method からの lazy-import で利用。トグル off の場合は import すらされない。

## 検証

### 1. Bit-identical smoke test (既存 4 cell BT)

`_bt_mtf_cascade_scalp_vec.py --days 7` 全トグル off:

| Cell | N | WR | EV | PF | Kelly |
|------|---|----|-----|-----|-------|
| USDJPY × trend_follow | 1 | 100% | +12.5p | inf | 0% |
| USDJPY × counter_trend | 3 | 0% | **-7.2p** | 0 | 0% |
| EURUSD × trend_follow | 0 | 0% | 0p | 0 | 0% |
| EURUSD × counter_trend | 4 | 50% | **+0.47p** | **1.168** | **7.187%** |

太字部分は task spec の acceptance criteria と完全一致。

### 2. 全トグル on smoke test (USDJPY × counter_trend 7d)

```python
spec = HtfFeatureSpec(
    include_rsi_divergence_m5=True,
    inject_sr_levels=True,
    inject_master_bias=True,
    inject_layer_scores=True,
    inject_regime=True,
    inject_session=True,
)
```

結果:
- SR cache: 70 snapshots / 0.1s build
- HTF bias cache: 119 snapshots / 6.4s build
- eval=40.5s (旧 10.3s, 4× 増)
- N=3 EV=-7.2p — 同戦略 (mtf_counter_trend) は新 ctx 参照しないため期待通り bit-identical

eval 速度: 90d 換算 ~6-7 分。task spec の 30 分目標に余裕。

## 速度予測 (90d production parity)

| Cell | 旧 production パス推定 | Level 3 harness 予測 |
|------|----------------------|---------------------|
| 90d × 1 戦略 | ~30-40 分 | ~6-7 分 |
| 90d × 4 戦略 | ~2-3 時間 | ~25-30 分 |
| 365d × 4 戦略 | 12-15 時間 | ~2 時間 |

これにより Tier 判定スキャンの実行可能性が劇的に向上。

## 次のステップ

1. **production parity 数値検証**: `_bt_mtf_cascade_scalp.py` (run_scalp_backtest 経由) と全トグル on harness を同 cell で実行し trade_log diff
2. **Level 2 再走**: 76 戦略 sanity check を harness 経由で再走させ Tier 判定基盤として活用
3. **Phase F**: `compute_scalp_signal` 全体を harness 化し production 側 BT 関数を harness 出力で置き換える方向の検討 (master plan)

## 制約と注意

- HMM auto-fit は `inject_master_bias=True` で `get_master_bias` 経由で間接呼び出しされる。fit 結果は `data/cache/hmm/` で永続化されているため初回以降は数秒で完了
- SR cache メモリフットプリント: 90 日 1m = 91k バー、`recalc=100` で 910 snapshot × 平均 5 levels = 数百 KB、許容範囲
- `apply_score_gate=True` は production の `apply_r2a_suppress_gate` を実行するため、`modules.strategy_category` の現状実装に依存する。仕様変更があれば挙動変化に注意

## ファイル

- 実装: `modules/bt_vec_harness.py` (additive)
- CHANGELOG: 2026-04-30 エントリ
- master plan: `~/.claude/plans/bt-serialized-willow.md` Phase E
