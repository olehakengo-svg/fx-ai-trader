---
id: 20260706-1600-order-layer-bar-dedup
title: "[T8-forensic/R3] order 層 per-bar dedup — engine 再構築で無効化された strategy 内 guard の構造代替"
owner: codex
status: queued
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
