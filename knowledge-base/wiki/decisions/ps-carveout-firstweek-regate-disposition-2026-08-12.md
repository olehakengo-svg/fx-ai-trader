# price_shock_rev carve-out 復帰初週 再ゲート — disposition (2026-08-12)

**rule**: R3 (監視・診断の決着。live パラメータ / tier / lot は**一切不変更**)
**トリガー**: registry `ps-carveout-firstweek-regate` (期日 2026-08-11 超過 = stale 点灯)
**親決裁**: [[track-c-capital-plumbing-decision-packet-2026-07-28]] D-c-1 (ps×5 carve-out + BE_LOCK OFF、user 承認 2026-07-28)
**判定**: **demote しない** (pre-reg 条件 live N≥10 が未達 — 実測 N=2)。初週窓は **PR #172 デプロイ後へ再アンカー**。

---

## 1. 事実 (本番実測、2026-08-12)

`/api/demo/trades` の `date_from=2026-07-28` 全ページ (1,427 行) から price_shock_rev を抽出:

| 指標 | 実測 |
|---|---|
| ps 行 (全経路) | **8** (全て `price_shock_rev_aud_jpy_h1_long` / AUD_JPY / BUY) |
| うち clean live (`oanda_trade_id != ''` ∧ `dedup_violation != 1`) | **2** |
| うち shadow | 6 |
| 他 4 セル (EUR_GBP / NZD_JPY 等) の発火 | **0** |

clean live 2 件の内訳:

| entry_time (UTC) | outcome | pnl_pips | close_reason |
|---|---|---|---|
| 2026-07-29T04:44 | WIN | **+0.6** | horizon |
| 2026-07-31T08:57 | LOSS | **−123.2** | horizon |

累計 **−122.6p / N=2 (mean −61.3 p/t)**。

## 2. 再ゲート 3 項目の監査結果

### (a) AGG_KELLY BYPASS ログ実確認 → **carve-out は機能。ただし初週の律速は agg-Kelly ではなく席**

- Render app ログ (2026-07-29〜08-01、`text=BYPASS`) に **AGG_KELLY 起因の block は 1 件も無い**。
- 代わりに支配的なのは席 (slot) による shadow 迂回:
  `[DemoTrader] [SHADOW] Slot bypass: price_shock_rev_aud_jpy_h1_long daytrade_1h_audjpy/AUD_JPY (live=1/1 shadow=1/2 → shadow)`
  が 07-31 20:44〜20:56 の 13 分間だけで **16 行** — **live 席が 1/1 で埋まっており ps は shadow へ落とされていた**。
- clean live が 2 件成立している事実自体が「carve-out 経路は通る」の行動証拠。**初週の N 不足は carve-out の失敗ではなく席供給の枯渇**。
- 席供給は **PR #172「price_shock_rev 席供給の是正 — 席優先 select + live feed MASSIVE 統一 + SCORE_GATE ミラー」(merged 2026-08-11T08:24Z)** で是正済み。
  → **初週ゲートの評価窓は #172 デプロイ後へ再アンカーする** (それ以前の窓は「席が無い」という別要因で汚染されており、carve-out の EV を測る窓として無効)。

### (b) exit 分布が horizon 系か (BE_LOCK OFF の実効性) → ✅ **確認**

clean live 2 件の `close_reason` は**両方 `horizon`**。BE_LOCK / ATR-BE / trail による早期 exit は観測されず、
D-c-1 で決裁した「BE_LOCK OFF」が live で実効。**N=2 なので「分布」ではなく「2/2 一致」の水準の証拠**である点は明記する。

> 注 (MEMORY `project_sl_hit_label_collision_2026_08_07`): `close_reason` 起点の分析は `outcome` 分割が必須。
> 本件は 2 件とも `horizon` で `SL_HIT` ラベル衝突の影響圏外。

### (c) watchdog / promote evaluator の estimand 整合 → ⚠️ **潜在的不整合。現時点の実データでは影響ゼロ**

