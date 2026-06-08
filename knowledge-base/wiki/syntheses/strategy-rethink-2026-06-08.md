# 戦略再構築 — 「低 friction 高 TF risk-premia」仮説の検証後 (2026-06-08)

司令塔の判断 doc。3脈 (TSMOM / Price-Shock / Carry) を実装・検証した結果と、過去全監査を突き合わせて方針を再接地する。

## 今日の仮説と結果

**仮説** (雑談監査発): 負けの真因は gross EV≈0 × friction × 規律 override。→ 低 friction (高 TF・広 TP・メジャー) に絞り、経済的根拠ある少数 pre-reg で Bonferroni を生き残る。

**結果**:
- **TSMOM (本命)**: NULL。**gross からエッジ無し** (ann 寄与 −0.0005)。高 TF でも risk-premia が立たない。真因 = ①2016-26 は trend premium 圧縮レジーム ②USD 集中 54% で「分散」が単一方向ベットに縮退。
- **Price-Shock**: BT エッジは本物だが production は **1%-percentile shock の設計通りの希少さ**で N が数ヶ月単位でしか貯まらない。近道無し。
- **Carry**: 未着手。

## 仮説のどこが間違っていたか

**「低 friction = 長保有・高 TF」と等値した**のが誤り。TSMOM は月次リバランス＝**ultra-low friction なのに負けた**。理由: edge-per-trade がゼロだったから。

→ **friction は二次の税。一次は edge-per-trade (WR × payoff)。**
- TSMOM: 高TF・低friction・**低WR (月次~46%)** → friction 中立でもエッジ無し → 負け
- orb_trap|GBP_USD|SELL: intraday・**高WR (.783) / PF 13.6** → friction 払っても圧勝
- Price-Shock LONG: 3-12 bar 保有・**高WR (.64-.73)** → エッジが friction を超える

gross EV≈0 の正体は「friction が高い」ではなく「**エッジの無い cell を大量に張っている**」。修正は「保有を伸ばす」ではなく「**エッジのある narrow cell だけ張る**」。

## 勝っているものの共通項 (システム全体を俯瞰)

OOS でプラスを示した / 全ゲートを通った数少ない例:
- **ZZ Pivot v60**: M15 MR-at-trend-extreme、単一ペア、1年 OOS PF 1.222 / +$57。LIVE 1.0x 稼働中。
- **orb_trap|GBP_USD|SELL**: session breakout-trap、単一 cell、WR.783/PF13.6/Wilson.581/Bonf.420/Kelly.725/**WF3-3 全通過**、**唯一の障害が N<30** ([[project_tp_hit_12cell_portfolio_2026_06_05]])。
- **cfd ORB SHORT** (SPX500): N=22 WR68.2% Wilson≈.487。orb_trap と**独立に ORB-short エッジを示唆** = 相互検証で prior 上昇 ([[project_cfd_trader_p3w1_orb_2026_05_11]])。
- **Price-Shock LONG** 5 cell: downside-shock reversion、BT robust。

共通項: **narrow・conditional・高WR・明確な行動メカニズム (overreaction / liquidity / session 構造)**。**広い factor premia ではない。** リテール規模では学術 factor (TSMOM/carry) は harvest できないが、**特定のマイクロ構造オーバーリアクションは exploit できる**。

## 再接地した方針

> **探索 (新 premia 発掘) から、検証済 narrow edge の集約 (N 蓄積) へ軸足を移す。**

全監査を通じた **真の binding constraint は「エッジが無い」ではなく「検証済エッジの N が足りない」**。orb_trap|GBP_USD|SELL がその純粋例 (設計欠陥ゼロ、N<30 だけ)。ならば最高 EV の行動は exploration ではなく:

1. **検証済 narrow edge を shadow で N≥30 まで素直に育てる** (orb_trap GBP_USD SELL / Price-Shock LONG / ORB SHORT family)
2. **それらを equal-risk で portfolio 化** — TP-HIT で平均ペア相関 −0.006 = 理想分散を実証済。decorrelated narrow edge の束が単一エッジより Calmar 高い (3.32→4.54)。
3. **W4-EDA の REDESIGN_QUEUE / 各種 NULL の再探索は凍結** — 91% design-broken の修理や Bonferroni 全滅 grid は ROI が低い。

## 期待値の再アンカー (CLAUDE.md 目標との整合)

CLAUDE.md は月利100%を掲げるが、TP-HIT 検証で**月利100%は証拠金4×NAV＋ruin63%で数学的に不可能、現実上限~21.6% (Bonferroni後)**と確定済。再構築方針はこの現実上限に整合 — narrow edge portfolio の複利を Kelly-half で回すのが算数的に正しい上限への道。

## 次アクション候補 (実装は別ターン)

- (A) orb_trap|GBP_USD|SELL の現 Shadow N を確認 → N≥30 までの ramp 計画 + ORB SHORT (cfd) との独立性確認
- (B) 「検証済 narrow edge portfolio」tracker を作り、equal-risk weight で運用 (corr matrix 更新)
- (C) Carry は保留 (TSMOM NULL を見るに factor premia 系の prior が下がった)

## 関連
- [[project_risk_premia_pivot_2026_06_08]] / [[project_cell_edge_deep_audit_2026_06_08]] / [[project_tp_hit_12cell_portfolio_2026_06_05]]
- [[feedback_size_lever_beats_skip_filter]] (narrow edge の loser-zone は SIZE lever で活かす)
- [[feedback_partial_quant_trap]] / [[feedback_audit_purpose_design_not_n]]
