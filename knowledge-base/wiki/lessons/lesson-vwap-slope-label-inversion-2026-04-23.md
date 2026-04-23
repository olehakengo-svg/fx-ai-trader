# Lesson: VWAPスロープ ラベル逆校正 (2026-04-23)

**Date**: 2026-04-23
**Severity**: Delta WR -7.0pp (N_has=1647, TF -13.3, MR -4.1)
**Source**: `modules/massive_signals.py:176-195`

## Observation

Full label audit で `VWAPスロープ` ラベル付き trades は unlabeled より **WR -7.0pp 劣る**:
- has (rising/falling のいずれか): N=1647 WR 22.5% EV -2.60p
- no (flat 等): N=410 WR 29.5% EV -1.26p
- Category 分解: TF Delta -13.3pp / MR Delta -4.1pp (両方逆校正)

## Root cause

VWAP が傾いている = 短期トレンド確立、という直感的仮説で conf_adj +2 を与えていた。
しかし実データは逆:
- VWAP slope rising 時の BUY は **遅いエントリ** (trend 終盤で逆回転を食う)
- VWAP slope falling 時の SELL も同様

現在の市場レジームでは VWAP の短期勾配はモメンタム継続ではなく **mean reversion の兆候**。

## Fix applied

- `modules/massive_signals.py:186-195` (commit `b37ee8b` 系): conf_adj 中立化済み
- 残存: label 文言 `"VWAPスロープ rising/falling"` が reasons に含まれる
  → 断定的 ("rising") でダッシュボード等下流の消費者が方向確信として誤読する恐れ

## Next action

label 文言を観察口調に変更 or 削除 (今回のコミットで実施予定)。

## Rule (derived)

[feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)
適用: 「VWAP が傾けばトレンド」のような仮説は直感的に正しく見えても、labeled data
の WR 実測を必ず verify せよ。

## References

- [[full-label-audit-2026-04-23]]
- [[lesson-why-missed-inversion-meta-2026-04-23]]
