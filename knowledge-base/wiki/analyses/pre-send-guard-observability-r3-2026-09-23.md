# 送信前拒否・shadow 化の観測性修復 5 件 — weekend_gap_fade / 共有 `_tick_entry` 経路 (rule:R3、2026-09-23、PR #293)

> **種別**: R3 (構造欠陥 = 観測面の欠落)。凍結値 / estimand / live 送信ロジック / gate 判定は**一切不変** — 追加は永続記録 (row reasons marker / oanda_audit 行 / gate_block_daily reason_key / DB log) のみ。
> **起点**: [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] §2「不成立 (v) 未到達 `PRE_SEND_GUARD`」行 (PR #289、Codex 3 巡 + 敵対的レビュー) が確定した「G0' event #2 が (v) で終端したとき、亜種 (a)〜(d) を**事後に**識別できない」5 欠陥。
> **pin**: `tests/test_pre_send_guard_observability_r3.py` 24 本 (counterfactual 10 + 対称側/恒真でない側 10 + shadow_only 母集団不変 2 + review P2 消化 2: audit 2 世代の正規化 helper / session_filter 行)。修復前に 10 本が挙動理由で RED、修復後 GREEN を実測。

## 0. 3 行サマリ

1. 09-27 21:00Z の G0' event #2 が「broker 到達の証拠なし」で終端した場合、DRAFT §2 は (a) 早期 `_block` / (b) 上流 shadow bypass / (c) bridge 拒否 / (d) promotion gate の 4 亜種へ帰属せよと言うが、**(a-後) は `order_bar_dedup` に上書きされ、(b) は 8000 行で刈り込まれる DB logs のみ、(c3) は無記録、(d) は現在 mode からの推定しかなかった**。
2. 5 箇所へ event 時点の永続記録を足した (下表)。判定・戻り値・is_shadow の最終値・行数は不変 (対称側 pin 10 本)。
3. 副産物 2 件: DRAFT (c2) の「`oanda_trade_id` 空の非 shadow row が残る」は **DB row については 2026-05-11 (48025ebd3) 以降 stale** (write-time invariant で fill 前は常に is_shadow=1、欠陥は in-memory / ExposureManager / marker ログ側)。DRAFT (d) の「`[SHADOW_FIX] Post-gate escalation` が event 時点記録」は **mode_off では発火しない** (無ログの v8.9 fallback `demo_trader.py:7680` が先に shadow 化し、`[SHADOW_FIX] Persisted is_shadow=True … (was False at open_trade)` だけが残る)。両方 DRAFT を訂正した。

## 1. 欠陥 → 修復 → 観測面 (転記キー)

| # | 亜種 | 修復前の観測面 | 修復 (record-only) | 修復後の一次ソース (転記キー) |
|---|---|---|---|---|
| 1 | (c2) demo_trader pre-check `_bridge_active` 偽 / `is_mode_allowed` 偽 (`demo_trader.py` ~8170–8186) | oanda_audit `blocked` (`bridge_inactive` / `mode_<mode>_not_allowed`) のみ。in-memory `_is_shadow` は False → ExposureManager に**実弾なしの live position** が残る、marker ログ無し | bridge 拒否経路 (`[SHADOW_FIX] Bridge refused transmission`) と対称に `_is_shadow=True` + `update_shadow_status` + `_exposure_mgr.set_shadow_status(True)` + DB log | audit `blocked` + `[SHADOW_FIX] Pre-send guard: <strategy> <pair> trade=<id> → shadow (<reason>, …)` → `bridge:<block_reason>` |
| 2 | (c3) `OandaBridge.open_trade` 内 `if not self.active` / `is_mode_allowed` 偽 / 未対応 instrument (`oanda_bridge.py` 682–711) | **audit も log も無し**で `False` (呼び出し側は `[SHADOW_FIX] Bridge refused` で shadow 化するが reason 不明 = `refused_no_audit`) | 新 helper `_add_refused_audit` (391–) が daily-loss gate と同形の `blocked` 行 + `🔗 OANDA: [BLOCKED] … Reason: <block_reason>` + logger.warning | audit `blocked` / `block_reason` ∈ {`bridge_inactive_race`, `mode_<mode>_not_allowed_race`, `unsupported_instrument(<inst>)`} → `bridge:<block_reason>` |
| 3 | (d) `_is_promoted_ex` の block cause (`mode_off` / `pair_demoted` / `force_demoted` / `session_filter` / `auto_demoted` / `cell_routing_block` …、評価 7542) | 汎用 DB log のみ。しかも mode_off は v8.9 fallback (7680、無ログ) で shadow 化されるため `[SHADOW_FIX] Post-gate escalation` は**発火しない**。転記時に現在 mode を読むと mode 変更後に誤帰属 (Codex P2 4075642847) | 全 flip 完了後の 1 箇所 (8006–) で「row 書込み時 live 意図 (`_shadow_at_open` 偽) ∧ 最終 shadow ∧ 非 promoted ∧ cause 非空 ∧ shadow_only mode でない」なら row reasons `[PROMO_BLOCK] <cause>` (`append_trade_reason`) + audit `shadow_tracking(promo_block:<cause>)` + DB log `[PROMO_BLOCK] … cause=<cause>` | row reasons `[PROMO_BLOCK] <cause>` / audit `skipped` `shadow_tracking(promo_block:<cause>)` → `promo:<cause>`。**例外: `session_filter` の audit は legacy `shadow_tracking(session_filter_out)` のまま** (P-V4 2026-07-02 契約、exact pin あり、書き換えない) — 消費側は `demo_trader.promo_block_cause_from_audit()` で両世代を `session_filter` / `<cause>` に正規化する (PR #293 review P2 4078290940)。marker 導入前の row のみ `promo:UNKNOWN` |
| 4 | (b) `_UNIVERSAL_SENTINEL` 等 `_is_shadow_eligible_full` / `_is_slot_shadow_eligible` 分岐の shadow bypass (`[SHADOW] <gate> bypass:` 23 サイト) | DB logs のみ (8000 行刈り込み、24h で消える) → `bypass:UNKNOWN` | 各サイトで `_shadow_bypass_gates.append("<gate>")`、row 生成時 (6973) に reasons へ `[SHADOW_BYPASS] <gate>` を fold (`[HOURBLOCK_CLASS_EXEMPT]` / `[SHADOW_RELAX]` と同型)。`max_open` の無ログ shadow 化にも `[SHADOW] max_open bypass:` を追加 | row reasons `[SHADOW_BYPASS] <gate>` → `bypass:<gate>` (slot は `max_per_mode_pair` / `max_open`) |
| 5 | (a-後) order-bar 予約 (5665–) の**後**の terminal `_block` (recent_emit / cooldown / circuit-breaker / spike / spread・SL guard …) | 初回 block 後、同じ closed bar の全 tick が `[ORDER_BAR_DEDUP] blocked` + `gate_block_daily` `order_bar_dedup` に固定 → 末尾が本当の blocker を隠す | `_block` closure が予約 key を持つ tick では `_note_order_bar_first_block` (1471–) を先に呼び、`gate_block_daily` に reason_key `order_bar_dedup_first:<reason_key>` を予約 key ごとに **1 回だけ**永続 + DB log `[ORDER_BAR_DEDUP] first terminal block after reservation: … reason=<full reason>`。以後の dedup ログに `first_block=<reason_key>` を併記 | `gate_block_daily` の `order_bar_dedup_first:<reason_key>` (日次集計、90d retention) → (a) の主 reason_key |

gate ラベル (修復 4) は `_block` reason の正規化キーと同じ語彙: `max_per_mode_pair` / `max_open` / `session_hours` / `regime_range_dt_tf` / `regime_trend_bull_dt_tf` / `gbp_asia_flash_crash` / `recent_emit` / `session_pair(EUR_GBP|EUR_USD_Tokyo|EUR_USD_Late_NY)` / `alpha_scan(EUR_USD_SELL|RANGE_SELL|TREND_BULL_BUY|H11_EUR_USD|H13_USD_JPY|H16-20_USD_JPY|BUY_TREND_BEAR|H7-8_EUR_USD)` / `regime_guardrail` / `spread_guard` / `spike` / `velocity_up` / `velocity_down`。数値 (pip / 秒 / conf) は含めない (ラベル安定性、metric は `gate_block_daily` 側)。

## 2. 不変であることの pin (対称側 / 恒真でない側)

| 性質 | pin |
|---|---|
| 既存 bridge 拒否経路 (`[SHADOW_FIX] Bridge refused transmission`) と accept 経路 (`sent` audit、is_shadow=0 は fill callback のみ) は不変 | `test_symmetric_bridge_refusal_path_unchanged` / `test_symmetric_accept_path_stays_live` |
| bridge daily-loss gate は従来どおり自前の `blocked` **1 行のみ** / gate 通過は `blocked` 0 行 | `test_symmetric_daily_loss_gate_still_writes_exactly_one_blocked_audit` / `test_symmetric_gates_pass_writes_no_blocked_audit` |
| promotion gate を通った row に `[PROMO_BLOCK]` は付かない / 上流 bypass で最初から shadow の row の audit は素の `shadow_tracking` (Post-gate escalation 不発火) | `test_promo_block_marker_absent_when_gate_passes` / `test_symmetric_shadow_tracking_plain_when_shadow_came_from_upstream` |
| `session_filter` 変種 `shadow_tracking(session_filter_out)` の優先順位は不変 | 既存 `tests/test_session_filter_promotion_guard.py` (通過確認済み) |
| 非 sentinel 戦略の `_block` は row を作らない (marker 追加は行数を変えない) / bypass gate を踏まない sentinel row に marker は付かない | `test_symmetric_non_sentinel_recent_emit_still_hard_blocks` / `test_sentinel_row_without_bypass_has_no_marker` |
| 予約前 block (`conf<`) / bar_ts なし (予約なし) では `order_bar_dedup_first:*` は記録されない | `test_pre_reservation_block_records_no_first_block` / `test_block_without_bar_ts_records_no_first_block` |
| **shadow_only 母集団 (pre-reg LOCK) の行数・選択は不変**: rnb_usdjpy relax 行は 1 行 / is_shadow=1 / `[SHADOW_RELAX]` 従来どおり、`[SHADOW_BYPASS]` `[PROMO_BLOCK]` 無し。daytrade_audjpy は strategy mode off でも 1 行 / audit 素の `shadow_tracking` / `[PROMO_BLOCK]` 無し (shadow_only は promo cause の対象外) | `test_rnb_relax_row_population_unchanged_and_no_new_markers` / `test_daytrade_audjpy_shadow_only_row_excluded_from_promo_marker` (+ 既存 `test_rnb_shadow_only_downstream_relax.py` 20 本通過) |
| bypass marker サイト数 = 23 のスコープ pin (増減 = 帰属面の変更) | `test_shadow_bypass_marker_sites_cover_every_bypass_log` |

母集団選択子 (`tools/rnb_shadow_demote_gate.py` = is_shadow=1 ∧ oanda_trade_id 空 ∧ mode / watcher の shadow 選択) は reasons を読まないため、marker の append は選択に影響しない。`shadow_tracking` 系の既存消費者 (`tools/tier1_shadow_tracking_drift_guard.py` / `tools/tier1_shadow_tracking_breakdown.py`) は `startswith("shadow_tracking")` で variant を扱うため `shadow_tracking(promo_block:<cause>)` は互換 (P-V4 の `session_filter_out` variant と同じ契約)。

## 3. 設計上の判断

- **キー空間**: `order_bar_dedup_first:<reason_key>` は既存 reason 正規化 (`reason.split('(')[0]`) を使うため、gate_block_daily のキー集合は既存 reason 数 × 1 で有界。in-memory の予約→初回理由 map は `_order_bar_signal_emits` に無い key を 512 超で剪定。
- **(d) の統一永続点**: 「post-gate escalation ブロック内」ではなく「全 flip 完了後 (`_ldn_live_send` の直前)」に置いた。理由 = mode_off / pair_demoted / force_demoted は v8.9 fallback (7680) が**無ログで先に** shadow 化し、escalation ブロック (`not _is_promoted and not _is_shadow`) に到達しない (テストで実測)。条件に `_shadow_at_open` 偽を含めることで「row 書込み時は live 意図だった」row のみを (d) に帰属し、上流 bypass row ((b)、書込み時から shadow) と shadow_only mode row (構造的 shadow) を除外する。cause 空 (SHIELD mode / VWAP trip / Kelly / MC ruin) は従来どおり素の `shadow_tracking` — Kelly / MC は自前の `blocked` audit を持つ。
- **audit key の 2 世代 (PR #293 review P2 4078290940)**: `shadow_tracking(session_filter_out)` は P-V4 の legacy variant で、exact pin (`tests/test_session_filter_promotion_guard.py`) と KB 参照 ([[zero-fire-diagnosis-carrydip-vix-2026-07-02]]) を持つ契約のため書き換えない。row reasons の `[PROMO_BLOCK] session_filter` は標準表記で付く (pin: `test_session_filter_keeps_legacy_audit_key_and_gets_promo_marker`)。消費側は文字列比較でなく `promo_block_cause_from_audit(block_reason)` (legacy alias → `session_filter`、`promo_block:<cause>` → `<cause>`、他 → "") で正規化する。
- **corner case (記録する)**: `_promo_block_cause` 非空 → force-live override (PRIME / GRAIL / C1 / kalman / edge-cell) で `_is_promoted=True` → その後 Kelly / MC で再度 False、の順で起きると `[PROMO_BLOCK] <cause>` は「promotion gate の verdict」として付くが最終 blocker は Kelly / MC (自前 audit あり)。転記時は audit `blocked` 行を優先する。
- **(c2) の DB row**: `demo_db.open_trade(enforce_oanda_live_invariant=True)` (48025ebd3、2026-05-11) 以降、fill 前の row は常に is_shadow=1 で、`set_oanda_trade_id` の fill callback だけが is_shadow=0 にする。従って pre-check 拒否 row が resend (`get_open_trades_without_oanda` は is_shadow=0 のみ) に拾われる経路は元から無い。修復 1 の実効 = ExposureManager の実弾なし live 計上の解消 + marker ログ。

## 4. 変更ファイル / 行 (worktree 実測、main マージ後は再実測)

- `modules/demo_trader.py`: 定数 834–836 / helper 1471–1521 (`_note_order_bar_first_block` / `_order_bar_first_block_reason` / `_persist_promo_block_marker`) / `_block` closure 5124–5133 / 予約 5665–5680 / bypass marker 23 サイト / reasons fold 6973 / (d) 統一永続点 7998–8015 / pre-check shadow 化 8170–8186 / audit variant 8204
- `modules/oanda_bridge.py`: `_add_refused_audit` 391–414 / `open_trade` 冒頭 675–711
- `tests/test_pre_send_guard_observability_r3.py` (新規 24 本)
- KB: 本ページ / `wiki/changelog.md` / `CHANGELOG.md` / DRAFT §2 (v) 行 + §6 転記項目 + §7 禁止事項の識別手順を新観測面へ更新 (凍結値・分類規則・消費規則は不変)

## 5. 残置 (範囲外)

- 09-27 前の **永続 first-qualification ts** (DRAFT §4 row 8、別 R3) — 本 PR は帰属面のみで順序問題には触れない。
- SHIELD mode / VWAP trip 由来 escalation の audit variant 化 (`shadow_tracking(post_gate:<gate>)`) — cause 空の escalation は素の `shadow_tracking` のまま。必要になれば同型で足す。
- `[SHADOW_BYPASS]` を持つ過去 row は存在しない (marker 導入前)。2026-09-23 以前の (b) 転記は従来どおり `bypass:UNKNOWN` / Render ログ補完。
- registry entry は不要 (期日付きの判定を新設しない)。

## 参照

- [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] §2 (v) / §6 / §7
- [[weekend-gap-execution-contract-r1-packet-2026-09-10]] §6 (G0')
- [[rnb-shadow-lane-health-precheck-2026-09-22]] §11 (`[SHADOW_RELAX]` marker の前例)
- [[hull-fire-rate-funnel-2026-08-24]] §8 (gate_block_daily の estimand)
- MEMORY `feedback_check_the_symmetric_side_2026_09_19` / `feedback_pycache_prefix_stale_bytecode_verification`
