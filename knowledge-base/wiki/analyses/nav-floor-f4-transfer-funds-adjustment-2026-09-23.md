---
title: F4 資金時計 edge 残差の入出金 (TRANSFER_FUNDS) 調整 — 2026-09-23
type: analysis
rule: R3
status: implemented
related:
  - "[[nav-floor-f4-estimator-decomposition-2026-09-22]]"
  - "[[path-to-win-reassessment-2026-09-22]]"
  - "[[integrated-decision-packet-d1-d12-2026-09-22]]"
  - "[[prereg-trigger-registry]]"
---

# F4 資金時計 edge 残差の入出金 (TRANSFER_FUNDS) 調整

**Rule 3 (構造欠陥、code derivation)** — 検知器の estimand 是正。registry F4 (`project-falsification-f4-nav-floor-clock`) の condition (`days_to_floor <= 90`) は不変。live 経路には触らない (monitoring + read-only route)。

## 1. 欠陥 (何が壊れていたか)

[[nav-floor-f4-estimator-decomposition-2026-09-22]] §2 の edge 成分は broker NAV Δ の**残差**で定義されていた:

```
edge_jpy  = (NAV_now − NAV_start) + keeper_rt_in_window × JPY_PER_RT
burn_edge = −edge_jpy / span
```

NAV Δ には入出金 (OANDA v20 tx type `TRANSFER_FUNDS`、amount: +入金 / −出金) が丸ごと乗るが、その調整が repo 全体で **0 件**だった (`grep TRANSFER_FUNDS / 入出金` in `modules/ tools/ app.py`、2026-09-23「バジェット増やせばいけるか」17 エージェント反証の完全性批評で発見)。

導出: 窓内に入金 D があると

```
burn_edge' = burn_edge − D / span
D = ¥100,000, span = 30d → −3,333 JPY/日  ≫  keeper 68.3 JPY/日
⇒ burn_total = keeper + burn_edge' < 0 ⇒ project() が DAYS_SENTINEL_NO_BURN (99999)
⇒ F4 (days_to_floor ≤ 90) は窓の間 (最長 EDGE_WINDOW_DAYS = 30 日) 発火不能
```

窓を抜けると start_row が入金後の行に切り替わり Δ から D が消えるので burn は真値へ戻る = **逆方向に跳ねる**。対称側: 出金 W は burn を +W/span 押し上げ、F4 を**偽早期発火**させる (¥50,000/30d ≈ +1,667/日)。

同じ根の警告は既に M2 会計側にあった — [[path-to-win-reassessment-2026-09-22]] §9-5「定義 A (入出金調整後 broker NAV Δ) の読み手は不在」/ [[integrated-decision-packet-d1-d12-2026-09-22]] D1「生の NAV Δ を読むと D3 (i) の入金が翌 30 日に +19.6〜82% の『リターン』となり M2 を虚偽達成する」。F4 の読み手 (`tools/nav_floor_projection.py`) は同じ生 NAV Δ を読んでいたのに、資金時計側では未調整だった。U3 (D3 (i) 入金) が決裁されるまさにその時に F4 が盲目化する構造。

## 2. 修正 (code derivation)

```
edge_jpy  = (NAV_now − NAV_start) − Σ transfers(window) + keeper_rt_in_window × JPY_PER_RT
burn_edge = −edge_jpy / span                                  (不変)

window    = (t_start, t_now]      t = NAV 採取時刻 (heartbeat.last_check)
  tx ∈ window ⇔ t_start < tx.time ≤ t_now       TRANSFER_FUNDS のみ数える
                                                (TRANSFER_FUNDS_REJECT は残高を動かさない /
                                                 約定・DAILY_FINANCING は trade 由来 = edge 側)
  t_start   = start_row.nav_ts_utc (新列)。無い legacy 行 (2026-09-23 以前) は日付で切り、
              tx.date == start_date なら前後不定 → unavailable:transfer_on_start_bound
  t_now     = nav_ts (heartbeat.last_check、無ければ取得時刻)。tests のように date しか無い
              場合は tx.date == asof で unavailable:transfer_on_asof_bound (両端対称)
  amount / time が読めない TRANSFER_FUNDS → unavailable:transfers_malformed

台帳       = 本番 GET /api/oanda/transfers?from=YYYY-MM-DD&to=YYYY-MM-DD (app.py、read-only)
             ← OandaClient.list_transactions_full(from, to, types=["TRANSFER_FUNDS"])
                = TransactionList の pages を idrange で辿って tx 本体を連結 (0 ページ = 空で成功、
                  どの hop の失敗も (False, err) — 部分結果を成功と偽らない)
             tool 側の取得窓は日付で [asof − 32d, asof + 1d)、窓判定は上の時刻で行う
台帳 None  (route 未デプロイ 404 / OANDA 失敗 / 形式不正) → unavailable:transfers_unavailable
             keeper 分は残る (method=decomposed のまま)。「入出金ゼロ」と偽らない
basis      = nav_delta:<start>-><asof>:<span>d,keeper_rt_in_window=<n>,transfers_jpy=±<X>,n_transfers=<k>
             — CSV の edge_basis 列から入出金の有無が毎日見える
```

