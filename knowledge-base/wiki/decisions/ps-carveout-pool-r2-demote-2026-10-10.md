# ps carve-out pool R2 demote — price_shock_rev ×5 を _PAIR_DEMOTED へ (2026-10-10、rule:R2、autopilot 執行)

**Status**: ✅ 執行 (code + KB 同一 PR)。**判定**: registry `ps-carveout-regate-post-172` の pre-registered 条件「clean live N≥10 ∧ EV<−0.5p → R2 demote」が成立 (**N=11、EV −6.08p**)。
**親決裁**: [[track-c-capital-plumbing-decision-packet-2026-07-28]] D-c-1 (ps×5 carve-out、user 承認 2026-07-28) — その withdrawal 条件を [[ps-carveout-firstweek-regate-disposition-2026-08-12]] §4 が registry 化 (since 2026-08-11、n_decide 10、EV<−0.5p)。
**動機**: データ駆動 (registry の機械判定が本日 TRIGGERED「live N=11 ≥ 10 — 再評価を実施せよ」)。感情的要素なし。**Rule 2 (Fast & Reactive)** = 損失停止・降格は N=10 で即断可、autopilot 単独で執行可 (再 live 化は Rule 1 = user 決裁)。

## 1. 母集団と readout (本番 `/api/demo/trades?limit=5000`、2026-10-10T09:2xZ、5,000 行の窓は 07-28 まで遡る = since 08-11 を完全被覆)

母集団 = `entry_type` 前方一致 `price_shock_rev` ∧ `created_at ≥ 2026-08-11` ∧ `oanda_trade_id` 非空 ∧ `dedup_violation != 1` ∧ CLOSED (`exit_time` ∧ `pnl_pips` 非 null)。shadow は数えない ([[feedback_live_vs_shadow_strict_separation]])。

| 指標 | 値 |
|---|---|
| N (pool、clean live closed) | **11** (ps 行 12、うち shadow 1 を除外、open 0) |
| Σ pnl_pips | **−66.9p** |
| EV | **−6.08p / trade** (条件 −0.5p を 12 倍下回る) |
| WR | 36.4% (4W / 7L) |
| Wilson lower (95%) | **0.152** (BT 主張 Wilson_lo ≥ 0.58 [[price-shock-rev-live-activation-2026-05-18]] に対し live は大きく下) |
| exit | 11/11 `horizon` (LOCK 済み exit 設計どおり、overlay 介入なし) |

セル内訳:

| セル | N | Σ pips | EV | 備考 |
|---|---|---|---|---|
| price_shock_rev_eur_gbp_h1_long × EUR_GBP | 9 | −9.5 | **−1.06** | 単独でも EV<−0.5p。in-process watchdog (exact セル N≥10 ∧ EV<0) まであと 1 fill だった |
| price_shock_rev_aud_jpy_h1_long × AUD_JPY | 2 | −57.4 | −28.7 | 08-26 +20.1 / 09-03 **−77.5** (JPY 急騰局面の逆行、07-31 の −123.2p と同型) |
| eur_aud / usd_cad / nzd_jpy | 0 | — | — | 席は spread_wide で block (§11 readout)、live 実測なし |

## 2. 敵対的検査 (Rule 2 なので採用規律の 3 点検査は不要だが、判定の頑健性を記録する)

