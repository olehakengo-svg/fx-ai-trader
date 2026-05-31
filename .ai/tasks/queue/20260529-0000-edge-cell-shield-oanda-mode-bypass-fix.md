---
id: 20260529-0000-edge-cell-shield-oanda-mode-bypass-fix
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-29
owner: claude
---

# Edge cell bypass for SHIELD OANDA_MODE_BLOCKED + Aggregate Kelly Gate

## 背景 (実測 deploy 後 24h)

5594a7a5 (line 5309 override) + 4bce59a1 (A1+A2 pre-block bypass) deploy 済 (両方 origin/main)。しかし production `/api/demo/trades` で **edge_cell_id 付き trades が 8 件あるうち 7 件で is_shadow=1 + oanda_trade_id=""** (= OANDA 転送無し)。

特に post-deploy 2 件 (2026-05-28 07:16 と 08:16 UTC):
```
2026-05-28T08:16:08  session_time_bias  EUR_USD  SELL  edge=E2  shadow=1  oanda_id=-
2026-05-28T07:16:24  session_time_bias  EUR_USD  SELL  edge=E2  shadow=1  oanda_id=-
```

これらは edge cell match 成功 (edge_cell_id 書き込み済) なのに OANDA 未送信。

### Root cause (深掘り判明)

`modules/demo_trader.py:5530-5538`:

```python
if _is_promoted and mode in self._OANDA_MODE_BLOCKED:
    if entry_type in self._SHIELD_EUR_DT_WHITELIST:
        self._add_log(f"[SHIELD] EUR DT whitelist bypass: {entry_type} mode={mode}")
    else:
        self._add_log(f"[SHIELD] OANDA blocked: mode={mode}")
        _is_promoted = False
```

`_OANDA_MODE_BLOCKED` (line 7467) contains:
```python
_OANDA_MODE_BLOCKED = frozenset({
    "daytrade_eur",              # EUR_USD DT 15m: OANDA WR=29.2%
    "daytrade_1h_eur",           # EUR_USD 1H: 未検証
    "daytrade_eurgbp",           # EUR_GBP DT: OANDA遮断
    "scalp_5m",                  # v6.8: Sentinel A/Bテスト (N≥50後に判断)
})
```

`_SHIELD_EUR_DT_WHITELIST` (line 7478): `{"htf_false_breakout"}` のみ。

session_time_bias は `daytrade_eur` mode で発火するため、line 5530 で `_is_promoted=False` にされ、後続の line 5568 `if _is_promoted:` 分岐に入らず line 5714 の skipped path → OANDA 未送信。

5594a7a5 fix は `_is_shadow` 経路を override したが、**`_is_promoted` 直接 False 化の経路は未対応**。これが「edge cell match に到達するのに OANDA 転送されない」真の原因。

### 影響範囲

| Cell | strategy | pair | mode | _OANDA_MODE_BLOCKED ヒット | 現状 LIVE? |
|---|---|---|---|:---:|:---:|
| E2 | session_time_bias | EUR_USD | daytrade_eur | ✅ | ❌ |
| E3 | dt_bb_rsi_mr | EUR_USD | daytrade_eur | ✅ | ❌ |
| E8 | session_time_bias | EUR_USD | daytrade_eur | ✅ | ❌ |

3 cell (25%) が EUR_USD `daytrade_eur` block で停止。

加えて line 5573 `Aggregate Kelly Gate` も edge cell 例外なし:
```python
if _strat_mode != "sentinel" and not _is_sentinel:
    _agg_kelly = self._get_aggregate_kelly()
    if _agg_kelly is not None and _agg_kelly < 0:
        # block OANDA forward
```

aggregate Kelly が負のとき全 OANDA 転送停止 → edge cell promote も同時 block。

## 修正方針 (Option 2: edge cell aware exemption)

### 修正 1: SHIELD OANDA_MODE_BLOCKED bypass

`modules/demo_trader.py:5530-5538` を:

