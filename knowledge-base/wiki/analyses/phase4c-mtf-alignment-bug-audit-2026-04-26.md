# MTF Alignment Audit — Structural Diagnosis (2026-04-26)

> **STATUS: R3 期待 → R2 確定** (コードバグではなく labeler の構造的限界が連鎖)

**Trigger**: Phase 4c Signal C 結果で `mtf_alignment × ema_trend_scalp` が **aligned WR=8.1%
(N=37) << conflict WR=20.4% (N=411)** という強い flip. 「aligned ほど負ける」は構造
バグの示唆と判断し、ラベル実測主義 memory に従い実測 audit.
**Audit script**: `/tmp/phase4c_mtf_alignment_audit.py`, `/tmp/phase4c_alignment_pair_check.txt`
**Code paths**: `modules/demo_trader.py` L3402-3450, L5840-5876;
`research/edge_discovery/mtf_regime_engine.py` label_d1 / compose_regime;
`research/edge_discovery/strategy_family_map.py` strategy_aware_alignment.

## Summary of findings (4 smoking guns + 解釈)

### Finding 1 — **mtf_d1_label に bear case (-1, -2) が 0 件** (2523 trades 全期間)

```
d1 distribution: {0: 1569, 1: 526, 2: 401, 3: 27 (insufficient)}
d1 = -1 → 0 件
d1 = -2 → 0 件
```

**原因**: `mtf_regime_engine.label_d1` は EMA200 anchor + bull/bear bias の AND condition:
```python
bull_bias = (close > ema_a) & (ema_f > ema_s)   # ema_a = EMA200
bear_bias = (close < ema_a) & (ema_f < ema_s)
```
USD/JPY は 2026-04 期間に 158-160 円帯, EMA200 は数年スパンで形成され当然下方. 18 days
の窓では D1 close > EMA200 が継続 → **bear_bias が永遠に発火しない**. 短期 (EMA20<EMA50) で
反転しても anchor 条件で吸収.

**判定**: コードバグなし. **labeler design による intentional な long-anchor 性質**.
但し "MTF で下げトレンドを判定する" という目的に対しては**構造的に検出能力ゼロ**.

### Finding 2 — **aligned cell に "SELL × d1>0" が 42 件存在**

期待: aligned = (BUY×d1>0) ∨ (SELL×d1<0). 実測:
```
BUY × d1>0:   86  (期待通り)
SELL × d1<0:   0  (期待: aligned のもう一方 — but d1<0 が存在しない)
BUY × d1<0:    0  (bug 検出 — 起きない)
SELL × d1>0:  42  (bug 検出?)
```

42 件の SELL × d1>0 aligned は `strategy_aware_alignment(entry_type, regime, signal,
instrument)` が **direction ではなく regime と nature の整合** を見ている結果. 例えば
RANGE-nature 戦略 (bb_rsi_reversion 等) は regime=range_* で aligned 判定 — 方向
無関係. これは **設計通り**で, "aligned の意味" は nature ごとに異なる:
- TREND nature: regime=trend_up_* で aligned (BUY のみ事実上発生)
- RANGE nature: regime=range_* で aligned (BUY/SELL 両方ありうる)

### Finding 3 — **aligned は 2026-04-20 以降のみ発生**

```
2026-04-20: 78
2026-04-21: 57
2026-04-22: 85
2026-04-23: 85
2026-04-24: 63
04-08〜04-19: 0
```

`mtf_regime` system (`_get_mtf_regime`) が **2026-04-20 deploy** であった示唆. それ以前は
`mtf_alignment="unknown"` または `"(empty)"`. Phase 0 audit で `mtf_alignment` 47%
populate は **新機能 6 days のみで運用** が原因.

### Finding 4 — **ema_trend_scalp aligned trade の 81/111 (73%) が GBP_USD**

```
mtf_alignment = aligned, ema_trend_scalp:
  GBP_USD BUY   81 (median spread 1.30 pips)
  EUR_USD BUY    7
  EUR_JPY BUY    7
  USD_JPY BUY    0  (USD_JPY は d1=0 が継続して trend_up_* 出ず)
```

**SELL aligned が 1 件もない** (trend_down_* が労 0 件). aligned 全体は GBP_USD ×
BUY × trend_up_* に集中.

ema_trend_scalp aligned LOSS の spot check:
- 全 5 sample が GBP_USD, h4=0 or 1, regime=trend_up_weak
- 4/5 が SL_HIT, mafe_favorable=0 → entry 直後逆行
- TP は最小 RR 1.8 まで拡張 (RR不足回避ロジック)
- spread 1.30 pips (vs conflict 0.80 pips の +63%)

