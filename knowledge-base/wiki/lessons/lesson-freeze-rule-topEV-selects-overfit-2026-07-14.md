# 教訓: 探索→OOS の「凍結規則 top-by-EV」は最も過学習したセルを選ぶ (2026-07-14)

**出典**: WS3 round-3 cross-asset divergence-reversion [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8

## 何が起きたか
discovery で選抜規則 (EV_ft>0 ∧ IC<0 ∧ N≥30) を満たした 47 セルから、pre-reg 実装は **first-touch EV 降順 top-8** を凍結した。結果:
- 凍結 8 のうち 5 が `GBP_JPY W=120 z=2.5` の near-duplicate。探索窓 (2024-02〜2025-06) の 2024-08 円 carry-unwind レジームで EV が amplify されたクラスタ。
- OOS (2025-07〜2026-05、post-unwind) で **8/8 が反転** (EV −0.7〜−7.4)、PASS=0。
- ところが凍結対象外だった `EUR_USD` / `EUR_JPY` の best-per-pair セルは OOS でも正 EV + 機構整合 IC を維持 (post-hoc・claimable 不可)。

## 教訓
**探索窓の raw EV は regime-amplified で、凍結指標として脆弱。** raw EV 最大のセルは「たまたま探索窓のレジームに最も適合した = 最も過学習した」セルであることが多く、top-by-EV freeze はそれを優先的に拾う。真に頑健なシグナル (EUR ペア) は raw EV が中位で freeze に入らず取り逃す。

## 次からの適用
探索→OOS の候補凍結では、raw EV 単独ランクを避け、以下のいずれかを併用する:
- **pair / パラメータ分散** を強制 (best-per-pair や best-per-(W,z) を優先)
- **fold 間 IC 安定性** (探索窓を時間分割し IC 符号が一貫するセルを優先)
- **exploration Sharpe / EV-per-vol** (regime-amplified な絶対 EV でなくリスク調整後)

freeze 規則自体を pre-reg に明記し、raw EV ランクだけに委ねない。関連: [[lesson-cell-audit-bt-required-2026-04-27]] (cell 分割の選択バイアス) / stage-2 の first-touch sequencing 反転 [[ws3-stage2-barrier-ev-prereg-2026-07-09]]。
