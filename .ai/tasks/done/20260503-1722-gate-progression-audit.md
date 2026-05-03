---
id: 20260503-1722-gate-progression-audit
title: Gate 1→2 進行判断のための Aggregate Kelly + MC 破産確率 現状監査
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T17:22:00+0900
roadmap_gate: Gate 1 → Gate 2 進行判断 (lot 0.3x → 0.5x → 月利100%)
rule: R1
parent_session: fizzy-patterson (Wave 3)
---

## 0. なぜ今このタスクか (司令塔判断)

queue には Wave 3 並列 3 本 (W3-4 C-1 London / W3-5 S3 pair-pool FDR / A2-alt simple-structure scalp pre-reg) が積まれているが、**いずれも個別戦略の BT/pre-reg 実装** であり、**集計レベル (aggregate Kelly / MC 破産確率) で Gate 進行判断ができる状態に無い**。

CLAUDE.md「月利100% → 全ての施策提案はこの目標への寄与度で優先順位を判断」、roadmap v2.1 §Gate 1: 「Aggregate Kelly > 0 → DD 0.2x → 0.3x」、§Gate 2: 「Kelly>0.05, PnL>+50pip, 破産<70% → ★月利100%」の **進行判断の前提となる現状指標** が未測定。

並列 3 本の BT verdict が出る前に、**現状の集計レベル baseline** を確定させることで:
- Wave 3 Tier 2 で promote 候補が出た時、portfolio 加算の影響を即時評価可能
- H-1 PR #16 の A/B 並走開始時 (5/4) の baseline として使える
- Gate 進行 / 維持 / 戻しの **数値判定ライン** を pre-registered で確定できる (cherry-pick 防止)

---

## 1. 仮説

**H1**: 現状 LIVE 戦略 (`is_shadow=0`) の aggregate Kelly が `> 0.05` かつ MC 60d 破産確率 < 70% なら、Gate 1 → Gate 2 移行 (lot 0.3x → 0.5x) の前提条件が揃う。

**H2**: aggregate Kelly が 0 〜 0.05 の borderline なら、Wave 3 Tier 2 BT 完了 + H-1 hour-bucket A/B 結果 (6/4) を待ってから再評価。

**H3**: aggregate Kelly が < 0 なら、どの cell (戦略 × pair × hour-bucket) が aggregate を引き下げているか特定し、R2 降格候補リストを作成する必要がある (Gate 0 退避検討)。

---

## 2. 対象データ + データ分離

### 一次ソース (必須)
- **Render API `/api/demo/trades`** — `is_shadow=0`, `outcome in (WIN, LOSS, BREAKEVEN)`, `pnl_pips != null`, `status=CLOSED`
- 期間: Live 開始日 〜 監査実行日 (Live 開始日は Render から最古 `is_shadow=0` レコードで特定)

### 二次ソース (検証用)
- `/api/risk/dashboard` — VaR/CVaR/Kelly/MC/DSR が既に算出済。**本タスクで独立計算し、値が一致するか確認**
- `oanda_audit` テーブル — `bridge_status='filled'` のみで実約定確認 (`reference_oanda_audit_twin_meaning`)

### 補助 (比較目的のみ)
- `raw/bt-results/bt-365d-2026-04-27.json` (post-gate-chain v9.3) — Live と乖離していないか比較

### データ分離 (絶対遵守)
| データ | 用途 | 集計に混ぜる? |
|--------|------|--------------|
| `is_shadow=0` (LIVE) | aggregate Kelly / MC / 集計 PF | ✅ メイン |
| `is_shadow=1` (Shadow) | 比較参照のみ | ❌ 厳禁 (`feedback_live_shadow_separation`) |
| BT post-gate-chain v9.3 | BT-Live 乖離検出 | ❌ Kelly 計算には使わない |
| OANDA `bridge_status='sent'` | 戦略名解決のみ | ❌ 実約定でない |
| OANDA `bridge_status='filled'` | 実約定確認 | ✅ Live N の sanity check |

---

## 3. 統計条件 (matrix v1 整合 + Gate 進行用追加軸)

### 戦略別 + 集計の必須測定軸
| 軸 | 戦略別 | 集計 | 必達閾値 |
|----|-------|------|---------|
| N (Live trades) | ✓ | ✓ | 集計 N ≥ 30 (測定可能性最低) |
| WR | ✓ | ✓ | (情報) |
| **Wilson 95% lo (WR)** | ✓ | ✓ | 集計 > 0.45 |
| EV (mean pnl_pips) | ✓ | ✓ | 集計 > 0 |
| **t-stat one-side p** | ✓ | ✓ | 集計 < 0.10 |
| PF | ✓ | ✓ | 集計 > 1.0 |
| **Aggregate Kelly** (Live ベース) | ✓ | ✓ | 集計 > 0 (Gate 1) / > 0.05 (Gate 2) |
| **MC 60d 破産確率** | — | ✓ | < 70% (Gate 2) |
| **Bonferroni p (m=戦略数)** | ✓ | — | 戦略別では情報のみ |
| max DD (期間内) | ✓ | ✓ | 集計 < 30% (Live) |
| Sharpe (annualized, 1trade base) | ✓ | ✓ | 集計 > 0 |
| DSR (if computable) | — | ✓ | (情報) |

