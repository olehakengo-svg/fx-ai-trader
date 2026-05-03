---
id: 20260504-0155-s6-w1p2-primary-bt-bonferroni-m8
title: S6 W1P2 — Primary 8-pattern Full BT with friction, OOS-WF, Bonferroni m=8, bootstrap null
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T01:55:00+0900
roadmap_gate: Wave 1 Phase 2 → Wave 4 promotion gate (Gate 1 Kelly Half 前提)
rule: R1
prereq_artifacts:
  - knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite  # 22,094 signals + 22,094 outcomes (W1P0 + W1P1 完了)
  - data/cache/massive/USD_JPY_5m.parquet  # 903,828 bars / 12.3y
  - tools/s6_chart_pattern_detector.py
  - tools/s6_w1p1_outcome_audit.py  # outcome labeling 既存実装
related:
  - .ai/decisions/20260504-0150-s6-w1p1-conditional-promote.md  # 8-pattern primary 採用根拠
  - .ai/decisions/20260504-0125-s6-w1p0-inventory-manual-promote.md
  - knowledge-base/wiki/lessons/lesson-cohort-time-check.md  # S4 単年集中 90.7% の罠
  - knowledge-base/wiki/strategies/s6-chart-pattern.md
---

# Hypothesis (仮説)

W1P1 で確認した 8 primary pattern × direction (ascending_triangle BUY / descending_triangle SELL / rising_wedge BUY / falling_wedge SELL / double_bottom BUY / double_top SELL / inverse_head_shoulders BUY / head_shoulders SELL) は、**spread/execution friction 込み + Bonferroni m=8 補正後**でも、

1. **PF > 1.2** で統計的に random null と区別できる (Bonferroni 後 p < 0.05/8 = 0.00625)
2. **Wilson 95% CI lower > 0.50** で TP 到達率が 50% を超えると言える
3. **OOS/IS PF ratio > 0.85** で out-of-sample 安定性がある (2014-2022 IS / 2023-2026 OOS 分割)
4. **max_year_share < 0.50** で単年集中 bias がない (S4 W3-3 で 2024 単年 90.7% で trap にハマった lesson)
5. **Kelly fraction > 0.05** で position sizing が成立する

これら 5 条件を全 8 patterns で満たせば **Wave 4 chart pattern strategy 化に直接 promote** する根拠となる。partial pass (8 patterns 中 N 個 ACCEPT) なら N 個のみ promote。全滅なら chart pattern family を Wave 5 以降に延期。

# Primary 8 patterns (PRE-REGISTERED, do not modify)

| # | Pattern | Direction | W1P1 raw HR | W1P1 N |
|---|---|---|---|---|
| 1 | ascending_triangle | BUY | 54.0% | 3,772 |
| 2 | descending_triangle | SELL | 55.2% | 2,839 |
| 3 | rising_wedge | BUY | 54.1% | 1,747 |
| 4 | falling_wedge | SELL | 55.9% | 1,251 |
| 5 | double_bottom | BUY | 59.5% | 4,666 |
| 6 | double_top | SELL | 57.4% | 4,869 |
| 7 | inverse_head_shoulders | BUY | 58.1% | 999 |
| 8 | head_shoulders | SELL | 58.0% | 1,017 |

W1P1 で除外確定したもの (本タスクでは触らない):
- bull_flag BUY (HR 44.9%) / bear_flag SELL (HR 42.1%): random 未満
- triple_bottom BUY / triple_top SELL: N < 200, symmetry 10.3pp small-N noise

# Friction / Execution model (PRE-REGISTERED)

| Cost | 値 | 根拠 |
|---|---|---|
| Spread | **1.5 pip** (= 0.015 JPY for USDJPY) | OANDA Japan USDJPY M5 平均 (2024-2026 audit) |
| Slippage | **0.3 pip** (one-way, applied at entry & exit) | system-reference.md 既存値 |
| Commission | 0 | OANDA Japan は spread に内包 |
| Total round-trip cost | **2.1 pip per trade** | 1.5 + 0.3 + 0.3 |

これを既存 outcome の `pnl_pips` に対して **post-hoc に減算**:
- TP hit: `pnl_pips_net = pnl_pips_raw - 2.1`
- SL hit: `pnl_pips_net = pnl_pips_raw - 2.1` (損失側にも friction 加算)
- TO (timeout): `pnl_pips_net = pnl_pips_raw - 2.1` (TO は exit_px が forced exit 時の close 値、それから friction 減算)

friction 反映後に PF / Kelly / Sharpe を再計算する。raw HR は変わらないが、effective WR (= friction 後で profit > 0 となった trade の比率) は raw HR より低下する。

# Position sizing (PRE-REGISTERED)

各 trade の risk = **account の 1.0%** (1 unit = 1% を基準)。
Kelly fraction を per-pattern で計算し、**Kelly half cap = Kelly_calc / 2** を実弾推奨 sizing とする (full Kelly はリスクが過大)。

position size (units) = (risk_pct / risk_per_trade_pips) ただし risk_per_trade_pips は (entry - SL) の絶対値 + spread/2。

# OOS-WF split (PRE-REGISTERED)

