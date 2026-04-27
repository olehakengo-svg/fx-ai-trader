# Pre-reg LOCK: Cell-by-Cell Promotion (2026-04-27)

## Status
**rule:R1** — Cell-by-Cell Edge Audit (Q1') + Portfolio Kelly (Q2') の結果を、CLAUDE.md Rule 1 (Slow & Strict) に沿って Pre-reg LOCK として固定。LOCK 期間中はパラメータ・閾値の調整禁止。

## Context

2026-04-27 のクオンツ方針再構築 (plan §7) で、Aggregate Fallacy の訂正により **「足りないのは filter ではなく cell promotion」** と判明。
Aggregate Kelly = -17.97% は赤字 cell が黒字 cell を希釈した結果であり、cell 単位の Wilson lower / Bonferroni / Kelly を正しく計算すると、明確な **promote 対象**と **suppress 対象** が浮上した。

## Audit Results (Source: `tools/cell_edge_audit.py`, demo_trades.db N=349)

### Q1' Cell-by-Cell Edge Audit

Bonferroni 有意な cell (N≥20, p_bonf < 0.05):

| Cell | N (Live/Shadow) | WR | Wilson lower | EV/trade | PF | p_bonf |
|---|---|---|---|---|---|---|
| **fib_reversal × Tokyo × q0 × Scalp** | 24 (0/24) | 87.5% | **69.0%** | +10.82pip | 14.60 | **0.0007** |
| ema_trend_scalp × Overlap × q0 × Scalp | 28 (0/28) | 17.9% | 7.9% | -1.89pip | 0.35 | 0.0020 |
| ema_trend_scalp × London × q0 × Scalp | 21 (0/21) | 14.3% | 5.0% | -2.52pip | 0.23 | 0.0032 |

Live-confirmed but N-thin (Bonferroni 不通過、要追加 N):

| Cell | N (Live/Shadow) | WR | Wilson lower | EV/trade | Kelly Half |
|---|---|---|---|---|---|
| bb_rsi_reversion × Tokyo × q0 × Scalp | 10 (10/0) | 70.0% | 39.7% | +4.09pip | 0.245 |
| bb_rsi_reversion × London × q0 × Scalp | 13 (12/1) | 53.8% | 29.1% | +11.31pip | 0.238 |

### Q2' Portfolio Kelly

| Cell | WR | RR (aw/al) | Kelly | Kelly Half | Kelly Quarter |
|---|---|---|---|---|---|
| fib_reversal × Tokyo × Scalp | 87.5% | 2.09 | 0.815 | **0.408** | 0.204 |
| bb_rsi_reversion × Tokyo × Scalp | 70.0% | 1.42 | 0.489 | 0.245 | 0.122 |
| bb_rsi_reversion × London × Scalp | 53.8% | 7.49 | 0.477 | 0.238 | 0.119 |

**注**: Scalp cells は execution timing 高相関のため、portfolio Kelly ≈ max(single Kelly) に近づく。単純合計は適用しない。

---

## Promotion Plan (LOCKED)

### Tier 1: PROMOTE (Bonferroni-significant)

#### **C1-PROMOTE: fib_reversal × Tokyo × q0 × Scalp**

- **Action**: Shadow → Live 昇格
- **Initial lot**: **0.05 lot (Kelly Quarter / 4)** — 極めて保守的に開始
  - 理由: N=24 全 Shadow、Live 経験ゼロ。Live discount 不明
  - Kelly Half = 0.408 だが、Live 初動は Quarter の 1/4 = 0.10 をさらに半分 = 0.05 lot

##### Standard graduation path

| Live N | 条件 | Lot |
|---|---|---|
| 0〜4 | (初期) | 0.05 維持 |
| ≥ 5 | WR ≥ 50% | 0.05 維持 (確認期) |
| ≥ 10 | Wilson lower > 50% | **0.10** 昇格 |
| ≥ 20 | Wilson lower > 60% | **0.20** 昇格 (Kelly Quarter) |
| ≥ 30 | Wilson lower > 60% | **0.40** 昇格 |
| ≥ 50 | Wilson lower > 60% | **0.80** 昇格 (Kelly Half target) |

##### Fast-track rules (2026-04-27 追加, ユーザー承認)

Live discount が想定 (×0.5) より良い場合、段階を skip して加速:

| 条件 | 通常 lot | Fast-track lot |
|---|---|---|
| Live N≥10 AND WR ≥ 80% AND Wlo > 60% | 0.10 | **0.20** (skip 0.10) |
| Live N≥20 AND WR ≥ 85% AND Wlo > 70% | 0.20 | **0.40** (skip 0.20) |
| Live N≥30 AND WR ≥ 85% AND Wlo > 75% | 0.40 | **0.80** (skip 0.40) |

**Fast-track 安全条件 (全て満たす必要あり)**:
1. 直近 5 trades が連続 LOSS ではない
2. Bonferroni p < 0.01 (Shadow + Live 合算)
3. MC ruin ≤ 5% (現在の Live state simulation で再計算)
4. Fast-track 適用は同一 cell につき各段階 1 回のみ
5. tools/daily_live_monitor.py が直近 7 日間 severity=OK を出している

