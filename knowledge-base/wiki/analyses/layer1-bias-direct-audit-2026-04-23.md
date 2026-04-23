# Layer 1 Large-flow Direction Match — Direct Audit (2026-04-23)

**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2059
**Script**: `/tmp/layer1_bias_audit.py`
**Trigger**: [[full-label-audit-2026-04-23]] で方向一致 Delta -8.8pp (TF -16.7pp) の源泉として
`app.py:8869-8878` Layer 1 を仮説。reasons tag を emit しないため direction × layer1_dir
カラムで直接検証。

## TL;DR — 仮説は誤り

Layer 1 direction-match の score *= 1.15 boost は **正校正** (Delta +18.3pp) だが、
データの **99% で layer1_dir=neutral** のため事実上 dormant。
方向一致 -16.7pp の主因は Layer 1 ではない。

## Raw data

### Classification definition

- `match`: `direction=="BUY" and layer1_dir=="bull"` or `direction=="SELL" and layer1_dir=="bear"` → score *= 1.15
- `conflict`: direction と layer1_dir が逆 → score *= 0.50
- `unknown`: layer1_dir=="neutral" → score *= 0.80
- `missing`: layer1_dir が NULL

### Overall

| Class | N | WR | Wilson 95% CI | EV |
|-------|---|-----|---------------|----|
| match | 13 | 30.8% | [12.7, 57.6] | -1.70p |
| conflict | 16 | 12.5% | [3.5, 36.0] | -3.75p |
| unknown | **2030** | 23.9% | [22.1, 25.8] | -2.33p |

Delta (match − conflict): **WR +18.3pp, EV +2.05p** ✓ POSITIVE (設計通り)

### Per-category

どの category (TF/MR/OTHER) でも match/conflict は N<15 で分解不可。
`unknown` が dominant (TF 573/573, MR 1085/1085, OTHER 372/372)。

## Interpretation

1. **Layer 1 boost は実質使われていない** — 99% の trade で layer1_dir=neutral
2. **使われた時は正しく機能** — match +18.3pp positive calibration, ただし統計的には
   N=13 で弱い確証 (CI [12.7, 57.6] が広い)
3. **以前の仮説 (Layer 1 が方向一致 -16.7pp の主因) は誤り** — 実測で棄却

## Corrected attribution

`full-label-audit-2026-04-23.md` の "方向一致 Delta -8.8pp (TF -16.7pp)" の源泉は:

1. ❌ ~~app.py:8869-8878 Layer 1 score *= 1.15~~ — dormant, かつ sign 正
2. **✓ strategy files (多数)** の `reasons.append("✅ EMA方向一致")` — label のみ、
   conf_adj なし。ただし label が入る condition = "EMA と direction が合う" は、
   現在の TF-fade レジームでは **selection bias** となり WR を下げる
3. **→ 真の原因**: TF 戦略そのものが regime-inappropriate。EMA alignment 検出 = trend 終盤で
   fade 食らう。戦略レベルの gating (Sentinel shadow 維持 / Tier 降格) 側で対処すべき

## Implication for lessons

[[lesson-mtf-category-dependent-calibration-2026-04-23]] の "Layer 1 score boost 要 user review"
記述は **訂正** が必要 — Layer 1 自体は問題ではなく、TF 戦略の regime mismatch が本質。

## Statistical caveat

- N=13 match は Wilson CI が広く (12.7%–57.6%), Δ=+18.3pp が有意かは怪しい
- 将来 N が増えたら再監査
- 現状では「layer1 boost は無害」という結論で十分

## Next actions

- [[lesson-mtf-category-dependent-calibration-2026-04-23]] の Fix status を訂正
- Layer 1 の修正は不要 (本 commit 対象外)
- 真の対処: TF 戦略群の Tier 再評価 (別 task)

## References

- [[full-label-audit-2026-04-23]]
- [[mtf-gate-category-audit-2026-04-23]]
- Raw output: `/tmp/layer1_bias_output.txt`
- Script: `/tmp/layer1_bias_audit.py`
