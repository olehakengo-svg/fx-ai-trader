# Lesson: Backfill タスクから全体診断への pivot (2026-04-21)

**発見日**: 2026-04-21 | **修正**: 判断のみ (コード変更なし)

## 問題

`scripts/backfill_mtf_regime.py` 作成 + `REGIME_ADAPTIVE_FAMILY` 拡張が依頼されたが, 実装中に以下 3つの前提破壊を発見:

1. **Instrument × Regime 完全交絡**: 全戦略で (regime, strategy) cell が単一 instrument にロック (例: macdh × trend_down_strong = 100% EUR_USD).
2. **BT-Live 乖離の真因 = 市場 regime 遷移**, Fidelity Cutoff bug ではない (4/16 を境に range_tight 14%→58% に 4x 変化).
3. **全 MR/TF 戦略が post-Cutoff で崩壊** (bb_rsi_reversion, fib_reversal 含む).

## 症状

- 当初タスク「新規戦略を REGIME_ADAPTIVE_FAMILY に追加」が意思決定に使えない分析であることが実装後に判明.
- 既存 mapping の validation では **全て符号正しく** (bug なし), しかし現在の損失源は mapping 外の range_tight.

## 根本原因 (方法論的)

**「依頼されたタスクが正しい問題か」を最初に疑わなかった**. 以下の順序で進めるべきだった:

1. Live の現況 (直近 N=全戦略) を先に見る
2. 損失分布 を regime × family で断面
3. **それから** 何を修正/拡張すべきか判断

代わりに「backfill → 2D スキャン → 拡張」の提供された構造に沿って進めた結果, 3回 pivot することになった.

## 修正 (判断)

- `REGIME_ADAPTIVE_FAMILY` 拡張は **凍結** (複数 regime 遷移観測までデータ不十分)
- 真の優先 P0: range_tight × MR 戦略の止血, Gate leak 調査
- Backfill script はデータ衛生として独立に有用 → 別途判断

## 予防策 (protocol)

**新しいタスクを受けたら, 着手前に以下 3問を自問**:

1. **問題の定義**: 「このタスクが解決する問題は何か? 現状データで見えるか?」
2. **前提検証**: 「タスクが前提としている事実 (例: macdh が regime-adaptive 候補) は最新データで真か?」
3. **逆命題**: 「このタスクを完了しても意思決定が変わらないケースは? あれば何故か?」

もし 3問のどれかで答えに詰まったら → **先に診断する**. 実装に入る前にユーザーに問い直す.

## ユーザー challenge が教えたこと

本セッションで 3回の pivot は全てユーザー challenge が契機:

| # | ユーザー発言 | もたらした発見 |
|---|---|---|
| 1 | 「クオンツとしての提案は？」 | エンジニアモードを止め, 実装前検証 3ステップを提案 |
| 2 | 「BT との乖離原因調査が優先じゃないかな？」 | BT-Live 乖離が Fidelity ではなく市場遷移であることを発見 |
| 3 | 「なんで 3戦略だけなんだっけ？」 | family 別の分布差 (BO だけ生存) を発見, pivot 3 |

→ [[lesson-user-challenge-as-signal]] の再確認事例. **ユーザーの簡潔な "ところで"型質問は depth-dive 指示**として扱うべき.

## 関連

- [[regime-strategy-2d-2026-04-20]] §12 (pre-declaration, pivot 後に書き換え予定)
- [[bt-live-divergence]] §3 (6 optimism biases — 本件の BT-Live 乖離は別因)
- [[sessions/2026-04-21-session]] Phase 2
- アーティファクト: `/tmp/step1_live_labeler_check.py`, `/tmp/step2_regime_coverage.csv`, `scripts/backfill_mtf_regime.py`

## 次セッションへの引き継ぎ

1. **P0**: range_tight × MR 戦略の止血判断 (1時間)
2. **P0**: Gate leak 調査 — bb_rsi × trend_up_strong × non-JPY × SELL 15件発火の原因 (30分)
3. **P1**: Backfill 本番適用可否 (Render Shell 経由, 15分)
4. **P2**: REGIME_ADAPTIVE 拡張は **凍結**. BT 2D 実装も P1 完了後.