```python
# 修正前:
if _is_promoted and mode in self._OANDA_MODE_BLOCKED:
    if entry_type in self._SHIELD_EUR_DT_WHITELIST:
        self._add_log(
            f"[SHIELD] EUR DT whitelist bypass: {entry_type} mode={mode} "
            f"(N<10→Sentinel自動適用)"
        )
    else:
        self._add_log(f"[SHIELD] OANDA blocked: mode={mode}")
        _is_promoted = False

# 修正後:
if _is_promoted and mode in self._OANDA_MODE_BLOCKED:
    if entry_type in self._SHIELD_EUR_DT_WHITELIST:
        self._add_log(
            f"[SHIELD] EUR DT whitelist bypass: {entry_type} mode={mode} "
            f"(N<10→Sentinel自動適用)"
        )
    elif _edge_cell_force_live:
        # Edge cell match overrides SHIELD mode block (pre-reg LOCK 2026-05-26).
        # Edge cells E2/E3/E8 require this bypass for daytrade_eur mode.
        self._add_log(
            f"[SHIELD] EDGE_CELL bypass: {_edge_cell_id} {entry_type} "
            f"mode={mode} → keep _is_promoted=True for force-live"
        )
    else:
        self._add_log(f"[SHIELD] OANDA blocked: mode={mode}")
        _is_promoted = False
```

### 修正 2: Aggregate Kelly Gate bypass

`modules/demo_trader.py:5571-5594` 周辺の `if _is_promoted:` ブロック内 (aggregate kelly check) を:

```python
# 修正前:
if _is_promoted:
    if _strat_mode != "sentinel" and not _is_sentinel:
        _agg_kelly = self._get_aggregate_kelly()
        if _agg_kelly is not None and _agg_kelly < 0:
            self._add_log(
                f"[SHIELD] Aggregate Kelly gate: {_agg_kelly:.3f} < 0 → "
                f"OANDA blocked for {entry_type} {instrument} (SENTINEL still allowed)"
            )
            self._add_oanda_audit(...)
            # block forward, continue to skipped path
            ...

# 修正後:
if _is_promoted:
    if _strat_mode != "sentinel" and not _is_sentinel and not _edge_cell_force_live:
        # Edge cell pre-reg 2026-05-26 explicitly accepts Aggregate Kelly < 0
        # because cell-specific Kelly > 0 (Half Kelly per cell already computed).
        _agg_kelly = self._get_aggregate_kelly()
        if _agg_kelly is not None and _agg_kelly < 0:
            ...
    elif _edge_cell_force_live:
        self._add_log(
            f"[SHIELD] EDGE_CELL Kelly bypass: {_edge_cell_id} {entry_type} "
            f"(per-cell Kelly Half pre-reg LOCK)"
        )
```

注意: 上記は具体的 line range が変動するため、Codex は実際の周辺コードを読んで適切に挿入する。`_edge_cell_force_live` がスコープにあることを確認。

## DDL / schema (paste-in)

```python
# modules/demo_trader.py constants (paste-in for Codex)
_OANDA_MODE_BLOCKED = frozenset({
    "daytrade_eur", "daytrade_1h_eur", "daytrade_eurgbp", "scalp_5m",
})
_SHIELD_EUR_DT_WHITELIST = frozenset({"htf_false_breakout"})
```

```python
# modules/edge_cell_promote.py EDGE_CELLS (unchanged, paste-in)
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
```

## Tests (必須)

### 1. unit test 新規: `tests/test_edge_cell_shield_oanda_mode_bypass.py`

```python
def test_shield_oanda_mode_block_bypassed_by_edge_cell():
    # Given: session_time_bias EUR_USD LDN signal, mode='daytrade_eur'
    # _edge_cell_force_live = True (E8 stage=1)
    # Expected: _is_promoted stays True after SHIELD check, log shows "EDGE_CELL bypass"

def test_shield_oanda_mode_block_fires_when_no_edge_cell():
    # Given: random non-edge-cell strategy with mode='daytrade_eur'
    # Expected: _is_promoted = False (existing behavior preserved)

def test_aggregate_kelly_gate_bypassed_by_edge_cell():
    # Given: edge cell match + agg_kelly < 0
    # Expected: NO block, signal proceeds to fire path

def test_aggregate_kelly_gate_fires_when_no_edge_cell():
    # Given: non-edge-cell + agg_kelly < 0
    # Expected: blocked, audit row with block_reason='agg_kelly=*<0'

def test_existing_eur_dt_whitelist_still_works():
    # Given: htf_false_breakout EUR_USD with mode='daytrade_eur', no edge cell
    # Expected: whitelist bypass log, _is_promoted=True (existing)
```

### 2. E2E test 新規: `tests/test_edge_cell_e2e_shield_bypass.py`

In-memory SQLite + EDGE_CELLS + PAIR_PROMOTED:
- session_time_bias EUR_USD/SELL LDN signal × 3 fire
  - Expected: all 3 trades is_shadow=0, oanda_trade_id non-empty (mocked OANDA ack), edge_cell_id='E8'
- dt_bb_rsi_mr EUR_USD/SELL signal × 3 fire
  - Expected: same, edge_cell_id='E3'
