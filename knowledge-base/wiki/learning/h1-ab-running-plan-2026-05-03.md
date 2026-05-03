# H-1 Hour-Bucket Gate — A/B 並走計画書 (2026-05-03)

## 目的

W3-1 で実装した H-1 Hour-Bucket Promotion Gate の本番運用前に、Shadow tier 内で **1 ヶ月並走 (control vs treatment)** を実施し、`false demotion 率 < 20%` の運用基準を満たすことを実証する。

## 並走仕様

| 項目 | 値 |
|---|---|
| 並走期間 | 2026-05-04 〜 2026-06-04 (1 ヶ月) |
| 並走先 tier | Shadow (LIVE には流さない) |
| Arm A (control) | 既存 promotion logic (bucket gate なし) |
| Arm B (treatment) | 新 hour-bucket gate (本 PR) |
| Gate 定数 | `H1_GATE_MIN_N=30` / `H1_GATE_WILSON_LO=0.40` / `H1_GATE_EV_CI_LO=0.0` |
| Grandfather | 13 戦略 (本 PR `_GRANDFATHERED_LIVE` 集合参照) |
| データソース | Render Postgres (一次)。ローカル DB 単独評価は禁止 |

## 主要メトリクス

1. **false_demotion_rate**
   - 定義: gate により soft-demote された cell のうち、後続 30 日で control 側が profitable だった比率
   - 閾値: `< 20%` (越えた場合は gate 再調整)
2. **demotion_count_per_strategy**
   - 戦略ごとの soft-demote 件数。grandfather が機能しているか確認
3. **bucket_coverage**
   - N≥30 を満たす cell の割合 (4-bucket × pair × strategy 内の有効 cell 比率)
4. **ev_delta_arm_a_vs_b**
   - Arm A と Arm B の累積 EV 差 (Shadow 段階の paper PnL ベース)

## 監査クエリ (Render Postgres)

`is_shadow=1` を必須条件とし、Arm 識別は `meta->>'gate_arm'` (実装時に追加) で分離する。`oanda_audit.entry_type` の二義性 (`bridge_status='sent'`/`'filled'`) に注意 (memory: `reference_oanda_audit_twin_meaning`)。

```sql
-- bucket × strategy × pair 別の Arm B 結果
SELECT
  meta->>'gate_arm' AS arm,
  strategy,
  pair,
  CASE
    WHEN EXTRACT(HOUR FROM ts AT TIME ZONE 'UTC') < 6 THEN 'A'
    WHEN EXTRACT(HOUR FROM ts AT TIME ZONE 'UTC') < 12 THEN 'B'
    WHEN EXTRACT(HOUR FROM ts AT TIME ZONE 'UTC') < 18 THEN 'C'
    ELSE 'D'
  END AS bucket,
  COUNT(*) AS n,
  AVG(CASE WHEN realized_pnl > 0 THEN 1.0 ELSE 0.0 END) AS wr
FROM trades
WHERE is_shadow = 1
  AND ts >= '2026-05-04'
  AND ts <  '2026-06-04'
GROUP BY 1,2,3,4
HAVING COUNT(*) >= 30
ORDER BY arm, strategy, pair, bucket;
```

## 月次レポート雛形

ファイル名: `wiki/learning/h1-ab-monthly-2026-06-04.md`

レポートには以下を必ず含める:
1. 並走期間の実 trade 件数 (Arm A / Arm B)
2. false_demotion_rate (戦略別 + 全体)
3. demotion_count_per_strategy 表
4. bucket_coverage 表
5. ev_delta (Arm A − Arm B、累積 + 95% CI)
6. 想定外の発見 (特に grandfather 救済の妥当性)
7. **判定**: GO (LIVE 移行) / NO-GO (gate 再調整) / EXTEND (もう 1 ヶ月並走)

## 中止条件 (Kill Switch)

並走中でも以下に該当した場合は即時 Arm B を停止し再設計:
- false_demotion_rate が中間 (2 週目) 時点で **30% 超**
- grandfather 戦略の Shadow PnL が control 比 -50% 以上劣化 (gate 実装に予期せぬバグの示唆)
- bucket 集計で `is_shadow` の混入 / `entry_type` 二義性の取り違えが発覚

## Verdict matrix v1 整合

PR マージ前に **Codex 独立再レビュー必須** (gate 定数 0.40/0.0/30、grandfather 13 戦略集合を別エージェントで検証)。

## 関連

- 設計書: `wiki/learning/h1-hour-bucket-design-2026-05-03.md`
- 3 ヶ月 counterfactual: `wiki/learning/w3-1-counterfactual-3month-2026-05-03.md`
- Verdict matrix: `wiki/learning/verdict-threshold-matrix-v1-2026-05-03.md`
- 親プラン: `.claude/plans/find-out-way-of-fizzy-patterson.md`
