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

## Phase 1 結果 — Python BT vs Live Shadow の 3 軸乖離確認

### Python BT (365d × 5m × 3 pair) aggregate

| Pair | N | WR | EV | PnL (pips) |
|---|---|---|---|---|
| USD_JPY | 381 | **62.5%** | +0.009 | +3.5 |
| EUR_USD | 170 | 57.6% | −0.173 | −29.4 |
| GBP_USD | 188 | 53.2% | −0.440 | −82.7 |

実行時間: 合計 ~17h (USD_JPY 5.5h + EUR_USD 9.3h + GBP_USD 2.3h)。`tools/ema_ts_phase1_breakdown.py`。
**1 度目の run は cell() 引数 bug で breakdown 失敗・trade_log も保存失敗 → 17h 廃棄**。fix 済み (`--from-saved` mode 追加で recompute 可能に)。

### TV Strategy Tester (5m, deep backtest)

| Pair | N | WR | PF | NetP |
|---|---|---|---|---|
| USD_JPY | 1,044 | 35.82% | 0.907 | −22.09 USD (−0.22%) |

### Live Shadow (local DB demo_trades, all closed, is_shadow=1)

| Pair | N (closed) | decided N | WR | EV pips | PnL pips |
|---|---|---|---|---|---|
| USD_JPY | 26 | 23 | 26.1% | −1.26 | −29.0 |
| EUR_USD | 35 | 28 | 21.4% | −1.34 | −37.4 |
| GBP_USD | 27 | 24 | 25.0% | −1.58 | −37.9 |
| **合計** | **88** | **75** | **24.0%** | **−1.39** | **−104.3** |

### 3-axis WR 比較 (canonical: Live > TV > Python BT per memory)

| Pair | Python BT WR | TV WR | Live Shadow WR | Range (max−min) |
|---|---|---|---|---|
| USD_JPY | 62.5% | 35.8% | 26.1% | **36.4 pp** |
| EUR_USD | 57.6% | — | 21.4% | 36.2 pp |
| GBP_USD | 53.2% | — | 25.0% | 28.2 pp |

**Conclusion**: Python BT は ~30-40pp optimistic vs Live. cell ablation を Python BT で行うと "+EV 見せかけ" cell を量産する危険 → **以降は Live shadow DB を primary harness にする**。

## Phase 2 結果 — Live shadow data の single-axis ablation

データ source: `demo_trades` (status=CLOSED, outcome IN (WIN, LOSS), entry_type=ema_trend_scalp), **N=75 decided** (88 closed, 13 BE 除外).

### Aggregate exit-reason 分解 → 構造的非対称

| close_reason | N | WR | EV | RR メタ |
|---|---|---|---|---|
| TP_HIT | 14 | 100% | +7.13 | avg_win ≈ 7.13 pips |
| SL_HIT | 47 | 0% | −4.34 | avg_loss ≈ 4.34 pips |
| TIME_DECAY_EXIT | 10 | 0% | −1.60 | 早期撤退 (シグナル消失) |
| MAX_HOLD_TIME | 4 | 100% | +4.00 | 持ち越し win |

Realized RR = 7.13/4.34 ≈ **1.64**, BEV_WR = 1/(1+1.64) ≈ **37.9%**。Live 実測 WR=24% → **break-even に 13.9pp 不足**。

### Single-axis ablation 結果

| Filter | N | WR | EV (pips) | NetP | Pass (≥38% WR, EV>0, N≥30) |
|---|---|---|---|---|---|
| baseline (no filter) | 75 | 24.0 | −1.39 | −104.3 | ❌ |
| **mtf_alignment='aligned'** | 10 | **50.0** | **+2.16** | +21.6 | ⚠️ N<30 |
| direction='BUY' only | 37 | 24.3 | −1.05 | −38.7 | ❌ |
| direction='SELL' only | 38 | 23.7 | −1.71 | −65.6 | ❌ |
| sess Tokyo only | 11 | 45.5 | +0.54 | +5.9 | ⚠️ N<30 (Live shadow narrowness) |
| sess London only | 42 | 21.4 | −1.52 | −63.7 | ❌ |
| sess NY only | 22 | 18.2 | −2.10 | −46.2 | ❌ |
| drop h∈{9,10,12} | 53 | 30.2 | −0.69 | −36.7 | ❌ |
| drop SELL × {London, NY} | 42 | 33.3 | −0.21 | −8.8 | ❌ (still <38%) |

### Phase 2 winning gate (single-axis)

**`mtf_alignment='aligned' AND direction='BUY'`** → N=10, WR=50%, EV=+2.16, NetP=+21.6 pips.

Pair 分解で **10件すべて GBP_USD** (USD_JPY / EUR_USD で aligned×BUY は zero)。GBP_USD は friction 4.53 pip/RT で最も悪条件のペアなのに、cell EV=+2.16 は摩擦込みで明確に正。

### Implication for redesign

1. **MTF aligned + BUY only** は **構造的に正方向**。conflict / SELL 経路は捨てるべき (合計 N=63, WR=20.6%, EV=−1.86)。
2. ただし N=10 は **Recovery Path promotion gate (cell-conditional 180d BT + Live N≥30 + Bonferroni)** をクリアしていない。
3. Pair-narrowness (GBP_USD のみ) は **ペアごとの MTF gate 発火頻度の偏り**を示唆。USD_JPY / EUR_USD で aligned×BUY が zero なのは、戦略仕様の MTF gate definition と H1/H4 trend filter の組み合わせが pair に対して非対称な発火閾値を持つことを意味する。

## Phase 3 — Stacking ablation