- Random non-edge strategy with daytrade_eur mode × 3 fire
  - Expected: all 3 blocked (existing behavior)

### 3. Local pytest baseline 維持

baseline 1802 件 → post-fix ≥ 1807 件 (5 new + 1 E2E)。NEW failure 0 件。

## Pre-reg (12h post-deploy)

deploy 後 12h で:

| 期待 | 閾値 |
|---|---|
| `[SHIELD] EDGE_CELL bypass` ログ件数 | ≥ 3 件 |
| `[EDGE_CELL] ... shadow→live force override` ログ件数 | ≥ 3 件 |
| oanda_audit で `edge_cell_id='E2'|'E3'|'E8'` + `bridge_status='sent'|'filled'` 件数 | ≥ 1 件 |
| demo_trades で edge_cell_id='E2'/'E3'/'E8' + is_shadow=0 件数 | ≥ 1 件 |

12h で 0 件 → P0-7 follow-up (まだ別の `_is_promoted=False` path 存在の疑い)。

## 禁止事項

- `_OANDA_MODE_BLOCKED` frozenset の **要素変更禁止** (kill-switch 自体は維持、edge cell 例外のみ)
- `_SHIELD_EUR_DT_WHITELIST` frozenset の **要素変更禁止** (whitelist 既存項目は不変)
- `_aggregate_kelly` の閾値 (< 0) 変更禁止
- `EDGE_CELLS` リストの追加/削除禁止
- `_edge_cell_force_live` 判定ロジックの変更禁止 (= line 5309 override 条件は不変)
- LIVE 戦略 tier の変更禁止
- 本番 demo_trades.db への手動書き込み禁止

## ロールバック

- deploy 後 4h で account DD>3% → 即 revert + Render redeploy
- 単一 cell DD>2%/日 → watchdog 自動 disable
- 12h で expected log 0 件 → P0-7 escalate

## クオンツチェック

- [x] R3 (correctness fix, BT skip 許容)
- [x] R1-EXCEPTION 維持 (edge cell pre-reg LOCK 2026-05-26)
- [x] Watchdog withdrawal trigger 既存
- [x] E2E test 必須
- [x] mock-only test 禁止
- [x] stash 漏れ verify ([feedback_codex_stash_leak](feedback_codex_stash_leak.md))
- [x] schema を spec に直貼り済
- [x] Live/Shadow 分離 (edge cell flip 経路のみ)

## Commit message template

```
fix(edge-cell): bypass SHIELD OANDA_MODE_BLOCKED + Aggregate Kelly Gate [rule:R3]

After 5594a7a5 + 4bce59a1 deployed, production /api/demo/trades still
shows edge_cell_id=E2/E8 with is_shadow=1 + oanda_trade_id="".

Root cause: line 5530 SHIELD OANDA_MODE_BLOCKED check sets
_is_promoted=False for entry_types not in _SHIELD_EUR_DT_WHITELIST
when mode='daytrade_eur'. Line 5573 aggregate Kelly gate similarly
blocks OANDA forward when agg_kelly < 0. Neither check edge cell
force-live state.

This patch adds _edge_cell_force_live exemption to both checks.
E2/E3/E8 (session_time_bias + dt_bb_rsi_mr × EUR_USD) can now reach
OANDA fire path while keeping the SHIELD kill-switch active for
non-edge-cell strategies.

Refs: ai/tasks queue 20260529-0000
```

## Acceptance

1. Patch applied to `modules/demo_trader.py:5530-5538` and aggregate Kelly check
2. 5 new unit tests + 1 new E2E test pass
3. Local pytest baseline failures unchanged
4. PR shows:
   - patch diff with `_edge_cell_force_live` elif branches added
   - test diffs
   - log sample of `[SHIELD] EDGE_CELL bypass: E2/E3/E8 ...` from E2E test
   - confirmation that line 5309 override + new line 5530 bypass both fire

## 関連 memory

- 前回 P0 fix: 5594a7a5 (line 5309 _is_shadow override)
- 前回 P0 fix: 4bce59a1 (A1+A2 pre-block bypass for r2_shadow_demoted_cell + same_price_0pip)
- 関連 audit: `.ai/tasks/done/20260528-0905-comprehensive-oanda-forwarding-audit.md` (この path を見落とした)
- [edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) — pre-reg spec
- [Kalman D7 LIVE 0.5x](project_kalman_d7_silent_drop_recovery_2026_05_28.md) — 同型の SHIELD bypass パターン
- [feedback_codex_stash_leak](feedback_codex_stash_leak.md) — push 後 git log verify 必須
