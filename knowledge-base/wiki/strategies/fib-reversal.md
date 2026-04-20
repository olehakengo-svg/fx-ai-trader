# fib_reversal

## Status: FORCE_DEMOTED (Recovery Path Active — 全ペア強制 Shadow) — v9.1 PAIR_PROMOTED 死コード削除; v9.x (2026-04-20) demo_db legacy override 削除
**Dramatic improvement post-cutoff: WR 25.6% → 55.0% (v6.3 parameter effect confirmed)**
**2026-04-20 Priority 2 監査: 180d Scalp BT で 60d EV=+0.271 → 180d EV=-0.147 符号反転** (lesson-orb-trap-bt-divergence 再現例)

## Performance
| Period | N | WR | PnL | Notes |
|--------|---|-----|-----|-------|
| Pre-cutoff (all) | 117 | 25.6% | -18.0 | Contaminated by SLTP bug |
| **Post-cutoff** | **20** | **55.0%** | **+35.6** | v6.3 params working |
| Post-cutoff (shadow-excl, latest) | 32 | 40.6% | +21.9 | More data, still positive |
| BT (Scalp v3.2) | 172 | 57.0% | - | EV=+0.056 ATR |

## Recovery Path
```
Current: FORCE_DEMOTED (N=32, WR=40.6%)
  N>=30 & WR>=50% → SENTINEL (0.01 lot)       ← approaching
  N>=50 & WR>=52% & PF>1.1 → PAIR_PROMOTED    ← target
```

## v6.3 Changes That Caused Improvement
| Parameter | Before | After | Effect |
|-----------|--------|-------|--------|
| proximity | 0.50 ATR | **0.35 ATR** | Entry at actual Fib level, not "near" |
| SL | 0.5 ATR | **0.7 ATR** | Survives initial shakeout |
| TP | 1.8 all | **JPY=1.8, EUR/GBP=1.3** | Friction-aware |
| body_ratio | none | **>=0.50 (v6.3), >=0.60 (v8.3)** | Confirmation candle |

## v8.3 Changes (instant death reduction)
- Fib hierarchy: 38.2% score>=4.5, 50% >=3.5, 61.8% >=3.0
- MACD-H required for non-Tier1 extreme entries
- body_ratio 0.50 → 0.60
- Expected: instant death 75.9% → 25-35%

## Statistical Significance (Independent Audit)
- WR=25.6% → 55.0%: z=3.013, **p<0.002 (significant)**
- Wilson 95% CI: [34.2%, 74.2%] (wide — N=20)
- Conclusion: "Improvement is statistically significant but true WR could be 35-55%"

## MAFE
- WIN avg MFE: 3.57pip
- LOSS 75.9% instant death (MFE=0)
- v8.3 targets 25-35% instant death

## v9.3 P2: REGIME_ADAPTIVE Family (2026-04-17)

本戦略も regime 方向で family 挙動が反転する非対称性を示す (Phase C N=177).
`REGIME_ADAPTIVE_FAMILY` で regime 別に family をオーバーライドする。

### 観測された非対称性

| Regime | BUY WR | SELL WR | 差 | 実挙動 |
|---|---|---|---|---|
| `trend_up_weak`/`_strong` | 25% | **48%** | +23pp | **MR** (逆張り SELL が aligned) |
| `trend_down_weak`/`_strong` | 33% | **45%** | +12pp | **TF** (順張り SELL が aligned) |

bb_rsi_reversion とは **方向が逆** の非対称性:
- bb_rsi: up=TF / down=MR
- fib: up=MR / down=TF

これは fib_reversal が本来 MR 戦略だが、下落トレンドでは「Fib 戻り売り」が
セキュラー下落トレンドに沿った TF 挙動になるため。

### 現行マッピング

```python
REGIME_ADAPTIVE_FAMILY["fib_reversal"] = {
    "trend_up_weak": "MR",
    "trend_up_strong": "MR",
    "trend_down_weak": "TF",
    "trend_down_strong": "TF",
}
```

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)

**EUR_USD BT 系列 — 符号反転事例:**
- Scalp 1m 60d EV=+0.271 (v8.3 時点で PAIR_PROMOTED 根拠)
- Scalp 1m 180d EV=**-0.147** (2026-04-15 更新で反転確認)
- 365d DT 15m: 発火 0

**EUR_USD Live (post 2026-04-07):** N=51 (shadow=22, live=29) WR=39.2% EV=-0.298 PnL=-15.2p

Gate1 (EV≥+0.2) 不通過 + Gate4 (60d/365d sign) 失敗 → demo_db legacy override 削除。
参照: [[pair-promoted-candidates-2026-04-20]], [[lesson-orb-trap-bt-divergence]]

## Related
- [[mfe-zero-analysis]] — 75.9% instant death analysis
- [[bb-rsi-reversion]] — Similar MR strategy (77.6% instant death)
- [[independent-audit-2026-04-10]] — Statistical validation
- [[mtf-regime-validation-2026-04-17]] §C (P0 forensics) / §E (REGIME_ADAPTIVE)
- [[pair-promoted-candidates-2026-04-20]] — Priority 2 監査