- **IS (in-sample)**: 2014-01-01 → 2022-12-31 (9 年)
- **OOS (out-of-sample)**: 2023-01-01 → 2026-04-30 (3 年 4 か月)
- IS / OOS 共に各 pattern の PF / HR / Kelly を計算
- **OOS/IS PF ratio** を ACCEPT 条件に組み込む

note: 5-fold rolling WF は本タスクでは行わない (chart pattern detector は parameters を train しないため、rolling WF の意味が薄い)。代わりに **yearly PnL 分布**でロバスト性を担保。

# Yearly stability check (S4 cohort-time-check lesson 反映)

各 pattern について以下を計算:
- 12 年分 (2014-2026 のうち full year 12 個 + partial 2026) の年次 PnL pips 合計
- max_year_share = max(year_pnl) / sum(year_pnl) (sum > 0 前提、sum ≤ 0 なら REJECT)
- positive_years = sum > 0 となった年数 / total_years

ACCEPT 条件: **max_year_share < 0.50 AND positive_years ≥ 8 / 12** (66%).

# Bonferroni m=8 + 1000-bootstrap null (PRE-REGISTERED)

各 pattern について null hypothesis: **「PF = 1.0 (no edge)」**

bootstrap 手順:
1. 元 outcomes (TP/SL/TO の 3 値) の順序を shuffle 1000 回
2. 各 shuffle で friction 込み PF を計算
3. observed PF が shuffled distribution の何 percentile かを measure
4. p_value = 1 - percentile_rank
5. **Bonferroni 補正**: p < 0.05 / 8 = **0.00625** で reject null

p_value < 0.00625 で「edge は random ではない」と判定 (= ACCEPT 候補)。

# Verdict matrix (per pattern × direction)

各 pattern × direction について以下を判定:

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| PF (friction 込み) | ≥ 1.20 | 1.05 ≤ PF < 1.20 | < 1.05 |
| Wilson 95% CI lower (effective WR) | ≥ 0.50 | 0.45 ≤ Wilson_lo < 0.50 | < 0.45 |
| OOS/IS PF ratio | ≥ 0.85 | 0.70 ≤ ratio < 0.85 | < 0.70 |
| max_year_share | < 0.50 | 0.50 ≤ x < 0.65 | ≥ 0.65 |
| positive_years (>0 PnL) | ≥ 8/12 | 6-7/12 | ≤ 5/12 |
| Bonferroni-corrected p_value | < 0.00625 | 0.00625 ≤ p < 0.05 | ≥ 0.05 |
| Kelly fraction (half cap) | ≥ 0.05 | 0.02 ≤ Kelly < 0.05 | < 0.02 |

7 条件全て ACCEPT で **per-pattern ACCEPT** (Wave 4 promote 候補)。
1 条件以上 REJECT または **2 条件以上 NEEDS_MORE_EVIDENCE** で **per-pattern NEEDS_MORE_EVIDENCE** (要追加検証)。
**3 条件以上 REJECT** または **PF / Kelly / Bonferroni のいずれかが REJECT** で **per-pattern REJECT** (除外確定)。

# Overall verdict (8 patterns aggregate)

- **8/8 ACCEPT**: Wave 4 全面 promote (chart pattern family が新 alpha source として確定)
- **5-7/8 ACCEPT**: 通った patterns のみ Wave 4 promote、残りは exploratory
- **2-4/8 ACCEPT**: 部分 promote、roadmap 上の Wave 4 期待値を下げる
- **0-1/8 ACCEPT**: chart pattern family 全体を Wave 5 以降に延期

# データ分離 (重要)

- 本タスクは **BT only**。Live / Shadow / OANDA 実弾には触らない。
- 入力: `chart_pattern_signals` + `chart_pattern_outcomes` + M5 parquet (全 read-only)
- 出力: 同 SQLite に新 table `chart_pattern_w1p2_bt` を追加 (per-pattern 結果格納)
- **demo.db 等のローカル DB / 本番 Render DB は一切触らない**

# 統計条件まとめ

各 pattern × direction について:
- N (raw signal count): W1P1 値そのまま
- raw HR: W1P1 値そのまま
- effective WR: friction 込みで profit > 0 となった trade 比率
- PF: gross profit / gross loss (friction 込み)
- Kelly fraction: (effective_WR * avg_win - effective_LR * avg_loss) / avg_win
- Wilson 95% CI lower: standard formula (effective_WR ± Z_0.025 * sqrt(...))
- Bonferroni-corrected p_value: 1000-bootstrap based, α'=0.00625
- OOS PF / IS PF ratio
- max_year_share, positive_years
- Sharpe: PnL 系列の mean / std * sqrt(annualization_factor)

# 検証コマンド (Codex 必須実行)

実行順:

