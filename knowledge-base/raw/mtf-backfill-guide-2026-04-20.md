# MTF Regime Backfill — Execution Guide (2026-04-20)

## Status
- **スクリプト**: `scripts/backfill_mtf_regime.py` (Agent #3 作成、c28ee91)
- **Dry-run 実行済** (ローカル、OANDA client 経由): 1,944 件 label 可能を確認
- **SQL 生成済** (`/tmp/backfill_mtf_regime.sql`、1,950 行): Render 適用待ち
- **再現**: 任意時点で再実行して最新 trades をカバー可能

## 効果

| Label | 新規件数 | 影響 |
|---|---|---|
| range_tight | 540 (27.8%) | ベースカバレッジ強化 |
| trend_up_weak | 483 (24.8%) | 同 |
| range_wide | 482 (24.8%) | 同 |
| **trend_down_strong** | **213 (11.0%)** | 🎯 **Phase E 検証の穴埋め** (現状ゼロカバレッジ) |
| uncertain | 147 (7.6%) | 除外候補 |
| trend_up_strong | 79 (4.1%) | 同 |

Agent #3 (`regime-strategy-2d-2026-04-20.md`) が「trend_down が未観測のため Phase E の
bb_rsi_reversion trend_down MR / fib_reversal trend_down TF の非対称性を post-cutoff
で検証できない」としていた問題が、この backfill で解消される。

## 実行手順 (Render 上で)

### Step 1: 最新 trades snapshot 取得
```bash
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000" > trades_all.json
```

### Step 2: SQL 生成
```bash
python3 scripts/backfill_mtf_regime.py --trades-json trades_all.json \
    --write sql --output backfill_mtf_regime.sql
```

### Step 3: Render Shell で適用
```bash
# Render Shell アクセス (Pro プラン必要)
sqlite3 /var/data/demo_trades.db < backfill_mtf_regime.sql

# 検証
sqlite3 /var/data/demo_trades.db \
    "SELECT mtf_regime, COUNT(*) FROM demo_trades WHERE mtf_regime IS NOT NULL AND mtf_regime != '' GROUP BY mtf_regime"
```

### Step 4: Regime 2D 再走査 (backfill 後)
```bash
# Agent #3 の再実行ブロックは /tmp/fx-regime-2d-analysis/run_analysis.py (参照)
# または regime-strategy-2d-2026-04-20.md の手順に従う
```

## idempotent 性
- SQL の各 UPDATE に `WHERE id=X AND (mtf_regime IS NULL OR mtf_regime='')` 付与
- 既に label された trade は skip される → **複数回実行安全**

## ロールバック
- 各 UPDATE は単一 BEGIN/COMMIT トランザクション内
- 失敗時は COMMIT 前なら自動ロールバック
- 成功後の undo が必要なら: `UPDATE demo_trades SET mtf_regime=NULL WHERE id IN (...)` の逆 SQL を別途生成

## 関連
- [[regime-strategy-2d-2026-04-20]] — backfill 未実行時の分析 (Gate 通過ゼロ)
- [[lesson-all-time-vs-post-cutoff-confusion]] — データウィンドウの誤用事例
- `scripts/backfill_mtf_regime.py` — 実行スクリプト本体
