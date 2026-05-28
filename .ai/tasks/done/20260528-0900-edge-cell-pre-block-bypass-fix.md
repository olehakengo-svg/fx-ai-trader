---
id: 20260528-0900-edge-cell-pre-block-bypass-fix
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-28
owner: claude
---

# Edge cell pre-block bypass — `r2_shadow_demoted_cell` と `same_price_0pip` を edge cell match で迂回

## 背景 (実測 deploy 後 3.5h)

5594a7a5 (edge cell force-live override fix) を deploy したが、**`[EDGE_CELL] ... shadow→live force override` ログ行は 0 件**。Render production log で SENTINEL_BLOCK_DIAG を実測したところ、edge cell strategy の signal は edge cell match (`modules/demo_trader.py:5011`) より手前で `_block()` 経由完全 reject されている。

確認できた block 経路:

| 戦略 | tier | block reason | line |
|---|---|---|---|
| `session_time_bias` (EUR_USD) | PAIR_PROMOTED | `same_price_0pip` | 3836-3837 |
| `bb_rsi_reversion` | PAIR_DEMOTED | `r2_shadow_demoted_cell` | 3547-3551 |
| `dt_bb_rsi_mr` | PAIR_PROMOTED | (live_n=0 未確認だが恐らく上記いずれか) | — |

これらは `_block()` で signal を完全 reject (return) するため、line 5011 の `edge_cell_promote.match()` に到達しない。Spec doc [edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) は「Tier gate 直前で force-live」と書いたが、実装では edge cell match が `_block()` 群の下流にある実装不整合。

Codex は 5594a7a5 commit message で予言済:
> If still 0 after 24h → file P0-5 (deeper bug in `_open_shadow_emit_trade` path not reached)

実際 24h 待たずに 3.5h で 0 件確認、edge cell match 到達ゼロ。

## 目的

`r2_shadow_demoted_cell` (line 3551) と `same_price_0pip` (line 3837) の `_block()` の手前で **edge cell match を pre-check** し、match (stage>0) なら `_block()` を skip → `_is_shadow=True` で続行 → line 5269 の既存 override で LIVE に flip させる。

## 修正方針 — 2 段階

### 修正 1: pre-check helper 関数の追加

`modules/demo_trader.py` の `_tick_entry()` 内、line 3540 直前 (R2_SHADOW_DEMOTE block の直前) で:

```python
def _edge_cell_eligible_at_pre_block(self, entry_type, instrument, direction, _entry_time, _v2_regime, _mtf_gate_action):
    """Returns True if this signal would match an active EdgeCell with stage>0."""
    try:
        cell = edge_cell_promote.match(
            strategy=entry_type,
            symbol=instrument,
            entry_time=_entry_time,
            direction=direction,
            v2_regime=_v2_regime or "",
            mtf_gate_action=_mtf_gate_action or "",
        )
        if cell is None:
            return False, ""
        lot = edge_cell_promote.get_cell_lot(cell.cell_id, self._db)
        return lot > 0, cell.cell_id
    except Exception as exc:
        # Fail-safe: if match raises, don't bypass (preserve original block)
        return False, ""
```

(関数本体 or インライン呼び出し、どちらでも可。re-usable helper 推奨。)

### 修正 2A: `r2_shadow_demoted_cell` block の前に edge cell pre-check

`modules/demo_trader.py:3547-3551` を以下に変更:

```python
# 修正前:
if is_shadow_demoted(entry_type, instrument) and not _is_live_tier_exempt:
    self._add_log(
        f"[R2_SHADOW_DEMOTE] blocked shadow-tracking cell "
        f"{entry_type} x {instrument}"
    )
    _block("r2_shadow_demoted_cell")
    return

# 修正後:
if is_shadow_demoted(entry_type, instrument) and not _is_live_tier_exempt:
    # Edge cell pre-check: if this signal would match an active EdgeCell,
    # mark as shadow but continue so the line 5269 override can flip to live.
    _ec_eligible, _ec_id = self._edge_cell_eligible_at_pre_block(
        entry_type, instrument, signal,
        _entry_time, _v2_regime or "", _mtf_gate_action or ""
    )
    if _ec_eligible:
        _is_shadow = True
        self._add_log(
            f"[R2_SHADOW_DEMOTE] edge cell {_ec_id} bypass: "
            f"{entry_type} x {instrument} marked shadow, will flip live"
        )
        # do NOT return; continue to edge cell match at line 5011
    else:
        self._add_log(
            f"[R2_SHADOW_DEMOTE] blocked shadow-tracking cell "
            f"{entry_type} x {instrument}"
        )
        _block("r2_shadow_demoted_cell")
        return
```

⚠️ 注意点:
- `signal`, `_entry_time`, `_v2_regime`, `_mtf_gate_action` が line 3547 時点で定義済か確認 (恐らく定義済、上流で signal/entry_time/v2_regime/mtf_gate_action が確定している)
- 未定義の場合は別の代替値 or defer を検討 (但しその場合 helper 呼べないので別案)

