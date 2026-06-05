---
id: 20260605-tp-hit-12cell-portfolio-validation
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-06-05
owner: claude
---

# TP-HIT 12-cell Pre-Registered Portfolio — 正式検証 (PF/Kelly/WF/Bonferroni)

**Rule classification**: R3 (shadow-first、quant validation、live promotion 前の statistical gate 測定)

## 背景 (司令塔の判断、変更禁止)

Claude Code が Render Production demo_trades.db を分解し、TP HIT を cell 単位 (entry_type × instrument × direction) で分析。
forward-relevant filter (N≥20 ∧ 全期間EV>0 ∧ 直近コホート≥2026-05-16 EV>0 ∧ n2≥5) を満たす **12 cell** を
pre-registered portfolio として固定した。**この 12 cell リストは凍結 (post-hoc 追加・差し替え禁止、memory `W3-3 post-hoc selection 罠`)。**

平均ペア日次相関 −0.006 (ほぼ無相関)、equal-risk(inv-vol) weight で maxDD 381→278pip。
ただし生 EV は m=116 cell からの選抜値であり、**PF/Kelly/WF/Bonferroni を測って初めて promotion 可否を判断できる** (memory `部分的クオンツの罠`)。

### 凍結 12 cell (entry_type | instrument | direction)
```
dt_bb_rsi_mr            | EUR_USD | SELL
dt_sr_channel_reversal  | USD_JPY | BUY
dt_bb_rsi_mr            | GBP_USD | SELL
wick_imbalance_reversion| EUR_USD | BUY
sr_fib_confluence       | EUR_USD | BUY
orb_trap                | GBP_USD | SELL
wick_imbalance_reversion| GBP_USD | BUY
trendline_sweep         | EUR_USD | SELL
dual_sr_bounce          | EUR_JPY | SELL
sr_anti_hunt_bounce     | EUR_JPY | BUY
dt_sr_channel_reversal  | EUR_JPY | BUY
rsk_gbpjpy_reversion    | GBP_JPY | BUY
```

## このタスクで Codex がやること

### 1. Shadow 実測ソース (一次データ) — Render Production が正

ローカル demo_trades.db は 2026-04-30 で stale。**一次ソースは Render Production**:
- Web API: `https://fx-ai-trader.onrender.com/api/demo/stats?...` (集計のみ、cell 分解不可)
- SSH 直: `ssh srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com 'sqlite3 /var/data/demo_trades.db < query.sql'`
  - 注意: 初回 hostkey 警告 `client_global_hostkeys_prove_confirm` が出るが接続は成立する。`2>&1 | grep -v global_hostkeys` で除去。

demo_trades の関連スキーマ (Codex は推測禁止、これを使う):
```sql
CREATE TABLE demo_trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trade_id TEXT UNIQUE, status TEXT DEFAULT 'OPEN', direction TEXT,
  entry_price REAL, entry_time TEXT, exit_price REAL, exit_time TEXT,
  sl REAL, tp REAL, pnl_pips REAL, pnl_r REAL, outcome TEXT,
  entry_type TEXT, confidence INTEGER, tf TEXT, reasons TEXT, regime TEXT,
  close_reason TEXT, mode TEXT, oanda_trade_id TEXT, instrument TEXT,
  is_shadow INTEGER DEFAULT 0, edge_cell_id TEXT DEFAULT ''
  -- (他列省略、上記が今回使用分)
);
```
TP 定義: `close_reason='TP_HIT' OR (close_reason='OANDA_SL_TP' AND outcome='WIN')`

### 2. 各 cell の statistical gate を測定 (shadow 実測ベース)

各 cell について以下を算出し JSON 出力:
- N, wins, WR
- **PF** (gross profit / gross loss, pnl_pips ベース)
- **Wilson 95% 下限 (生)** と **Bonferroni 補正 (m=116, α=0.05/116, z≈3.52) 下限**
- **EV (avg pnl_pips)** と bootstrap 95%CI (resample 10,000)
- **Kelly fraction** = WR − (1−WR)/RR、RR=avg_win_pip/avg_loss_pip
- **Walk-Forward 3-fold** (時系列 3 分割、各 fold の EV 符号一致を Sign test、memory `W3-2` の WF 3+folds 要件)
- 時間コホート: 前半(<2026-05-16)/後半(≥)別 EV (崩壊検知)

H1 Gate (memory `W3-1 H1 Gate`): N≥30 / Wilson_lo≥0.40 / EV≥0。各 cell の PASS/FAIL を明記。

### 3. ポートフォリオ合成検証 (BT は MASSIVE 必須)

memory `BT は MASSIVE 必須`: データソースは `data/cache/massive/*.parquet` を使う (Yahoo 禁止、60日制限で 365d BT 不可)。
利用可能 parquet 例: `data/cache/massive/{EUR_USD,GBP_USD,USD_JPY,EUR_JPY,GBP_JPY}_{5m,15m,1h}.parquet`

- 12 cell の戦略を該当 pair/TF で BT 再走 (各戦略の既存 BT runner を流用、無ければ shadow 実測のみで代替可)
- equal-risk(inv-vol) weight で日次合成 PnL 系列を構築
- **合成 maxDD / Calmar / 月次 Sharpe / 日次相関行列** を算出
- DD20% 上限サイジング下の月次リターン期待値 (生 + Bonferroni 保守係数0.5)

### 4. 成果物

- `bt-results/tp-hit-12cell-portfolio-2026-06-05.json` (cell 別 gate + 合成統計)
- `final.md`: 各 cell の Gate PASS/FAIL 表、promote 推奨 cell リスト (Gate 通過 ∧ WF 符号一致 ∧ Bonferroni 生存)、合成 DD/Calmar、月利期待値レンジ、棄却 cell とその理由
- git commit + origin/main push (memory `Codex stash leak`: stash 埋没禁止、必ず commit/push して final.md と git log/diff が一致すること)

## 制約・罠回避 (必読)
- **12 cell リスト凍結** (post-hoc 追加禁止)
- shadow 実測が真の estimator、BT は sanity (memory `Shadow-first quant architecture`)。BT に Live promotion 基準を要求しない
- XAU 除外 (memory `feedback_exclude_xau`)
- mock-only テストで PASS 報告禁止、実 API/実 DB E2E 必須 (memory `Codex mock-only テストの罠`)
- LIVE/Shadow 分離 (is_shadow=0/1)、混入禁止 (memory `LIVE/Shadow 分離必須`)
