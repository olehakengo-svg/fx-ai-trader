### [[lesson-resend-shadow-leak]]
**発見日**: 2026-04-20 | **修正**: v9.x hotfix (demo_db.py)
- 問題: `_resend_pending_oanda_trades()` が FORCE_DEMOTED/PAIR_DEMOTED/MTF-shadow 戦略を OANDA に実弾送信
- 症状: is_shadow=1 の open trade に oanda_trade_id が設定される。db では shadow なのに OANDA margin が消費される
- 原因: `get_open_trades_without_oanda()` の SQL が `is_shadow` を未フィルタ (`WHERE status='OPEN' AND oanda_trade_id IS NULL`)
  → 起動時・OANDA 再接続時に shadow trades も "未送信" と判定され全件 OANDA 送信
  → 通常フロー (L4190-4207) の shadow/promoted チェックを完全バイパス
- 修正: SQL に `AND is_shadow=0` 追加 (1行)。shadow trades は resend 対象外になる
- 発覚経緯: "デモ LIVE=0 なのに OANDA 転送されている" という本番監視で判明
- 具体的被害:
  - sr_channel_reversal USD_JPY BUY (FORCE_DEMOTED, oanda_trade_id=320787)
  - orb_trap GBP_USD BUY (FORCE_DEMOTED, oanda_trade_id=318111)
  - bb_rsi_reversion EUR_USD SELL (PAIR_DEMOTED, oanda_trade_id=325370)
  - vwap_mean_reversion GBP_USD SELL (MTF gate A 降格, oanda_trade_id=325362)
- 教訓: **"補完送信" 系の再送パスは、通常の OANDA 送信ガード (is_promoted / is_shadow) と同じフィルターを持つべき。補完パスはガードをバイパスしやすい**
