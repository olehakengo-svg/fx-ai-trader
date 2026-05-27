---
id: 20260527-1300-sr-break-retest-cell-forensic
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-05-27
owner: claude
---

# sr_break_retest cell-level Win/Loss forensic audit

## 背景

`sr_break_retest` は現在 `FORCE_DEMOTED`、shadow N=222 WR=22.1% PnL=-694.3p で全 8 direction_cell が Wilson_bf_lo ≤ 0.19 と判定されている。しかし `/api/oanda/stats?strategy=sr_break_retest` で実 demo 約定を実測すると以下の不一致がある:

| pair/dir | shadow N | shadow WR | shadow EV | demo N (all-time) | demo WR | demo Pips |
|---|---|---|---|---|---|---|
| USD_JPY BUY | 52 | 32.7% | +0.16 | 11 | 54.5% | -2.0 |
| **USD_JPY SELL** | **18** | **0.0%** | **-7.29** | **26** | **57.7%** | **+35.5** |
| GBP_USD BUY | 42 | 26.2% | -1.43 | 20 | 45.0% | -22.0 |
| GBP_USD SELL | 30 | 30.0% | -3.29 | 17 | 35.3% | -21.8 |
| EUR_JPY SELL | 24 | 37.5% | +0.17 | 3 | 33.3% | -10.5 |
| EUR_JPY BUY | 15 | 0.0% | -6.33 | 0 | — | — |
| GBP_JPY BUY | 29 | 6.9% | -8.97 | 0 | — | — |
| GBP_JPY SELL | 12 | 16.7% | -5.16 | 0 | — | — |

🚨 **USD_JPY/SELL: shadow simulator は WR=0% / -7.29 EV と評価したが、実 demo は WR=58% / +35.5p**。Force-Demote の主因はこの 1 cell の simulator 誤評価の可能性。

加えて GBP_USD の demo 37 trades が **TP 0 / SL 37 / MC 0** で TP に一度も到達していない (構造的設計欠陥の可能性)。

[LIVE/Shadow 分離必須](feedback_live_shadow_separation.md) / [時間コホート整合](feedback_cohort_time_check.md) / [Spread 基準で MAFE 比較](feedback_spread_basis_for_mafe.md) 案件。

## 目的

`demo_trades` (本物の outcome) と `oanda_audit` (signal-side metadata) を join し、以下を実測決定:

1. USD_JPY/SELL +35.5p は **真のエッジ** か、それとも 26 サンプルの偶然か?
2. USD_JPY/SELL の shadow simulator はなぜ WR=0% と判定したか? (simulator バグ or 別 cohort?)
3. GBP_USD の TP 0/37 SL は何が原因か? (TP 距離 / spread / direction logic / volatility regime)
4. recommend: USD_JPY/SELL 単独 shadow 復活 / strategy 全体 reject / simulator 修正先 ?

## DB schema (paste-in, do not infer)

DB 本体は **`/var/data/demo_trades.db`** (Render persistent disk)。Local repo は SQLite-only 運用 (memory: [dexter FX Phase 0 完了](project_dexter_fx_phase0_2026_05_03.md))。

