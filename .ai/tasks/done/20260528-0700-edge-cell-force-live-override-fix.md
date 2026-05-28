---
id: 20260528-0700-edge-cell-force-live-override-fix
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-28
owner: claude
---

# Edge cell force-live override — spec 違反の AND 条件を撤去

## 背景 (Diagnosis 済)

[edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) で 12 cell が Stage-3 直行 LIVE 候補として pre-reg LOCK 済。各 cell は `modules/edge_cell_promote.py:32-45` で `EdgeCell` インスタンスとして登録、`stage=1` で active (system_kv default = "1")。

しかし watchdog audit (`knowledge-base/raw/audits/edge-cell-watchdog/2026-05-26.json`) で全 12 cell が:
- `stage: 1`
- `n: 0` (zero live fills)
- `zero_fill_7d: true`
- `verdict: HOLD`

7 日連続 live fill 0 件。Live N=0 で promotion 効果ゼロ。

### Root cause (実測 2026-05-28)

`modules/demo_trader.py:5269`:

```python
_edge_cell_mtf_shadow = bool(_is_shadow and _mtf_gate_action == "downgraded")
...
if _edge_cell_force_live and _edge_cell_mtf_shadow:  # ← AND 条件
    _is_shadow = False
    self._add_log(f"[EDGE_CELL] {_edge_cell_id} MTF downgrade bypassed before tier routing")
```

`_edge_cell_force_live = True` でも、`_edge_cell_mtf_shadow` (= MTF downgrade 起因の shadow) が True でなければ override が効かない。

しかし spec doc は「**Tier gate 直前で force-live + dedicated lot**」と書いており、shadow 化の理由を問わず edge cell match 時は LIVE 化が意図されていた。

実装の不一致:
- spec: 「edge cell match → LIVE (理由問わず)」
- 実装: 「edge cell match AND MTF downgrade 起因 shadow → LIVE のみ」

EUR_USD/SELL session_time_bias (E8 候補) は shadow N=85, Live N=0。`/api/strategies/status` 確認 (tier=`PAIR_PROMOTED`, EUR_USD whitelist 済) — `mtf_gate_action != "downgraded"` の他の shadow source (cooldown / score gate / sentinel / dedup 等 25+ 箇所) で is_shadow=True が立ち、edge cell の override が機能しない。

実証: `modules/demo_trader.py` の `_is_shadow = True` 代入箇所は 5269 行以前に 25+ 箇所 (`grep -n "_is_shadow = True" modules/demo_trader.py`)。各々が独自の理由で shadow を立てる。

## 目的

E8 (session_time_bias EUR_USD LDN) を含む 12 edge cell が **shadow 化の理由を問わず LIVE に到達できるよう** `modules/demo_trader.py:5269` の AND 条件を撤去する。

## ユーザー承認

2026-05-28 ユーザー指示: 「とりあえず見つかったものを LIVE へ」 (R1-EXCEPTION user judgment、Kalman D7 / vix_carry 1.0x と同型)。

12 cell 一括活性化を承認。撤退条件は既存 watchdog (Render cron 15分毎) で自動執行。

## 修正方針 (Option A — 最小、spec 準拠)

`modules/demo_trader.py:5269` の AND 条件を撤去:

```python
# 修正前 (line 5269):
if _edge_cell_force_live and _edge_cell_mtf_shadow:
    _is_shadow = False
    self._add_log(
        f"[EDGE_CELL] {_edge_cell_id} MTF downgrade bypassed before tier routing"
    )

# 修正後:
if _edge_cell_force_live and _is_shadow:
    # shadow 化の理由を問わず edge cell match 時は LIVE に override
    _is_shadow = False
    _shadow_reason_label = "MTF_DOWNGRADE" if _edge_cell_mtf_shadow else "OTHER_UPSTREAM"
    self._add_log(
        f"[EDGE_CELL] {_edge_cell_id} shadow→live force override "
        f"(was shadow due to: {_shadow_reason_label})"
    )
```

`_edge_cell_mtf_shadow` の計算は残す (log に shadow 起因を残すため、削除しない)。

`_edge_cell_force_live` 自体の判定 (line 5021 `_edge_cell_lot > 0`) は変更しない (= stage=0 disabled の cell は依然 override しない)。

## DDL / schema (paste-in, do not infer)

