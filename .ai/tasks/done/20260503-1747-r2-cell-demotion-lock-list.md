---
id: 20260503-1747-r2-cell-demotion-lock-list
title: R2 cell-level 降格候補 LOCK list — aggregate Kelly<0 復帰のための cell 単位 STOP_OANDA / LOT_HALF 提案
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T17:47:00+0900
roadmap_gate: Gate 0 復帰 (aggregate Kelly < 0 → ≥ 0、生存条件)
rule: R2
parent_session: fizzy-patterson (Wave 3)
prerequisite_audit: 20260503-1722-gate-progression-audit (REJECT verdict, raw Kelly=-0.17, MC破産=100%)
---

## 0. なぜ今このタスクか (司令塔判断)

直前の Gate Progression Audit (`20260503-1722-gate-progression-audit`) で **REJECT verdict** が確定:

- aggregate raw Kelly = **-0.1737** (clipped 0)
- MC 60d 破産確率 = **100%**
- aggregate WR=38.60%, EV=-0.79 pip, PF=0.695, max DD=74.80%
- Live N=917 (2026-04-02 〜 2026-05-01, 約 30 日)

主犯は **既存 Tier 1 LIVE / PAIR_PROMOTED 戦略** が aggregate を引き下げている構造:
- bb_rsi_reversion: N=324 (aggregate の 35%), EV=-0.15, raw Kelly=-0.05
- fib_reversal: N=97, EV=-0.44
- macdh_reversal: N=62, EV=-0.90
- vol_surge_detector: N=47, EV=-0.19
- sr_fib_confluence: N=36, EV=-1.78
- sr_channel_reversal: N=34, EV=-0.71

**個別新戦略を増やす (Wave 3 Tier 2 BT) より、既存 LIVE の負け cell を切るほうが aggregate 改善 EV が圧倒的に高い**。これが現状の最短 Gate 0 復帰経路。

ロードマップ寄与: **Gate 0 復帰 (aggregate Kelly < 0 → ≥ 0) → Gate 1 進入再挑戦 → Gate 2 月利100%**。

CLAUDE.md「攻撃は最大の防御」と「クリーンデータ蓄積が最優先」の整合: 負け cell を切るのは攻撃の妨げを除く前向きアクション、cell 単位なので Bonferroni-significant な edge は誤って切らない。

---

## 1. 仮説

**H1**: aggregate raw Kelly = -0.17 を引き下げている cell 上位 ~10-20 件 (worst EV / raw Kelly 降順) を OANDA 転送停止または lot 半減した場合、aggregate raw Kelly が **0.0 以上** に復帰する。

**H2**: 切る対象は **(strategy × instrument × hour_bucket)** の cell 単位であり、戦略全体ではない。これにより:
- `feedback_ma_filter_breaks_mr` の罠回避 (戦略全停止で Bonferroni-significant cell を巻き添えにしない)
- bb_rsi_reversion (N=324) のような大規模戦略でも、負け hour-bucket だけ切って残りを温存できる

**H3**: 切った cell のシミュレーション (counterfactual) で aggregate Kelly が改善し、かつ MC 破産確率が < 90% に下がるなら、Gate 0 復帰の前提条件が揃う。

---

## 2. 対象データ + データ分離

### 一次ソース (再取得不要 — Audit と同じ snapshot を使う)
- **`/tmp/live-trades-20260503.json`** (Audit task で生成済、`render-demo-trades-20260503.db` 由来)
- **直前 Audit 出力** `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` の §"R2降格候補 cell" を起点とする (30 cell 出力済)
- **必要なら** `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` を再 query (Render API DNS が解決できれば最新化推奨)

### データ分離 (Audit と同一基準、絶対遵守)
- LIVE: `is_shadow=0`, `status=CLOSED`, `outcome in (WIN, LOSS, BREAKEVEN)`, `pnl_pips != null`
- XAU除外: `instrument NOT LIKE 'XAU%'`
- Shadow (3930 件): **集計に混ぜない** (counterfactual シミュ時の baseline 比較のみ)
- BT 結果: 比較参照のみ (R2 判定には使わない、Live 実測ベース)

---

## 3. 統計条件

### Cell 単位の必須測定軸
各 (strategy, instrument, hour_bucket) cell について:
| 軸 | 測定対象 | 用途 |
|----|---------|------|
| N (cell-level) | 各 cell | 信頼性最低条件 (N≥5 でカウント) |
| WR + Wilson 95% lo | 各 cell | 確率下限 |
| EV (mean pnl_pips) | 各 cell | 損益期待値 |
| **raw Kelly** | 各 cell | clip しない値 (negative も可視化) |
| total pip (cell 内累積) | 各 cell | aggregate への寄与 |
| PF | 各 cell | profit factor |
| Bonferroni p (m=cell数) | 各 cell | 多重検定補正 |
| Sharpe (annualized) | 各 cell | (情報) |
| max DD (cell 内, period 内) | 各 cell | (情報) |

