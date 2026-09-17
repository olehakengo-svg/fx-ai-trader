# P-S1(a) Option C (retire) 決裁 — sweep_reversion_eurgbp_late 退役 (2026-09-17)

**Status**: ✅ FINAL — user 決裁 2026-09-17「推奨で進めて」(= [[ps1a-trigger-estimand-audit-2026-09-16]] §7 の二択で **(a) Option C = retire** を採択)
**Rule**: R2 (降格/退役 = Fast & Reactive)。live 露出ゼロのため出血停止の緊急性はなく、user 決裁成立に基づく整理執行
**対象**: `sweep_reversion_eurgbp_late` (T8 DEFER → P-S1(a) 執行トリガ)

---

## 1. 決裁内容

- **Option C = retire を採択** — 執行トリガ (`t8-sweep-defer-decision`) を恒久終了。Option B (live 昇格) は永久に執行しない
- **shadow rescue (`_GBP_ASIA_SHADOW_RESCUE_CELLS`) は残置** — runbook §6-3 の残置選択肢を採用。4原則#3 (Shadow データ蓄積は削らない) と整合し、コストゼロで regime 反転時の将来検証余地を残す。**modules/ 側コードは不変**
- **score_gate shadow rescue の決裁 (forensic #2 §8-2) は自動的に不要化** ([[ps1a-trigger-estimand-audit-2026-09-16]] §7-2 の規定どおり)
- draft branch `draft/ps1a-option-b-20260731` は退役に伴い obsolete (マージ禁止のまま放置可、削除は任意)

## 2. 根拠 (EV 実測、監査 2026-09-16)

| 量 | 値 |
|---|---|
| unique N (dedup_violation!=1) | 10 (2026-09-14 到達) |
| gross spaced EV | +2.92 p/t |
| **net spaced EV (凍結閾値と同 estimand)** | **−3.33 p/t (符号反転)** |
| 摩擦 convention 感度 | 4 通り中 3 通りで負 (唯一正 = spread 1.5p 仮定、10/10 で反証済み) |
| cap 救済集合 | **空** (cap≤5.0p で生存 N=0、breakeven 7.72p でも net −2.35) |
| 研究エッジ再現率 | 38% (監査 §5) |
| live 露出 | ゼロ (18 行全て is_shadow=1、oanda_trade_id 空) |

摩擦前提 (研究 grid の spread 1.5p) が LATE ロールオーバー実勢 5.4〜16.6p で全観測反証。cap で正 EV 部分集合を残す経路も空。よって監査推奨 (a) を採択。

## 3. 執行項目 (本コミット)

1. ✅ registry `t8-sweep-defer-decision` → `active: false` + resolution 記録 (runbook §6-1)
2. ✅ 戦略カード + 決裁パケット + runbook に retire FINAL 追記 (runbook §6-2)
3. ✅ `tools/ps1a_execution_check.py` — CLI/fetch 層で恒久 verdict `OPTION_C_RETIRED_USER` を返す (凍結文言リプレイの純関数 `evaluate()` は歴史記録として不変、test pin 温存)
4. ✅ scheduled task `ps1a-sweep-trigger-executor` を無効化 (マージ後に実施、SKILL.md は残置)
5. ✅ MEMORY `project_t8_week1_gate_breach` を resolved 化

## 4. 残す監視

- shadow rescue 残置により `daytrade_eurgbp` の shadow 行は蓄積継続。**ただし読み手となる registry/トリガは存在しない** — 将来 regime 反転を検証したい場合は新規 pre-reg (Rule 1) を起こすこと (本カードが唯一のポインタ)
- 執行形態の再設計 (指値・LATE 窓外への移動等 = 監査 §7 の選択肢 (b)) は**採択しない**が、禁止もしない。再挑戦は同型再試行禁止 lesson 群 (`zz_pivot`/`range_fade` 等) と同じく、新規 family として estimand を net で設計すること

## 5. 関連

- [[ps1a-trigger-estimand-audit-2026-09-16]] (§3 cap menu 空 / §7 決裁事項)
- [[sweep-reversion-ps1a-decision-packet-DRAFT]] / [[sweep-reversion-ps1a-execution-runbook-2026-07-31]] (§6 Option C 経路)
- [[sweep-zero-fire-forensic-2026-09-14]] (breakeven 7.72p 導出)
- MEMORY: `project_t8_week1_gate_breach` / `project_ps_capture_estimand_disjoint_2026_09_09` (BT 由来 EV を live 期待値に使うな)
