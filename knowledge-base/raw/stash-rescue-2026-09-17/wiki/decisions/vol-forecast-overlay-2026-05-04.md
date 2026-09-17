---
title: Vol Forecast Overlay (VFO-1) — GARCH/HAR-RV による動的サイジング層
date: 2026-05-04
status: PROPOSED → READY_FOR_POC
owner: claude-司令塔
implementer: codex
trigger: 現行は方向予測戦略のみ、ボラ自体を予測する層が皆無
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md
roadmap_gate: meta-discipline / cross-strategy overlay
---

# 1. Why this overlay exists

Qiita 記事の指摘: **方向は当たらないがボラは比較的予測可能** (vol clustering)。
現行 fx-ai-trader は:

- 方向予測戦略 31 個 (Phase 0 Shadow Gate)
- DD ベース sizing (`risk_analytics.get_dd_lot_multiplier`) ✓
- ATR ベース停止距離 ✓
- **だが GARCH/HAR-RV ベースの ex-ante vol 予測層は無し**

VFO-1 は **方向戦略を一切変えず**、Kelly × DD × **vol_forecast_mult** の 3 段サイジングに拡張する。MA filter trap (記憶) や HMM gate trap (記憶) の教訓: 方向戦略にゲートを足すとエッジが消える。**サイジング層なら direction edge を毀損しない**。

期待効果:

- vol-of-vol 拡張時に lot を削り、Wave 4 max DD を構造的に抑制
- vol 収縮直後に lot を維持 (現行 ATR は静的なので "波収まり" を逃す)
- vol regime を新 cell 軸として tier-master.md に追加 (将来的に MR/Trend の cell 振り分けに使う)

# 2. Scope of v1 (POC)

**v1 は overlay 1 機能のみ**。tier-master 拡張や regime cell 化は v2 (別決定文書) で扱う。

## 2.1 v1 機能

ペア×TF ごとに ex-ante 1-step σ̂ を予測 → vol_forecast_mult を返す pure function。

```python
def vol_forecast_mult(
    instrument: str,           # "USD_JPY" 等
    timeframe: str,            # "M5" / "M15" / "H1" / "D1"
    asof_utc: datetime,        # 予測時点 (closed-bar 規律)
    *,
    target_realized_vol: float | None = None,   # None なら 12y rolling median
    floor: float = 0.30,
    ceiling: float = 1.50,
    cache_dir: str | None = None,
) -> float:
    """Return scalar in [floor, ceiling]. Multiply lot by this value."""
```

挙動:

- σ̂_{t+1} を **HAR-RV** (Heterogeneous Autoregressive Realized Volatility) で推定。GARCH(1,1) は v2 候補で、v1 は HAR-RV のみ。
  - HAR-RV: `RV_t = β0 + β_d RV_{t-1} + β_w RV_{1:5}_avg + β_m RV_{1:22}_avg + ε`
  - 採用理由: 解釈容易、closed-form、外部依存なし (numpy/statsmodels で十分)、long-memory を捕捉。GARCH は arch lib 依存で運用の摩擦が大きい。
- 1 ステップ先 σ̂ を、その instrument×TF の 12y 中央値で割る → ratio。
- `mult = clip(target_vol / σ̂, floor, ceiling)`. σ̂ が大きいほど mult は小さい (lot を削る)。

## 2.2 規律

- **closed-bar 規律**: `asof_utc` の直前 closed bar までの情報のみ使用 (lookahead 禁止)。bb_rsi_reversion 等で確立済の規律と同等。
- **ペア×TF ごとに独立** に学習 / 推論 (cross-pair pooling は v2 候補)。
- **再学習は週次** (`tools/audit/refit_vol_forecast.py` を週末 cron で運用)。POC 期間は手動再学習で OK。
- **キャッシュ**: 予測結果は process-level dict に instrument×TF×asof_min 単位でキャッシュ。同 bar 内多重呼び出しは O(1)。

# 3. Integration point

## 3.1 demo_trader.py での挿入箇所

既存 sizing flow:

```
base_lot → DD multiplier (get_dd_lot_multiplier) → final_lot
```

VFO-1 適用後:

```
base_lot → DD multiplier → vol_forecast_mult → final_lot
```

挿入は `demo_trader.py` の lot 確定直前 (`_dd_lot_mult` 適用直後)。1 箇所、5 行以内の patch。

