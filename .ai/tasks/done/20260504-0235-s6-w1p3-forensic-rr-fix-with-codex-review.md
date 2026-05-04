---
id: 20260504-0235-s6-w1p3-forensic-rr-fix-with-codex-review
title: S6 W1P3 — Forensic RCA on W1P2 REJECT + 3 pre-registered TP/SL geometry variants + Codex adversarial self-review
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T02:35:00+0900
roadmap_gate: Wave 1 Phase 3 — chart pattern family の真の expected value 計測 (W1P2 REJECT が detector 設計のせいか strategy 自体のせいかを切り分ける)
rule: R1
prereq_artifacts:
  - knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite  # signals/outcomes/w1p2_bt 全 3 table 既存
  - data/cache/massive/USD_JPY_5m.parquet
  - tools/s6_chart_pattern_detector.py
  - tools/s6_w1p2_primary_bt.py
related:
  - .ai/tasks/done/20260504-0155-s6-w1p2-primary-bt-bonferroni-m8.md  # W1P2 REJECT (8/8)
  - .ai/decisions/20260504-0150-s6-w1p1-conditional-promote.md
  - knowledge-base/wiki/lessons/feedback_success_until_achieved.md  # Null/Scenario A で closure 短絡禁止
---

# 0. なぜこのタスクか (動機)

W1P2 で chart pattern primary 8/8 が REJECT した。表面的には「chart pattern family 棄却」だが、実データの forensic で **真因が detector の TP/SL geometry 設計欠陥**であることが判明:

| Pattern | 平均 TP 距離 | 平均 SL 距離 | R:R 比 |
|---|---:|---:|---:|
| double_bottom BUY | 12.1 pip | 17.9 pip | **0.69** |
| double_top SELL | 11.8 pip | 17.8 pip | 0.68 |
| ascending_triangle BUY | 21.5 pip | 26.4 pip | 0.82 |
| (他 5 primary patterns) | … | … | 0.71-0.81 |

R:R < 1.0 = TP < SL (= 損失幅 > 利益幅)。break-even HR = 1/(1+R:R) ≈ 58-60%。実測 HR 54-59% は break-even 直前で、friction 2.1 pip で完全に陥落して PF 0.68-0.87 = REJECT。

**Bulkowski (Encyclopedia of Chart Patterns)** 等の文献では chart pattern は profitable とされる。それは **measured move TP** (パターン全高プロジェクション、R:R 1.5-2.5) を使うため。本実装の "neckline TP / 構造端 SL" 設定が profitable trading の幾何と逆で、これが REJECT の真因。

Strategy 自体が dead と結論する前に、**detector の TP/SL を pre-registered 変種で再 BT**し、family 救済可能性を統計的に確定する。

# 1. 仮説

**H0 (W1P2 verdict のまま)**: Detector を修正しても 8/8 REJECT。chart pattern family は USDJPY M5 + OANDA Japan friction 環境では本質的に profitable でない。**Wave 5 以降に延期確定**。

**H1 (本タスク主仮説)**: TP/SL geometry を Bulkowski measured-move 方式に修正すると R:R ≥ 1.5 となり、HR 54-59% でも friction-adjusted PF > 1.0 を達成する pattern が **3 つ以上存在**する。

**H2 (代替)**: TP geometry 単独修正では不十分。さらに confidence_score top-50% フィルタを足さないと PF > 1.0 にならない。

**H3 (反証)**: いずれの修正を試しても PF が 1.0 を超えない = strategy 真に死んでいる。

これら 3 仮説を **pre-registered 3 variants の A/B BT + Codex adversarial self-review** で切り分ける。

# 2. Forensic phase (実行必須)

タスクの最初に **以下 6 項目を実測 query で出力**:

1. **R:R 距離分布**: 8 primary patterns × direction の (TP-entry, entry-SL) histogram 中央値・平均・標準偏差。
2. **Friction sensitivity curve**: friction 0.0/0.5/1.0/1.5/2.0/2.5/3.0/4.0 pip → 各 pattern の PF を表で出す。PF=1 cross point を特定。
3. **Time-to-resolution distribution**: TP-hit までの bar 数 (median/p25/p75) vs SL-hit までの bar 数。早く SL する trade が多ければ entry timing 問題、TP まで長ければ horizon 短縮問題。
4. **Regime split**: ATR(14) を bar ごとに計算し、ATR の median で 2 分位 (low_vol / high_vol)。各 regime の per-pattern PF を出す。
5. **Quality filter analysis**: confidence_score column を quartile 分割。Top 25% / 25-50% / 50-75% / Bottom 25% の PF を per-pattern で算出。
6. **Yearly PnL**: per-pattern × per-year PnL 集計。S4 で 90.7% 集中の lesson を chart pattern にも適用、bias 検出。