### 修正 2B: `same_price_0pip` block の前に edge cell pre-check

`modules/demo_trader.py:3835-3837` を以下に変更:

```python
# 修正前:
for t in mode_trades:
    if abs(t["entry_price"] - current_price) < _same_price_dist:
        _block(f"same_price_{_same_price_dist*100:.0f}pip"); return

# 修正後:
_blocked_same_price = False
for t in mode_trades:
    if abs(t["entry_price"] - current_price) < _same_price_dist:
        _blocked_same_price = True
        break

if _blocked_same_price:
    _ec_eligible, _ec_id = self._edge_cell_eligible_at_pre_block(
        entry_type, instrument, signal,
        _entry_time, _v2_regime or "", _mtf_gate_action or ""
    )
    if _ec_eligible:
        _is_shadow = True
        self._add_log(
            f"[SAME_PRICE] edge cell {_ec_id} bypass: "
            f"{entry_type} x {instrument} marked shadow, will flip live"
        )
        # do NOT return; continue to edge cell match at line 5011
    else:
        _block(f"same_price_{_same_price_dist*100:.0f}pip")
        return
```

## DDL / schema (paste-in)

```python
# modules/edge_cell_promote.py - 既存 EDGE_CELLS
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

`edge_cell_promote.match()` シグネチャ (line 51 in `modules/edge_cell_promote.py`):
```python
def match(
    *, strategy: str, symbol: str, entry_time: datetime, direction: str,
    v2_regime: str = "", mtf_gate_action: str = "",
) -> Optional[EdgeCell]:
```

`get_cell_lot(cell_id, demo_db) -> int` は line 82。stage=0 のとき 0 を返す。

## Tests (必須)

### 1. unit test 新規: `tests/test_edge_cell_pre_block_bypass.py`

```python
def test_r2_shadow_demote_bypassed_when_edge_cell_matches():
    # Given: bb_rsi_reversion EUR_USD SELL NY session
    # is_shadow_demoted() returns True
    # edge_cell_promote.match() returns E4 cell with stage=1
    # Expected: NO _block() call, _is_shadow=True, signal continues to line 5011

def test_r2_shadow_demote_still_blocks_when_no_edge_cell():
    # Given: random non-edge-cell strategy with is_shadow_demoted=True
    # Expected: _block("r2_shadow_demoted_cell") called, return

def test_same_price_bypassed_when_edge_cell_matches():
    # Given: session_time_bias EUR_USD LDN with adjacent entry_price
    # edge_cell_promote.match() returns E8 cell with stage=1
    # Expected: NO _block() call, _is_shadow=True, signal continues

def test_same_price_still_blocks_when_no_edge_cell():
    # Given: other strategy with adjacent entry_price
    # Expected: _block("same_price_0pip") called, return

def test_edge_cell_helper_handles_match_exception():
    # Given: edge_cell_promote.match() raises Exception
    # Expected: helper returns (False, ""), original block path taken
```

### 2. E2E test 新規: `tests/test_edge_cell_e2e_real_block_paths.py`

In-memory SQLite に R2_SHADOW_DEMOTE list + EDGE_CELLS を populated して、DemoTrader を起動:

- bb_rsi_reversion EUR_USD SELL NY signal × 5 fire → all should produce `[EDGE_CELL] E4 shadow→live force override` log + is_shadow=0 in demo_trades
- session_time_bias EUR_USD LDN SELL with existing trade at adjacent price × 5 fire → all should produce `[EDGE_CELL] E8 shadow→live force override` log
- 比較: 修正前は全て `_block()` で reject、demo_trades 0 行追加

### 3. Local pytest baseline

- 修正前 pytest 全件実行、PASS 数を記録 (`tests/test_*` 既存 1802 件想定)
- 修正後 pytest 全件、PASS 数が baseline 以上であること
- 新規 test の追加分を除いた baseline failure 数が増えていないこと

## Pre-reg (24h post-deploy)

deploy 後 24h で以下を観測 (Render production log):

| 期待 | 閾値 |
|---|---|
| `[EDGE_CELL] ... shadow→live force override` ログ件数 | ≥ 5 件 |
| `[R2_SHADOW_DEMOTE] edge cell ... bypass` ログ件数 | ≥ 3 件 (bb_rsi_reversion NY SELL の発火頻度依存) |
| `[SAME_PRICE] edge cell ... bypass` ログ件数 | ≥ 5 件 (session_time_bias EUR_USD LDN の発火頻度依存) |
| oanda_audit で edge_cell_id 列が非空かつ is_live=True の行 | ≥ 3 件 |

未達なら P0-6 へエスカレ (更に深い block path 存在の疑い)。

## 禁止事項

- edge cell match 関数 (`edge_cell_promote.match`) のシグネチャ変更 **禁止**
- EDGE_CELLS リストの追加/削除/filter 変更 **禁止** (pre-reg LOCK)
- `_block()` 関数自体の変更 **禁止**
- 他の `_block()` 経路 (spread_gate / recent_emit / velocity / spike 等) への bypass 追加 **禁止** (本タスク scope 外、別 PR)
- LIVE 戦略 tier の変更 **禁止**
- `EDGE_CELL_ADMIN_TOKEN` の export / 露出 **禁止**
- 本番 demo_trades.db への手動書き込み **禁止**

## ロールバック

- deploy 後 4h で account DD>3% → 即 revert commit + Render redeploy
- 単一 cell DD>2%/日 → watchdog 自動 disable (既存 logic)
- 12 cell 一斉発火で初日 DD>5% → Discord URGENT + 全 cell stage=0

## クオンツチェック

- [x] R3 (correctness fix, 365d BT skip 許容)
- [x] R1-EXCEPTION user judgment (Kalman D7 同型) 引き続き有効
- [x] Watchdog withdrawal trigger 既存
- [x] Cell pre-reg LOCK
- [x] E2E test 必須 ([feedback_codex_mock_test_trap](feedback_codex_mock_test_trap.md))
- [x] mock-only test 禁止
- [x] stash 漏れ verify ([feedback_codex_stash_leak](feedback_codex_stash_leak.md))
- [x] schema を spec に直貼り済
- [x] Live/Shadow 分離 (edge cell flip 経路のみ変更)

## Commit message template

```
fix(edge-cell): pre-block bypass for r2_shadow_demoted_cell + same_price_0pip [rule:R3]

