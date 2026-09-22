# rnb_support_bounce shadow レーン lane-health 事前調査 (2026-09-22)

**rule**: R3 (件数・配線・頻度のみ — WR/EV/PnL は計算も閲覧もしていない、P-10 非抵触)
**対象**: registry `rnb-shadow-lane-health-checkpoint-1` (期日 2026-09-24、closed shadow N<3 で TRIGGERED) の到達前調査。sprint 2026-09-22 S4 (final_assessment §3 Rank 8 (i))。
**一次資料**: [[rnb-support-bounce-r1-packet-2026-09-10]] §2/§6/§9 / [[rnb-dead-mode-and-block-estimand-2026-09-05]] / [[blocker-refutation-2026-09-10]] §2 (rnb-shadow-forward 行 = cadence 穴、kb-06 = conf 単位バグ) / 本番 `/api/demo/status`・`/api/demo/block-counts` (2026-09-22 08:4x UTC pull) / Render app ログ (srv-d6va1of5r7bs73en10vg、2026-09-10〜09-22) / `modules/demo_trader.py`・`app.py` (main 0e911f04)。
**凍結 look 非接触**: LOCK `rnb-support-bounce-shadow-forward` の outcome (WR / net EV) は本稿で一切計算していない。trades 行からは id / 時刻 / is_shadow / oanda_trade_id / confidence のみ読んだ (close_reason・pnl 列は読んでいない)。

---

## 0. 要約 (5 行)

1. **closed shadow N = 2** (09-11 10:42Z / 11:31Z)。09-24 checkpoint-1 は **TRIGGERED 確定見込み** (期日まで 1.5 営業日、09-12 以降 12 日間で行ゼロ)。
2. **配線は開いている**: 2 行とも `is_shadow=1 ∧ oanda_trade_id=''`、confidence 48 / 68 (0-100 スケール)、11 日永続集計で `conf<30` / `no_confirm` / `unknown_type` は **0 件**。conf 単位バグ再発・QUALIFIED_TYPES 落ち・shadow_only 配線落ちの 3 仮説は **全て反証**。
3. **setup 供給も止まっていない**: 登録修理後 (09-10 16:49Z〜) の active 窓 (UTC 7–20) で BUY bar は **11 本** (forming-bar 評価)。「単に相場 setup 不在」も **反証**。
4. **行ゼロの真因 = `_tick_entry` 下流の live 保護 gate**: 09-12 以降の BUY bar 6/6 が `mtf_strong_bias` (trend_down_strong 下の BUY) / `velocity_down` / `1h_rr_low` で **hard block** (shadow 迂回なし)。この 3 gate は 365d ablated BT では**適用されていない** = BT⇄live 母集団の非同期 (CLAUDE.md「フィルターは本番⇄BT 同期必須」に反する状態)。
5. 09-11 の `session_hours` **211 件**は **stale feed アーティファクト** (fetched bars が 20:54Z〜21:54Z+ で 4403 に凍結、hour=20 の stale bar を 21 時台に再評価) で、tz バグでも配線バグでもない。実 setup の損失ゼロ。

---

## 1. 母集団と N (2026-09-22 08:4x UTC)

| 項目 | 値 | 出所 |
|---|---|---|
| LOCK 母集団 | mode `rnb_usdjpy` × `rnb_support_bounce` × USD_JPY × BUY、closed、dedup_violation=0、厳格 shadow (`is_shadow=1 ∧ oanda_trade_id=''`)、since 2026-09-10 | registry `rnb-support-bounce-shadow-forward` |
| **closed shadow N** | **2** — id 17559 (entry 2026-09-11T10:42:42Z) / id 17565 (entry 2026-09-11T11:31:28Z) | scratchpad `trades.json` (2,002 行、08-18〜09-22 を被覆 = since 以降を完全被覆)、Render ログ `📥 IN [RNB USD/JPY (shadow)]` 10:42:44Z / 11:31:28Z |
| 厳格 shadow 判定 | 2/2 が `is_shadow=1`、`oanda_trade_id=''`、ログ `🔗 OANDA: [SKIP] rnb_support_bounce — Reason: shadow_tracking` | 同上 |
| confidence | 48 / 68 (0-100) | 同上 — conf gate (threshold 30) 通過を実測で確認 |
| checkpoint-1 (09-24, n_floor 3) | N=2 < 3 → **TRIGGERED 見込み** | registry |
| checkpoint-2 (10-08, n_floor 6) | 現ペース (09-12 以降 0 行/日) では **TRIGGERED 見込み** | registry |
| first look (N≥41 or 2027-01-15) | 残 39 行 / 16.4 週 = **2.4 行/週** が必要 | §7 |

