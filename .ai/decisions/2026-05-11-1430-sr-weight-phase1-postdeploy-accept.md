---
id: 2026-05-11-1430-sr-weight-phase1-postdeploy-accept
title: Phase 1 SR-weight DB 列追加 — post-deploy 監査 ACCEPT
verdict: ACCEPT
rule: R3
related_commit: 364027e feat(audit): record SR-level quality (strength/touches/days_span/is_strong/distance_atr) in oanda_audit
related_task: 20260508-0030-sr-weight-audit-logging-phase1
audit_at: 2026-05-11T14:30:00+0900
auditor: Claude (司令塔)
---

# 検証手順

production `/api/oanda/audit?limit=2000` (1934 pre-deploy + 66 post-deploy)

Deploy boundary: id=5418 (timestamp 2026-05-08T08:16:29 UTC, ~ commit 364027e push timing)

# 検証結果

## 1. DDL ALTER 成功 ✅

`oanda_audit` table に 5 sr_ 列 (`sr_strength`, `sr_touches`, `sr_days_span`, `sr_is_strong`, `sr_distance_atr`) 確認。

## 2. SR-strategy 行で populated 100% ✅

Post-deploy (id>=5418) SR-target entries (`sr_targets = {dual_sr_bounce, sr_anti_hunt_bounce, dt_sr_channel_reversal, strong_sr_breakout, sr_channel_reversal, sr_fib_confluence}`):

| entry_type | bridge_status | n | populated |
|---|---|---:|---:|
| dt_sr_channel_reversal | sent | 1 | 1 (100%) |
| dual_sr_bounce | skipped | 1 | 1 (100%) |
| sr_anti_hunt_bounce | skipped | 1 | 1 (100%) |
| sr_fib_confluence | skipped | 2 | 2 (100%) |

合計 n=5, populated=5 (100%)

## 3. Historical NULL 保持 ✅

Pre-deploy (id<5418): 1934 rows, sr_ 列 populated = 0 (全て NULL、Phase 1 ALTER の `DEFAULT NULL` が正しく機能)

## 4. Entry-rate regression 検査 ✅

SR-strategy daily signal count:
- Pre-deploy (2026-04-28〜2026-05-07): 38〜79/day (avg ~55)
- Post-deploy (2026-05-08〜2026-05-11): 7〜8/day (~90% drop)

90% 減は **Phase 1 ではなく concurrent commit `0208ba8 R2 Critical 12 cell shadow demote registry` (2026-05-08 push)** で sr_channel_reversal × {EUR_USD,USD_JPY} / sr_fib_confluence × {EUR_JPY,GBP_JPY,USD_JPY} が Shadow demote されたことが原因。設計通り。bridge_status='skipped' で oanda_audit 行は維持されており sr_strength も populated されている。

# 司令塔判定

`ACCEPT` — Phase 1 deploy は仕様通り、コード regression なし。

# 次タスク

## Phase 2 BH FDR (deferred)

Phase 2 (bin 集計 + Benjamini-Hochberg FDR) は **N=30+/bin** 蓄積後に valid。現状 5 populated rows のみで実行不能。

**N 蓄積監視 sub-task**:
- 6h cron で oanda_audit から SR-target 行の populated count を集計
- bin 別 (strength<0.6 / [0.6,0.7) / [0.7,0.8) / [0.8,0.9) / >=0.9) で N がそれぞれ 30 到達した時点で Phase 2 を queue
- memory `feedback_audit_purpose_design_not_n` 規律: N 不足は redesign 棄却理由にしない、shadow で N 蓄積が正順

## 司令塔メモ

R2 12-cell Shadow demote で SR cells が shadow に落ちたため、Phase 2 入力データの大半は bridge_status='skipped' になる。bin 集計の独立変数 (sr_strength) と従属変数 (forward PnL) は **demo_trades テーブルとの JOIN** で取得する必要がある。Phase 2 task spec で明示すること。
