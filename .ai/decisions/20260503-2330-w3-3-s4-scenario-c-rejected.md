---
id: 20260503-2330-w3-3-s4-scenario-c-rejected
title: W3-3 S4 Connors-Raschke 80-20 BT — Scenario C (REJECT) on pre-registered primary
date: 2026-05-03T23:30:00+0900
verdict: ACCEPT (= BT 完走、判断は Reject)
related_task: .ai/tasks/done/20260503-1715-w3-3-rerun-s4-connors-raschke-80-20-bt.md
related_run: .ai/runs/20260503-173011-20260503-1715-w3-3-rerun-s4-connors-raschke-80-20-bt/final.md
artifacts:
  - knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md
  - knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.json
  - knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.md
  - knowledge-base/raw/bt-results/s4-primary-trade-list-2026-05-03.parquet
  - knowledge-base/raw/bt-results/s4-primary-daily-pnl-2026-05-03.parquet
rule: R1
---

# Verdict: ACCEPT (BT 実装) / Strategy verdict = Scenario C / REJECT

Codex Job `task-mopifuaf-1muchp` (W3-3-rerun) は initial run で `INTERVENTION_LIST_MISSING` で正しく abort、catalog §B-2 に 8 件 BoJ 介入リストを Claude (司令塔) が埋め込んだ後、Claude 側で BT 再実行 → 完走。BT 実装・テスト (6 件 PASS)・成果物 emit すべて acceptance criteria 通過。

## Quant 7 軸 (pre-registered primary cell `(10, 50_trailing, NY_close_21UTC)`)

| 軸 | 実測 | B-marg threshold | 通過 |
|---|---|---|---|
| 1. N | 468 | ≥50 | ✅ |
| 2. Wilson 95% lo | **0.390** | >0.40 | ❌ |
| 3. PF | **1.083** | >1.0 | ✅ borderline |
| 4. OOS/IS PF | 1.377 | >0.4 | ✅ |
| 5. Bonferroni p (m=27, vs BEV 34.4%) | 0.00095 | <0.20 | ✅ |
| 6. Sharpe | 0.43 | >0.0 | ✅ |
| 7. Kelly | 0.030 | >0 | ✅ |

**1 軸 fail (Wilson_lo<0.40)** で per-cell verdict = `FAIL`。

## Null bootstrap (1000 shuffles)

- Actual primary PF = 1.083
- Null mean PF = 1.076 (実 PF と差 0.007)
- Empirical PF percentile = **0.547** (median 付近)
- **Two-sided p = 0.906** — 完全に non-significant

つまり pre-registered primary cell の見かけの edge は label-shuffle に対して **ほぼゼロ**。Bonferroni p が低かったのは「BEV=34.4% vs 観測 WR=43.4%」を比較した結果で、ランダム shuffle 後の null PF 分布と比較すると edge は消える。

## Time cohort (12年 USDJPY 年次 PnL)

| 年 | PnL pip | N |
|---|---:|---:|
| 2014 | -11.3 | 37 |
| 2015 | -149.8 | 27 |
| 2016 | +273.7 | 42 |
| 2017 | -243.5 | 43 |
| 2018 | -178.6 | 40 |
| 2019 | -85.9 | 30 |
| 2020 | -10.5 | 33 |
| 2021 | +246.6 | 41 |
| 2022 | +222.2 | 47 |
| 2023 | +340.0 | 40 |
| **2024** | **+535.3** | 40 |
| 2025 | -246.9 | 41 |
| 2026 | -101.1 | 7 |
| **合計** | **+590.2** | 468 |

- 2014-2020 net = **-405.9 pip** (7 年連続赤字)
- 2021-2024 net = +1344.1 pip (4 年好調)
- 2025-2026 net = -348.0 pip (LIVE 直近で再赤字)
- **max_year_share (2024 / total) = 0.907** = 単年で総利益の 90.7% を占める

12 年で +590 pip だが **総利益のほぼ全てが 2024 年** (BoJ 介入連発 + USDJPY 145→160 trend) に集中。介入日自体は除外しているが、介入「環境」(円安加速期 + intervention threat) が edge の出所。これは structural alpha ではなく **regime artifact**。`feedback_cohort_time_check` 違反。

## Scenario verdict

**Scenario C — REJECT** (pre-registered primary に対して):

1. Wilson_lo<0.40 (1 軸 fail)
2. Null bootstrap p=0.906 (label-shuffle vs実 edge ほぼ無差別)
3. Time cohort 90.7% 2024 集中 = regime artifact

## クオンツ確認 (review checklist 通過)

- Rule R1 → 必要 8 軸全測定、null bootstrap・cohort 検証も完了
- BT/Shadow/Live/OANDA 混在: なし。BT は cache parquet のみ参照、Live API 不使用
- 本番 DB / `.env` / OANDA 秘密: 触られていない
- `feedback_partial_quant_trap` ✅ (7 軸全部測った)
- `feedback_label_empirical_audit` ✅ (Codex は INTERVENTION_LIST_MISSING で正しく停止し、Claude が catalog 修復後に再実行)
- `feedback_cohort_time_check` ✅ (90.7% 集中を発見)
- `feedback_success_until_achieved` ✅ (Reject だが代替候補をグリッド分析から enumerate)