```bash
cd /data/repo/fx-ai-trader

# 1. SQLite と parquet 整合性確認
python3 -c "
import pandas as pd, sqlite3
df = pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet')
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
n_sig = con.execute('SELECT COUNT(*) FROM chart_pattern_signals').fetchone()[0]
n_out = con.execute('SELECT COUNT(*) FROM chart_pattern_outcomes').fetchone()[0]
print(f'parquet={df.shape}, signals={n_sig}, outcomes={n_out}')
"
# 期待: parquet (903828, 7), signals 22094, outcomes 22094

# 2. W1P2 BT script を新規作成 (codex が tools/ 配下に追加)
#    tools/s6_w1p2_primary_bt.py
#    --pattern <name> --direction <BUY|SELL>
#    内部で friction / OOS / yearly / bootstrap / Bonferroni を計算

# 3. 8 patterns 一括実行 (loop or single-shot multi-pattern)
python3 tools/s6_w1p2_primary_bt.py \
  --signals knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
  --output  knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
  --primary-only \
  --bootstrap-iters 1000 \
  --spread-pip 1.5 --slippage-pip 0.3 \
  --is-end 2022-12-31 --bonferroni-m 8

# 4. per-pattern verdict 集計レポート
python3 -c "
import sqlite3
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
print('=== per-pattern verdict matrix ===')
for row in con.execute(\"\"\"
SELECT pattern_name, direction, n_total, pf, wilson_lo, oos_is_pf_ratio,
       max_year_share, positive_years, bonf_pvalue, kelly_half, verdict
FROM chart_pattern_w1p2_bt
ORDER BY verdict, pattern_name
\"\"\"):
    print(row)
"
```

# 出力すべきレポート (codex `--output-last-message`)

1. **Overall verdict**: 8/8 ACCEPT / 5-7/8 / 2-4/8 / 0-1/8 のどれか
2. **Per-pattern verdict table** (8 行: pattern, dir, PF, Wilson_lo, OOS/IS, max_year_share, positive_years, bonf_p, Kelly, verdict)
3. **Promote 推奨 list**: Wave 4 即着手対象 patterns
4. **Exploratory list**: NEEDS_MORE_EVIDENCE patterns + 追加検証推奨内容
5. **Reject list**: 除外確定 patterns + 除外理由
6. **次にやるべきこと**: Wave 4 への直接 promote / 追加 BT 設計 / family 延期 のいずれか

# 禁止事項

- ❌ `.env`, OANDA / OPENAI / Render API key を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/` を編集 (Live promotion は Wave 4 promote 後)
- ❌ 本番 DB (Render `/var/data/*.db`) への接続
- ❌ ローカル DB (`demo.db` 等) への書き込み
- ❌ 既存の未 commit 変更を上書き / stash / discard
- ❌ `data/cache/massive/*.parquet` を編集 / 削除 (read-only)
- ❌ `chart_pattern_signals` および `chart_pattern_outcomes` への UPDATE / DELETE / DROP (read-only)
- ❌ Friction model parameters (1.5 pip spread / 0.3 pip slippage) の post-hoc 調整
- ❌ Bootstrap iterations / Bonferroni m / IS-OOS split / Kelly cap の post-hoc 調整 (= cherry-pick disguise)
- ❌ verdict matrix の境界値の post-hoc 調整
- ❌ `bull_flag` / `bear_flag` / `triple_*` を W1P2 primary に混ぜない (W1P1 で除外確定済)
- ❌ `git push` / `git rebase --onto` 等の history rewrite

# Rule R1 verification

- 365日 BT スキップ不可 (本タスクは BT そのもの)
- pre-registration LOCK: 本ファイルの "Friction model" / "Position sizing" / "OOS split" / "Yearly stability" / "Bonferroni" / "Verdict matrix" / "Primary 8 patterns" 全てが LOCK
- post-hoc に上記いずれかを変更した場合、verdict は強制 INVALID で **全 patterns NEEDS_MORE_EVIDENCE 扱い**

# Performance note

- 22,094 signals × 1000 bootstrap × 8 patterns ≈ 176M trade simulations
- numpy/vectorized 実装で **estimated 10-30 分** (loop 実装だと 2 時間+)
- Codex は必ず vectorize すること (per-trade Python loop 禁止)

# 月利 100% ロードマップへの寄与

- W1P0 → W1P1 → **W1P2 (本タスク)** → Wave 4 chart pattern strategy 化
- Gate 1 (Kelly Half) alpha source 多様化の最大の山場
- 8/8 ACCEPT なら **Wave 4 で 8 種類の chart pattern strategies が即時 promote** 候補となり、現行 strategy pool (S2/S3/S5/H1) と低相関なら portfolio 効果大
- 1 つでも ACCEPT なら **新 alpha family 1 つ追加**で Gate 1 進捗
- 全滅なら chart pattern family は Wave 5 以降に延期、roadmap 上の期待値を下げる

# 参考: W1P1 → W1P2 の引き継ぎ

W1P1 (`.ai/decisions/20260504-0150-s6-w1p1-conditional-promote.md`) で:
- 22,094 signals 全件 outcome labeled (DM 1/22094)
- 12 patterns × 2 dir のうち 10 が hit_rate > 50%
- 8-pattern primary set (4 bull/bear pair) は全て symmetry pass + HR > 54% + N > 999

W1P2 はこの 8 patterns について **friction 込み + statistical rigor (Bonferroni / bootstrap / OOS / yearly) で BT 化**するタスク。raw HR は既知だが effective WR はまだ未知。