```sql
-- demo_trades (modules/demo_db.py 408-)
CREATE TABLE IF NOT EXISTS demo_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT UNIQUE,
    status          TEXT DEFAULT 'OPEN',
    direction       TEXT,            -- 'BUY' / 'SELL'
    entry_price     REAL,
    entry_time      TEXT,
    exit_price      REAL,
    exit_time       TEXT,
    sl              REAL,
    tp              REAL,
    pnl_pips        REAL,
    pnl_r           REAL,
    outcome         TEXT,
    entry_type      TEXT,             -- strategy name (e.g. 'sr_break_retest')
    confidence      INTEGER,
    tf              TEXT DEFAULT '15m',
    reasons         TEXT,
    regime          TEXT,
    dow_regime      TEXT,
    v2_regime       TEXT,
    edge_cell_id    TEXT DEFAULT '',
    confluence_score TEXT,
    confluence_details TEXT,
    layer1_dir      TEXT,
    score           REAL,
    close_reason    TEXT,             -- 'TAKE_PROFIT' / 'STOP_LOSS' / 'MARKET_CLOSE'
    ema_conf        INTEGER,
    sr_basis        REAL,
    -- ALTER columns:
    mode            TEXT DEFAULT '',
    oanda_trade_id  TEXT DEFAULT '',
    instrument      TEXT DEFAULT 'USD_JPY',
    signal_price    REAL DEFAULT 0,
    spread_at_entry REAL DEFAULT 0,   -- pips
    spread_at_exit  REAL DEFAULT 0,   -- pips
    slippage_pips   REAL DEFAULT 0,
    cooldown_elapsed REAL DEFAULT 0,
    close_analysis  TEXT DEFAULT '',
    mafe_adverse_pips   REAL,         -- max adverse excursion
    mafe_favorable_pips REAL,         -- max favorable excursion
    is_shadow       INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- oanda_audit (modules/demo_db.py 408-426)
CREATE TABLE IF NOT EXISTS oanda_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    demo_trade_id   TEXT,
    entry_type      TEXT,             -- strategy name
    direction       TEXT,
    instrument      TEXT,
    units           INTEGER DEFAULT 0,
    is_live         INTEGER DEFAULT 0,
    bridge_status   TEXT,              -- 'skipped' / 'sent' / 'filled'
    block_reason    TEXT DEFAULT '',
    oanda_trade_id  TEXT DEFAULT '',
    sr_strength     REAL,
    sr_touches      INTEGER,
    sr_days_span    REAL,
    sr_is_strong    INTEGER,
    sr_distance_atr REAL,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

NOTE: 公開 API 経由で確認したところ sr_break_retest の audit 203 行は **sr_strength/touches/days_span/is_strong/distance_atr が全 NULL**。このカラムは別 SR 戦略 (`sr_anti_hunt_bounce` / `sr_fib_confluence`) 専用で sr_break_retest は書き込んでいない。よって SR-feature による分解は不可能 — `reasons` カラム (JSON?) や `confluence_details` / `edge_cell_id` / `regime` 等で代替する。

## 分析タスク

### Phase A: 母集団確認 & Shadow/Demo 分離

```sql
-- A1: demo_trades の sr_break_retest 全件、shadow/non-shadow 別件数
SELECT is_shadow, COUNT(*) FROM demo_trades
WHERE entry_type='sr_break_retest' AND status='CLOSED'
GROUP BY is_shadow;

-- A2: oanda_audit 全件と demo_trades 全件の N 差分
SELECT
  (SELECT COUNT(*) FROM oanda_audit WHERE entry_type='sr_break_retest') AS audit_n,
  (SELECT COUNT(*) FROM demo_trades WHERE entry_type='sr_break_retest' AND status='CLOSED') AS demo_n,
  (SELECT COUNT(*) FROM demo_trades WHERE entry_type='sr_break_retest' AND status='CLOSED' AND is_shadow=1) AS demo_shadow_n,
  (SELECT COUNT(*) FROM demo_trades WHERE entry_type='sr_break_retest' AND status='CLOSED' AND is_shadow=0) AS demo_live_n;
```

判定:
- shadow.n=222 が demo_trades.is_shadow=1 と一致するか確認
- /api/oanda/stats N=82 が is_shadow=0 か、それとも別 filter (last 30d) によるものか確認

### Phase B: pair × direction × is_shadow × close_reason マトリクス

```sql
SELECT instrument, direction, is_shadow, close_reason,
       COUNT(*) AS n,
       SUM(CASE WHEN pnl_pips>0 THEN 1 ELSE 0 END) AS wins,
       ROUND(AVG(pnl_pips), 2) AS avg_pips,
       ROUND(SUM(pnl_pips), 1) AS tot_pips,
       ROUND(AVG(spread_at_entry), 3) AS avg_spread,
       ROUND(AVG(slippage_pips), 3) AS avg_slip,
       ROUND(AVG(mafe_favorable_pips), 2) AS avg_mfe,
       ROUND(AVG(mafe_adverse_pips), 2) AS avg_mae
