# weekend_gap_fade — 週末ギャップ・フェード

- **Status**: 🟢 LIVE (固定 1000u sentinel) — rule:R1 pre-reg LOCK、user 最終承認 2026-07-24 (option (b) 直接 live MIN lot)
- **Tier**: PAIR_PROMOTED (EUR_USD, USD_JPY, AUD_USD) + UNIVERSAL_SENTINEL 併存 (vix_carry_unwind と同型)。GBP_USD は永久対象外 (逆符号 family 用に OOS 清浄維持)
- **実装**: 2026-07-24 (本カードと同一コミット)

> ⚪🔴 **2026-09-07 実測 — 09-06 の発注は `MARKET_HALTED` で拒否され、約定していない (fill 実績にカウントしない)**。tx **837792** (2026-09-06T21:01:12Z、USD_JPY **+1,000u** `CLIENT_ORDER`) は **同一秒に tx 837793 で `ORDER_CANCEL` reason=`MARKET_HALTED`**。broker `openTradeCount` **0** が裏付け ⇒ **orphan 建玉なし**。⚠️ ただし `/api/oanda/status.recent_errors[0]` はこれを `"OPEN buy ok but no tradeID"` と記録しており、**ハンドラが halt キャンセルを「ok」と誤分類している** (本戦略の欠陥ではなく共通の error 分類バグ — 未修理の独立 item)。詳細: [[2026-09-07]]
>
> 🔑 **副産物として本戦略は診断上の対照群になった**: この発注は `stopLossOnFill` **154.452** を載せており、市場 ~156.0 に対し **~155 pip** = 設計通りの広い SL。同時期の [[usdjpy_carry_dip_accumulator]] は宣言 150p に対し **24.6–28.5 pip** しか載せていなかったため、**SL 切り詰めは `daytrade_1h_*` 共有ブリッジ普遍の現象ではなく carry_dip 側に固有**と切り分けられた。
>
> 📌 救済注記 (2026-09-17): 本項執筆時 (09-07) の「発注タイミングを市場再開の確定後にずらす価値がある」は、**2026-09-10 の執行契約 AMENDMENT (B) §4.1 (下記) で採用・実装済み** — 未決事項ではない。

## 根拠 (凍結統計 — OOS 再接触・再集計は §8 で禁止)

| 項目 | 値 | 出典 |
|---|---|---|
| OOS verdict | **arm B PASS**: N=177 pair-events / 112 週末、gross +15.60p/event、weekend-block bootstrap p<1e-4、stressed-net +9.04p、knife-edge 4/4 維持 | [[weekend-gap-oos-prereg-2026-07-24]] §11 |
| 実測 RT 置換 (R1 step①) | pooled 初バー実測 RT mean 7.70p / p90 12.34p → net **+7.90p / +3.26p (p90 tail)** — 正 EV 保存 | `reports/sunday_open_spread-2026-07-24.md` §3 |
| 頻度 | ~3.28 イベント/月 (2.07 qualifying 週末/月)、cap skip 計画値 10–20% | OOS report §6 |
| 月次期待 | +22〜26 pip ≈ +$2 @1000u、σ_month ≈ 63p (単月負け 34% = 正常挙動) | 執行 pre-reg §3.2 |
| 執行 pre-reg (LOCKED) | [[weekend-gap-stage2-execution-prereg-2026-07-24]] — §2/§3/§5 の凍結値変更は R1 | user 承認 2026-07-24 |

## シグナル定義 (explore ツールと同一 — `tools/weekend_gap_fill_explore.py` を厳密複製)

- Friday close = Fri 21:00 UTC 境界前の最終 15m バー Close (≤6h guard、mid)
- Sunday open = Sun 21:00 UTC 以降の最初のバー Open (≤24h guard、mid — 冬の 22:0x open もガード内)
- qualify: |gap| ≥ **EUR_USD 20.0p / USD_JPY 21.4p / AUD_USD 25.0p** (凍結。再計算禁止)
- 方向: gap fade (gap up → SELL / gap down → BUY)
- entry 窓: 初バー open ts から 4 bars (bar-length terms、15m→60分)。窓外は不発 (追いかけ禁止)
- **shadow row も同一シグナル経路** — live/shadow の分岐は demo_trader の共通ガードチェーンのみが行う (§4.0: shadow 分母は常に完全、cap は LIVE 側 winning-location フィルタ)