##### Rollback gate (常時優先、fast-track より優先)

以下のいずれかで即対応:

| 条件 | アクション |
|---|---|
| Live N ≥ 5 で WR < 50% | 0.05 lot 復帰 + observation 延長 |
| Live N ≥ 10 で Wilson lower < 40% | 即 Shadow 復帰 |
| 連続 3 LOSS | 0.05 lot 復帰 (一段階以上昇格していた場合) |
| MC ruin > 10% | 即 Shadow 復帰 |

### Tier 2: SUPPRESS (Bonferroni-significant losers)

#### **C2-SUPPRESS: ema_trend_scalp × Overlap × q0 × Scalp**

- **Action**: 既存 R2-A Suppress に **追加** (現在 London のみ登録)
- 修正対象: `modules/strategy_category._R2A_SUPPRESS` に行追加
  ```python
  ("ema_trend_scalp", "Overlap", "q0"): 0.5,
  ```
- **根拠**: N=28 WR=17.9% Wilson lower 7.9% p_bonf=0.0020、明確に有意な負エッジ
- **rollback**: 不要 (suppress は loss prevention only)

#### **C3-SUPPRESS: ema_trend_scalp × London × q0 × Scalp** (既登録)

- 既に R2-A Suppress 対象 — 確認のみ
- 監査値: N=21 WR=14.3% Wilson lower 5.0% p_bonf=0.0032 で suppress 妥当性を再確認

### Tier 3: WATCH (Live-confirmed, N不足)

#### **C4-WATCH: bb_rsi_reversion × Tokyo × q0 × Scalp**

- **Action**: 現状維持 (既に Live 出走中、N=10 全 Live)
- Live N≥20 まで観察、Wilson lower>50% かつ Bonferroni 有意になれば PROMOTE

#### **C5-WATCH: bb_rsi_reversion × London × q0 × Scalp**

- **Action**: 現状維持 (Live N=12)
- Live N≥20 まで観察、Wilson lower>50% に到達するか追跡

---

## Implementation (Code Changes)

### 1. routing_table.json 更新 (C1-PROMOTE 反映)

`modules/routing_table.json` に fib_reversal × Tokyo × q0 × Scalp の Live entry を追加 (lot 0.05)。

### 2. modules/strategy_category._R2A_SUPPRESS 更新 (C2 追加)

```python
_R2A_SUPPRESS: dict[tuple, float] = {
    ("stoch_trend_pullback", "Overlap", "q2"): 0.5,
    ("sr_channel_reversal", "London", "q3"): 0.5,
    ("ema_trend_scalp", "London", "q0"): 0.5,
    ("vol_surge_detector", "Tokyo", "q3"): 0.5,
    ("ema_trend_scalp", "Overlap", "q0"): 0.5,  # NEW (C2-SUPPRESS, p_bonf=0.0020)
}
```

### 3. tests/test_r2a_suppress.py 拡張

C2 の追加に対応する assertion を追加 (Overlap × q0 × ema_trend_scalp で multiplier=0.5 を確認)。

---

## LOCK 期間

- **Start**: 2026-04-27
- **End**: 2026-05-11 (2 weeks)
- LOCK 中: 上記パラメータ・lot 値・閾値の変更禁止
- Live N≥10/cell で中間レビュー、それまでは継続観察のみ

## Failure Modes (lesson 化条件)

以下に該当した場合、本 Pre-reg LOCK は失敗として `wiki/lessons/` 行きとする:

1. **C1 fib_reversal Tokyo Scalp**:
   - Live N≥10 で Wilson lower < 40% (Shadow→Live 乖離が想定以上)
   - Live N≥10 で WR < 50% (構造的な Live discount 過小評価)
2. **C2 ema_trend_scalp Overlap suppress**:
   - 既に negative edge なので失敗ケースは限定的だが、suppress 後に当該 cell の Live trade が著しく増えた場合は実装ミス疑惑

## Verification

LOCK 期間終了後 (2026-05-11) に再 audit:

```bash
python3 tools/cell_edge_audit.py --include-shadow --min-n 10
```

期待結果:
- C1: Wilson lower 50%+ 維持
- C2: Live trade 数 0 (suppress 効果)
- C4/C5: N≥20 到達、Bonferroni 有意 → 次回 LOCK で PROMOTE 検討

## References

- [Plan file (approved)](/Users/jg-n-012/.claude/plans/users-jg-n-012-downloads-files-zip-cozy-finch.md) §7
- [Cell Edge Audit raw output](../../../raw/audits/cell_edge_audit_2026-04-27_inclshadow.md)
- [Cell Edge Audit JSON](../../../raw/audits/cell_edge_audit_2026-04-27_inclshadow.json)
- [Wave 2 prereg bypass decision](wave-2-prereg-bypass-2026-04-27.md)
- [CLAUDE.md Rule 1/2/3](../../../CLAUDE.md)

## Sign-off

- Quant analysis: Claude Opus 4.7 (cell_edge_audit + portfolio_kelly)
- Approval (plan §7): User, 2026-04-27
- Implementation: pending (commit 後)