FROM demo_trades
WHERE entry_type='sr_break_retest' AND status='CLOSED'
GROUP BY instrument, direction, is_shadow, close_reason
ORDER BY instrument, direction, is_shadow, close_reason;
```

per cell (instrument, direction, is_shadow):
- Wilson 95% lower bound
- **Bonferroni-adjusted Wilson lower bound (m=8)** ← MUST
- Wald CI for EV
- avg_pips (=EV)

### Phase C: USD_JPY/SELL 深掘り (the candidate edge)

```sql
-- C1: 全 trade 列挙
SELECT trade_id, entry_time, exit_time, entry_price, exit_price, sl, tp,
       pnl_pips, close_reason, mafe_favorable_pips, mafe_adverse_pips,
       spread_at_entry, slippage_pips, is_shadow,
       regime, dow_regime, v2_regime, reasons
FROM demo_trades
WHERE entry_type='sr_break_retest' AND instrument='USD_JPY' AND direction='SELL'
  AND status='CLOSED'
ORDER BY entry_time;

-- C2: hour-of-day, day-of-week 別 WR/EV
SELECT
  strftime('%H', entry_time) AS h,
  COUNT(*) AS n,
  SUM(CASE WHEN pnl_pips>0 THEN 1 ELSE 0 END) AS wins,
  ROUND(AVG(pnl_pips), 2) AS avg_pips
FROM demo_trades
WHERE entry_type='sr_break_retest' AND instrument='USD_JPY' AND direction='SELL'
  AND status='CLOSED'
GROUP BY h ORDER BY h;

-- C3: time-cohort split (前半 13 trades vs 後半 13 trades)
--      memory: [時間コホート整合]
WITH ordered AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY entry_time) AS rn,
         COUNT(*) OVER () AS tot
  FROM demo_trades
  WHERE entry_type='sr_break_retest' AND instrument='USD_JPY' AND direction='SELL'
    AND status='CLOSED'
)
SELECT
  CASE WHEN rn <= tot/2 THEN 'first_half' ELSE 'second_half' END AS half,
  COUNT(*) AS n, SUM(CASE WHEN pnl_pips>0 THEN 1 ELSE 0 END) AS wins,
  ROUND(AVG(pnl_pips), 2) AS avg_pips, ROUND(SUM(pnl_pips), 1) AS tot_pips
FROM ordered GROUP BY half;
```

判定:
- Wilson_bf_lo (m=8) > 0.50 → 真のエッジ (1次承認)
- 前半/後半で WR/EV が安定 (どちらも > 50%) → time-cohort 整合 OK
- 後半で WR 急落 / EV 反転 → past edge, not current

### Phase D: GBP_USD TP 0/37 SL 原因究明

```sql
-- D1: 距離 (signal_price→tp の絶対 pip)、direction、reach (entry_price で TP がどれだけ近かったか)
SELECT trade_id, direction, entry_price, sl, tp,
       ROUND(ABS(tp - entry_price) * 10000, 1) AS tp_dist_pip,
       ROUND(ABS(sl - entry_price) * 10000, 1) AS sl_dist_pip,
       pnl_pips, close_reason,
       mafe_favorable_pips, mafe_adverse_pips,
       spread_at_entry, slippage_pips
FROM demo_trades
WHERE entry_type='sr_break_retest' AND instrument='GBP_USD'
  AND status='CLOSED'
ORDER BY entry_time;
```

判定: avg_mfe / avg_tp_dist_pip < 0.5 なら TP 構造的に届かない設定。

### Phase E: Shadow simulator divergence の発見

is_shadow=1 で USD_JPY/SELL を引いた cohort と is_shadow=0 (実約定) cohort で:
- entry_price 分布
- entry_time 分布
- regime / dow_regime ラベル分布
- spread_at_entry 分布

```sql
SELECT is_shadow, COUNT(*) AS n,
  ROUND(AVG(pnl_pips), 2) AS avg_pips,
  ROUND(AVG(spread_at_entry), 3) AS avg_spread,
  ROUND(AVG(mafe_favorable_pips), 2) AS avg_mfe,
  ROUND(AVG(mafe_adverse_pips), 2) AS avg_mae
FROM demo_trades
WHERE entry_type='sr_break_retest' AND instrument='USD_JPY' AND direction='SELL'
  AND status='CLOSED'
GROUP BY is_shadow;
```

oanda_audit との join (timestamp 近傍 ±1 分 OR demo_trade_id) で entry-side メタ確認:

```sql
SELECT dt.is_shadow, dt.pnl_pips, dt.close_reason, dt.regime,
       oa.bridge_status, oa.block_reason
