# trendline_sweep Pine replica → TV Strategy Tester 検証 — 2026-05-14

## 目的
`bt-results/tv-overlays/trendline_sweep-replica.pine` は Python BT (`strategies/daytrade/trendline_sweep.py`) を **完全再現**した Pine v5 strategy。TV Strategy Tester で全期間バックテストし、KB claim (EUR/USD EV=+0.927 WR=80.8%, GBP/USD EV=+0.599 WR=73.1%) を head-to-head 検証する。

## 手順
1. `tv_health_check` → CDP 接続確認 (OK)
2. `tab_new` → **tab_count が 1 のまま** (修理は未完了。後述「regression」)
3. 既存タブで進行: `chart_set_symbol` → `chart_set_timeframe(15)`
4. `pine_new(strategy)` → `pine_set_source(replica)` → `pine_smart_compile`
5. `ui_open_panel("strategy-tester", "open")` → `capture_screenshot(region="strategy_tester")`
6. EUR/USD 検証後、`chart_set_symbol("GBPUSD")` + `sell_only` デフォルト false に書き換え再 compile → GBP/USD 検証

## バックテスト範囲
- TF: 15m
- 期間: **2025-07-01 〜 2026-05-14**（約 318 日、TV Deep Backtest 自動選定）
- 初期資本: $10,000 / qty=10% equity / commission=0.014% / process_orders_on_close=true

## 結果

| Pair    | Direction | TV N | TV WR    | TV PF | TV NetP    | TV MaxDD | KB claim (EV / WR) | 乖離 (WR) |
|---------|-----------|-----:|---------:|------:|-----------:|---------:|-------------------:|----------:|
| EUR/USD | SELL-only | 184  | **43.48%** | 1.021 | +$5.34 (+0.04%) | 0.38% | EV=+0.927 / WR=**80.8%** | **−37.3pp** |
| GBP/USD | BUY+SELL  | 243  | **41.56%** | **0.895** | **−$32.48 (−0.32%)** | 0.59% | EV=+0.599 / WR=**73.1%** | **−31.5pp** |

- 両ペア共に **TV Strategy Tester は KB claim と整合せず**、break-even / 損失レンジ
- GBP/USD は **PF < 1.0 / NetP < 0** の純粋な負け戦略
- KB の trendline_sweep は ELITE_LIVE 指定（`wiki/index.md` 参照）だが、TV ベースでは正の期待値を再現できない

## 分析: なぜ Python BT と TV がここまで乖離するか

直近 2 ケースと同じパターンが再発:
- `bb_rsi_1m_mtf` 検証 (`bb-rsi-1m-mtf-variant-audit-2026-05-14.md`) — TV で BT を再現できず
- `xs_momentum` 検証 (`xs_momentum-tv-phase1.md`) — TV で BT 主張 EV を再現できず
- **今回 `trendline_sweep`** — 3 例目

3 戦略連続で「Python BT > TV」の方向に乖離する偶然は考えづらい。仮説:

1. **Pine 再現の構造差** — replica は本番ロジックを忠実に写しているつもりだが、ATR 計算 (`ta.atr` vs Python の `atr_series`) や pivot 検出 (`ta.pivothigh` の confirmation lag) で 1〜数 bar の差が出ている可能性
2. **データ feed の差** — Python BT は OANDA / massive-parquet, TV は `OANDA:EURUSD` feed。15m bar 境界は揃っているが、tick aggregation の違いで pivot/sweep の判定が変わり得る
3. **Python BT の look-ahead / fill 仮定** — 本番コードに「同 bar 内 SL/TP 同時 hit 時に TP 優先」など TV と異なる扱いがあれば、Python 側が systematically 楽観的になる
4. **過去 BT を作った時の cutoff / pair × 戦略 universe 選択 bias** — 80.8% WR は cell-level cherrypick の結果かもしれない

## 結論 (Asymmetric Agility Rule 2: 損失停止 / Shadow降格 は即断可)

**KB の trendline_sweep ELITE_LIVE タグは保留すべき。**

- Live は本物 (memory `feedback_tv_edge_discovery_loop`: "Live > TV > Python BT") なので、Live PnL が +EV を保っている限り即停止はしない
- 但し以下を実施:
  - **次セッションで Live N と PnL の最新状態を確認** (analyst エージェント経由 / `bt-results/audits/`)
  - Live でも負けに転じていれば **shadow 降格 + KB ELITE_LIVE タグ撤去**
  - Live がまだ +EV なら、なぜ TV/Python BT と Live がここまで違うかを 3 軸 (Live / TV / BT) で 1 戦略まとめて分析 (`xs_momentum-tv-phase1.md` の続編フォーマット)

## サイドファインディング: TV MCP の regression

### 1. `tab_new` が tab_count を増やさない
- `tab_new` 呼び出し → `{"success": true, "action": "new_tab_opened", "created_via_cdp": false, "tab_count": 1}`
- 後続 `tab_list` でも tab_count=1 のまま
- `created_via_cdp: false` から、CDP 直接生成に失敗してフォールバック経路を走ったが結果反映なし
- ワークアラウンド: 既存タブで完結（今回採用）

### 2. `data_get_strategy_results` が常に空
- Strategy Tester に **184 trades / 80 wins / PF=1.021** が描画済みでも `metric_count: 0`
- すべてのケースで `metrics: {}` を返す
- 視覚 OK / API NG → スクリーンショット読みが唯一の信頼経路
- ワークアラウンド: `capture_screenshot(region="strategy_tester")` + Read tool で目視

### 3. `indicator_set_inputs` がキー検出に失敗
- entity_id "P5DaTK" は valid だが `{"sell_only": false}` も `{"SELL-only (...)": false}` も `updated_inputs: {}` を返す
- ワークアラウンド: Pine source の `input.bool(true,...)` を `input.bool(false,...)` に書き換えて再 compile

### 4. Pine v5 short-circuit 信頼性
- `while array.size(arr) > 0 and array.get(arr, 0) < x` が bar 0 で `array.get` index OOB を起こす
- 静的解析 `pine_analyze` は通すが、runtime で短絡してくれない
- 修正済み (replica.pine): `while size > 0 / if get(0) >= x then break` の 2 段構造に書き換え

3 件いずれも tradingview-mcp 側の課題。再現性高くスクリーンショット中心の workflow になっているので、`tools/tv_overlay_gen.py` や本検証フローへの優先度高い fix としてバックログに残す。

## 関連
- `bt-results/tv-overlays/trendline_sweep-replica.pine` — 本検証で使った Pine source
- `wiki/analyses/tv-bt-overlay-verification-2026-05-13.md` — overlay 方式の汎用ガイド (先行)
- `wiki/analyses/bb-rsi-1m-mtf-variant-audit-2026-05-14.md` — 同セッションの並行検証
- `wiki/analyses/xs_momentum-tv-phase1.md` — 先行 Python BT 乖離事例
- `wiki/strategies/trendline-sweep.md` — 戦略カード（Live 数値で update 予定）
- screenshots: `/Users/jg-n-012/test/tradingview-mcp/screenshots/trendline_sweep_eurusd_15m_st_v2.png`, `trendline_sweep_gbpusd_15m_st.png`
