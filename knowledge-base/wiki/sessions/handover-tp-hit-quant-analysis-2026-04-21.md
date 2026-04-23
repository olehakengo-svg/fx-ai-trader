# Handover: TP-hit Quant Analysis (2026-04-21)

## Summary
全 Trade-log の TP-hit 698 件を 107 条件でテスト。クオンツ的結論:
**「条件が揃えば再現性あり」は統計的に noise レベル** (DSR-style null FP=5.4 vs Bonferroni pass=5)。
4/5 条件が pre→post cutoff で EV 符号反転 (regime shift 脆弱)。

詳細: `knowledge-base/wiki/analyses/tp-hit-quant-analysis-2026-04-20.md`
分析スクリプト: `scripts/analyze_tp_hits.py` (再実行可能)
生データ: `knowledge-base/raw/analysis/tp-hit-raw-2026-04-20.csv`

## 主要発見 (3 点、今後の判断に影響)

### 1. `score` は TP-hit 予測力ゼロ (p=0.42)
- P1 Sentinel score_gate bypass は実装として正しいが、**score の予測力前提は崩れた**
- **対応**: P1 は維持 (shadow 蓄積効果は不変)、score 計算方法見直しを**別 task 候補**として記録
- **実装提案なし** (lesson-reactive-changes)

### 2. `confidence` は WIN<LOSS の負相関 (p=1e-3)
- [[lesson-confidence-ic-zero]] の再確認
- `confidence=min(85, 50+score*4)` の線形+cap が予測力を破壊する既知現象

### 3. `spread_at_entry` は有意な edge (p=1.9e-5)
- WIN 平均 0.763 pips vs LOSS 0.842 pips
- 低スプレッド時の entry が TP-hit 率高
- **365d BT 検証を次 task 候補** (実装提案は保留)

## 個別条件の詳細

### Most robust (唯一の candidate)
`bb_rsi_reversion × EUR_USD × BUY`
- WR 64.5% (Wilson 95% CI [46.9, 78.9])
- EV +1.84 pip, Kelly +0.41
- 4/4 window 符号一致 (pre +1.24 / post +4.33 / live +1.12 / shadow +4.30)
- ⚠️ **N=31 (post-cutoff N=6)** — 判断プロトコル N≥30 にギリギリ、確証には post-cutoff N≥20 必要

### Most fragile (典型的 curve-fit)
`bb_rsi_reversion × USD_JPY × RANGE`
- N=186, pre-cutoff EV +0.16 → post-cutoff EV -1.56 (1.72 pip 符号反転)
- [[bb-rsi-reversion]] KB の post-cutoff EV=-1.76 と整合 (regime shift 脆弱性実例)

## 残タスク (次セッション参照用)

### 🔴 Blocker-type (時間/権限待ち)
- [ ] **Render Shell で `backfill_mtf_regime.sql` 適用** → Regime 2D v2 rescan 実行可能に
  - 1,944 UPDATE 文 ready at `/tmp/backfill_mtf_regime.sql` (要再生成)
  - guide: `knowledge-base/raw/mtf-backfill-guide-2026-04-20.md`
- [ ] **Live N ≥ 20 到達** (現 14, +6 必要、ETA ~2 日) → aggregate Kelly 初回有効計算

### 🟡 Watch (N 蓄積監視)
- [ ] **bb_rsi_reversion × EUR_USD × BUY** post-cutoff N 監視 (現 N=6 → N≥20 で確証判断可能)
- [ ] **bb_squeeze_breakout × USD_JPY** Live 確認 (shadow N=38 EV=+1.87 但し Live N 不足)

### 🟢 Research-type (実装前に BT 検証必要)
- [x] `spread_at_entry` edge の 365d BT 検証 — **INVALIDATED 2026-04-23**: ペア識別子との交絡 (Simpson's paradox) で edge は擬似効果。詳細 [[spread-at-entry-confounding-2026-04-23]]
- [~] `score` 計算方法見直し — **WATCH 2026-04-23**: post-cutoff aggregate p=0.55 noise 確認、bb_rsi_reversion で inverse 傾向 (Bonferroni 後非有意)。N>=200 で再検証。詳細 [[score-predictive-power-2026-04-23]]

### 🔵 Routine
- [ ] 毎セッション開始時: `python3 tools/quant_readiness.py` で状態把握

## 🚨 次セッション開始時の必読 (Challenge-Response Protocol 準拠)

1. **本 handover ファイル** — このページ
2. **`wiki/lessons/lesson-user-challenge-as-signal`** — Challenge-Response Protocol
3. **`wiki/lessons/lesson-all-time-vs-post-cutoff-confusion`** — 指標ウィンドウ検証
4. **`wiki/lessons/lesson-reactive-changes`** — 1日データで実装禁止
5. **`wiki/analyses/tp-hit-quant-analysis-2026-04-20.md`** — 本分析の full detail

## Kelly 計算 filter 再確認 (間違えやすい)

```python
# _get_aggregate_kelly の正しい filter
trades = [t for t in all_closed
          if t.get("status") == "CLOSED"
          and not t.get("is_shadow")
          and "XAU" not in t.get("instrument", "")
          and t.get("exit_time", "") >= "2026-04-16T08:00:00+00:00"]
# min_trades=20 未達なら return None
```

本番 API `/api/demo/stats` default は **all-time** なので `?date_from=2026-04-16` 明示指定必須。

## Related
- [[tp-hit-quant-analysis-2026-04-20]] — 本分析詳細 (700行級)
- [[lesson-all-time-vs-post-cutoff-confusion]]
- [[lesson-user-challenge-as-signal]]
- [[shadow-baseline-2026-04-20]]
- [[regime-2d-v2-preregister-2026-04-20]]
