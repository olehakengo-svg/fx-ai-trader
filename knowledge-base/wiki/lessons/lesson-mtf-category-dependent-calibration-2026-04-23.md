# Lesson: MTF alignment は category-dependent (2026-04-23)

**Date**: 2026-04-23
**Severity**: TF Delta WR -7.5pp (INVERSE), MR Delta WR +10.8pp (POSITIVE)
**Source**: `mtf_alignment` カラム + `reasons` tag

## Observation

MTF alignment (aligned / conflict / neutral) の WR 効果は **戦略カテゴリに依存**:

| Category | aligned WR | conflict WR | Delta | 判定 |
|----------|-----------|-------------|-------|------|
| TF | 12.9% (N=31) | 20.4% (N=284) | -7.5pp | 🚨 INVERSE |
| MR | 30.3% (N=208) | 19.5% (N=200) | +10.8pp | ✓ POSITIVE |
| OTHER | 23.1% (N=26) | 27.3% (N=66) | -4.2pp | ⚠ weak inv |

MR は設計通り (aligned = 逆張り support)、TF は逆 (aligned = trend 終盤のモメンタム枯渇)。

## Root cause

1. 現在の市場レジーム (2026-04-08〜) は **TF 逆行バイアス**
2. MTF aligned 検出は内部的に一律 boost として扱われていた (category 非条件)
3. TF aligned で boost しても勝率は **下がる** — これが逆校正

## Fix status

Conf_adj レベルの MTF alignment boost はすでに中立化済。

**Correction (2026-04-23 後日)**: 当初は `app.py:8869-8878` Layer 1 `大口方向一致`
`score *= 1.15` が TF -16.7pp の主因と仮説したが、[[layer1-bias-direct-audit-2026-04-23]]
で実測: data の **99% が layer1_dir=neutral で boost 未適用**、かつ適用時は Delta +18.3pp
(正校正)。Layer 1 自体は無害。

真の原因は **TF 戦略群そのものの regime mismatch** (EMA alignment 検出 = trend 終盤で
fade される)。戦略レベルの Tier 降格 / Sentinel で対処すべき問題。

## Prevention rule

[feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md) に追加:

> **Aggregate の label × WR だけではなく、category × label × WR の 2D を必ず見る。**
> Aggregate が 0.0 でも category 内で +10.8 / -7.5 が打ち消し合っている可能性。

## References

- [[mtf-gate-category-audit-2026-04-23]]
- [[full-label-audit-2026-04-23]]
- [[tf-inverse-rootcause-2026-04-23]]
