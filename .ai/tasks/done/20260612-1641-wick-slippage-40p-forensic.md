---
id: 20260612-1641-wick-slippage-40p-forensic
priority: P2
gate: R3
rule: R3
status: queued
created: 2026-06-12
owner: codex
---

# wick_imbalance_reversion slippage -40p×2 forensic — 記録バグ vs 実損の判定

**Rule 分類**: R3 (データ整合 / 記録の算数破綻疑い)

## Background (Claude 一次データ実測 2026-06-12)

30d clean live 監査で GBP_USD の slippage 異常値を 2 件検出:

| entry_time (UTC) | strategy | slippage_pips | pnl_pips | edge_cell_id |
|---|---|---|---|---|
| 2026-06-10T17:46 | wick_imbalance_reversion | **-40.2** | +1.3 | (空) |
| 2026-06-10T18:41 | wick_imbalance_reversion | **-40.8** | -10.9 | E10 |

GBP_USD の通常時間帯で 40pip スリッページは市場実態として不自然 (当日 NY 午後、フラッシュイベント未確認)。同戦略の他 3 件は 0.8〜2.5p。**-40p が実損なら pnl_pips への反映有無も含め E10 の即停止判定 (R2) に直結**するため、記録系か実損かを確定させる。

## Tasks

1. 該当 2 トレードの `demo_trades` 全カラム + `oanda_audit` 対応行 (signal_price / entry_price / OANDA fill price) を突合
2. OANDA transaction 履歴 (`/api/oanda/trades` or sync 済 oanda_trades テーブル) の実 fill price と比較し、slippage_pips の計算式を derivation
3. 判定:
   - **記録バグ** (例: signal_price と fill price の基準ズレ、pip scale 誤り) → 修正 + 過去データ backfill + 単体テスト
   - **実損** → E10/wick_imbalance の執行品質レポート (時間帯×spread×slippage 分布) を出し、R2 停止判定の材料として final.md に明記
4. slippage_pips 異常値 (|slip|>10p) の全期間スキャンを添付 — 他戦略にも同パターンがないか

## 制約

- spread 基準は entry_price ベースで比較 (lesson: spread-basis-for-mafe 2026-05-XX)
- データ一次ソースは Render 本番 API。ローカル DB 不可
- 外部 API (OANDA) を使うテストは mock-only 禁止、実 API E2E で検証 (lesson: codex-mock-test-trap)


## Result (2026-06-12T08:01:58Z)

exit=0 · 364s

```
判定: **記録/基準価格バグ**です。OANDA 実約定は -40p ではありません。

対象 2 件は OANDA transaction ledger で opening fill が `1.33841` / `1.33837`、`demo_trades.entry_price` と一致。`slippage_pips=-40p` は stale な `signal_price=1.34245` と実 entry を比較した診断値でした。`pnl_pips` は実 entry/exit から計算されており、-40p は PnL に反映されていません。

対応内容:
- [app.py](/data/repo/fx-ai-trader/app.py:3602): wick V2 の signal payload に `slippage_signal_price_basis="entry_fill"` と `rebase_tp_to_current_price=True` を追加。
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:3737): TP 距離を実 entry price 基準へ再基準化する helper を追加。
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:5438): 診断用 `signal_price` を entry fill 基準で記録する分岐を追加。
- [tools/backfill_stale_signal_slippage.py](/data/repo/fx-ai-trader/tools/backfill_stale_signal_slippage.py:1): Render shell 用 backfill スクリプトを追加。dry-run default、`--apply` で更新。
- [tests/test_stale_signal_slippage_backfill.py](/data/repo/fx-ai-trader/tests/test_stale_signal_slippage_backfill.py:1): slippage 符号、候補抽出、backfill、TP rebase の単体テストを追加。
- 監査レポート: [reports/wick_imbalance_slippage_forensic_2026-06-12.md](/data/repo/fx-ai-trader/reports/wick_imbalance_slippage_forensic_2026-06-12.md:1)

全期間スキャンは Render API から 2026-04-01〜2026-06-12 の closed 9,797 rows を週次取得。`|slippage_pips|>10` は 76 件で、`wick_imbalance_reversion × GBP_USD × live` は今回の 2 件のみでした。他は主に shadow または XAU/JPY 系の別パターンです。

検証:
```bash
.venv/bin/python -m pytest tests/test_stale_signal_slippage_backfill.py tests/test_wick_imbalance_reversion_shadow_redesign_v2.py tests/test_alpha_wick_imbalance_shadow_redesign_v2.py
```
結果: `11 passed`

補足: この worker には本番 `/var/data/demo_trades.db` が無いため、backfill の本番適用自体は未実行です。Render shell ではレポート記載のコマンドで OANDA fill 検証付き適用できます。
```
