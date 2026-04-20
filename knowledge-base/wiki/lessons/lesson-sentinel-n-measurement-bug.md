# Lesson: Sentinel N 測定バグ — 観測専用トレードを非観測フィルタで数えた

**発見日**: 2026-04-20 | **修正**: v9.x (task/priority3-sentinel-n-measurement)

## 何が起きたか

62 戦略中 `bb_squeeze_breakout` だけが Sentinel N=1 と報告され、他 61 戦略が N=0。
しかし本番 DB には closed Shadow トレードが **1,466 件** 存在していた
(`/api/demo/stats?include_shadow=1`)。つまり「Sentinel は動いていたのに
ダッシュボード上はゼロに見える」という構造的測定バグ。

## 根本原因

`modules/demo_db.py :get_trades_for_learning()` は v7.0 から `is_shadow=0` を
**固定フィルタ**として適用している（lesson-shadow-contamination の正しい修正）。
aggregate Kelly / 学習エンジンに Shadow を混ぜない目的で、これは正しい。

しかし `_evaluate_promotions` (`modules/demo_trader.py :4742`) は
同じ関数を流用して `_strategy_n_cache[et] = n` を更新し、
`_build_strategy_status_map` (`app.py :11814`) がその `n` をそのまま UI に表示していた。

結果: Shadow でのみ発火する戦略（Sentinel セット全体）は N=0 のまま固定。
`bb_squeeze_breakout` が N=1 を出せたのは、過去にフィルタを通り抜けて
実弾発注された 1 件の live トレードがあっただけの偶然。

言い換えると: **「観測専用トレードの観測サンプル数」を
「観測専用トレードを除外する関数」で数えていた**。

## 修正

1. `demo_db.get_shadow_trades_for_evaluation()` を新設
   （is_shadow=1 固定、by_type/by_type_pair/by_instrument、XAU 除外デフォルト）
2. `app._build_strategy_status_map()` が新関数を呼び、
   `shadow_n / shadow_wr / shadow_ev` を各戦略に付与
3. `/api/sentinel/stats` 新設（entry_type/instrument/after_date フィルタ対応）
4. `get_trades_for_learning` は**変更しない**（Kelly 汚染防止は維持）
5. `tests/test_shadow_stats.py` — 正例 4 / 負例 3 / 空 3 = 10 tests

## 教訓

### データ二系統の原則

Shadow と Live は**役割が逆**のデータなので、集計関数も二系統必要:

| 用途 | 対象 | 関数 |
|---|---|---|
| aggregate Kelly / 学習 | is_shadow=0 (Live) | `get_trades_for_learning` |
| Sentinel 昇格評価 / UI | is_shadow=1 (Shadow) | `get_shadow_trades_for_evaluation` |

「shadow=1 を除外する関数」を「shadow=1 を数える場面」で使うのは定義矛盾。

### lesson-tool-verification-gap の再適用

- 「N=0 が 61 戦略」を**見たのに疑わなかった** → 空結果＝バグの典型
- スモーク指標（「N が出てる」）で OK 判定 → 「出ている N が正しいか」未検証
- 本番 shadow_count=1466 を早期に確認していれば即検出できた

### lesson-shadow-contamination の逆向き警告

Shadow を「混ぜてはいけない場所」だけでなく
「数えなければいけない場所」を明示的に持たないと、
contamination 対策が測定バグに化ける。

## 再発防止

- 新規の「N / WR / EV を使う場所」を追加するとき、
  データソースが `is_shadow=0` / `is_shadow=1` のどちらなのかをコメントで明示
- UI 側は `n` (live) と `shadow_n` を並列表示し、0 表示の意味を曖昧にしない
- N=0 が広範囲に出るときは**先に DB の生カウントを確認**する

## 関連

- [[lesson-shadow-contamination]] — aggregate Kelly を汚さない（正しい）原則
- [[lesson-shadow-persistence-bug]] — is_shadow フラグの DB 反映ずれ
- [[lesson-tool-verification-gap]] — 空結果を疑う
- [[lesson-raw-json-to-llm]] — 集計は Python 側で確実に
- [[changelog]] — v9.x エントリ
