# Edge Promotion Rubric (satisfied = 全AND / 欠ければ needs_revision か failed)

入口 (shadow 投入) はほぼ素通り — 下記は **LIVE 昇格の出口** 基準。

1. **pre-reg**: 仮説・方向・TF・m・閾値が「検証着手より前に」台帳登録済み (事後登録は failed)
2. **多重検定**: BH-FDR q=0.10 (rolling window) で生存 (累積Bonferroniは使わない)
3. **Walk-Forward**: 登録時の12y履歴で >=3/4 fold directional 正 (shadowのN件は再分割しない)
4. **Wilson_lo >= 0.40** (FDR補正後 / cell単体実測。集約WRは不可。低Nでは自動的に高WRを要求)
5. **friction <= TP10%**
6. **shadow N >= 20** で維持 (= 前向きOOS。BT/40d/TV黒字は昇格根拠にしない)

## 不合格基準 (即 failed)
- 「BTで+EV / 月利達成」だけで満点を付ける
- pre-reg を事後に登録する
- 集約WRで判定する (cell単体でない)
- is_shadow を分離していない

## lot ランプ (LIVE flip時)
- N>=20 -> 1000u (マイクロ) / N>=35 -> 2500u / N>=50 -> 5000u
- 低N (20-34) は自動 demote 高速化: Live N>=5 ∧ EV<0 で撤退 (通常は N>=10)

## 残留リスク (設計上の前提)
N=20 flip は偽陽性を含む (小標本崩壊 [Phase1b 70/1] 型)。これは「防ぐ」のでなく
マイクロlot + 高速demote で「封じ込める」。許容できるのは shadow N が実戦の前向きOOSだから。