⚠️ 統計的な「異常」ではない点は据え置き (final_assessment: P(N≤2) ≈ 0.11)。本稿の結論は統計ではなく**機構の帰属**による。

---

## 2. 配線検査 — 仮説別の証拠と判定

| # | 仮説 | 証拠 | 判定 |
|---|---|---|---|
| A | **conf 単位バグ再発** (0-1 スケール → `conf<30` 全滅、09-10 kb-06 型) | `app.py:4525` `int(round(min(_score/2.5,1.0)*100))` (0-100)。実行 2 行の confidence 48 / 68。永続集計 11d (`/api/demo/block-counts?days=11`) の `rnb_usdjpy:conf<30` = **キーなし (0)**。`tests/test_rnb_confidence_scale.py` が pin | **反証** |
| A' | **`no_confirm` (✅ marker 欠落) 再発** | `app.py:4487-4491` で `✅ RNB support` / `✅ wick` / `✅ engulfing` 付与。ログの IN 行 `理由: ✅ RNB support 154.00 / ✅ wick 50%`。永続 11d に `no_confirm:rnb_support_bounce` **なし** | **反証** |
| B | **QUALIFIED_TYPES 落ち** (`unknown_type`) | `demo_trader.py:5758` に `"rnb_support_bounce"` 現存。永続 11d に `rnb_usdjpy:unknown_type:*` **なし**。`tests/test_rnb_block_reason_estimand.py` (登録ドリフト完全一致 pin) / `tests/test_rnb_shadow_only_registration.py::test_rnb_support_bounce_is_qualified` | **反証** |
| C | **shadow_only 配線落ち** (行が live 化 or write-path で落ちる) | `demo_trader.py:764` `"shadow_only": True`。2 行とも厳格 shadow。ログ `[SHADOW] Phase0 tier gate: rnb_support_bounce USD_JPY → shadow` → `OANDA: [SKIP] shadow_tracking` → `📥 IN`。`test_rnb_shadow_only_registration.py` 8 本が 3 点 block を pin | **反証** |
| D | **単に相場 setup 不在** | 修理後 active 窓で BUY bar **11 本** (§4)、うち 09-12 以降 **6 本** | **反証** — setup は出ている、行にならない |
| E | **エンジン/mode 停止** | `engine_tick_status ok`、`tick_counts["rnb_usdjpy"]=231` (06:01Z 再起動以降、他 30s モードと同水準)、`modes.rnb_usdjpy.running=true`、Render `[MainLoop/rnb_usdjpy] tick ## ok` 継続 | **反証** |
| **F** | **下流 live 保護 gate による hard block** (`mtf_strong_bias` / `velocity_down` / `1h_rr_low` / `same_price_3pip`) | §4–§6。永続 11d: mtf 9 / velocity 3 / rr 3 / same_price 1 (tick 件数)。09-12 以降の BUY bar **6/6** がこれで消滅 | **採択 — 真因** |
| G | 09-11 `session_hours` 211 件 (tz バグ疑い) | §5 — stale feed アーティファクト。tz 不整合ではない | **反証 (tz)** / **artifact と帰属** |

---

## 3. 配線の読み (コード参照、main 0e911f04)