FROM demo_trades dt
LEFT JOIN oanda_audit oa ON dt.trade_id = oa.demo_trade_id
WHERE dt.entry_type='sr_break_retest' AND dt.instrument='USD_JPY' AND dt.direction='SELL'
  AND dt.status='CLOSED'
ORDER BY dt.entry_time;
```

## 統計判定基準 (pre-registered)

### Rule 1: USD_JPY/SELL 単独 cell 蘇生条件
- **N ≥ 24** (実約定 is_shadow=0)
- **Wilson_bf_lo (m=8) ≥ 0.50** (Bonferroni 後)
- **avg_pips ≥ +0.5** (after-cost を意識した最低 EV)
- **time-cohort split: 前後半とも WR ≥ 50%** (cohort drift 無し)
- **TP/SL distribution: TAKE_PROFIT 比率 ≥ 25%** (構造 OK)

5/5 → **ACCEPT (USD_JPY/SELL のみ shadow 再開を推奨)**
3-4/5 → **NEEDS_MORE_EVIDENCE (Shadow 継続 + N=50 到達まで待機)**
≤2/5 → **REJECT**

### Rule 2: Strategy 全体保留 / 復活条件
- 他セルで Wilson_bf_lo (m=8) > 0.50 のセルが 1 つもなければ **戦略全体は REJECT 維持 / FORCE_DEMOTED 継続**

### Rule 3: Shadow simulator バグ判定
- USD_JPY/SELL の `is_shadow=1` cohort WR < 30% かつ `is_shadow=0` cohort WR > 50% であれば **simulator divergence 確認** → R3 hot-fix エスカレーション

## Output

`done/<task_id>.md` に追記する Result section:

1. **Phase A reconciliation matrix** — shadow 222 / demo 82 が schema-level でどう整合するかの定義
2. **Phase B per-cell stats table** — instrument × direction × is_shadow × close_reason、Wilson_bf_lo (m=8) 列付き
3. **Phase C USD_JPY/SELL 26-trade full ledger + cohort split** — Rule 1 5項目の verdict
4. **Phase D GBP_USD TP 不達原因** — tp_dist_pip と mafe_favorable_pips の対比、構造仮説
5. **Phase E shadow vs live divergence** — simulator バグの再現 SQL とエビデンス
6. **Recommend section**:
   - USD_JPY/SELL のみ shadow 復活する場合の env 変数 / config 変更ポイント (具体 file:line)
   - simulator バグ修正パス
   - REJECT 維持の場合は次セッション用 archive メモ

## 禁止事項

- 本番 `/var/data/demo_trades.db` への **書き込み** (SELECT only。SQLite は read-only モードで開くこと: `sqlite3 'file:/var/data/demo_trades.db?mode=ro' -readonly`)
- `.env` / OANDA secret の読み出し
- Live 戦略の tier 変更 / config 改変 (R3 では分析のみ、修正は別 PR)

## クオンツチェック

- [x] Live (is_shadow=0) / Shadow (is_shadow=1) 分離
- [x] Bonferroni m=8 補正
- [x] Wilson lower bound (BF 込み)
- [x] Time cohort split (前後半)
- [x] Spread 基準 (spread_at_entry を MAFE と対比)
- [x] N (per cell), WR, EV, PF, Wilson_lo, Wilson_bf_lo
- [x] Rule 1/2/3 数値境界
- [x] ACCEPT / NEEDS_MORE_EVIDENCE / REJECT 境界明示
- [x] 本番 DB 破壊禁止条項

## 関連 memory

- [LIVE/Shadow 分離必須](feedback_live_shadow_separation.md)
- [時間コホート整合](feedback_cohort_time_check.md)
- [Spread 基準で MAFE 比較](feedback_spread_basis_for_mafe.md)
- [SR-weight Phase 2 ACCEPT](project_sr_weight_phase2_accept_2026_05_11.md) — sr_break_retest は survivor ではない
- [監査=設計の正誤、N不足は別問題](feedback_audit_purpose_design_not_n.md)
- [部分的クオンツの罠](feedback_partial_quant_trap.md)
