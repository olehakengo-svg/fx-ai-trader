# Handoff

## State
mtf_regime_trend_cascade_scalp v2 のコンセプト実証完了 (PF=2.58, EV=+3.03p, Kelly=+23.6%, 180日 USD_JPY)。ただし3つのバグが未修正のままで戦略コミット保留中。新戦略ファイル群・wiki docs・CHANGELOG がすべて untracked (git add 未実施)。

## Next
1. **Fix 1**: `app.py` の `_compute_bt_htf_bias` に m15/m5 inject を追加 (BT pipeline bug — 現状 MTF cascade 戦略は全 BT で N=0)
2. **Fix 2**: `strategies/scalp/mtf_regime_trend_cascade_scalp.py` の L3 を緩和 (ema_order + ema9_touch 削除)
3. **Fix 3**: SL formula に floor 追加 `max(atr7*0.3, 5pip)` → EUR_USD の 100% SL hit を解消

その後 365日 BT 再実行 → Rule 1 gate 通過確認 → 全ファイルまとめて commit。

## Context
- `_bt_regime_cascade_scalp_vec.py` は m15/m5 precompute あり (local parquet 活用) — Fix 1 の参考実装として使える
- range cascade (`mtf_regime_range_cascade_scalp`) は demo_trades 実測で否定済み → enabled=False のまま放置で OK
- BT 汚染防止: `BT_MODE=1 NO_AUTOSTART=1` 環境変数が fix 済み (13f7d24)
- Fix 検証の BT は `_bt_regime_cascade_scalp.py` を直接実行
