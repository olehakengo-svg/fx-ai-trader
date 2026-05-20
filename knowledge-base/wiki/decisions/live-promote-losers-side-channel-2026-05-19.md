# LIVE_PROMOTE_LOSERS Side-Channel — 2026-05-19

**Rule**: R3 (Immediate / 構造バグ)
**Status**: IMPLEMENTED
**Author**: Claude (quant-analyst harness)

## 問題

`xs_momentum_rsi`×USD_JPY (2026-05-13 PAIR_PROMOTED user override, Live promote 意図) と `macd_rsi_pullback` (2026-05-14 SCALP_SENTINEL shadow-first) は登録から **4 London-NY セッション経過 (2026-05-14 → 2026-05-19) しても prod 0 fire**。

同じ tick 上で base `xs_momentum` は 5 USD_JPY shadow を発火 (2026-05-14 production trades 監査済) しているため、データ availability や session gate の問題ではない。

## 根本原因

`DaytradeEngine.select_best()` の **max-score 単一勝者** セマンティクス。本番 tick で `xs_momentum_rsi` (score ~5.6) は `session_time_bias` / `london_fix_reversal` / `vix_carry_unwind` (score 6.0-6.5) に競り負けて捨てられる。`split_shadow_always()` の対象 frozenset にも未登録だったため shadow trade としても拾われず、完全に消失していた。

これは「PAIR_PROMOTED で Live 発火」「SCALP_SENTINEL で shadow N 蓄積」の宣言と select_best の挙動が矛盾している R3 構造バグ。

## 修正方針

### Option A: SHADOW_ALWAYS baseline 拡張 (安全ネット)

`DaytradeEngine.SHADOW_ALWAYS_STRATEGIES` に `xs_momentum_rsi`/`macd_rsi_pullback` を追加。primary 競争敗北時に `_db.open_trade(is_shadow=True)` で N 蓄積を保証する。

### Option B: LIVE_PROMOTE_LOSERS side-channel (Live 発火パス)

新 frozenset `LIVE_PROMOTE_LOSERS = {xs_momentum_rsi, macd_rsi_pullback}` と `split_live_promote_emits()` を導入。app.py の daytrade sig builder で `live_promote_emit_signals` を sig に積み、`demo_trader._tick()` が **`_tick_entry` を再呼び出し** する。

`_tick_entry` 経由のため:
- PAIR_PROMOTED USD_JPY 緩和 (spread_sl_gate / live_tier_exempt) が自然に効く
- slot/hedge/dedup で詰まれば自動 shadow 降格
- 60s dedup は primary と key 空間共有 (`_maybe_reserve_signal_emit`) で二重発火を抑止

## 影響範囲

- `strategies/daytrade/__init__.py`: `SHADOW_ALWAYS_STRATEGIES` 拡張 + `LIVE_PROMOTE_LOSERS` 新設 + `split_live_promote_emits()` メソッド
- `app.py`: daytrade sig builder (1箇所) に `live_promote_emit_signals` payload 追加 (~29行)
- `modules/demo_trader.py`: `_tick()` に live_promote_emits ループ追加 (~64行)
- `tests/test_live_promote_emits.py`: 9 ユニットテスト (membership / split 挙動 / edge case)

## 検証

- ユニットテスト 9/9 PASS
- フルテスト 1575 passed (pre-existing failures は無関係 — PYR attribution WIP / Python 3.9 構文)
- check.py 6/6 通過

## Pre-reg

Deploy 後 48h で 1st KPI check:

| 指標 | 期待 | 失敗時 |
|---|---|---|
| `xs_momentum_rsi` USD_JPY total trades | ≥ 1 | side-channel コード経路の dedup/gate 監査 |
| `macd_rsi_pullback` total trades | ≥ 1 (shadow可) | 同上 |
| 既存 SHADOW_ALWAYS (rsk_gbpjpy_reversion) 発火率 | 維持 | regression 確認 |

7日経過時点で N≥10 蓄積したら R2 watchdog (EV<0 → demote) で自然 cleanup される。

## 関連

- [feedback_shadow_first_quant_architecture.md] — Shadow-first quant architecture
- [feedback_live_shadow_separation.md] — LIVE/Shadow 分離必須
- 旧 SHADOW_ALWAYS 修正: `sr-strategies-signal-track-2026-04-28.md`
