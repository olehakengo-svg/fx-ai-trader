# E2_SILENT 4 セルの判別 — 「4 セル沈黙」は 2 セルの配線落ち + 2 セルの窓アーティファクトだった (2026-09-10)

**rule**: R3 (診断のみ。live コード変更なし)
**対象 registry**: `roster-e2-silent-promoted-cells` (期日 2026-10-06)
**手法**: [[rnb-dead-mode-and-block-estimand-2026-09-05]] と同じコードトレース (auto_start / QUALIFIED_TYPES / エンジン配線 / gate 経路) + 本番 API 実測 (`/api/demo/trades` mode×期間 filter、read-only)
**関連**: [[live-roster-attrition-2026-09-06]] §3.2 / MEMORY `project_candidate_gap_readout_window_ceiling_2026_09_01` (窓天井) / `project_roster_d_class_estimand_audit_2026_09_10` (クラス名が estimand を運ぶ)

---

## 0. 要約

registry の前提「4 セルとも 2026-05-06 以降 LIVE/shadow 行ゼロ」は**本番 DB 実測で 4 セル中 2 セルについて偽**。正しい分類:

| cell | 分類 | 一言 |
|---|---|---|
| `bb_squeeze_breakout × EUR_USD × BUY` | **配線落ち** (commit 942e3800、2026-05-06) | v2 評価器が live 呼び出し規約で構造的 None — 前提通り 05-06 12:45 が最終行 |
| `bb_squeeze_breakout × EUR_USD × SELL` | **配線落ち** (同上) | 同一評価器 |
| `ema200_trend_reversal × USD_JPY × SELL` | **シグナル未発生 (E2 分類は premise 誤り)** | SELL 19 行が 05-08〜08-05 に実在。沈黙は attrition tool の 30d 窓アーティファクト + PR #168 hour gate 実効化 |
| `squeeze_release_momentum × GBP_USD × BUY` | **シグナル未発生 (E2 分類は premise 誤り)** | 51 行が 05-20〜08-31 に実在 (BUY 最終 08-07)。同じく窓アーティファクト + PR #168 |

「意図的無効 (決裁による停止)」に該当するセルは **0 件** — 4 セルとも SHADOW_RETIRED_STRATEGIES / SHADOW_DEMOTED_CELLS / FORCE_DEMOTED いずれにも入っていない (コード確認済み)。

---

## 1. 前提の実測検証 — registry の一般化は 2/4 で偽

本番 API (`/api/demo/trades?mode=X&date_from=2026-05-01`) の実測:

| cell | 05-01 以降の行 | 最終行 | attrition tool (30d 窓) |
|---|---:|---|---|
| bb_squeeze×EUR_USD (両方向) | scalp_eur 9 行 + scalp_5m_eur 1 行、**全て ≤2026-05-06 12:45** | 2026-05-06 12:45 (shadow SELL) | 0 ✓ (真の沈黙) |
| ema200×USD_JPY×SELL | **19 行** (05-08〜08-05、shadow) | 2026-08-05 19:33 | 0 (窓が 08-11 開始のため) |
| ema200×USD_JPY×BUY (参考) | 58 行、直近 08-31 12:17 | — | 5 行 |
| SRM×GBP_USD×BUY | **31 行** (05-22〜08-07、shadow) | 2026-08-07 04:33 | 0 (窓外) |
| SRM×GBP_USD×SELL (参考) | 20 行、直近 08-31 07:02 | — | 1 行 |

**教訓 (窓天井の再発)**: `tools/live_roster_attrition.py` の `current_rows_any` は **30d 窓**の量。registry message はこれを「2026-05-06 以降ゼロ」と読み替えて一般化した — 「現在形の集合で過去形の主張をする」型 (09-10 D クラス監査と同型) + 「窓が狭くて問いに答えられない」型 (09-01 readout 教訓と同型) の複合。E2_SILENT というクラス名が「05-06 以来沈黙」という estimand を運んでしまった。

---

## 2. bb_squeeze_breakout × EUR_USD (BUY/SELL) — 配線落ち、3 層構造

### 2.1 断定根拠 (env 実値なしで p≈1)