- 発火経路: `rnb_usdjpy` (`demo_trader.py:746-765`、interval 30s、tf 15m、`active_hours_utc (7,20)`、`direction_filter BUY`、`shadow_only True`) → `_get_base_mode`="rnb" → `app.compute_rnb_signal` (`demo_trader.py:4308-4309`) → `_tick_entry` (`:4583`)。
- `compute_rnb_signal` の WAIT 経路 (`app.py:4401-4475`): bar 数不足 / **UTC 7–20 外 (bar index の hour、`:4407-4421`)** / range・ATR 0 / zone 外 / 上から接近でない / momentum 不足 / overshoot / rejection なし。BUY 時は `entry_type=rnb_support_bounce`、TP +20p / SL −15p (`:4393-4394`)。
- `_tick_entry` 内の rnb に効く gate (上流→下流順): `no_signal` (WAIT、`:5001-5003`) → `QUALIFIED_TYPES` (`:5758`) → conf gate → confirm gate → **`session_hours(outside_active)` (`:5289-5304`、wall-clock UTC; `_is_shadow_eligible_full` が偽なら hard block)** → **dedup 予約 `_maybe_reserve_order_bar_emit` (`:5506`、bar key = 形成中 bar の index、`:1263-1272`)** → `same_price_Npip` (`:5573`) → **`velocity_down` (`:6389`、base_mode "rnb" は辞書外 → 既定 8.0pip / 10 分、`:6355-6361`)** → **`mtf_strong_bias` (`:6421-6431`、15m tactical bias strength="strong" ∧ 方向逆 → block、免除は `trend_rebound` のみ)** → `_1H_PRESERVE_SLTP` (`:6449`) → **`1h_rr_low` (`:6552`、`tp_dist/sl_dist < 1.2`、免除は `hull_donchian_fade` のみ)** → order/shadow write。
- **`_is_shadow_eligible_full` (`:5073-5078`) は force_demoted / SCALP_SENTINEL / UNIVERSAL_SENTINEL / trendline_sweep_v2 のみ** — `shadow_only` mode は含まれない。∴ rnb は「shadow 迂回」経路を一つも持たず、上記 gate は全て **hard block** になる。packet §4 が `_UNIVERSAL_SENTINEL` 非追加を選んだ (minlot live 経路を開けないため) 副作用として、sentinel 型に付随する shadow 迂回も失っている。

---

## 4. 日別 funnel (永続 `gate_block_daily` を days=k 差分で日別化 + Render ログの bar 列挙)

出所: `/api/demo/block-counts?days=k&strategy=rnb_support_bounce` k=1..14 の差分 (`query_block_counts` は `day >= date('now','-k days')`、`modules/block_event_logger.py:291-293`)。単位は **tick 件数** (30s poll、bar 数ではない — endpoint docstring の estimand 警告どおり)。bar は Render ログ `[ORDER_BAR_DEDUP] ... bar_ts=` と `[MTF_MONITOR] ... entry=rnb_support_bounce` から列挙。

| 日 (UTC) | BUY bar (bar_ts) | 行 | 下流 block (tick) | dedup (tick) | session_hours (tick) |
|---|---|---:|---|---:|---:|
| 09-10 (修理デプロイ 16:49Z 以降 ~4h) | — | 0 | — | 0 | 0 |
| **09-11** | 09:00 / **10:30 (行)** / **11:30 (行)** / 12:45 / 20:45 (§5) | **2** | velocity_down 2 / same_price_3pip 1 / 1h_rr_low 1 / mtf_strong_bias 2 | 54 | **211** |
| 09-12, 09-13 | 週末 | 0 | — | 0 | 0 |
| 09-14 | 11:45 / 15:30 | 0 | velocity_down 1 / 1h_rr_low 2 | 3 | 0 |
| 09-15 | なし | 0 | — | 0 | 0 |
| 09-16 | 11:45 / 12:00 / 15:30 | 0 | mtf_strong_bias 5 | 45 | 0 |
| 09-17 | 07:00 | 0 | mtf_strong_bias 2 | 4 | 0 |
| 09-18 | なし | 0 | — | 0 | 0 |
| 09-19, 09-20 | 週末 | 0 | — | 0 | 0 |
| 09-21 | なし | 0 | — | 0 | 0 |
| 09-22 (〜08:4x) | なし | 0 | — | 0 | 0 |
| **計** | **11 bar** | **2** | **16 tick** | 106 | 211 |

- **全 11 bar の MTF_MONITOR 行が `mtf=trend_down_strong d1=-2 h4=-1 vol=expansion`** (09-11 09:03Z 〜 09-17 07:13Z、一貫)。
- ログ上、1 bar の初回評価が **~3 秒差で 2 本** (例: 09-16 12:03:44 / 12:03:47、09-11 10:42:07 / 10:42:44) 出る → 下流 block 16 tick ≈ block された 9 bar × ~2 評価と整合。`_tick_entry` の複数呼び出し経路 (`:4574` limit fill / `:4643` live_promote_emit) は rnb に該当しないため **二重評価の機構は未帰属** (§8 (iv))。件数を bar に換算するときは **×2 を割り戻す**。
- 09-11 10:30 bar は 10:42:07 評価 (MTF_MONITOR、下流 block) → 10:42:40 dedup → **10:42:44 に行生成** — 同一 bar で dedup 予約を 2 回通過した痕跡。DB の行重複は無い (bar ごとに 1 行) が、dedup 予約の key 一致性は別途確認対象 (§8 (iv))。