これらが forensic 仮説生成の根拠となる。

# 3. 3 Pre-registered TP/SL Geometry Variants (LOCK, post-hoc 変更禁止)

W1P0 detector を **再実行せず** (= signals 22,094 は固定)、SQLite 上で **outcome を再計算**する形で 3 変種を A/B test。各 signal は同じ entry_px + 同じ pattern_height_atr を持つので、新 TP/SL は entry_px から幾何学的に算出可能。

## V1: Bulkowski Measured-Move TP

- **TP**: entry + (pattern_height_atr * atr_at_detection * direction_sign)
  - 既存の pattern_height_atr column と atr_at_detection column を使い、pattern 全高をピップ換算してそのまま projection
- **SL**: entry - (pattern_height_atr * atr_at_detection * 0.5 * direction_sign)
  - 全高の半分を SL として下流に置く (breakdown 防御)
- **目標 R:R**: 2.0
- **Hypothesis**: Bulkowski 文献整合の R:R で profitable

## V2: Tight SL at Pivot

- **TP**: 既存 tp_px そのまま (= neckline)
- **SL**: pivot_anchor_ts または pivot_opposite_ts のうち entry に近い方の price を SL とする
  - swing pivot 近接 SL = breakdown 確認直後すぐに損切る tight stop
- **目標 R:R**: 1.2-1.5 (entry-pivot 距離が SL 距離になるので狭まる)
- **Hypothesis**: SL を狭めるだけでも friction-adjusted PF が改善

## V3: V1 + Confidence Filter

- **TP/SL**: V1 と同じ
- **Filter**: confidence_score の top 50% (median 以上) signals のみ使用
- **Hypothesis**: Quality filter で N が半減するが per-trade edge が向上、Bonferroni m=8 でも合格水準

## V4 (control): Original W1P2 (no change)

W1P2 結果をそのまま再現 (regression check)。Friction sensitivity 検証用。

# 4. 採用 / 保留 / 棄却基準 (per variant × per pattern)

W1P2 と同じ 7 軸:

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| PF (friction 込み) | ≥ 1.20 | 1.05 ≤ PF < 1.20 | < 1.05 |
| Wilson 95% CI lower (effective WR) | ≥ 0.50 | 0.45 ≤ Wilson_lo < 0.50 | < 0.45 |
| OOS/IS PF ratio | ≥ 0.85 | 0.70 ≤ ratio < 0.85 | < 0.70 |
| max_year_share | < 0.50 | 0.50 ≤ x < 0.65 | ≥ 0.65 |
| positive_years (>0 PnL) | ≥ 8/12 | 6-7/12 | ≤ 5/12 |
| Bonferroni-corrected p_value | < 0.00625 | 0.00625 ≤ p < 0.05 | ≥ 0.05 |
| Kelly fraction (half cap) | ≥ 0.05 | 0.02 ≤ Kelly < 0.05 | < 0.02 |

**Bonferroni m**:
- V1: m=8 (8 patterns)
- V2: m=8
- V3: m=8 (filter は新仮説でなく v1 の subset)
- 合計検定数 m_total = 24 (3 variants × 8 patterns) で **family-wise** Bonferroni を適用すると α' = 0.05/24 = 0.00208 になり過度に厳格。**variant 内 m=8 で固定**し、複数 variant が ACCEPT した場合は別途 cross-variant comparison を行う (本タスクの後続)。

# 5. Codex Adversarial Self-Review (LOCK)

3 variants の BT 実行後、Codex 自身が以下の self-review を実行:

1. **Pre-registration violation チェック**: 仕様外のパラメータ調整を行っていないか
2. **Cherry-pick 検出**: forensic phase で見えた特定の bias を最終検定で除外していないか
3. **Friction model の妥当性**: 1.5 pip spread / 0.3 pip slippage が USDJPY OANDA Japan の **2024-2026 実測**と整合するか確認 (audit DB あれば参照)
4. **OOS split の data leakage**: IS 期間と OOS 期間で detector parameters が同じかを確認 (再 train なし)
5. **Yearly stability の解釈**: max_year_share NULL ケースの扱いが verdict matrix と整合するか
6. **Survivorship bias**: 失敗した patterns (W1P1 で除外した triple/flag) を "もし変種で蘇生したら" を **本タスクで検定しない** ことを明示 (post-hoc family expansion 防止)
7. **Statistical multiple testing**: m=8 vs m=24 の判断根拠を文書化

self-review 結果を `.ai/runs/.../adversarial-review.md` に書き出す。1 つでも violation があれば verdict を **強制 NEEDS_MORE_EVIDENCE** にする。

# 6. データ分離

