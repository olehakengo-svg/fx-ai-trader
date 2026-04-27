# Lesson: TREND_BULL Gate Over-block (2026-04-27, rule:R3)

## Symptom
- `streak_reversal × USD_JPY` PAIR_PROMOTED にもかかわらず production で **Live N=0 / Shadow N=4** (全 LOSS)
- ELITE_LIVE 3戦略 (session_time_bias / trendline_sweep / gbp_deep_pullback) が 2026-04-24 elite-freeing-patch (c195d16) 以降も Live fire = 0 継続
- M1 (commit 641bfe4) で `spread_sl_gate` に ELITE_LIVE 例外を入れたが、post-deploy 4 時間で ELITE_BYPASS ログ・ELITE Live fire が共にゼロ

## Root Cause
`modules/demo_trader.py` の **DT TREND_BULL TF bypass gate** (旧 line 3046-3056) が:

```python
if (_base_mode == "daytrade" and _regime_type_r == "TREND_BULL"
        and not _is_mr_entry):    # ← negation form
    _is_shadow = True
```

- 「TF戦略 (ema_cross / sr_fib_confluence / sr_break_retest) が TREND_BULL で WR=0%」が当初の根拠
- だが実装は **`_RANGE_MR_STRATEGIES` 未登録の全戦略** (= negation) を一括 shadow 化
- `_RANGE_MR_STRATEGIES = {bb_rsi_reversion, macdh_reversal, fib_reversal, vol_surge_detector, eurgbp_daily_mr, dt_bb_rsi_mr, dt_sr_channel_reversal}` には:
  - `streak_reversal` が KB 上 MR 分類だが未登録 → 過剰 block
  - `session_time_bias`, `gbp_deep_pullback` (ELITE_LIVE) も未登録 → 過剰 block
  - `trendline_sweep` (ELITE_LIVE) は `_DT_TREND_STRATEGIES` に該当 → 妥当 block だが ELITE 例外なし

そして直前の RANGE gate (line 3024-3040) は **positive list** (`_DT_TREND_STRATEGIES`) を使う**正しい実装**だった。**TREND_BULL gate 単独で対称性を崩していた**。

`mtf_gate_action=kept`、`gate_group=mtf_gated` であってもこの gate が earlier に発火するため、PAIR_PROMOTED / ELITE_LIVE 例外をかけた MTF / Q4 / Phase0 / spread_sl_gate (M1) より上流で `_is_shadow=True` がセットされていた。

## Fix (rule:R3 構造バグ)
1. **Positive list 化**: `not _is_mr_entry` → `entry_type in _DT_TREND_STRATEGIES`
2. **対称な ELITE_LIVE / PAIR_PROMOTED 例外** を RANGE gate と TREND_BULL gate の両方に追加 (`_regime_gate_exempt`)

```python
_regime_gate_exempt = (
    entry_type in self._ELITE_LIVE
    or (entry_type, instrument) in self._PAIR_PROMOTED
)
# RANGE
if (... and entry_type in _DT_TREND_STRATEGIES and not _regime_gate_exempt): ...
# TREND_BULL
if (... and entry_type in _DT_TREND_STRATEGIES and not _regime_gate_exempt): ...
```

## Why rule:R3
- 算数破綻ではないが**構造的 execution path bug** (gate 1 個が 4 戦略の Live promotion を全停止)
- 365日BT は不要 — 既存 PAIR_PROMOTED / ELITE_LIVE の pre-reg (BT STRONG / WF クロスTF stable) を尊重して通すだけ
- 後段の MTF / Q4 / Phase0 / spread_sl_gate / Q4 gate exemption と一貫させる

## Verification Pre-req
- 511 tests pass (回帰なし)
- AST parse OK
- Tokyo session で streak_reversal × USD_JPY × BUY が _is_shadow=False で発火することを post-deploy で確認

## Expected Effect

### Direct (intended) targets
| Strategy | Pair | Pre-fix | Post-fix |
|---|---|---|---|
| streak_reversal | USD_JPY | Shadow only (N=4 全 LOSS, 全 TREND_BULL) | Live 復活 (PAIR_PROMOTED 通過) |
| session_time_bias | any | Shadow (TREND_BULL 時) | Live (ELITE_LIVE 通過) |
| gbp_deep_pullback | any | Shadow (TREND_BULL 時) | Live (ELITE_LIVE 通過) |
| trendline_sweep | any | Shadow (RANGE/TREND_BULL 両方) | Live (ELITE_LIVE 通過) |

### Side-effect (expanded scope) — UNIVERSAL_SENTINEL 系
positive list 化に伴い、TREND_BULL × daytrade で**新たに通過し得る戦略**:

- 非 FORCE_DEMOTED, 非 _RANGE_MR_STRATEGIES, 非 _DT_TREND_STRATEGIES, 非 PAIR_PROMOTED の戦略群
- 例: liquidity_sweep, gotobi_fix, vix_carry_unwind (non-PP version), trend_rebound,
  london_close_reversal, dt_fib_reversal, dt_sr_channel_reversal, etc.
- これらは `_is_promoted()` が default True を返すため、N<10 sentinel lot で発火可能

**評価**: 原則 #1「マーケット開いてる間は攻める」+ #4「攻撃は最大の防御 — データ蓄積優先」と整合。
sentinel 戦略は本来 0.01 lot で観察対象であり、TREND_BULL のみ過剰 block されていたのは
gate の意図 (TF 戦略 block) からの逸脱だった。post-deploy で sentinel 発火頻度を観察し、
予想外の Live promotion が発生しないかを daily_live_monitor.py で監視する。

### Negative scope guard
- `_FORCE_DEMOTED` 戦略 (16+ entries) は `_is_promoted()=False` で line 4401 catch-all が `_is_shadow=True` を強制 → 影響なし
- Q4 gate (bb_rsi_reversion / ema_cross / ema_trend_scalp / fib_reversal at conf>69) は別レイヤーで継続
- spread_sl_gate (M1) と Phase0 gate も別レイヤーで継続

## Related Lessons
- [[lesson-cell-audit-bt-required-2026-04-27]] — BT/KB と Live data の対応関係
- [[lesson-mtf-gate-inversion-observation-2026-04-23]] — 同類 gate inversion bug
- [[lesson-late-stage-signal-override]] — 上流 gate が下流 exemption を無効化する pattern

## Future Audit
- 次回 regime / safety gate を新設する際は **positive list** + **明示的 ELITE_LIVE / PAIR_PROMOTED / PRIME 免除** を SOP として記載 (本 lesson から CLAUDE.md へ昇格候補)
- `_RANGE_MR_STRATEGIES` と `_DT_TREND_STRATEGIES` の **両方に未登録の戦略**は今後も発生し得る → audit で抽出する script (`tools/regime_gate_coverage.py`) を future task に
