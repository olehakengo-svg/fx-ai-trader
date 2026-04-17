### [[lesson-dte-htf-bypass]]
**発見日**: 2026-04-16 | **修正**: v9.1 (36e5cbb)
- 問題: DTE戦略がHTF Hard Blockをバイパスし、GBP_USD session_time_bias 4/4 SELL全敗、dt_sr_channel_reversal 4/4全敗
- 症状: HTF=bullでSELLトレードが実行される。reasonsに「📈 4H+1D 上昇一致 → SELLブロック」が記録されているのにトレードが通過
- 原因: (1) DTE HTF Hard Blockが最善候補にのみ適用（リスト段階でフィルタリングしていなかった） (2) 個別戦略にHTFチェックがなかった
- 修正: 3重HTFガード実装 — (a) DTE候補リスト全体からHTF違反を除外 (b) session_time_bias.py/dt_sr_channel.py内にself-contained HTFチェック追加 (c) mainパイプラインのscore=0化
- 教訓: **セーフティネットは単一レイヤーに依存してはならない。戦略自身がHTFを知っているべき（self-contained guard）。中央フィルターのみに依存すると、パイプラインの構造変更でバイパスが生まれる**