**不変量 (pin する性質)**: 台帳を差し引いた burn_edge は入出金に対して不変 — ∂burn_edge/∂D = 0。入金が窓に入る日も窓を抜ける日も burn = drift のまま (跳ねない)。

設計原則:
- **入出金は edge に不可視** — 資金時計の estimand は「口座が自力で減る速さ」であり、user の入金は分母 (NAV) を動かすが burn を動かさない。project() は伸びた NAV を正しい burn で割る (days_to_floor は増える = 正しい)。
- **窓端は時刻** — 日付で切ると nav_start の採取前後に同日入出金が載った場合に ±D/span の誤差が丸ごと出る (入金なら偽の burn 5,000/日級 → 偽発火、逆なら盲目化)。どちらの方向も許容できないので、時刻の無い端に同日 tx が載れば fail-closed。新列 `nav_ts_utc` で今後の行は時刻を持つ。
- **取得不能を 0 と折り畳まない** (monitoring-blind 教訓) — 09-23 時点で本番 route は未デプロイ (HTTP 404) → dry-run は `WARN: 入出金台帳 (TRANSFER_FUNDS) 取得不能 — edge は unavailable:transfers_unavailable として記録` を出し、行の burn は keeper のみ (68.3/日、days_to_floor 197、09-23 実測 dry-run)。edge_basis は先行する理由 (`keeper_split_unknown(span=16d)`、CSV が当月内から始まる窓) が優先表示される — 理由は 1 つだけ書く設計、transfers の判定は keeper 側が確定した後。
- **対称に処置** — 入金/出金、start 端/asof 端、REJECT/本体、それぞれ両側を同じ関数で同じ規則にした ([[feedback_check_the_symmetric_side_2026_09_19]] の教訓: 片側だけ塞いだ fail-closed は「再発できない」を偽にする)。

## 3. pin (tests/test_nav_floor_projection_f4.py §14) と counterfactual

| テスト | 性質 | 既知 NG 入力 |
|---|---|---|
| `test_deposit_inside_window_is_invisible_to_edge_burn` | 入金 ¥100,000 (10-10) を台帳で差し引くと burn = 台帳なし・入金なしの値 (drift 10/日) と一致、basis に `transfers_jpy=+100000,n_transfers=1` | 台帳を見ない (`transfers=[]` と偽る) と burn < 0 → `project()` が 99999 |
| `test_withdrawal_inside_window_is_invisible_to_edge_burn_symmetric` | 出金 ¥50,000 も不変 | 台帳なしで burn が base の 50 倍超 (偽早期発火) |
| `test_edge_burn_does_not_rebound_when_deposit_leaves_window` | 入金 09-20 が窓内 (asof 10-10) / 窓外 (asof 10-30) のどちらでも burn = drift | 台帳なしの窓内 asof で −3,000/日 未満へ跳ぶ |
| `test_edge_unavailable_when_transfer_ledger_missing_not_silent_zero` | `transfers=None` (既定含む) → `unavailable:transfers_unavailable`、decomposed は keeper のみ (>0) | — |
| `test_transfer_ledger_ignores_non_transfer_types_and_flags_malformed` | REJECT / DAILY_FINANCING は不算入、amount・time 不正は `transfers_malformed` | — |
| `test_transfer_window_bounds_use_nav_timestamps_and_fail_closed_on_legacy_boundary` | legacy start 端の同日 tx → `transfer_on_start_bound`、`nav_ts_utc` があれば 02:00Z (採取前) は除外・08:00Z (採取後) は差し引き、asof 端も対称 | — |
| `test_append_row_persists_nav_timestamp_for_future_window_bounds` | 新列 `nav_ts_utc`、既存 6 列不変 | — |
| `test_main_fetches_transfer_ledger_over_window_and_exposes_unavailable` | main が窓を覆う範囲で台帳を取り、None をそのまま渡す、nav_ts = heartbeat.last_check | — |
| `test_fetch_transfers_returns_none_on_failure_or_bad_scheme` | scheme 遮断 / 例外 / transactions 配列なし → None | — |
| `test_transfers_reader_wiring_tool_path_matches_app_route` | tool の path 定数と app.py の route が一致 (write-only 教訓) | — |
| `test_registry_f4_message_records_transfer_funds_adjustment` | registry F4 message に方法変更、condition 不変 | — |
| `tests/test_oanda_client_transactions_full.py` (3 本) | ページ走査・空窓成功・部分結果を成功と偽らない | — |
| `tests/test_api_oanda_transfers_endpoint.py` (5 本) | type フィルタ・RFC3339 窓・400 (不正/逆転/400 日超)・to を今で clamp・500・503 | — |

