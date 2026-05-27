# Fix shadow dedup gate runtime bypass — `_maybe_reserve_signal_emit` never called

priority: P0
rule: R3 (immediate — Shadow KPI 二重カウント、promotion gate 統計が systematically biased)
gate: N/A (correctness fix, validated by post-fix `/api/admin/dedup_status` counters)

## Why this is P0

Live audit of `/api/admin/dedup_status` on Render fx-ai-trader.onrender.com (2026-05-27 04:52 UTC) shows:

```
runtime_dedup_stats: {
  primary_called: 0,  primary_blocked: 0,  primary_passed: 0,
  shadow_called:  0,  shadow_blocked:  0,  shadow_passed:  0,
  hydrated_from_db: 0,
  shadow_pass_log: []
}
runtime_dedup_dict_size: 0
```

→ `_maybe_reserve_signal_emit()` ([modules/demo_trader.py:3249](modules/demo_trader.py:3249)) は
本番で **一度も呼ばれていない**。コード上は `_tick_entry` (line 3793) と shadow_emit loop
(line 3178) の両方に gate 呼び出しが入っているが、実 run で counter が 0 のまま
= 経路が走っていない or `try/except` で握りつぶされている。

## Symptom evidence (live 2026-05-27 04:50 UTC)

`/api/demo/status` の `open_trades` 16 件中 12 件が同一 (instrument × entry_price × direction × strategy)
で重複。すべて `dedup_violation=0`（gate を通ったことになっている）、すべて `is_shadow=1`。

| pair | strategy | entry | Δ秒 |
|---|---|---|---:|
| EUR_USD SELL | dt_bb_rsi_mr | 1.16372 | **12s** |
| GBP_USD SELL | dt_bb_rsi_mr | 1.34540 | 17s |
| EUR_USD SELL | dt_bb_rsi_mr | 1.16370 | 22s |
| GBP_JPY BUY | sr_break_retest | 214.190 | 48s |
| GBP_JPY BUY | sr_break_retest | 214.262 | 22s |
| EUR_USD BUY | wick_imbalance_reversion | 1.16305 | **3s** |

15m / 1h bar 戦略で 3-48s 差の再エミットは window_sec=900s/3600s 設定なら全件
ブロックされるはず。

## Empirical loss impact (since 2026-04-01, sentinel scope N=6524)

| Strategy | N | EV | 判定 |
|---|---:|---:|:---:|
| dt_bb_rsi_mr | 116 | **+1.38p** | 🟢 勝ち (重複 OK) |
| sr_break_retest | 257 | **−3.18p** | 🔴 負け |
| wick_imbalance_reversion | 134 | **−0.77p** | 🔴 負け |
| donchian_momentum_breakout | 33 | **−7.81p** | 🔴 負け |
| **overall** | **6524** | **−1.58p** | 🔴 負け |

3/4 が EV<0 + overall EV<0。dedup bypass はこれらの負けを 2 倍に増幅 →
**ユーザー判断基準「勝てているなら問題ない、負けが増えるならミス」に照らして fix 対象**。

加えて `dedup_status.targets = ["vsg_jpy_reversal", "rsk_gbpjpy_reversion", "mqe_gbpusd_fix"]`
の 3 戦略のみが flag 検出対象になっており、実際に重複している上記 4 戦略は
audit pipeline からも漏れている。

## Investigation targets (Codex must verify)

1. **`_maybe_reserve_signal_emit` の呼び出し経路を全 grep**: `_tick_entry` と shadow_emit
   ループ以外に signal emit path が存在しないか確認。例えば:
   - `_open_shadow_emit_trade` を直接呼ぶ他箇所
   - hourly engine / scalp 単独ループ
   - watchdog / exposure restore / replay path
2. **counter が 0 の原因**:
   - 経路が走っていない (path bypass)
   - try/except で握りつぶされて counter ++ 前に raise
   - `self._dedup_stats` を別オブジェクトで上書き / リセット
   - thread-local で別インスタンス参照
3. **`hydrated_from_db: 0` の原因**:
   - `_db.get_recent_signal_emits(window_sec=120)` が空を返している
   - 該当テーブル / index 不在
   - try/except で握り潰し
4. **`runtime_dedup_dict_size: 0`**: ↑が原因なら自明だが、念のため `_recent_signal_emits`
   が他箇所で `= {}` リセットされていないか確認

## Files & line refs

- `modules/demo_trader.py:618-642` — `_dedup_stats` 初期化 + hydration
- `modules/demo_trader.py:3236-3247` — `_tf_to_window_sec`
- `modules/demo_trader.py:3249-3310` — `_maybe_reserve_signal_emit` 本体
- `modules/demo_trader.py:3782-3799` — primary path 呼び出し (`_tick_entry`)
- `modules/demo_trader.py:3145-3216` — shadow_emit ループ呼び出し
- `modules/demo_trader.py:825-` — `_open_shadow_emit_trade` (直接呼ばれる他経路がないか)
- `modules/demo_db.py:` — `get_recent_signal_emits` SQL (hydration ソース)
- `app.py` — `/api/admin/dedup_status` route

