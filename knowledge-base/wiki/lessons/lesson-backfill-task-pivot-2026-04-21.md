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
3. **P0'**: BT 摩擦 Tier 1 (mode×pair 摩擦係数テーブル化) — レジーム判定の根本原因 R1-R3 を一発緩和する唯一の fast path (半日)
4. **P1**: Backfill 本番適用可否 (Render Shell 経由, 15分)
5. **P2**: REGIME_ADAPTIVE 拡張は **BT 摩擦改善後に解凍**. BT 2D 実装もその後.

## 追加教訓 (2026-04-21 session 末尾)

「別プロジェクト」のラベルは危険信号. BT 摩擦モデル改善を当初「別プロジェクト」と分類したが,
実際には本件 (レジーム判定不可能の根本原因) を一発緩和する唯一の fast path だった.

**教訓**: タスクを「別」と呼ぶ前に「それが解決すると何が unblock されるか」を明示する.
別として分離するのは, unblock 対象がない (独立) か, unblock しても優先度が変わらない時のみ.

## Phase 3 追記: Shadow contamination で同じ間違いを繰り返した

セッション末, ユーザーが「本日の OANDA はプラス」と指摘してくれたことで私の分析の重大な欠陥が判明:

**問題**: `/tmp/trades_all.json` を解析する際に `is_shadow` フィルタをかけずに LIVE と SHADOW を合算.
結果として SHADOW の損失を LIVE の損失と誤認し, 「全戦略崩壊」「gate leak 疑い」「range_tight 止血必要」という誤った緊急対応を提案した.

**実際**:
- LIVE post-Cutoff: **+5 pips 黒字** (bb_rsi_reversion WR 75%)
- SHADOW post-Cutoff: -1388 pips (gate 通過前の観測値)
- 「gate leak 疑いの 15件」は **全て is_shadow=1** (仕様どおりの shadow 観測)

**[[lesson-shadow-contamination]] (2026-04-10, v8.4) の再発**. `get_stats()` のバグは修正済だが, ad-hoc 分析で同じ汚染を起こした.

**影響**: challenge なしに次セッションへ引き継がれていたら「機能している gate を壊す P0 変更」に着手するところだった. production harm 寸前.

**予防策**:
1. Live trades を解析する際は **冒頭で is_shadow 分布を必ず print**. 混在ありなら LIVE/SHADOW 別々に集計.
2. 「全戦略が losing」のような極端な結論が出た時点で shadow contamination を疑う
3. ad-hoc 分析用の helper 関数化を検討 (P1 tooling 候補)

**教訓 (統合)**: ユーザー challenge は **診断の深化** だけでなく **事実訂正** の機会でもある. 自分の分析結果が production 観察と矛盾する時, まず分析の前提 (フィルタ条件, サンプル定義) を疑う.