## Grid 全体観 (代替仕様の発見)

27 cell verdict 集計:

- **FAIL = 9 cells** (全て 50_trailing exit) → 50%-trailing 設定は全滅
- **B-marg = 12 cells** → 100_trailing と fixed_time で出てくるが boundary 不問
- **B = 6 cells** → **全て London_close_16UTC**
- **A = 0 cells**

Best non-primary cell: **`(10, 100_trailing, London_close_16UTC)`**:
- N=448, WR=48.7%, Wilson_lo=0.441, PF=1.31, IS_PF=1.00, OOS_PF=1.57, OOS/IS=1.56, Sharpe=1.46, Kelly=11.1%, max DD=903.1 pip, total +2180.1 pip
- raw_p=3.7e-10, Bonferroni_p=1.0e-8

Connors-Raschke spec の 50%-trailing は USDJPY M5 で trailing が tight すぎて利を取り切れていない。100%-trailing (range 全幅) に緩めると **6 cells で B 通過**、Sharpe 1.4+/Kelly 11%+。これは興味深い signal だが…

**重要な留保 (post-hoc selection の罠)**:

- 本タスクの pre-reg は `(10, 50_trailing, NY_close_21UTC)` で LOCK 済み。グリッドを見て London_close-100_trailing が良いと選ぶのは **post-hoc cell selection**。pre-reg 規律違反。
- B-tier cells 自体は null bootstrap を実施していない。primary の null p=0.906 を見ると London-close-100 cells も label-shuffle に脆弱な可能性が高い。
- 90.7% 2024 集中は primary の cohort 結果。London-close cells も同じ regime に依存している可能性が高い (同じデータ・期間)。

## Catalog §B-2 status diff (proposal、Claude が user 承認後に書く)

```diff
- | **S4** | **Connors-Raschke 80-20 (intraday reversal)** | B/E | USDJPY (M5-H1) | ◎ | 既存 fib_reversal の補強候補 | 中-高 — 17 年で正利益 |
+ | ~~**S4**~~ | ~~**Connors-Raschke 80-20**~~ → **academic only** | — | USDJPY (M5) | ✗ | 12.3y BT で pre-reg primary fail (null bootstrap p=0.91, 90.7% 2024 集中) | 低 — regime artifact |
```

§B-2 本文末尾に追記:

```markdown
- **2026-05-03 BT verdict (W3-3-rerun)**: USDJPY M5 12.3y / pre-registered primary `(10, 50_trailing, NY_close_21UTC)` で **Scenario C / REJECT**。Wilson_lo=0.390 < 0.40, null bootstrap p=0.906, 単年 (2024) 集中 90.7%。grid 観察上 London_close+100_trailing 系 6 cell が B 通過 (PF 1.27-1.31) だが post-hoc selection で pre-reg LOCK 違反のため **本カタログ上は academic only に降格**。Wave 4 候補としては「London_close+100_trailing primary で **fresh data 待ち** + 別 pair」しか正攻法はない。
```

## Wave 4 follow-up 提案 (`feedback_success_until_achieved` 準拠で代替明示)

3 つの選択肢を user 判断で 1 つ選ぶ。

### 選択肢 A: 完全 reject (推奨)

- catalog §B-2 を academic only に降格
- 90.7% 単年集中は LIVE で再現される保証なし。2025 年が既に -246.9 pip (赤字) なのが robust edge ではない決定打
- 他の §B (Holy Grail / Anti / Turtle Soup) や §C / §D の新規候補に Wave 3 Tier 2 の枠を譲る

### 選択肢 B: London-close + 100_trailing で fresh-data 待ち pre-reg

- 新 primary = `(10, 100_trailing, London_close_16UTC)` を Wave 4 で LOCK 起票
- BT は 2026-05-01 以降の **新規 OOS** だけで実施 (post-hoc selection を避けるため過去データ再使用禁止)
- N=10/月想定 → N=30 で B-marg 判定可能になるまで 3 ヶ月 Shadow 蓄積

### 選択肢 C: pair extension (GBPJPY)

- USDJPY が 2024 偏重なら、GBPJPY で別 regime cohort を取る
- W3-4 と同じ "GBPJPY M5 12 年 cache が必要" blocker と衝突 → W3-4-data 先行

## 次の一手 (1つ)

**選択肢 A — catalog §B-2 を academic-only に降格**。理由:

- 12 年 BT で primary が Scenario C (null bootstrap fail + 90.7% 単年集中)
- 90.7% 集中は post-hoc cell selection で誤魔化せない構造的問題
- 2025 年が既に赤字 = LIVE turn-around は仮想ではなく実測
- Wave 3 Tier 2 の限られた枠を使う候補としては、信号 / 選択肢 B (fresh data 待ち 3 ヶ月+) より §B-3 (Holy Grail / Anti / Turtle Soup) の新規 BT 起票のほうが **時間あたり期待値**が高い

選択肢 B/C は user が Wave 4 で再考可能だが、まず本タスクは選択肢 A で closure する。
