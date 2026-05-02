# H-1 Hour-Bucket Gate — A/B Test Plan

**Date**: 2026-05-03
**Status**: Plan (gate not yet enabled in production)
**Wave 2 task**: W2-4
**Spec**: `wiki/learning/h1-hour-bucket-design-2026-05-03.md`
**Parent audit**: `wiki/learning/h1-spread-time-audit-2026-05-03.md`

---

## 1. 目的

H-1 hour-bucket promotion gate (W2-4 で実装) の本番適用前に、Shadow tier 限定で
1 ヶ月並走 A/B を行い、以下を確認する:

1. **既存 LIVE 戦略の破壊が起きないこと** (grandfather + N_min 防御の実効性)
2. **過剰 demote が起きないこと** (false demote rate < 20%)
3. **promote 候補の品質改善** (B treatment で promote された戦略の post-promote EV ≥ A control)

---

## 2. 前提

- W2-4 PR でゲートは実装済み (`H1_GATE_ENABLED=False` 既定)
- 必須事前検証 (counterfactual + grandfather dry-run) 完了
- LIVE 戦略は `H1_GRANDFATHERED_LIVE` + runtime auto-grandfather (現在 promoted 状態)で二重保護
- Render 本番データを一次ソースとする (`feedback_check_orphan_local_app`)

---

## 3. 設計

### 3.1 Cohort

- **A (control)**: `H1_GATE_ENABLED=False` (現行 promotion logic そのまま)
- **B (treatment)**: `H1_GATE_ENABLED=True`, `H1_PROMOTION_BUCKET_MODE=4_bucket`,
  既定 thresholds (`N_min=30`, `wilson_min=0.40`, `ev_min=-0.5`)

両 cohort とも:
- LIVE 戦略 grandfather 適用
- Shadow tier のみ gate 対象
- 同じ Render データソース、同じ通貨ペア集合、同じ FIDELITY_CUTOFF

### 3.2 Run-mode

**運用上の制約 (Render Pro plan は 1 instance)** → 同一プロセス内で 2 cohort を同時 run できない。
代替案 2 つを評価:

| 案 | 内容 | 推奨 |
|---|---|---|
| **Sequential** | 月前半 A、月後半 B (両 cohort 各 14 日) | × N 不足 |
| **Counterfactual** | 本番は A 固定で運用、B は 7 日毎に counterfactual_replay tool で過去データ再評価し蓄積 | ◎ |
| Live-shadow split | 1 instance で gate 動作させ、現実 promotion は A、bucket-demoted set だけ別に追跡 | △ 妥当性あるが状態管理複雑 |

**推奨**: Counterfactual。理由:
- LIVE/Shadow 状態に副作用を一切残さない
- 同じ time window で完全 paired 比較が可能
- gate config を変えての sensitivity analysis も追加 cost ゼロ

### 3.3 期間と通貨

- 期間: **2026-05-XX 〜 2026-06-XX (約 1 ヶ月)**
- 通貨ペア: USD_JPY / EUR_USD / GBP_USD / GBP_JPY / EUR_JPY / AUD_USD (主要 6)
- 戦略: 全 Shadow 戦略 (H1_GRANDFATHERED_LIVE 以外)

---

## 4. 評価指標

### 4.1 一次指標 (success criteria)

| 指標 | 期待 | 失敗閾値 |
|---|---|---|
| **false demote rate** = (B で demote / A でも promote 候補ありえた cell 数) | < 20% | ≥ 20% |
| **bb_rsi_reversion / USD_JPY** が demote されない | 0 | > 0 cells demoted |
| **post-promote 1-week EV** (B promote 戦略) | ≥ A の post-promote EV | B が A − 0.5 pip 以上低下 |

### 4.2 二次指標 (品質モニタ)