- 入力: `chart_pattern_signals` + `chart_pattern_outcomes` + M5 parquet (全 read-only)
- 出力: 同 SQLite に新 table:
  - `chart_pattern_w1p3_v1_outcomes` (V1 の per-signal outcome)
  - `chart_pattern_w1p3_v2_outcomes` (V2 の per-signal outcome)
  - `chart_pattern_w1p3_v3_outcomes` (V3 の per-signal outcome)
  - `chart_pattern_w1p3_bt` (各 variant × pattern × verdict aggregation)
- 既存 table への UPDATE / DELETE 禁止
- demo.db / 本番 Render DB は触らない
- Live / Shadow / OANDA データは混入禁止 (本タスクは BT のみ)

# 7. 検証コマンド (Codex 必須実行順)

```bash
cd /data/repo/fx-ai-trader

# 1. 整合性確認
python3 -c "
import pandas as pd, sqlite3
df = pd.read_parquet('data/cache/massive/USD_JPY_5m.parquet')
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
n_sig = con.execute('SELECT COUNT(*) FROM chart_pattern_signals').fetchone()[0]
n_out = con.execute('SELECT COUNT(*) FROM chart_pattern_outcomes').fetchone()[0]
n_w1p2 = con.execute('SELECT COUNT(*) FROM chart_pattern_w1p2_bt').fetchone()[0]
print(f'parquet={df.shape}, signals={n_sig}, outcomes={n_out}, w1p2_bt rows={n_w1p2}')
"

# 2. Forensic phase: §2 の 6 項目を SQL + numpy で算出、forensic-report.md に出力

# 3. V1/V2/V3 BT script 実装 (codex が tools/ 配下に追加)
#    tools/s6_w1p3_variant_bt.py
#    --variant V1 / V2 / V3
#    --signals knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite
#    --output  knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite

# 4. 3 variants 実行
for V in V1 V2 V3; do
  python3 tools/s6_w1p3_variant_bt.py --variant $V \
    --signals knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
    --output knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite \
    --bootstrap-iters 1000 \
    --spread-pip 1.5 --slippage-pip 0.3 \
    --is-end 2022-12-31 --bonferroni-m 8
done

# 5. Adversarial self-review (§5 の 7 チェック)
#    出力: .ai/runs/<run_id>/adversarial-review.md

# 6. 集計レポート
python3 -c "
import sqlite3
con = sqlite3.connect('knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite')
print('=== W1P3 verdict matrix (V1/V2/V3 x 8 patterns) ===')
for row in con.execute('''
SELECT variant, pattern_name, direction, n_total, pf, wilson_lo, oos_is_pf_ratio,
       max_year_share, positive_years, bonf_pvalue, kelly_half, verdict
FROM chart_pattern_w1p3_bt
ORDER BY variant, verdict, pattern_name
'''):
    print(row)
"
```

# 8. 出力すべきレポート (codex `--output-last-message`)

1. **Forensic findings**: §2 の 6 項目の要約 (R:R 分布, friction sensitivity の cross-point, etc.)
2. **Per variant overall verdict**: V1 / V2 / V3 それぞれで X/8 ACCEPT
3. **Per variant × per pattern verdict table** (24 行)
4. **Codex self-review summary**: 7 チェックの pass/fail
5. **Promote 推奨 list**: どの (variant, pattern) ペアが Wave 4 promote 候補か
6. **真因 closure**: H0 / H1 / H2 / H3 のどれが支持されたか、根拠込み
7. **次のタスク提案**:
   - もし複数 variant が ACCEPT → cross-variant comparison + 本番 detector への variant 採択判断
   - もし 1 variant のみ ACCEPT → そのまま Wave 4 promote 設計
   - もし全 variant REJECT → strategy が真に dead と確定、Wave 5+ 延期 (W1P2 verdict 維持)

# 9. 禁止事項

