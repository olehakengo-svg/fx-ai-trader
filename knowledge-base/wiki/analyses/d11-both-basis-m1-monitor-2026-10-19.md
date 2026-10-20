---
title: D11 両基準併記 — m1_clean_live_monitor --strong に broker realized 列 (2026-10-19)
tags: [d11, m1, f3, estimand, monitoring, r3]
status: implemented
---

# D11 両基準併記: demo pnl_pips と broker realized を同一母集団で並記する

**Rule**: R3 (計測器の構造修理、live 経路変更なし)。registry `integrated-decision-packet-d11-both-basis-impl` (期日 10-31) の (1) Claude 実装。(2) user 決裁 (REG F3 の predicate 改定可否) は本稿では**確定しない** — 読み手は姉妹 entry `integrated-decision-packet-d11-user-decision` (11-10、実効窓は carry_dip clean live N≥30 到達の前日 ≒ 10-25)。

## 1. なぜ今日か

- carry_dip の clean live closed N は 27/30 (10-19 09:3xZ、monitor 実走)、直近 30d 13 fill の線形外挿で **N≥30 到達 ETA 2026-10-26**。packet §8-0 の見積り 11-09 より 2 週早い。
- pre-reg 規律「N≥30 到達後の基準選択禁止」のため、到達前に **両基準が同じ母集団で読める状態**が要る。片方 (demo) しか読めない状態で到達すると、broker 基準は事後に「選ぶ」形になる。

## 2. データ経路

| 層 | 実装 | 備考 |
|---|---|---|
| broker 一次 | OANDA v20 `GET /v3/accounts/{id}/trades?state=CLOSED&count=500&beforeID=` | closed trade object: `price` (open avg) / `averageClosePrice` / `initialUnits` / `realizedPL` / `financing` / `closeTime` |
| 本番 proxy | `GET /api/oanda/trades_remote?state=CLOSED&count=500[&before_id=N][&instrument=]` (`app.py`、read-only、count≤500) | 既存 `/api/oanda/trades` はローカル同期表 `oanda_trades` を読むが **2026-09-24T04:37:02Z で同期停止** (最大 trade id 893189) — 10 月 fill を 1 件も返さないため新設 |
| 読み手 | `tools/m1_clean_live_monitor.py --strong` (既定で broker 列を取得、`--no-broker` で抑止) | `needed_broker_ids` = demo 側 clean live 母集団 (cutoff 2026-04-08〜anchor) の `oanda_trade_id` 集合 (10-19 実測 614 件)。`beforeID` 遡行で最古必要 id まで被覆 (≈2 ページ) |

## 3. 定義 (基準は選ばない)

- **broker pips** = `(averageClosePrice − price) × sign(initialUnits) / pip_size`、pip_size = 0.01 (JPY quote) / 0.0001 (他)。価格由来なので spread/slippage を内包し、demo の bid/ask 建て `pnl_pips` と直接比較可。
- **broker PnL** = `realizedPL` (口座通貨 JPY、Claude_auto_trade_KG)。`financing` は別掲 (`net_jpy = pl + financing`)。REG F3 字義「PnL>0」を broker で読むときは **realizedPL 合計 > 0**。
- **predicate 2 つ × 基準 2 つ** を同一セル集合 (entry_type×instrument×direction、clean live 累積) で評価:
  - REG 字義: `N≥30 ∧ ΣPnL>0` (`project-falsification-f3-m1-durable-cell` condition)
  - STRONG: `N≥30 ∧ EV≥+1.0p/t ∧ Wilson95下限(WR)>0` (2026-09-10 user 指示の実装主定義)
- 母集団は demo 側と**同一** (`cumulative_cell_stats` と同じ filter)。broker 側に無い行は `n_unmatched` に積み、**0 で埋めない**。1 本でも欠けたセルの broker predicate は `unavailable` (真でも偽でもない、不一致にも数えない)。
- 取得失敗 (HTTP 非 200 / 被覆未達 / ページ上限) は `broker_basis.status = "unavailable"` + 理由。markdown は「0 として読まないこと」を明記。

## 4. 出力 (JSON `strong.broker_basis` / markdown)

- `broker_basis.table.counts` = `{reg_literal_demo, strong_demo, reg_literal_broker, strong_broker, broker_unavailable_cells}`
- `broker_basis.table.disagreements` = 2 基準で predicate が割れたセル (両方評価できた場合のみ)
- `strong.n_cells_reg_literal_demo` を新設 — 既存 `n_cells_rederivation_literal` は Wilson_lo>0 を含む旧定義で、REG 字義 (PnL>0 のみ) とは別物 (09-24 検証で判明)。両方残す。
- markdown 1 行: `両基準 (D11): REG字義 demo=k / broker=k | STRONG demo=k / broker=k | 不一致セル=m`。unavailable 時は ⚠️ 行。

## 5. 検証

- 単体 15 本 (`tests/test_m1_broker_basis.py`): pips 符号・刻み (long/short/JPY/非 JPY)、OPEN/欠損/units 0 → None、未突合は n_unmatched (0 埋め禁止)、母集団同一性、predicate 境界 N=29/30、基準間不一致を選ばず両記、incomplete → unavailable、pagination 停止条件、失敗 = unavailable、skipped/unavailable/ok の markdown。
- route 4 本 (`tests/test_api_oanda_trades_remote_endpoint.py`): 既定 CLOSED/500、before_id/count/instrument の転送、不正値 400 (broker 未呼出)、上流失敗 500 (0 件と偽らない)。
- **counterfactual pin 3 本** (pycache purge 後に実施): REG 字義を `N≥29` に崩す → 1 fail / 未突合を pl=0 で埋める → 2 fail / route が before_id を落とす → 1 fail。
- 本番実走 (proxy 未デプロイ時): `broker_basis.status = unavailable (HTTP 404)`, covered 0 / missing 614、demo 側 verdict (NOT_MET N=27 −15.2p) は不変 = fail-loud 経路の実証。

## 6. 限界・次

- 口座通貨 JPY 前提 (`BROKER_ACCOUNT_CCY`)。口座を替えたら realizedPL の通貨も変わる。
- demo 行に units が無いため、broker 側 `initialUnits` を units の一次ソースとする (1000u 前提の M3b 推定とは独立)。
- `financing` は predicate に含めない (REG 字義 PnL = realizedPL)。kalman R2 の「broker realized net」estimand が financing 込みを要求するなら D7 決裁時に明示する。
- 読み手 cron (`quant_gate_status --strong`、00:20Z) は markdown pass-through で自動的に両基準行を出す。デプロイ直後の初回は proxy 到達を確認する。
- 6 日後 (10-25) までに user が D11 を返さなければ REG 字義 (demo 簿) が既定 predicate として凍結される (registry の既定挙動、本稿は変更しない)。

関連: [[integrated-decision-packet-d1-d12-2026-09-22]] D11 行 / [[carry-dip-broker-reconcile-2026-09-22]] (手動 14/14 突合の前例、本稿はその tool 化) / MEMORY `project_f4_nav_floor_transfer_funds_adjust_2026_09_23` (同型の fail-loud 規律)
