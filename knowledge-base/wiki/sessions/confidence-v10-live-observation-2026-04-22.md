# Confidence v10 Live Observation Log (2026-04-22)

**目的**: v10 (commit `8fc90eb`) 本番デプロイ後の観測記録。
**対象**: `[v2]` marker / Q4 gate 発火 / confidence 分布 shift / OANDA 実弾安全性

## 1. デプロイ概要

- **Commit**: `8fc90eb` — `feat(confidence-v2): strategy-type aware conf + Q4 gate safety net (v10)`
- **Render auto-deploy 完了**: 2026-04-22 ~02:20 UTC (推定)
- **最初のv10 marker trade**: `id=2540 ema_trend_scalp` @ 02:24:14 UTC

## 2. 稼働verify — v10 修正の本番確認

### 2.1 直接verify (reasons 内 `[v2]` marker)

| trade ID | time (UTC) | strategy | conf | ADX | penalty 計算 | marker 確認 |
|---|---|---|---:|---:|---|---|
| 2540 | 02:24:14 | ema_trend_scalp (pullback) | 47 | 32.3 | (32.3-31)×3=**4** | `🔧 [v2] pullback anti-trend: ADX=32.3>31 → conf 67→63` ✓ |
| 2542 | 02:52:05 | fib_reversal (MR) | 71 | 25.8 | (25.8-25)×2=**2** | `🔧 [v2] MR anti-trend: ADX=25.8>25 → conf 69→67` ✓ |
| 2555 | 05:14:50 | squeeze_release_momentum (DTE) | 64 | 6.3 | — | `🔧 [v2] DTE conf respected: conf=66 (legacy formula bypassed)` ✓ |
| 2571 | 05:35:47 | vol_spike_mr (DTE) | 79 | 15.7 | — | `🔧 [v2] DTE conf respected: conf=74 (legacy formula bypassed)` ✓ |
| 2576 | 06:08:43 | dt_fib_reversal (DTE) | 59 | 18.0 | — | `🔧 [v2] DTE conf respected: conf=62 (legacy formula bypassed)` ✓ |

**数学的に期待値一致**: penalty = `(ADX-threshold) × slope` の切上げ整数 = 観測値

### 2.2 間接verify (threshold boundary 動作)

| trade ID | strategy | ADX | threshold | penalty 期待 | marker 観測 | 判定 |
|---|---|---|---|---|---|---|
| 2548 | fib_reversal | 13.2 | 25 (MR) | 0 | なし | ✓ 正しく抑制 |
| 2549 | bb_rsi_reversion | 24.8 | 25 (MR) | 0 | なし | ✓ 境界-0.2 で non-trigger |
| 2575 | ema_trend_scalp | 26.9 | 31 (pullback) | 0 | なし | ✓ pullback はまだ有効帯 |
| 2578 | bb_rsi_reversion | 24.1 | 25 (MR) | 0 | なし | ✓ 境界-0.9 で non-trigger |

### 2.3 Q4 gate 動作 (safety net)

| trade ID | strategy | conf | gate target | is_shadow | gate log emit | 備考 |
|---|---|---|---|---|---|---|
| 2542 | fib_reversal | 71 | ✓ (>69) | 1 | No (既 shadow) | Tier先行で抑制 |
| 2548 | fib_reversal | 75 | ✓ | 1 | No | Tier先行 |
| 2549 | bb_rsi_reversion | 73 | ✓ | 1 | No | Tier先行 |
| 2575 | ema_trend_scalp | 70 | ✓ (境界+1) | 1 | No | Tier先行 |
| 2578 | bb_rsi_reversion | 72 | ✓ | 1 | No | Tier先行 |

**Q4 gate の独立発火 case は観測されず** (全 scalp が tier で既に shadow)。`_add_log("🛡️ Q4_GATE...")` は `if not _is_shadow:` で抑制される設計通り。

## 3. 重要な発見

### 3.1 bb_rsi_reversion の構造的制約

`strategies/scalp/bb_rsi.py` に `adx_max = 25` の自己フィルターが存在:

```python
class BBRsiReversion(StrategyBase):
    adx_max = 25  # レンジ判定上限
```

→ **bb_rsi は構造的に ADX<25 でしか発火しない** → v10 MR penalty (threshold=25) は**常に 0**。

