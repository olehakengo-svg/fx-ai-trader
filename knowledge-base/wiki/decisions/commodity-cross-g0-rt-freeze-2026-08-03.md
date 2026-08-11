# G0 凍結 — commodity_cross_range_mr (#21) の OANDA RT 実測ゲート — 2026-08-03

> **rule:R3 (摩擦実測、シグナル計算ゼロ)**。台帳 [[hypothesis-catalog-2026-07-24]] #21 の必須事前ゲート。
> **凍結原則**: 本ドキュメントの閾値・定義は**測定実行前にコミット**され、測定後に変更しない。
> **関連**: [[ea-landscape-sweep-2026-07-31]] §4.1 (G0 の由来) / [[weekend-gap-stage2-execution-prereg-2026-07-24]] (BA candles 実測の先行方法論)

## 1. 目的と範囲

台帳 #21 の G0 = 「OANDA の 3 クロス実測 RT。stressed_RT×10 > prior_edge_width (30-50p) なら family ABORT」。
本測定は **fwd return / シグナル / MFE に一切接触しない摩擦のみの測定** — pre-reg スロット・BH 分母を消費しない。

**原文 (ledger) からの明示的偏差**: 原文は「live RT spread ≥1 週間」だが、本測定は **OANDA M5 bid/ask candles の遡及 60 営業日** (≥1 週間を包含する上位互換)。weekend_gap R1 step① (`tools/sunday_open_spread_measure.py`、prereg §9 で承認済み) と同一の測定原理 (candle ask−bid = 実配信スプレッド)。

## 2. 測定仕様 (凍結)

- **対象**: AUD_NZD, AUD_CAD, NZD_CAD (pip = 1e-4)
- **アンカー (妥当性検証用)**: AUD_USD, USD_JPY — friction table 既知値との突合
- **データ**: OANDA live REST `candles`, granularity=M5, price=BA, complete バーのみ。直近 60 営業日 (週末 Fri 21:00 UTC〜Sun 21:00 UTC のバーは除外)
- **spread 定義**: `(ask.c − bid.c) / pip` (バー close 時点の配信スプレッド)
- **統計**: 全時間帯 p50/p75/p90/p99、UTC 時間帯別 (24 bucket) p50/p75、特別窓 = ロールオーバー/D1 close 帯 (21:00–22:59 UTC)・流動窓 (07:00–16:00 UTC)

## 3. stressed RT 定義と ABORT 閾値 (凍結 — 測定前)

- **stressed_RT_primary = p75(spread, 全時間帯) + 1.0p** (slippage 往復: 0.5p ×2、メジャー実測値をクロスに保守適用)
- **stressed_RT_conservative = p90(spread, 全時間帯) + 2.0p** (薄板 slippage 感度、参考値 — 判定には使わない)
- **判定 (機械的)**:
  - ペア **PASS** ⟺ stressed_RT_primary ≤ **5.0p** (= prior_edge_width 上限 50p ÷ headroom 10×)
  - ペア **MARGINAL** ⟺ 5.0p < stressed_RT_primary ≤ 6.5p — explore 参加可だが、explore 側の headroom gate (実測 MFE ≥ 10×RT) を stressed_RT_conservative で通過することを追加条件とする
  - ペア **FAIL** ⟺ stressed_RT_primary > 6.5p
  - **family ABORT ⟺ 3 ペア全て FAIL**。PASS ≥1 で explore pre-reg 起案へ進む (MARGINAL のみ生存の場合は起案時に敵対的検証で可否判断)
- **測定 INVALID 条件**: アンカーの p50 spread が friction table 記載 spread (USD_JPY 0.7p / AUD_USD 参考 1.2p) の 2.5 倍を超える場合、測定系の異常とみなし verdict を出さない

## 4. 副次出力 (explore 設計への friction-informed 入力 — fwd 非接触)

- **執行時間帯マップ**: 20:00–02:59 UTC の時間帯別 p75 から、D1 close 近傍で最も摩擦の低い執行時間を特定 (D1 close 21/22:00 UTC はロールオーバー窓と重なるため、explore pre-reg の entry 執行時刻凍結に使う)
- multi-day 保有の swap は本測定の範囲外 — explore pre-reg 側で stressed-net に算入 (weekend_gap 基準)

## 5. 実装

`tools/commodity_cross_rt_measure.py` (本コミットに同梱)。read-only GET のみ、注文 API 不使用。出力: `knowledge-base/raw/bt-results/commodity_cross_rt-2026-08-03.json` + `reports/commodity-cross-rt-g0-2026-08-03.md`。
