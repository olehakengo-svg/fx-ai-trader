# SR Strength Audit Pre-registration

```yaml
hypothesis:
  H0: "SR strength と LIVE/Shadow EV は無相関 (cohort 内共通)"
  H1: "strength>=0.7 cell の EV > strength<0.5 cell (片側 Welch、cohort 別)"

primary_cohort:
  strategies:
    - dual_sr_bounce
    - sr_anti_hunt_bounce
    - dt_sr_channel_reversal
    - strong_sr_breakout
  primary_cell:
    strategy: dual_sr_bounce
    bin: strength>=0.7
    bridge_status: 'sent'
    is_live: 1
    expected_n_30d: 30+
  cells: 12
  multiple_testing:
    method: BH FDR
    q: 0.10
    m: 12
  decision_criteria:
    promote: "Wilson_lo(WR)>0.45 AND PF>=1.20 AND Kelly>=0.10 AND BH-FDR adj p<0.05"
    shadow_keep: "Wilson_lo(WR)>0.40 AND PF>=1.05"
    demote: "それ以外"

exploratory_cohort:
  strategies:
    - sr_channel_reversal
    - sr_fib_confluence
  rationale: |
    R2 で全 cell demote されたが strength 別に分離すると strength>=0.7 cell が
    生き残っている可能性。Shadow N 蓄積を続けて feature 観察、redesign 根拠化。
  cells: 6
  multiple_testing:
    method: BH FDR
    q: 0.10
    m: 6
  decision_criteria:
    redesign_recommend: "strength>=0.7 cell の Wilson_lo(WR)>0.40 AND PF>=1.0"
    graveyard_confirm: "全 cell で Wilson_lo(WR)<0.30"
  prohibitions:
    - "本 cohort 結果のみによる active promote 禁止 (post-hoc bias、demote 後に都合の良い cell を拾う罠)"
    - "primary cohort と合算した m=18 BH FDR 計算禁止 (family 独立)"
    - "redesign_recommend 該当時は spec 書き直し → 新タスク投入 (本 task では実装しない)"

sanity_floor:
  catastrophic_only: "平均 EV 符号反転"

stages:
  stage_0_7d: "primary cell N<5/週なら BLOCKED_DATA = 戦略 dead 扱い、本監査打切り"
  stage_1_30d: "primary cohort 全 cell N>=30 揃うか sanity 確認、足りなければ +30d 延長"
  stage_2_60_90d: "final verdict、両 cohort で BH FDR 補正後判定"

global_prohibitions:
  - "post-hoc cell selection 禁止 (W3-3 S4 / W3-5 で reject 確定済罠)"
  - "primary cell 以外で有意 → 報告は許可、判定根拠としては不可"
  - "stage 完了前の中間 promote 禁止"
  - "exploratory cohort の有意結果を primary cohort に流用禁止"
```
