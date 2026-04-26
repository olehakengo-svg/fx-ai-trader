# R2 Suppress Implementation — stoch_trend_pullback × Overlap (2026-04-26)

> **STATUS: 実装完了** (rule:R2, Asymmetric Agility framework)

**Source evidence**: [[phase4d-II-nature-pooling-result-2026-04-26]]
**Pre-reg path**: [[pre-registration-phase4d-II-nature-pooling-2026-04-26]] LOCKED → result → R2-A 抽出
**File modified**: `modules/demo_trader.py` L2767-2786 (after L2766 mode_trades, before entry filters)
**Asymmetric Agility classification**: **Rule 2 (Fast & Reactive)** — lot↓/suppression
**Discipline**: 365日 BT skip 認可 (R2 framework), Bonferroni 不要

## Implemented rule

```python
# Phase 4d-II R2-A: stoch_trend_pullback × Overlap session 抑制
if entry_type == "stoch_trend_pullback":
    _hour_utc = datetime.now(timezone.utc).hour
    if 13 <= _hour_utc < 17:  # Overlap session (London×NY, UTC 13:00-17:00)
        _orig_conf = confidence
        confidence = int(confidence * 0.5)
        self._add_log(...)
```

## Evidence summary

| | Before suppression | Wilson 95% CI |
|---|--------------------|---------------|
| stoch_trend_pullback overall | N=164, WR=24.4% | — |
| stoch_trend_pullback × Overlap | N=54, WR=11.1% | **[5.2, 22.2]%** |
| Tokyo (best) | N=62, WR=29.0% | [19.2, 41.3]% |

Wilson upper bound 22.2% < baseline 24.4% で **clean suppress** (lift -13.3%).

## Important caveat (discovered post-implementation)

**stoch_trend_pullback は既に `_FORCE_DEMOTED` (modules/demo_trader.py L5199)** で
shadow-only 運用中. 元の demote 理由:
> Post-cut N=19 WR=31.6% EV=-0.97 PnL=-18.5 全ペアで負

これは本 R2 rule の **直接 live PnL impact** が限定的であることを意味する:
- FORCE_DEMOTED 戦略は **OANDA live 送信なし**
- Shadow trade として記録のみ
- 本 rule は shadow trade の confidence を下げ、`confidence_threshold` 未達で
  shadow 記録自体を block する可能性

### それでも本 rule に意味がある理由

1. **Shadow data quality 向上**: WR 11% の noisy shadow を学習 (Sentinel/Kelly
   推定) から除外する効果. 下流 alpha 探索の noise 削減.
2. **将来の re-promotion 時の保護**: stoch_trend_pullback が将来 PAIR_PROMOTED 等
   で live に戻る場合、本 rule が**自動的に Overlap session を抑制**.
3. **Infrastructure template**: 同じ pattern で他 strategy × session の R2 rule を
   追加する template 確立. Per-strategy session-specific suppression が今後 standard
   pattern.
4. **Asymmetric Agility framework の R2 demonstration**: pre-reg → result → 抽出 →
   実装 → KB 記録の full cycle を 1 day で実行.

## Trade volume estimate (rule 適用範囲)

```
Overlap session = UTC 13:00-17:00 = 4 hours/day
Market open = 5 days/week
Total Overlap minutes/week = 1200

stoch_trend_pullback × Overlap historical: 54 trades / 18 days = 3.0/day
→ Rule 適用予想: ~3 shadow entries/day を confidence ×0.5 で抑制
→ 多くは confidence_threshold 未達で shadow 記録から消える見込
→ 月次 ~60 noisy WR=11% trades を学習データから除外
```

## Reversibility

```python
# Revert は 1 行コメントアウトで完了:
# if 13 <= _hour_utc < 17:
#     confidence = int(confidence * 0.5)
```

または条件分岐 1 行 (`if False and 13 <= _hour_utc < 17:`) で即時無効化.

## Monitoring (本日以降)

R2 framework 通り、live N=10 程度で効果評価:
- `[R2_PHASE4D_II]` ログを `/api/demo/logs` で grep
- Overlap stoch trade が減少しているか確認 (既存 shadow が threshold 未達で
  block される expected)
- 1 week 後に rule 適用前後の shadow stoch × Overlap WR を比較

## 次の R2 候補 (live impact 大、要 evidence 強化)

本 R2-A は shadow-only 戦略のため live PnL impact 限定. **live 影響大** の R2 候補
を以下に列挙:

| 候補 | 状態 | Phase 4d/4d-II 上の evidence |
|------|------|------------------------------|
| ema_trend_scalp × Overlap session ×0.7 | Active in PAIR_PROMOTED for some pairs | descriptive のみ, dWR -0.8% (weak) |
| vol_surge_detector × Tokyo × high spread | ELITE_LIVE 候補 | descriptive のみ, N=23 WR=30.4% |
| bb_rsi_reversion × NewYork session | Active | dWR -12.3%, Wilson [11.7, 38.1]% (CI overlap, weak) |

これらは現データでは Wilson CI が baseline と overlap で **decisive evidence なし**.
60 days 蓄積後に再評価で R2 promotion 候補.

## Discipline check

- ✅ Pre-reg LOCK → result → 抽出の順序 (post-hoc narrative なし)
- ✅ R2 framework 適合 (loss prevention, lot↓)
- ✅ rule:R2 marker in code comment
- ✅ Reversibility 確保
- ✅ KB doc cross-reference
- ⚠️ 直接 live PnL impact は限定的 (FORCE_DEMOTED 状態のため)
- ⚠️ Bonferroni 通過なし — Wilson CI 単独 evidence

## References

- [[phase4d-II-nature-pooling-result-2026-04-26]] (本 R2 evidence source)
- [[phase4d-session-spread-routing-result-2026-04-26]] (descriptive routing emergence)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (上位 plan, Section 10 R2 immediate)
- `modules/demo_trader.py` L2767-2786 (実装箇所)
- `modules/demo_trader.py` L5199 (`stoch_trend_pullback` FORCE_DEMOTED 記録)
- [[lesson-asymmetric-agility-2026-04-25]] (R2 framework 定義)
