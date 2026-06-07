---
id: 20260603-1028-kalman-d7-v18e-audjpy-eurjpy-shadow-promote
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-03
owner: claude
---

# Kalman D7 v18e — AUDJPY/EURJPY M15 Shadow Tier 投入

**Rule classification**: R1 (Slow & Strict — cross-pair promotion candidate, shadow
tier only. Stage 0 TV BT で edge 発見、Codex 監修 Python port 修正後の真値で
PF 1.07-1.10 marginal positive 確認。 Live 直行不可 → shadow tier N≥30 + BH-FDR 経由)

## Context — 本タスクは何を入れるか

2026-06-03 session で Kalman D7 v18e LIVE (USDJPY M15, slot 66bd93e0、本番稼働中)
を **同じ Pine source で 3 JPY cross に展開**した。詳細は memory
[project_kalman_d7_jpy_cross_2026_06_03.md] 参照。

修正済 Python port (Codex agent codex:codex-rescue 監修、`next_open` exit semantics、
tick quantization、first-bar fix、commission accounting) で TV USDJPY と PF 1% 一致を
確認。同 port で 4 pair 365d BT 結果:

| Pair | PF | N | WR | Net % | MaxDD % | Verdict |
|---|---:|---:|---:|---:|---:|---|
| USDJPY (本家) | 1.101 | 72 | 54.17% | +0.054% | -0.109% | LIVE 維持 |
| **EURJPY** | **1.076** | 119 | 64.71% | +0.049% | -0.154% | **Shadow 投入候補** |
| GBPJPY | 0.987 | 129 | 59.69% | -0.010% | -0.104% | breakeven、skip |
| **AUDJPY** | **1.097** | 109 | 65.14% | +0.088% | -0.183% | **Shadow 投入候補** (data 差で OANDA 直接 fetch 後再検証推奨) |

PF 1.07-1.10 は Live 直行に弱い → shadow tier で N≥30 + BH-FDR 検証経由が正規ルート。

## 要件 — Codex が実装すること

### 1. Python 戦略実装

新規ファイル: `strategies/intraday/kalman_d7_v18e_jpy_cross.py`

- Class: `KalmanD7V18eJpyCross` (LONG-only signal generator)
- `name = "kalman_d7_v18e"` (LIVE USDJPY と同 family name)
- 対象 pair: `AUD_JPY`, `EUR_JPY` (env override で activate)
- TF: M15
- ロジック: Pine v18e の完全 port (canonical:
  `/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine`)
  - EMA 25/75/200 / ATR(14) / RSI(14) / ATR percentile P20-P80 (window=200)
  - Entry: PO-UP start + DIST<3 + GAP<3 + ATR_Q + RSI<70 + sess(ASN/LDN/NY)
  - Exit: dynamic SL = entry - 2.0×current_ATR, trail activate @ +1.0×current_ATR,
    trail offset 0.5×current_ATR (Pine `process_orders_on_close=true` semantics →
    Python では `next_open` 評価で実装、`tools/kalman_d7_v18e_jpy_cross_bt.py`
    に既に存在する修正済 port を参照可)
- Per-pair tick quantization (JPY pairs mintick=0.001)

### 2. Strategy registry 接続

`strategies/intraday/__init__.py` (or wherever Kalman D7 LIVE が register されている)
に追加。Env override pattern:

```python
KALMAN_D7_V18E_AUDJPY_SHADOW = os.environ.get("KALMAN_D7_V18E_AUDJPY_SHADOW") == "1"
KALMAN_D7_V18E_EURJPY_SHADOW = os.environ.get("KALMAN_D7_V18E_EURJPY_SHADOW") == "1"
```

両 env=1 のとき `_shadow_always` set に該当 pair の entry を登録 → shadow tier 自動。
**Live tier には絶対投入しない** (env で蓋した状態でデフォルト OFF)。

### 3. Tests

`tests/test_kalman_d7_v18e_jpy_cross_shadow.py`:
- Pine source の golden trade (USDJPY 365d) を JSON fixture 化
- AUDJPY/EURJPY の sample bar (MASSIVE parquet 直近 N=100 bars) で entry signal
  evaluation 一致確認
- Shadow tier 投入時 oanda_audit に `bridge_status='skipped' block_reason='shadow_tracking'`
  行が出るかの integration test (env=1 + dummy signal で)

### 4. Pre-registration LOCK

Memory に Pre-reg 条件 LOCK (本タスク commit message に明記):

- Pair: AUD_JPY, EUR_JPY (M15)
- Window: 365日BT (Codex 監修済 Python port で N=109/119 PF 1.10/1.08 確認済み)
- Shadow tier 投入後 N≥30 蓄積 (~3-6 ヶ月想定)
- Promote to Live 条件 (将来):
  - Wilson 95% lower bound WR ≥ 0.50
  - PF ≥ 1.10 (shadow 実測)
  - BH-FDR survivor (m=2, q=0.10)
  - Max DD ≤ 5%
  - Sharpe > 0