- 最終行 2026-05-06 12:45 UTC。**同日 06:18 UTC に w4-shadow-redesign-v2-squeeze (commit `942e3800`) が main 到達** — v2 化コードのデプロイ + env 設定 (同日午後) と行停止が分単位で一致
- 直前 6 日 (05-01〜05-06) に 9 行 ≈1.5 行/日 のペースが、以後 **127 日間 0 行**。「env 未設定で v1 が生きている」仮説の下では Poisson P(0) ≈ e^(−190) — 棄却
- 同じ w4/wave の env が本番設定済みだった前例 2 件: SR family 6 lever=1 ([[../decisions/sr-family-render-env-audit-2026-06-02]])、BB_RSI lever=1 ([[../decisions/edge-cell-e1-e4-code-disable-2026-07-02]] 2026-07-03 検証)
- ⇒ **SQUEEZE_REDESIGN_V2=1 が本番に設定され、v1 経路は死んでいる**と判定 (最終確認手段は §2.4)

### 2.2 配線落ちの 3 層 (コード確定)

`strategies/scalp/squeeze.py` `_evaluate_v2` (commit 942e3800 由来):

1. **live 恒久 None**: `if not ctx.backtest_mode and ctx.bar_time is None: return None`。live のシグナル呼び出しは `compute_fn(df, tf, sr, symbol)` (`modules/demo_trader.py` _tick) = **bar_time は常に None、backtest_mode は常に False** → v2 は live で候補を 1 件も返せない。タスク仕様 ([.ai/tasks/done/20260505-1947]) は「shadow で実測する」ことが目的 (`INSUFFICIENT_BT_EVIDENCE → shadow promote`) なのに、**実測するはずの live 経路で評価器自体が常時 None = 目的と配線の矛盾**。同 wave でも xs_momentum / macd_rsi_pullback 等は `bar_time is None なら df.index[-1] を使う` fallback を実装しており (rows 実在)、squeeze (と stoch/ema_pullback/ema_ribbon/dt_fib 等の hard-guard 組) だけが live-dead
2. **✅ 欠落**: v2 の reasons に "✅" が 1 つもない (v1 と stoch v2 は ✅ あり)。仮に発火して select_best に勝っても `_tick_entry` の QUALIFIED gate `no_confirm:bb_squeeze_breakout` で live/shadow とも死ぬ
3. **loser-shadow 経路も不達**: `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` による shadow_emit 対象化は評価器が None を返すため永遠に候補が来ない

### 2.3 「意図的無効」ではない証拠

- ×EUR_USD は 2026-05-07 volume emergency で _PAIR_DEMOTED から**外され** (= 有効化方向)、_PAIR_PROMOTED に現役登録 (`modules/demo_trader.py` L9196)。wiki Current Portfolio にも現役掲載
- 停止を指示した decision doc は存在しない (decisions/ 全文検索)。v2 設計文書はむしろ shadow promote を推奨 (verdict `INSUFFICIENT_BT_EVIDENCE` → `RECOMMEND_SHADOW`)

### 2.4 処分案 (執行しない — 提案のみ)

- **R3 修復案**: `_evaluate_v2` に `bar_time is None → df.index[-1]` fallback (xs_momentum idiom) + reasons に ✅ 1 本追加。挙動追加は shadow 行の発生のみ (365d BT で EUR_USD は N<20 = 低頻度)。修復 PR には counterfactual テスト (fallback を消すと落ちる) を併設
- **代替案 (v2 実験放棄)**: env 2 lever 削除 + _PAIR_PROMOTED から除去 + wiki 掲載除去 (= 意図的無効を正式化)。**どちらを選ぶかは user 決裁** — 128 日間観測ゼロの実験を再開する価値 vs 掲載と実態の乖離解消
- env 実値の最終確認は `render ssh srv-d6va1of5r7bs73en10vg` + `printenv | grep SQUEEZE` (commander 手順、[[../decisions/bb-rsi-redesign-v2-lever-removal-blocked-2026-07-03]] 前例)。本セッションは権限外 (classifier deny) で未実施

## 3. ema200_trend_reversal × USD_JPY × SELL — シグナル未発生 (設計整合)