- **外れ値感度**: AUD_JPY −77.5p を除くと pool は +10.6p / N=10 = **+1.06p** に反転する。⇒ pool 条件の成立は 1 トレードに依存する。しかし (a) pre-reg 条件に外れ値除外は無く、事後除外は look-ahead (ハウス規律: 結果を見てから母集団を削らない)、(b) horizon exit は 2×ATR catastrophic SL 以外に損失上限を持たない設計で、−77.5p / −123.2p はこの family の**設計上の tail** であり異常値ではない、(c) EUR_GBP 単独 (N=9) でも EV −1.06p < −0.5p。⇒ 判定は維持。
- **BT 主張との整合**: BT Wilson_lo ≥ 0.58 (12.3y MASSIVE、BH-FDR m=3744) に対し live Wilson_lo 0.152、WR 36.4%。N=11 の二項検定で WR 真値 0.58 以上が出る確率 ≈ 0.09 (片側) — 単独では有意でないが、方向は BT→live 乖離 ([[bt-live-divergence]] 型) と整合。**BT の棄却ではない**: live は 1000u 固定の席供給 (~1/週) で、摩擦 (EUR_GBP RT ~3.0p = 構造的 BEV_WR 57%) が BT に無い。
- **代替説明**: (i) 席供給 fix (#172) 後の窓でも発火は spread_wide block が支配 (3 席 N=0) — 降格は供給問題を解かないが、損失停止とは独立。(ii) EUR_GBP は 2026-05 以降「STRUCTURALLY IMPOSSIBLE (RT 3.0p、BEV_WR 57%)」と friction 表に記載済み — ps EUR_GBP の live EV −1.06p はこれと整合。

## 3. 執行内容 (本 PR、code + KB 同一 commit)

1. `modules/demo_trader.py`: `_PAIR_PROMOTED` から ps ×5 を除去 → `_PAIR_DEMOTED` へ追加 (block reason `pair_demoted(<inst>)`、shadow tracking は継続 = 4原則 #3) / `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` から ps ×5 を除去 (eligible vs effective 教訓)。`PRICE_SHOCK_REV_TIER1_*` / MIN lot literal / seat priority / `_eur_base_shock_lock` / in-process watchdog `WATCHED_CELLS` は不変 (family 識別子・shadow 経路・再 live 化契約)。
2. tests: `test_price_shock_rev_live_activation_v2.py` (membership pin 反転) / `test_track_c_plumbing.py` (bypass pin 反転) / 新規 `tests/test_ps_carveout_pool_r2_demote_2026_10_10.py` (5 セル × demoted / not promoted / bypass 外 / runtime predicate / family 識別子不変)。
3. KB: 本 doc / strategies ×5 Status → `PAIR_DEMOTED` + family card / registry `ps-carveout-regate-post-172` を **resolved** 化 (執行済み live_count_decision を active のままにすると N=11 ≥ 10 で毎日 TRIGGERED を出し続ける — PR #324 Codex P2。cell_deepdive の LOCK redaction は「決定が執行済み = 凍結 look なし」なので母集団から外れるのが正しく、`tests/test_cell_deepdive_lock_redaction.py` の pin を「resolved lock は含まれない」に反転) / `ps-seat-spread-magnitude-readout` (10-19) と `ps-watchdog-demotion-state-unreachable` (10-11) に「live 送信は降格済み」を追記 / tier-master 再生成 / changelog / index / session log。

## 4. 影響と M1/M2 への寄与

- live 送信セル: 降格前のロースタ (carry_dip / kalman_d7 ×3 / weekend_gap_fade / ps ×5 …) から ps ×5 が外れる。10 月の ps live fill は 10-05 の 1 本のみで、席供給 ~1/週 × EV −6p の除去 = **月次 clean live PnL の期待値 ≈ +25p 改善** (N=11 / 50 日の実測レートから、幅広)。M1 (月次符号転換) の分母から負 EV 源を 1 つ消す。
- shadow 蓄積は継続するので ps family の統計 (BT→live 乖離の診断、E2 席供給 readout 10-19) は失われない。
- **再 live 化 = Rule 1** (365d BT 再走 or shadow N≥30 + Bonferroni + pre-reg LOCK + user 決裁)。in-process watchdog の `_reset_price_shock_rev_in_process_demotions` は本降格には無関係 (static `_PAIR_DEMOTED` が先に効く)。

## 5. 引用規律

- 「ps は BT で棄却された」と書かない (live 摩擦・席供給・N=11 の判定)。
- pool EV −6.08p は 1 トレード依存 (§2) — 引用時は外れ値感度を併記する。
- 09-30 readout の N=7 / 10-08 watchdog dry-run の EUR_GBP N=9 は本 readout (N=11、母集団: prefix × since 08-11 × canonical) と母集団が違う — 数字を混ぜない。

## 関連
- [[ps-carveout-firstweek-regate-disposition-2026-08-12]] / [[track-c-capital-plumbing-decision-packet-2026-07-28]] / [[price-shock-rev-live-activation-2026-05-18]] / [[price-shock-rev-promote-criteria-2026-05-18]] / [[price-shock-reversion]] / [[friction-analysis]] / [[lesson-asymmetric-agility-2026-04-25]]
