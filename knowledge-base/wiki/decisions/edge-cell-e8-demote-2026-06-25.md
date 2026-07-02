# Edge Cell E8 (session_time_bias × EUR_USD × LDN broad) — Code-level DISABLE (rule:R2)

**Date**: 2026-06-25 (判断) / 2026-07-02 (コミット — fable5 audit P1-4 の指摘を反映して完結)
**Rule**: R2 (Fast & Reactive 止血 — 損失停止は N<10 でも即断可)
**Author**: Claude (司令塔)
**Related**: [[edge-cells-stage3-wilson-lo-restoration-2026-06-07]] / [[fable5-system-audit-2026-07-02]] (P1-4) / commit 9e508ee2 (A2: session_time_bias EUR_USD `_PAIR_PROMOTED` 除去)

## Decision

`modules/edge_cell_promote.py` に **code-level kill-switch `DISABLED_CELLS = {"E8"}`** を新設。
E8 = `EdgeCell("E8", {strategy: session_time_bias, symbol: EUR_USD, session: LDN})` (broad cell、mtf_gate_action 条件なし)。

`get_cell_lot("E8", db)` は Render KV `edge_cell_stage:E8` の値に関わらず **常に 0** を返す →
- Stage-3 force-live override (5000u) 停止
- pre-block bypass (SAME_PRICE / R2_SHADOW_DEMOTE) の eligibility 喪失
- fallback は通常 tier 解決 = `_UNIVERSAL_SENTINEL` → `_resolve_is_shadow_for_write`=True (**shadow、OANDA 送信なし**)。9e508ee2 A2 で `_PAIR_PROMOTED` が除去済みのため sentinel 実弾経路も存在しない

## Evidence (2026-06-25 時点)

| bucket | N | WR | EV | 累計 |
|---|---|---|---|---|
| Live (oanda fill) | 8 | 38% | **-3.51 pip** | **-28 pip** |
| Shadow | 10 | — | **-2.10 pip** | — |

- 両 bucket 負 EV。12y MASSIVE BT 全ペア REJECT (2026-06-11) とも整合 — BT・Live・Shadow の 3 者が同方向
- E8 は KV `edge_cell_stage:E8=0` で 2026-06-04 に既に OFF ([[edge-cells-stage3-wilson-lo-restoration-2026-06-07]] 記載: Live N=8 EV=-3.51p / Shadow N=8 EV=-5.24p)
- 本変更は新エッジ主張ではなく損失停止 + 構造ピン留めのため 365 日 BT 不要 (R2)

## なぜ KV stage=0 では不十分か (code-level pin の根拠)

`get_cell_lot` の KV getter は **key 欠損時に default="1" (stage 1 = 5000u)** を返す。KV の消失・リセット・別 DB での起動で E8 が**無警告で 5000u 再武装**する構造。code-level `DISABLED_CELLS` はこの default 経路ごと遮断する（テスト `test_e8_disabled_e2_active` が KV stage=3 でも lot=0 を固定）。

## E2 は据え置き

E2 = 同 strategy/symbol/session だが `mtf_gate_action=live_tier_exempt` の subset cell。Live EV≒+0.26 (≒トントン、E8 のような明確な負けなし) のため R2 止血対象外。E2 の将来判断は watchdog / R1 プロセスに従う。

## fable5 audit P1-4 の反映 (2026-07-02)

監査指摘 4 点への対応:
1. **(a) fallback=Sentinel 実弾疑義** → 9e508ee2 A2 (PAIR_PROMOTED 除去) 後は `_resolve_is_shadow_for_write` が UNIVERSAL_SENTINEL tier を shadow 強制するためコード上解消済み（本コミットでコメントも修正）
2. **(b) lot=0 で `edge_cell_id` 無タグ化 → watchdog 盲目化** → `demo_trader.py` のタグ付けを **match 適格性基準**に変更 (force-live のみ lot>0 gate)。watchdog は `is_shadow=0` フィルタ済みなので Live 統計は汚染されず、shadow N 蓄積 (再昇格判定の母集団) が回復
3. **(c) decision doc 不在** → 本文書
4. **(d) 依存テスト 7 件 red** → bypass 経路検証は active cell (E3/E4) へ付け替え、E8 側は disabled 挙動を固定する専用テストを追加 (下表)

**監査修正案② (`SHADOW_DEMOTED_CELLS` への追加) は不採用**: 同 registry は shadow row の emit 自体をブロックするため、原則3 (Shadow データ蓄積は削らない) および 9e508ee2 の「Shadow は継続」と矛盾する。shadow 化は UNIVERSAL_SENTINEL 経由で既に達成されている。

## Test coverage (同コミット)

| テスト | 検証内容 |
|---|---|
| `test_edge_cell_promote.py::test_e8_disabled_e2_active` | lot=0 固定 (KV stage=3 でも)、E2=5000 維持 |
| `test_edge_cell_e2e_force_fire.py::test_e2e_e8_disabled_force_fire_stays_shadow` | 5 連射 → shadow のみ、OANDA 送信ゼロ |
| `test_edge_cell_e2e_real_block_paths.py` (E8 半) | SAME_PRICE pre-block が通常適用 (bypass なし) |
| `test_edge_cell_e2e_shield_bypass.py` (E8 節) | SHIELD mode/Kelly bypass 不発、shadow 落ち |
| `test_edge_cell_force_live_override.py::test_e8_disabled_cell_no_force_live_override` | override 不発 + E8 タグは shadow row に残る |
| `test_edge_cell_pre_block_bypass.py::test_same_price_blocks_when_matched_cell_disabled` | disabled cell は pre-block eligibility を持たない |
| `test_edge_cell_shield_oanda_mode_bypass.py::test_e8_disabled_cell_does_not_bypass_shield` | SHIELD block 維持 + タグ残存 |

bypass 機構そのものの回帰は E3 (dt_bb_rsi_mr EUR_USD SELL) / E4 (bb_rsi_reversion NY SELL) に付け替えて維持。

## Re-enable 条件 (R1 only)

Shadow (edge_cell_id='E8' タグ付き) で **Wilson_lo ≥ 0.55** (Bonferroni-correct, `WILSON_LO_THRESHOLD`) + pre-reg LOCK。`DISABLED_CELLS` からの除去はこの decision doc の後継文書を必須とする。