### Aggregate counterfactual
- 提案 cell リスト適用後の aggregate を **再計算**:
  - aggregate N (停止 cell の trades を除外)
  - aggregate Kelly (raw + clipped)
  - MC 60d 破産確率 (1000 sim)
  - aggregate EV / Wilson lo / PF / max DD

### Bonferroni 母数 m の固定 (pre-reg LOCK)
- m = **本タスクで評価する全 cell 数** (Audit report で出力された 30 cell + 追加採掘 cell の合計)
- 事前に m を確定し、α' = 0.05 / m を pre-registered LOCK
- 事後の m 動かしは禁止

---

## 4. 採用 / 保留 / 棄却 条件 (pre-registered LOCK)

### STOP_OANDA (R2 即停止候補、最強)
**全条件 AND**:
- N ≥ **5**
- EV < **-2.0 pip/trade**
- Wilson 95% lo (WR) < **0.30**
- raw Kelly < **-0.5**
- total pip (cell 内累積) < **-15.0 pip**

→ 該当 cell の OANDA 転送設定で **lot=0 (転送停止)**。Shadow 集計は継続 (データ蓄積のため)。

### LOT_HALF (lot 半減候補、中強度)
**全条件 AND** (STOP_OANDA に該当しない場合のみ):
- N ≥ **10**
- EV < **-0.5 pip/trade**
- Wilson 95% lo (WR) < **0.40**
- raw Kelly < **-0.1**
- total pip < **-5.0 pip**

→ 該当 cell の lot を **現在値 × 0.5** に低下。

### WATCH (現状維持、監視継続)
- N < 5 (信頼性不足)
- OR 上記閾値の境界 (margin ±10%)
- OR Wilson lo / EV のいずれかが positive

→ アクションなし、月次再監査。

### KEEP (positive cell、明示維持)
- EV > 0
- OR Wilson 95% lo (WR) > 0.50
- OR raw Kelly > 0

→ **明示的に R2 対象から除外**。Bonferroni-significant な edge を巻き添えにしないため。

### 必須 counterfactual check
提案リスト適用後の aggregate raw Kelly が **negative のままなら** リストを **拡張** (次の worst cell 追加) → reapply → aggregate ≥ 0 になるまで繰り返す。
**ただし上限 30 cell** (それ以上切ると残り N が小さくなりすぎ統計的にも意味が薄れる)。

---

## 5. 月利 100% ロードマップ寄与

| シナリオ | aggregate 復帰可否 | Gate 進行 |
|---------|-------------------|----------|
| Counterfactual aggregate Kelly ≥ 0 | ✅ Gate 0 復帰 | Gate 1 進入再挑戦可 |
| Counterfactual aggregate Kelly 0 〜 -0.05 | ⚠️ marginal | Tier 1 戦略の構造的見直し必要 (lesson 化) |
| Counterfactual aggregate Kelly < -0.05 | ❌ R2 だけでは不足 | 戦略全停止検討 + lessons 更新 |

ACCEPT (=Counterfactual aggregate ≥ 0) なら **Gate 0 復帰 PR** を別タスクで spawn (rule:R2 OANDA 転送停止)。
NEEDS_MORE_EVIDENCE (=marginal) なら追加 N 蓄積 + 月次再監査。
REJECT (=不足) なら戦略全停止 (PAIR_PROMOTED 等の tier 降格) を別タスクで検討。

---

## 6. 受け入れ条件 (Codex 完了基準)

完了条件 (すべて AND):

1. ✅ レポート `knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md` 生成 (日本語)
2. ✅ STOP_OANDA / LOT_HALF / WATCH / KEEP の 4 区分 cell 表
3. ✅ 各 cell に対し N / WR / Wilson lo / EV / raw Kelly / total pip / Bonferroni p / max DD
4. ✅ Counterfactual aggregate (停止リスト適用後の Kelly / MC / EV / Wilson lo / max DD)
5. ✅ Bonferroni 母数 m を pre-reg LOCK で明示
6. ✅ KEEP cell リスト (Bonferroni-significant 候補 + EV>0 cell) — 司令塔が「誤って切らないか」レビュー可能
7. ✅ 提案 STOP/LOT_HALF cell の OANDA 転送停止 PR テンプレート (`feat/r2-cell-demotion-2026-05-03` ブランチ案)
8. ✅ MC simulation 1000 sim, horizon 60d, baseline と post-cut の比較
9. ✅ `feedback_check_orphan_local_app` 整合: 分析前 `pgrep -f app.py` 確認 (sandbox 制約あれば fallback 明示)
10. ✅ `feedback_ma_filter_breaks_mr` 整合: KEEP cell に Bonferroni-significant な edge があれば明示的に守られていることを確認

