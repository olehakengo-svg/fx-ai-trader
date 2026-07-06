---
id: 20260706-1600-order-layer-bar-dedup
title: "[T8-forensic/R3] order 層 per-bar dedup — engine 再構築で無効化された strategy 内 guard の構造代替"
owner: codex
status: done
priority: P1
created_at: 2026-07-06T16:00:00+0900
roadmap_gate: "T8 forensic #2 帰結 (pre-reg ゲート④『共通なら order 層に補正』分岐)。ゲート④再LOCK 自体は user R1 決裁"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/decisions/t8-week1-gate-breach-2026-07-06.md
related:
  - knowledge-base/wiki/analyses/zero-fire-diagnosis-carrydip-vix-2026-07-02.md
---

# 0. なぜこのタスクか

T8 forensic #2 (2026-07-06) で確定した構造問題:
`compute_daytrade_signal` / `compute_hourly_signal` が **poll 毎 (30秒) に DaytradeEngine / HourlyEngine を再構築**するため、strategy instance の per-bar dedup dict (`_last_emit_bar_ts` 等) / multi-bar cooldown 状態は毎 tick 消滅し、**live ではデッドコード**。live の dedup 層は recent_emit (tf-aware window) のみ。07-06 hull 同一 M15 バー ~55 行再 emit の根本原因。

# 1. 要求仕様

- demo_trader の signal 受理〜DB insert の order 層に **per-bar dedup** を追加:
  - key = `(entry_type, instrument, signal, bar_ts)` — bar_ts は該当 TF の closed bar timestamp
  - 教訓遵守: 「辞書 key は同一 block 域に属する単位を全て含める」「bar-based guard は bar 長そのもので測る」
- recent_emit (900s/3600s) は**そのまま併存** (多層防御、置換しない)
- Shadow 経路も dedup 対象 (同一バー重複 shadow row はデータ汚染源) — ただし is_shadow bypass 系の既存設計 (SHADOW_ALWAYS 等) の guard chain 共有関係を明示すること (教訓: bypass 経路の guard 共有は明示)
- block 時は block_counts に `order_bar_dedup` として計上 (観測性、silent drop 禁止)
- multi-bar cooldown (sweep 12-bar / carry dip 12h) の order 層代替は**本タスクでは実装しない** (BT 突合 = forensic #3 完了後に別タスク。BT が cooldown をどう執行しているか未確定のまま live だけ変えると BT/Live 乖離が逆向きに開く)

# 2. テスト

- 同一バー内 2 回目の同 (entry_type, instrument, signal) emit が order 層で block されること (mode スレッド跨ぎ含む)
- 新バーでは通ること / 逆方向 signal は独立であること
- shadow row の同一バー重複が消えること
- 既存 recent_emit テストが green のまま

# 3. 成果物

- 実装 + tests + changelog/KB 同一コミット
- t8-week1-gate-breach-2026-07-06.md の forensic #2 行に実装完了を追記


## Result (2026-07-06T07:40:00Z)

- Codex companion job task-mr8w4srl-egospv (5m58s): TDD (RED→GREEN) で実装完了
- order 層 per-bar dedup: key=(entry_type, instrument, signal, closed_bar_ts)、primary `_tick_entry` と shadow emit DB insert が共有、recent_emit 併存、block counter `order_bar_dedup`
- tests/test_dedup_gate_all_paths.py 12 passed + 関連 suite 29 passed

## Claude Review (2026-07-06)

- **bar_ts 供給の確認**: `_tick` が全シグナルに `sig["_closed_bar_ts"] = _closed_bar_ts_from_df(df)` を設定 (5m 補完経路も個別設定) — guard が no-op に落ちる懸念は解消済み
- **key 設計**: mode / is_shadow を意図的に含めない (並行 mode スレッドと SHADOW_ALWAYS が同一バー観測を重複させない) — 教訓「辞書 key は同一 block 域の単位を全て含める」と整合
- **guard 順序**: order_bar_dedup → recent_emit の直列 (多層防御維持)。state pruning は max(7200, 2×bar) で TF-aware
- **naming nit**: `_closed_bar_ts_from_df` は実際には df.index[-1] (live では forming bar) を返す — per-bar dedup としては機能等価 (同一バー内で不変・新バーで更新) だが名前は不正確。動作影響なしのため受容
- **判定**: 承認。multi-bar cooldown の order 層代替は仕様通りスコープ外 (forensic #3 後)
