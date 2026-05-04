---
id: 20260504-0215-tier1-routing-anomaly-rca-rerun
title: "Tier 1 LIVE routing anomaly RCA — ELITE_LIVE 0.5% OANDA pass-through 構造解析 (R3 forensic) [RERUN — previous run lost to silent push failure]"
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T02:15:00+0900
roadmap_gate: Gate 0 復帰後 — 構造的 BT-Live divergence の根因特定
rule: R3
rerun_of: 20260504-0130-tier1-routing-anomaly-rca
rerun_reason: |
  Previous run (job claim af1bee2 at 17:00:25 UTC, exit 0 at 17:06:31)
  succeeded inside the worker but the result commit silently failed to
  push to origin/main due to a GitPython Remote.push() rejection-handling
  bug. Worker logged status=success but origin never received the result.
  Fixed in fx-ai-trader-codex-runner commit 1e29a8c (PushRejectedError
  detection + clone_or_pull reset --hard recovery). Re-running.
prerequisite_decisions:
  - 2026-05-03-1826-r2-strategy-instrument-reject-tier1-h4-confirmed (H4 Tier 1 LIVE 真犯人)
  - 2026-05-04-0017-r2-15cell-lock-gate0-accept-commit (Gate 0 ACCEPT 達成)
---
## 0. なぜ今このタスクか

R2 strategy × instrument counterfactual TRUE_LIVE で **H4 confirmed** (Tier 1 LIVE が真犯人):

- Tier 1 LIVE 5 cell (gbp_deep_pullback / trendline_sweep / session_time_bias 各 instrument) の Live 実績:
  - 過去 BT EV +0.6〜+1.0 → **Live EV -4〜-5** (壊滅的乖離)
  - Live 流路 N=736 のうち **OANDA 約定 N=29 (0.5%)**

→ Live 流路では多発しているのに OANDA 約定はほぼ通過しない = **routing anomaly**。

memory `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` 同類の **構造的 BT-Live divergence** の可能性。Gate 0 ACCEPT で出血止血は達成したが、**根因不明のまま月利100% を再開すると同じ問題で再爆発するリスク**。

本 task は forensic で 0.5% pass-through の **どの gate がどの cell をどれだけ block しているか** を実測 query で特定する。

## 1. 仮説

**H1**: ELITE_LIVE 5 cell の Live → OANDA 経路で、ある特定 gate (spread / SL / Phase Gate / friction model / time block / aggregate Kelly gate / MC ruin gate) が支配的に block している。block 比率を gate 別に計測する。

**H2**: pre-cutoff (2026-04-08 以前) と post-cutoff (2026-04-08 以降) で gate block 比率が変化している。新 gate chain (v9.3) が ELITE_LIVE edge を破壊している可能性。

**H3 (反証)**: gate block ではなく、signal 生成時点で既に Live trade が発火しないパターンも多い (例: timestamp window outside session_time_bias の許可時間帯)。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| Live 流路全体 | `oanda_audit` (bridge_status='sent' 戦略名 row, memory `reference_oanda_audit_twin_meaning` 通り) | bridge_status='filled' (MODE 名 row) — GROUP BY 前に必ず分離 |
| OANDA 約定 | `oanda_audit` (bridge_status='filled', oanda_trade_id != '') | filled 行で entry_type が MODE 名 (PYR等) は親解決必要 |
| Block reason 集計 | `block_reason` 列 (`pair_demoted`, `phase_gate`, `aggregate_kelly_negative`, `mc_ruin_high`, `spread_too_wide`, `sl_too_wide`, etc.) | hardcode |
| 期間 | post-cutoff (2026-04-08 ~ 2026-05-03) | pre-cutoff trades |
| Cell | ELITE_LIVE 5 cell + PAIR_PROMOTED 主要 cell (xs_momentum × USDJPY 等) | FORCE_DEMOTED |

## 3. 統計条件

- 各 (strategy, instrument) cell について:
  - Live 流路 N (signal 発火数 = `oanda_audit` rows where bridge_status='sent')
  - OANDA 約定 N (`bridge_status='filled' AND oanda_trade_id != ''`)
  - pass-through rate = OANDA N / Live N
  - block_reason 別の集計 (上位 10 reasons の比率)
  - pre/post-cutoff 別の比較

## 4. 対象 5 + α cell

```python
ELITE_LIVE_CELLS = [
    ("gbp_deep_pullback", "GBP_USD"),       # Tier 1 デモト直後だが pre-merge 期間の集計
    ("trendline_sweep", "GBP_USD"),
    ("trendline_sweep", "EUR_USD"),
    ("session_time_bias", "USD_JPY"),
    ("session_time_bias", "EUR_USD"),
    ("session_time_bias", "GBP_USD"),  # 既 SENTINEL 降格済
]

PAIR_PROMOTED_REFERENCE = [
    ("xs_momentum", "USD_JPY"),  # PAIR_PROMOTED の比較対照
    ("xs_momentum", "EUR_USD"),
    ("doji_breakout", "USD_JPY"),
    ("squeeze_release_momentum", "EUR_USD"),
]
```

## 5. ACCEPT / NEEDS_MORE / REJECT 条件

