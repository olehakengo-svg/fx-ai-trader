---
id: 20260507-1515-r2-critical-demote-and-schedule
title: "[R2-Critical-Demote] 12 CRITICAL cell shadow 除外 + R2 alert 6h scheduled task 化"
owner: codex
status: queued
priority: P0
created_at: 2026-05-07T15:15:00+0900
roadmap_gate: "R2 alert tool 初回実行で 12 CRITICAL 検出 → データ汚染源を即時除外、6h 自動監視継続"
rule: R2
related:
  - tools/shadow_promote_r2_alert.py
  - knowledge-base/raw/audits/shadow-promote-r2-alert-2026-05-07-0325.md
  - tools/volume_live_promotion_watchdog.py
---

# 0. 背景

2026-05-07 03:25 UTC の R2 alert 初回 run で **12 CRITICAL cell** 検出 (N≥30, EV<0):

| Strategy | Instrument | N | EV | PF |
|---|---|---|---:|---:|
| bb_rsi_reversion | EUR_USD | 51 | -0.75 | 0.66 |
| bb_rsi_reversion | GBP_USD | 34 | -2.31 | 0.34 |
| bb_rsi_reversion | USD_JPY | 86 | -0.28 | 0.90 |
| ema_trend_scalp | EUR_USD | 79 | -0.91 | 0.63 |
| ema_trend_scalp | GBP_USD | 98 | -0.78 | 0.75 |
| ema_trend_scalp | USD_JPY | 215 | -1.44 | 0.61 |
| engulfing_bb | USD_JPY | 47 | -1.95 | 0.53 |
| sr_channel_reversal | EUR_USD | 31 | -1.18 | 0.62 |
| sr_channel_reversal | USD_JPY | 97 | -1.77 | 0.36 |
| sr_fib_confluence | EUR_JPY | 43 | -13.06 | 0.17 |
| sr_fib_confluence | GBP_JPY | 63 | -6.71 | 0.55 |
| sr_fib_confluence | USD_JPY | 30 | -3.71 | 0.67 |

shadow N 蓄積を継続するとそのまま Wave 5 Bonferroni 補正下 promotion 判定の **誤誘導要因**。**即時 shadow 除外が必要**。

# 1. 仕様

## 1.1 12 CRITICAL cell の demote (per-cell)

各 cell について **source 特定 → 適切な demote 経路**:

### A. ソース判定フロー

各 cell について:
1. **Round 1+2+3 の `*_REDESIGN_V2_SHADOW_PROMOTE=1` env から登録か?**
   - YES → **demote 方法: env value を空に or 削除する list を生成 (user 手動操作向け)**
   - もしくは strategy 内コードで env value を `0` 扱いにする short-circuit
2. **`SHADOW_ALWAYS_STRATEGIES` hardcoded か?**
   - YES → **demote 方法: hardcoded set から除外**
3. **元の v1 shadow worker (どこで登録されているか不明)**
   - YES → **demote 方法: strategy 内 `worker_modes` 設定を編集 or pair 単位 disable**

### B. cell 単位 (pair-specific) demote

戦略全体ではなく **(strategy, pair) cell 単位** で demote:
- 例: bb_rsi_reversion は 3 pair 全部 CRITICAL → 戦略全体 disable
- 例: engulfing_bb は USD_JPY のみ CRITICAL、EUR_USD は WARN だけ → USD_JPY のみ disable (EUR_USD は WARN なので demote 保留)
- 実装: `strategies/<strategy>/<file>.py` 内で `(symbol, pair)` ごとの emit 判定追加 or `_FORCE_DEMOTED` set を pair-specific に拡張

### C. 注意事項

- **`sr_fib_confluence GBP_USD` は今日 PAIR_PROMOTED Live 化対象** → demote しない (pair 別選別の正解パターン)
- 同様に `engulfing_bb` は `engulfing_bb_redesign_v2` (Round 1 enabled) と元の `engulfing_bb` v1 が混在する可能性 → 慎重に v1 だけ demote

## 1.2 R2 alert scheduled task 化

`tools/shadow_promote_r2_alert.py` を **6h ごと自動実行**:

オプションA (推奨): scheduled-tasks MCP 経由
- name: `shadow-promote-r2-alert-6h`
- schedule: `0 */6 * * *` UTC (00:00, 06:00, 12:00, 18:00 UTC)
- command: `python3 tools/shadow_promote_r2_alert.py --json`
- output: stdout JSON + Markdown report 自動生成

