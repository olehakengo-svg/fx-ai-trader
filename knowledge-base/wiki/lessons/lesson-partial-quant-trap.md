### [[lesson-partial-quant-trap]]
**発見日**: 2026-04-21 | **修正**: 判断プロトコル統合済み (Rule 1 promotion 判断で必須)
- 教訓: **N/WR/EV の一次統計だけでは engineer mode**。完全な quant 判断には PF / Wilson 95% CI / Walk-Forward / Bonferroni / Kelly まで要求される。
- 発端: 2026-04-21 bb_squeeze_breakout × USD_JPY PAIR_PROMOTED commit でユーザーから「クオンツとしての見解は?」と challenge を受け、PF/Wilson/WF/Bonferroni/Kelly が抜けていたことが判明。
- 同日 Audit B で `dt_fib_reversal × GBP_USD` を 365d BT 再走 → promotion 時 N=22 WR=72.7% → 現在 N=30 WR=53.3% (19.4pp シフト、Wilson CI 下限 51.8% を下回り)。**小-N BT はノイズ、365d BT ≠ ground truth**。
- 適用ルール:
  1. promote/demote 判断前に必ず PF + Wilson 95% CI + WF 3-bucket + Sharpe-like + Kelly full/half を計算
  2. 複数セル検定時は Bonferroni α/M を適用
  3. Live データ前に decision rule を pre-register (post-hoc bias 排除)
  4. 小-N BT (N<30) は promotion 候補にしない、既存の小-N promoted は Audit B パターンで定期再監査
  5. BT 推定は random variable — PF/EV を書くなら不確実性レンジも併記
  6. 逆校正判定にも同じ厳格さ (Fisher exact 2-tail p + Bonferroni + WF 2-bucket 符号安定性)
- 参照ノート: 3 箇所 (regime-2d-v2-rescan-result-2026-04-22, spread-entry-gate-preregister-2026-04-22)
- 関連: [[lesson-reactive-changes]], [[pre-registration-label-holdout-2026-05-07]]
