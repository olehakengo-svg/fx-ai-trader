---
id: 20260504T1753-fx-nexus-step1-shadow
title: FX Nexus Step 1 — Currency Value V_ti + Triangular residual α + τ_exec jitter (shadow only, no LIVE intervention)
owner: codex
status: queued
priority: P2 (data-layer infrastructure for FX Nexus research, not on critical path)
created_at: 2026-05-04T17:53:00+0900
roadmap_gate: Wave 5 候補化に向けた shadow データ蓄積（W4-EDA Tier 1 監査と並列）
rule: R1 (新規 feature 追加だが LIVE 介入なし → R1 strict prereg、ただし shadow 観測 N 蓄積フェーズに限定)
prerequisite_decisions:
  - 2026-05-04 Plan: /Users/jg-n-012/.claude/plans/fx-nexus-fx-sunny-wombat.md (User APPROVED)
  - 参考論文: arXiv 2508.14784 (Hong & Klabjan, 2025)
unblocks:
  - Wave 5 α reversion MR 戦略 spec 起票（Bonferroni m=5 / p<0.01 で α が next-bar return を予測した場合のみ）
  - W4-EDA Tier 1 TIMING_BROKEN 自動判定 CI 統合
deliverable:
  - modules/fx_graph.py（新規）
  - modules/currency_strength.py（拡張、後方互換維持）
  - modules/backtest_engine.py（--exec-lag-jitter フラグ追加）
  - tests/test_fx_graph.py（新規、TDD red→green、3 ケース）
  - tools/fx_nexus_shadow_audit.py（新規）
  - knowledge-base/wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md（pre-reg LOCK）
  - knowledge-base/wiki/strategies/fx_nexus_alpha_residual.md（shadow 観測対象として登録）
---

## 0. なぜ今このタスクか