---

## 5. 09-11 `session_hours` 211 件の正体 — stale feed アーティファクト (tz バグではない)

- 構造: `compute_rnb_signal` の時間 filter は **bar index の hour** (`app.py:4409-4412`)、`_tick_entry` の `session_hours` は **wall-clock UTC** (`demo_trader.py:5293-5296`)。両者は本来同じ 7–20 UTC 窓 (`_active_hours[0] <= hour <= _active_hours[1]` = 14 時間) で、bar が新鮮なら `session_hours` は到達不能。**到達した = bar index の hour と wall-clock が乖離した時間帯があった**。
- 実測 (Render `[DemoTrader/rnb_usdjpy] fetched N bars`、09-11): 19:32Z 4398 → 19:57Z 4399 → 20:01Z 4400 → 20:26Z 4401 → **20:54Z 4403 → 20:58Z 4403 → 21:23Z 4403 → 21:26Z 4403 → 21:51Z 4403 → 21:54Z 4403**。15m 足なら 60 分で +4 本のはずが **0 本 = feed が ≥60 分 stale**。
- 帰結: 最終 bar (20:45 bar、hour=20 で signal 側 filter を通過、かつ BUY setup) を 21 時台に 30s ごと再評価 → wall-clock hour=21 で `session_hours(outside_active)` hard block (`_is_shadow_eligible_full` 偽)。211 tick ≈ 105 分 ≈ 21:00Z〜22:45Z 前後。同 bar の 20:54–20:59Z の評価は dedup (09-11 dedup 54 の一部)。
- **tz 仮説 (index が London/JST) は棄却**: 乖離が 09-11 の 1 夜だけで、09-14〜09-22 の全 bar_ts (`bar_ts=...T07:00:00+00:00` 等) は UTC 表記で wall-clock と整合。恒常的 tz ズレなら毎日出る。
- 実 setup の損失: **0** (20:45 bar は 20:4x〜20:5x に in-window で評価済み、下流 block)。ただし **「fetched bars が市場時間中に伸びない」を検知する読み手は無い** (freshness_policy の tick/candidate/trade 鮮度とは別の estimand、MEMORY `project_engine_tick_liveness_2026_08_28` の階層で言えば「データ鮮度」層) → §8 (iii)。

---

## 6. 09-12 以降の行ゼロの帰属 — live 保護 gate の構造的衝突 (ps 席 `spread_wide` と同型)

| gate | コード | rnb との衝突 | 09-11〜22 実測 |
|---|---|---|---|
| `mtf_strong_bias` | `:6421-6431` — 15m tactical bias `strength=="strong"` ∧ signal≠bias 方向 → block。免除 `trend_rebound` のみ、shadow 迂回なし | RNB = 下落後の支持線反発 BUY。USD/JPY が `trend_down_strong` (D1 −2 / H4 −1、全 11 bar で一貫) の間は **BUY setup が出るたび block** — gate 条件と entry 条件が同じレジームで同時成立する | 09-11 2 / 09-16 5 / 09-17 2 (tick)。09-16・09-17 の 4 bar は全てこれ |
| `velocity_down` | `:6355-6389` — 直近 10 分 (base_mode "rnb" は窓辞書外 → 既定 10 分) の下落 ≥ **8.0 pip** (閾値辞書外 → 既定) ∧ BUY → block、shadow 迂回は `_is_shadow_eligible_full` のみ | RNB の entry 条件 = 5 本 (75 分) で ≥0.5×ATR 下落 + 支持線到達。速い dip は 10 分 8p を容易に超える → **「dip を買う」戦略を「落ちている最中は買うな」gate が殺す** | 09-11 2 / 09-14 1 |
| `1h_rr_low` | `:6549-6552` — `_1H_PRESERVE_SLTP` (rnb 含む) で TP/SL を signal 値のまま保存し、`tp_dist/sl_dist < 1.2` → block。免除 `hull_donchian_fade` のみ | 設計 RR = 20/15 = **1.33**、床 1.2 との差は **1 pip 分の余裕** (current_price が signal close より +1.0p 上なら 19/16 = 1.19 → block)。`current_price` は OANDA bid/ask (`:4900-4909`) で bar close と数 pip ズレうる = ナイフエッジ | 09-11 1 / 09-14 2 |
| `same_price_3pip` | `:5573` | 同値近傍の再エントリー抑止 (副次) | 09-11 1 |

