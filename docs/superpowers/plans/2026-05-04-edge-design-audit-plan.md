# W4-EDA: Edge Design Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tier-master 全戦略の設計（特にエントリータイミング設計）を Codex に逐次監査させ、再設計対象を S/A/B/C/D で優先順位化する。

**Architecture:** 司令塔（Claude）が Codex タスクを 1 戦略ずつキュー投入 → Codex worker (fx-codex-runner) が `audits/edge_design/<strategy>.md` に単独出力 → 司令塔が確認後に次戦略を投入。並列禁止。Tier 境界に gate (`THESIS_VALID_DESIGN_BROKEN` 多発時の停止条件) を設置。

**Tech Stack:** Codex queue (`.ai/tasks/queue/*.md`) / fx-run-codex skill / 既存 audit DB (sqlite) / tier-master.md

**核心設計判断（spec §1）:** 思想（edge thesis）は前提として正、エントリータイミング設計の欠陥が大半を占めるという仮説で監査する。よって `THESIS_INVALID` は最終手段、優先は trigger / filter / timing / stop の再設計。

**監査単位:** **strategy file 単位（= 1 edge = 1 思想 = 1 Codex task = 1 output file）**。strategy が複数 pair に展開されている場合は単一監査内で per-pair Axis 6 を併記。tier-master の cell 数（121 entries 含重複）ではなく **distinct strategy file** を単位とする。

---

## File Structure

| Path | Responsibility |
|---|---|
| `audits/edge_design/_INVENTORY.md` | 監査対象 strategy 一覧（Tier 別、優先度順） |
| `audits/edge_design/_PROMPT_TEMPLATE.md` | Codex に渡す per-strategy 監査 prompt のテンプレート |
| `audits/edge_design/_INDEX.md` | 全監査結果のロールアップ（verdict + 再設計推奨度） |
| `audits/edge_design/_REDESIGN_QUEUE.md` | S/A 推奨度の戦略を Wave 4 取り組み順にランク化 |
| `audits/edge_design/_TIER1_GATE.md` | Tier 1 完了時の gate 判定記録 |
| `audits/edge_design/<strategy>.md` | 各戦略の 8 軸監査結果（spec §4.1 テンプレ） |
| `tools/build_edge_audit_inventory.py` | tier-master.json から `_INVENTORY.md` を生成 |
| `tools/edge_audit_dispatch.py` | 1 戦略分の Codex task md を `.ai/tasks/queue/` に書き出すヘルパ |
| `tests/test_edge_audit_inventory.py` | inventory 生成スクリプトのユニットテスト |
| `tests/test_edge_audit_dispatch.py` | dispatch ヘルパのユニットテスト |

---

## Task 1: Pre-flight — 戦略インベントリ自動生成スクリプト

**Files:**
- Create: `tools/build_edge_audit_inventory.py`, `tests/test_edge_audit_inventory.py`
- Source: `knowledge-base/wiki/tier-master.json`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_edge_audit_inventory.py
import json
import subprocess
import sys
from pathlib import Path