## 執行仕様 (凍結)

> **⚠️ AMENDMENT 2026-09-10 — 執行契約 (B) 発効 (rule:R1、user 承認「進めて」2026-09-10)**
> 決裁: [[weekend-gap-execution-contract-r1-packet-2026-09-10]] §4。機構: エンジン発火 21:01 UTC < OANDA 実開場 21:04-21:05 (直近 16 週末 × 3 ペア = 48/48 実測) → 旧契約 (即時 FOK) は MARKET_HALTED cancel が決定論的で **live fill 0/3 イベント**だった。改定内容:
> 1. **entry 送信の繰り下げ (§4.1)**: シグナル成立後、live 送信は **OANDA 実開場確認 (pricing の instrument `tradeable`、quote age <10s、poll ≤60s) 後の最初の評価 tick** まで保留。保留中は latch を立てない (`modules/data.fetch_oanda_pricing_state` + `weekend_gap_entry_send_decision`、scoped runner 前段)。
> 2. **打ち切り (§4.2、凍結値)**: 初バー ts + **15 分**を過ぎても halt 継続 → live 放棄、latch=`ABANDONED_HALT`、shadow row 記録 (分母保存)。
> 3. **放棄境界 (§4.3、凍結値)**: 送信直前の fade 方向 adverse drift (基準 = Sunday open) > **+8.0p** → live 放棄、latch=`ABANDONED_DRIFT`、shadow row 記録。
> 4. **halt-race 限定再送 (§4.4、凍結値)**: tradeable 確認後の FOK が `MARKET_HALTED` cancel (cancel tx 確認済み) で返った場合のみ **30s 後に 1 回だけ** FOK 再送 (最大計 2 送信)。他 reason は従来どおり再送禁止。
> 5. **G1 slippage 基準 (§4.5)**: 「実際に fill した送信 attempt の直前 quote」— 再送時は再送直前 quote に基準を差し替え (初回 quote 固定だと繰下げドリフト mean +3.15p が G1 に混入し N=6 で恒久誤停止 = packet §3 が案 A を棄却した理由)。
> 6. **観測強化 (§4.6)**: 評価ごとに `[WEEKEND_GAP][EXEC_B]` ログ (tradeable/quote_age/drift/send_mid) + demo row reasons へ `[WG_EXEC_B]` 永続化。cap 10.0p 判定は実開場後の実 quote で行われる (indicative quote 判定は構造的に消滅)。tradeable 未確認 sig の live 送信は `_tick_entry` backstop が block (`weekend_gap_tradeable_unconfirmed`、row/latch なし = HOLD 相当 — 冗長エンジン経路も対象)。
> **不変更**: シグナル定義・qualify 閾値・cap 10.0p・1000u・4h exit・disaster SL 150p・G1/G2/G3 の全定義と閾値。estimand コスト (繰下げ mean +3.15p) は織り込み済み → 実効 EV ≈ +4.75p/event (packet §5.3)。改定後 fill 成立率見積り: 点 ~94% / 保守 ~75%。

