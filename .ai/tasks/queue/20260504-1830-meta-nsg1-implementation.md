---
id: 20260504-1830-meta-nsg1-implementation
title: "[META] NSG-1 (Neighborhood Stability Gate) 実装と W3-3 S4 retrospective 検証"
owner: codex
status: queued
priority: P1
created_at: 2026-05-04T18:30:00+0900
roadmap_gate: meta-discipline (Top 4 of post-Qiita-article gap analysis)
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md
  - .ai/runs/20260503-173011-20260503-1715-w3-3-rerun-s4-connors-raschke-80-20-bt/final.md
  - tools/bt/s4_connors_raschke.py
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md
---

# 0. Why this task

司令塔 Claude が Qiita 記事 (https://qiita.com/tikeda123/items/e777dcadbc850c357419) 由来のギャップ分析で抽出した 5 提案のうち Top 4。**parameter neighborhood stability** をゲート化することで、W3-3 S4 で経験した "primary fail / grid 上 6 B 帯 cell" 型 post-hoc selection trap を構造的に防ぐ。

詳細仕様は `knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md` (NSG-1 Protocol) に確定済み。本タスクはその spec の実装+ retrospective 検証。

# 1. Inputs (Codex が読むべきもの)

1. **Spec** (必読): `knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md`
   - §2 metrics A/B/C の定義
   - §3 retrospective test cases (A/B/C)
   - §5 acceptance criteria
2. **Existing gate code (パターン参照)**: `modules/confidence_q4_gate.py`, `modules/prime_gate.py` — pure-classifier style を踏襲する
3. **W3-3 S4 grid evidence**: `.ai/runs/20260503-173011-20260503-1715-w3-3-rerun-s4-connors-raschke-80-20-bt/final.md`
   - 27 cell grid (rsi=10, exit=50_trailing, time=NY_close_21UTC が primary)
   - W3-3 BT は INTERVENTION_LIST 不足で BLOCKED だが、その前段の Scenario C grid (B 帯 6 cell)は別ファイルにあるはず: `knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.*` を確認のこと
4. **W3-2 S2 turtle evidence** (PASS が出るべき対照): tier-master.md の turtle_s2 セル + .ai/runs/ 配下の最新 W3-2 BT 結果
5. **Tier 1 LIVE 1 戦略**: doji_breakout か ema200_trend_reversal の最新 BT grid (なければ tier-master.md と最新 cell stats から再構築)

# 2. Scope

Codex may change:

- `tools/audit/neighborhood_stability.py` (新規)
- `tests/test_neighborhood_stability.py` (新規)
- `tools/audit/gate0_evaluator.py` (なければ新規、あれば `--require-nsg1` flag を追加)
- `knowledge-base/raw/audits/nsg1-retrospective-w3-3-s4-2026-05-04.md` (新規 retrospective レポート)
- `knowledge-base/raw/audits/nsg1-retrospective-summary-2026-05-04.json` (新規、機械可読サマリ)
- `knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md` の **§3 末尾の "NSG-1 retrospective summary table" のみ** 追記可。それ以外の §は claude 編集領域。

Codex must not change:

- production secrets / .env / render.yaml
- 既存の `modules/confidence_q4_gate.py` `modules/prime_gate.py` `modules/spread_gate.py` (pattern 参照のみ)
- 既存戦略コード `strategies/**`
- 既存 BT runner `tools/bt/s4_connors_raschke.py` (読み取りのみ)

# 3. Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md` (本タスクの spec)
- `knowledge-base/wiki/lessons/feedback_partial_quant_trap.md` (PF/Wilson/Bonf/Kelly 揃え原則)
- `knowledge-base/wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md` (gate 過剰適用防止)

# 4. Implementation contract

## 4.1 `tools/audit/neighborhood_stability.py`

Pure function module. **No I/O, no DB call, no global state**。

```python
@dataclass(frozen=True)
class NeighborhoodVerdict:
    median_lift: float       # NSG-1.A
    sign_agreement: float    # NSG-1.B
    variance_cv: float       # NSG-1.C
    a_pass: bool
    b_pass: bool
    c_pass: bool
    pass_overall: bool       # AND of A/B/C
    n_neighbors: int         # 実際に評価した近傍 cell 数
    skipped_axes: list[str]  # step 数 < 3 で A 適用免除した軸
    notes: list[str]

def compute_neighborhood_stability(
    grid_results: pd.DataFrame,
    primary_cell: Mapping[str, Any],
    bev_wr: float,
    *,
    axes: Sequence[str] | None = None,        # None なら primary_cell.keys() を使う
    max_step: int = 1,
    a_threshold: float = 0.80,
    b_threshold: float = 0.50,
    c_threshold: float = 1.00,
) -> NeighborhoodVerdict: ...
```

Required behaviors:

- `grid_results` は最低 columns: param 軸 + `["N", "wilson_lo", "kelly"]`. wilson_lo は 0..1 の実数。
- primary_cell が grid に無ければ `KeyError`。
- 1-step 近傍の抽出は各軸独立 (Hamming distance 1)。
- 軸の grid step が < 3 (端点しかないケース) は NSG-1.A 評価から除外し `skipped_axes` に記録。
- N < 5 の近傍 cell は無視 (信頼性低)。残った近傍が 0 になったら `notes` に "neighbor_pool_empty" を追記し `pass_overall=False`。
- `kelly = 0` の primary cell は variance_cv 計算で 0 除算回避: `c_pass = stdev(kelly_neighbors) <= max(|kelly_primary|, 0.01)` の運用。

## 4.2 Tests `tests/test_neighborhood_stability.py`

最低 6 テスト:

1. **smooth surface PASS**: synthetic grid で primary を含む滑らかな丘 (Wilson_lo が ±1 step で 95% 維持) → A/B/C すべて PASS。
2. **single spike FAIL (A)**: primary=0.60、近傍=0.30 → A FAIL (median_lift < 0.80)。
3. **half-flip FAIL (B)**: 近傍中半数が BEV_WR 未満 → B FAIL。
4. **kelly variance FAIL (C)**: primary=0.05 だが近傍 stdev=0.08 → C FAIL。
5. **boundary cell handling**: grid 端の cell でも片側 neighbor のみで評価できること (KeyError 出ない)。
6. **small N exclusion**: 近傍に N=3 cell があれば pool から除外され notes に記録されること。

## 4.3 Gate harness integration `tools/audit/gate0_evaluator.py`

- 既存ファイルがあれば `--require-nsg1` flag 追加、なければ新規でも可 (新規時はスケルトンのみ、既存 verdict ロジックの再現は本タスク対象外)。
- 出力 JSON に `nsg1: {a_pass, b_pass, c_pass, pass_overall, ...}` を必ず含める。

## 4.4 Retrospective レポート

`knowledge-base/raw/audits/nsg1-retrospective-w3-3-s4-2026-05-04.md` に以下:

- Test Case A: W3-3 S4 27-cell grid (primary fail) → expected: NSG-1 が独立に FAIL を出す。実測値表 (median_lift, sign_agreement, variance_cv) を記載。**入力 grid データが取れない場合 (BLOCKED 由来)** は、tier-master.md にある最新の S4 cell stats から **recoverable な subset** で評価し、その旨を limitation として明記する。
- Test Case B: W3-2 S2 turtle PASS confirmation。
- Test Case C: doji_breakout 等 1 戦略の confirmation。
- まとめ表を `knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md` §3 末尾に Markdown table で append (新規 H2 を追加せず、既存 §3 の中)。

# 5. Acceptance Criteria

- [ ] `tools/audit/neighborhood_stability.py` 存在、ruff / mypy clean
- [ ] `python3 -m pytest tests/test_neighborhood_stability.py -v` で 6 テスト以上 PASS
- [ ] `tools/audit/gate0_evaluator.py --require-nsg1 --help` が成立 (CLI 動作確認のみ。実評価は不要)
- [ ] retrospective MD + JSON レポート生成
- [ ] spec 文書 §3 末尾のサマリ table が追記されている
- [ ] 各 retrospective ケースで判定が spec §3 の期待 (A FAIL, B PASS, C PASS) と整合。**1 つでも乖離した場合は spec §3.4 に従い 1 回だけ閾値 sweep**、結果を retrospective report に明記
- [ ] Run report 標準書式で `.ai/runs/<timestamp>-meta-nsg1-implementation/final.md` に書き出し

# 6. Verification Commands

```bash
python3 -m pytest tests/test_neighborhood_stability.py -v
python3 tools/audit/gate0_evaluator.py --require-nsg1 --help
ruff check tools/audit/neighborhood_stability.py
mypy tools/audit/neighborhood_stability.py
ls knowledge-base/raw/audits/nsg1-retrospective-w3-3-s4-2026-05-04.md
ls knowledge-base/raw/audits/nsg1-retrospective-summary-2026-05-04.json
```

# 7. Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.

**重要 (mock-only test trap 回避)**: NSG-1 metric は pure function なので unit test は synthetic grid で OK だが、**retrospective ケースは必ず実 BT 結果 / 実 cell stats を入力にすること**。CSV/parquet/JSON の実データが見つからない場合は、tier-master.md にある cell stats から最低限の subset を再構築して評価する。完全 mock の grid だけで retrospective を済ませてはならない。

実装手順:

1. spec を読む。retrospective に使える W3-3 S4 grid 実データの所在を `knowledge-base/raw/bt-results/`, `.ai/runs/`, `knowledge-base/wiki/learning/` から特定。
2. 見つからなかった場合は tier-master.md の S4 cell から subset を再構築する方針で進めるが、**"完全に取れない" を理由に retrospective を skip するのは不可**。最低 1 戦略 (Test Case B か C) で実データ retrospective を完遂すること。
3. RED first: テストを先に書いて FAIL することを確認 → GREEN へ。
4. ruff / mypy / pytest が全 PASS した状態で commit (1 commit でも複数でも可、ただし retrospective レポートは別 commit を推奨)。
5. 最終レポート `final.md` に: status, files changed, verification 出力 summary, retrospective verdict 表, remaining risks, next recommended task。

In the final report, include status, files changed, verification output summary, retrospective verdict table, remaining risks, and next recommended task.