- **BT⇄live 非同期**: 365d ablated BT (packet §3、`raw/session-scripts/rnb-support-bounce-ablated-bt-2026-09-10.py`) は `compute_rnb_signal` のみで走り、上記 4 gate を適用していない。∴ live shadow 母集団 = 「RNB ∩ ¬strong_bias ∩ ¬velocity ∩ RR≥1.2」で、BT の 2.99/週 (setup 頻度) は **行頻度の前提として成立しない**。LOCK の estimand (forward shadow rows) 自体は不変だが、**cadence 前提 (packet §6「頻度前提の検証」) は下方修正が必要**。
- 4 原則との整合: 原則 3 の「静的時間ブロック」ではないが、原則 4 (防御フィルターの積み上げより蓄積) と `shadow_only` の設計意図 (OANDA 送信は構造的にゼロ = live 資本リスクなし) に対して、live 保護 gate が shadow 分母を削っている。sentinel 型には shadow 迂回 (`[SHADOW] velocity_down bypass` 等) が用意されているのに、`shadow_only` mode には無い — **非対称**。

---

## 7. 頻度前提の再評価 (件数のみ)

- 修理デプロイ後の active 窓被覆: 09-10 4h + 営業日 7 日 (09-11, 14–18, 21) × 14h + 09-22 ~1.7h ≈ **103.7 active-h ≈ 1.48 週** (5 営業日 × 14h = 70h/週)。
- setup 供給 (forming-bar、in-window BUY bar): **11 / 1.48 週 = 7.4 bar/週** vs 確定足 BT 2.99/週 — forming-bar 評価の一時的 BUY を含むため上振れは想定内 (MEMORY `project_ps_capture_estimand_disjoint_2026_09_09` と同型、bar 数を BT setup 数と同一視しない)。**供給側は枯れていない**。
- 変換 (bar → 行): **2/11**、09-12 以降 **0/6**。全て `trend_down_strong` 下。
- first look 到達条件: 残 39 行 / 16.4 週 = **2.4 行/週**。現在の変換率 (0/6、直近 7 営業日) が続けば **2027-01-15 の stale 分岐 (N≪41) が既定路線**。レジームが `strong` を外れれば `mtf_strong_bias` は消えるが、`velocity_down` / `1h_rr_low` の構造衝突はレジーム非依存で残る。
- **下方修正案 (修理しない場合)**: checkpoint-2 (10-08) の n_floor 6 は現ペースで TRIGGERED 確定。「期待 2.99/週の半分」基準は setup 頻度を行頻度に流用した前提の誤りなので、**cadence 期待値を「setup 頻度 × gate 通過率 (レジーム条件付き)」に書き換え**、通過率は本稿の日別 funnel を初期値 (2/11) として 10-08 に再計測する。これは outcome 非接触の件数指標のまま維持できる。

---

## 8. 09-24 TRIGGERED 時の disposition 案 (本 PR は docs のみ、code は触らない)