| 項目 | 実装 |
|---|---|
| entry | **(AMENDMENT B)** OANDA 実開場確認後の最初の評価 tick に成行 FOK。リトライは §4.4 の halt-race 限定再送 1 回のみ (bridge `max_attempts=1` は不変 — timeout retry の二重約定封鎖は維持) |
| spread cap | 発注時 quoted spread > **10.0p** → live 送信スキップ + shadow row (`block_cause=weekend_gap_spread_cap(spread=X.XXp)`、実測値保存 = 分母保存)。quoted 取得不能時も fail-closed で shadow |
| E1 置換の範囲 | **置換 = E1 per-pair limit + 動的 spread/TP guard の 2 つのみ (entry_type-scoped)**。共有 = is_shadow/is_promoted チェーン、daily loss gate (bridge)、watchdog/blacklist、exposure (1000u 実値で見積)、spike/velocity、order-bar dedup、agg-Kelly (min-lot bypass 登録) / MC-ruin gate |
| exit | **entry+4h (14400s) 成行 time-exit のみ** (`close_reason="horizon"`、exact override — mode default 8h と max() 合成しない)。TP/BE/Trail/BE_LOCK/C1/SIGNAL_REVERSE 全て無効化済み |
| disaster SL | entry ∓ **150p** (OANDA stopLossOnFill)。発火時は `close_reason="disaster_sl"` で個別 flag (G3③ 審査対象)。OANDA 注文に takeProfit は付けない (demo row の TP 500p は engine placeholder) |
| サイジング | **固定 1000u** (`WEEKEND_GAP_FADE_MIN_LOT`)。lot 3-factor / Kelly / DD lever / FLAT_UNITS / agg-Kelly boost 全て非適用を code で固定 |
| dedup | **per-pair per-weekend latch を system_kv 永続** (`weekend_gap_fade:{pair}:{sunday_date}` = EXECUTED / SKIPPED_SPREAD / **ABANDONED_HALT / ABANDONED_DRIFT** ← AMENDMENT B §4.2/§4.3)。row 作成直後・OANDA 送信前に set。HOLD (実開場未確認・打ち切り前) は latch を立てない。DB read 失敗は fail-closed (= latched 扱い) |
| 同時ポジション | 3 ペア同時 qualify は全執行 (§2.4 — 選択的執行禁止。cap skip のみが正当な未執行)。exposure 見積を 1000u 実値にして 20k cap 誤衝突を回避 |

## 実行経路 (夏/冬の非対称に注意)

1. **Primary: scoped Sunday runner** (`demo_trader._weekend_gap_tick`) — `_is_fx_market_closed()` が日曜 22:00 UTC まで True のため、market-closed gate より**前**に本 entry_type 専用の評価だけを走らせる (夏 21:05±2 の estimand を満たす唯一の経路)。発注は通常の `_tick_entry` 共有ガードチェーン — **別送信経路は作らない**。
2. **冗長系: DaytradeEngine 登録** (`strategies/daytrade/__init__.py`) + `LIVE_PROMOTE_LOSERS` side-channel (select_best silent-drop の 7 例目回避)。latch が二重発注を防ぐ。
3. **AUD_USD**: 15m mode が無かったため `daytrade_audusd` を新設 — ただし `weekend_gap_only=True` で**本戦略以外は一切走らない** (他戦略の挙動へ波及ゼロ)。
4. estimand 保存のための scoped 免除 (§2.4「cap スキップのみが正当な未執行」): HTF Hard Block (app.py 候補段, T8 と同型の silent-drop 防止) / EUR_USD Late-NY 静的 gate / MTF tactical bias / SL狩り対策②③B1 (150p 凍結 SL の改変防止)。**口座防御系 gate は全て共有**。

## 前向きゲート (pre-reg §5 — R2 自動停止、code + system_kv)

| gate | 発動 | 実装 |
|---|---|---|
| G0 配管 | 最初の 2 qualifying 週末: 発火時刻 21:05±5m (冬 22:05±5m) / latch / exit 4h±10m / cap 判定ログ | 週次監査 + 月曜 daily report で人手確認 (不備 = R3) |
| **G1 slippage** | live N≥6 rolling mean slippage > +2.0p | `_weekend_gap_check_r2_gates()` が送信前に毎回評価 → 恒久 kv flag `WEEKEND_GAP_LIVE_STOPPED` + `[ALERT][WEEKEND_GAP]` print + AlertManager 通知。**一度 fire したら code 上の再武装経路なし** (watchdog DECREMENT 教訓)。slippage は OANDA 実 fill vs signal_price を bridge が demo row に永続化 (`record_fill_slippage`) |
| **G2 first-look** | live N=12 cumulative net < −60p | 同上 (同一 flag) |
| G3 confirm | live N=30: mean>0 ∧ WR≥35% ∧ disaster SL 0 件 → lot ladder の R1 起案権のみ (自動増額なし) | 人手 (R1) |
| 常設 | 月次 `tools/sunday_open_spread_measure.py` re-run (冬時間初週末は注視) | 既存ツール |

