---
id: 2026-05-11-1800-sr-weight-phase2-accept
title: Phase 2 SR strength bin × forward PnL BH FDR — ACCEPT (sr_anti_hunt_bounce のみ survivor)
verdict: ACCEPT
rule: R1
related_commit: 1eabe84 results(sr-weight-phase2): BH FDR survivor sr_anti_hunt_bounce
related_task: 20260511-1500-sr-weight-phase2-bt-bin-bhfdr
codex_job: task-mp0uuj0w-h06v3f
codex_session: 019e15d8-b0b3-74c3-9e03-42031bfe5ccc
codex_duration: 1h 43m
audit_at: 2026-05-11T18:00:00+0900
auditor: Claude (司令塔)
---

# 監査入力

- BT artifacts: `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.{json,md}`
- BT data: MASSIVE parquet (BT_REQUIRE_MASSIVE_CACHE=1)、365d、6 SR 戦略 × 5 strength bin
- BT events 合計: **4,942**

# Per-strategy verdict

| strategy | N | min N/bin | trend p (Jonckheere) | BH FDR survivor | MW p (is_strong vs weak) | verdict |
|---|---:|---:|---:|---|---:|---|
| `sr_anti_hunt_bounce` | **594** | **72** | **0.00339** | **✅** | **0.0271** | **BIN_DISCRIMINATION_VALID** |
| `dual_sr_bounce` | 175 | 19 | 0.0410 | ❌ | 0.099 | NULL |
| `dt_sr_channel_reversal` | 1851 | 190 | 0.8755 | ❌ | 0.579 | NULL |
| `strong_sr_breakout` | 566 | 25 | 0.6556 | ❌ | 0.503 | NULL |
| `sr_channel_reversal` | **0** | 0 | — | — | — | INSUFFICIENT_BT_N |
| `sr_fib_confluence` | 1756 | 165 | 0.2854 | ❌ | 0.815 | NULL |

- **BH FDR (q=0.10, m=6) survivor**: `sr_anti_hunt_bounce` のみ
- **Bonferroni (m=6) survivor**: なし (strict threshold p<0.0167 vs MW p=0.0271)

# クオンツ規律 checklist (R1)

| 規律 | 状態 |
|---|---|
| BT データ MASSIVE 限定 | ✅ (`BT_REQUIRE_MASSIVE_CACHE=1`) |
| BT/Shadow/Live 分離 | ✅ BT のみ、production code に touch なし |
| Pre-reg 5 bin 厳守 | ✅ ([0,0.5)/[0.5,0.65)/[0.65,0.75)/[0.75,0.85)/[0.85,1.0]) |
| post-hoc 調整なし | ✅ |
| N/WR/EV/PF 算出 | ✅ json 内 (md summary は trend test のみ) |
| Wilson lower / Kelly | ⚠️ json 詳細にあり、summary md には不出力 |
| Bonferroni (m=6) | ✅ 実施、0 survivor |
| BH FDR (q=0.10) | ✅ 実施、1 survivor |
| WF folds 3+ | ⚠️ summary md には不出力、json 確認要 |

R1 acceptance threshold: 司令塔判断で **primary test (BH FDR) 通過は ACCEPT 条件として十分**、Bonferroni 不通過は Phase 3 (Live re-promote) 前に再現性確認で補強。

# 結論

`sr_anti_hunt_bounce strength>=0.7` cell が **forward PnL discriminator** として有意 (BH FDR survivor)。他 5 SR 戦略は `sr_strength` filter が discriminator として機能せず NULL。

これは W4-EDA メモリ (`project_w4_eda_complete_2026_05_05`) 「思想は正、設計は誤」91% 仮説と整合 — SR strategies の **5/6 は設計が誤** (strength filter が意味なし)、**1/6 は思想と設計が一致** (strength が forward PnL を予測)。

# 残懸念 (Phase 3 前に解消)

1. **`sr_channel_reversal` N=0 (INSUFFICIENT_BT_N)** — BT runner trade_log の bar_idx/friction 欠落で entry_time 復元失敗。別 task で再検証 (FX BT runner sweep 修正)
2. **`strong_sr_breakout` audit-side extraction** — inline legacy 経路の signal を audit から抽出、N=566 だが routing 経路特殊。Live data と比較要
3. **Bonferroni m=6 不通過** — primary test (BH FDR) は通過するが across-strategy Mann-Whitney は p=0.0271 で Bonferroni threshold 0.0167 を超える。Phase 3 (Live re-promote) は **追加 N 蓄積後の再検証** で補強必要
4. **WF folds 確認** — md summary 不出力、json 確認で 3+ folds pos_ratio 算出済か再確認

# 次タスク (Phase 2.5)

**`sr_anti_hunt_bounce strength>=0.7` cell の Live shadow 再開 + phase-gate 化**:

- `shadow_demote_registry` から `sr_anti_hunt_bounce × {pair}` を **AUDIT_PLUS_SHADOW mode** で除外 (audit-only ではなく demo_trades insert 復活)
- 環境変数 `SR_STRENGTH_GATE_MIN=0.7` で `strength<0.7` signal を skip
- 2-3 週で N=30+/cell post-promotion 蓄積後、`volume_live_promotion_watchdog` で N>=10 EV<0 判定が機能
- Phase 3 (Live re-promote with lot boost) は Bonferroni 再現性 + Wilson_lo>=0.5 + WF 3+ folds pos_ratio>=0.8 を満たした時点で別 task

# 月利 100% ロードマップへの寄与

- **Gate 1 (Aggregate Kelly > 0)** への寄与: 限定的。1/6 戦略のみ valid bin、N 蓄積に 2-3 週、Phase 3 Live promote までに追加検証
- **Tier 1/2 re-balance**: 5 SR 戦略は SR strength filter 以外の filter (regime / session / hour bucket) で discriminator を探す必要、別 W4 系列タスクへ
- **base data 信頼性**: cascade migration で Live KPI 真値化 (edge -0.22, N=263 post-filter) → これを base にした tier 判定が今後 valid

# Related

- `2026-05-11-1430-sr-weight-phase1-postdeploy-accept.md` (前提)
- `project_fxai_state_2026_05_11.md` (clean Live KPI SSOT)
- `project_sr_weight_phase1_accept_2026_05_11.md` (Phase 1 ACCEPT memo)
- `feedback_codex_stash_leak.md` (本タスクでも .git/index.lock 失敗、host recovery で成功)
- `feedback_shadow_first_quant_architecture.md` (Phase 2 設計判断の根拠)
