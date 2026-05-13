---
id: 20260513-2000-gap1-cross-pair-confluence-bt
title: "[Gap 1 Cross-Pair Confluence] ダウ理論原則④「平均は相互に確認されなければならない」を FX で実装 — 相関ペア同方向 confirmation gate"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T20:00:00+0900
roadmap_gate: "ダウ理論 5 Gap 分析 (2026-05-11 司令塔読了) の Gap 1 (cross-pair confluence)。Phase E (Gap 5 regime gate) は universal observation layer 完成 + 10 Bonferroni cells が forward Shadow validation 待ち。Phase F は E と独立直交軸なので並走可。原則④の FX 解釈: 同方向に動くべき相関ペア (USDJPY long + DXY up + EURUSD down 等) の confirmation を gate にすれば single-pair 局所判断の bias を断てる。"
rule: pre-reg
related:
  - knowledge-base/wiki/decisions/regime-gate-phase-e-2026-05-13.md      # Phase E verdict
  - data/cache/massive/*_1h.parquet                                       # 相関 BT データ源
  - app.py:run_daytrade_backtest                                          # BT entry
  - tools/regime_gate_full_bt.py                                          # Phase B2.5 雛形 (commit 436ffaf)
  - reports/regime_gate_phase_b2/trade_log_tagged.csv                    # 5617 trades base
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
---

# 0. 思想 (ダウ理論原則④の FX 解釈)

> "平均は相互に確認されなければならない" — 両市場が同じ方向性を示さない限り本格的トレンドではない (OANDA Lab Education)

**FX 翻訳**:
- USDJPY long → DXY up + (EURUSD down or USDCHF up) で confirmation
- GBPUSD long → DXY down + GBPJPY up (相関 pair の同方向確認)
- 相関 pair が同方向に動いていない場合 = local fakeout 可能性高

**現状の課題**: 我々のシステムは strategy-per-pair で動き、cross-pair confirmation gate なし。W3-5 で FDR 補正 (pair pool m=6, q=0.10) は実装したが、これは多重検定補正のみで、リアルタイム confluence gate ではない。

# 1. 設計

## 1.1 Confluence pair の定義 (correlation taxonomy)

司令塔事前 mapping (post-hoc tune 禁止、Codex 検証で必要なら literal 改訂):

| Primary pair | Confluence requirements |
|---|---|
| USD_JPY | DXY (USD↑) + (EUR_USD 反方向 OR USD_CHF 同方向) |
| EUR_USD | DXY 反方向 + EUR_JPY 同方向 |
| GBP_USD | DXY 反方向 + GBP_JPY 同方向 |
| EUR_JPY | EUR_USD 同方向 + USD_JPY 同方向 |
| GBP_JPY | GBP_USD 同方向 + USD_JPY 同方向 |
| AUD_USD | DXY 反方向 + (相関 commodity USD pair) |

**Confluence gate**:
- "STRONG" = primary signal direction と confluence pair が **3 つ以上** 同方向
- "WEAK" = 2 つのみ confluence
- "MIXED" = 1 つ以下 (gate fail)

実装: 各 trade entry 時点で H1 close-to-close direction (直近 5 H1 bars) を計算、primary signal direction と比較。

## 1.2 Universal Tagging 拡張 (Phase E と並走)

`demo_trades` に新カラム追加:

```sql
ALTER TABLE demo_trades ADD COLUMN confluence_score TEXT;  -- 'STRONG'/'WEAK'/'MIXED'/'NULL'
ALTER TABLE demo_trades ADD COLUMN confluence_details TEXT;  -- JSON: 各 pair direction
```

signal 時点で confluence 計算 → `open_trade(..., confluence_score=..., confluence_details=...)` で保存。

dow_regime / v2_regime と並走、universal observation 原則維持。

## 1.3 Retrospective BT validation (forward 蓄積前の sanity)

Phase B2.5 trade_log (commit 436ffaf, N=5617) を retrospective に confluence tag:

```python
# 各 trade の entry_time で MASSIVE 1h parquet から confluence pair の direction を取得
for trade in trades:
    primary_dir = trade["direction"]  # BUY=long, SELL=short
    confluence = compute_confluence(
        primary_pair=trade["instrument"],
        primary_dir=primary_dir,
        entry_time=trade["entry_time"]
    )
    trade["confluence_score"] = confluence["score"]
    trade["confluence_details"] = confluence["details"]
```

その後 cross-tab で edge 検証:

```sql
SELECT entry_type, confluence_score,
       COUNT(*) AS N,
       AVG(CASE WHEN pnl_pips > 0 THEN 1.0 ELSE 0.0 END) AS WR,
       AVG(pnl_pips) AS EV_pip,
       SUM(CASE WHEN pnl_pips > 0 THEN pnl_pips ELSE 0 END) /
         NULLIF(SUM(CASE WHEN pnl_pips < 0 THEN -pnl_pips ELSE 0 END), 0) AS PF
FROM tagged_trades
WHERE confluence_score IS NOT NULL
GROUP BY entry_type, confluence_score
HAVING N >= 30
ORDER BY EV_pip DESC;
```

## 1.4 3 軸 composite (Phase E と統合)

最終的に **(entry_type × dow_regime × v2_regime × confluence_score)** の 4 軸 cell を生成。
Sparsity でほとんどの cell は N<30、Bonferroni effective m は小さく抑えられる。

Phase E2 で見つかった 10 Bonferroni cells を confluence で再分解、edge が cofluence-STRONG に集中するか確認 (= 仮説検証)。

# 2. 完了条件

1. `tools/cross_pair_confluence.py` 新規: compute_confluence helper
2. `modules/demo_db.py` migration (confluence_score + confluence_details カラム)
3. `modules/demo_trader.py` signal-time hook (best-effort fail-safe)
4. `tools/confluence_backfill.py` (dry-run-first)
5. `tools/composite_cell_with_confluence.py`: Phase B2.5 trade_log を retrospective confluence tag、cross-tab + Bonferroni
6. `tests/test_cross_pair_confluence.py` (unit + integration, mock 禁止)
7. `reports/gap1_cross_pair_confluence/` 出力 (crosstab / proposals / verdict / SUMMARY)
8. 生成物即 commit (--no-verify) — `.git/index.lock` で blocked なら final.md に明記、司令塔が手動 commit

# 3. 司令塔ガード

- [ ] dow_regime / v2_regime / regime / mtf_regime カラム無編集 (4 並走)
- [ ] Score-race / signal logic 無編集 (純観測層)
- [ ] OANDA bridge / live runner 無編集
- [ ] confluence pair mapping は literal 固定、post-hoc tune 禁止
- [ ] MASSIVE parquet 使用 (`feedback_bt_must_use_massive`)
- [ ] XAU 除外
- [ ] PF / Wilson_lo / Bonferroni 全算出
- [ ] mock-only test 禁止、実 MASSIVE 1h parquet で integration test
- [ ] **本タスクで Live 昇格判定しない** (retrospective EDA、forward 蓄積前)
- [ ] 4 軸 composite (dow × v2 × confluence × strategy) でも universal gate にしない、cell-specific 判定のみ

# 4. 期待される下流分析 (本タスク完了後、別 task)

```sql
-- Phase E 10 Bonferroni cells を confluence で再分解
SELECT entry_type, dow_regime, v2_regime, confluence_score,
       COUNT(*) AS N, WR, EV_pip, PF
FROM tagged_trades_with_confluence
WHERE entry_type IN ('streak_reversal', 'sr_anti_hunt_bounce', 'xs_momentum',
                     'session_time_bias', 'trendline_sweep', 'vix_carry_unwind')
  AND v2_regime = 'no_go'
GROUP BY entry_type, dow_regime, v2_regime, confluence_score
HAVING N >= 30
ORDER BY EV_pip DESC;
```

仮説:
- 10 cells の edge が **confluence_STRONG に集中** → Gap 1 が Gap 5 を補強する強い証拠
- 10 cells の edge が **confluence_MIXED でも残る** → confluence は独立 dimension、追加 filter として価値ある
- 10 cells の edge が **WEAK で散ってる** → confluence は noise、棄却

# 5. 禁止事項

- 本番 DB / .env / OANDA secret 無触
- regime / mtf_regime / dow_regime / v2_regime カラム改変禁止
- Score-race / signal logic 改変禁止
- confluence backfill を本番 DB に対して実行禁止
- post-hoc confluence pair mapping tune 禁止
- 本タスクで Live 昇格判定の short-circuit 禁止 (shadow-first 維持)

# Appendix A: 相関 pair の H1 direction 計算 (Codex 実装ヒント)

```python
def get_h1_direction(pair: str, ts: pd.Timestamp, lookback: int = 5) -> str:
    """直近 lookback H1 bars の close-to-close で direction 判定。
    Returns: 'up' / 'down' / 'flat'
    """
    df = load_massive_1h(pair)  # data/cache/massive/<pair>_1h.parquet
    df = df.loc[df.index <= ts].tail(lookback + 1)
    if len(df) < 2:
        return 'flat'
    delta = df['close'].iloc[-1] - df['close'].iloc[0]
    threshold = df['close'].std() * 0.5  # noise filter
    if delta > threshold:
        return 'up'
    if delta < -threshold:
        return 'down'
    return 'flat'
```

# Appendix B: DXY proxy

MASSIVE に DXY parquet がなければ proxy 計算:
```
DXY_proxy = weighted_avg({USD_JPY: 0.136, EUR_USD: -0.576, GBP_USD: -0.119,
                          USD_CHF: 0.036, USD_CAD: 0.091, AUD_USD: -0.042})
```
(literal weights、ICE DXY 公式式に近似)

実 DXY parquet あれば優先使用。