```python
# modules/edge_cell_promote.py の関連定数
EDGE_CELLS: list[EdgeCell] = [
    EdgeCell("E1", {"strategy": "dt_bb_rsi_mr", "session": "ASN", "direction": "SELL"}),
    EdgeCell("E2", {"strategy": "session_time_bias", "symbol": "EUR_USD", "session": "LDN", "mtf_gate_action": "live_tier_exempt"}),
    EdgeCell("E3", {"strategy": "dt_bb_rsi_mr", "symbol": "EUR_USD", "direction": "SELL"}),
    EdgeCell("E4", {"strategy": "bb_rsi_reversion", "session": "NY", "direction": "SELL"}),
    EdgeCell("E5", {"strategy": "dt_bb_rsi_mr", "symbol": "GBP_USD", "direction": "SELL"}),
    EdgeCell("E6", {"strategy": "rsk_gbpjpy_reversion", "symbol": "GBP_JPY", "direction": "BUY"}),
    EdgeCell("E7", {"strategy": "dt_bb_rsi_mr", "symbol": "GBP_USD", "session": "ASN"}),
    EdgeCell("E8", {"strategy": "session_time_bias", "symbol": "EUR_USD", "session": "LDN"}),
    EdgeCell("E9", {"strategy": "orb_trap", "symbol": "GBP_USD", "direction": "SELL"}),
    EdgeCell("E10", {"strategy": "wick_imbalance_reversion", "symbol": "GBP_USD", "v2_regime": "no_go"}),
    EdgeCell("E11", {"strategy": "dt_bb_rsi_mr", "session": "NY", "direction": "SELL"}),
    EdgeCell("E12", {"strategy": "sr_anti_hunt_bounce", "symbol": "EUR_JPY"}),
]
LADDER_LOTS = {1: 5000, 2: 7500, 3: 10000}
```

system_kv keys: `edge_cell_stage:{cell_id}` (default "1") / `edge_cell_stage_changed_at:{cell_id}` / `edge_cell_disabled_reason:{cell_id}`.

## Tests (mandatory — E2E + unit)

### 1. unit test (新規): `tests/test_edge_cell_force_live_override.py`

- Each fixture: trade attributes that satisfy 1 edge cell + `_is_shadow=True` (set via various non-MTF reasons)
  - reason A: score gate fail → is_shadow=True
  - reason B: cooldown active → is_shadow=True
  - reason C: sentinel bypass → is_shadow=True
  - reason D: MTF downgrade → is_shadow=True
- Expected: 全ケースで `_is_shadow=False` after edge cell override
- Verify [EDGE_CELL] log line includes the shadow source hint

### 2. unit test (既存変更): `tests/test_edge_cell_promote.py`

- 既存テストが `_edge_cell_mtf_shadow` 限定 override を assume している場合は、新仕様に合わせて期待値を更新
- assert 件: 12 cell すべて match → stage=1 で lot=5000 取得

### 3. E2E test (新規): `tests/test_edge_cell_e2e_force_fire.py`

- DemoTrader を本番に近い初期状態で起動 (in-memory SQLite)
- session_time_bias EUR_USD/SELL LDN シグナルを 5 回 force-fire
- 期待: 5/5 が `is_shadow=0`, `edge_cell_id='E8'`, `oanda_trade_id` set
- 比較: 修正前は `is_shadow=1` で OANDA 送信 skip するはず

### 4. Watchdog dry-run

- `python tools/edge_cell_watchdog.py --dry-run --apply` (--apply は実行せず、--dry-run のみ)
- 修正後の架空 8h Live trades を inject (E8 で 12 trade WR 50% / EV+3 を fixture)
- 期待: watchdog が "verdict: HOLD" を出し、disable trigger 発火せず

## 禁止事項

- 既存 25+ 箇所の `_is_shadow = True` 代入ロジック自体は **変更しない** (本タスクは override 拡張のみ)
- `EDGE_CELLS` リストの追加 / 削除 / filter 変更 **禁止** (pre-reg LOCK)
- `LADDER_LOTS` の変更 **禁止** (5000→7500→10000 ramp 固定)
- watchdog `tools/edge_cell_watchdog.py` の withdrawal trigger 変更 **禁止** (separate PR)
- `EDGE_CELL_ADMIN_TOKEN` の export / 露出 **禁止**
- 本番 demo_trades.db への手動書き込み **禁止** (deploy 後の自然発火を待つ)
- `EDGE_CELLS_GLOBAL_DISABLED` env var の解除 **触らない** (現状 unset = 有効)
- Discord webhook URL の hard-code **禁止**

## ロールバック

- 修正後 4 時間 monitoring で account DD>3% 即 rollback (commit 直接 revert + Render redeploy)
- 単一 cell DD>2%/日 は watchdog が自動 disable (Render KV 経由)
- 12 cell 一斉発火で初日 DD>5% で Discord URGENT + 全 cell stage=0 強制 (watchdog 既存 logic)

## 期待される影響

| 項目 | 修正前 | 修正後 (期待) |
|---|---|---|
| 12 edge cell Live fills/day | 0 | ~5-15 (cell match 頻度依存) |
| 期待 daily PnL (5000 lot × ~10 fills × EV ~+2p) | 0 | ~+1,000 JPY/day |
| 期待 daily DD (5σ tail) | 0 | ~-3,000 JPY/day |
| Watchdog actions/day | ZERO_FILL_7D_ALERT_ONLY | proper PF/WR/DD eval |