既存テストは `transfers=[]` (台帳を参照して入出金ゼロ) を明示する形に改めた — 省略 = 未参照 = unavailable に意味が変わったため。09-22 の発火日再現値 (`_simulate_first_fire`: keeper のみ 2027-01-05 / drift 13.7 で 2026-12-04) は入出金ゼロ前提で不変。

**counterfactual (pycache purge `Library/Caches/com.apple.python/...` を毎回挟む、[[feedback_pycache_prefix_stale_bytecode_verification]])**:
- CF1 `edge_jpy` から `− transfer_jpy` を外す → §14 の 4 本 (deposit / withdrawal / rebound / bounds) が落ちる、28 本 pass
- CF2 `transfers is None` を `transfers or []` (ゼロ扱い) にする → `..._ledger_missing_not_silent_zero` が落ちる、31 本 pass
- restore 後 sha256 一致 (`8859bf048b5740e2…`)、40/40 green。全 suite 3,924 passed / 17 skipped / 1 xfailed、`scripts/check.py` 全 10 チェック通過

## 4. 現況と移行

- **本番 route は本 PR のマージ → Render auto-deploy 後に生きる**。それまで (および deploy 失敗時) の cron run は `transfers_unavailable` で keeper のみ — 現状 (09-22/23 の行) と同じ値で、悪化はしない。
- **legacy 行 (09-07〜09-23、`nav_ts_utc` 空) が start_row の間** (窓 30 日 → 10 月下旬まで) は、その start 日に入出金が載れば unavailable。入出金が無ければ従来通り測れる。U3 入金 (D3 (i)、期限 11-30) はこの移行期の後。
- 本 CSV の estimand は burn (F4) で M2 判定器ではない。定義 A (入出金調整後 broker NAV 30d Δ、packet D1) の 30d **読み手**は台帳 route + `transfers_in_window` で初めて組めるようになったが、それ自体は別 R3 (M2 会計の読み手は `tools/m1_clean_live_monitor.py` 系)。
- registry F4 message に方法変更を追記 (condition 不変)。

## 5. 残る限界 (caveat)

- 窓端の時刻は `heartbeat.last_check` (bridge の 60s heartbeat)。heartbeat が止まっている間の入出金は「nav_now 未反映」として正しく除外されるが、NAV 自体が古いのは別問題 (freshness は watcher 側の責務)。
- `TRANSFER_FUNDS` 以外の非トレード残高変動 (手数料・調整系の ADMIN tx) は未調整。本口座での有無は**未確認** — 出たら route の type を足す (同型の兄弟を同じ PR で掃く教訓、[[project_mof_ingest_defect_family_2026_09_17]])。
- OANDA `to` は route 側で「今」に clamp。tool の取得窓は日付 [asof−32d, asof+1d) で、窓判定は時刻。TransactionList の pageSize 1000 で 1 ページに収まる想定 (入出金は月に数件)。
- `nav_ts_utc` は 12 列目 (registry `csv_row_match` が読む先頭 6 列は不変)。

## 6. 変更点

| ファイル | 変更 |
|---|---|
| `tools/nav_floor_projection.py` | `transfers_in_window` / `fetch_transfers` / `nav_ts_from_status` / `_parse_ts` 追加、`edge_burn_per_day` に `transfers` / `nav_ts` (None = unavailable)、basis に `transfers_jpy,n_transfers`、新列 `nav_ts_utc`、`main()` が台帳を窓分取得し None は WARN + そのまま渡す |
| `modules/oanda_client.py` | `list_transactions_full(from, to, types)` — pages → idrange 走査 (失敗は部分結果を返さない) |
| `app.py` | `GET /api/oanda/transfers?from&to` (read-only、400 日上限、to を今で clamp、TRANSFER_FUNDS のみ、503/500 で 0 件と偽らない) |
| `tests/test_nav_floor_projection_f4.py` §14 / `tests/test_oanda_client_transactions_full.py` / `tests/test_api_oanda_transfers_endpoint.py` | 上記 pin (11 + 3 + 5 本)、既存呼び出しは `transfers=[]` 明示 |
| `prereg-trigger-registry.json` | F4 message 追記 (1 行、condition 不変) |
| `nav-floor-f4-estimator-decomposition-2026-09-22.md` §5 | 本ページへの追記 1 行 |

## 7. レビュー消化記録

PR 作成後、connector レビュー (P1/P2) の消化をここに追記する (`tools/pr_review_gate.py` で到着 + 消化を確認してからマージ)。
