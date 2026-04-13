### [[lesson-sentinel-promoted-conflict]]
**発見日**: 2026-04-13 (3回目: 2026-04-14) | **修正**: v8.9

- 問題: PAIR_PROMOTEDとUNIVERSAL_SENTINELの両方に同じ戦略が存在 → shadow化 → OANDA送信遮断
- 症状: 「PAIR_PROMOTED + QH適用開始」と宣言したのに、実際はis_shadow=1のまま。QH/BE/TS全て未適用
- 原因: `_is_shadow_eligible_full`がUNIVERSAL_SENTINELを参照 → フィルターバイパス時にshadow=True → `_is_promoted`がFalseに上書き(3713行)
- 再発履歴:
  1. session_time_bias (v8.9初期) → SENTINELから削除で修正
  2. london_fix_reversal (v8.9初期) → 同上
  3. xs_momentum (2026-04-14) → 同上。post-commit-verifyが検出すべきだったが、FORCE_DEMOTED×SENTINELのみチェックしていた
- 修正:
  - xs_momentumをUNIVERSAL_SENTINELから削除
  - post-commit-verify.shにPAIR_PROMOTED×SENTINEL重複チェックを追加
- 教訓: **PAIR_PROMOTEDに追加したら、同じ戦略がUNIVERSAL_SENTINEL/SCALP_SENTINEL/FORCE_DEMOTEDに残っていないか必ず確認する。自動検出がなければ人間が3回同じ間違いをする**
- 対策: post-commit-verifyで自動検出済み。今後は同じ矛盾がコミット時に即座にフラグされる

## Related
- [[lesson-say-do-gap]] — 「実装した」と言って検証しないパターンの一形態
- [[lesson-tool-verification-gap]] — ツールを作って使わないパターン