def test_inventory_groups_by_tier(tmp_path):
    tier_master = {
        "elite_live": [{"strategy": "trendline_sweep"}],
        "pair_promoted": [
            {"strategy": "doji_breakout", "pair": "GBP_USD"},
            {"strategy": "doji_breakout", "pair": "USD_JPY"},
        ],
        "force_demoted": [{"strategy": "ema_cross"}],
        "scalp_sentinel": [{"strategy": "bb_rsi_reversion"}],
        "phase0_shadow": [{"strategy": "adx_trend_continuation"}],
    }
    src = tmp_path / "tier-master.json"
    src.write_text(json.dumps(tier_master))
    out = tmp_path / "_INVENTORY.md"

    result = subprocess.run(
        [sys.executable, "tools/build_edge_audit_inventory.py",
         "--source", str(src), "--out", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    for tier in ["Tier 1 (LIVE)", "Tier 2 (Shadow)", "Tier 3 (FORCE_DEMOTED)", "Tier 4 (SCALP_SENTINEL)"]:
        assert tier in body
    assert body.count("doji_breakout") == 1
    assert "GBP_USD, USD_JPY" in body
    assert body.index("Tier 1") < body.index("Tier 2") < body.index("Tier 3") < body.index("Tier 4")
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_edge_audit_inventory.py -v
```

- [ ] **Step 3: Implement inventory builder**

```python
# tools/build_edge_audit_inventory.py
"""Generate audits/edge_design/_INVENTORY.md from tier-master.json.

Tier mapping:
  Tier 1 = elite_live + pair_promoted   (LIVE, 即影響)
  Tier 2 = phase0_shadow                (昇格候補)
  Tier 3 = force_demoted                (思想は正・設計が誤 仮説の本命検証)
  Tier 4 = scalp_sentinel
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

TIER_MAP = [
    ("Tier 1 (LIVE)", ["elite_live", "pair_promoted"]),
    ("Tier 2 (Shadow)", ["phase0_shadow"]),
    ("Tier 3 (FORCE_DEMOTED)", ["force_demoted"]),
    ("Tier 4 (SCALP_SENTINEL)", ["scalp_sentinel"]),
]


def build(source: Path, out: Path) -> None:
    raw = json.loads(source.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    lines: list[str] = ["# Edge Design Audit — Inventory", ""]
    lines.append("自動生成: `python3 tools/build_edge_audit_inventory.py`")
    lines.append("")
    for tier_label, keys in TIER_MAP:
        lines.append(f"## {tier_label}")
        lines.append("")
        lines.append("| # | Strategy | Pairs | Source Tier |")
        lines.append("|---|---|---|---|")
        idx = 0
        for key in keys:
            entries = raw.get(key, [])
            grouped: dict[str, list[str]] = defaultdict(list)
            for e in entries:
                strategy = e["strategy"]
                pair = e.get("pair", "ALL")
                grouped[strategy].append(pair)
            for strategy in sorted(grouped):
                if strategy in seen:
                    continue
                seen.add(strategy)
                idx += 1
                pairs = ", ".join(sorted(set(grouped[strategy])))
                lines.append(f"| {idx} | {strategy} | {pairs} | {key} |")
        lines.append("")
    out.write_text("\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    build(args.source, args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_edge_audit_inventory.py -v
```

- [ ] **Step 5: Generate real inventory**

```bash
python3 tools/build_edge_audit_inventory.py \
  --source knowledge-base/wiki/tier-master.json \
  --out audits/edge_design/_INVENTORY.md
head -40 audits/edge_design/_INVENTORY.md
```

- [ ] **Step 6: Commit**

```bash
git add tools/build_edge_audit_inventory.py tests/test_edge_audit_inventory.py audits/edge_design/_INVENTORY.md
git commit -m "feat(audit): add edge design audit inventory builder"
```

---

## Task 2: Codex 監査 prompt template

**Files:** Create `audits/edge_design/_PROMPT_TEMPLATE.md`

- [ ] **Step 1: Write template** (full template per spec §3 + §5.1, with placeholders `{{STRATEGY}}`, `{{STRATEGY_PATH}}`, `{{TIER}}`, `{{SOURCE_TIER}}`, `{{PAIRS}}`, `{{HISTORICAL_METRICS_JSON}}`, `{{TASK_ID}}`, `{{CREATED_AT}}`. 8軸 method, 4 constraints (single strategy, no BT, no code mod, cite path:line, AMBIGUOUS halt), 出力フォーマット as spec §4.1)

- [ ] **Step 2: Commit**

```bash
git add audits/edge_design/_PROMPT_TEMPLATE.md
git commit -m "docs(audit): add Codex per-strategy audit prompt template"
```

---

## Task 3: Dispatch ヘルパスクリプト

**Files:** Create `tools/edge_audit_dispatch.py`, `tests/test_edge_audit_dispatch.py`

- [ ] **Step 1: Write failing test** (subprocess.run helper, assert placeholders replaced, output file written to queue_dir, assert no `{{TASK_ID}}` / `{{STRATEGY}}` left)

- [ ] **Step 2: Run test (FAIL)** — `pytest tests/test_edge_audit_dispatch.py -v`

- [ ] **Step 3: Implement** (`dispatch()` function: reads template, replaces 8 placeholders, writes to `<queue_dir>/<task_id>.md` where `task_id = "<ts>-w4-eda-<strategy>"`)

- [ ] **Step 4: Run test (PASS)**

- [ ] **Step 5: Commit**

```bash
git add tools/edge_audit_dispatch.py tests/test_edge_audit_dispatch.py
git commit -m "feat(audit): add per-strategy edge audit Codex dispatch helper"
```

---

## Task 4: Scaffold rollup files

**Files:** Create skeleton `_INDEX.md`, `_REDESIGN_QUEUE.md`, `_TIER1_GATE.md` in `audits/edge_design/`

- [ ] **Step 1: Write `_INDEX.md`** — header + empty table (`| Strategy | Tier | Verdict | Recommendation | Audited At | Audit File |`)

- [ ] **Step 2: Write `_REDESIGN_QUEUE.md`** — header + placeholder note "(全 audit 完了後にスクリプトで生成)"

- [ ] **Step 3: Write `_TIER1_GATE.md`** — header + stop conditions (`DESIGN_BROKEN ≥ 3` / `INVALID ≥ 30%`) + `Gate Decision: PENDING`

- [ ] **Step 4: Commit**

```bash
git add audits/edge_design/_INDEX.md audits/edge_design/_REDESIGN_QUEUE.md audits/edge_design/_TIER1_GATE.md
git commit -m "docs(audit): scaffold edge design audit rollup files"
```

---

## Task 5: Tier 1 dispatch loop — LIVE 系（10 戦略、逐次）

**Dispatch contract: 1 戦略 = 1 Codex task = 1 output file. Strict serial.**

- [ ] **Step 1: Extract Tier 1 strategy list** from `_INVENTORY.md` (awk Tier 1 section)

- [ ] **Step 2: For each strategy, dispatch:**
  1. `find strategies -name "${S}.py"` → `STRATEGY_PATH`
  2. Pull metrics rows from `tier-master.json` (elite_live + pair_promoted filtered by strategy)
  3. `python3 tools/edge_audit_dispatch.py --strategy "${S}" --strategy-path "${STRATEGY_PATH}" --tier "Tier 1 (LIVE)" --source-tier "elite_live_or_pair_promoted" --pairs "..." --metrics "$METRICS" --template audits/edge_design/_PROMPT_TEMPLATE.md --queue-dir .ai/tasks/queue/`
  4. `git add .ai/tasks/queue/*-w4-eda-${S}.md && git commit -m "task(audit): dispatch W4-EDA edge audit for ${S}" && git push`

- [ ] **Step 3: Wait for Codex completion + review output**
  - Poll: `until [ -f "audits/edge_design/${S}.md" ]; do sleep 60; done; git pull`
  - 司令塔 checklist: Verdict ∈ 5 分類, Recommendation ∈ S/A/B/C/D, Axis 1 = code-derived, evidence table 埋まり, code refs path:line 形式
  - 問題があれば task md に note 追加して reissue

- [ ] **Step 4: Append to `_INDEX.md`** (regex extract verdict / rec / audited_at, append row, commit)

- [ ] **Step 5: Repeat Steps 2-4 for remaining Tier 1 strategies (one at a time, 並列禁止)**

- [ ] **Step 6: Tier 1 gate decision**
  - Count `THESIS_VALID_DESIGN_BROKEN` and `THESIS_INVALID` in INDEX Tier 1 rows
  - If broken ≥ 3 → STOP, escalate user
  - If invalid / total ≥ 0.30 → STOP, request re-brainstorm
  - Else → record `Gate Decision: PROCEED to Tier 2`
  - Commit `_TIER1_GATE.md`

---

## Task 6: Tier 2 dispatch loop — Phase0 Shadow（~33 戦略）

**Pre-condition:** `_TIER1_GATE.md` = PROCEED.

- [ ] **Step 1: Extract Tier 2 list** (awk Tier 2 section)
- [ ] **Step 2: For each strategy, dispatch (Task 5 Step 2 同手順, source-tier=`phase0_shadow`)**
- [ ] **Step 3: 1 戦略ずつ commit + 待機 + INDEX 更新**
- [ ] **Step 4: 共通失敗パターン抽出**

```bash
grep -A 1 "BREAKS" audits/edge_design/*.md | head -40
grep -A 1 "MISMATCH" audits/edge_design/*.md | head -40
```
書き出し: `audits/edge_design/_TIER2_PATTERNS.md` → commit

---

## Task 7: Tier 3 dispatch loop — FORCE_DEMOTED（22 戦略、本命検証）

**Files:** Tier 5 の核心 — 「思想は正、設計が誤」仮説の本命検証群。

- [ ] **Step 1: Extract Tier 3 list**
- [ ] **Step 2: For each strategy, dispatch with source-tier=`force_demoted`**
  - **Axis 8 (failure mode 診断) 必須**
  - 再設計案を最低 1 案出させる
- [ ] **Step 3: 1 戦略ずつ commit + 待機 + INDEX 更新**

---

## Task 8: Tier 4 dispatch loop — SCALP_SENTINEL（10 戦略）

- [ ] **Step 1: Extract Tier 4 list**
- [ ] **Step 2: For each strategy, dispatch with source-tier=`scalp_sentinel`**
- [ ] **Step 3: 1 戦略ずつ commit + 待機 + INDEX 更新**

---

## Task 9: Final rollup — REDESIGN_QUEUE 生成

**Files:** Update `audits/edge_design/_REDESIGN_QUEUE.md`

- [ ] **Step 1: Generate REDESIGN_QUEUE** — Python script:
  - 全 `audits/edge_design/<strategy>.md` を走査
  - Verdict ∈ {`DESIGN_BROKEN`, `TIMING_BROKEN`} かつ Recommendation ∈ {S, A} のみ抽出
  - Sort: Recommendation S→A, Tier 1→4
  - Output: `_REDESIGN_QUEUE.md` table

- [ ] **Step 2: Commit + push**

```bash
git add audits/edge_design/_REDESIGN_QUEUE.md
git commit -m "audit: finalize W4-EDA redesign queue"
git push
```

- [ ] **Step 3: 司令塔 → user 完了報告**
  - 監査総数 / Tier 別内訳 / Verdict 分布
  - REDESIGN_QUEUE Top 5
  - 共通失敗パターン
  - Wave 4 推奨進行順

---

## Self-Review

- **Spec coverage**: spec §1-9 すべて Task 1-9 にマッピング済み
- **Placeholder scan**: TBD/TODO なし
- **Type/name consistency**: Verdict 5 分類 / S-D recommendation / Tier 1-4 ラベルが Task 4-9 で一貫
- **Cell vs strategy 整合**: spec §2 は cell 単位だが pair-tier 違いで思想は変わらないため strategy 単位 + per-pair Axis 6 で集約。本判断を明示。
