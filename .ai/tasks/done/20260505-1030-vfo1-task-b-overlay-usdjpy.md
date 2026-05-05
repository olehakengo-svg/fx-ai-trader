---
id: 20260505-1030-vfo1-task-b-overlay-usdjpy
title: "[VFO-1 Task B] HAR-RV vol-target overlay 統合 (USDJPY 単独, Shadow デフォルト ON / LIVE デフォルト OFF)"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T10:30:00+0900
roadmap_gate: VFO-1 Task B (Top 1 of post-Qiita-article gap analysis) — Phase 1 PASS 後の overlay 統合
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md
  - knowledge-base/wiki/decisions/vfo1-phase1-qlike-override-2026-05-05.md  # R3 override 2026-05-05 — gate amended
  - .ai/runs/20260504-182426-20260504-1840-vfo1-phase1-validation/final.md
  - knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md  # 2026-05-05 amended to PASS under override
  - .ai/runs/20260505-103613-20260505-1030-vfo1-task-b-overlay-usdjpy/final.md  # prior BLOCKED_PRECONDITION run; override now resolves
  - modules/vol_forecast.py
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
---

# 0. Why this task

VFO-1 Phase 1 **PASS for USDJPY (under R3 override 2026-05-05)**:

旧 strict gate (MAE と QLIKE の両方 ≥5%) では FAIL だったが、**司令塔 Claude が R3 override を発行**:
- 理由: 両 predictor の R² が 0.93+ で saturated 領域、QLIKE が log space で非情報的になる構造的問題
- 詳細: `knowledge-base/wiki/decisions/vfo1-phase1-qlike-override-2026-05-05.md`
- Amended gate: (a) MAE ≥5% PASS / (b) QLIKE ≥0% sanity / (c) HAR R² ≥ Naive R² sanity → 3/3 cells PASS

USDJPY M5/H1/D1 amended gate PASS:
- M5: MAE imp 21.39%, QLIKE imp 0.04% (>=0%, sanity OK), R² 0.969 vs 0.965
- H1: MAE imp 24.96%, QLIKE imp 0.05%, R² 0.954 vs 0.947
- D1: MAE imp 18.97%, QLIKE imp 0.07%, R² 0.947 vs 0.932

EUR_USD / GBP_USD は INSUFFICIENT_DATA (12y MASSIVE cache 未拡張)。Task B は **USDJPY 単独で先行統合**、データ拡張後に他ペアを追加する 2 段階運用。

**Safety net**: R3 override の正当性は Phase 2 BT (max DD -10%+ 削減 / Kelly ±15% 以内) で検証される。Phase 2 で Kelly -15% 超え戦略が複数出たら override 撤回 + QLIKE 計算 bug 調査。

Phase 1 PASS (under override) により Task B 起動条件 (spec doc §5.2) を満たす。本タスクは overlay 統合 + Phase 2 BT 評価のみ。LIVE 切替は Phase 3 (Shadow 並走 4 週) 後の別決定。

## 重要 (前回 BLOCKED_PRECONDITION の解消)

前回 run (`.ai/runs/20260505-103613-...`) は canonical Phase 1 audit が `FAIL` となっていたために Codex が正しく BLOCKED_PRECONDITION 判定。司令塔 Claude が R3 override を発行 + audit を「PASS under override」に amendment 済み。本 run では **canonical audit を必ず再読** して PASS confirmation を取ってから Task B 実装に入る。確認手順:

```bash
head -10 knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md  # "PASS under override" header を確認
```

ヘッダーが PASS でなければ **再度 BLOCKED_PRECONDITION** で stop & escalate。

# 1. Inputs

1. **Spec** (必読): `knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md` §3 Integration point / §4.2 Phase 2 / §5.2 Task B
2. **Phase 1 verdict report**: `knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md` (USDJPY only PASS の根拠)
3. **既存予測モジュール**: `modules/vol_forecast.py` (Task A で作成済、本タスクで `vol_forecast_mult` をインポートして使う)
4. **既存 sizing flow**: `modules/demo_trader.py:4608-4615`
   - line 4608: `_eq_mult = self._dd_lot_mult`
   - line 4612: `_agg_boost = self._get_agg_kelly_lot_boost()`
   - line 4613: `_boost_factor = _strat_boost * _eq_mult * _agg_boost`
   - line 4615: `_lot_ratio = _risk_factor * _edge_factor * _boost_factor`
