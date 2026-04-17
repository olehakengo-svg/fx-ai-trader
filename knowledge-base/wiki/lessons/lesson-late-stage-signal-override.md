### [[lesson-late-stage-signal-override]]
**発見日**: 2026-04-16 | **修正**: v9.x
- 問題: vwap_mean_reversion/streak_reversalがSL/TP計算後にsignal方向を変更 → SL/TPが逆方向のまま + HTF Hard Blockをバイパス
- 症状: BUYなのにTPがentry下方(158.706→158.612)、0.3秒で即TP_HIT損失。HTF=bearなのにBUY発行
- 原因: compute_signal_daytrade()内の実行順序。SL/TP計算(L1707)→HTFブロック(L2464)→vwap/streak(L3092+)の順で、後段がSL/TPもHTFも無視
- 修正: (1) vwap/streak: signal変更後にSL/TP再計算 (2) 独立HTFチェック追加 (3) vwap: score上書き(旧方向のscore汚染防止)
- 教訓: **関数内で後段がsignal/SL/TPを変更する場合、前段の計算結果(SL/TP, HTF, score)との整合性を再確認する。直列処理の後段は前段の前提条件を壊しやすい**