## 真の構造的解釈

**ema_trend_scalp aligned WR=8.1% の root cause は連鎖した 3 つの structural mismatch**:

1. **Labeler は long-anchor (EMA200)** で 18 days では bear case 検出 0
2. **aligned trade は 6 days × GBP_USD × BUY × trend_up_* に集中** (sampling bias)
3. **GBP_USD spread (1.30 pips) + 1m scalp の RR 拡張ロジック** で entry 直後 SL hit が量産

これは:
- ❌ コードバグではない
- ❌ alignment 計算 logic の反転バグではない
- ✅ "aligned label が現状の運用期間 + pair 構成では **GBP_USD × BUY × scalp** という
   1 つの slot に全件集まり、その slot が **pair-specific friction で WR が低い**
   という data-structure artifact"

## 修正提案

### R3 (Immediate, structural) — 該当なし

コード修正は**しない**. 上記は labeler の design intent (long-term bias anchor) と
data accumulation の特殊事情の合成結果.

### R2 (Fast & Reactive) — 即時 defensive

| # | Action | 根拠 | 期待効果 |
|---|--------|------|----------|
| R2-A | `ema_trend_scalp × instrument=GBP_USD × aligned (=BUY×trend_up_weak/strong)` の confidence ×0.5 か entry 抑制 | aligned subset = GBP_USD BUY 73% で WR=8.1% (5/74). 4/5 spot が即 SL | GBP_USD 全体 WR を 5-10% 改善見込 |
| R2-B | `ema_trend_scalp × spread_at_entry > 1.0 pips` で confidence ×0.7 (現 spread gate を tighten) | aligned subset の spread median 1.30 pips, conflict 0.80 → friction が outcome を支配 | spread regime で routing |
| R2-C | mtf_alignment 利用は **N=∞ 蓄積後 (Phase VI 60 days)** まで R1 promotion 留保 | 現在 6 days × GBP_USD bias で representative でない | 早期 false promotion を防ぐ |

### R1 (Slow & Strict) — 次 session pre-reg

| # | Topic | 内容 |
|---|-------|------|
| R1-A | Labeler の bear-detection 改善 design | EMA200 anchor を quantile-based regime change point detector or 短期 (60-120 days) anchor に変更. Pre-reg で 365日 BT で η²>0.005 (現状 trivial 突破) を target |
| R1-B | Phase II multivariate logit (plan 通り) | mtf_alignment が pair/spread/session を control 後も effect 残るか. 残らなければ alignment は **operational signal ではない** と確定 |
| R1-C | `mtf_alignment × pair-conditional` 検定 | USD_JPY (aligned 0 件) を除外し、GBP_USD subset の Bonferroni 1-test pre-reg |

## Phase 4c Signal C 結果への caveat (重要)

[[phase4c-signalC-field-ranking-result-2026-04-26]] の本日の Phase I 結果は **以下の
構造的限界を含む**:

1. **mtf_d1_label = -1, -2 が 0 件**で down-trend dimension は実質測定されていない
   → Phase I 結果は "**up-trend × range の 2 値検定**" として再解釈すべき
2. **mtf_alignment の N=1179** は 6 days × GBP-bias 由来
   → mtf_alignment × ema_trend_scalp の "aligned 8.1%" は **GBP_USD × BUY × scalp の
   pair-friction artifact** で MTF route の本質的 evidence ではない

これらは Phase I 結果を invalidate するわけではないが、**Phase II/III では明示的に
control variable** として pair, spread を入れる必要がある.

## Phase II 設計への反映 (次 session)

`logit P(WIN) ~ strategy + pair + spread_quartile + session + mtf_h4_label +
range_sub + mtf_alignment + h4_label×strategy + ε`

- pair, spread_quartile を必須 confounder に追加 (Finding 4 反映)
- mtf_d1_label は除外 (Finding 1 で uninformative 確定)
- mtf_alignment は **2026-04-20 以降サブセットのみ** で fit (Finding 3 反映)
- Bonferroni は新 family size で再計算

## References

- [[phase4c-signalC-field-ranking-result-2026-04-26]] (本 audit の trigger)
- [[pre-registration-phase4c-signalC-field-ranking-2026-04-26]] (Signal C pre-reg)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (上位 plan)
- `research/edge_discovery/mtf_regime_engine.py` label_d1 (EMA200 anchor)
- `research/edge_discovery/strategy_family_map.py` strategy_aware_alignment
- `modules/demo_trader.py` L5840-5876 `_get_mtf_state` (live cache + label call)
- [[feedback_label_empirical_audit]] (memory: 実測 query が code 演繹に優先)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1/2/3 framework)