### MC simulation 仕様
- iterations: 1000
- horizon: 60 day
- Kelly fraction: 現状 Live 推定値
- bootstrap source: Live trades distribution (戦略別 weighted)
- **look-ahead bias なし**: 各 trade の outcome を resample のみ
- runtime: 30 分以内

---

## 4. 採用 / 保留 / 棄却 条件 (pre-registered)

### ACCEPT (Gate 1 → Gate 2 移行可)
**全条件 AND**:
- aggregate Kelly > **0.05**
- MC 60d 破産確率 < **70%**
- Live aggregate N ≥ **100**
- Wilson 95% lo (集計 WR) > **0.50**
- aggregate EV > **0**
- aggregate PF > **1.0**
- max DD (期間内) < **30%**

→ **lot 0.3x → 0.5x 増加の根拠** として `wiki/decisions/gate-progression-audit-2026-05-03.md` 内に PR テンプレート添付。

### NEEDS_MORE_EVIDENCE (Gate 1 維持、再監査待ち)
- aggregate Kelly が `0 ≤ Kelly ≤ 0.05` (borderline)
- OR Live aggregate N < 100
- OR MC 破産 70-90%
- OR Wilson lo (WR) 0.45-0.50

→ **次回監査トリガー**: H-1 PR #16 マージ後の A/B 1ヶ月並走完了 (~6/4) または Wave 3 Tier 2 verdict 揃い時。本監査ではアクション無し。

### REJECT (Gate 0 戻し検討)
- aggregate Kelly < 0
- OR MC 破産 > 90%
- OR aggregate EV < 0 + Wilson lo (WR) < 0.45

→ **R2 降格候補リスト作成**: aggregate を引き下げている戦略 × pair × hour-bucket cell を Wilson lo / EV / Kelly で降順 sort、最下位 cell を `entry_type='strategy_X' AND instrument='Y' AND hour_bucket='Z'` 単位で停止候補リスト化。OANDA 転送停止 (lot=0) は **司令塔承認待ち** (Codex は提案のみ)。

---

## 5. 月利 100% ロードマップ寄与

| シナリオ | Gate 進行 | 月利寄与 |
|---------|----------|---------|
| ACCEPT | Gate 1 → Gate 2 (lot 0.3x → 0.5x) | **+67% lot → +67% PnL 直接寄与** |
| NEEDS_MORE_EVIDENCE | Gate 1 維持 | 0% (但し Tier 2 verdict 待ち時間の可視化) |
| REJECT | Gate 0 退避検討 + R2 降格 | -損失停止寄与 (aggregate 改善) |

いずれの結果も roadmap v2.1 進行判断の根拠となる。**ACCEPT 時のみ月利100% ロードマップ加速**、それ以外は **構造健全性の維持** に寄与。

---

## 6. 受け入れ条件 (Codex 完了基準)

完了条件 (すべて AND):

1. ✅ レポート `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` 生成 (日本語)
2. ✅ 戦略別表: WR / Wilson lo / EV / PF / Kelly / N / max DD / Sharpe / Bonferroni p
3. ✅ 集計表 (aggregate): 同上 7 軸 + MC 破産確率 + DSR
4. ✅ ACCEPT/NEEDS_MORE_EVIDENCE/REJECT verdict 1 件 + 数値根拠
5. ✅ `/api/risk/dashboard` の Kelly/MC と本タスク独立計算の **値一致確認** (誤差 ±5% 内)
6. ✅ ACCEPT 時: lot 増加 PR テンプレート添付 (`feat/gate-2-lot-increase-2026-05-03` ブランチ案)
7. ✅ NEEDS_MORE_EVIDENCE 時: 不足 N 戦略リスト + 次回監査日付提案
8. ✅ REJECT 時: R2 降格候補リスト (戦略×pair×bucket cell, EV/Kelly 降順)
9. ✅ Wave 3 Tier 2 promote 候補が将来加算された場合の portfolio 影響シミュレーション (S2 Shadow を Live 化した場合の Kelly/MC 変化)
10. ✅ `feedback_check_orphan_local_app` 整合: 分析前 `pgrep -f app.py` で 0 件確認

---

## 7. 検証コマンド

