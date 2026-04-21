### [[lesson-kb-blind-pp-proposal]]
**発見日**: 2026-04-21 | **修正**: 提案撤回（コード変更未発生）

- 問題: shadow post-cutoff の `engulfing_bb × EUR_USD` N=23 EV=+1.13 を見て「未トラッキングの新エッジ → 即時 PAIR_PROMOTED 登録」と提案した
- 実態（KB確認後）:
  - `strategies/engulfing-bb.md` 既存
  - Tier = **FORCE_DEMOTED**（v8.0 WR=14.3% PnL=-$353.5）
  - EUR_USD / USD_JPY 両方 **PAIR_DEMOTED** 済み（v8.9）
  - 現 N=23 は Edge Pipeline の shadow 再検証フェーズが **正しく動作している観察** であり、Stage 2→3 Gate（N≥30, BT確認）未達
- 原因:
  1. 前セッションの trade 分析結果（shadow +34.6pip）を KB 照合せず「新エッジ」と判定
  2. 直前に「Edge Pipeline を飛ばさない」で自己訂正したにも関わらず同セッションで再発
  3. 「PAIR_PROMOTED 追加前に FORCE_DEMOTED 残留確認」lesson を無視
- 修正: 提案1撤回。正しい処遇は「shadow 観察継続（N≥30）→ 365d BT 符号確認 → Bayesian posterior 判定」
- 教訓: **「shadow 観察で +EV が出た」は Edge Pipeline が動いている証拠。次の行動は `strategies/*.md` と `tier-master.md` を読むこと。読まずに「新エッジ発見」と結論するのは KB を飾り扱いしている証左**

## 再発防止
- strategy 提案前の必須手順:
  1. `grep -i <entry_type> knowledge-base/wiki/tier-master.md`
  2. `Read knowledge-base/wiki/strategies/<name>.md`（存在すれば）
  3. `grep <entry_type> knowledge-base/wiki/analyses/pair-promoted-candidates-*.md`（直近）
- 1-3 のいずれもゼロ件のときのみ「新規登録」を議題にする
- FORCE_DEMOTED からの復活は **必ず 365d BT 符号確認を先行**
