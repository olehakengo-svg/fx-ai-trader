# E21 human_signal_stream — S2 標本量実測と disposition (2026-08-17)

**位置づけ**: [[external-hypothesis-scan-round3-2026-08-14]] §2.2 で採用された **E21 (user 手動トレード
実績の帰属分解、S2 診断枠)** の最初の測定項目「標本量の実測」の執行。**読み取り専用 — 分解統計は
一切計算していない** (母集団の所在確定が先)。台帳 **#23** 登録。live/tier/lot 変更なし。

## 方法

- OANDA transaction API (`list_transactions` / `get_transactions_id_range`、bot 口座) +
  本番 `/api/demo/trades` の `oanda_trade_id` 集合との突合で fill を bot / manual に分類
  (bot は clientExtensions を使っていないため、照合が唯一の判別法 —
  `tools/transactions_shadow_drift_audit.py` と同じ照合原理)
- 口座 ID・個人データは非出力 (集計値のみ)

## 実測結果 (bot 口座 Claude_auto_trade_KG)

| 項目 | 値 |
|---|---|
| 口座開設 | **2026-04-02** (earliest tx CREATE) |
| ORDER_FILL 総数 | 1,862 (bot 1,782 / **manual 80** / ambiguous 0) |
| manual 内訳 | USD_JPY 36 / GBP_USD 42 / EUR_USD 2、units 10k×66・30k×14 |
| manual 期間 | 2026-04-09 → **2026-07-13** (以後ゼロ)、opens 40 = closes 40 (**全決済済み**) |
| 現在の未決済 | **0** (openTrades 空) |
| DAILY_FINANCING | 7 イベントのみ、**manual トレード接触 0 日** |
| manual 実現 PL | **−6,821 JPY** (USD_JPY −620 / GBP_USD −6,089 / EUR_USD −112)、**全て分単位保有** (並行監査実測) |

## 並行セッション監査との照合 (2026-08-17 同日)

本 S2 と独立に、並行セッションの OANDA 全 transaction 監査 (MEMORY
`user_manual_edge_usdjpy_carry_2026_08_12` 追記) が同一結論に到達している — 突合:
- 真の手動 = **40 往復** (両者一致)、financing ゼロ (一致)、勝ち玉は別口座 (一致)
- 先方の追加所見: 手動 40 往復の実現 PnL = **−6,821 円** (全て分単位保有)、
  30000u×7 の約定日訂正 (07-10/07-13、「07-29」は確認日)、および**教訓 = 手動判定 join は
  本番 trades の全期間走査 (date_from/date_to、17,527 行) による oanda_trade_id 全集合 (934) で
  行うこと — 直近 5,000 行だけの join は 1,674 fills を誤分類する** (04-02 のシステム初期
  rapid-fire を含むため)。本 S2 の join も全量取得で id 集合 934 が一致しており誤分類なし
  (bot 1,782 / manual 80 / ambiguous 0 の完全分割)

## 判定 (S2 の結論)

1. **bot 口座内の手動取引は「長期キャリー」の母集団ではない** — 全決済済み・financing 接触 0 日 =
   短期ホールドの 40 往復。user 明言 (2026-08-12)「優位の正体は USD_JPY 長期キャリー」の実績は
   **この口座に存在しない**
2. **30000u×7 の実約定は 2026-07-10 (1 件) + 07-13 (6 件) の分単位スキャル** — 本 S2 の manual
   集合 (30k×14 fills) に含まれる。MEMORY 従来記載の「07-29」は**確認日であって約定日ではない**
   (並行監査が特定・MEMORY 訂正済み)。「user 本人の手動発注・漏洩なし」判定自体は不変
3. **トークンは個人口座 (CFD タグ、ID 非記載) を視認可能** — ただし当該口座への読み取りアクセスは
   **permission classifier がブロック**した。回避は行わない。**E21 の主 estimand
   (キャリー帰属分解) の実行可否は user 決裁点**

## user 決裁点 (E21 の続行形態)

E21 の主 estimand (arXiv 2302.01010 の 4 分解: financing/swap 累計 × spot ドリフト β ×
タイミング α × サイズ寄与、会計恒等式・探索自由度ほぼゼロ) には個人口座の取引台帳が必要。選択肢:

- **(a) 読み取り許可** — Bash allow ルール等で個人口座の transaction API 読み取りを許可
  (読み取り専用・集計出力のみ・口座 ID 非出力の運用は本 S2 と同一)
- **(b) user による export 提供** — OANDA の取引履歴 CSV export を `data/external/e21/` に配置
  (API アクセス不要になる)
- **(c) carry 成分を data-blocked クローズ** — bot 口座内 40 往復 (短期・swap≈0) のみの
  タイミング α 分解は実行可能だが、**キャリー主張の検証にはならない**ことを前置した縮小版

いずれの場合も分解は観測前に手続きを凍結してから実行する (scan §2.2 のスコープ制限
— WR/N≥30 統計ではない・供給ラインとして数えない・M2/M3 主経路ではない — を複写)。

## 監視

registry `e21-personal-account-decision` (deadline 2026-08-31) — 決裁が 2 週間出ない場合に再浮上。
