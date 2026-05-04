# Edge Design Audit (W4-EDA): Per-Strategy Design Forensics

**Date**: 2026-05-04
**Author**: 司令塔 (Claude) ／ 実働 (Codex)
**Wave alignment**: W4 (Wave 4) preparatory — 全戦略の設計品質ベースライン化

## 1. Background & Premise

Wave 1〜3 の Codex BT 監査で繰り返し観察された失敗パターンは、**思想（edge thesis）の誤りではなく、エントリータイミング設計の欠陥**であることが多い。代表例:

- **MA filter breaks MR** (memory: `feedback_ma_filter_breaks_mr.md`) — bb_rsi_reversion 等の MR 戦略に H1 EMA200 整合フィルタを追加すると LIVE エッジが BT で消滅
- **HMM gate same trap** (memory: `feedback_hmm_gate_same_trap.md`) — regime gate を素直に適用すると edge 消滅 (USDJPY TF +478p→-4p)
- **R2 14-cell pair_demoted LOCK** (May 3) — セルレベルの demote 判定が cohort 時系列で破綻
- **rsk bar-close gate 未修正** (memory: `project_rsk_gbpjpy_bar_close_gate_pending.md`) — per-bar dedup 欠落で 76 件 runaway / -813.7p
- **S3 COT inversion clause 誤り** (memory: `project_s3_cot_literal_no_inversion.md`) — 公開実証と逆方向で BT 12.3 年棄却

これらはすべて **trigger / filter / timing 設計の誤適用** であり、思想自体（MR / momentum / positioning / news）は否定されていない。

### 核心仮説

> **大半の demoted/underperforming 戦略は「思想は正、設計が誤」に分類される。エントリータイミング設計を再設計すれば復活する candidate が相当数存在する。**

本監査はこの仮説を全戦略で検証し、再設計対象を特定する。

## 2. Scope

- **対象**: tier-master.md 全カテゴリ（73 cell / 85 strategy file）
  - 1 ELITE + 9 PAIR_PROMOTED + 31 Phase0 Shadow Gate + 22 FORCE_DEMOTED + 10 SCALP_SENTINEL
- **除外**: なし（demoted も再設計 candidate として全件対象）
- **粒度**: cell 単位（pair × strategy × timeframe × variant）で監査、cell 間共通の設計欠陥は親 strategy にロールアップ

## 3. Audit Framework: 8軸チェックリスト

各 cell について Codex に以下を診断させる。

| # | 軸 | 問い | 出力形式 |
|---|---|---|---|
| 1 | **思想 articulation** | 暗黙の仮説は何か（MR/momentum/news/seasonality/positioning…）。コード内に明示されているか | 1-2行のテーゼ文 |
| 2 | **trigger 整合** | エントリー条件は思想を数学的に捕捉しているか（MR thesis なのに momentum proxy で引いていないか） | PASS / MISMATCH + 数式比較 |
| 3 | **timing window** | bar-close vs intrabar、signal→execution latency、look-ahead bias | OK / LATE / LOOKAHEAD |
| 4 | **filter coherence** | フィルタが思想を強化/破壊しているか | NEUTRAL / STRENGTHENS / BREAKS |
| 5 | **stop/TP geometry** | 思想と R:R 構造の整合（MR=wide stop / momentum=asymm / breakout=trailing） | ALIGNED / MISALIGNED |
| 6 | **pair-regime fit** | 対象ペアのレジーム特性と思想が合うか | FIT / FORCED |
| 7 | **empirical evidence** | Wilson CI lower bound / PF / WF folds / Bonferroni-adjusted p / Kelly fraction | 数値テーブル |
| 8 | **failure mode 診断 (demoted のみ)** | 1-7 のどこで思想が壊れたか、再設計案 | trigger 修正 / filter 削除 / timing 変更 / 棄却 |

### Verdict 分類

各 cell に以下のいずれかを付与:
- `THESIS_VALID_DESIGN_VALID` — 何もしない（既稼働 LIVE が該当）
- `THESIS_VALID_DESIGN_BROKEN` — **再設計対象**（軸 2-5 で MISMATCH/BREAKS/MISALIGNED 検出）
- `THESIS_VALID_TIMING_BROKEN` — タイミングのみ修正で復活見込み（軸 3 のみ問題）
- `THESIS_VALID_INSUFFICIENT_EVIDENCE` — 思想 OK、設計 OK、ただし軸 7 で統計不足
- `THESIS_INVALID` — 思想自体が否定された（公開実証/12y BT で逆方向 等）。catalog §B-2 academic only へ

### 再設計推奨度

`S/A/B/C/D` を付与（demoted は S/A 優先で復活 candidate プール化）:
- **S**: 修正一点で即 Shadow 復帰可能（例: filter 1 行削除）
- **A**: trigger or timing 1 系統の再設計で復活見込み
- **B**: 複数軸の再設計が必要
- **C**: 大幅再設計（実質新戦略）
- **D**: 棄却（思想自体が崩壊）

## 4. Output Artifacts

### 4.1 Per-cell audit file

`audits/edge_design/<strategy>__<cell>.md`:

```markdown
---
strategy: <name>
cell: <pair>_<timeframe>_<variant>
tier: PAIR_PROMOTED | FORCE_DEMOTED | …
audited_at: 2026-05-XX
auditor: codex
---

## Thesis (Axis 1)
…

## 8-Axis Diagnosis
| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 | MISMATCH | trigger: RSI<30 ∧ price>EMA200 — MR thesis と momentum filter の衝突 |
…

## Verdict
THESIS_VALID_DESIGN_BROKEN

## Redesign Proposal (S/A/B/C/D = A)
- Remove H1 EMA200 alignment filter (Axis 4)
- Keep RSI<30 trigger (Axis 2)
- Expected effect: BT Kelly 0 → 0.43 復元 (memory bb_rsi_reversion 同等)

## Empirical Evidence (Axis 7)
| Metric | Original | Proposed Redesign |
|--------|----------|-------------------|
| PF     | 0.91     | (TBD: BT 必要) |
…
```

### 4.2 Roll-up

`audits/edge_design/_INDEX.md` — 全 cell の verdict と再設計推奨度を一覧化、S/A 優先度でソート。

### 4.3 Redesign queue

`audits/edge_design/_REDESIGN_QUEUE.md` — Wave 4 で取り組む再設計対象を順位付け（recommendation S → A → B、tier 高い順、historical edge 大きい順）。

## 5. Process: Per-Cell Codex Dispatch

### 5.1 Single-cell Codex task template

各 cell について以下のテンプレートで Codex タスクを発行:

```
[W4-EDA] Edge Design Audit — <strategy>__<cell>

You are auditing ONE strategy cell against the 8-axis design framework defined in
docs/superpowers/specs/2026-05-04-edge-design-audit-design.md.

Target cell:
- strategy file: strategies/<category>/<strategy>.py
- cell: <pair>_<tf>_<variant>
- current tier: <tier>
- historical metrics (from tier-master/audit DB): <inline numbers>

Task:
1. Read the strategy code. Articulate the thesis (Axis 1) explicitly.
2. Walk through axes 2-7 with code references and numerical evidence.
3. If demoted/underperforming, apply Axis 8 (failure mode diagnosis).
4. Issue a Verdict and a Redesign Recommendation (S/A/B/C/D).
5. If recommending S/A, write a concrete redesign proposal (specific lines to
   change, formulas to replace, filters to drop).
6. Output to audits/edge_design/<strategy>__<cell>.md following the template
   in §4.1 of the spec.

Constraints:
- Single cell only. Do NOT batch multiple cells per task.
- Do NOT run BT. Statistical evidence comes from existing audit DB / tier-master.
- Cite code with file:line references.
- If thesis cannot be inferred from code, mark Axis 1 as AMBIGUOUS and stop —
  do not invent a thesis post-hoc.

Reference memory:
- feedback_ma_filter_breaks_mr.md (Axis 4 example)
- feedback_hmm_gate_same_trap.md (Axis 4 example)
- feedback_partial_quant_trap.md (Axis 7 standard)
- feedback_label_empirical_audit.md (Axis 7 evidence requirement)
```

### 5.2 Sequencing

**並列ではなく逐次** で実行する。理由:
- 並列実行は中途半端な結果を返す（user directive）
- 逐次なら早期 cell の発見を後続 cell の audit に反映できる（共通失敗パターンの抽出）
- 司令塔（Claude）が各結果を読んで次タスクの prompt を chein refinement できる

### 5.3 Priority order

1. **Tier 1 (LIVE 系 / 即影響)**: 1 ELITE + 9 PAIR_PROMOTED = 10 cell
   - 設計欠陥が即 PnL 毀損 → 最優先で防御的監査
2. **Tier 2 (Shadow / 昇格候補)**: 31 Phase0 Shadow Gate
   - 昇格前に設計欠陥を潰す ROI 最大
3. **Tier 3 (FORCE_DEMOTED / 復活候補)**: 22 FORCE_DEMOTED
   - 「思想は正、設計が誤」仮説の本命検証群
4. **Tier 4 (SCALP_SENTINEL)**: 10 SCALP_SENTINEL
   - 既に sentinel 化されているので最後

各 Tier 完了時に司令塔が共通失敗パターンを抽出し、次 Tier の audit prompt にフィードバック。

## 6. Stop Conditions

- **Tier 1 完了時**: もし LIVE 系で `THESIS_VALID_DESIGN_BROKEN` が 3 件以上出た場合、Tier 2-4 を一旦止めて user に報告 → LIVE 防御 patch を Wave 4 entry の前に投入するか判断
- **思想無効率が高い場合** (`THESIS_INVALID` > 30%): 全体仮説を見直し、user に re-brainstorm を依頼

## 7. Out of Scope

- BT 再実行（既存 audit DB / tier-master の値を使う）
- 実装変更（本監査は **設計レビューのみ**、修正は Wave 4 で別タスク）
- 新規 edge 探索（既存 cell の再設計のみ）

## 8. Success Criteria

- 全 73 cell が 8軸チェックを通過し、verdict が付与されている
- `_INDEX.md` で再設計優先度ランキングが完成
- `_REDESIGN_QUEUE.md` で Wave 4 取り組み順序が決定
- Tier 1 (LIVE) で発見された欠陥は防御 patch として即時 PR 化判断ができる状態

## 9. Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Codex が思想を post-hoc rationalize する（Axis 1 hallucination） | Axis 1 が AMBIGUOUS なら停止のルールを prompt に固定 |
| Codex schema hallucination (memory) | tier-master 数値は prompt に inline 直貼り |
| Codex mock-only test trap (memory) | 本監査は BT 不要なので影響軽減、ただし Axis 7 数値は実 DB 由来であることを明記 |
| 並列化誘惑 | 逐次フローを spec で明文化（§5.2） |
| LIVE 防御の遅延 | Tier 1 完了時の早期報告ゲート（§6） |
