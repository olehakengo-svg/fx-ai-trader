# carry_dip broker 突合 14/14 + 戦略カード訂正 + velocity_down 照合 (2026-09-22)

**Status**: 記録完了 (rule:R3 — 突合・訂正・観測のみ。lot / tier / 契約 / フィルタの変更なし)
**Scope**: [[usdjpy_carry_dip_accumulator]] の LIVE 全 14 本 (`oanda_trade_id != ''`) について、demo 簿 `pnl_pips` と broker realized (`/api/oanda/transactions` の閉じ ORDER_FILL `pl`) を 1 本ずつ突合し、REG `carry-dip-v3-revival-watch` の事前規定 R2 (deduped LIVE N≥10 ∧ EV<0) を **demo 簿 (凍結 estimand) と broker realized の両基準で**判定する。併せてカード L3 の誤帰属 (`agg_kelly` block / 「08-14 以降」) を訂正し、直近 11 日の fill ゼロを velocity_down ガードと価格キャッシュで照合する。
**入力**: [[path-to-win-reassessment-2026-09-22]] §3 Rank 5 (a)(b)(c) / D5 (user 決裁) の入力。carry_dip は凍結 look ではないため outcome 計算可。
**取得時刻**: 2026-09-22 08:3x–08:5x UTC (全て本番 GET、書込みなし)。

---

## 0. 結論 (TL;DR)