5594a7a5 (line 5269 AND condition fix) was insufficient: edge cell match
runs at line 5011 which is downstream of multiple _block() paths that
return before edge cell match is reached.

This patch adds early edge cell match pre-check at:
- line 3547 (r2_shadow_demoted_cell block) - catches bb_rsi_reversion / E4
- line 3836 (same_price_0pip block) - catches session_time_bias / E8

When edge cell matches (stage>0), set _is_shadow=True and continue to
line 5011 where the regular edge_cell_promote.match() + line 5269
override flips to live.

Production log (2026-05-28 deploy after 3.5h) confirmed [EDGE_CELL]
override count = 0 due to upstream _block() returns.

Refs: ai/tasks queue 20260528-0900
```

## Acceptance

Codex completes if:
1. Patch applied to `modules/demo_trader.py:3547-3551` and 3835-3837 (or equivalent)
2. Helper function `_edge_cell_eligible_at_pre_block` or inline equivalent added
3. 5 new unit tests + 1 new E2E test pass
4. Local pytest baseline failures unchanged
5. PR shows:
   - patch diff
   - test diffs
   - log sample of `[R2_SHADOW_DEMOTE] edge cell E4 bypass` and `[SAME_PRICE] edge cell E8 bypass` from E2E test
   - confirmation that line 5269 override fires after bypass (`[EDGE_CELL] E? shadow→live force override`)

## 関連 memory / docs

- [edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) — pre-reg spec
- 前回 R3 fix: commit 5594a7a5 (`20260528-0700-edge-cell-force-live-override-fix`)
- 関連: commit 29ec95cb (shadow-eligible bypass for recent_emit/spread_guard) — 別 P0 で同じパターン適用済
- [Kalman D7 3-spec LIVE](project_kalman_d7_regime_bound_live_2026_05_20.md) — R1-EXCEPTION 前例
- [feedback_codex_stash_leak](feedback_codex_stash_leak.md) — push 後 git log で verify 必須


## Result (2026-05-28T09:02:41Z)

exit=0 · 571s

```
Implemented the pre-block edge-cell bypass.

Changed:
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:3546)
  - Adds early `_entry_time` / `_v2_regime`.
  - Bypasses `r2_shadow_demoted_cell` when an active edge cell matches.
  - Bypasses `same_price_0pip` when an active edge cell matches.
  - Adds `_edge_cell_eligible_at_pre_block()` at [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:7467).
- Added unit tests:
  - [tests/test_edge_cell_pre_block_bypass.py](/data/repo/fx-ai-trader/tests/test_edge_cell_pre_block_bypass.py:65)
- Added E2E real block-path test:
  - [tests/test_edge_cell_e2e_real_block_paths.py](/data/repo/fx-ai-trader/tests/test_edge_cell_e2e_real_block_paths.py:53)

Verification:
- `6 passed` for new tests.
- `22 passed` for existing edge-cell tests.
- Full suite: `1805 passed, 9 failed, 2 skipped, 1 xfailed`.
  - The 9 failures are all missing local MASSIVE parquet cache files under `data/cache/massive`, not edge-cell regressions.

E2E log samples confirmed:
```text
[R2_SHADOW_DEMOTE] edge cell E4 bypass: bb_rsi_reversion x EUR_USD marked shadow, will flip live
[EDGE_CELL] E4 shadow→live force override (was shadow due to: OTHER_UPSTREAM)
[SAME_PRICE] edge cell E8 bypass: session_time_bias x EUR_USD marked shadow, will flip live
[EDGE_CELL] E8 shadow→live force override (was shadow due to: OTHER_UPSTREAM)
```

Worktree is clean except for the intended modified/new files.
```
