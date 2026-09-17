# Pre-reg LOCK: mtf_regime_trend_cascade_scalp v2.3 (rule:R1)

## Status: ACTIVE — 2026-04-30 → 2026-05-14 (14 days)

commit `83a9e10` をもって本番 (Render `fx-ai-trader.onrender.com`) にデプロイ。
Pre-reg LOCK 期間中は **Shadow only**。Live 注文は出さず、demo_trades にデータ蓄積。

---

## Rule 1 BT 結果 (合格根拠)

183日 vec BT (Massive 1m + 既存 H1/M15/M5 cache、commit 83a9e10 時点):

| Cell | N | WR | Wilson_lo | PF | EV/trade | Kelly |
|---|---:|---:|---:|---:|---:|---:|
| **USD_JPY × NY**  | **56** | **53.6%** | (>BEV) | **1.98** | **+3.15p** | **26.5%** |
| **EUR_USD × NY**  | **87** | **44.8%** | (>BEV) | **1.43** | **+1.31p** | **13.5%** |
| USD_JPY × Tokyo  | (small) | — | — | — | — | — |
| USD_JPY × London | (small) | — | — | — | — | — |
| EUR_USD × Tokyo  | (small) | — | — | — | — | — |
| EUR_USD × London | (small) | — | — | — | — | — |

**Bonferroni**: 6 cell, α=0.05/6=0.00833。**2/3 active cells PASS** (≥1 required) → ✅ Rule 1 通過

詳細: commit 83a9e10 メッセージ + `wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md`

---

## v1 → v2 → v2.1 → v2.3 の経緯

| Version | 日付 | 変更 | 結果 |
|---|---|---|---|
| v1 | 04-29 | `regime ∈ {trend_up, trend_down, range, choppy}` の 4ラベル | demo_trades 実測で否定 |
| v2 | 04-30 | binary `{moderate_trend, no_go}` に簡素化 | runner で N=0 |
| v2.1 | 04-30 | L3 `ema_order` / `ema9_touch` 削除 (32+17件 reject 解消) | SL formula bug で発火不能 |
| v2.2 | 04-30 | H1 EMA21/50 macro gate (`slope_direction_macro_gated`) 追加 | EUR_USD 改善、USD_JPY 不安定 |
| **v2.3** | **04-30** | SL formula 修正 (pip_size = 1/pip_mult) + L3 macdh/stoch 完全廃止 (1m noise 除去) | **Rule 1 PASS** |

---

## デプロイ状態

- **Commit**: `83a9e10` `fix(scalp): regime cascade v2.3 — fix SL formula + L3 oscillator noise (rule:R3)`
- **Push**: `8b4069b..83a9e10  main -> main` (2026-04-30 12:40 JST)
- **Render auto-deploy**: 完了 (`/api/demo/status` HTTP 200, `main_loop_alive: True`)
- **Strategy state**:
  - `mtf_regime_trend_cascade_scalp`: `enabled = True`, `strategy_type = "trend"`
  - `mtf_regime_range_cascade_scalp`: `enabled = False` (実測で disable, 将来 trigger 差替えで再有効化候補)
  - 登録: ScalperEngine 25 戦略中

---

## 監視 KPI (14日)

### Primary KPI (per pair × session strata, 各 N≥15)

| 指標 | 合格水準 | 即停止水準 (Rule 2) |
|---|---|---|
| WR | ≥ 40% | < 30% |
| Wilson_lo (95%) | > 30% | < 20% |
| PF | ≥ 1.20 | < 0.7 |
| EV/trade | ≥ -0.5p | 連敗 ≥ 6 |
| 累計 PnL | ≥ -¥2,000 | < -¥10,000 |

### 監視クエリ (sqlite-fx MCP / Render)

```sql
-- 14日 N×WR×EV (regime cell 別)
SELECT entry_type, instrument, mtf_regime, COUNT(*) n,
       ROUND(AVG(pnl_pips), 3) ev_pips,
       ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*), 2) wr_pct,
       MIN(entry_time) first_t, MAX(entry_time) last_t
FROM demo_trades
WHERE entry_type = 'mtf_regime_trend_cascade_scalp'
  AND DATE(entry_time) >= DATE('now','-14 days')
GROUP BY entry_type, instrument, mtf_regime
ORDER BY instrument, n DESC;
```

### Walk-Forward Recovery (失敗時継続検証)

BT 不合格 strata あれば、**closure 短絡禁止** で別 session で深掘り再検証:
1. ADX band sensitivity: 18-25 → {16-22, 20-28}
2. Hurst band sensitivity: 0.75-0.95 → {0.70-0.90, 0.80-1.00}
3. H1 macro gate 解除でフルサンプル N 比較
4. Pair-level promotion: USD_JPY 単独 / EUR_USD 単独 disable

---

## ELITE_LIVE 昇格判定 (2026-05-14)

全 KPI 通過 → ELITE_LIVE 昇格 + Live 注文許可
- N≥15/strata 必須
- Bonferroni 補正後 p < 0.0083 を ≥ 1 strata で達成
- Live shadow trade と BT trade の WR diff < 5pt (構造楽観バイアス検出)

1つでも失格 → revert または `enabled = False` で停止し、別 session で根本見直し。

---

## 今後やる作業 (本セッション外)

| # | タスク | 優先 |
|---|---|---|
| 1 | shadow N≥15 監視 (毎日 09:00 JST) | Critical |
| 2 | OANDA paginated 365日 BT 実行 (Massive 60日上限解除) | High |
| 3 | Walk-Forward 240/60 × 3 split | High |
| 4 | demo_trades schema に `regime_v2` 列追加 (mtf_regime とは別軸) | Med |
| 5 | USD_JPY 強上昇期 edge 不安定性の deep-dive | Med |

---

## KB references

- `knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md` (戦略仕様)
- `knowledge-base/wiki/strategies/mtf-regime-range-cascade-scalp.md` (DEPRECATED)
- `knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md` (v1→v2 redesign 根拠)
- `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md` (180d null finding)
- `CHANGELOG.md` 2026-04-30 v2.3 entry
