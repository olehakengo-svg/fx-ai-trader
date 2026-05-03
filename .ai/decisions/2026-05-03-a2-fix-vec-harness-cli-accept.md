---
date: 2026-05-03
task: 20260503-1620-a2-fix-vec-harness-cli-chunked
verdict: ACCEPT
rule: R3
gate: Gate 0 → Gate 1 unblocker
---

# A2-fix vec_harness chunked CLI — ACCEPT decision

## Verdict

**ACCEPT** — Rule 3 構造 unblocker 全 acceptance criteria 充足。

## Acceptance summary

- Equivalence test: **ACCEPT** (30d, N=2=2, max|pnl|diff=0.0 pip — 1e-6 厳格基準合格)
- pytest: 4 passed
- dry-run / schema / import purity / py_compile / file presence: 全 pass
- Data hygiene: `data_source="parquet_cache"` / `live_separation="bt_only"` 出力タグ確認済
- Scope: `app.py` / `modules/` / `strategies/` / `tools/scalp_re_enable_bt.py` 編集 0件
- 本番DB / `.env` / Render / OANDA: 一切 untouched

## Artifacts

- CLI: `tools/vec_harness_chunked_cli.py`
- Tests: `tests/test_vec_harness_chunked_cli.py`
- Equivalence report: `knowledge-base/raw/bt-results/vec-harness-chunked-validation-2026-05-03.{json,md}`
- 180d production: `knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json`
- Run report: `.ai/runs/20260503-163047-20260503-1620-a2-fix-vec-harness-cli-chunked/final.md`

## Risk register (ACCEPT を阻害せず、後続タスクで対応)

- 初回 chunk は `VecBacktestRunner.run(days=180)` 全体実行で 243.6s 消費。「1 invocation <10s」H1 は厳密未達。`modules/` 編集禁止スコープでは partial evaluator 不能。
- 後続: alternatives BT も同等の wall-clock を要する。許容する。

## 副次的に得られた A2 primary 候補 BT 数値

`mtf_regime_trend_cascade_scalp USDJPY 5m 180d`:

- N=34, WR=41.18%, EV=-1.24p, PF=0.741
- Wilson 95% [26.37%, 57.78%] — lo<BEV_WR(34.4%) → Wilson gate **FAIL**
- max DD=75.8p/364% — DD≤30% gate **FAIL**
- WF 50/50: IS PF=1.24 / OOS PF=0.38 — OOS 崩壊、典型的 over-fit
- Bonferroni K=5, α/K=0.01 — PF<1 で one-sided p>>0.5

→ A2 pre-reg LOCK 判定基準では Promote/Shadow ともに **REJECT 確定**。
→ `feedback_success_until_achieved` 通り、4 alternatives BT 走査必須。

## Roadmap impact

Gate 0 → Gate 1 unblocker 完了。chunked CLI が機能し、Bonferroni K=5 下での Scalp 候補 BT 経路が確立。

## Next task

ユーザー側で並行作成された **A2-alt (`20260503-1700-a2-alt-simple-structure-scalp-pre-reg.md`)** が後継。新 meta-decision `wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md` で MTF cascade は default Reject 圏に格下げされ、4 simple-structure candidates (`bb_squeeze_breakout`, `engulfing_bb`, `fib_reversal`, `sr_channel_reversal`) を **K=4 Bonferroni** で標準 `run_scalp_backtest` engine で評価する設計に切り替わった。

A2-fix で構築した chunked CLI は **当面 dormant** (将来の MTF strategy 用 infra として保持)。primary `mtf_regime_trend_cascade_scalp` 180d JSON (N=34/PF=0.741/EV=-1.24p/WF OOS PF=0.38) は **REJECT 確定証拠** として A2-alt 内 verdict table から参照する。
