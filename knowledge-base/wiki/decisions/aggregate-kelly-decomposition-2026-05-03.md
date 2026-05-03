# Aggregate Kelly Decomposition Decision — 2026-05-03

**Date**: 2026-05-03
**Rule**: R2 (Gate 1 unlock diagnosis)
**Status**: VERDICT — surgical demote 不可、N不足

## Bottom Line

**Gate 1 を surgical demote でアンロックすることは現時点で不可能**。

Live trade 母数が 25 日で N=29 (`oanda_trade_id != ''`) と薄く、Bonferroni 補正下で powered な負エッジ cell が一つも検出されない。出血源を「特定の戦略・ペア・セッション」に局所化できる粒度の証拠が無い。

## Evidence

### Aggregate (Render API 2026-05-03 実測)

| Filter | N | WR | EV/trade | PnL | edge | Kelly |
|---|---|---|---|---|---|---|
| `oanda_trade_id != ''` (真 Live) | 29 | 48.28% | -2.20 | -63.7 | -20.02pp | 0.0 |
| `is_shadow=0` (legacy) | 68 | 39.70% | -1.41 | -95.7 | — | — |
| 旧 KB 2026-04-29 snapshot | 286 | 38.10% | -0.80 | -228.6 | -18.04pp | 0.0 |

**KB の N=286 数値はフィルタ定義が混濁しており本決定では使用しない**。`oanda_trade_id != ''` を真 Live と定義（lesson "`oanda_trade_id IS NOT NULL` で集計する」が正しい live 判定" に準拠、ただし空文字列除外も追加）。

### Cell decomposition (4軸)

[`raw/audits/aggregate-kelly-decomposition-2026-05-03.md`](../../raw/audits/aggregate-kelly-decomposition-2026-05-03.md) 参照。要約:

- **DEMOTE flag = 0** (基準: N≥8 かつ Wilson_up_95 < BEV_WR + 5pp)
- **WATCH flag = 7** (経済的負だが統計未確定)
- **OK flag = 1** — `fib_reversal/USD_JPY` (N=8, WR=50%, PnL=+1.4)
- 戦略×ペア軸で N≥5 を満たす cell は **2つのみ**:
  - `session_time_bias/GBP_USD` (ELITE_LIVE) N=5 PnL=-17.6 WATCH
  - `fib_reversal/USD_JPY` (FORCE_DEMOTED) N=8 PnL=+1.4 OK

### Sensitivity

DEMOTE 候補 0 件 → 除外しても aggregate Kelly は 0 のまま。**「数 cell を切れば Kelly>0 が見える」シナリオは存在しない**。

## Tier 整合性の異常

| 戦略 | Tier | 実 Live PnL | 矛盾 |
|---|---|---|---|
| `fib_reversal/USD_JPY` | **FORCE_DEMOTED** | +1.4 (N=8 WR=50%, OK flag) | tier 降格中の戦略が唯一黒字 |
| `session_time_bias/GBP_USD` | **ELITE_LIVE** | -17.6 (N=5 WR=40%, WATCH flag) | ELITE 階層で経済的負 |
| `vwap_mean_reversion` | **FORCE_DEMOTED** | -30.2 (N=2 is_shadow=0) | tier と整合 |

ELITE_LIVE の `session_time_bias/GBP_USD` は N=5 で統計的判決保留だが、ELITE 階層で連敗継続中という事実は次の monitoring で再確認必須。

## Drift 警告

| 指標 | 2026-04-29 (KB) | 2026-05-03 (Render 実測) | 差 |
|---|---|---|---|
| DD% | 34.76% | **40.65%** | +5.89pp 悪化 |
| DD pip | 347.6 | 406.5 | -58.9pip |
| Ruin prob | 1.72% | 1.88% | +0.16pp |
| `is_shadow=0` PnL | -228.6 | -95.7 | フィルタ差で -132.9pip 縮小 |

DD は ⚠️⚠️ 領域へ突入。defensive mode 0.2x のまま蓄積継続。

## Decision (rule:R2)

1. **Gate 1 unlock 待機**: surgical demote 経路は閉じている。N が増えるまで Live で Kelly>0 達成不可。
2. **DEMOTE/降格アクション無し**: 全 cell が WATCH 帯、Bonferroni 補正下で有意負を示せない。
3. **monitoring 強化対象**:
   - `session_time_bias/GBP_USD` (ELITE_LIVE) を WATCH に格上げし、N=10 到達時に Wilson lower で再評価
   - `fib_reversal/USD_JPY` (FORCE_DEMOTED が黒字) の tier 再考は別タスクで quant-first に検証
4. **KB 更新済み**: `wiki/index.md` System State block を Render API 実測値で書き換え

## Open Questions (Wave 2 へ)

- ~~`is_shadow=0` (N=68) と `oanda_trade_id != ''` (N=29) の 39 件差は何か~~ → **解決済 2026-05-03 13:25**: B audit 判決 `FLAG_DRIFT_BUG`。39件全て `is_shadow` flag の post-hoc 誤書き換え。OANDA 送信は正しくブロック。詳細: [`raw/audits/oanda-passthrough-gap-2026-05-03.md`](../../raw/audits/oanda-passthrough-gap-2026-05-03.md)
- Live N=29 が真の Live 母数として確定。`is_shadow=0` フィルタは Rule 2 で write-path 修正後に再評価。
- Live N が 25 日で 29 件しかない理由（OANDA 通過率の構造）→ B 判決により **gates は正しく機能**、N 不足は単に trade 頻度の問題と確定。Scalp 早期再開が唯一の Gate 1 unlock 経路。
- Scalp 枝の早期再開で N 蓄積を加速すべきか（roadmap-v2.1 Track E 連動） → **YES**（A1 → A2 task chain で進行）

## Related

- Roadmap: [[roadmap-v2.1]]
- Lessons:
  - "集計値は必ずセグメント分解する。平均値は嘘をつく"
  - "促進判定 (Kelly)も逆校正判定 (Bonferroni) も同じ統計厳格さで行う"
  - "止血判定は EV 軸で行う。WR は補助指標"
  - "`oanda_trade_id IS NOT NULL` で集計する」が正しい live 判定"
- Tooling:
  - [`tools/aggregate_kelly_decomposition_audit.py`](../../tools/aggregate_kelly_decomposition_audit.py) (`--allow-drift` 拡張済み)
  - [`tools/render_trades_snapshot.py`](../../tools/render_trades_snapshot.py) (Render → SQLite mirror)
  - Snapshot DB: `raw/snapshots/render-demo-trades-20260503.db`
- Run reports: `.ai/runs/20260503-112225-20260503-1118-aggregate-kelly-decomposition/`