ユーザーは FX Nexus 構想（マルチカレンシー × Graph DB 分析基盤）の参考論文として
[Hong & Klabjan (2025)](https://arxiv.org/abs/2508.14784) を提示し、クオンツ視点での応用検討を依頼。

**Claude (司令塔) の評価結論**:
- 論文の GNN 予測モデルそのものは現行システムへの直接導入に不適（取引コスト/JGB 異常値/N 不足）
- ただし論文の **3 つの数学的構造** は現行 5 ペア体制でも実装可能で、既存規律（Wilson/Bonferroni/Rule 1）と整合:
  - **A**: Currency Value V_ti を MLE で同時推定（既存 `currency_strength.py` の経験則の数学的一般化）
  - **B**: Triangular residual α_tij を MR signal 候補として shadow 計測
  - **C**: τ_exec ∈ (0,1) jitter による lookahead 戦略の自動 TIMING_BROKEN 判定

**本タスクの目的**:
1. データ層に V_ti / α 計算を導入（LIVE 介入なし）
2. 過去 12 ヶ月分の α residual を計測し、各 LIVE 戦略 entry 時の α 値分布を report
3. BT エンジンに τ_exec jitter フラグを追加し、squeeze_release_momentum 等 lookahead 戦略の edge 喪失を自動検証
4. **判定ゲート**は本タスクでは触らず、次セッション（Wave 5 起票時）に決定

## 1. 仮説（pre-registered）

**H1 (V_ti)**: Eq. 8-9 の MLE 推定 V_ti は、既存 basket_strength と相関 0.85+ だが、cross-section 同時推定により basket_strength より低分散・高安定。
判定: V_ti と basket_strength の差分が、基準ペア return の H1 next-bar 予測力で **Wilson 95% lower bound > 0.51** を満たす。

**H2 (α residual)**: α_tij = log(X_tij) − [log(V_i) − log(V_j)] は次バー return に対し MR 方向の predictive power を持つ。
判定: 5 ペア × 1 horizon (H1 next-bar) で Bonferroni m=5、p < 0.01 で全ペア有意なら ACCEPT。1〜4 ペアのみ有意なら NEEDS_MORE_EVIDENCE（次の 12 ヶ月で再計測）。0 ペアなら REJECT（V_ti のみ filter feature として保留）。

**H3 (τ_exec jitter)**: lookahead を含む戦略は τ_exec を [0, bar_duration] uniform でランダム化すると BT PF が 0.95-1.05 の閾値内に落ちる。
判定: `squeeze_release_momentum` を control として PF が jitter ON で **少なくとも 0.30 低下** することを assert。

**ロードマップ前進条件**: H2 採択時のみ Wave 5 で α reversion MR 戦略 spec 起票へ進む。

## 2. 対象データ・分離

| Bucket | フィルタ | 用途 |
|---|---|---|
| OHLCV (5 pair, H1) | USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY 同時アライン | V_ti / α 計算入力 |
| α residual time series | 上記から派生 | shadow 観測対象 |
| LIVE 戦略 entry log | `is_shadow=0 AND oanda_trade_id != ''` | α residual と signal 発火の方向一致 audit |
| BT (squeeze_release_momentum) | 既存 backtest_engine | τ_exec jitter control test |

- **ローカル DB は使わない**（`feedback_check_orphan_local_app`）→ Render API + 既存 OHLCV キャッシュ
- **XAU 除外**（`feedback_exclude_xau`）
- **Live/Shadow 厳格分離**（`feedback_live_shadow_separation`）

## 3. 統計条件 (pre-registered LOCK)

判定基準は本ファイル commit 時点で **凍結**。post-hoc 変更禁止。

### 3.1 V_ti（H1 検証用）
| 指標 | ACCEPT | NEEDS_MORE | REJECT |
|---|---|---|---|
| MLE 解の condition number | < 1e6 | 1e6-1e9 | > 1e9 (numerical instability) |
| basket_strength との相関 | 0.7-0.99 | (out of band) | < 0.7 or > 0.99 (= identity) |
| H1 next-bar return predictive Wilson lower | ≥ 0.51 | 0.49-0.51 | < 0.49 |
| N (12 ヶ月 H1) | ≥ 4000 | 2000-4000 | < 2000 |

### 3.2 α residual（H2 検証用、これが本命）
| 指標 | ACCEPT | NEEDS_MORE | REJECT |
|---|---|---|---|
| 全 5 ペア Bonferroni p (m=5) | < 0.01 全ペア | 1-4 ペアのみ | 0 ペア |
| α magnitude vs spread の相関 | < 0.30 (α が spread でないこと) | 0.30-0.50 | > 0.50 |
| α 自己相関 (lag 1, H1) | < 0.50 (mean reverting 系) | 0.50-0.70 | > 0.70 (trending 系で MR 仮説不成立) |
| LIVE 戦略 entry 時の α 偏り (Kruskal-Wallis) | p < 0.05 | p < 0.10 | p ≥ 0.10 |

### 3.3 τ_exec jitter (H3)
| 指標 | ACCEPT (lookahead 検出) | NEEDS_MORE | REJECT |
|---|---|---|---|
| `squeeze_release_momentum` PF 低下 (jitter ON vs OFF) | ≥ 0.30 | 0.10-0.30 | < 0.10 |
| Closed-bar 健全戦略 (`asia_range_fade_v1`) PF 低下 | < 0.05 | 0.05-0.10 | ≥ 0.10 (false positive) |

**最終判定**: 各 H ごとに独立判定。H1/H2 が REJECT でも H3 は独立に採否決定。

## 4. 実装

### 4.1 `modules/fx_graph.py`（新規）

```python
"""FX currency network graph features (Hong & Klabjan 2025 arXiv 2508.14784 inspired).

Pure data layer. No LIVE intervention.
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

CURRENCIES_5PAIR = ["USD", "EUR", "GBP", "JPY"]  # 4 currencies covered by 5 pairs

# Pair → (base, quote) for 5-pair universe.
# Reuse modules/currency_strength.py:24 PAIR_MAP (do NOT duplicate definitions).

def compute_currency_value(
    log_prices: pd.DataFrame,
) -> pd.DataFrame:
    """Compute MLE currency value V_ti per Hong & Klabjan Eqs. 8-9.

    Solves: log(X_tij) = log(V_i) - log(V_j) for all pairs (i,j) in L_t,
    subject to (1/|C|) Σ_i log(V_ti) = 0 (normalization).

    For 4 currencies × 5 pairs: 5 equations, 4 unknowns + 1 constraint.
    Resulting 6×4 system solved via least-squares with normalization row.

    Args:
        log_prices: DataFrame indexed by timestamp, columns = pair codes
                    (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY).
                    Values = log(close_price).

    Returns:
        DataFrame indexed by timestamp, columns = currency codes (USD, EUR, GBP, JPY).
        Values = log(V_ti). Σ across columns = 0 per row (normalization).
    """
    # Implementation: build A matrix from PAIR_MAP, b = log_prices row, solve via np.linalg.lstsq
    # See arXiv 2508.14784 §4.1 for derivation
    raise NotImplementedError


def triangular_residual(
    log_prices: pd.DataFrame,
    log_currency_value: pd.DataFrame,
) -> pd.DataFrame:
    """Compute α_tij = log(X_tij) - [log(V_i) - log(V_j)] per pair.

    Args:
        log_prices: same as compute_currency_value input.
        log_currency_value: output of compute_currency_value.

    Returns:
        DataFrame with same index as log_prices, columns = pair codes.
        Values = α residual (basket-implied deviation in log space).
    """
    raise NotImplementedError
```

### 4.2 `modules/currency_strength.py`（拡張、後方互換維持）

既存 `basket_strength()` は **一切変更しない**（後方互換）。以下を末尾に追加:

```python
def mle_currency_value(log_prices: pd.DataFrame) -> pd.DataFrame:
    """MLE-based currency value (Hong & Klabjan Eqs. 8-9). Wraps fx_graph.compute_currency_value.

    Use this alongside basket_strength() to compare empirical vs theoretical strength.
    """
    from modules.fx_graph import compute_currency_value
    return compute_currency_value(log_prices)
```

### 4.3 `modules/backtest_engine.py`（拡張、慎重に）

新フラグ `--exec-lag-jitter <float>` を追加（default 0.0 = 既存挙動）:

- `0.0`: 既存挙動。closed-bar gate / intrabar 設定に従う
- `(0, 1]`: 各シグナル発火時、執行価格を **bar 内 uniform random offset** で取得
  - 具体実装: signal が bar t の close で発火した場合、execution price を `entry = open + (close - open) * U(0, jitter)` で再計算（U=uniform random）
  - random seed は固定（reproducibility）

**既存 closed-bar gate / shadow audit ロジックには介入しない**。jitter は新たな読み取り専用 layer として追加。

### 4.4 `tests/test_fx_graph.py`（新規、TDD レッド先行）

3 ケース全 RED で書く:

```python
def test_currency_value_recovers_synthetic_truth():
    """既知 V を生成 → ペア合成 → compute_currency_value が誤差 1e-9 以内で復元."""
    np.random.seed(42)
    true_log_v = pd.DataFrame({
        "USD": [0.0], "EUR": [0.1], "GBP": [0.2], "JPY": [-0.3]
    })  # Σ = 0
    # Synthesize: log(USD_JPY) = log(V_USD) - log(V_JPY) = 0 - (-0.3) = 0.3
    log_prices = pd.DataFrame({
        "USD_JPY": [true_log_v.USD[0] - true_log_v.JPY[0]],
        "EUR_USD": [true_log_v.EUR[0] - true_log_v.USD[0]],
        "GBP_USD": [true_log_v.GBP[0] - true_log_v.USD[0]],
        "EUR_JPY": [true_log_v.EUR[0] - true_log_v.JPY[0]],
        "GBP_JPY": [true_log_v.GBP[0] - true_log_v.JPY[0]],
    })
    result = compute_currency_value(log_prices)
    assert np.allclose(result.values, true_log_v.values, atol=1e-9)


def test_triangular_residual_zero_for_no_arb_data():
    """No-arb 合成データ (V から生成) で α が常にゼロ."""
    # ... build log_prices from a known V ...
    log_v = compute_currency_value(log_prices)
    alpha = triangular_residual(log_prices, log_v)
    assert np.allclose(alpha.values, 0.0, atol=1e-9)


def test_exec_lag_jitter_breaks_lookahead_strategy():
    """squeeze_release_momentum BT で jitter ON 時に PF が 0.30 以上低下."""
    pf_off = run_bt("squeeze_release_momentum", exec_lag_jitter=0.0)
    pf_on = run_bt("squeeze_release_momentum", exec_lag_jitter=0.5)
    assert (pf_off - pf_on) >= 0.30
    # Counter-test: closed-bar healthy strategy unaffected
    pf_off_h = run_bt("asia_range_fade_v1", exec_lag_jitter=0.0)
    pf_on_h = run_bt("asia_range_fade_v1", exec_lag_jitter=0.5)
    assert abs(pf_off_h - pf_on_h) < 0.05
```

### 4.5 `tools/fx_nexus_shadow_audit.py`（新規）

```
usage:
  python3 tools/fx_nexus_shadow_audit.py \
    --pairs USD_JPY,EUR_USD,GBP_USD,EUR_JPY,GBP_JPY \
    --start 2025-05-01 --end 2026-05-01 \
    --horizon H1 \
    --output knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md
```

機能:
1. OHLCV (H1, 5 pair) を Render API or 既存 cache から取得（XAU 除外）
2. log_prices DataFrame 構築 → compute_currency_value → triangular_residual
3. 統計指標を §3.1 / §3.2 の表に従って算出（Wilson, Bonferroni）
4. LIVE 戦略 entry log を Render API `/api/demo/trades` から取得（`is_shadow=0` のみ）
5. 各 entry 時刻の α 値分布を戦略 × 方向別に集計、Kruskal-Wallis 検定
6. 出力 markdown に決定基準 vs 実測値、判定（ACCEPT / NEEDS_MORE / REJECT）を記載

### 4.6 KB 更新

- `knowledge-base/wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md`（**本タスク commit と同一コミット**）に §3 の判定基準を LOCK
- `knowledge-base/wiki/strategies/fx_nexus_alpha_residual.md`（shadow 観測対象として、まだ live signal 化されていないことを明示）
- `wiki/changelog.md` に entry 追加

## 5. 受け入れ条件 (acceptance)

1. `pytest tests/test_fx_graph.py -v` で 3 ケース全 GREEN
2. `python3 tools/fx_nexus_shadow_audit.py --start 2025-05-01 --end 2026-05-01` 実行が成功し、output markdown が生成される
3. output markdown に H1 / H2 / H3 各々の判定（ACCEPT / NEEDS_MORE / REJECT）が記載される
4. `wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md` が pre-reg LOCK 文書として commit に含まれている
5. Render 本番には **一切デプロイしない**（feature branch のみ、PR は open するが merge は次セッションで判断）
6. 既存 BT / LIVE 経路に regression がないこと（`pytest tests/ -v` で全テスト GREEN）

## 6. 禁止事項

- LIVE 戦略のロジック変更は禁止（filter 追加・パラメータ変更を含む）
- `modules/currency_strength.py:24-52` の `basket_strength()` シグネチャ変更禁止
- shadow audit 結果を見て §3 の判定基準を後付けで変える（post-hoc selection）禁止
- main ブランチへの直接 push 禁止（feature branch + PR）
- α residual を新戦略の signal として live 化することは本タスクのスコープ外

## 7. 完了報告フォーマット

PR description に以下を含める:
- 実装ファイル一覧と各ファイルの行数
- `tests/test_fx_graph.py` の 3 ケース PASS スクリーンショット
- shadow audit output markdown の判定サマリ（H1 / H2 / H3 各 ACCEPT/NEEDS_MORE/REJECT）
- 既存 pytest 全 GREEN の確認
- 次セッションへの引き継ぎ事項（H2 ACCEPT なら Wave 5 spec 起票候補、REJECT なら α は filter feature 保留）

## 8. 関連リソース

- 参考論文: [arXiv 2508.14784](https://arxiv.org/abs/2508.14784)
- Plan: `/Users/jg-n-012/.claude/plans/fx-nexus-fx-sunny-wombat.md`
- 既存 currency_strength.py: `modules/currency_strength.py` (52 行)
- 既存 stats_utils.py の Wilson/Bonferroni: `modules/stats_utils.py`
- W4-EDA Tier 1 監査（並列で進行中、TIMING_BROKEN 自動判定として H3 は寄与）


## Result (2026-05-04T09:32:59Z)

exit=0 · 519s

```
実装・検証・push まで完了しました。PR 作成だけは GitHub API が `403 Resource not accessible by personal access token` で拒否したため未作成です。branch は push 済みなので、GitHub の PR 作成画面から開けます。

Branch: `feature/fx-nexus-step1-shadow-audit`  
Commit: `3443cf2 Add FX Nexus graph shadow audit`

主な追加:
- [modules/fx_graph.py](/data/repo/fx-ai-trader/modules/fx_graph.py): MLE `V_ti` と triangular residual `alpha`
- [tools/fx_nexus_shadow_audit.py](/data/repo/fx-ai-trader/tools/fx_nexus_shadow_audit.py): H1/H2/H3 audit markdown 生成
- [tests/test_fx_graph.py](/data/repo/fx-ai-trader/tests/test_fx_graph.py): 3 ケース追加
- [knowledge-base/wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md): pre-reg LOCK
- [knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md): 監査出力

検証:
- `pytest tests/test_fx_graph.py -v`: `3 passed`
- `python3 tools/fx_nexus_shadow_audit.py ...`: 成功、audit markdown 生成
- `pytest tests/ -v`: `933 passed, 1 xfailed`

監査 verdict:
- H1 `V_ti`: `NEEDS_MORE`
- H2 `alpha residual`: `NEEDS_MORE`。有意ペアは 2/5 なので Wave 5 spec 起票はまだ不可。
- H3 `exec jitter`: `NEEDS_MORE`。365d 15m BT データが現環境で取得できず、SRM/Asia control は N=0。

Render 本番デプロイはしていません。`basket_strength()` 本体と LIVE 戦略ロジックも変更していません。
```