| ツール | live 判定 | dedup 除外 | 発動条件 |
|---|---|---|---|
| `tools/price_shock_rev_live_watchdog.py` | `is_shadow == 0` | **無し** | N≥10 ∧ (EV<0 ∨ Wilson_lo<0.40) → auto DEMOTE state file |
| `tools/price_shock_rev_promote_evaluator.py` | `is_shadow == 0` | **無し** | N≥30 ∧ Wilson_lo≥0.50 → lot ramp 提案 |

- KB 規約 (MEMORY `feedback_live_vs_shadow_strict_separation` / 教訓「`oanda_trade_id IS NOT NULL` で集計するのが正しい live 判定」) に対し、
  両ツールは **非 canonical な単一列 `is_shadow=0`** を使い、`dedup_violation` 除外も持たない。
- **ただし実測での乖離はゼロ**: 2026-06-01 以降 7,761 行で `is_shadow=0 ∧ oanda_trade_id 空` = **0 件**
  (has-oanda_trade_id = 151 件)。ps 行 19 件の内訳も `(is_shadow=1, oid無, dv=0) 15 / (0, oid有, 0) 2 / (1, oid無, dv=1) 2` で、
  **dedup_violation=1 は shadow 側のみ** = live 二重計上も現時点で無い。
- 結論: **現在の判定は汚染されていない。バグとして起票しない**。ただし 2 列は歴史的に乖離した実績があるため
  (SL_HIT ラベル衝突 / 二重列 UPDATE 欠落の教訓)、canonical 判定 (`oanda_trade_id != ''` ∧ `dedup_violation != 1`) への
  ハードニングを**別タスクへ queue** する (防御的、期日圧なし)。auto-demote を握るツールなので変更は単独 PR + test pin で行う。

## 3. 判定と根拠

- **R2 demote は発動しない** — pre-reg 条件は「live N≥10 ∧ EV<−0.5p」であり実測 **N=2**。
  N=2 の mean −61.3p は 1 件の −123.2p に完全に支配されており、統計的主張にならない
  (教訓「1 日データで対策実装は禁止」/ lesson-reactive-changes)。**pre-reg の N ゲートを事後に下げることはしない**。
- **downside は既に有界** — lot 1000u + watchdog auto-demote (N≥10) + disaster SL。−123.2p は
  ロット階段 L1 の想定内 (MEMORY `project_lot_ladder_template_frozen_2026_08_05`: wg binding = disaster SL 150p)。
- **初週ゲートは「未達」ではなく「窓が無効」** — 席枯渇 (live=1/1) により carve-out の EV を測れる窓が
  存在しなかった。#172 後の窓で測り直すのが正しい estimand。

## 4. 執行内容 (本 PR)

1. registry `ps-carveout-firstweek-regate` を **resolved** 化 (本 disposition を resolution に記録)
2. 後継エントリ **`ps-carveout-regate-post-172`** を新設 — #172 デプロイ後窓での再ゲート:
   - `type: live_count_decision` (entry_type 前方一致 `price_shock_rev`、since **2026-08-11**)
   - live N≥10 到達で EV / Wilson_lo を再判定 (EV<−0.5p なら R2 demote)、backstop 期日 **2026-09-30**
   - 期日到達で N<10 なら「席供給が是正されても発火しない」= 供給側の別問題として stale レビュー
3. 本 doc + changelog + registry を同一コミット

## 5. M1 への寄与

Track C の主張は「ps×5 が発火可能になれば live N 蓄積が桁で加速し M1 の統計確認が前倒しされる」。
本監査は **その前提が初週には成立していなかった (席枯渇で 8 発火中 live 2)** ことを実測で確定し、
#172 後の窓に測定を再アンカーした。**M1 の見通しは変えない** (依然 wg + ps の live N 蓄積待ち)。

## 関連

