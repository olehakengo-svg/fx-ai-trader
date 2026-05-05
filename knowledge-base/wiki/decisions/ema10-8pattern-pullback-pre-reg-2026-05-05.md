# EMA10 × M15 × 8-Pattern Pullback Pre-Registration (2026-05-05)

## Status
**rule:R1-pre-reg** — 新規戦略候補の BT 実施に先立ち、primary cell・Gate 閾値・Bonferroni 計算を**事後改竄不能な形で固定**する pre-registration。
本 doc 確定後の primary cell 変更は Wave 1 BT 結果に基づく**棄却**としか扱わない（後出し最適化禁止）。

## Why this strategy candidate

ユーザーが SNS 上で流通する「EMA10 × M15 × 8 つのローソク足パターン」手法を提示し、数学的にエッジ化可能か問うた。司令塔判断:

- 機械化は完全に可能。
- ただし fx-ai-trader 既存戦略 [`ema_pullback`](../../../strategies/scalp/ema_pullback.py) [`ema_trend_scalp`](../../../strategies/scalp/ema_trend_scalp.py) [`engulfing_bb`](../../../strategies/scalp/engulfing_bb.py) と本質同型。
- 構造的弱点 4 件（後付け選択バイアス / 混雑トレード / DoF 増加 / spread 感受性）を memory `feedback_partial_quant_trap.md` 基準で評価する必要あり。

ユーザー意思決定（2026-05-05 確認）:
1. Stage 0 sanity のみ先行投入（Stage 1 pre-reg は Gate 通過後）
2. ablation は行わず本手法単独評価のみ
3. tier-master.md 登録は BT 完了まで保留

詳細経緯: `/Users/jg-n-012/.claude/plans/zany-soaring-dolphin.md`

## Mechanized rules (DoF 固定)

### Setup
- **TF**: M15
- **Indicator**: EMA(close, 10) のみ。ADX / RSI / BB / MACD / Stoch は使わない（指示書通りの literal 実装）
- **対象 pair**: USD_JPY のみ（後述 §Data availability で他 3 pair が data prep blocker のため）
- **XAU 除外**: memory `feedback_exclude_xau.md` 準拠

### Trend definition
- Long trend 確立: 足 t の `close > EMA10_t` で確定（前足 `close_{t-1} ≤ EMA10_{t-1}`）
- Long trend 継続: `close > EMA10` が続く間
- Long trend 終了: 足 t の close が下抜け確定した瞬間
- Short は対称

### Pullback touch
- Trend 中の足 t について `Low_t ≤ EMA10_t ≤ High_t`

### 4-pattern confirmation (Long; Short は対称反転)
触れた足 t がこのいずれかであれば valid:

| # | パターン名 | 判定式 |
|---|---|---|
| L1 | Bull pinbar | `lower_wick ≥ 2 × body` AND `body / range ≤ 0.4` AND `close > open` |
| L2 | Hammer-like 陰線（下ヒゲ陰線） | `lower_wick ≥ 2 × body` AND `close < open` |
| L3 | Bullish engulfing | `close_t > open_t` AND `open_t ≤ close_{t-1}` AND `close_t ≥ open_{t-1}` AND `close_{t-1} < open_{t-1}` |
| L4 | Bullish harami breakout | 前足陰線で安値更新、t が `close_t > open_t` AND `close_t > high_{t-1}` |

ここで:
- `body = abs(close - open)`, `range = high - low`, `lower_wick = min(open, close) - low`, `upper_wick = high - max(open, close)`
- `range == 0` の足は全パターン除外（doji 防止）

### Entry / Exit
- **Entry**: 確認足 t の **次の足 t+1 の open** に成行（指示書「次の足でロング」を厳格解釈）
- **TP**: t-1 から遡って直近 N=20 本以内の swing high（fractal-2: 左右 2 本より高い高値が定義式）。見つからなければ entry + 1.5 × ATR(14)
- **SL**: 同 swing 検出で直近 swing low。見つからなければ entry - 1.0 × ATR(14)
- **Forced exit**: 反対方向の trend cross 確定で flat
- **Spread**: USD_JPY は OANDA 30 日中央値（参考: 1.5 pip 程度を 0.015 円換算）を bid/ask 双方向に上乗せ。Pre-registration 値として **1.5 pip 固定**（実測中央値が ±0.3 pip 以内なら採用、外れたら再校正）
- **Slippage**: 0.5 pip / 片道（pre-reg 固定）

### Position sizing
- Kelly fraction = `max(0, 0.25 × raw_kelly)`（Wave 4 系 BT 規約準拠、memory `project_r2_15cell_lock_gate0_accept.md` 同様）

## Stage 0 — Sanity 仕様（本タスクで実行）

| 項目 | 値 |
|---|---|
| Pair | USD_JPY のみ（M5 → M15 リサンプル） |
| Period | 2014-01-02 ~ 2026-04-30（最大利用可能、約 12.3 年） |
| Cell | 1（pre-registered primary cell のみ） |
| Primary cell parameters | `pattern_set = {L1, L2, L3, L4}` 全 4 パターン union, `SL = ATR(14) × 1.0` (swing fail 時), `TP_lookback = 20 bars`, `swing_fractal = 2`, `spread = 1.5 pip`, `slippage = 0.5 pip / side` |
| 出力 metrics | PF, WR, Wilson_lo (95%), N, EV_pip, Avg_R/R, MaxDD, profit_year_concentration, Sharpe |

