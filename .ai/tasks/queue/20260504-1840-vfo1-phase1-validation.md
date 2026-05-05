---
id: 20260504-1840-vfo1-phase1-validation
title: "[VFO-1 Task A] HAR-RV σ̂ predictor + Phase 1 validation (no overlay yet)"
owner: codex
status: queued
priority: P2
created_at: 2026-05-04T18:40:00+0900
roadmap_gate: VFO-1 (Top 1 of post-Qiita-article gap analysis)
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. Why this task

司令塔 Claude の Qiita 記事ギャップ分析 5 提案中 Top 1 (VFO-1) の **POC Task A**。spec doc §5.1 に対応。**Phase 1 で σ̂ 予測精度が naive を上回らなければ overlay は実装しない** 設計のため、本タスクは予測精度検証のみ (overlay 統合 = Task B は別ファイル別ジョブ)。

# 1. Inputs

1. **Spec** (必読): `knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md`
2. 既存 OHLCV ローダ: `modules/data.py`
3. 12y キャッシュの所在: `data/cache/extended/`, `data/cache/massive/`

# 2. Scope

Codex may change:

- `modules/vol_forecast.py` (新規)
- `tests/test_vol_forecast.py` (新規)
- `tools/audit/vol_forecast_phase1_validation.py` (新規)
- `knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md` (新規 Phase 1 レポート)

Codex must not change:

- `demo_trader.py`, `modules/risk_analytics.py` (Task B の対象)
- 既存戦略 `strategies/**`
- 既存 BT runner

# 3. Required Reading

- `CLAUDE.md`
- spec doc `knowledge-base/wiki/decisions/vol-forecast-overlay-2026-05-04.md`
- HAR-RV の参照: Corsi (2009) "A Simple Approximate Long-Memory Model of Realized Volatility" (statsmodels の OLS で実装可)
- `knowledge-base/wiki/lessons/feedback_codex_mock_test_trap.md` (mock-only テストの罠回避)

# 4. Implementation contract

## 4.1 `modules/vol_forecast.py`

Pure module. **No I/O 以外の副作用なし**、process-level dict cache のみ。

```python
def fit_har_rv(rv_series: pd.Series) -> dict[str, float]:
    """OLS で β0, β_d, β_w, β_m を推定。返り値はパラメタ dict。"""

def predict_har_rv(params: dict[str, float], rv_history: pd.Series) -> float:
    """1-step ahead σ̂ を返す。closed-bar 規律: rv_history は asof_utc 直前まで。"""

def realized_vol_from_returns(returns: pd.Series, window: int) -> pd.Series:
    """sqrt(sum r^2) over window。standard RV definition。"""

def vol_forecast_mult(
    instrument: str,
    timeframe: str,
    asof_utc: datetime,
    *,
    target_realized_vol: float | None = None,
    floor: float = 0.30,
    ceiling: float = 1.50,
    cache_dir: str | None = None,
) -> float: ...
```

## 4.2 Tests `tests/test_vol_forecast.py` (最低 5 テスト)

1. **HAR-RV fit on synthetic AR(1) data**: パラメタが OLS で安定推定されること。
2. **closed-bar guard**: `rv_history` の最終 bar が `asof_utc` より新しい場合 `ValueError`。
3. **floor / ceiling clip**: 極端 σ̂ 入力で `vol_forecast_mult` が [floor, ceiling] にクリップされること。
4. **cache deterministic**: 同 instrument×TF×asof_min で 2 回呼んで同値、cache hit カウントが増えること。
5. **insufficient history**: rv_history が 22 bar 未満なら mult=1.0 (no-op fallback)。

## 4.3 Phase 1 validation script `tools/audit/vol_forecast_phase1_validation.py`

CLI:

```bash
python3 tools/audit/vol_forecast_phase1_validation.py \
    --instruments USD_JPY,EUR_USD,GBP_USD \
    --timeframes M5,H1,D1 \
    --train-end 2024-04-30 \
    --test-end 2026-04-30 \
    --output knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md
```

挙動:

- 各 (instrument, TF) で:
  - 12y データを `--train-end` で分割
  - HAR-RV を train で fit
  - test 期間で 1-step ahead σ̂ を rolling 予測 (closed-bar 規律維持)
  - Naive baseline (rolling 22-day std) も並行計算
  - MAE / QLIKE / R² の 3 指標で比較
- レポート MD に表形式で出力 (instrument × TF × metric × {HAR-RV, Naive, % improvement})
- **判定基準**: HAR-RV が MAE と QLIKE の **両方** で 5% 以上改善している (instrument×TF) cell が **過半数** あれば PHASE 1 PASS、そうでなければ FAIL。

## 4.4 Acceptance Criteria

- [ ] `pytest tests/test_vol_forecast.py -v` 5 テスト PASS
- [ ] `python3 tools/audit/vol_forecast_phase1_validation.py --help` 成立
- [ ] `python3 tools/audit/vol_forecast_phase1_validation.py` を 実 12y データで実行成功 (mock 不可)
- [ ] レポート `knowledge-base/raw/audits/vfo1-phase1-2026-05-04.md` に判定 (PASS / FAIL) と数値表が記載
- [ ] **重要**: PASS ／ FAIL いずれの場合も Task B は **投入しない**。判定結果を司令塔 Claude が確認してから Task B 起動。
- [ ] Run report `.ai/runs/<timestamp>-vfo1-phase1-validation/final.md`

# 5. Verification Commands

```bash
pytest tests/test_vol_forecast.py -v
ruff check modules/vol_forecast.py tools/audit/vol_forecast_phase1_validation.py
mypy modules/vol_forecast.py
python3 tools/audit/vol_forecast_phase1_validation.py --help
python3 tools/audit/vol_forecast_phase1_validation.py \
    --instruments USD_JPY,EUR_USD --timeframes H1,D1 \
    --train-end 2024-04-30 --test-end 2026-04-30 \
    --output /tmp/vfo1-phase1-smoke.md
```

# 6. Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.

実装手順:

1. spec を読み、HAR-RV 数式を理解 (Corsi 2009)。
2. RED first: tests を先に書いて FAIL → GREEN へ。
3. Phase 1 script は **必ず実 12y データで動かす** (記憶: mock-only テスト trap)。データが取れない instrument×TF があれば限定的に走らせて limitation を report に明記。
4. レポートは **判定 (PASS/FAIL) を目立つ形で先頭** に。

In the final report, include status, files changed, verification output summary, **Phase 1 verdict (PASS/FAIL)**, per-instrument-TF improvement table, remaining risks, and next recommended task (= Task B 起動可否)。
