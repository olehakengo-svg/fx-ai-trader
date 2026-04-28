---
title: Live/Shadow 21pp WR 乖離の root cause investigation
date: 2026-04-27
type: forensics
session_ref: synchronous-plotting-seahorse
related: [[edge-reset-direction-2026-04-26]], [[external-audit-2026-04-24]]
---

# Live/Shadow 21pp WR 乖離 — Root Cause Investigation (2026-04-27 evening)

## Trigger

シニアクオンツ監査 ([[../../../.claude/plans/synchronous-plotting-seahorse]]) で発見:
- Live (is_shadow=0): N=36, WR=50.0%, +6.0 pip total, +53.3R
- Shadow (is_shadow=1): N=383, WR=30.0%, -432.1 pip, -77.67R

差 +20pp / +131R は selection bias か execution quality か未解明のまま放置されていた。

## 規律

- **クオンツファースト**: コード演繹禁止、ラベル実測のみ
- **部分的クオンツの罠回避**: WR/N に加え EV / 直接寄与 / outlier dependency / Wilson_BF / direction split / TF split / mode split を全て出す
- **XAU除外**: 全集計から除去
- **成功するまでやる**: Null 短絡禁止

## 実測 (demo_trades.db, status=CLOSED, last 30d, XAU除外)

### 1. Composition 概観

| Mode | is_shadow | N | WR | EV(pip) | total(pip) |
|---|---:|---:|---:|---:|---:|
| scalp | 0 | 25 | 64.0% | +3.06 | +76.5 |
| scalp | 1 | 80 | 42.5% | +3.27 | +261.6 |
| scalp_eur | 0 | 1 | 100% | +135.3 | **+135.3** |
| daytrade_gbpusd | 0 | 3 | 0% | -60.87 | **-182.6** |

→ Live 36 trades のうち **scalp が 25 (69%)**。Shadow は 12+ mode に分散。

### 2. Outlier dependency (致命的)

```
Live total = +6.0 pip (N=36)
Largest +135.3 pip (bb_rsi_reversion EUR_USD 1m, single trade)
Largest -170.0 pip (turtle_soup GBP_USD 15m, single trade)

Live total without largest +outlier   = -129.3 pip
Live total without ±largest both       = +40.7 pip
```

→ **2 outliers (1ペアの BUY と 1 ペアの SELL) が ±152 pip を作っている**。
→ +6.0 pip は実質的に 1 BUY trade (+135.3) の単発偶然に依存。

### 3. Per entry_type (N(live)>=3)

| entry_type | n_live | wr_live | n_shadow | wr_shadow | ev_live | ev_shadow |
|---|---:|---:|---:|---:|---:|---:|
| bb_rsi_reversion | 22 | 63.6% | 14 | 14.3% | +8.74 | -2.64 |
| vol_momentum_scalp | 4 | 50.0% | 1 | 100% | +4.30 | +6.00 |

→ Live 36 中 22 (61%) が **bb_rsi_reversion 一戦略に集中**。
→ Live 22 件のうち 20 件が **bb_rsi_reversion × USD_JPY × 1m × scalp** (1 cell)。

### 4. bb_rsi_reversion × USD_JPY × 1m × scalp 詳細

| is_shadow | direction | N | WR | EV | total |
|---|---|---:|---:|---:|---:|
| 0 (live) | BUY | 9 | 55.6% | +0.77 | +6.9 |
| 0 (live) | SELL | 11 | 72.7% | +4.61 | +50.7 |
| 1 (shadow) | BUY | 3 | 0% | -4.6 | -13.8 |
| 1 (shadow) | SELL | 0 | — | — | — |

**Wilson_BF lower (z=3.29, n=20, p=0.65)**:
- centre=0.921, spread=0.443, denom=1.541
- **WL_BF = 0.310 > 0.294 (BEV) → PASSES**
- EV/trade = +2.88 pip; USD_JPY friction ~1.5 pip → net EV ~+1.38 pip

→ **これは Bonferroni-corrected で生き残る live cell**。tier-master.json では `pair_demoted` 扱いだが、実測は逆方向のシグナル。

### 5. Live/Shadow filter selectivity

| 指標 | Live | Shadow | 差 |
|---|---:|---:|---:|
| avg confidence | 57.9 | 59.5 | -1.6 (live 低い) |
| avg score | -0.07 | +0.947 | -1.02 (live 低い) |
| avg spread (pip) | 0.308 | 0.853 | **-0.55 (live 65% 狭い)** |
| avg slippage (pip) | 0.231 | 0.540 | -0.31 |
| avg \|pnl\| (pip) | 14.43 | 8.32 | +6.11 (live 大きい振れ) |

