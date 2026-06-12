# wick_imbalance_reversion slippage forensic - 2026-06-12

## Verdict

記録/基準価格バグ。OANDA 実約定は -40p ではない。

対象 2 件の OANDA opening fill は `demo_trades.entry_price` と一致しており、
`slippage_pips=-40p` は stale な `signal_price=1.34245` と実 entry 1.3384 台を
比較した診断値だった。`pnl_pips` は実 entry/exit 価格から計算されているため、
-40p は PnL に二重反映されていない。

ただし、wick V2 closed-bar confirmation の `sig["entry"]` が実行時価格ではなく
candle 側価格を保持していたため、診断値だけでなく TP の距離基準もズレる。
今回の修正では wick V2 のみ、実行時に TP 距離を current fill 基準へ再基準化し、
`signal_price/slippage_pips` も entry fill 基準で記録する。

## Target Trades

| demo_trade_id | entry_time UTC | edge | demo entry | demo signal | demo slip | demo pnl | OANDA trade | OANDA open fill | OANDA close fill | OANDA realizedPL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `873e93ab-8fd` | 2026-06-10T17:46:20.573840+00:00 |  | 1.33843 | 1.34245 | -40.2 | +1.3 | 506330 | 1.33841 | 1.33856 | +120.1155 |
| `918c870a-d0e` | 2026-06-10T18:41:40.934936+00:00 | E10 | 1.33837 | 1.34245 | -40.8 | -10.9 | 508690 | 1.33837 | 1.33728 | -876.5400 |

## Derivation

Current code recorded:

```text
BUY slippage_pips = (current_price - signal_price) * 10000
```

For `873e93ab-8fd`:

```text
(1.33843 - 1.34245) * 10000 = -40.2p
```

For `918c870a-d0e`:

```text
(1.33837 - 1.34245) * 10000 = -40.8p
```

OANDA transaction ledger:

```text
506330 ORDER_FILL MARKET_ORDER price=1.33841 units=5000
508687 ORDER_FILL STOP_LOSS_ORDER price=1.33856 units=-5000 pl=120.1155
508690 ORDER_FILL MARKET_ORDER price=1.33837 units=5000
508694 ORDER_FILL MARKET_ORDER_TRADE_CLOSE price=1.33728 units=-5000 pl=-876.5400
```

## All-Period Scan

Source: Render production `/api/demo/trades`, weekly windows from 2026-04-01 to
2026-06-12, plus 2026-06-01 to 2026-06-12 refresh. Rows fetched: 9,797 closed
trades. Threshold: `abs(slippage_pips) > 10`.

Result: 76 abnormal rows. Most are shadow rows or XAU rows with large spread
units. The only `wick_imbalance_reversion × GBP_USD × live` rows above 10p are
the two target rows.

June non-XAU abnormal groups:

| group | n |
|---|---:|
| vix_carry_unwind / USD_JPY / SELL / shadow | 4 |
| dt_sr_channel_reversal / GBP_JPY / BUY / shadow | 2 |
| wick_imbalance_reversion / GBP_USD / BUY / live | 2 |
| dt_sr_channel_reversal / EUR_JPY / BUY / shadow | 2 |

## Fix

- `app.py`: wick V2 signal payload now carries:
  - `slippage_signal_price_basis="entry_fill"`
  - `rebase_tp_to_current_price=True`
- `modules/demo_trader.py`: when those flags are set:
  - TP preserves the original TP distance but is rebased from actual current entry price.
  - diagnostic `signal_price` is recorded as current entry fill, so `slippage_pips=0` unless real order-send/fill drift is separately introduced.
- `tools/backfill_stale_signal_slippage.py`: dry-run by default; on Render shell, use `--apply` to set `signal_price=entry_price, slippage_pips=0` for verified stale signal rows.

Recommended production backfill command:

```bash
python3 tools/backfill_stale_signal_slippage.py \
  --db /var/data/demo_trades.db \
  --strategy wick_imbalance_reversion \
  --instrument GBP_USD \
  --verify-oanda \
  --apply
```

## Verification

```bash
.venv/bin/python -m pytest \
  tests/test_stale_signal_slippage_backfill.py \
  tests/test_wick_imbalance_reversion_shadow_redesign_v2.py \
  tests/test_alpha_wick_imbalance_shadow_redesign_v2.py
```

Result: 11 passed.