→ bb_rsi の Q4 (conf>69) 問題の primary defense は **Q4 gate** のみ、anti-trend penalty は effectively no-op。

### 3.2 DTE conf-respect の衝撃

**Pre-deploy (legacy bug)**:
- `id=2523 vol_spike_mr BUY` : conf=40 / ema_conf=72 → **32pt gap**
- 原因: legacy `base_conf + ema_boost` が `Candidate.confidence=72` を上書き

**Post-deploy (v10)**:
- `id=2571 vol_spike_mr BUY` : conf=79 / ema_conf=79 → **gap 解消**
- DTE self-calibrated conf=74 尊重 + layer-2 boost で 79

→ legacy formula が **strategies の出力を破壊** していたことを数値で証明。v10 L2772 fix によって DTE pipeline の正しい conf が流通開始。

**追加観測 (06:08:43)**: `id=2576 dt_fib_reversal BUY` — conf=59 / DTE self-conf=62 (layer-2 で -3 pt: VWAP slope falling + 3連続逆行)。
→ daytrade MR-family の `dt_fib_reversal` も DTE pipeline 経由で L2772 fix が適用されていることを確認。v11 gap 候補リストに残るが ADX=18 では penalty=0 なので即時 risk はなし。

### 3.3 未カバー gap (v11 候補)

daytrade MR-type 戦略で `strategy_type` 未タグ → anti-trend penalty 未適用:
- `vol_spike_mr`
- `dt_bb_rsi_mr`
- `dt_fib_reversal`
- `vwap_mean_reversion`
- `eurgbp_daily_mr`
- `ema200_trend_reversal` ⬅ 観測中に追加発見 (2026-04-22 07:31, id=2599, DTE-respect marker)

将来 ADX>25 時に過大 conf が L2772 を通過するリスク。v11 iteration として分離。

**Note**: DTE pipeline を通る全戦略が L2772 fix の恩恵を受けることは観測で確認済み (squeeze_release_momentum / vol_spike_mr / dt_fib_reversal ×3 / ema200_trend_reversal)。v11 は ADX-based penalty の追加適用のみで済む。

## 4. System Safety

| 項目 | 状態 |
|---|---|
| OANDA heartbeat | ok / 106ms latency |
| NAV | ¥441,779 (変化なし) |
| open_trades (OANDA) | 0 |
| recent_errors | `[]` |
| emergency_killed | False |
| main_loop_alive | True |
| main_loop_restarts | 1 (deploy時のみ) |
| watchdog_alive | True |
| 全 trade `oanda_trade_id` | 空 (=OANDA 未送信) |

→ **v10 デプロイ後の実弾リスクはゼロ**。全 scalp/daytrade trade が shadow 扱い。

## 5. 観測の結論 (暫定、~3.5時間 post-deploy)

- ✅ **v10 コード稼働**: 4 case で直接確認 (数学的に期待値一致)
- ✅ **threshold boundary 動作**: ADX<threshold で penalty=0 正しく抑制
- ✅ **Q4 gate 設計通り**: 全対象 trade shadow化、誤動作なし
- ✅ **OANDA 安全**: 実弾送信ゼロ、エラーゼロ、latency 安定
- ⚠️ **bb_rsi penalty no-op**: 自己 `adx_max=25` で penalty 領域に到達せず
- ⚠️ **daytrade MR gap**: v11 iteration 候補 (spawn_task 記録済み)

## 6. 長期観測計画

- **現時点**: N_post=7 gated trades (統計判定には N>50 必要)
- **目標**: 24-48時間 post-deploy で conf 分布 pre/post 比較 → `ema_trend_scalp` の conf>69 率が 25% から有意に低下するか
- **次 checkpoint**: Post-deploy N=30 到達時点で distribution shift 中間レポート
- **Q4 gate 削除 criteria**: confidence_v2 が N>=50 trades/strategy で Kelly>-5% 達成 + ~2026-06-03 目途

## 7. 関連文書

- [[confidence-q4-full-quant-2026-04-22]] — 発動の binding quant 証跡
- [[confidence-formula-root-cause-2026-04-22]] — コード病因解剖
- [[modules/confidence_v2.py]] — 実装
- [[modules/confidence_q4_gate.py]] — 移行期 safety net
- Commit `8fc90eb` — v10 実装本体