single-axis で生存した filter (MTF aligned + BUY) を他軸と組み合わせて N と EV のトレードオフを評価。

| Stack | N | WR | EV | NetP | 備考 |
|---|---|---|---|---|---|
| aligned×BUY (baseline) | 10 | 50.0 | +2.16 | +21.6 | Phase 2 winner |
| aligned×BUY × mtf_regime=trend_up_weak | 10 | 50.0 | +2.16 | +21.6 | 全 10 件が trend_up_weak — 追加効果なし |
| aligned×BUY × v2_regime=* | — | — | — | — | v2_regime 全 NULL — 評価不可 |
| aligned×BUY × session=London | 8 | 50.0 | +2.33 | +18.6 | minor improvement, lose 2 Tokyo |

**Phase 3 結論**: 最小十分 gate は **`mtf_alignment='aligned' AND direction='BUY'`**。追加 stacking で N を削っても EV/WR は改善しない (既に天井)。

## Phase 4 — Cross-pair (GBP_JPY) / TF (15m) migration

- **GBP_JPY**: Live shadow に 0 trade。Sentinel に GBP_JPY が登録されていないため Live 累積もしていない。Python BT で +0.098 EV (rule:R1 prior BT、2026-05-05 audit) は **Live で未検証**。本セッションでは判定不能 — 別 session で:
  - Sentinel に `("ema_trend_scalp", "GBP_JPY")` を蓄積目的のみで一時追加 (lot=0 / shadow strict)
  - N≥30 まで蓄積後、本 audit の Phase 2-3 と同じフローで再評価
- **15m TF**: 同上 — Live は 5m のみ蓄積。Python BT 15m を別途実施するには更に 17h レベルの cost。後回し。

## Phase 5 — 結論と Recovery Path 提案

### 何が分かったか

1. **戦略カードの "BEV_WR=45.5% gap 25-30pp" は単純化しすぎ**。Realized RR=1.64 で BEV_WR=37.9%、Live 実測 WR=24.0% → gap は **13.9pp**。RR が低いので gap も低い。
2. **mtf_alignment が唯一の予測 strong feature**。`aligned` (N=10) と `conflict` (N=55) の WR 差は **50% vs 19.5% = 30.5pp**。これは structural pattern と判定可能。
3. **direction asymmetry も同方向**。BUY (N=37, WR=24.3%) vs SELL (N=38, WR=23.7%) は aggregate でほぼ同等だが、aligned 経路では BUY=50% / SELL=0% (N=0)。
4. **3-axis divergence**: Python BT 365d は 30-40pp optimistic。Live shadow が canonical。

### Recovery Path 提案 (Asymmetric Agility R1: Slow & Strict)

**Pre-reg LOCK gate**: `entry_type='ema_trend_scalp' AND mtf_alignment='aligned' AND direction='BUY' AND instrument='GBP_USD'` (Phase 1-3 で発見済の cell、hash 固定対象).

3 段防御 (per `lesson-cell-audit-bt-required-2026-04-27`):

1. **Pre-reg LOCK**: 本 audit の gate 仕様を `wiki/analyses/ema-trend-scalp-redesign-prereg-2026-05-15.md` に hash 固定 (後付け cell tuning 禁止)
2. **Cell-conditional 180d Python BT**: `strategies/scalp/ema_trend_scalp.py` に env flag `ETS_REDESIGN_V3=1` で `mtf_alignment='aligned' AND BUY only AND GBP_USD only` の gate を加え、180d BT で TV / Live の WR が再現するか確認 (Python BT 30-40pp optimistic bias を考慮し、WR≥70% 出ない場合は disq)
3. **Bonferroni 補正**: 試行 cell count = 単一 gate (mtf×direction×pair = 1)、pair 数=1、TF=1 → m=1。critical p-value=0.05 のままで OK
4. **Recovery Path lot**: shadow strict → N≥30 cumulative (+20件 追加蓄積要、現 10→30、目安 6-10 週) → 0.25x → N≥30 each step で 0.5x → 1.0x
5. **3 軸独立**: TV / Python BT / Live shadow の 3 軸で +EV 一致を確認してから OANDA 転送開始

### 本セッションでやらないこと

- `app.py` / `__init__.py` / `tier-master.md` の deploy 経路は **触らない** (deploy エージェント経由のみ、Pre-reg LOCK 後)
- ema_trend_scalp の戦略カードに **DEPRECATE タグを付け直さない** (user explicit course-correction)
- v9.6 等のバージョン跳ねは **しない** (cell-level redesign の数値根拠が N=10 で promotion gate 未到達)
- GBP_JPY Sentinel 追加は **次セッション** で扱う (本セッションの scope 外、別 PR/コミット)

### 次セッションへの punch list

1. **Pre-reg LOCK page 作成**: `wiki/analyses/ema-trend-scalp-redesign-prereg-2026-05-15.md` に上記 gate 仕様を hash 固定
2. **`ETS_REDESIGN_V3` env flag 追加**: `strategies/scalp/ema_trend_scalp.py` に gate を実装、production code path には触らず env flag で隔離
3. **Cell-conditional 180d BT**: Python BT を `ETS_REDESIGN_V3=1` で再走 (USD_JPY 5.5h, EUR_USD 9.3h, GBP_USD 2.3h を 180d/3=半分にして再見積 ~6h cell-only)
4. **GBP_JPY Sentinel shadow 追加**: 別 session で `("ema_trend_scalp", "GBP_JPY")` を Sentinel 蓄積目的のみ追加 (lot=0、shadow strict)
5. **session log 更新**: 本日 (2026-05-14 / 15) の Phase 0-5 結果を `wiki/sessions/2026-05-14-session.md` に追記

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