- Wilson lo 違反率 (post-promote 戦略)
- Bonferroni 有意 cell 検出数 (B で発見できる新エッジ)
- promote → demote 復帰サイクル数 (短期発振の指標)
- 4-bucket vs 24-bucket sensitivity (audit-only で並走計測)

### 4.3 探索指標 (将来検討)

- bucket × instrument cross-effects (例: USD_JPY/A_00-05 と EUR_USD/A_00-05 の相関)
- bucket transition の time-of-day 分布 (週末跨ぎ等のエッジ効果)

---

## 5. 監視と運用

### 5.1 Daily report

毎日 04:00 UTC に `tools/h1_counterfactual_replay.py` を cron で実行:

```bash
python3 tools/h1_counterfactual_replay.py \
  --source render \
  --bucket-mode 4_bucket \
  --output knowledge-base/raw/h1_ab_daily_$(date -u +%Y-%m-%d).md
```

- 出力は KB の `raw/h1_ab_daily_YYYY-MM-DD.md` に保存
- 前日 diff を `raw/h1_ab_daily_diff_YYYY-MM-DD.md` に出力 (実装は別タスク)

### 5.2 Weekly summary

毎週月曜に手動で:
- 一次指標を表で要約
- 失敗閾値超過があれば即座に gate 設計再検討
- 4-bucket vs 24-bucket の counterfactual を比較

### 5.3 Stop conditions

以下のいずれかが発生したら **即座に B treatment を中止し A に戻す**:

1. LIVE 戦略の demote 検出 (grandfather 防御失敗 = 設計欠陥)
2. false demote rate > 30%
3. Codex 独立レビュー (5/7 schedule task) で重大欠陥指摘
4. ユーザーから明示的中止指示

---

## 6. 完了基準と次フェーズ

### 6.1 完了 (success)

下記全てを満たせば LIVE tier への適用検討に進む (grandfather 解除は別議論):

1. ✓ false demote rate < 20%
2. ✓ post-promote 戦略の WF 安定性が A 以上
3. ✓ Codex 独立レビュー passed
4. ✓ 4-bucket と 24-bucket counterfactual 結果に大きな矛盾なし

### 6.2 改善 (partial)

下記のうち 1 つでも該当すれば gate 設計再調整:

- false demote rate 20-30%: thresholds 緩和 (e.g., `H1_BUCKET_WILSON_MIN=0.35`)
- 特定 bucket で false demote 集中: bucket boundary 再設計 (3-bucket / 6-bucket 試行)
- 特定戦略で過剰 demote: 戦略別 grandfather 拡張

### 6.3 棄却 (failure)

下記のいずれかなら本設計を棄却 (Wave 1 audit と整合する別アプローチへ):

- LIVE 戦略の grandfather が機能しない (実装バグ)
- Counterfactual で再現性なし (時期・データ依存)
- promote 戦略の post-promote EV が A より大幅劣化

---

## 7. 関連

- 親プラン: `/Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md`
- 設計書: `wiki/learning/h1-hour-bucket-design-2026-05-03.md`
- Wave 1 audit: `wiki/learning/h1-spread-time-audit-2026-05-03.md`
- Counterfactual 結果: `raw/h1_counterfactual_dryrun_2026-05-03.md`
- Codex schedule (5/7): obs#827
- Memory 整合: `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`,
  `feedback_live_shadow_separation`, `feedback_check_orphan_local_app`

---

**rule:R1** (Slow & Strict — 新フィルタは 365 日 BT or Live N≥30 + Bonferroni + Pre-reg LOCK 必須)
- 365 日 BT: counterfactual replay tool で実施可能 (Render dump の date range 拡張)
- Live N≥30: 4-bucket grouping により USD_JPY/bb_rsi の最大 bucket で N=80+ 達成見込み
- Bonferroni: z=3.29 (52 strategy × 4 bucket = 208 比較相当を考慮)
- Pre-reg LOCK: 本ドキュメント自体が pre-registration となる。期間中の閾値変更は禁止
