### [[lesson-shadow-persistence-bug]]
**発見日**: 2026-04-16 | **修正**: v9.x
- 問題: FORCE_DEMOTED戦略がis_shadow=0でDBに書き込まれ、統計を汚染（114件）
- 症状: get_stats()でFORCE_DEMOTED戦略のトレードが非shadow扱い → PnL/WR/Kellyが実態より悪化
- 原因: open_trade() (L3890)でis_shadow書込み → 安全ネット(L4049)でis_shadow=True変更 → DB UPDATEなし。~160行の乖離
- 修正: (1) 安全ネット後にDB UPDATE追加 (2) 起動時マイグレーションで既存114件を修正
- 教訓: **DB書込み後にフラグを変更するロジックは、変更をDBに反映しないと無意味。書込みと後処理の順序を常に確認する**
