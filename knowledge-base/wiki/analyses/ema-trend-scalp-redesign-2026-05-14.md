# ema_trend_scalp redesign — 2026-05-14 (in progress)

## Mandate

直前セッションで「DEPRECATE 推奨」を提示したが user に course-correct された:
> いえ、というよりこれを tv での検証を経て進化させたい、そもそも -ev なので、残す価値がないのは理解しているが、設計が誤りなだけでしょ

approved plan: `/Users/jg-n-012/.claude/plans/prancy-waddling-ullman.md`. 6 phases, abort 条件なし、+EV variant 見つかるまで継続。

## TV harness regression — Phase 0 結果

Pine `ema_trend_scalp-replica.pine` 449 → 571 lines に label-emission 改修:
- 6 既存 table block の各 cell を `label.new(transparency=100)` でも emit
- prefix 付き parseable text: `HOUR.NN|N=...|WR=...|PF=...|NetP=...`, `SESS./RSI./EXIT./MTF./SUM.`
- show_labels / draw_lines / draw_exits = false (default) で 500-label cap を breakdown 専用に確保

`pine_smart_compile` は severity-4 warning のみで成功。Strategy Tester 表示 (USDJPY 5m, ~1y): **N=1,044, WR=35.82%, PF=0.907, NetP=-22.09 USD (-0.22%), DD=29.23 USD (0.29%)**。

しかし **TV MCP の read API は全て strategy script に対し無効**:
| API | 結果 |
|---|---|
| `data_get_pine_labels` (any filter) | study_count=0 |
| `data_get_pine_tables` (any filter) | study_count=0 |
| `data_get_trades` | "No strategy found on chart." |
| `data_get_strategy_results` | (prior session) 常に空 |
| `indicator_set_inputs` | (prior session) updated_inputs={} |

→ **Pine label-emission による cell breakdown 抽出は実現できず**。screenshot だけが唯一 working な path。

## Pivot 戦略 — Python BT primary, TV aggregate cross-check

Plan の Phase 1-3 は「TV cell breakdown を取得して single-axis / stack ablation」だったが、cell breakdown 抽出が不可能になったので:

1. **Phase 1 baseline**: `app.run_scalp_backtest('ema_trend_scalp', interval='5m', lookback_days=365)` × USD_JPY / EUR_USD / GBP_USD → trade_log JSON 保存 → Python で hour-24 / session-4 / exit-3 / BUY-SELL breakdown 計算
2. **TV cross-check**: 各 pair aggregate (N/WR/PF/NetP) を TV Strategy Tester screenshot と比較。**TV → Python BT 乖離は trendline_sweep audit で documented**。差分が中位 (<10pp) なら Python BT の cell-level data を信頼、>10pp なら Live shadow の cell breakdown に pivot
3. **Phase 2-3**: Python BT を harness にして single-axis filter / stacking variant を試す。+EV cell stack 発見後に TV Strategy Tester で aggregate 確認

## Phase 1 結果 (TODO — running)

[実行中: `tools/ema_ts_phase1_breakdown.py`]

## Validated TV regressions (cumulative)

| Regression | First documented | This session |
|---|---|---|
| `data_get_strategy_results` empty | trendline-sweep-tv-replica-2026-05-14 | 再現 |
| `indicator_set_inputs` no-op | trendline-sweep-tv-replica-2026-05-14 | 再現 |
| `tab_new` no count increment | trendline-sweep-tv-replica-2026-05-14 | 再現 |
| `data_get_pine_labels` blind to strategy scripts | **(new)** | 確認 |
| `data_get_pine_tables` blind to strategy scripts | **(new)** | 確認 |
| `data_get_trades` "No strategy found on chart" | **(new)** | 確認 |

screenshot + `Read` tool への OCR が唯一の TV からの data 取得経路。

## 関連

- approved plan: `/Users/jg-n-012/.claude/plans/prancy-waddling-ullman.md`
- prior diagnosis: `wiki/analyses/sell-bias-forensics-2026-04-17.md`, `ema-tr-live-breakdown-2026-04-20.md`
- TV MCP harness pattern: `wiki/analyses/tv-bt-overlay-verification-2026-05-13.md`
- TV regression precedent: `wiki/analyses/trendline-sweep-tv-replica-2026-05-14.md`
- Pine source: `bt-results/tv-overlays/ema_trend_scalp-replica.pine` (571 lines)
- BT driver: `tools/ema_ts_phase1_breakdown.py`