**解除**: `WEEKEND_GAP_LIVE_STOPPED` kv の手動削除 + R1 決裁のみ (code は削除経路を持たない)。stop 後も shadow 蓄積は継続 (分母保存)。

## 監視

- N 定義: live 執行済み pair-event (cap skip は分母記録のみ)。統計検定は weekend-block。
- 週次戦略監査 (`raw/audits/`) に weekend_gap 行を追加、月曜 daily report で前週末イベントに言及 (T5 教訓: 執行されない pre-reg を作らない)。
- 観測点: system_kv `weekend_gap_fade:*` (latch) / `WEEKEND_GAP_LIVE_STOPPED` (stop flag) / oanda_audit `block_reason=weekend_gap_spread_cap*` (cap skip 分母)。

## イベントログ

### 2026-07-26 (日) — 初回 qualifying イベント

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | qualify | 発火 → row 挿入 + latch 済み | **shadow −22.8p = バグ起因の未送信** | `_is_xau_inst` UnboundLocalError (2026-04-10 から chronic) で OANDA 送信前にクラッシュ。live 執行分母 (G1/G2/G3 の N) には**入れない** — pre-reg 上の正当な未執行ではなくインフラ障害。詳細: [[lesson-preserve-sltp-unboundlocal-2026-07-28]] |
| EUR_USD | **+19.9p < 20.0p** | no-qualify | 不発 (正常) | 閾値 0.1p 差の near-miss。当時 no-qualify は無音 — 2026-07-28 rule:R3 で週末ごと 1 行の gap 診断ログを追加 (分母保存、行挿入なし)。**閾値は凍結値 — near-miss を理由とした再調整は §8 で禁止** |
| AUD_USD | no-qualify | — | 不発 (正常) | — |

**フォローアップ (2026-07-28 rule:R3)**: ① `_is_xau_inst` スコープ修正 + regression pin `tests/test_preserve_types_tick_entry.py` (preserve 全型を送信判定直前まで通す統合テスト)、② wg tick error handler に traceback 追加、③ **データソース**: AUD_USD を `_MASSIVE_SYMBOLS` に追加 — 凍結統計は Massive parquet ベースであり **Massive が estimand 正** (従来 AUD_USD だけ live が OANDA fallback でソース不一致だった)。

### 2026-08-02 (日) — 第 2 回 qualifying イベント (2026-08-03 診断、Render ログ + oanda_audit + 口座実査)

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | **−22.5p ≥ 21.4p** | qualify → BUY fade 発火、**live 送信は正常実行** (agg-Kelly carve-out BYPASS 作動、1000u FOK SL=155.646) | **OANDA order 作成 (tx 549257, 21:01:27.9Z) だが fill transaction なし = tradeID 未取得、ポジション不成立** | oanda_audit = `sent` のまま。口座実査 (08-03): openTrades 0 / balance==NAV = **実損ゼロ・orphan なし**。**✅ cancel reason 実測確定 (08-05、`/api/oanda/transactions` 照会): tx 549258 ORDER_CANCEL reason=`MARKET_HALTED`** — FOK の流動性/価格バウンド問題ではなく、**日曜オープンの激動で OANDA 側が USD_JPY 市場を halt していた** (21:01:27.9Z、order 作成と同 ms)。含意: (i) FOK→IOC 変更は無効 (halt 中は注文タイプ無関係) (ii) 有効な候補は entry 繰り下げ (halt 解除後) or 限定 retry のみ (iii) 08-09 観測ではエントリー時点の halt 状態 (`tradeable`/halted) も記録すること |
| EUR_USD | +17.5p < 20.0p | no-qualify | 不発 (正常) | 07-28 R3 の gap 診断ログが設計どおり作動 |
| AUD_USD | +23.0p < 25.0p | no-qualify | 不発 (正常) | — |