**Feature flag**: 環境変数 `FX_VOL_OVERLAY=1` でオン、デフォルト OFF。POC 期間は LIVE で OFF、Shadow で ON 並走。

## 3.2 Backtest harness での挿入

`tools/bt/*` の sizing 行に同名関数を呼び出すだけ。BT は env flag 不要、常時オンで OK (検証目的)。

# 4. POC validation plan

## 4.1 Phase 1: σ̂ predictability (mandatory pre-implementation)

実 BT 結合の前に **σ̂ そのものの予測精度** が naive を上回るか確認:

- USDJPY M5 / H1 / D1 の各 TF で 12y データを 80/20 train/test 分割
- Naive baseline: rolling 22-day std
- HAR-RV と Naive を MAE / QLIKE で比較
- HAR-RV が **両指標で 5% 以上改善** しなければ **本実装中止** (overlay の前提が崩れる)

## 4.2 Phase 2: BT で Kelly / max DD への寄与を測定

Phase 1 PASS なら BT で:

- 既存 Tier 1 LIVE 戦略 5 つ (doji_breakout, ema200_trend_reversal, など) に overlay を被せた場合 vs 被せない場合の Kelly / max DD / Sharpe を比較
- **採用条件**: max DD が 10% 以上削減、Kelly が ±15% 以内 (=方向 edge を毀損しない)
- 1 戦略でも Kelly が 15% 以上削減されたら overlay の floor / ceiling を 1 回だけ調整 (post-hoc selection 罠を避けるため 2 回目以降は禁止)

## 4.3 Phase 3: Shadow 並走

Phase 2 採用条件 OK なら Shadow で 4 週間並走、PRIME 並走と同じく:

- LIVE/Shadow 分離規律 (記憶 feedback_live_shadow_separation) を厳守
- 4 週後に max DD / Kelly / N をレビュー → LIVE 切替判定

# 5. Implementation contract (POC ステージのみ)

POC は **2 タスクに分割** (実装の安全性確保):

## 5.1 Task A — σ̂ predictor + Phase 1 validation

- `modules/vol_forecast.py` 新規 (HAR-RV pure module、closed-bar、process cache)
- `tests/test_vol_forecast.py` 新規 (synthetic AR(1) データで closed-bar 規律と HAR-RV の妥当性を確認)
- `tools/audit/vol_forecast_phase1_validation.py` 新規 (Phase 1 MAE/QLIKE 比較スクリプト)
- レポート `knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md` 出力
- **Phase 1 が naive 5% 改善を満たさない場合は Task B 投入を保留**

## 5.2 Task B — Overlay 統合 (Phase 1 PASS 後のみ起動)

- `demo_trader.py` に overlay 呼び出し挿入 (env flag 付き)
- `modules/risk_analytics.py` に `apply_vol_overlay(lot, instrument, tf, asof)` ヘルパ追加
- BT harness 1 本に同名関数を結合 (`tools/bt/<...>` 1 ファイル)
- Phase 2 BT 実施、レポート出力
- LIVE 切替は **本タスクの対象外** (Phase 3 Shadow 並走後の別決定で)

# 6. Risks

- **R1 — HAR-RV は寒帯で歪む**: 重要イベント直後の極端 RV で σ̂ が overshooting し、過剰に lot を削る可能性。緩和: floor=0.30 で下限を切る。
- **R2 — TF mismatch**: M5 σ̂ で M5 lot を制御するのは自然だが、D1 戦略で M5 σ̂ を使うと過敏。**戦略の TF と同じ TF の σ̂ を使う規律** を Task B で明示。
- **R3 — overfit risk on POC**: Phase 1 で HAR-RV vs naive 比較する際、target σ の中央値選び方で post-hoc 罠あり。緩和: 12y 中央値固定、in-sample で決めない。
- **R4 — feature flag 漏れ**: Shadow で ON、LIVE で OFF を保つはずが LIVE に漏れる事故。緩和: env flag は demo_trader.py の 1 箇所のみで読み取り、デフォルト OFF をハードコード。

# 7. Out of scope (v1)

- GARCH(1,1) 系 (arch lib 依存、v2 候補)
- vol regime cell 化 (tier-master 拡張、v2 候補)
- Variance proxy 合成 VIX 風シグナル (派生戦略、v2 候補)
- Cross-pair pooling (v2 候補)