```bash
# Step 1: ローカル app.py orphan 検知 (絶対先行)
pgrep -f app.py
# → 0 件確認、もし起動していたら kill してから再開

# Step 2: 一次データ取得
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' \
  -o /tmp/live-trades-$(date +%Y%m%d).json

# Step 3: risk dashboard 取得 (検証用)
curl -s 'https://fx-ai-trader.onrender.com/api/risk/dashboard' \
  -o /tmp/risk-dashboard-$(date +%Y%m%d).json

# Step 4: 監査スクリプト実行
python3 tools/gate_progression_audit.py \
  --trades /tmp/live-trades-$(date +%Y%m%d).json \
  --risk /tmp/risk-dashboard-$(date +%Y%m%d).json \
  --output knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md \
  --mc-iterations 1000 \
  --mc-horizon 60

# Step 5: verdict 表示
grep -E "^(ACCEPT|NEEDS_MORE_EVIDENCE|REJECT):" \
  knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md

# Step 6: risk dashboard との独立計算一致確認
python3 -c "
import json
risk = json.load(open('/tmp/risk-dashboard-$(date +%Y%m%d).json'))
print(f'API Kelly: {risk[\"kelly_fraction\"]:.4f}')
print(f'API MC ruin (60d): {risk[\"mc_ruin_60d\"]:.4f}')
"
# → 監査レポート内の独立計算値と ±5% 内なら OK
```

---

## 8. 禁止事項 (絶対遵守)

| 禁止 | 理由 |
|------|------|
| **本番 DB 書き込み** | 監査タスクは read-only |
| **`.env` の編集・読み取り** | OANDA API key / Render secret 露出禁止 |
| **OANDA API への取引リクエスト** | 監査中に意図しないトレード発火を防ぐ |
| **既存未コミット変更の破棄** | `git stash` 経由でも禁止。レビュー責任は司令塔 |
| **`is_shadow=0/1` の混在集計** | `feedback_live_shadow_separation` 違反 |
| **BT 数値での Kelly 上書き** | BT-Live 乖離があるため、Live ベースのみ採用 |
| **MC iterations < 1000** | 統計的信頼性確保 |
| **`oanda_audit.entry_type='sent'` での実約定集計** | `reference_oanda_audit_twin_meaning` 違反、`filled` 必須 |
| **ローカル DB (`demo_trades.db`) 単独での集計** | `feedback_check_orphan_local_app` 違反、Render 一次必須 |
| **Codex 単独での lot 変更コミット** | 監査結果を司令塔承認後に別 PR で実施 |

---

## 9. 関連 KB / memory

### 内部 memory 必須整合
- `feedback_partial_quant_trap`: 本タスクは集計レベルで PF / Wilson / Kelly / Bonferroni / DSR すべて測定
- `feedback_live_shadow_separation`: is_shadow=0/1 厳格分離
- `feedback_cohort_time_check`: 戦略別 demote/promote 履歴の時系列整合 (現状 LIVE と過去 Live を取り違えない)
- `feedback_check_orphan_local_app`: 分析前 `pgrep -f app.py` で 0 件確認
- `feedback_label_empirical_audit`: コード演繹ではなく実測ラベル × WR/EV
- `feedback_quant_first`: 監査 → 判断 → (司令塔承認) → 実装 PR の順序厳守
- `reference_oanda_audit_twin_meaning`: `bridge_status='sent'` (戦略名) と `'filled'` (MODE 名) の二義性を集計前に分離
- `feedback_claude_codex_division`: 監査実装は Codex、verdict 判断と PR 承認は Claude 司令塔
- `project_w3_2_s2_verdict_pre_reg`: S2 portfolio 加算シミュレーション時の参照点
- `project_w3_1_h1_gate_done_2026_05_03`: H-1 hour-bucket gate 投入後の cell 集計に対応

### 関連 KB
- 親ロードマップ: `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Gate 0/1/2/3/4 定義)
- リスク dashboard 仕様: `modules/risk_analytics.py` (VaR/CVaR/Kelly/MC/DSR)
- BT-Live 乖離: `wiki/analyses/bt-live-divergence.md` (6 つの構造的楽観バイアス)
- Verdict matrix v1 (司令塔参照): `/Users/jg-n-012/test/wiki/learning/verdict-threshold-matrix-v1-2026-05-03.md`
- Codex review (Wave 1): `/Users/jg-n-012/test/wiki/learning/codex-review-wave1-2026-05-03.md`

---

## 10. 報告 (Codex → Claude 司令塔)

完了時、Codex は本タスクの最終 verdict (ACCEPT / NEEDS_MORE_EVIDENCE / REJECT) を 1 行サマリ + 数値で日本語報告。司令塔は受領後:
- ACCEPT → lot 増加 PR を別タスクとして spawn (rule:R1)
- NEEDS_MORE_EVIDENCE → 監査結果を Wave 3 Tier 2 verdict 表に統合、次回監査日付確定
- REJECT → R2 降格候補リストを別タスクで個別判断 (cell 単位、`feedback_ma_filter_breaks_mr` の罠を再発させないため事前 cell 単独実測必須)
