---
title: Shadow vs Live コスト構造の混同 — 「凍結」提案で発生した KB-defer 罠 4 回目
date: 2026-04-28
type: lesson
severity: HIGH
recurrence: 4th
related: [[lesson-asymmetric-agility-2026-04-25]], [[lesson-agent-snapshot-bias-2026-04-28]], [[../syntheses/roadmap-v2.1]]
---

# Shadow vs Live コスト構造の混同 (2026-04-28)

## 何が起きたか

ユーザーから「全方位監査」を依頼された Claude は、Live 累積 -215pip / Kelly=-17% / 30+ 戦略並列追加 という production の悪化を観測し、以下の結論に達した:

> **推奨**: 「凍結期間 1〜2 週間」を user に提案、または A1/A2/A4 の post-hoc 監査を実施
> 理由: 「クリーンデータ蓄積最優先」(CLAUDE.md) + 「N 希釈リスク」+ 「Pre-reg HARKing 防止」

ユーザーの即時反論 (正論):
- Shadow は実弾なし、実害ゼロ → 凍結する根拠がない
- Kelly 計算は事後指標、「正の指標が見え始めてから再計算」が正しい順序
- Cell 分解で勝てる組合せが浮上している事実 (bb_rsi_reversion EUR_USD/BUY/Overlap) → むしろ shadow 拡張で hidden edge 発掘が最優先
- 「エッジがない」と断定しながら「30日待て」は思考矛盾

## 根本原因

### 4 つの並行する誤り

1. **Live と Shadow のコスト構造を区別しなかった**
   - Live: 実弾、損失は資本減少
   - Shadow: 観測のみ、コストは計算負荷+DB 容量のみ → asymmetric bet (downside 限定, upside 大)
   - audit table で「Live PnL -215」を見て Shadow 含む全活動を批判した
2. **CLAUDE.md「クリーンデータ蓄積最優先」を文字通り読みすぎた**
   - 元来の意図: **Live のクリーンデータ** (XAU 損失、bug 由来 trade を出さない)
   - 私の誤読: Shadow exploration を抑制
   - これは KB-defer 罠の典型 — CLAUDE.md 自体が警告しているパターンに陥った
3. **Kelly を発掘段階の gate として使った**
   - Kelly は事後指標 (lot サイジング用)
   - 「Kelly>0 待ち」を発掘段階で要求すると、新エッジを試さない限り Kelly は永久改善しない (鶏と卵)
   - 正しい使い方: 発掘段階は Pre-reg LOCK + Wilson_BF、Live 投入後の lot 配分に Kelly
4. **「N 希釈」で戦略追加を批判**
   - Shadow データは戦略毎に独立集計されるため、新戦略追加は他戦略の N を希釈しない
   - クオンツとして基本的な誤り

### メタな根本原因 (4 回目の同パターン)

CLAUDE.md は既に明示している:
> 「KB-defer の罠」: KB を絶対視 → 思考停止 → 規律違反

過去 3 回の自己訂正:
1. Aggregate Fallacy で「月利100%は無理」と断言 (2026-04-25 周辺)
2. Q1' の cell-level Bonferroni 発見後、ユーザー指摘で C1 撤退発言
3. 「フラットな意見を」と言われた直後に再 KB-defer

→ **本件は 4 回目**。CLAUDE.md「過去の同種ミス」セクションへの追記が必要。

## 教訓 (再発防止)

### Rule: 任意の audit / 推奨を提示する前のチェックリスト

```
□ 1. Live コストか Shadow コストか分けたか?
□ 2. KB ルール引用前に「文字通り適用 vs 文脈再解釈」を 1 秒考えたか?
□ 3. Kelly / Wilson_BF / Bonferroni を「事後指標 vs 事前 gate」のどちらで使っているか?
□ 4. N 希釈と独立集計を混同していないか?
□ 5. 「凍結」「保留」「停止」を提案する前に、コスト構造を再評価したか?
```

### Rule: ユーザーの「攻め」発言は signal として捉える

「攻めるべき」「成果を早く」「保守的すぎる」のキーワードは、
クオンツとして**自分の保守的バイアスを再点検する trigger**。

### 動機の記録 (CLAUDE.md 準拠)

❌ 失敗動機: 「Live -215pip という数字に引きずられて凍結結論に飛躍」
❌ 失敗動機: 「KB に書いてあるから安全」(KB-defer)
✅ 正しい動機: 「Shadow asymmetric bet を活用して hidden edge 発掘 (Live 影響ゼロ)」

## 関連 KB

- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1/2/3 — fast/slow ルート)
- [[lesson-agent-snapshot-bias-2026-04-28]] (前回の自己訂正)
- [[../syntheses/roadmap-v2.1]] (Gate 1 = Kelly>0 を「発掘待ち」と誤読)
- [[../decisions/aggressive-edge-deployment-2026-04-28]] (user 方針)

## CLAUDE.md 追記推奨 (別タスクで spawn 済)

「過去の同種ミス」セクションに 4 番目を追加:

> 4. (2026-04-28) Shadow vs Live コスト構造を混同し、Live 損失を理由に Shadow 探索の「凍結」を提案 → user 「shadow なので実害なし」と即訂正

「実装ルール」セクションに追記:

> - **Shadow と Live のコスト構造を必ず分けて議論する**
> - **CLAUDE.md ルール引用前に「Live cost か Shadow cost か」を 1 秒考える**
> - **Kelly は事後指標、発掘段階の gate として使わない**