5. **既存 Tier 1 LIVE 戦略 BT runner**: `tools/bt/_bt_all_strategies_analyze.py` 等 (Phase 2 評価用)

# 2. Scope

Codex may change:

- `modules/risk_analytics.py` — `apply_vol_overlay(lot_mult: float, instrument: str, timeframe: str, asof_utc: datetime, *, enabled: bool) -> tuple[float, dict]` 追加 (pure function、副作用なし)
- `modules/demo_trader.py` — line 4613 周辺に **5 行以内の patch** (overlay 呼び出し + log)
- `tools/bt/vfo1_phase2_overlay_eval.py` (新規) — Phase 2 BT 評価スクリプト
- `tests/test_vfo_overlay_integration.py` (新規) — overlay 結合テスト
- `knowledge-base/raw/audits/vfo1-phase2-2026-05-05.md` (新規 Phase 2 レポート)
- `.ai/runs/<timestamp>-vfo1-task-b-overlay-usdjpy/final.md`

Codex must not change:

- `modules/vol_forecast.py` (Task A で完成済、変更不可。バグ発見時は spec 違反として stop & escalate)
- `strategies/**`
- `app.py`, `live_*.py`
- production secrets / .env / render.yaml
- 既存 Tier 1 LIVE 戦略の signal/entry/exit ロジック

# 3. Required Reading

- `CLAUDE.md`
- spec doc (`knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md`)
- Phase 1 report (`knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md`)
- `knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md` (direction edge を毀損しない原則)
- `knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md` (BT は MASSIVE データソース)

# 4. Implementation contract

## 4.1 `modules/risk_analytics.py:apply_vol_overlay`

```python
def apply_vol_overlay(
    lot_mult: float,
    instrument: str,
    timeframe: str,
    asof_utc: datetime,
    *,
    enabled: bool,
    floor: float = 0.30,
    ceiling: float = 1.50,
) -> tuple[float, dict]:
    """Apply VFO-1 vol-target overlay to a sizing multiplier.

    Returns (new_lot_mult, info_dict). info_dict contains
    {'enabled', 'instrument', 'tf', 'vfo_mult', 'reason'} for logging.
    """
```

挙動:
- `enabled=False` → return `(lot_mult, {'enabled': False, ...})` no-op
- `instrument != 'USD_JPY'` → return `(lot_mult, {'enabled': False, 'reason': 'non_usdjpy_v1_scope'})` (Task B v1 は USDJPY 単独限定。spec §2.1 PASS 範囲に厳格に従う)
- `instrument == 'USD_JPY'` AND `enabled=True` →
  - `vfo_mult = vol_forecast.vol_forecast_mult(instrument, timeframe, asof_utc, floor=floor, ceiling=ceiling)`
  - return `(lot_mult * vfo_mult, {'enabled': True, 'vfo_mult': vfo_mult, ...})`

## 4.2 `modules/demo_trader.py` 統合

line 4613 直前 (`_boost_factor = _strat_boost * _eq_mult * _agg_boost` の **直前**) に挿入:

```python
# VFO-1 vol-target overlay (Phase 2 trial; FX_VOL_OVERLAY env, default OFF)
_vfo_enabled = _os.environ.get("FX_VOL_OVERLAY", "0") == "1"
_vfo_tf = self._get_strategy_default_tf(entry_type) or "M5"  # 戦略既定 TF を使う
_eq_mult, _vfo_info = apply_vol_overlay(
    _eq_mult, instrument, _vfo_tf, _now_utc, enabled=_vfo_enabled
)
if _vfo_info.get('enabled'):
    self._add_log(f"[VFO] {instrument}/{_vfo_tf} mult={_vfo_info['vfo_mult']:.3f}")
```