**counterfactual (shadow book)**: USD_JPY shadow row は **disaster_sl −182.7p** — 週末リスクオフ (JPY 急騰) で gap は fade せず走った。fill されていた場合の live 損失 ≈ −182p × 1000u ≈ −1,800 JPY (disaster SL は設計どおり機能した想定)。**no-fill は結果的に得だったが、これは執行設計の検証ではない**。

**分母の扱い**: 「送信 OK・FOK 不成立」は pre-reg §2.2 (no-retry) の執行契約内の正当な未執行 = **G1/G2/G3 の live N には入れない** (07-26 のバグ未送信とは区別: あちらはインフラ障害)。live 執行 N = **0/2 イベント**。

**⚠️ 執行設計への実測疑義 (R1 決裁事項として記録、変更は未実施)**: stage-2 執行 pre-reg は Sunday open での fill 可能性を前提とするが、2 イベント連続で live fill ゼロ。FOK→IOC 変更・retry 追加・entry 時刻繰り下げ (spread 正常化 22:01 以降) はいずれも**凍結執行契約の変更 = R1 全段 + user 承認が必要**。次イベント 2026-08-09 (日) 前に user 決裁を仰ぐこと。

**決裁記録 (2026-08-03)**: user 決裁「推奨で進めて」= **現状維持 (凍結執行契約のまま) で 08-09 イベントを追加観測**。根拠: live fill 失敗 N は実質 1 (07-26 はインフラ障害で執行設計の証拠にならない)、「大 gap ほど FOK 不成立」仮説の証拠不足、執行方式変更は estimand 破壊のため counterfactual (FOK vs IOC の約定率・スリッページ差) 定量化を前提とする。counterfactual の第一材料 = 08-02 cancel reason の確定 (`/api/oanda/transactions?from=549256&to=549260` — 本決裁と同 PR で追加した read-only 照会エンドポイント)。08-09 も不成立なら fill-rate 選択バイアスの証拠が N=2 になり、執行契約変更パケット (R1) を正式起案する。