- **ACCEPT**: gate-by-gate block 比率テーブル + pre/post-cutoff 比較が出力され、**支配的 block reason が特定**される (top reason が全 block の 60% 以上)
- **NEEDS_MORE_EVIDENCE**: 集計は出るが top reason が 30% 未満で分散、追加 dimension (hour bucket / session) が必要
- **REJECT**: forensic で signal 生成自体の問題 (発火しているのか?) が前提崩壊 → 別 task で signal trace

## 6. Scope

Codex MAY change:

- `tools/tier1_routing_rca.py` (new) — block_reason 別集計 + pass-through rate 計算
- `tests/test_tier1_routing_rca.py` (new) — bridge_status 分離 unit test (memory `reference_oanda_audit_twin_meaning` 規律確認)
- `knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md` — RCA ledger
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/`
- `tier-master.{json,md}` (本 task は forensic のみ)
- 既存 task spec、production credentials

## 7. Acceptance Criteria

- [ ] `tools/tier1_routing_rca.py --dry-run` で対象 cell リスト + 期間 + bridge_status 分離 (`feedback_oanda_audit_twin_meaning` 通り) 確認
- [ ] `pytest tests/test_tier1_routing_rca.py` pass (bridge_status='sent' / 'filled' 分離 unit test 含む)
- [ ] `wiki/decisions/tier1-routing-rca-2026-05-04.md` に: 5+α cell × pass-through rate 表, gate-by-gate block 比率 (top 10), pre/post-cutoff 比較, 支配的 block reason 特定, H1/H2/H3 verdict
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, RCA 結論 (root cause), recommended fix (R3 patch proposal、本 task では実装しない)

## 8. Verification Commands

```bash
# 1. Dry-run
python3 tools/tier1_routing_rca.py --dry-run

# 2. Tests (bridge_status 分離検証含む)
python3 -m pytest -q tests/test_tier1_routing_rca.py

# 3. Production run (Render mirror snapshot 使用、parent Claude が DNS 解決して fetch)
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' -o /tmp/live-trades-tier1-rca.json
python3 tools/tier1_routing_rca.py \
  --trades /tmp/live-trades-tier1-rca.json \
  --output knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md

# 4. Verdict 確認
grep -E "^Top block reason|^Pass-through rate|^Cell:" knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md | head -20
```

## 9. Codex Instructions

これは **Rule 3 (構造) forensic** タスク。実装変更なし、verification only。

memory `reference_oanda_audit_twin_meaning` 厳守: `oanda_audit` の `bridge_status='sent'` 行は戦略名、`'filled'` 行は MODE 名。GROUP BY 前に分離必須。PYR 等は filled で親解決要。

memory `feedback_label_empirical_audit`: コード演繹禁止。実 trades の `block_reason` 分布で root cause 特定。

memory `feedback_live_shadow_separation`: `is_shadow=0` で Live 集計、Shadow 流路は別 bucket で参照のみ。

DNS 失敗時は `/tmp/live-trades-20260503.json` フォールバック (前 audit と同じ SSOT)。

最終レポートに: status, files changed, top block reason (% 含む), pre/post-cutoff 比較, H1/H2/H3 verdict, recommended fix (例: spread gate 緩和、Phase Gate 解除、特定 hour bucket 除外等の R3 patch 候補)、次タスク (実装は別 task)。


## Result (2026-05-04T05:08:34Z)

exit=0 · 274s

```
実装・RCA 生成まで完了しました。production 実測では **ACCEPT** です。

変更:
- [tools/tier1_routing_rca.py](/data/repo/fx-ai-trader/tools/tier1_routing_rca.py)
- [tests/test_tier1_routing_rca.py](/data/repo/fx-ai-trader/tests/test_tier1_routing_rca.py)
- [tier1-routing-rca-2026-05-04.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md)
- [.ai/runs/20260504-tier1-routing-rca/final.md](/data/repo/fx-ai-trader/.ai/runs/20260504-tier1-routing-rca/final.md)

結論:
- Top block reason: `shadow_tracking` = `74 / 77` blocks, `96.10%`
- matched sent→filled pass-through: `15 / 15 = 100.00%`
- audited route-through: `15 / 92 = 16.30%`
- Live-only gate blocks: `0`
- つまり spread / SL / phase / MC ruin gate が Live 約定を潰している証拠はなく、post-cutoff の blocker は Shadow/reference 側の `shadow_tracking` 支配です。

Verdict:
- H1: ACCEPT。route blocker は `shadow_tracking` 支配。
- H2: ACCEPT。post-cutoff blocker concentration が `shadow_tracking`。
- H3: REJECT。対象 cell は route rows `N=92`、sent rows `N=15` で発火しています。

Verification:
- `python3 tools/tier1_routing_rca.py --dry-run` passed
- `.venv/bin/python -m pytest -q tests/test_tier1_routing_rca.py` passed: `3 passed`
- `python3 -m pytest ...` は system Python に pytest が無く、PEP 668 externally managed で user install も拒否されたため、この container では exact command は実行不能でした。
- production run と grep verdict 確認は完了済みです。

Recommended fix は ledger に記載済みです。本 task では実装変更なし。次は spread/SL gate 緩和ではなく、Gate 0 demotion/shadow dispatch と edge erosion の整合 RCA を切るのが妥当です。
```