## クオンツチェック

- [x] R3 (immediate correctness fix, 365d BT skip 許容)
- [x] R1-EXCEPTION user judgment (Kalman D7/vix_carry 1.0x 同型) 文書化
- [x] Watchdog withdrawal trigger 既存 (LOCK)
- [x] Cell pre-reg (LOCK 2026-05-26)
- [x] E2E force-fire test 必須
- [x] mock-only test 禁止 ([feedback_codex_mock_test_trap](feedback_codex_mock_test_trap.md))
- [x] stash 漏れ verify (push 後 `git log` で必ず確認 — [feedback_codex_stash_leak](feedback_codex_stash_leak.md))
- [x] schema を spec に直貼り済 ([feedback_codex_schema_hallucination](feedback_codex_schema_hallucination.md))
- [x] Live/Shadow 分離 (修正は is_shadow flip のみ、shadow tracking は別ロジック)

## Commit message template

```
fix(edge-cell): force-live override works for all shadow sources [rule:R3]

Was: _is_shadow=False only when _edge_cell_mtf_shadow (MTF downgrade specific).
Now: any _is_shadow=True path gets overridden when edge cell matches + stage>0.

Per spec edge-cells-stage3-live-promote-2026-05-26.md ("Tier gate 直前で force-live").
12 cells (E1-E12) currently at stage=1 but live N=0 due to AND condition.

User-judgment R1-EXCEPTION (2026-05-28). Watchdog auto-disable on WR<28%
or EV<-1p will limit blast radius. Cohort: E8 shadow N=56 WR 50% EV+2.96
(half-2 WR 46.4% — formal Stage 4 fail but +EV consistent).

Refs: .ai/tasks/queue/20260528-0700-edge-cell-force-live-override-fix.md
```

## Acceptance

Codex completes if:
1. Patch applied to `modules/demo_trader.py:5269` (AND condition removed)
2. 4 new/updated tests pass
3. Watchdog dry-run logs verdict=HOLD with no disable trigger
4. Local pytest baseline failures unchanged (per [project_fxai_stale_test_backlog](project_fxai_stale_test_backlog_2026_05_07.md))
5. PR contains:
   - patch
   - test diffs
   - log sample showing `[EDGE_CELL] E8 shadow→live force override (was shadow due to: OTHER_UPSTREAM)` from E2E test
   - 修正前後の expected fill count diff

## 関連 memory

- [edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) — pre-reg spec
- [Kalman D7 3-spec LIVE 2026-05-20](project_kalman_d7_regime_bound_live_2026_05_20.md) — 同型の R1-EXCEPTION 前例
- [vix_carry 1.0x intentional exception 2026-05-21](project_vix_carry_1x_intentional_exception_2026_05_21.md) — 同型
- [LIVE/Shadow 分離必須](feedback_live_shadow_separation.md) — flip 後も shadow tracking ロジックを破壊しない
- [監査=設計の正誤、N不足は別問題](feedback_audit_purpose_design_not_n.md) — N=56 で promote 判断する根拠
- [shadow-first quant architecture](feedback_shadow_first_quant_architecture.md) — 例外として明示


## Result (2026-05-28T05:01:00Z)

exit=0 · 499s

```
Implemented the edge-cell force-live override.

Changed [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:5211):
- Replaced `if _edge_cell_force_live and _edge_cell_mtf_shadow:` with `if _edge_cell_force_live and _is_shadow:`
- Kept `_edge_cell_mtf_shadow` for source labeling.
- New log shape:
  `[EDGE_CELL] E8 shadow→live force override (was shadow due to: OTHER_UPSTREAM)`

Added/updated tests:
- [tests/test_edge_cell_force_live_override.py](/data/repo/fx-ai-trader/tests/test_edge_cell_force_live_override.py:195)
- [tests/test_edge_cell_e2e_force_fire.py](/data/repo/fx-ai-trader/tests/test_edge_cell_e2e_force_fire.py:12)
- [tests/test_edge_cell_promote.py](/data/repo/fx-ai-trader/tests/test_edge_cell_promote.py:69)
- [tests/edge_cell_test_helpers.py](/data/repo/fx-ai-trader/tests/edge_cell_test_helpers.py:1)

Verification:
- Targeted tests: `22 passed`
- E2E E8 force-fire: before expected `0/5` live fills under upstream shadow; after test confirms `5/5` rows are `is_shadow=0`, `edge_cell_id='E8'`, `oanda_trade_id` set, `5000u`.
- Watchdog dry-run evaluator fixture: `E8 verdict=HOLD`, `n=12`, `WR=0.50`, `EV=+3.00p`, `actions=[]`.

Full pytest:
- `1794 passed, 2 skipped, 1 xfailed`
- `9 failed`, all existing local data-cache failures due missing MASSIVE parquet files under `data/cache/massive`, not from this patch.
```
