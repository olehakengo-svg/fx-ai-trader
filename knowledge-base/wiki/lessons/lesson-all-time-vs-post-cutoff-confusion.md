### [[lesson-all-time-vs-post-cutoff-confusion]]
**発見日**: 2026-04-20 | **修正**: 判断プロトコル追加 (本 lesson)

- **問題**: Claude が 1セッション内で「aggregate edge=-0.1348 (Kelly=0)」「ema_trend_scalp edge=-0.353」などの指標を根拠に複数の施策提案 (XAU 浄化、pair-level 救済、PAIR_DEMOTED 拡充) を実施・提案したが、これらの edge 値は **all-time data** から算出されたもので、**post-cutoff (`_FIDELITY_CUTOFF=2026-04-16`) の Kelly 基準データではなかった**。
- **症状**:
  - 本番 `/api/demo/stats?include_shadow=0` の `total: 448` は all-time
  - post-cutoff 指定 (`date_from=2026-04-16`) すると **N=14** しかない
  - Risk dashboard の `edge=-0.1348` も内部計算ウィンドウ不明のまま使用してしまった
  - 真の状態: Post-cutoff Live **WR=35.7%, EV=+0.36 pip, PnL=+5.0** (わずかに正EV、ただし N<20 で Kelly 算出不能)
- **原因**:
  1. `/api/demo/stats` のデフォルト date_from は None (all-time) — cutoff 明示指定が必須
  2. `_get_aggregate_kelly()` は cutoff + exclude_xau + exclude_shadow の 3 重 filter、Risk dashboard の "edge" は別計算経路
  3. Strategy-level Kelly の `edge` / `kelly` / `n` の算出ウィンドウが混在していたことを見逃した
  4. **KB 確認なしに指標を信頼** (lesson-kb-drift, lesson-reactive-changes 同根)
- **修正**:
  - 判断前に必ず「**その指標の算出ウィンドウは?**」を明示確認
  - 本番 API 呼び出しは cutoff 明示指定 (`?date_from=2026-04-16`)
  - 複数 source の edge/Kelly 値を比較する前に filter を揃える
- **教訓**: **数値を信じる前に、その数値がどの期間・どのフィルタで算出されたかを確認する。All-time data は pre-cutoff 汚染を含むため、Kelly/edge 判断に使ってはならない**
- **関連**:
  - [[lesson-clean-slate-2026-04-16]] — `_FIDELITY_CUTOFF` 導入の経緯
  - [[lesson-kb-drift-on-context-limit]] — KB 読まずに判断する失敗パターン
  - [[lesson-reactive-changes]] — 1日/短期データでの反射的変更
  - [[lesson-raw-json-to-llm]] — 集計済みテーブルを LLM に渡すべき
