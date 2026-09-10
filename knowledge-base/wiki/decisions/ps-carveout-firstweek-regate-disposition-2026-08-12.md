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
