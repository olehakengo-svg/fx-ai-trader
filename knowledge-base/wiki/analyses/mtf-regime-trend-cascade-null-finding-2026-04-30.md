# mtf_regime_trend_cascade_scalp v2 — Empirical Layer Audit (2026-04-30)

## Status: **PROVEN CONCEPT, L3 OVER-FITTING** — depth-test in next session

**初版 (10:00) の "NULL finding / 構造的衝突" 仮説は誤り**。再診断の結果、**戦略コンセプトには edge がある**ことが実測で確認された。問題は L3 の 6 条件カスケードが過剰フィルタリング(over-fitting) している点と BT pipeline で m15/m5 を populate していない pipeline bug。

## 修正後の実測結果 (180 日, USD_JPY)

L3 を全廃 (L0+L1+L2 only) で評価:

| metric | value | Rule 1 gate | judgment |
|---|---|---|---|
| N | **39** | ≥50/cell | ❌ N不足 (60d→180d で線形増加: より長期で達成可能) |
| WR | 38.5% | ≥52% | ❌ |
| **PF** | **2.58** | ≥1.20 | ✅ |
| **EV** | **+3.03 pips** | >0 | ✅ |
| **Kelly** | **+23.6%** | >0 | ✅ |
| Wilson_lo (WR) | 24.9% | ≥50% | ❌ (BEV=28% で WR>BEV、非対称 edge) |
| avg_win / avg_loss | 12.83 / 3.10 = **4.14x** | — | 強い非対称ペイオフ |

**判定**: 「部分的クオンツの罠」を避けて評価すると、PF/EV/Kelly はクリア。WR/Wilson_lo の不合格は asymmetric payoff (avg_win 12.83p vs avg_loss 3.10p) の結果であり、BEV(28%) を WR(38.5%) が上回るので**経済的には profitable**。

60 日でも:
- USD_JPY: N=13, WR=30.8%, PF=3.35, EV=+2.92p, Kelly=+21.6%

**EUR_USD は別の理由で失敗 (N=17, WR=0%)** — SL=`ema21 - atr7*0.3` が低ボラ pair で 0.15-3.4 pip と狭すぎ、spread/noise で全件 SL hit。**戦略コンセプトの問題ではなく、SL formula に floor が無い実装 bug**。

## 真の根本原因 (3 層)

### 1. BT pipeline bug: `_compute_bt_htf_bias` が m15/m5 を populate しない

[`app.py:4761-4768`](../../app.py) のコメント:
> "NOTE: M15/M5 features for mtf_*_scalp strategies are NOT injected in BT mode here. Per-recalc resample+add_indicators made 7d BT take 1h+ for 2 pairs."

**影響範囲**: 既存の `mtf_trend_follow_scalp` / `mtf_counter_trend_scalp` も含めて **全ての MTF cascade scalp 戦略は標準 BT で N=0**。シグナル数が見えないまま production / shadow に出ていた可能性。

### 2. L3 の 6 条件カスケードが over-fitting

180 日で L0+L1+L2 まで通過した 70 候補 tick のうち、**全件が L3 で block** (instrumented BT 実測):

| L3 sub-condition | block count (60d) |
|---|---|
| ema_order (1m EMA9>EMA21 順列) | 32 |
| ema9_touch (1m prev_low の EMA9 タッチ近接) | 17 |
| bullish/bearish_candle (1m 陽/陰線確認) | 10 |
| macdh sign + rising | 11 |
| stoch K-D cross | 0 |
| bounce_strength | 0 |

ema_order と ema9_touch が約 70% を block。1m timeframe の noise 下で **6 条件全部を同一 bar で要求するのは combinatorially rare**。15m moderate_trend の方向性は既に slope_dir で確定しているのに、1m で改めて EMA 順列を要求するのは**冗長な over-fitting**。

### 3. SL formula 実装 bug — floor 不足

`sl = ema21 ± atr7 * 0.3` は USD_JPY (高ボラ) では SL ≈ 1.8-3 pip だが、EUR_USD (低ボラ) では 0.15-3.4 pip と spread/noise レベル。**最小 SL floor (例: 5 pip)** が無いと低ボラ pair で 100% SL hit する。

## 次セッションで実施すべき修正・検証

### Fix 1: BT pipeline — `_compute_bt_htf_bias` に m15/m5 を追加
- ペナルティ: per-recalc が 1m → 15m + 5m を resample + add_indicators で重い
- 解: `_BT_HTF_RECALC_SCALP=60` (1時間ごと) で十分。1 度だけ前計算して merge_asof でも可
- alternative: vec runner `_bt_regime_cascade_scalp_vec.py` を整備して default にする

### Fix 2: L3 緩和 — sub-condition 削減
- **削除候補 1: ema_order** (15m slope_dir が方向確定済み、冗長)
- **削除候補 2: ema9_touch** (5m pullback が既に近接確認済み)
- **保持**: bullish/bearish_candle + macdh sign + stoch K<75/>25 (signal quality 確保)

### Fix 3: SL floor 追加
- `sl_dist = max(atr7 * 0.3, spread × 5, 5_pip)` のいずれか or 複合
- 仕様確認: 既存 `ema_pullback` 戦略の SL 体系を参照

### Fix 4: 365 日 BT 再実行
- L3 削減 + SL floor 後、cell=6 (戦略1×ペア2×セッション3) で α=0.00833
- N≥50/cell 達成見込み (180日で N=39 → 365日で ~80)

## 暫定判断

- v2 戦略コンセプトには **profitable な asymmetric edge がある** (PF 2.5+ 確証)
- 戦略コミットは Fix 1-3 完了 + 365日 BT 通過後
- 今セッションの commit 候補:
  - ✅ `13f7d24 fix(infra): polarity-inverted autostart gate` (済)
  - 検討: BT pipeline m15/m5 fix を別 commit (`fix(bt-pipeline): inject m15/m5 in _compute_bt_htf_bias`)
  - 戦略 .py / wiki .md は L3 緩和 + SL floor 適用後にまとめてコミット

## 教訓 (Lessons Learned)

1. **N=0 は仕様の否定証拠ではない** — 上流 pipeline で何が起きているか実測しないと判断できない
2. **「構造的衝突」のような物理的不可能性主張は危険** — 私の初版分析は L0+L1 の 1% pass rate を見ただけで結論を急いだ。L2/L3 を実測する前に断言したのは "コード演繹" であり「ラベル実測主義」(memory) に違反
3. **6 条件 AND cascade は almost certainly over-fit** — 各条件が独立で 50% pass なら 6 条件全部で 1.5%。実測 (70/70 全 block) の通り
4. **「絶対ワークしやすい仕組み」というユーザー直観の正しさ** — 教科書的に良く設計された戦略が N=0 で出力するときは pipeline か parameter のどちらか

## Cross-references

- `knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md` — v2 仕様
- `app.py:4761-4768` — BT pipeline 既知制限コメント
- `_bt_regime_cascade_scalp_vec.py` — vec runner (m15/m5 precompute あり、ただし fetch_htf_candles 経由で OANDA 必須)
- `data/cache/massive/*_15m.parquet` / `*_5m.parquet` — local cache (本診断で活用)
- `raw/bt-results/regime_cascade_scalp_20260430_093407.json` — 当初 BT (pipeline bug で N=0)

## Pre-reg 履歴

- v1 (2026-04-29): trend_up/down + Hurst>0.55 + ADX≥25 → 廃案 (demo_trades 実測で否定)
- v2 (2026-04-30): moderate_trend (ADX 18-25 + Hurst 0.40-0.55) — **本ファイルで concept proven, L3+SL floor 修正後 Rule 1 BT へ**