- Retreat 条件:
  - Wilson 95% upper bound WR < 0.50
  - PF < 0.95 (N≥30 で)
  - 3 ヶ月 net negative 継続

## データソース

- Live signal: OANDA candles via `modules.data.fetch_ohlcv_oanda` (既存)
- BT validation: `data/cache/massive/{AUD_JPY,EUR_JPY}_15m.parquet`
- ⚠️ MASSIVE と OANDA の data 差は 20% PF affect しうると判明 (memory 参照)。
  本タスクは shadow tier 投入のみ、本格 BT validation は **OANDA 直接 fetch で
  再 BT** を別 task で実施 (optional, 本タスクの blocking ではない)

## 触らないこと

- `modules/demo_trader.py` の Kalman D7 LIVE 配線 (USDJPY 用) を保護
- USDJPY M15 v18e LIVE (slot 66bd93e0) を絶対 touch しない
- `tools/kalman_d7_v18e_jpy_cross_bt.py` は **read-only reference**、port は新ファイル
  に移植
- 既存 strategy ファイルを編集しない (新規ファイルで完結)

## Acceptance

- 新ファイル 2 つ (`strategies/intraday/kalman_d7_v18e_jpy_cross.py` + test)
- registry 更新 (env override registration のみ)
- 全 test pass (新 test + 既存 test 影響なし)
- env=0 default で shadow も live も非発火確認 (regression test)
- env=1 で shadow tier 発火、oanda_audit に shadow_tracking 行 (integration test)
- `wiki/strategies/kalman_d7_v18e_jpy_cross.md` 戦略カード作成
- commit message: `feat(kalman_d7): AUDJPY/EURJPY M15 shadow tier port [rule:R1]`

## 関連 memory / lesson

- [project_kalman_d7_jpy_cross_2026_06_03] — 本件本体
- [project_kalman_d7_regime_bound_live_2026_05_20] — USDJPY LIVE 投入経緯
- `wiki/lessons/lesson-tv-bt-cache-stale-port-bug-2026-06-03.md` — TV cache + port 学び
- [feedback_shadow_first_quant_architecture] — Shadow tier 経由 promote 規律
- [feedback_codex_mock_test_trap] — Codex 単独 PASS で実 API 失敗、本件で再現


## Result (2026-06-07T06:29:21Z)

exit=0 · 580s

```
Implemented and committed as `5d78c28d`:

`feat(kalman_d7): AUDJPY/EURJPY M15 shadow tier port [rule:R1]`

Changes:
- Added [kalman_d7_v18e_jpy_cross.py](/data/repo/fx-ai-trader/strategies/intraday/kalman_d7_v18e_jpy_cross.py:1) with env-gated AUD_JPY/EUR_JPY M15 long-only shadow signal logic.
- Wired [strategies/daytrade/__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py:82) to register `kalman_d7_v18e` only when `KALMAN_D7_V18E_AUDJPY_SHADOW=1` or `KALMAN_D7_V18E_EURJPY_SHADOW=1`.
- Added [test_kalman_d7_v18e_jpy_cross_shadow.py](/data/repo/fx-ai-trader/tests/test_kalman_d7_v18e_jpy_cross_shadow.py:1), including default-off, shadow registration, live-override exclusion, MASSIVE parity, and `oanda_audit` shadow_tracking coverage.
- Added USDJPY 365d golden fixture and [strategy card](/data/repo/fx-ai-trader/wiki/strategies/kalman_d7_v18e_jpy_cross.md:1).

Verification:
- `.venv/bin/pytest -q tests/test_kalman_d7_v18e_jpy_cross_shadow.py` passed: `6 passed`.
- Existing targeted tests passed:
  - `tests/test_kalman_d7_regime_refactor.py`: `6 passed`
  - `tests/test_shadow_emit_audit_all_strategies.py tests/test_sr_shadow_emit_metadata.py`: `4 passed`
- Full suite was attempted: `1902 passed, 2 skipped, 1 xfailed, 3 failed`. The 3 failures reproduce in isolation and are in existing shield-log tests:
  - `tests/test_edge_cell_e2e_shield_bypass.py::test_e2e_edge_cells_bypass_shield_mode_and_aggregate_kelly`
  - `tests/test_edge_cell_shield_oanda_mode_bypass.py::test_shield_oanda_mode_block_fires_when_no_edge_cell`
  - `tests/test_edge_cell_shield_oanda_mode_bypass.py::test_aggregate_kelly_gate_fires_when_no_edge_cell`

Worktree is clean after commit.
```