**規律**:
- `FX_VOL_OVERLAY` 環境変数で gate (default OFF)。LIVE プロセスでは未設定で動かないこと。
- 戦略 TF が取得できない場合 M5 fallback (spec §6 R2 緩和)。
- log 出力は `[VFO]` prefix 必須 (既存 `[KELLY]`, `[PRIME]`, `[DD]` と整合)

`_get_strategy_default_tf(entry_type)` ヘルパが既存にない場合: 既存 strategy → TF mapping から推定 (`strategies/scalp/* → M5`, `strategies/daytrade/* → M15` or `H1`, `strategies/hourly/* → H1` 等)。1 行 dict で足りる。**新規ヘルパ追加は許容**。

## 4.3 Phase 2 BT 評価 `tools/bt/vfo1_phase2_overlay_eval.py`

CLI:

```bash
python3 tools/bt/vfo1_phase2_overlay_eval.py \
    --strategies doji_breakout,ema200_trend_reversal,squeeze_release_momentum,xs_momentum,trendline_sweep \
    --instrument USD_JPY \
    --timeframes M5,H1,D1 \
    --start 2024-04-30 \
    --end 2026-04-30 \
    --output knowledge-base/raw/audits/vfo1-phase2-2026-05-05.md
```

戦略は **既存 Tier 1 LIVE のうち USDJPY 通過しているもの 5 つ**:
- doji_breakout (USD_JPY pair_promoted)
- ema200_trend_reversal (USD_JPY pair_promoted)
- streak_reversal (USD_JPY pair_promoted)
- xs_momentum (USDJPY 経由)
- trendline_sweep (ELITE_LIVE)

データソース: **MASSIVE Market Data 必須** (`feedback_bt_must_use_massive` 記憶)、`data/cache/massive/USD_JPY_*.parquet` を `modules/data.py` 経由で読む。

評価指標 (per strategy × {with overlay, without overlay}):
- N
- Wilson_lo (95% CI)
- PF
- Kelly
- Max DD (pip)
- Sharpe (annualized)
- Total PnL (pip)

**採用条件** (spec §4.2):
- max DD が **10% 以上削減** (with vs without overlay)
- Kelly が **±15% 以内** (direction edge 不毀損確認)

**1 回限定の閾値調整**: 1 戦略でも Kelly が -15% 以下なら overlay の floor (0.30) / ceiling (1.50) を 1 回だけ調整 (spec §4.2 規律)。2 回目以降の調整は post-hoc selection trap として禁止。

## 4.4 Tests `tests/test_vfo_overlay_integration.py` (最低 6 テスト)

1. **disabled passthrough**: `enabled=False` で lot_mult 不変
2. **non-USDJPY skip**: `instrument='EUR_USD'` で v1 scope 外 → no-op + reason 記載
3. **USDJPY enabled application**: `instrument='USD_JPY'` で `vfo_mult ∈ [floor, ceiling]` が掛かる
4. **floor / ceiling clip**: 極端 σ̂ 入力で clip される
5. **demo_trader integration smoke**: `FX_VOL_OVERLAY=1` で `apply_vol_overlay` が正しく呼ばれることを mock で確認 (一部 mock 可、ただし vol_forecast 自体は実関数呼び出し必須)
6. **env default OFF**: `FX_VOL_OVERLAY` 未設定で no-op

# 5. Acceptance Criteria