**(i) R3 修理候補 — `shadow_only` mode の live 保護 gate を shadow 迂回に振り替える (推奨)**
- 変更点 (最小): `demo_trader.py:5073-5077` `_is_shadow_eligible_full` に `or _mode_is_shadow_only(mode)` を加える。これで `session_hours` (`:5297-5303`) / `velocity_down` (`:6382-6389`) の既存 shadow 迂回が rnb に効く。`mtf_strong_bias` (`:6431`) と `1h_rr_low` (`:6552`) は迂回分岐を持たないため、`shadow_only` mode では `_is_shadow=True` に落として続行する分岐を追加する (hard block → shadow 化)。
- 根拠: `shadow_only` は OANDA 送信を 3 点 block で構造保証 (`test_rnb_shadow_only_registration.py`) しており、live 保護 gate が守るべき資本が存在しない。BT⇄live 母集団を揃える方向 (CLAUDE.md 同期原則) でもある。
- **やらないこと**: `_UNIVERSAL_SENTINEL` への追加 (minlot live 経路が開く、packet §4)。gate 閾値 (8.0pip / RR 1.2 / strength) の変更 (他戦略に波及)。`compute_rnb_signal` のパラメータ変更 (カーブフィッティング禁止)。
- **pin (同 commit 必須)**: (a) rnb BUY が `strength=strong` 逆方向 / 10 分 −8pip / RR 1.19 の各 counterfactual で **shadow 行になる**こと、(b) 同じ入力で非 shadow_only mode は従来どおり block されること (対称側、MEMORY `feedback_check_the_symmetric_side_2026_09_19`)、(c) OANDA 送信ゼロが不変 (既存 8 本)、(d) stale bar (hour=20 bar を 21 時台に評価) が **行にならない**こと — `session_hours` 迂回を rnb に開くと §5 型の stale bar が shadow 行になり得るため、迂回条件に「bar 鮮度 (bar_ts と now の差 ≤ 2×tf)」を要求する。
- **LOCK への影響**: estimand (forward shadow rows) は不変だが母集団の gate 構成が変わるため、**registry `rnb-support-bounce-shadow-forward` の message に amendment 追記** (修理デプロイ日、変更前 N=2、変更内容) が必要 — S7 経由。first look 時は N=2 (旧 gate 構成) を除外するか層別する判断を **事前に**書く (中間再計算は行わない)。

**(ii) 修理しない場合 — 頻度前提の下方修正** (§7): checkpoint-2 の判定基準を「setup 頻度 × 通過率」型に書き換え、LOCK の 2027-01-15 stale 分岐が既定路線であることを registry message に明記。

**(iii) データ鮮度の読み手 (別 R3、rnb 非固有)**: 市場時間中に `fetched N bars` が 2×tf 以上伸びないモードを検知 (engine_tick とは別 estimand)。09-11 20:54Z〜21:54Z+ の 60 分凍結は現行の読み手 (tick / candidate / trade 鮮度) では見えない。

**(iv) 件数整合の確認 (別 R3、低優先)**: 1 bar の初回評価が ~3 秒差で 2 本出る機構 (`_tick_entry` 二重呼び出し or mode スレッド二重化 — StatusHeal `Mode not running — restarting` `:2066` 起点の可能性) と、09-11 10:30 bar で dedup 予約を 2 回通過した痕跡の帰属。行の重複は無いが、block tick 件数の bar 換算 (×2) と DB 負荷 (09-22 §H HTTP 盲目の背景) に関わる。

---

## 9. 引用規律・注意

- 本稿の N (2) は LOCK と同一母集団の件数で、outcome は一切含まない。WR / EV / PnL / close_reason は計算も閲覧もしていない。
- 「2.99/週」は確定足 setup 頻度であり行頻度ではない。「7.4 bar/週」は forming-bar 評価の BUY bar 数であり setup 数でも行数でもない。両者を混ぜて引用しない。
- block 件数は tick 単位 (30s poll、~2 評価/周期の痕跡あり)。bar 数・setup 数として引用しない。
- `session_hours` 211 件は「時間 filter が shadow を削った」証拠として引用しない (stale feed アーティファクト、§5)。
- 09-05 分析の予測 1 (`direction_filter` 恒久 0) は本窓でも成立 (永続 11d にキーなし)。

## 10. 出所

- 本番 API: `GET /api/demo/status` (block_counts / tick_counts / modes、2026-09-22 08:4x UTC)、`GET /api/demo/block-counts?days=1..14&strategy=rnb_support_bounce`
- Render app ログ (workspace tea-d6va0dia214c7386glv0 / srv-d6va1of5r7bs73en10vg): text `rnb_support_bounce` 2026-09-10〜09-22 (2 ページ、hasMore=false)、text `DemoTrader/rnb_usdjpy` 2026-09-11T19:30Z〜09-12T00:30Z
- scratchpad `trades.json` (2,002 行、2026-08-18〜09-22)、`block_counts_11d.json`
- code: `modules/demo_trader.py` (746-765, 1263-1272, 4292-4296, 4308-4309, 4574/4583/4643, 4900-4909, 5001-5003, 5073-5078, 5289-5304, 5506, 5573, 5758, 6355-6389, 6421-6431, 6449, 6549-6552, 2066) / `app.py` (4358-4527) / `modules/block_event_logger.py` (270-330) — main 0e911f04
