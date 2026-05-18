# PRIME v2 N+30d Re-audit Schedule (2026-06-17)

## Status

**SCHEDULED** — manual trigger on 2026-06-17 (or any time after). Not automated due to scheduled-tasks MCP requiring user approval dialog. See section §3 for trigger steps.

## Purpose

C audit (2026-05-18, `research/prime_v2_audit_2026_05_18.md`) returned NULL with 3 NEEDS_N strategies. Re-run the same 8-axis methodology after 30 days of shadow accumulation to detect:

- **PROMOTE_CANDIDATE**: NEEDS_N that now passes Bonferroni m=9
- **STILL_NEEDS_N**: insufficient growth, continue
- **NEW_DESIGN_BROKEN**: regression in previously-OK design
- **REVIVED_DEAD**: emit-stopped strategies confirming death

Also: monitor Micro LIVE results of the 2 Tier B 0.05x entries (`fib_reversal_PRIME`, `sr_fib_confluence_GBP_ADXQ2`) — apply `volume_live_promotion_watchdog` rule (Live N≥10 EV<0 → demote).

## Targets (locked, m=9 hypothesis space)

| Strategy | Verdict 2026-05-18 | Shadow N | best cell | Action target |
|---|---|---:|---|---|
| gbp_deep_pullback | NEEDS_N | 12 | _ALL | shadow N≥30 で再評価 |
| orb_trap | NEEDS_N | 19 | _ALL | shadow N≥30 |
| ob_retest | NEEDS_N | 40 | OVERLAP_BUY (N=11) | base emit 確認 + N |
| trend_rebound | THESIS_INVALID (demoted) | 60 | ATRQ2 | emit 0 確認 |
| dt_sr_channel_reversal | DESIGN_BROKEN | 106 | ADXQ2 | redesign 効果検証 |
| wick_imbalance_reversion | DESIGN_BROKEN | 70 | _ALL | redesign 効果検証 |

Micro LIVE 2 entries:
- `fib_reversal_PRIME` (revived 2026-05-18, Tier B 0.05x)
- `sr_fib_confluence_GBP_ADXQ2` (revived 2026-05-18, Tier B 0.05x)

## §3 Trigger steps (manual on 2026-06-17)

User or司令塔 Claude session が以下を実行:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
git pull origin main

# Option A: Codex cloud task として queue
cp .ai/tasks/queue/20260518-1730-prime-v2-shadow-audit-w4eda.md \
   .ai/tasks/queue/20260617-1000-prime-v2-reaudit-n30d.md
# spec の冒頭に「前回 audit (2026-05-18) との delta + Micro LIVE 検証」を追記
git add .ai/tasks/queue/20260617-1000-prime-v2-reaudit-n30d.md
git commit -m "test(codex-cloud): queue 20260617-1000-prime-v2-reaudit-n30d"
git push origin main

# Option B: ローカルで直接実行 (Codex 不要)
python3 tools/prime_v2_shadow_audit.py > research/prime_v2_audit_2026_06_17.md
# 出力を 2026-05-18 と diff、KB sessions/ に書き込み
```

## Audit method (locked, no post-hoc changes)

- Bonferroni m=9 (前回と同じ)
- α=0.05/9=0.005556
- Cell selection 原則は前回と同じ (aggregate + session×direction + regime quartile)
- Each strategy max 5 cells

## Output

- `knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-06-17.md`
- `research/prime_v2_audit_2026_06_17.md`
- Diff summary @ top (200 chars)
- Verdict matrix @ bottom

## Decision authority

Re-audit alone does NOT modify `modules/prime_gate.py`. Adding/removing PRIME entries requires:

1. Re-audit output (this task)
2. 司令塔 Claude review
3. New pre-reg LOCK Codex task

This separation is the "Claude=司令塔 / Codex=実働" 規律 ([feedback_claude_codex_division](memory/feedback_claude_codex_division.md)).

## Reminder hook

Not implemented (scheduled-tasks MCP unavailable in unsupervised mode). Manual reminder via:

- Session-start hook が `wiki/decisions/` を読む際に "SCHEDULED" status を表示する
- User memory に「2026-06-17: PRIME v2 N+30d 再 audit」を追加することを推奨