- ❌ `.env`, OANDA / OPENAI / Render / Massive API key を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/` を編集
- ❌ 本番 DB への接続
- ❌ 既存 SQLite の `chart_pattern_signals` / `chart_pattern_outcomes` / `chart_pattern_w1p2_bt` を UPDATE / DELETE / DROP
- ❌ pre-registration LOCK 違反: V1/V2/V3 の TP/SL 公式の post-hoc 修正、Bonferroni m の調整、verdict matrix 境界変更
- ❌ Forensic phase の結果を見て改善仕様を変える (= cherry-pick disguise)
- ❌ Variant を 4 つ以上に増やす (m が膨らんで検定力低下、また post-hoc selection 罠)
- ❌ Friction model パラメータ (1.5 / 0.3 pip) の post-hoc 調整 (`feedback_partial_quant_trap` lesson)
- ❌ `git push` / `git rebase --onto` history rewrite

# 10. Rule R1 verification

- pre-registration LOCK: 本ファイルの **§3 の 3 variants 公式** + **§4 の verdict matrix** + **§5 の self-review 7 チェック** + **§7 の検証コマンド順** 全て LOCK
- post-hoc に上記を変更した場合、verdict は強制 INVALID で **全 variants NEEDS_MORE_EVIDENCE 扱い**
- 365日 BT スキップ不可 (本タスクは BT そのもの、12.3y full)

# 11. 期待される所要時間

- Forensic phase: ~5 min (SQL + numpy)
- 3 variants BT: 各 5-10 min × 3 = 15-30 min
- Adversarial self-review: ~5 min
- 合計: **30-45 min** (vectorized 実装の場合)

# 12. ロードマップへの寄与

- W1P2 で chart pattern family は表面的に dead だったが、本 W1P3 で **真の生死を確定**する
- 1 variant でも ACCEPT すれば Wave 4 promote 候補が復活、Gate 1 alpha source 多様化が前進
- 全 variant REJECT なら chart pattern family 公式に Wave 5+ 延期、無駄な Live 投入を防いだ価値が確定

# 13. 参考: W1P2 → W1P3 の引き継ぎ

W1P2 (`.ai/tasks/done/20260504-0155-s6-w1p2-primary-bt-bonferroni-m8.md`) で:
- 8 primary patterns 全 REJECT (PF 0.677-0.868)
- Verdict matrix 5 軸 (PF / Wilson / OOS-IS / Bonf / Kelly) 全て fail
- max_year_share NULL = 全 pattern で 12 年合計 PnL ≤ 0

本 W1P3 で **真因 (TP/SL geometry の R:R < 1) が判明**したので、W1P2 verdict は **detector 設計欠陥に起因する false REJECT** だった可能性を再評価する。


## Result (2026-05-04T05:03:17Z)

exit=0 · 312s

```
**完了**
W1P3 を locked 条件で実行しました。system `python3` には pandas/numpy が無かったため、同等コマンドを `.venv/bin/python` で実行しています。

出力:
- [forensic-report.md](/data/repo/fx-ai-trader/.ai/runs/20260504-s6-w1p3-chart-pattern-geometry/forensic-report.md)
- [adversarial-review.md](/data/repo/fx-ai-trader/.ai/runs/20260504-s6-w1p3-chart-pattern-geometry/adversarial-review.md)
- [s6_w1p3_forensic.py](/data/repo/fx-ai-trader/tools/s6_w1p3_forensic.py)
- [s6_w1p3_variant_bt.py](/data/repo/fx-ai-trader/tools/s6_w1p3_variant_bt.py)

SQLite には新規 table を作成済み:
- `chart_pattern_w1p3_v1_outcomes`: 21,160 rows
- `chart_pattern_w1p3_v2_outcomes`: 21,160 rows
- `chart_pattern_w1p3_v3_outcomes`: 21,160 rows
- `chart_pattern_w1p3_bt`: 24 rows

**Forensic 要約**
- Original R:R は全 primary で < 1.0。平均 R:R は `double_top 0.677`, `double_bottom 0.686`, `triangles 0.813-0.823`, `wedges 0.712-0.724`, H&S 系 `0.720-0.741`。
- Friction sensitivity は 0 pip でも大半が PF<1。PF=1 cross は `double_bottom` が 0.009 pip、`inverse_head_shoulders` が 0.796 pip。他は 0 pip 時点で PF<1。
- Time-to-resolution は TP が SL より早い傾向。例: double_top TP median 10 bars vs SL median 19 bars。horizon 不足というより、payoff geometry と raw edge 不足が主因。
- ATR split は high_vol の方が全体に改善するが、最高でも original `inverse_head_shoulders high_vol PF=0.987` で PF>1 には届かず。
- `confidence_score` は各 primary pattern 内で完全に定数。V3 の median filter は全件通過し、実質 V1 と同一。
- Yearly PnL はほぼ全 pattern で複数年にわたり負。特定 1 年集中ではなく、構造的に負けている。

**Variant Verdict**
| Variant | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT | Best PF |
| --- | ---: | ---: | ---: | ---: |
| V1 measured-move | 0/8 | 0/8 | 8/8 | 0.798 |
| V2 tight pivot SL | 0/8 | 0/8 | 8/8 | 0.813 |
| V3 V1 + confidence | 0/8 | 0/8 | 8/8 | 0.798 |

**24 行 Verdict Matrix**
| V | pattern | dir | PF | Wilson_lo | OOS/IS | pos_years | p | Kelly_half | verdict |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| V1 | ascending_triangle | BUY | 0.798 | 0.325 | 1.125 | 1 | 0.356 | -0.043 | REJECT |
| V1 | descending
…(truncated)
