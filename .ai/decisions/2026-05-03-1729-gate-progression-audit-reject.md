---
date: 2026-05-03
task: 20260503-1722-gate-progression-audit
verdict: ACCEPT (Codex deliverable) / REJECT (Gate 1→2 progression)
rule: R3 (audit) → triggers R2 (defensive)
gate: Gate 0 (生存危機検出)
---

# Gate Progression Audit — 1→2 REJECT, Gate 0 危機水域

## Verdict (Codex deliverable)

**ACCEPT** — Codex 成果物は仕様通り、verdict logic は data-driven。

## Quant findings (Live N=917, FX-only, is_shadow=0 CLOSED decided, XAU除外)

| Field | Value |
|---|---:|
| N | 917 |
| WR | 38.60% |
| Wilson_lo | 35.51% |
| EV pip/trade | **-0.79** ⚠️ |
| PF | 0.695 (<1.0) |
| Kelly | 0 (raw=-0.1737) |
| **MC60d 破産確率** | **100.00%** 🚨 |
| max DD | 74.80% |
| Sharpe | -2.04 |
| total pip | -720.0 |

## 解釈

- 私の前回 `/fx-roadmap-status` の N=29 は `oanda_trade_id != ''` (真 OANDA 約定 = 実弾転送のみ) の狭いフィルタ。
- 今回 N=917 は memory `feedback_live_shadow_separation` 通りの **Live 流路全体** (`is_shadow=0 status=CLOSED outcome IN (WIN/LOSS/BE)`)。
- 両者は意味が異なる。N=917 が「Live 流路の真の景色」。
- Wilson_lo 35.51% > BEV ~32-33% で **統計的にはわずかに正の edge**。
- しかし **EV=-0.79p / PF=0.695 / MC60d=100%** で実質壊滅状態。
- 摩擦 (spread/SL gate/QH) が edge を食い尽くしている。
- Gate 1→2 ではなく **Gate 0 (生存) 自体が崩壊水域**。

## R2 降格候補 (audit からの top picks)

| entry_type | instrument | hour_bucket | N | EV pip |
|---|---|---:|---:|---:|
| ema_cross | USD_JPY | 15 | 4 | -9.50 |
| vix_carry_unwind | USD_JPY | 07 | 3 | -9.43 |
| ema_cross | USD_JPY | 16 | 5 | -8.40 |
| session_time_bias | GBP_USD | 06 | 3 | -6.73 |
| inducement_ob | EUR_GBP | 14 | 3 | -5.17 |
| dual_sr_bounce | USD_JPY | 05 | 3 | -4.47 |
| sr_channel_reversal | USD_JPY | 07 | 3 | -3.83 |

N≤5 で統計検定不能だが、Rule 2 (Fast & Reactive) で N≥3 で即降格判断可。

## API 照合 (2026-05-03 18:30 JST, parent Claude DNS解決済)

| 指標 | Audit (N=917, /tmp mirror) | API (/api/risk/dashboard 直接) |
|---|---:|---:|
| Kelly | 0.0 | 0.0 |
| edge | -0.1737 | -0.1668 |
| WR | 38.60% | 37.96% |
| n_trades | 917 | 511 |
| MC ruin | **100.00%** (60d / 1875t fwd) | **1.88%** (300t fwd) |
| DD pct | 74.80% (peak-trough audit) | 40.65% (current API) |

**reconciliation**: 数字に矛盾なし。API は短期 horizon (300 trades) で 1.88%、audit は 60日 horizon (1875 trades = 30/day × 60d 投影) で 100%。月利100%目標は月単位スケール → **60日 horizon が operationally meaningful** で MC=100% が Gate 0 危機の正解。

API側 DD 40.65% は wiki/index.md 表記と一致 → audit 74.80% は trough-to-peak (より厳格) なので differ。両者 defensive 0.2x 維持を裏付ける。

## Blockers / Caveats — 解消済

## Roadmap impact

- Gate 1→2 不可は当然、Gate 0 維持自体が **defensive emergency**。
- 月利100% ロードマップは **凍結相当**。今優先すべきは Live edge 構造の止血 (R2 cell 降格)。
- A2-alt Scalp re-enable は Gate 1 unlock 経路だが、**Gate 0 危機解消が論理的に先**。

## Next task (Claude action)

**emergency-r2-cell-demote-2026-05-03**: 上記 7 cell + Bonferroni-aware で N≥3 EV<-3p の cell を一括 lot=0 / SHADOW 強制降格する Rule 2 task を即時起こす。

API DNS 解決可能な環境を Claude (parent) 側で確保 → live-trades / risk-dashboard 再取得 → audit 再走 → 確定降格リスト → Codex に Rule 2 patch task を渡す。