- [[track-c-capital-plumbing-decision-packet-2026-07-28]] (親決裁 D-c-1)
- [[shortest-path-decision-memo-2026-07-10]] (トラック C)
- MEMORY: `project_preserve_bug_fixed_10cells_live_2026_07_28` / `project_track_c_carveout_gap_and_gotobi_2026_07_28` / `project_549250_incident_mc_ruin_fix_2026_08_05`

---

## 6. 後継 `ps-carveout-regate-post-172` 期日前 readout (2026-09-29、期日 09-30 の 1 日前)

**rule**: R3 (件数の記録と帰属のみ。gate / tier / lot / 閾値 / live 経路は**一切不変更**)
**判定 (暫定、09-30 checkpoint で確定)**: **N<10 のまま期日を迎える見込み = stale。carve-out の EV 判定は保留** (pre-reg どおり、N ゲートは下げない)。entry は resolve しない。期日 09-30 は**動かさない** — 本節は as-of 09-29T01:20Z の**期日前 readout**であり、09-30 checkpoint 到達後に N を数え直してから 10-30 へ roll する (§6.3)。
EV / WR / PnL は本節で計算・転記していない — N≥10 到達時の判定 look を消費しないため。

### 6.1 事実 (本番 `/api/demo/trades`、as-of 2026-09-29T01:20Z)

`status=closed&date_from=2026-08-11` 全ページ (2,980 行、offset 500 刻み) + `status=open` (2 行) から
`entry_type` 前方一致 `price_shock_rev` を抽出:

| 区分 | 件数 |
|---|---|
| ps 行 (全経路) | **7** |
| clean live (`oanda_trade_id != ''` ∧ `dedup_violation != 1`) | **6** (eur_gbp 4 / aud_jpy 2) |
| shadow | 1 (eur_gbp、08-17) |
| 他 3 席 (NZD_JPY / EUR_AUD / USD_CAD) | **0** |
| 最終 ps 行 | **2026-09-03T15:08Z** (以後 26 日間 row ゼロ、live・shadow とも) |

- watchdog (`tools/price_shock_rev_live_watchdog.py`、`is_shadow=0` 基準) でも 6 件全て `is_shadow=0` = canonical 定義と一致 (§2(c) の乖離は本窓でも 0)。
- ⚠️ **訂正**: 2026-09-26 / 09-28 session log の未解決欄にあった「clean live N since 08-11 = 0 (09-26 実測)」は**誤り**。
  09-10 の [[trigger-watch-gap-audit-2026-09-10]] は N=6/10 と記録しており、本実測 N=6 と一致する (09-03 以降 増分ゼロ)。

### 6.2 帰属 — 「席が是正されても発火しない」の中身は **送信前 gate (下流) 100%**

[[ps-seat-supply-remeasure-2026-09-10]] §11 (09-21、窓 09-07〜09-21) で「5 席の候補 141 行 = distinct bar 10 本が全て order 層到達前に block、
席優先 select は 141/141 勝ち」= **(B) 下流で確定**済み。その後の窓を 2 面で追認した:

**(a) Render ログ `[ORDER_BAR_DEDUP] first terminal block after reservation: price_shock_rev*`** (marker は PR #293 = 09-23 以降のみ存在、窓 09-23〜09-29T01:30Z、hasMore=false):
distinct (seat, bar_ts) **11 本すべて block、order 送信 0**。

| 終端 gate | distinct bar | 席 |
|---|---|---|
| `spread_wide` @ 21:00Z ロールオーバー | 5 | usd_cad ×2 (1.9 / 2.2p > 1.5) / eur_aud ×3 (19.7 / 18.5 / 8.4p > 2.0) |
| `spread_wide` @ 08:00Z | 1 | nzd_jpy (3.0 / 3.3p > 3.0) |
| `mtf_strong_bias` (SELL vs BUY) | 3 | eur_gbp (09-28 07/08/13 時台) |
| `velocity_down` (44〜49p) | 2 | aud_jpy (09-25 13 時 / 09-28 08 時) |

(同一 bar の first terminal 行が別 instance で 2 回出るのは二重エンジン — [[dual-engine-dup-rate-readout-2026-09-24]]。数えるのは distinct bar)

**(b) `/api/demo/block-counts?days=28` の `persisted.per_cell_metrics`** (magnitude、per-tick 計上で bar 単位ではない):
aud_jpy velocity_down n=6 (44〜49p) / eur_aud spread_wide n=6 (3.5〜35.4p、mean 14.9) / usd_cad spread_wide n=7 (1.9〜11.6p) /
nzd_jpy spread_wide n=3 (3.0〜3.3p) / eur_gbp spread_wide n=1 (1.6p)。magnitude の disposition は registry `ps-seat-spread-magnitude-readout` (10-19) が持つ — **本節では判定しない**。

**読み**: 「席」は是正後も一度も律速していない。N が 10 に届かない理由は **シグナル後段の防御 gate** であり、carve-out (agg-Kelly bypass) の成否とは独立。
spread_wide の 21:00Z 分 (5/11) は原則 2 (デスゾーン = スプレッド異常の動的検出) どおりの正当な防御で、緩める対象ではない。
`mtf_strong_bias` / `velocity_down` (5/11) は block されると **shadow row も書かれない** (shadow N も同時に死ぬ) — rnb レーンで同型を shadow 化した前例
([[rnb-shadow-lane-health-precheck-2026-09-22]] → PR #290 の `[SHADOW_RELAX]` レーン) があるが、ps への汎用化は **Rule 1** (新フィルタ緩和・母集団変更) であり autopilot では執行しない。

### 6.3 閉じ方と残る防御

- registry `ps-carveout-regate-post-172` は **resolve しない・期日 09-30 は据え置き** (期日前 readout を message に追記)。`evaluate_live_count_decision` は `today >= deadline` で発火するので、
  1 日前に roll すると 09-30 checkpoint が発火せず、残り窓の fill が N=6 の結論から漏れる (PR #306 Codex P2)。**09-30 以降のセッションで 09-29T01:20Z 以降の増分を数え直し、N<10 なら 10-30 へ roll** する。
  理由: 本 entry は cell_deepdive の LOCK redaction 母集団 (`match=prefix`) を定義しており、resolve すると保留中の EV look が deepdive 出力に露出する
  (`tests/test_cell_deepdive_lock_redaction.py::test_real_registry_preserves_prefix_match_flags` が初版の resolve で落ちて検知)。
  10-30 の再レビューは `ps-seat-spread-magnitude-readout` (10-19) の disposition を受けて決める (退役なら resolved / 継続なら N≥10 待ちで再 roll)。
- ⚠️ **watchdog は本 entry の R2 条件の代替ではない** (PR #306 Codex P2): `tools/price_shock_rev_live_watchdog.py --apply` (Render cron、render.yaml:283) は
  **exact セル単位** × **全期間** × `is_shadow=0` で N≥10 を数える。本 entry は **prefix プール** × **since 08-11** × canonical (`oanda_trade_id` ∧ dedup) で数える。
  例: プール N=10 が複数セルに分散すればどのセルも watchdog に掛からない / 08-11 以前の行で watchdog だけが別母集団で発火しうる。
  ⇒ **プール条件 (N≥10 ∧ EV<−0.5p → R2 demote) を執行するのは本 entry だけ** — これも resolve しない理由の一つ (redaction と並ぶ)。
  (registry 側の EV<−0.5p と watchdog の EV<0 は watchdog の方が厳しい = 保護側に倒れている)
- 供給側の次の決裁点 = `ps-seat-spread-magnitude-readout` (10-19)。mtf/velocity の shadow 化は R1 候補として記録のみ (起案は user 決裁の統合パケット経由)。
- M1 への寄与: ps 席からの live N 供給は **09-03 以降ゼロ**。M1 見通しの供給源に ps を数えない (wg は G0' 終了・W1 決裁待ち、kalman / carry_dip が現行の live 供給)。