---

## 7. 検証コマンド

```bash
# Step 1: 既存 Audit データ確認 (再取得不要)
ls -la /tmp/live-trades-20260503.json
ls -la knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md

# Step 2: ローカル app.py orphan 検知 (sandbox 制限ある場合は明示 fallback)
pgrep -f app.py || echo "sandbox-restricted-fallback"

# Step 3: R2 cell-level 監査スクリプト実行
python3 tools/r2_cell_demotion_audit.py \
  --trades /tmp/live-trades-20260503.json \
  --output knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md \
  --mc-iterations 1000 \
  --mc-horizon 60 \
  --max-cuts 30

# Step 4: counterfactual aggregate 確認
grep -E "^(Counterfactual|Aggregate post-cut):" \
  knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md

# Step 5: STOP_OANDA / LOT_HALF cell 数確認
grep -cE "STOP_OANDA|LOT_HALF" \
  knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md
```

---

## 8. 禁止事項 (絶対遵守)

| 禁止 | 理由 |
|------|------|
| **OANDA API への自動転送停止** | R2 判定提案までで、実 STOP は **司令塔承認後の別 PR** で実施 |
| **lot 設定の自動変更** | 同上、提案リストのみ |
| **戦略全停止 (entry_type 単位)** | 本タスクは **cell 単位** 降格のみ。戦略全停止は別タスクで Tier 降格として個別判断 |
| **本番 DB 書き込み** | Read-only 監査 |
| **`.env` の編集・読み取り** | OANDA API key / Render secret 露出禁止 |
| **既存未コミット変更の破棄** | `git stash` 経由でも禁止 |
| **`is_shadow=0/1` の混在集計** | `feedback_live_shadow_separation` 違反 |
| **BT 数値での R2 判定** | Live 実測ベース必須 |
| **Bonferroni 母数 m の事後変更** | pre-reg LOCK 違反 |
| **KEEP cell を切る** | Bonferroni-significant な edge を破壊する罠 (`feedback_ma_filter_breaks_mr`) |
| **`oanda_audit.entry_type='sent'` での実約定集計** | `reference_oanda_audit_twin_meaning` 違反 |
| **Render mirror snapshot を勝手に更新** | Audit と同一データで cell-level 評価が前提 |

---

## 9. 関連 KB / memory

### 内部 memory 必須整合
- `feedback_partial_quant_trap`: cell 単位で PF / Wilson / Kelly / Bonferroni すべて測定
- `feedback_live_shadow_separation`: is_shadow=0 厳格集計
- `feedback_cohort_time_check`: hour_bucket 軸での分離が demote/promote 履歴と整合
- `feedback_check_orphan_local_app`: 分析前 `pgrep -f app.py`
- `feedback_label_empirical_audit`: コード演繹ではなく実測 cell × WR
- `feedback_ma_filter_breaks_mr`: Bonferroni-significant cell を巻き添えにしない
- `feedback_quant_first`: 監査 → 判断 → (司令塔承認) → 実装 PR の順序
- `feedback_claude_codex_division`: cell 評価実装は Codex、最終 STOP_OANDA 承認は Claude 司令塔
- `project_w3_1_h1_gate_done_2026_05_03`: H-1 hour-bucket gate と整合 (4-bucket grouping default 推奨)
- `project_w3_2_s2_verdict_pre_reg`: S2 は KEEP 対象 (Shadow only でまだ Live 影響なし)

### 関連 KB
- 直前の Audit: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` (R2 候補 30 cell リスト)
- 親ロードマップ: `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Gate 0/1/2)
- BT-Live 乖離: `wiki/analyses/bt-live-divergence.md` (構造的楽観バイアス)
- Verdict matrix v1: `/Users/jg-n-012/test/wiki/learning/verdict-threshold-matrix-v1-2026-05-03.md`
- Tier-master: `knowledge-base/wiki/tier-master.md` (現状 ELITE_LIVE / PAIR_PROMOTED 状態)

---

## 10. 報告 (Codex → Claude 司令塔)

完了時、Codex は以下 1 行サマリ + 数値で日本語報告:

```
Counterfactual: aggregate raw Kelly={baseline}→{post-cut}, MC60d={baseline}→{post-cut}, STOP_OANDA={N}件, LOT_HALF={N}件, KEEP={N}件
Verdict: {ACCEPT_GATE_0_RECOVERY | NEEDS_MORE_CUTS | REJECT_INSUFFICIENT}
```

司令塔は受領後:
- ACCEPT_GATE_0_RECOVERY → 提案リストの最終承認 + OANDA 転送停止 PR を別タスクで spawn (rule:R2)
- NEEDS_MORE_CUTS → max_cuts を緩和 (30 → 50) して再実行
- REJECT_INSUFFICIENT → 戦略全停止 (Tier 降格) を別タスクで個別判断