- 配線は生存: BUY が 30d 窓でも 5 行 (08-12/08-13/08-31、全て hour 12-13 UTC)。SELL も 05-08〜08-05 に 19 行
- **頻度低下の主因は PR #168 (2026-08-09) の ctx.hour_utc 凍結修復**: 旧 live は hour が定数 12 に凍結 → `EMA200_TREND_REVERSAL_REDESIGN_V2` の 12-16 UTC gate も SRM の 7-17 gate も**素通り**だった。修復後は実時刻 gate が効き、発火窓が 24h→4h に縮小 (これは v2 lever の意図された設計。post-fix の BUY 3 行が全て 12-16 内であることが lever=1 の稼働証拠)
- SELL 固有の沈黙: SELL 条件 = `not bull200` + 直近 5 バー内 EMA200 下抜けクロス + 価格が EMA200 直下 (−0.5ATR<dist<0) + macdh 下向き + rsi>45、かつ 12-16 UTC 限定。USD_JPY の 2026 夏の上昇 regime (152→161) では 12-16 UTC の bear-retest 成立が稀 — **市場条件由来で設計と整合**
- anchor N=1 (live 通算 1 行) のセル — 元々ほぼ発火しないセルであり、「沈黙」は異常シグナルではない
- 処分案: E2 → **E1 (supply present)** へ再分類。追加アクション不要 (09-02 の [[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 2 で live 化候補としては既に死亡確定済み)

## 4. squeeze_release_momentum × GBP_USD × BUY — シグナル未発生 (窓アーティファクト)

- 配線は生存: 05-20〜08-31 に GBP_USD で 51 行 (BUY 31 / SELL 20、全 shadow、mode daytrade_gbpusd)。EUR_USD 側も 30d で 8 行
- BUY 最終 08-07 04:33 → attrition 30d 窓 (08-11 開始) の直前 = **窓アーティファクト**
- 頻度低下も PR #168 と整合: pre-fix の行は 00:00/21:46/04:33 UTC など **ACTIVE_HOURS 7-17 外が多数** (hour 凍結 12 で gate 素通りしていた)。修復後は 7-17 実 gate が効き、GBP_USD の squeeze release が集中する Asia 時間帯 (00-06 UTC) の行が正しく消えた → 実効頻度 ~2.9/週 → 在 gate ~1/週 に低下。**これは gate の意図された挙動が 123 日ぶりに実現した状態** (発火数ベースの過去判断は引用前に再検討 — MEMORY `project_dt_ctx_hour_utc_live_freeze_2026_08_09` の帰結そのもの)
- 処分案: E2 → **E1** へ再分類。追加アクション不要

## 5. 観測基盤の欠陥 (本判別で露出したもの)

1. **registry の指示した判別手順が実行不能だった**: `roster-e2-silent-promoted-cells` は「`/api/demo/live-enable-flags` で SQUEEZE_REDESIGN_V2 等 env 実値を確認」と指示するが、**当該 endpoint は KALMAN_D7 / USDJPY_CARRY_DIP の 2 lever しか返さない** (app.py L13712)。REDESIGN_V2 系 ~40 lever は観測経路ゼロ (ssh printenv のみ)。→ **R3 提案 (別 task)**: live-enable-flags に REDESIGN_V2 系 lever の実効値を一括追加 (import 時 os.environ snapshot で可)
2. **attrition tool の窓は 30d 固定**で「いつから沈黙か」に答えられない — E2_SILENT 判定に `last_row_at` (全期間) を併記する改修が読み手として必要 (R3 提案、別 task)

## 6. registry 変更提案 (本セッションでは registry を変更しない)

`roster-e2-silent-promoted-cells` の更新案:
- E2_SILENT の実体は `bb_squeeze_breakout × EUR_USD` の 2 セルのみ、と message を訂正 (ema200/SRM セルは E1 = 未帰属ではなく supply present)
- 到達経路を「§2.4 の user 決裁 (R3 修復 vs v2 実験放棄) + env 最終確認 (ssh printenv)」に差し替え
- 期日 2026-10-06 は維持

## 7. 変更したもの / しなかったもの

| | 内容 |
|---|---|
| ✅ 作成 | 本文書 (診断のみ) |
| ❌ しない | live コード / env / tier / registry の変更 (全て提案として §2.4/§5/§6 に記載) |
| ❌ しない | bb_squeeze v2 の修復実装 (user 決裁後の R3) |