- [ ] `pytest tests/test_vfo_overlay_integration.py -v` 6 テスト PASS
- [ ] `python3 -m ruff check modules/risk_analytics.py modules/demo_trader.py tools/bt/vfo1_phase2_overlay_eval.py` PASS
- [ ] `python3 -m mypy modules/risk_analytics.py` PASS
- [ ] `python3 tools/bt/vfo1_phase2_overlay_eval.py --help` 成立
- [ ] **実 MASSIVE データで Phase 2 BT 完遂**: 5 戦略 × {with, without overlay} = 10 BT 結果が JSON+MD 出力
- [ ] 採用条件評価表が report に含まれる: 各戦略について max DD 削減率 / Kelly 変化率 / verdict (ADOPT_FOR_SHADOW / REJECT)
- [ ] **demo_trader.py の patch は 5 行以内** (cosmetic 1-2 行追加は許容)。それ超えたら spec 違反、stop & escalate
- [ ] **LIVE 環境影響ゼロ確認**: `FX_VOL_OVERLAY` 未設定での既存 Tier 1 戦略 BT 1 本が pre-overlay と完全同値であること (numerical regression test)
- [ ] Run report `.ai/runs/<timestamp>-vfo1-task-b-overlay-usdjpy/final.md` に Phase 2 verdict 表 + Phase 3 (Shadow 並走) 起動可否の推奨

# 6. Verification Commands

```bash
pytest tests/test_vfo_overlay_integration.py -v
python3 -m ruff check modules/risk_analytics.py modules/demo_trader.py tools/bt/vfo1_phase2_overlay_eval.py
python3 -m mypy modules/risk_analytics.py
python3 tools/bt/vfo1_phase2_overlay_eval.py --help
python3 tools/bt/vfo1_phase2_overlay_eval.py \
    --strategies doji_breakout,ema200_trend_reversal,streak_reversal,xs_momentum,trendline_sweep \
    --instrument USD_JPY --timeframes M5,H1,D1 \
    --start 2024-04-30 --end 2026-04-30 \
    --output knowledge-base/raw/audits/vfo1-phase2-2026-05-05.md

# Numerical regression check (LIVE 影響ゼロ):
FX_VOL_OVERLAY="" python3 tools/bt/_bt_all_strategies_analyze.py --strategy doji_breakout --instrument USD_JPY --start 2025-01-01 --end 2025-04-30 --output /tmp/pre-overlay.json
# After patch:
FX_VOL_OVERLAY="" python3 tools/bt/_bt_all_strategies_analyze.py --strategy doji_breakout --instrument USD_JPY --start 2025-01-01 --end 2025-04-30 --output /tmp/post-overlay.json
diff /tmp/pre-overlay.json /tmp/post-overlay.json  # 期待: 完全同値
```

# 7. Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.

実装手順:

1. spec を読む。**Task B v1 は USDJPY 単独**であり、EUR_USD/GBP_USD は scope 外。間違って scope 拡張しないこと。
2. **MASSIVE データソース必須**。Yahoo / yfinance を使ったら `feedback_bt_must_use_massive` 違反。
3. RED first: tests を先に書いて FAIL → GREEN へ。
4. Phase 2 BT は **5 戦略 × USDJPY × 24 ヶ月** (test 期間)。LIVE 影響ゼロ regression test も必ず走らせる。
5. 採用条件 (max DD 10%+ 削減 + Kelly ±15% 以内) を満たさない戦略があったら、その旨を report に明記。1 戦略でも Kelly -15% 以下なら spec §4.2 の 1 回限定 floor/ceiling 調整を実施 (回数厳守)。
6. **direction edge 毀損 (Kelly -15% 超え) が複数戦略で出たら overlay 採用は STOP**。Phase 3 起動を report で否定し、claude にエスカレート。

In the final report, include status, files changed, verification output, **per-strategy Phase 2 verdict 表 (ADOPT_FOR_SHADOW / REJECT)**, max DD 削減率と Kelly 変化率の集計、LIVE regression test 結果、Phase 3 (Shadow 4 週並走) 起動可否の推奨、remaining risks。


## Result (2026-05-05T02:38:13Z)

exit=0 · 8s

```
BLOCKED_PRECONDITION.

The canonical Phase 1 audit still begins with:

```text
# VFO-1 Phase 1 Verdict: FAIL

**Decision:** PHASE 1 FAIL
```

Per your instruction, I stopped before implementation because `knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md` does not confirm “PASS under override”.

Additional blockers found during required reading:

- `knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md` is missing.
- `knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md` is missing.
- `knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md` is missing.

No files were changed.
```
