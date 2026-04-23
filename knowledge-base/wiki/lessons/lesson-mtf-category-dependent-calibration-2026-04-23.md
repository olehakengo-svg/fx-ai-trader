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
ただし `app.py:8869-8878` Layer 1 `大口方向一致` の `score *= 1.15` は active、
これは category-naive な boost で TF で最強 -16.7pp の逆校正に寄与している可能性。

**User review required**: Layer 1 category-aware 化 or 中立化の可否。

## Prevention rule

[feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md) に追加:

> **Aggregate の label × WR だけではなく、category × label × WR の 2D を必ず見る。**
> Aggregate が 0.0 でも category 内で +10.8 / -7.5 が打ち消し合っている可能性。

## References

- [[mtf-gate-category-audit-2026-04-23]]
- [[full-label-audit-2026-04-23]]
- [[tf-inverse-rootcause-2026-04-23]]