### Stage 0 Gate (Stage 1 進行可否)

**Pass 条件**: 以下を**全て**満たすこと
1. `PF ≥ 1.10`
2. `Wilson_lo (95%) ≥ 0.50` （WR の 95% Wilson 信頼下限）
3. `N ≥ 150` （統計的有意性最低ライン）
4. `profit_year_concentration < 0.55` （単年が利益の 55% 以上を占めない）
5. `EV_pip > 0` （cost 込みで正期待値）

**Fail 条件**:
- 1〜5 のいずれか不通過 → 棄却 decision doc を `knowledge-base/wiki/decisions/ema10-8pattern-pullback-stage0-reject-YYYY-MM-DD.md` に保存して終了
- データ欠損率 > 2% → data prep task を先行発行（memory `project_w3_4_c1_london_blocked_data.md` 教訓）

## Stage 1 — Bonferroni 計算事前固定（参考、別タスクで発行）

Stage 0 通過時のみ Stage 1 を発行する。pre-reg 値:
- Cell grid（**Stage 1 で他 3 pair の data prep が完了した場合のみ拡張**）:
  - Pair: USD_JPY + EUR_USD + GBP_USD + EUR_JPY = 4
  - SL multiplier: {0.8, 1.0, 1.2} = 3
  - TP_lookback: {10, 20, 30} = 3
  - pattern_set: {pinbar_only(L1+L2), engulfing_only(L3+L4), all_four} = 3
  - **合計 cell 数 = 4 × 3 × 3 × 3 = 108**
- **Bonferroni α**: `0.05 / 108 ≈ 4.6e-4`
- **Primary cell** (LOCK): pair=USD_JPY, SL=1.0, TP_lookback=20, pattern_set=all_four
- **NSG-1 適用**: median_lift > 0 AND sign_agreement ≥ 0.7 AND cv ≤ 0.5 を pair × pattern_set 軸で評価

USD_JPY 単独で Stage 0 通過した場合、Stage 1 は USD_JPY 単独 9 cell から開始（α=0.05/9）し、他 3 pair は data prep 完了後に追加 Bonferroni で再判定。

## Data availability snapshot (2026-05-05)

| Pair | M5 long | M15 cache | Stage 0 利用可否 |
|---|---|---|---|
| USD_JPY | ✅ 2014-01〜2026-04 (903,828 bars) | M5 → M15 リサンプルで 12.3y | ✅ |
| EUR_USD | ❌ 短期のみ | 268 日分 | ❌ data prep blocker |
| GBP_USD | ❌ 短期のみ | 268 日分 | ❌ data prep blocker |
| EUR_JPY | ❌ 短期のみ | 268 日分 | ❌ data prep blocker |

USD_JPY M5 → M15 リサンプル: pandas `resample('15min', closed='left', label='left').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})` を **必ず closed='left', label='left'** で実施（lookahead bias 防止）。

Stage 0 で edge が出た場合に他 3 pair の M5 long データ取得を Stage 1 prerequisite として data prep task に切り出す。

## Acceptance criteria (Codex BT report 必須項目)

Codex Stage 0 タスクは以下を全て出力すること:

```json
{
  "primary_cell": {
    "pair": "USD_JPY",
    "pattern_set": "all_four",
    "sl_multiplier": 1.0,
    "tp_lookback": 20,
    "spread_pip": 1.5,
    "slippage_pip": 0.5
  },
  "metrics": {
    "n": <int>,
    "wr": <float>,
    "wilson_lo_95": <float>,
    "pf": <float>,
    "ev_pip_per_trade": <float>,
    "avg_rr": <float>,
    "max_dd_pip": <float>,
    "max_dd_pct": <float>,
    "sharpe": <float>,
    "profit_year_concentration": <float>
  },
  "yearly_breakdown": [
    {"year": 2014, "n": <int>, "pf": <float>, "ev_pip": <float>}, ...
  ],
  "data_quality": {
    "expected_bars": <int>,
    "actual_bars": <int>,
    "missing_pct": <float>,
    "weekend_filtered": true,
    "resample_method": "M5 closed=left label=left → M15"
  },
  "gate_decision": "PASS" | "FAIL",
  "fail_reasons": [<list of unmet criteria>]
}
```

## What is NOT in scope

- **Strategies/ 配下の実装**: 本タスクは BT のみ、`strategies/scalp/ema10_8pattern.py` の作成は Stage 0 通過後の別タスク
- **demo_trader / app.py 結合**: 実装後タスク
- **ablation study**（既存 ema_pullback との比較）: ユーザー指示で本タスク範囲外
- **tier-master.md 登録**: ユーザー指示で BT 完了まで保留
- **他 3 pair の BT**: data prep 完了前は不可

## Owners
- 司令塔: Claude（pre-reg LOCK、Stage 0 verdict、memory 更新）
- 実働: Codex（BT runner 実装、Stage 0 実行、JSON/md 成果物生成）

## References
- 計画書: `/Users/jg-n-012/.claude/plans/zany-soaring-dolphin.md`
- NSG-1 spec: [`neighborhood-stability-gate-2026-05-04.md`](./neighborhood-stability-gate-2026-05-04.md)
- 部分的クオンツの罠 lesson: [`feedback_partial_quant_trap.md`](../lessons/feedback_partial_quant_trap.md)
- W3-4 C-1 data prep blocker 教訓: memory `project_w3_4_c1_london_blocked_data.md`
- Spread 基準 lesson: memory `feedback_spread_basis_for_mafe.md`
