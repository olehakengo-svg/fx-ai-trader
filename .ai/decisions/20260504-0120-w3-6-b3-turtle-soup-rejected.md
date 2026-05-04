# W3-6 §B-3 Turtle Soup BT — REJECT (Scenario C)

- Date: 2026-05-04 01:20 JST
- Rule: R1 (Wave 3 Tier 2 alpha source replacement, 1/3 of S4 reject 補充)
- Source: `.ai/runs/20260504-011035-20260503-2340-w3-6-b3-turtle-soup-bt/final.md`
- Task: `.ai/tasks/done/20260503-2340-w3-6-b3-turtle-soup-bt.md`
- Codex Job ID: `task-mopyvwwy-b1lh64`
- Codex Session: `019dee9b-3cd8-7430-8579-3571dd641fcc`
- Verdict (Claude review): **REJECT** — 一致 (Codex self-verdict も Scenario C / REJECT)

## Pre-registered primary cell の実測

Primary = `(failure_window=12, exit_method=100_trailing, session_boundary=London_close_16UTC)`

| metric | 実測 | pre-reg B band 閾値 | 判定 |
|---|---|---|---|
| N | 331 | (informational) | — |
| WR | 0.2991 | — | — |
| Wilson 95% lo | 0.2523 | > 0.42 | **FAIL** |
| PF | 1.1159 | > 1.20 | **FAIL** |
| OOS/IS PF | 1.0547 | > 0.60 | PASS |
| Bonferroni p (m=27) | 1.0000 | < 0.10 | **FAIL** |
| Sharpe | 0.5342 | > 0.50 | PASS |
| Kelly | 0.0275 | > 0.05 | **FAIL** |
| Max DD | 872.1 pip | (informational) | — |
| Total pip | 488.9 pip | (informational) | — |

Pre-reg 6 条件中 4 つ FAIL。

## Validity-of-evidence (追加 gate)

| gate | 実測 | 閾値 | 判定 |
|---|---|---|---|
| Null bootstrap two-sided p | 0.902 (empirical PF percentile=0.549) | < 0.05 | **FAIL** |
| max_year_share (cohort 集中) | 1.4457 (cohort_concentrated=true) | < 0.50 | **FAIL** |
| Intervention catalog load | 8 events / §B-2 | ≥ 1 | PASS |
| Bonferroni m | 27 (locked) | == grid size | PASS |

null 区別不能 + 単年集中。エッジ実在性は否定。

## データ分離・操作安全性

- BT のみ。Live/Shadow/OANDA 無接触。
- 出力先は `knowledge-base/raw/bt-results/` 配下のみ (本番 DB・`.env` 無接触)
- 編集は detector/test/learning/results 限定 (catalog, matrix, modules/, strategies/, cache 無編集) — Codex 自己申告とログ整合
- pytest 8/8 PASS, dry-run PASS, full BT exit 0

## ロードマップ寄与

- Wave 3 Tier 2 alpha source 補充 1/3 が **失敗**。残候補は §B-3 Holy Grail / Anti の 2/3。
- Gate 1 Kelly Half は依然 alpha 多様化が不足。S2/S3 通過済 + S4 reject + Soup reject。
- §B-3 family が 2 連続棄却なら catalog 全体の prior を再評価する分岐に入る (今回はまだ 1/3)。

## Deferred 検証 (Codex から繰越し)

- D: S2 Turtle anti-correlation (rolling 30d corr < -0.10) — 元々 hedge 仮説の鍵だが本 cell が REJECT なので **検証スキップ可** (棄却済 strategy の hedge 性は議論不要)
- E: fib_reversal LIVE corr — 同上、不要
- F: yfinance broker cross-check — 同上、不要

## Next

- 次タスクキュー: `W3-7 §B-3 Holy Grail` BT (catalog §B-3 残候補 1/2)。同 BT インフラ流用、pre-reg matrix を Holy Grail 仕様に書き換え。
- S6 W1P0 production rerun (直前 run) は **CHANGES_REQUESTED** — production inventory は ACCEPT 級だが test/fixture 契約が一致しない (29 expected vs 20 collected, 30 row fixture vs 12 row)。spec or test の整合のみで W1P1 進めるよう task 修正必要。本決定とは独立。