## Required changes

### 1. 原因特定

Codex must:
- `grep -rn "open_shadow_emit_trade\|self\._open_trade\|_oanda\.open_trade\|self\._db\.insert.*demo_trades" modules/`
- 各 signal emit path で `_maybe_reserve_signal_emit` を**通っていない**経路を列挙
- 列挙結果を final.md に table で報告（path / line / 呼び出し有無）

### 2. 全 emit path に dedup gate を強制

漏れている path に `_maybe_reserve_signal_emit` を追加。仕様:
- key = (entry_type, instrument, signal)
- window_sec = `_tf_to_window_sec(tf)`（tf 不明な path は最低 60s）
- `_path` パラメータでどこからの呼び出しか区別 ("primary" / "shadow" / "watchdog" / "replay" etc.)
- 既存の `_dedup_stats` counter を新 `_path` でも増やす

### 3. hydration 失敗の修正

`hydrated_from_db: 0` の原因を特定して修正：
- `get_recent_signal_emits` が空を返すなら SQL を実 demo_trades テーブルで動作確認
- try/except で握りつぶしていれば log を吐く

### 4. flag target を全 SHADOW 戦略に拡大

`dedup_status.targets` が 3 戦略固定なので、すべての shadow_emit 経由戦略を
カバーするように拡張（hardcoded list ではなく `demo_trades` の SHADOW 戦略を動的取得）。

### 5. Tests

`tests/test_dedup_gate_all_paths.py`:
- すべての signal emit path で `_maybe_reserve_signal_emit` が呼ばれることを assert
- 同一 (entry_type, instrument, signal) を window 内で 2 回呼ぶ → 2 回目は blocked
- hydration: DB に 60s 以内のレコードがある状態で startup → `_recent_signal_emits` に入る
- multi-thread race: 同一 key を 2 thread が同時 reserve → 1 個だけ pass

## Acceptance criteria

1. Render redeploy 後 1h 経過し `/api/admin/dedup_status` で
   - `primary_called > 0`、`shadow_called > 0`
   - `runtime_dedup_dict_size > 0`
   - `hydrated_from_db > 0`（直近 closed trade があれば）
2. 同一 (instrument, entry_price, direction, strategy) で 60s 以内に 2 件以上 OPEN している
   ペアが open_trades から消える（または `dedup_violation=1` でフラグ立つ）
3. `tests/test_dedup_gate_all_paths.py` PASS
4. 全 suite: `python3 -m pytest tests/ -x -q` PASS
5. `scripts/check.py` 6/6 pass
6. Final report に **emit path 監査 table**（どの path が gate を通り、どの path が通らないか）
   + **修正後 6 ペア重複の解消 evidence**（再現テストでブロック）

## Out of scope (explicitly NOT do)

- DO NOT touch `_tf_to_window_sec` の window 設定（既に audit 済み）
- DO NOT change strategy logic（fire 条件 / TP/SL / confidence threshold）
- DO NOT modify oanda_audit twin-meaning（別タスク `20260519-1832-fix-pyr-strategy-attribution-and-dedup.md` の領域）
- DO NOT modify pyramid logic (PYR Group A/B/C — 上記別タスクと directly重なるので merge せず別 PR)

## Memory references

- `lesson-shadow-emit-dedup-2026-04-30` — 元の dedup gate 設計
- `rsk bar-close gate 未修正 R3 pending` — vsg/rsk per-bar dedup 欠落 (本件と同根)
- `feedback_live_shadow_separation` — Live/Shadow分離、Shadow汚染で景色反転
- `feedback_label_empirical_audit` — ラベル実測主義 (本件 N水増しがこれの violation)
- 関連 queue task: `20260519-1832-fix-pyr-strategy-attribution-and-dedup.md` (PYR side、本件と協調)

## Verification (Codex must run before reporting done)

```bash
python3 -m pytest tests/test_dedup_gate_all_paths.py -v
python3 -m pytest tests/ -x -q
python3 scripts/check.py
# Local smoke: simulate same (entry_type, inst, signal) twice within window → second blocked
git diff --stat HEAD
git status
git stash list   # ensure nothing leaked to stash
```

Final report MUST include:
- emit path 監査 table (path / dedup gate 呼び有無 / 修正後の状態)
- 修正前後の `runtime_dedup_stats` 比較（ローカル simulator or unit test 出力）
- 6 ペア重複再現テストの結果（修正後ブロックされること）