| 問い | 答え | 出所 |
|---|---|---|
| 14/14 突合できたか | **できた**。14 本すべて閉じ ORDER_FILL を tx ID で特定 (§2) | `/api/oanda/transactions?from=&to=` idrange (§1.2) |
| 符号一致 | **13/14**。不一致は **#709598 のみ** (demo +11.6p / broker −¥141 = −14.1p、週末 `MARKET_HALTED` 経由の閉じ = 既知の halted-exit 欠陥) | §2 |
| 合計 | demo **+103.0p** / broker **+¥793 = +79.3p** (¥10/pip @1000u、units は 14/14 で 1000 を実測)。**両方正** | §3 |
| EV/trade | demo **+7.36p** / broker **+¥56.6 = +5.66p** | §3 |
| R2 (N≥10 ∧ EV<0) | **両基準とも不成立** → R2 発火条件は成立しない。停止の autopilot 執行は無い | §4 |
| 「符号逆」 | 14/14 では **成立しない** (09-22 統合 §7-9 の refute を全数で確定)。旧「突合 7 本 −41.1p」は部分集合の値であり、正の寄与は #549260 / #573986 / #681149 / #893161 の 4 本 (broker 計 +¥1,633) が担う | §3 |
| SL 契約 | as-placed SL は **14/14 で 9.8–28.5p** (宣言 150p の 0.065–0.19×)。demo 行の `sl` 列も同じ距離 ⇒ 置換は demo_trader 内 (OANDA 送信前) | §5 |
| TP | broker TP 距離 / demo TP 距離 = **0.841–0.867 (14/14)** = `_QUICK_HARVEST_MULT = 0.85` (`modules/demo_trader.py:10281`、適用 `:7834`) と整合 | §5 |
| カード L3 | `agg_kelly` block 帰属は **誤り** (bypass set 所属 + 台帳 AGG_KELLY 0 件/11d)。「08-14 以降」は **誤り** (初 fill #549260 = 08-05) — 同 PR で訂正 | §6 |
| velocity_down | 09-11T12:00Z 以降の qualifying H1 bar は価格キャッシュ再現で **2 本** (09-11 12:00Z body −56.5p / 09-14 18:00Z −38.3p)、いずれも 20p 閾値を大きく超える下落中 ⇒ velocity_down block と**整合** (断定はしない、§7) | §7 |

---

## 1. データと方法

### 1.1 demo 簿
- `GET /api/demo/trades?limit=10000&date_from=2026-04-01&status=closed` (2026-09-22 08:3x UTC、10,000 行)。`entry_type == 'usdjpy_carry_dip_accumulator' ∧ oanda_trade_id != ''` で **14 行** (`dedup_violation` は 14/14 で 0、`is_shadow` 0)。scratchpad の 2,002 行窓 (`trades.json`、08-18 以降) では 8 行しか見えないため全期間を再取得した。
- 凍結規律 (REG `carry-dip-v3-revival-watch` message / [[t5-restore-eval-and-carrydip-revival-2026-08-10]] L95–104): dedup は `dedup_violation != 1`、勝敗は `close_reason` でなく `outcome` / `pnl_pips`、LIVE と shadow を混ぜない。本稿はこれに従う。

### 1.2 broker realized
- `/api/oanda/trades` (ローカル `oanda_trades` テーブル) は USD_JPY で **2 行** (#549260 / #573986、`synced_at` 2026-08-11 06:44) しか持たず、同期は 08-11 で止まっている ⇒ 14/14 の一次ソースにはならない (記録のみ、修理は別件)。
- 一次ソース = `GET /api/oanda/transactions?from=<int>&to=<int>` (`app.py:14227–14249`、from/to 整数 tx ID、span ≤100)。手順: (i) trade ID = 建玉 open の ORDER_FILL tx ID なので `[id, id+4]` で ON_FILL の `STOP_LOSS_ORDER` / `TAKE_PROFIT_ORDER` を取得、(ii) 閉じ tx は demo `exit_time` を目標に tx ID を時刻で二分探索 (`[mid, mid]` の `time` を比較) し、収束点から +2,000 tx を 100 刻みで走査して `tradesClosed[].tradeID == id` の ORDER_FILL を採る。(iii) #709598 は demo `exit_time` (09-04T21:45Z、意図した週末クローズ) と broker 閉じ (09-06T21:04:58Z、halt 明け) が 47 時間ずれるため二分探索が外れ、カード記載の tx 837943 を直接照会して確定。
- broker realized = 閉じ ORDER_FILL の `pl` (JPY)。`financing` は 14/14 で 0.0000 (日次 financing は別 tx で計上されるため **本 realized は financing を含まない**)。`halfSpreadCost` は 14 本中 12 本が ¥4.0、#893161 ¥12.5、#709598 ¥18.5 (halt 明け)。
- pip 換算: USD_JPY 1000u ⇒ ¥10/pip。units は 14/14 で open `units = 1000` / close `−1000` を実測。

### 1.3 価格キャッシュ (§7)
- `data/cache/massive/USD_JPY_15m.parquet` (gitignored、末尾 2026-09-22T06:00Z、316,781 行)。H1 へ resample (label/closed = left) し、戦略と同じ Wilder RSI(14) (`strategies/hourly/usdjpy_carry_dip_accumulator.py:194–201`、`ewm(alpha=1/14, adjust=False)`) で「RSI_prev ≥ 45 ∧ RSI < 45 ∧ close < 159.5」の qualifying bar を再現。**全 14 fill の直前 closed bar が qualifying bar に 14/14 で一致**した (再現の妥当性 pin)。08-27T15:00Z bar (16:02Z emit、REG `carry-dip-live-to-shadow-drop-cause` で hour block 落ちと確定済み) も再現集合に含まれる。
- Render ログは retention 30 日で 08-23 以前が無いため、fill 時点の `velocity_down(..)_vs_BUY` 行は読めない。§7 は価格キャッシュのみによる照合で、ガードの実測ではない。

---

## 2. 14/14 突合表

demo = `pnl_pips` (凍結 estimand)。broker = 閉じ ORDER_FILL `pl` (JPY) と ¥10/pip 換算。差 = broker − demo (pip)。

| # | trade | broker open (UTC) | broker close (UTC) / close tx | close reason (broker) | demo pnl_pips (outcome / close_reason) | broker pl ¥ | broker pip | 差 | 符号 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | #549260 | 08-05 04:17:52 @157.385 | 08-05 06:32:49 / 573983 | STOP_LOSS_ORDER (trail) | +29.0 (WIN / OANDA_SL_TP) | +291 | +29.1 | +0.1 | ✓ |
| 2 | #573986 | 08-09 22:03:56 @157.842 | 08-10 07:20:34 / 677393 | TAKE_PROFIT_ORDER | +63.7 (WIN / OANDA_SL_TP) | +637 | +63.7 | 0.0 | ✓ |
| 3 | #677396 | 08-12 10:50:10 @159.172 | 08-12 12:10:22 / 677399 | STOP_LOSS_ORDER | −13.3 (LOSS / SL_HIT) | −127 | −12.7 | +0.6 | ✓ |
| 4 | #677402 | 08-14 06:02:16 @159.233 | 08-14 07:45:19 / 677907 | STOP_LOSS_ORDER (trail) | +0.8 (WIN / OANDA_SL_TP) | +8 | +0.8 | 0.0 | ✓ |
| 5 | #677910 | 08-16 23:02:49 @159.150 | 08-17 00:26:43 / 677913 | STOP_LOSS_ORDER | −11.8 (LOSS / SL_HIT) | −116 | −11.6 | +0.2 | ✓ |
| 6 | #677917 | 08-17 06:52:21 @158.979 | 08-17 07:19:28 / 677920 | STOP_LOSS_ORDER | −11.6 (LOSS / SL_HIT) | −119 | −11.9 | −0.3 | ✓ |
| 7 | #677924 | 08-19 01:05:38 @159.489 | 08-19 02:16:05 / 677927 | STOP_LOSS_ORDER | −11.7 (LOSS / SL_HIT) | −118 | −11.8 | −0.1 | ✓ |
| 8 | #677931 | 08-20 07:03:09 @158.401 | 08-20 07:42:30 / 681146 | STOP_LOSS_ORDER (trail) | +0.7 (WIN / OANDA_SL_TP) | +7 | +0.7 | 0.0 | ✓ |
| 9 | #681149 | 08-20 10:19:05 @158.258 | 08-20 13:35:16 / 709522 | STOP_LOSS_ORDER (trail) | +38.2 (WIN / OANDA_SL_TP) | +384 | +38.4 | +0.2 | ✓ |
| 10 | **#709598** | 09-04 17:01:45 @156.122 | **09-06 21:04:58 / 837943** | **MARKET_ORDER_TRADE_CLOSE** (halt 明け) | **+11.6 (WIN / WEEKEND_CLOSE)** | **−141** | **−14.1** | **−25.7** | **✗** |
| 11 | #837947 | 09-06 22:03:39 @156.274 | 09-07 00:23:00 / 837950 | STOP_LOSS_ORDER | −24.8 (LOSS / SL_HIT) | −246 | −24.6 | +0.2 | ✓ |
| 12 | #837978 | 09-08 10:02:11 @153.961 | 09-08 12:27:24 / 847563 | STOP_LOSS_ORDER (BE trail) | +0.5 (BREAKEVEN / OANDA_SL_TP) | +5 | +0.5 | 0.0 | ✓ |
| 13 | #847578 | 09-09 23:28:13 @153.383 | 09-10 02:01:28 / 859453 | STOP_LOSS_ORDER (BE trail) | +0.6 (WIN / OANDA_SL_TP) | +7 | +0.7 | +0.1 | ✓ |
| 14 | #893161 | 09-11 11:02:36 @153.927 | 09-11 12:30:04 / 893170 | STOP_LOSS_ORDER (trail 自己約定) | +31.1 (WIN / OANDA_SL_TP) | +321 | +32.1 | +1.0 | ✓ |

- 突合不能 0 本。#709598 の閉じは二分探索では見つからず (demo `exit_time` と broker 閉じの 47h ずれ)、tx 837943 の直接照会で確定 (§1.2 (iii))。
- 差の分布 (#709598 除く 13 本): |差| ≤ 0.3p が 11 本、+0.6p (#677396)、+1.0p (#893161)。spread スケール内。
- カード「確認済み OANDA fill 11 本 (#677402〜)」に無かった 3 本 (#549260 / #573986 / #677396) も broker tx で fill・閉じとも実在を確認。

## 3. 集計 (両基準)

| 基準 | N | 正 / 負 / scratch | 合計 | EV/trade | 備考 |
|---|---|---|---|---|---|
| demo 簿 `pnl_pips` (凍結 estimand) | 14 | 8W / 5L / 1BE (`outcome` 列) | **+103.0p** | **+7.36p** | カード上表と一致 |
| broker realized `pl` | 14 | 8 正 / 6 負 (符号) | **+¥793 = +79.3p** | **+¥56.6 = +5.66p** | financing 含まず |
| broker、\|pl\| ≤ ¥10 を scratch 扱い | 14 | 4 正 / 6 負 / 4 scratch (#677402 / #677931 / #837978 / #847578) | 同上 | 同上 | decided WR 4/10 = 40% |

- **両基準とも合計・EV は正**。旧記述「demo +103.0 / broker −41.1 で符号逆」は、broker 側が **突合済み 7 本の部分集合**だったことによる (09-22 統合 §7-9 で refute 済み、本稿で 14/14 確定)。
- broker 正値の内訳: #573986 +637 / #681149 +384 / #893161 +321 / #549260 +291 = **+¥1,633** が 4 本で、残 10 本の合計は **−¥840**。うち #893161 は trail の単調性違反による自己約定 (カード 09-14 節)、#549260 / #681149 / #677402 / #677931 / #837978 / #847578 も閉じ理由は `STOP_LOSS_ORDER` (trail 後の SL) で、**TAKE_PROFIT で閉じたのは #573986 の 1 本のみ (それも as-placed 63.5p で、宣言 80p の TP ではない)**。
- broker 基準の 30d (09-22 起点、08-23 以降): #709598 / #837947 / #837978 / #847578 / #893161 の 5 本 = −141 −246 +5 +7 +321 = **−¥54 = −5.4p** (demo 同 5 本 = +11.6 −24.8 +0.5 +0.6 +31.1 = **+19.0p**)。30d 窓だけを見ると符号が割れるが N=5 で判定対象外。

## 4. R2 判定 (REG `carry-dip-v3-revival-watch`)

- 凍結条件: deduped LIVE N≥10 ∧ EV<0 → lot↓ or LIVE 停止 (shadow 継続)。estimand = demo 簿 `outcome` / `pnl_pips`。
- **demo 簿**: N=14 ≥ 10、EV **+7.36p > 0** ⇒ 不成立。
- **broker realized**: N=14 ≥ 10、EV **+¥56.6 > 0** ⇒ 不成立。
- ⇒ **R2 発火条件は成立しない** (両方負のときのみ「成立」と書く規律に対し、両方正)。停止・lot↓ の autopilot 執行は行わない。単一トレード損失 ≤ −150p は 0 件 (最大損失 #837947 −¥246 = −24.6p) でテールキャップ R3 監査条件も未到達。
- 乖離記録: 30d 窓 (N=5) では demo +19.0p / broker −5.4p と符号が割れる (§3)。#709598 の halted-exit 25.7p 反転 1 本で説明される。N<10 で判定対象外だが、次回判定時は broker 列を併記すること (統合 §3 Rank 3 (ii) の F3 両基準併記と同じ規律)。

## 5. 執行契約 (as-placed) — 14/14

| # | trade | as-placed SL 距離 (p) | vs 150p | as-placed TP 距離 (p) | demo TP 距離 (p) | broker/demo TP 比 |
|---|---|---|---|---|---|---|
| 1 | #549260 | 18.7 | 0.125× | 69.0 | 80.9 | 0.853 |
| 2 | #573986 | 20.0 | 0.133× | 63.5 | 75.5 | 0.841 |
| 3 | #677396 | 12.2 | 0.081× | 67.6 | 79.6 | 0.849 |
| 4 | #677402 | 9.8 | 0.065× | 62.6 | 73.7 | 0.849 |
| 5 | #677910 | 11.4 | 0.076× | 68.5 | 80.3 | 0.853 |
| 6 | #677917 | 11.9 | 0.079× | 66.5 | 78.8 | 0.844 |
| 7 | #677924 | 11.8 | 0.079× | 67.4 | 79.5 | 0.848 |
| 8 | #677931 | 16.7 | 0.111× | 67.3 | 79.3 | 0.849 |
| 9 | #681149 | 17.1 | 0.114× | 60.4 | 71.0 | 0.851 |
| 10 | #709598 | 28.5 | 0.190× | 64.9 | 76.9 | 0.844 |
| 11 | #837947 | 24.6 | 0.164× | 58.8 | 69.6 | 0.845 |
| 12 | #837978 | 25.9 | 0.173× | 67.0 | 79.0 | 0.848 |
| 13 | #847578 | 21.8 | 0.145× | 66.0 | 77.9 | 0.847 |
| 14 | #893161 | 17.7 | 0.118× | 71.5 | 82.5 | 0.867 |

(SL 距離 = broker open price − ON_FILL `STOP_LOSS_ORDER.price`、TP 距離 = ON_FILL `TAKE_PROFIT_ORDER.price` − open price。demo TP 距離 = demo `tp` − demo `entry_price`。)

- **SL 契約は 14/14 で不履行** (カードの「11/11」を全数に拡張)。範囲 9.8–28.5p。**demo 行の `sl` 列も同じ距離 (9.8–28.5p)** ⇒ 置換は demo 簿に書かれる前、つまり demo_trader の order construction 内で起きている (OANDA 側でも bridge 側でもない)。修正箇所の特定は本稿の範囲外 (契約復元は user 決裁事項)。
- **TP は demo TP 距離 × 0.841–0.867** で 14/14 一定。`_QUICK_HARVEST_MULT = 0.85` (`modules/demo_trader.py:10281`) を `_tp_oanda = signal_price + (tp − signal_price) × 0.85` (`:7834`) で適用した値と整合 (比の揺れは signal_price と demo entry_price の差 = spread/slippage 由来)。カード「TP 固定 65.5p (suspected)」の suspected は解ける: **固定値ではなく demo TP の 0.85 倍**で、demo TP 自身が 69.6–82.5p と散るため broker TP は 58.8–71.5p に散る。
- 宣言 (TP 80p / SL 150p、R:R 0.53) に対し as-placed R:R は 2.28–6.39 ⇒ カード §(a) の「ペイオフ幾何の反転」は 14/14 で成立。

## 6. カード訂正 (同 PR、`strategies/usdjpy_carry_dip_accumulator.md` L3)

| 旧記述 (誤り) | 訂正 | 根拠 |
|---|---|---|
| 「2026-08-14 以降 fill 実績あり」 | **初 LIVE fill は #549260 (2026-08-05T04:17:52Z)**。08-05 / 08-09 / 08-12 の 3 本 (#549260 / #573986 / #677396) を含めて 14 本 (08-05〜09-11) | §2 broker tx 実在確認。カード L37 の「確認済み 11 本」は #677402 以降を数えた部分列挙 |
| 「`agg_kelly=-0.327<0` でゲート block」で fill 0 | **誤帰属**。`usdjpy_carry_dip_accumulator` は `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` (`modules/demo_trader.py:10560–10586`) に所属し 1000u では agg_kelly gate を bypass する。永続 block 台帳 (`GET /api/demo/block-counts?days=11`、09-22 06:3x UTC、`persisted.per_cell_counts`) の本セルは `order_bar_dedup` 319 / `velocity_down` 4 / `same_price_3pip` 1 / **AGG_KELLY 0**。fill 0 の第一候補は `_tick_entry` 下流の velocity_down ガード (§7) | [[path-to-win-reassessment-2026-09-22]] §1 執行層 |
| 「5.03 日間 live fill 0 本」 | 09-22T08:47Z 時点で最終 fill 09-11T11:02:36Z から **10.9 日** | demo 簿 |

訂正は旧文を置き換え、「2026-09-22 訂正、旧記述は誤り」を併記した (撤回は旧文の横ではなく旧文を置き換える — [[lesson-unscoped-global-replace-2026-09-18]])。**他の行は触っていない**。カード上表の「broker 実測 N=7 / 未集計」行は本稿で superseded (14/14、+¥793) だが、行の置換は orchestrator へ回す (本 PR は L3 のみ)。

## 7. velocity_down 照合 (価格キャッシュ、断定しない)

ガード仕様 (`modules/demo_trader.py:6350–6389`): `daytrade_1h` は直近 **60 分**の `_price_history` の最古 tick と current_price の差が **20 pip 以上の下落**なら BUY を block。本セルは `_is_shadow_eligible_full` でないため shadow 行にも残らず、行ゼロ = 台帳の 1 カウントだけが痕跡。entry は closed H1 bar 確定直後 (fill 時刻は毎時 +2 分〜+50 分) なので、60 分窓 ≈ 直前 closed H1 bar の値幅。本稿では **signal bar の body (close − open) と、entry − bar open** を代理値に使う (tick 最古値の厳密再現ではない。再起動直後は `_price_history` が空で fail-open — `:6362–6364`)。

### 7.1 09-11T12:00Z 以降 (fill 0 の窓) — qualifying bar 2 本
| bar (start UTC) | RSI prev→now | close | body | close − High |
|---|---|---|---|---|
| 09-11 12:00 | 47.0 → 33.0 | 153.457 | **−56.5p** | −102.8p |
| 09-14 18:00 | 54.3 → 44.1 | 154.016 | **−38.3p** | −39.8p |

- 2 本とも 20p 閾値を大きく超える下落中の bar ⇒ **velocity_down block と整合**。台帳の `velocity_down` 4 とは本数が合わない (bar 2 vs count 4) — per-tick 計数か feed 差か再起動再到達かは Render ログなしでは決められない (**未確定として記録**)。`same_price_3pip` 1 の帰属も不明。
- 09-15 以降は qualifying bar 自体が 0 本 (09-15〜09-22T06:00Z)。**直近 11 日の fill 0 は「シグナルが 2 本しか無く、その 2 本が急落バーだった」で説明でき、統計的異常ではない** (統合 §1 の Poisson P = 0.045〜0.16 と整合)。

### 7.2 08-01〜09-11 — qualifying bar 30 本 / fill 14 本
- 再現 qualifying bar 30 本のうち **14 本が実 fill と 1:1 一致** (14/14、外れなし)。未 fill 16 本の内訳 (代理値 body):
  - body ≤ −20p: **9 本** (08-07 12:00 −94.0 / 08-17 00:00 −20.5 / 08-21 08:00 −29.5 / 09-04 12:00 −58.9 / 09-07 00:00 −31.7 / 09-07 05:00 −24.3 / 09-08 12:00 −46.0 / 09-08 18:00 −63.7 / 09-09 11:00 −32.7) — velocity_down と整合する候補
  - body > −20p: **7 本** (08-13 12:00 −16.3 / 08-13 14:00 −11.3 / 08-24 00:00 −15.3 / 08-25 19:00 −8.7 / 08-26 01:00 −11.7 / 08-27 15:00 −6.8 / 09-08 21:00 −16.2) — うち 08-27 15:00 は hour block 落ち (REG resolved、shadow 行 id 16624)。残 6 本の理由は不明 (static hour block 免除前 = 09-04 commit 0268ad09 以前が 5 本 / cooldown・dedup・DD・feed 差のいずれか)
- fill 14 本の代理値: body −27.0〜+15.0p、entry − bar open −23.1〜+36.3p。**閾値を超える代理値でも fill した例が 3 本** (#677931 body −26.9 / #837978 −27.0 / #847578 −22.7) ⇒ 代理値と tick 最古値の差 (bar 頭の数分は窓外・再起動) が ±5–7p あり、**「20p ちょうどで切れる」ことは価格キャッシュからは言えない**。言えるのは「fill 集合は緩い押し目に偏り、急落 bar は fill していない」という傾向のみ。
- ⇒ カード L3 の訂正文は「fill 0 の第一候補は velocity_down (台帳 4 件、価格キャッシュで整合)」までに留め、「帰属確定」「設計衝突」とは書かない。ガード免除は live セルの新フィルタ変更 = R1 + user (D5/D8)。

## 8. Claude 推奨 (D5 入力、1 段落)

両 estimand (demo 簿 +7.36p/trade、broker realized +¥56.6/trade、N=14) が正で R2 は不成立 ⇒ **LIVE 停止は推奨しない**。一方、積まれている N=14 は SL 9.8–28.5p × TP 0.85 倍 × BE trail の「宣言と異なる戦略」の N であり、宣言契約 (TP 80p / SL 150p、BT WR 90.9% / PF 4.35 の前提) の N は 0 本のまま。推奨は **宣言契約 (SL 150p / TP 80p、QUICK_HARVEST 免除) の復元を R1 pre-reg で起案**すること — 復元後の live N≥30 を新規 estimand として凍結し、現行 14 本は「契約前」として別集計に置く (混ぜない)。これは autopilot 禁止 3 件の「carry_dip SL 150p 復元」そのもので **user 決裁 (D5) が必須**。復元を選ばない場合の既定は現状継続 + broker 列併記 (R2 は demo 簿凍結のまま)。velocity_down 免除は別の R1 (D8) で、本稿は起案しない。

## 9. caveat / 未検証

- broker realized は閉じ ORDER_FILL `pl` のみで **financing 非含**。スワップは別 tx (DAILY_FINANCING) で本稿は集計していない (hold は #709598 以外すべて <24h、週末跨ぎは halt 中に閉じた #709598 のみ)。
- `/api/oanda/trades` のローカル同期は 08-11 で停止しており、**14/14 のうち 12 本はローカル `oanda_trades` テーブルに存在しない**。再現性は `/api/oanda/transactions` idrange (tx ID は本稿の表に固定) に依存。
- §7 は価格キャッシュ (MASSIVE 15m → H1) による再現で、live engine の feed / RSI と一致する保証は「14 fill の 14/14 一致」のみ。台帳 count 4 と bar 2 の差は未解決。
- 30d 窓 (N=5) の符号割れは #709598 1 本で説明され、判定には使わない。
- カード上表の broker 行 (N=7 / 未集計) は本稿で superseded、行置換は未実施 (本 PR は L3 のみ)。
- `_QUICK_HARVEST_MULT` の carry_dip 免除有無 (`_QUICK_HARVEST_EXEMPT` は (entry_type, instrument) 集合) は code で本セル非所属を確認したが、demo TP 自体が宣言 80p (shift 3p 後 77p) と一致しない理由 (69.6–82.5p) は未追跡。

## 10. 出所

- demo: `GET https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000&date_from=2026-04-01&status=closed` (2026-09-22 08:3x UTC)
- broker: `GET /api/oanda/transactions?from=&to=` (`app.py:14227–14249`、`modules/oanda_client.py:358–370` `get_transactions_id_range`)、`lastTransactionID` 893179。閉じ tx: 573983 / 677393 / 677399 / 677907 / 677913 / 677920 / 677927 / 681146 / 709522 / 837943 / 837950 / 847563 / 859453 / 893170
- `GET /api/oanda/trades?limit=500&date_from=2026-08-01&instrument=USD_JPY` → 2 行 (synced_at 2026-08-11 06:44)
- 台帳: `GET /api/demo/block-counts?days=11` (09-22 06:3x UTC、scratchpad `block_counts_11d.json`) `persisted.per_cell_counts["usdjpy_carry_dip_accumulator|USD_JPY:*"]`
- code: `modules/demo_trader.py:5506` (order_bar 予約) / `:5549–5573` (same_price) / `:6350–6389` (velocity) / `:7828–7838` + `:10281` (QUICK_HARVEST) / `:10560–10614` (bypass set・判定) ; `strategies/hourly/usdjpy_carry_dip_accumulator.py:60–67, 94–107, 194–201`
- 価格: `data/cache/massive/USD_JPY_15m.parquet` (gitignored、末尾 2026-09-22T06:00Z)
- KB: [[usdjpy_carry_dip_accumulator]] / [[t5-restore-eval-and-carrydip-revival-2026-08-10]] / [[path-to-win-reassessment-2026-09-22]] / REG `carry-dip-v3-revival-watch`, `carry-dip-live-to-shadow-drop-cause`
