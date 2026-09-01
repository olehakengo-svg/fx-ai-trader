# Status Volume Keeper — OANDA API 存続のための出来高維持 (2026-09-01, rule:R3)

**user 決裁: 2026-09-01 案 A (自動 keeper 実装) を選択。arm (env 有効化 = 初回実弾発注) は別途 user 最終確認後。**

## 問題 (存続条件)
- OANDA JP REST API の利用条件 = **Gold ステータス + プロコース + 口座残高 25 万円以上**を「利用している間ずっと」充足 (FAQ 720)。割れると **API 停止 + トークン再発行** (FAQ 1730) = live 執行・E1 order book 収集・テレメトリの物理停止 (価格は Massive/yfinance fallback で shadow のみ劣化継続)
- Gold = **前月取引量 USD 50 万** (新規+決済の双方でカウント)。毎営業日判定、昇格は翌月末まで維持
- 2026-09-01 時点: 現在 PLATINUM (9 月末まで) / **10 月 SILVER 降格見込み** (8 月出来高 ≈ $28k) / 9 月出来高 $0
- エッジトレードは MIN lot 契約 (1000u) 下で月 ~$28k、有機レバー全部でも $82-106k = **構造的に $500k に届かない**
- 分析: [[live-frequency-and-oanda-status-survival-2026-09-01]]

## 設計 (modules/status_volume_keeper.py)
USD_JPY 10,000 通貨の市場即時往復 (数秒保有、SL/TP なし) を月 ~26 回、東京流動時間帯 (UTC 0-5) に実行して月間 $520k (バッファ込み) を積む。**これはエッジ主張ではない — API 利用料をスプレッドで払う運用コスト** (見積 月 ¥1,000-4,000)。

### ガード (全て code 固定)
| ガード | 値 | 根拠 |
|---|---|---|
| env キルスイッチ | `STATUS_VOLUME_KEEPER_ENABLE` **default OFF** | arm は user 最終確認後 |
| 口座完全フラット要求 | openTradeCount == 0 | エンジン/手動玉との netting 干渉ゼロ。決済は trade_id 指定 close のみ |
| NAV floor | < ¥262,000 で発注停止 | API のもう 1 つの存続条件 (残高 25 万) を keeper 自身が侵食しない |
| スプレッド | > 1.0p skip | デスゾーン動的検出の原則に整合 |
| サイズ hard cap | 20,000u (default 10,000u) | margin 25x で ¥64k、瞬間エクスポージャ上限 |
| 日次上限 / 間隔 | 3 RT/日、≥1h 間隔 | 集中発注の回避 |
| 月次 target | $520k 到達で自動停止 | 過剰出来高を積まない |
| crash-safe | close 失敗玉は state 永続化 → 次 cycle 回収 | 玉の置き去り防止 |

### データ規律
- **demo DB には一切書かない** — Kelly / agg-Kelly / quant-eval / 鮮度検知 (`last_trade_row` / `live_n_stagnation`) の母集団を汚染しない。keeper が定期約定を作ると停滞検知が無効化されるため、DB 非経由は機能要件
- OANDA 側識別: `tradeClientExtensions.tag = "SVK"` (market_order に clientExtensions サポート追加)。transaction 監査で機械分離可能 (手動 join 誤分類の教訓対応)
- fork-safety §11: thread は before_request heartbeat (`ensure_worker_running`) からのみ起動

### 読み手 (writer と同一コミット)
- `/api/demo/status` に `status_volume_keeper` telemetry (enabled / volume_usd / target / last_skip_reason / behind_pace)
- anomaly_watcher に `nav_floor` (NAV < ¥262k、6h 間隔通知) + `svk_behind_pace` (enabled ∧ ペース 60% 未達 ∧ 10 日以降、24h 間隔) を新設。status 空 run では判定しない (blind ≠ 正常、PR #210 規律)

## arm 手順 (user 最終確認後)
1. Render env `STATUS_VOLUME_KEEPER_ENABLE=1` 設定 (再デプロイ発生)
2. 初回 RT を Render ログ (`[svk] RT done`) と `/api/demo/status`.status_volume_keeper で確認
3. OANDA 取引量画面で反映確認 (翌日 17 時以降)
4. 9 月中の完了目標: **09-24 までに $500k** (反映ラグ数日を吸収)

## rollback
env を 0/unset に戻すのみ (worker 不起動)。玉が残っていた場合も次回 enable 時の回収経路が閉じる。

## 明示的な非目標
- ステータスのための lot 昇格 (lot ladder 凍結テンプレの違反)
- keeper 約定の統計利用 (エッジ情報ゼロ、全 pipeline から除外)