オプションB: GitHub Actions cron
オプションC: Render Cron Job

→ **オプションA を採用** (既存 scheduled-tasks 機構と整合)

実装:
- `.github/workflows/r2-alert-scheduled.yml` または scheduled-tasks 設定ファイル追加
- 既存 `scheduled-tasks` パターン (例: `cell-deepdive-7strategies-weekly`) を参照

## 1.3 Demote 実装パターン (recommended)

新規ファイル `modules/shadow_demote_registry.py`:

```python
# Per-cell shadow worker disable list
# Updated by R2 critical demote task
SHADOW_DEMOTED_CELLS = frozenset({
    ("bb_rsi_reversion", "EUR_USD"),
    ("bb_rsi_reversion", "GBP_USD"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("ema_trend_scalp", "EUR_USD"),
    ("ema_trend_scalp", "GBP_USD"),
    ("ema_trend_scalp", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),  # v1 demote, v2 (REDESIGN_V2 env) は別 path で active
    ("sr_channel_reversal", "EUR_USD"),
    ("sr_channel_reversal", "USD_JPY"),
    ("sr_fib_confluence", "EUR_JPY"),
    ("sr_fib_confluence", "GBP_JPY"),
    ("sr_fib_confluence", "USD_JPY"),
})

def is_shadow_demoted(strategy: str, instrument: str) -> bool:
    return (strategy, instrument) in SHADOW_DEMOTED_CELLS
```

各 strategy の shadow emit 判定箇所に hook:
```python
from modules.shadow_demote_registry import is_shadow_demoted
if is_shadow_demoted(strategy, instrument):
    return None  # skip emit
```

## 1.4 R2 watchdog auto-update integration

`tools/shadow_promote_r2_alert.py` に **`--apply-demote` flag** 追加:
- CRITICAL cell を `SHADOW_DEMOTED_CELLS` に追加する PR generation (read-only output)
- 実際の編集は別 commit で行う (auto-merge は人間判断)

# 2. 失敗テスト (TDD)

`tests/test_shadow_demote_registry.py`:
- `is_shadow_demoted("bb_rsi_reversion", "EUR_USD")` → True
- `is_shadow_demoted("bb_rsi_reversion", "EUR_JPY")` → False
- `is_shadow_demoted("sr_fib_confluence", "GBP_USD")` → False (PAIR_PROMOTED Live 化対象)
- `is_shadow_demoted("sr_fib_confluence", "EUR_JPY")` → True

`tests/test_shadow_emit_skip_demoted.py`:
- 各 strategy の signal 生成テストで demoted cell が emit されないこと

# 3. データ分離

- BT: 不使用
- Shadow: demote 対象は is_shadow=1 の `(strategy, pair)` cell
- Live: 影響なし (Live は別 path)
- OANDA: 影響なし

# 4. クオンツ条件

- **Rule 2 (fast & reactive)**: N>=30 EV<0 で即時 shadow 停止 (R2 demotion 既存 pattern)
- **データ汚染源除去**: Wave 5 Bonferroni 補正前提のクリーンデータ確保
- **engulfing_bb v1 demote の慎重さ**: Round 1 で env enabled な v2 path とは別判定を確保

# 5. Acceptance Criteria

- `modules/shadow_demote_registry.py` 新規作成
- 12 CRITICAL cell が `SHADOW_DEMOTED_CELLS` に含まれる
- 各 strategy の emit hook が demote 判定を呼び出す (grep で確認)
- failed tests 緑
- R2 alert scheduled task 設定 (cron file 作成)
- `tier_integrity_check.py --check` ERROR=0
- 1回の R2 alert run で CRITICAL 数が 12 から減少することを確認 (実 API 経由)

# 6. Out of Scope

- WARN 16 cell の demote (CRITICAL のみ対象、WARN は観察継続)
- env vars の自動削除 (user 手動対応)
- 12 cell の戦略丸ごと disable (cell 単位 demote のみ)

# 7. Notes

- 12 CRITICAL のうちいくつかは元の v1 shadow worker、env と無関係に動いている可能性
- code edit が demote の唯一の確実手段
- `sr_fib_confluence GBP_USD` は今日 PAIR_PROMOTED Live 化対象なので慎重保護
- engulfing_bb USD_JPY: v1 demote しても v2 redesign (Round 1 ENGULFING_BB_REDESIGN_V2=1) は別 path で動き続けるべき