→ Live は spread/slip が顕著に低い → **spread_sl_gate が calm regime のみ通している**
→ confidence/score は live の方が低い → 高 confidence が live に通るわけではない (むしろ逆)
→ つまり「live は良い signal を選んでいる」のではなく **「live は良い regime を選んでいる」**

### 6. Direction asymmetry

| direction | is_shadow | N | WR | EV |
|---|---|---:|---:|---:|
| BUY | 0 | 16 | 43.8% | +8.69 |
| BUY | 1 | 239 | 28.5% | -2.22 |
| SELL | 0 | 20 | 55.0% | -6.65 |
| SELL | 1 | 144 | 32.6% | +0.68 |

→ Live BUY EV +8.69 のうち +135.3 pip が単一 trade (8.4 pip/trade に分散しているがその内 16倍)。
→ Live SELL EV -6.65 ← 高 WR (55%) でも -EV。±170 pip の単一 SELL outlier 影響大。

### 7. TF asymmetry

| tf | is_shadow | N | WR | EV |
|---|---|---:|---:|---:|
| 15m | 0 | 6 | 16.7% | -31.88 |
| 15m | 1 | 131 | 33.6% | -3.63 |
| 1m | 0 | 26 | 65.4% | +8.14 |
| 1m | 1 | 137 | 32.8% | +1.40 |
| 5m | 0 | 4 | 0% | -3.60 |
| 5m | 1 | 111 | 23.4% | -1.11 |

→ **Live 15m は壊滅 (-31.88 EV / N=6)**、Live 1m は強い (+8.14 EV / N=26)。
→ 15m のうち turtle_soup × GBP_USD の -170 pip が effect size を歪めている。

## Root Cause 判定

**21pp WR gap は execution quality difference ではなく、3 段の selection bias**:

1. **Composition concentration**: Live 36 件中 20 件 (56%) が **bb_rsi_reversion×USD_JPY×1m×scalp** という単一 cell。これは tier-master.json で pair_demoted されているはずだが scalp slot で 0.01 lot として通過している。
2. **Outlier domination**: ±150 pip の 2 単発 trade が Live total の符号を決めている。removing both → +40.7 pip (N=34)。
3. **Spread filter selectivity**: spread_sl_gate が live spread 0.31 / shadow 0.85 と 65% の calm-regime selectivity を生んでいる。「signal quality」ではなく「regime quality」の差。

## クオンツ含意

### Live の +53R 結果は予測力がない (Null hypothesis 採択)
- 単発 outlier dependency → 統計的に不安定
- 1 cell concentration → strategy diversification は機能していない
- 仮に live 数字を信じて lot を上げると、次の outlier が逆向きで来るリスクが現状不可視

### ただし Null 短絡しない (成功するまでやる)
**bb_rsi_reversion × USD_JPY × 1m × scalp (N=20, WR=65%) は Bonferroni-corrected (Wilson_BF=0.310 > 0.294) で個別に survive する**:
- BUY/SELL 両方向で +EV (BUY +0.77, SELL +4.61)
- friction 1.5 pip 控除後 net EV ~+1.38 pip
- **これは P1#4 の単独再検証対象として最有力候補**

## 推奨アクション (本投資計画には未実装、別 plan で実行)

1. **bb_rsi_reversion×USD_JPY×1m×scalp の sub-conditional Bonferroni**
   - session×spread×regime grid で K=4-8 の Bonferroni K corrected で再検証
   - shadow 14 件 vs live 20 件の WR 乖離 (14.3% vs 65%) の root cause 解明
   - shadow が壊滅なのはなぜか? → 多分 spread regime 違い、確認必要

2. **tier-master.json の `pair_demoted: [bb_rsi_reversion, USD_JPY]` を再評価**
   - live N=20, WR=65%, Wilson_BF pass, +EV → 降格状態が現実と矛盾
   - ただし shadow は逆 → どちらが正しいかは sub-conditional 分析で決定

3. **Live data を「proof of edge」と扱わない政策の文書化**
   - Live は execution gate filter による selection biased sample
   - +EV proof は shadow + Bonferroni で行う
   - Live は「実装の sanity check」として参照のみ

4. **Outlier robust metrics の導入**
   - Median EV / 5%-trimmed mean を併用
   - 単発 trade で signal が flip しないようにする

## Out of Scope
- bb_rsi_reversion×USD_JPY×1m の strategy_family_map 確認 (別 task)
- spread_sl_gate threshold の tuning (Phase 4 以降)
- VPIN/GARCH/CS-MR 実装 (edge-witty-umbrella P2 dependency)

## Related
- [[../syntheses/roadmap-v2.1]]
- [[../analyses/friction-analysis]]
- [[../analyses/bt-live-divergence]]
- [[edge-reset-direction-2026-04-26]]
- [[external-audit-2026-04-24]]
