### [[lesson-orb-trap-bt-divergence]]
**発見日**: 2026-04-16 | **修正**: v9.1 (36e5cbb)
- 問題: orb_trapが短期BT(60d)ではWR=79-83% EV>+0.5だったが、365d BTでは全ペア負EV (JPY=-0.854, EUR=-0.488, GBP=-0.258)
- 症状: PAIR_PROMOTED 3ペア + LOT_BOOST 1.5xで損失拡大
- 原因: 短期BTのカーブフィッティング。60日の好調期間がたまたまBTウィンドウに入っていた
- 修正: FORCE_DEMOTE + PAIR_PROMOTED削除 + LOT_BOOST削除
- 教訓: **短期BT(60d)のWR/EVを365d BTで必ず検証すべき。特にN<30の戦略は短期BTの分散が大きく、カーブフィッティングと区別がつかない**