### 2026-09-06 (日) — 第 3 回 qualifying イベント (2026-09-10 一次実査、packet 起案と同時)

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | qualify | 発火 → BUY fade、live 送信正常 (oanda_audit #16503 `sent`, 1000u, 21:01:12Z) | **tx 837792 order → tx 837793 ORDER_CANCEL reason=`MARKET_HALTED`** — 08-02 と同一機構、fill なし。shadow row 17179 (signal 156.269, spread_at_entry 3.1p) は horizon −35.4p | halt 解除は **21:04:58.2Z** (tx 837943) と直接実測。live 執行 N = **0/3 イベント** (G 分母は 0/2 — ① はインフラ障害) |

**機構確定 (2026-09-10)**: エンジン発火 21:01 (MASSIVE forming bar) vs **OANDA 実開場 21:04–21:05 (直近 16 週末 × 3 ペア = 48/48 で初 M1 = 21:04)** → 現行契約 (FOK 1 回・リトライなし) の fill 率は構造的に ~0%。08-03 決裁の残存仮説「大 gap ほど FOK 不成立」は棄却 (gap サイズ無関係)。**執行契約 R1 改定パケット起案済み → [[weekend-gap-execution-contract-r1-packet-2026-09-10]] (user 決裁期限 09-12、次イベント 09-13 前)**。実測: `bt-results/wg_gap_drift-2026-09-10.json`。

### 2026-09-10 — 執行契約 (B) AMENDMENT 発効 (rule:R1、user 承認「進めて」)

- パケット [[weekend-gap-execution-contract-r1-packet-2026-09-10]] 提示 → **user「進めて」で案 (B) 承認**。同日実装 PR (feat/wg-execution-contract-b-20260910) で §4 全条項を執行 (内容は上の 執行仕様 AMENDMENT 註記)。次イベント **2026-09-13 (日) 21:00 UTC** が改定後初の検証点 — 手順は registry `weekend-gap-execution-amendment-g0prime` (期日 09-28、最初の 2 qualifying イベントで G0' 配管確認)。
- **採用/棄却境界 (packet §6、凍結)**: 改定後最初の 2 qualifying イベントで fill 成立 (cap skip / 正当放棄除く) → 通常運用へ。**2 連続 fill 不成立 → 執行モダリティ自体を再審 (R1 再起案)** — 3 度目の「観測して待つ」はしない。冬時間初週末 (2026-11-01) は実開場 22:04-22:05 からの乖離 >±10 分で R3 打ち切り時刻再導出。
- registry: `weekend-gap-live-g1-slippage` / `weekend-gap-live-g2-cumloss` / `project-falsification-f2-wg-live-conversion` に AMENDMENT 発効を追記 (live N カウントは発効後 fill から)。

### 2026-09-13 (日) — 改定後第 1 回 qualifying イベント (G0' event #1) — live = ABANDONED_DRIFT (2026-09-22 転記、事象から 9 日遅延)

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | **−50.0p ≥ 21.4p** (Fri close 153.620 → Sun open 153.120) | qualify → BUY fade 発火 **21:05:03Z**、shadow row **id 17602** | **live 放棄 = `ABANDONED_DRIFT`**: OANDA tradeable 確認時点 (quote_age **7.5s**) の fade 方向 adverse drift **+41.0p > +8.0p** (凍結境界 §4.3) → latch=`ABANDONED_DRIFT`、shadow row 記録 (分母保存)。oanda_audit `weekend_gap_exec_abandon(ABANDONED_DRIFT,drift=+41.00p)` **21:05:05Z** | ギャップの ~47p が初 15m バー内 (大半は約定不能の halt 窓 ~4 分) で消費。**改定後 qualifying 不成立 1 件目** (packet §6「2 イベント連続で fill 不成立」の第 1 件 — drift 放棄は不成立に含む、registry `weekend-gap-execution-amendment-g0prime` message)。出所: [[daily-observations-2026-09]] O-2026-09-14-1 / [[2026-09-16]] L241 |
| EUR_USD | **−2.2p < 20.0p** | no-qualify | 不発 (正常) | gap 診断ログ `[WEEKEND_GAP] EUR_USD gap=-2.2p < 20.0p no-qualify` **21:01:08Z** (Render ログ API 実読 2026-09-22 (service `srv-d6va1of5r7bs73en10vg`、2026-09-13T20:55–21:30Z、text=`WEEKEND_GAP` 25 行・hasMore=false)) |
| AUD_USD | **−14.7p < 25.0p** | no-qualify | 不発 (正常) | 同 `AUD_USD gap=-14.7p < 25.0p no-qualify` **21:01:29Z**。⚠️ 09-22 初版は oanda_audit 09-13 行数 1 ([[2026-09-16]] L242) から「no-qualify (推定)」と書いていた — audit 不在は「監査経路未到達」の証明にすぎず (`_weekend_gap_tick` の非監査 return / `_tick_entry` 早期 block)、**以後は診断ログで確定するまで UNKNOWN と転記する** (DRAFT §6、PR #281 review P2) |

- **本イベントの shadow outcome は意図的に記載しない** (G0'/G1/G2/G3 凍結 look の汚染防止 — O-2026-09-14-1 と同じ規律)。
- 価格系の記述のみで観測可能な仮説: **|gap| が大きいほど tradeable 時点の drift も大きく、qualify する最大級 event ほど live 送信が構造的に不可能になる選択バイアス** (O-2026-09-14-1 の反証可能予測: 今後の qualify event で |gap| と drift は正相関、|gap|≥40p では drift>8p が常態のはず)。境界導出時の実測 (packet §5.3: qualifying・cap 通過 N=8 の +5m adverse drift mean +3.15p / 全 48 pair-weekend p90 6.7p、`bt-results/wg_gap_drift-2026-09-10.json`) に対し mean 比 ~13 倍 / p90 比 ~6 倍。
- live fill 通算: **0/4 qualifying イベント** (07-26 インフラ障害 / 08-02・09-06 MARKET_HALTED / 09-13 ABANDONED_DRIFT)。改定後 (契約 B) = **0/1**。G1/G2/G3 の live N は依然 0。
- ドリフト検出 (§4.3) は設計どおり作動 — 放棄は契約の欠陥ではなく契約の仕様。**+8.0p 境界の R1 再起案は packet §6 の事前コミット (不成立 2 連続) まで保留** — 本 event で 1 件消費。
- EXEC_B 遷移 (Render ログ実読 09-22): `[WEEKEND_GAP][EXEC_B] USD_JPY decision=HOLD tradeable=False` **14 行 21:01:27–21:04:33Z** (halt 窓、quote_age ~173,000s = 金曜 quote) → `decision=ABANDONED_DRIFT tradeable=True quote_age=7.493s drift=+41.00p send_mid=153.53 sunday_open=153.12` **21:05:02.5Z** → `live execution abandoned (ABANDONED_DRIFT) → shadow record` 21:05:03.2Z → OANDA `[SKIP] weekend_gap_exec_abandon(ABANDONED_DRIFT,drift=+41.00p)` 21:05:14.3Z。09-13 の pair-event 列は **[USD_JPY ABANDONED_DRIFT] の 1 件のみ** (他 2 ペアは診断ログで no-qualify 確定 = 分母外) — G0' 不成立カウント 1/2 は一次データで確定。

### 2026-09-20 (日) — NO-QUALIFY (分母外、G0' event #2 は 09-27 へ繰越)

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | **−19.0p < 21.4p** | no-qualify | 不発 (正常) | near-miss 2.4p。**閾値は凍結値 — near-miss を理由とした再調整は §8 で禁止** (07-26 EUR_USD +19.9p と同じ扱い) |
| AUD_USD | **−20.5p < 25.0p** | no-qualify | 不発 (正常) | — |
| EUR_USD | **−1.9p < 20.0p** | no-qualify | 不発 (正常) | — |

- 出所: Render ログ `[WEEKEND_GAP]` gap 診断行 **2026-09-20T21:01:13–21:01:29Z** (07-28 R3 で追加した週末ごと 1 行の診断ログ、2026-09-22 実読 → [[2026-09-22-session]] に転記)。row 挿入・latch なし (設計どおり)。
- NO-QUALIFY は G0' の**分母外** — 改定後不成立カウントは 1 件のまま不変。**次の検証点 = 2026-09-27 (日) 21:00 UTC** (以後 10-04 / 10-11 …)。registry `weekend-gap-execution-amendment-g0prime` の期日 09-28 は繰越が必要 (registry 編集は別担当)。
- 3 週末連続 non-qualifying の確率 ≈ 14% (2.07 qualifying 週末/月 ÷ 4.35 週末/月 → p≈0.48 → (1−p)³ ≈ 0.14; [[path-to-win-reassessment-2026-09-22]] §3 Rank 6 は 14〜17% 幅) — 起きても異常ではない。

### 分岐の事前固定 (2026-09-22、DRAFT) — 次の qualifying イベント (09-27 以降)

**fill** → F2 resolve — **自動ではない**: watcher `tools/prereg_trigger_watch.py::evaluate_live_count_decision` は clean live N≥1 (registry `project-falsification-f2-wg-live-conversion`、n_decide=1) で `TRIGGERED` を返すだけで registry を書き換えない。24h 以内に registry 編集 PR (別担当) で `active:false` + `resolved` + `resolution` を明示記録、編集までは F2 active のまま (DRAFT §2 row 1) + **G0' 完了** (packet §6「改定後の最初の 2 qualifying イベント」で fill 成立 → 通常運用へ、連続不成立 trigger は終了 — 以後の放棄は記録のみ、rolling gate は未承認) + 改定後 fill 成立率の第 1 観測 (G0' 手順 (1)–(5)、slippage は当該 1 event の persisted 値の読み取りのみ・集計しない) / **`ABANDONED_*` または新種 cancel** → **G0' event #2** (09-13 USD_JPY = event #1 の次に qualify する pair-event、cap skip 除く) が不成立 (`ABANDONED_*` / SEND 後 2 回とも `MARKET_HALTED` cancel / 新種 cancel / SEND 後 fill も cancel tx も無し [`OPEN … FAILED` / `ok but no tradeID`、oanda_bridge.py:797–826、再送なし] = `oanda_trade_id` 空で終端) なら **改定後不成立 2 連続 = packet §6 発動 → 執行モダリティ R1 再審**。同一週末に複数 pair-event が qualify し結果が**混在**した場合、event #2 の順序付けは永続 first-qualification ts (未実装、R3 — 09-27 前の実装を推奨) が存在するまで運用に使わず、全時刻 (Render ログ初回発火 / latch `ts` / `entry_time` / 終端) を転記して **W5 で user 上程** — 終端時刻は halt-race 再送 +30s で反転、ログ発火は再発火・非永続、latch / entry_time は HOLD・guard・open_trade の後で qualification 順を保証しない (DRAFT §2 (β))。全て同一クラスなら順序不問。**G0' は 2 event で終了** — event #2 が fill なら後続の放棄は記録のみ (rolling gate は未承認) (骨子: [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] — DRAFT であり LOCK ではない、R1 起案への昇格は user 承認) / **`SKIPPED_SPREAD`** → 正当な未執行、G0' の 2 イベントに数えず繰越 / **NO-QUALIFY** → 分母外、次週へ繰越。**イベント後 24h 以内 (月曜 daily report と同時) に本カードへ転記する** (価格系・執行系のみ、shadow outcome は書かない) — 09-13 は 9 日遅延した (本節が是正)。冬時間初週末 2026-11-01 の打ち切り基準時刻 (first_bar_ts の冬解決) の R3 確認は 10-25 まで (DRAFT §5)。

## テスト

`tests/test_weekend_gap_fade.py` (29 tests): 検出 (qualify/非qualify/方向/ガード/窓/凍結閾値) / cap 境界とスコープ / latch dedup + fail-closed / G1/G2 発火・境界・**非再武装** / 1000u・horizon・disaster SL・no-TP・登録 4 点 pin。
`tests/test_weekend_gap_execution_contract_b.py` (26 tests、AMENDMENT 2026-09-10): 凍結値 pin / send decision 境界 (tradeable 直後 SEND・+15 分 strictly-after・drift strictly >+8.0p・符号規約両スケール) / **counterfactual kill pin** (繰り下げ配線を殺すと halt 中 tick が `_tick_entry` に到達して落ちる — 実証: 配線 kill で 5 tests fail) / halt-race 限定再送 (1 回のみ・MARKET_HALTED 限定・flag なし再送なし・transport error 対象外) / **G1 基準 quote 差し替え pin** (再送 fill の slippage が再送直前 quote 基準 — basis swap を殺すと落ちることを実証) / `fetch_oanda_pricing_state` (ナノ秒 ts parse・halted・fail-closed)。

## 参照

- [[weekend-gap-stage2-execution-prereg-2026-07-24]] (執行 pre-reg LOCK) / [[weekend-gap-oos-prereg-2026-07-24]] (OOS verdict)
- `reports/sunday_open_spread-2026-07-24.md` (実測スプレッド)
- MEMORY: `project_engine_reconstruction_live_dedup_dead` / `project_be_trail_inflates_python_bt_wr` / `project_watchdog_decrement_rearm_bug` / `project_t5_jpy_cap_prereg_executed` / `project_t8_week1_gate_breach`
