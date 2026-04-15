### [[lesson-conf-undefined-bug]]
**発見日**: 2026-04-14 | **修正**: v9.0 C1
- 問題: demo_trader.py L2974/2993/3035で `conf` 変数が未定義 → NameErrorで tick全体が中断
- 症状: RANGE+SELL, TREND_BULL+BUY, TREND_BEAR+BUY のシグナルが全て無音で消失。ログは「シグナル取得失敗」に誤分類
- 原因: `confidence` 変数を `conf` として参照（タイポ）
- 修正: `conf` → `confidence` に全箇所置換 + ログ文字列も修正
- 教訓: **変数名変更時は全参照箇所をgrepで確認する。新変数が既存フィルターで使われていないか検証する。**
