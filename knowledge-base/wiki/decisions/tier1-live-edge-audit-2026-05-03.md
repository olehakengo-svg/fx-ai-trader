# Tier 1 LIVE edge audit - 2026-05-03

Verdict: NEEDS_MORE_EVIDENCE
ACCEPT cell count: 0 / 5
ACCEPT cell list: none

## Source / separation

- 一次ソース: `/tmp/live-trades-20260503.json`
- 最新取得: `curl -s https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000 -o /tmp/live-trades-tier1.json` はこの環境で exit 6。既存Render snapshotで判定。
- Live集計: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status=CLOSED`。
- XAU除外、outcome は WIN/LOSS/BREAKEVEN、`pnl_pips != null`。
- Live/OANDA closed rows: 736
- Shadow rows (closed, FX): 3930。Live統計には混入なし。
- Drift warning rows (`is_shadow=1` and `oanda_trade_id!=''`): 0。本タスクのLive集計からは除外。
- Bonferroni: m=5, alpha'=0.05/5=0.010。本レポートの ACCEPT_CELL は Bonferroni p < 0.010 を要求。

## Verdict rationale

- 判定: **NEEDS_MORE_EVIDENCE**
- 根拠: 5 cells have N<30
- 本監査は LOCK proposal。`app.py` / `modules` / `strategies` / 本番DB / OANDA設定は変更していない。

## 5 cell delta-from-BT

| strategy | instrument | N | WR | BEV_WR | Wilson lo | EV pip | PF | total pip | max DD | raw Kelly | p(edge) | Bonferroni p | delta-from-BT WR | delta-from-BT EV | delta-from-BT PF | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback | GBP_USD | 3 | 66.67% | 37.90% | 20.77% | -4.43 | 0.409 | -13.3 | 2.25% | -0.9638 | 0.3220 | 1.0000 | -8.33% | -5.50 | -1.59 | NEEDS_MORE_EVIDENCE |
| trendline_sweep | GBP_USD | 4 | 50.00% | 37.90% | 15.00% | -0.97 | 0.418 | -3.9 | 0.67% | -0.6964 | 0.4882 | 1.0000 | -23.00% | -1.57 | -1.26 | NEEDS_MORE_EVIDENCE |
| session_time_bias | USD_JPY | 0 | 0.00% | 34.40% | 0.00% | +0.00 | 0.000 | +0.0 | 0.00% | +0.0000 | 1.0000 | 1.0000 | -79.00% | -0.58 | -2.46 | REJECT_CELL |
| session_time_bias | EUR_USD | 0 | 0.00% | 39.70% | 0.00% | +0.00 | 0.000 | +0.0 | 0.00% | +0.0000 | 1.0000 | 1.0000 | -70.00% | -0.21 | -1.34 | REJECT_CELL |
| xs_momentum | USD_JPY | 0 | 0.00% | 34.40% | 0.00% | +0.00 | 0.000 | +0.0 | 0.00% | +0.0000 | 1.0000 | 1.0000 | -69.00% | -0.27 | -1.43 | REJECT_CELL |

## Aggregate impact estimate

| bucket | N | WR | EV pip | total pip | PF | raw Kelly | max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| all Live/OANDA rows | 736 | 38.86% | -0.81 | -597.4 | 0.680 | -0.1854 | 60.46% |
| Tier 1 target 5 cells only | 7 | 57.14% | -2.46 | -17.2 | 0.411 | -0.8190 | 2.25% |
| non-target Live/OANDA rows | 729 | 38.68% | -0.80 | -580.2 | 0.684 | -0.1810 | 60.10% |

## Next task

- 次タスク: まず shell network/DNS が通る環境で最新Render snapshotを再取得して同スクリプトを再実行。結果が同じなら N<30 / N<100 cell の蓄積待ち、または Shadow→Live 通路と `is_shadow` drift の再点検。
