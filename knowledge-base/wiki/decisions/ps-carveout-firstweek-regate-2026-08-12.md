# ps×5 carve-out 復帰初週再ゲート監査 (2026-08-12、期日 08-11 の 1 日超過で執行)

> **rule:R3 (監査・読むだけ)**。live/shadow/tier/env 変更ゼロ。
> 対象: [[track-c-capital-plumbing-decision-packet-2026-07-28]] D-c-1 (price_shock_rev ×5 の agg-Kelly min-lot carve-out、user 承認 2026-07-28) の復帰初週再ゲート — registry `ps-carveout-firstweek-regate`。
> live 判定は正規規約 `oanda_trade_id != ''` (SSOT live 判定の教訓、wiki/lessons/index.md)。

## 0. 結論

**3 項目 PASS (c は条件付き) / R2 demote 規則は N 不足で非発動 / carve-out 配管は設計どおり作動。** ただし live 発火レートが packet 想定の ~18% (実測 4.3/月 vs 想定 24.5/月) で、N≥10 到達は現レートで ~2026-10 見込み。

## 1. Live fill 実態 (2026-07-29 carve-out 稼働 〜 08-12)

| # | セル | entry | exit | pnl | close_reason |
|---|---|---|---|---|---|
| 1 | price_shock_rev_aud_jpy_h1_long × AUD_JPY | 07-29 04:44Z | 07-29 16:44Z | +0.6p | horizon |
| 2 | 同上 | 07-31 08:57Z | 07-31 20:57Z | **−123.2p** | horizon |

- live N=2、EV −61.3p (単一 −123.2p が支配 — 12h horizon の shock long 逆行、disaster SL 150p 未満で設計どおり horizon 決済)。open 0、08-01 以降 fill なし。
- **判断しない**: N=2 で EV 評価は不能 (packet 自身が「EV 点推定は不明が正」)。downside は 1000u 固定で有界のまま。

## 2. 監査 3 項目の判定

### (a) AGG_KELLY BYPASS ログ実確認 — ✅ PASS (一次証拠 2/2)

Render 本番ログ (30d 保持内) で両 fill と秒単位一致:

- `2026-07-29T04:44:29Z [SHIELD] Aggregate Kelly gate BYPASS (min-lot pre-reg contract 1000u): -0.343 < 0 but price_shock_rev_aud_jpy_h1_long AUD_JPY kept live`
- `2026-07-31T08:57:19Z 同形式 (-0.367 < 0)`

**選択性の実証**: 07-29 04:47Z (bypass の 3 分後) に同じ負 Kelly 下で非 bypass 戦略が `Aggregate Kelly gate: -0.343 < 0 → OANDA blocked for vsg_jpy_reversal EUR_JPY` とブロックされている — bypass は price_shock_rev 固定契約のみに効いており、gate 本体は生きている。

### (b) exit 分布 = horizon 系か (BE_LOCK OFF 実効) — ✅ PASS

closed live 2/2 とも `close_reason=horizon`、保有 12h ちょうど (04:44→16:44 / 08:57→20:57)。BE/trail overlay 由来の exit はゼロ = [[preserve-exit-overlay-2026-07-28]] で決裁された horizon-exit estimand が live で実走している。LOCK 済み設計と live estimand の乖離なし。

### (c) watchdog / promote evaluator の estimand 整合 — ✅ PASS (条件付き、潜在乖離 1 件記録)

- `tools/price_shock_rev_live_watchdog.py` の auto-demotion 規則 (N≥10 ∧ EV<−0.5p → state file) は packet の R2 併設規則と一致。
- **潜在乖離**: watchdog の live 判定は `is_shadow=0` (line 109) で、正規規約 `oanda_trade_id != ''` と異なる。本監査窓では両定義の ps 母集団が完全一致 (N=2) し実害なし。ただし FLAG_DRIFT 型 (is_shadow=0 ∧ oanda 空) の行が混入した場合に watchdog N が過大計上される経路は残る — 将来 watchdog を触る際に `oanda_trade_id` join へ寄せるのが正 (本監査では変更しない)。

## 3. 付帯観測

- **発火レート実測**: 2 fills / 14 日 ≈ **4.3/月** — packet の想定トリガ率 ~24.5/月 (guard 通過後は要実測、と packet 自身が留保) の ~18%。ガード鎖 (spread/SL gate、dedup、他) 通過後の実効レートはこれが初の実測値。N≥10 (watchdog auto-demote 判定の分母) 到達は現レートで ~2026-10。
- ps demote 可否が絡む決裁は 549250 事故 disposition ([[mc-ruin-dashboard-artifact-2026-08-05]] / MEMORY `project_549250_incident_mc_ruin_fix_2026_08_05`) の系譜どおり **LOCK watchdog + user 決裁**の枠を維持 — 本監査はそれを変更しない。
- R2 demote 規則 (live N≥10 ∧ EV<−0.5p) は**非発動** (N=2)。−123.2p 単発を理由とする反応的措置は取らない (lesson-reactive-changes)。

## 4. 処分

- registry `ps-carveout-firstweek-regate` → resolved (本文書参照)。
- 後続監視は既存の ps watchdog cron (4h 毎、auto-demotion state) と R2 alert が担う — 新規 registry エントリ不要。
