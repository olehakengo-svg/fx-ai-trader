---
date: 2026-04-29
phase: Phase 10 G2
rule: R3
status: in-progress (1/3 strategies committed)
related:
  - "~~[[../../../raw/audits/never_logged_diagnosis_2026-04-28]]~~"
  - "~~[[../../../raw/audits/production_routing_audit_2026-04-28]]~~"
  - "[[../lessons/lesson-select-best-bottleneck-2026-04-28]]"
  - "[[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]]"
---

# Phase 10 G2: NEVER_LOGGED 3 戦略 production routing 修正

## 背景

Phase 10 G1 (`raw/audits/never_logged_diagnosis_2026-04-28.md`) は `production demo_trades` に **NEVER_LOGGED** な 7 戦略のうち 3 つで **365d × 5 majors の BT 検証で >0 fire** を確認した:

| Strategy | BT signals (365d) | Pair | Production 31d |
|---|---|---|---|
| vsg_jpy_reversal | 331 (EUR_JPY 145 + GBP_JPY 186) | JPY crosses | 0 fire |
| rsk_gbpjpy_reversion | 182 (GBP_JPY only) | GBP_JPY | 0 fire |
| mqe_gbpusd_fix | 20 (GBP_USD only, month-end-only) | GBP_USD | 0 fire |

残 4 戦略 (`sr_anti_hunt_bounce` / `sr_liquidity_grab` / `cpd_divergence` / `vdr_jpy`) は BT でも 0 fire — 真の entry-condition 不発、別タスク (G2 緩和) で対応。

## 仮説検証

| # | 仮説 | 検証手段 | 結果 |
|---|---|---|---|
| H1 | production の signal 関数が BT より strict | 3 戦略 evaluate() を read — backtest_mode flag 未参照 | ❌ 同一コードパス |
| H2 | cooldown / max_open / spread gate で全 block | 候補は select_best 後段の `_tick_entry` でしか gate に当たらない | ❌ select_best で消える |
| H3 | pair scope filter bug | dispatcher は all 5 majors を loop。`_ALLOWED_SYMBOLS` filter は string compare で正しく動作 | ❌ pair filter 健全 |
| **H4** | **select_best() max-score bottleneck (G0a と同根)** | 各戦略の score 設計を読む | **✅ 確定** |

### Score 分布の決定的差

| Strategy | score 式 | 範囲 |
|---|---|---|
| vsg_jpy_reversal | `4.0 + min(2.0, surprise - 1.0)` | [4.0, 6.0] |
| rsk_gbpjpy_reversion | `4.0 + min(2.0, abs(z) - 2.0)` | [4.0, 6.0] |
| mqe_gbpusd_fix | `4.5` (固定) | 4.5 |
| 確立済 strategy 群 (ema_cross / sr_break_retest / london_session_breakout / 他) | 多くが score 6+ | 5-9 |

`DaytradeEngine.select_best(candidates) = max(candidates, key=lambda c: c.score)` のため、3 戦略は **構造的に primary slot を取れない**。Live にも Shadow にも DB 永続化されない (現 `SHADOW_ALWAYS_STRATEGIES = frozenset()`)。

これは `lesson-select-best-bottleneck-2026-04-28.md` で identified された 30/54 NEVER-in-DB バケットの具体例。

## 修正方針 (R3)

`SHADOW_ALWAYS_STRATEGIES` に 3 戦略を追加 — sr_anti_hunt_bounce / sr_liquidity_grab で確立された SHADOW_EMIT 機構の再利用:

1. `DaytradeEngine.split_shadow_always()` が primary 敗北の SHADOW_ALWAYS 戦略候補を抽出
2. `app.py` が `shadow_emit_signals` payload にシリアライズ
3. `modules/demo_trader.py` が `is_shadow=1` で `_db.open_trade()` を呼ぶ

R2 demotion 出口は維持: N>=30 かつ Live EV<0 を実測したら除外 (sr_* と同 flow)。

## 実施状況

| Strategy | Commit | Status |
|---|---|---|
| vsg_jpy_reversal | `9fa1501` | ✅ Committed |
| rsk_gbpjpy_reversion | — | 🚫 BLOCKED |
| mqe_gbpusd_fix | — | 🚫 BLOCKED |

## ブロッカー

並列セッションが新規 scalp 戦略 2 件を実装中だが pre-commit consistency check 通過前の状態:

- `strategies/scalp/mtf_counter_trend_scalp.py` (untracked, `enabled=True`)
- `strategies/scalp/mtf_trend_follow_scalp.py` (untracked, `enabled=True`)
- `strategies/scalp/__init__.py` (M, 上記 import 追加と推測)
- 関連 wiki page 2 件 (untracked)

`scripts/check.py` が:
```
❌ 'mtf_counter_trend_scalp' (mtf_counter_trend_scalp.py) → QUALIFIED_TYPES 未登録 (enabled=True)
❌ 'mtf_trend_follow_scalp' (mtf_trend_follow_scalp.py) → QUALIFIED_TYPES 未登録 (enabled=True)
```
を返し pre-commit hook で全 commit がブロックされる。私の `strategies/daytrade/__init__.py` 変更とは独立した collision のため、並列セッションが `modules/demo_trader.py` の `QUALIFIED_TYPES` を更新するまで rsk + mqe の commit を保留。

vsg_jpy_reversal (commit `9fa1501`) は parallel session のファイルが untracked になる前の時点で commit が通った可能性が高い (タイミング差)。

## 失敗した没ルート

- **Score boost (Option A)**: 3 戦略の score baseline を 6.0+ に底上げ → 確立済 strategy と競合させる
  → **棄却**: HARKing。BT WR (vsg 55-59% / rsk 55% / mqe 70%) を score に直接織り込めば結果に対する条件付け = quant 規律違反。
- **HTF agreement gate 緩和**: 3 戦略専用に HTF Hard Block を bypass
  → **棄却**: 当該戦略は HTF にもとから違反する direction を取らない MR fade。HTF gate は無関係。
- **parallel-session の新規 scalp を私が登録**: collision を避けるため不採用。

## Production 観察計画

- vsg_jpy_reversal: BT firing rate 1.082% × 15m bars on EUR_JPY/GBP_JPY ≈ **1 fire / 22h**
- 24h 内に最低 1 件の `is_shadow=1` entry 発生を期待 (deploy 完了後)。
- N=30 到達まで ~30 日を見込む。Render Postgres でモニタリング。

## 次アクション

1. ✅ `9fa1501` を main に push (auto-deploy → Render)
2. 24-48h 後に `demo_trades` で `entry_type='vsg_jpy_reversal'` × `is_shadow=1` を確認
3. 並列セッションの mtf_*_scalp 登録完了後に rsk + mqe commit を retry
4. N=30 / EV<0 で R2 demotion threshold 監視 (Phase 8 cell_edge_audit に合流)
