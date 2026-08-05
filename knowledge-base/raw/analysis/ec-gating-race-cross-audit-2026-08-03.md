# #22 equity_curve_shadow_gating — 並行セッション race の記録と独立検証 cross-audit (2026-08-03)

> **status: 非規範 (archival)。#22 の SSOT は main 着地済みの [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] (v2 forward、🔒 LOCKED 2026-08-03、first look 2026-11-06)。本文書はそれに対するいかなる変更・挑戦でもない。**

## 1. 何が起きたか (race timeline)

- 本セッション (worktree sharp-pike) は台帳 #22 の explore pre-reg を起案: セル在庫調査 → DRAFT (`equity-curve-shadow-gating-prereg-draft-2026-08-03.json`) → 敵対的検証 subagent (SURVIVES-W-AMENDMENTS #1-#8) → LOCK 文書ローカルコミットまで実施。
- push 前の `HEAD..origin/main` 確認 (T4/T12/T13 教訓の手続き) で、**並行セッションが同日中に #22 の v1 起案 → 敵対的検証 KILL → v2 forward 転換 → LOCK を PR #155 で main に着地済み**であることを検出。
- **first-to-main 原則により並行セッション版が SSOT**。本セッションの LOCK 文書・registry 2 エントリ・台帳行更新は撤回 (本コミットで除去)。競合 LOCK の並立 = 同一 family への二重 pre-reg であり規律違反のため。

## 2. 独立収束 — corroboration としての価値

完全に独立な 2 セッション (互いの作業を見ずに同日実施) が、同一の一次ソース (ea-landscape-sweep §4.2) から出発して**同じ構造的結論**に到達した:

| 論点 | 本セッション | 並行セッション (SSOT) |
|---|---|---|
| §4.2 の遡及 explore は実行可能か | **不可** — 凍結 eligibility (N≥300×12-18mo) の充足セル 0 (shadow book 全長 4.04mo) | **不可** — 敵対的検証 3 レンズで v1 KILL |
| 遡及窓の致命傷 | 運用者 drawdown 停止による censored series 3/5 = 条件付けの自己言及 + 単一レジーム | outcome-conditioned truncation (retired 6/10 セル) + **構造ブレーク偽陽性 100% の合成データ実証** + 週層化では識別不能 |
| 帰結 | forward 化 (E12/MoF 前例) | forward 化 (同前例、明示引用一致) |
| 遡及窓の扱い | 未測定のまま温存 | 未測定のまま保存 (burn なし) — 一致 |

独立再現は「遡及 explore 不成立」という判定自体の頑健性を裏付ける。#22 の verdict 解釈時に引用可。

## 3. Cross-audit (a): SSOT v2 が本セッション案より強い点 — 敗着の記録

- **K1 (構造ブレーク偽陽性) は本セッション案にも刺さっていた**: 本案の primary null (window 全長 548d の day-block permutation) は、deploy 由来の一度きりの水準シフトを「持続性」として拾う。knife-edge の 7d-block permutation・時間半割 (両半 ≥0) でも純粋 step ケースは素通りし得る (step 側半分のみ uplift 正、平坦半分は ≈0 で「≥0」を通過)。**SSOT v2 の epoch 層化 permutation (deploy commit 由来の epoch 境界を git 履歴から機械導出し、層内シャッフルで水準シフトを null 側に保存) が構造的に正しい解**。本セッションの敵対的検証はこの攻撃を発見できなかった (C 節は drift への anti-conservative を指摘し 7d-block を追加させたが、step 型 artifact の合成データ実証までは行っていない)。
- **estimand の正直化**: v2 の「改善源泉は持続性+市場ドリフトの合成でよい (gate は実運用で両方収穫する)、除外すべきは engine artifact のみ」という切り分けは、本案の「regime 持続性」フレーミングより実運用 estimand として誠実。
- **first look の速さ**: v2 は forward 13 週 (2026-11-06) で、本案の 2027-05-06 より 6 ヶ月早い。§4.2 の N≥300 eligibility を維持した本案は「凍結忠実性」を買う代わりに時間を失っていた。

## 4. Cross-audit (b): SSOT v2 と sweep §4.2 凍結 form の差分 — on-record 化 (挑戦ではない)

将来 §4.2 を一次ソースとして読む者のため、v2 LOCK が凍結 testable form から乖離した点を中立に記録する (v2 §10 は v1 KILL の開示は十分だが、以下の §4.2 デルタの明示列挙はない):

1. **primary 統計量**: §4.2 = `uplift = mean(pnl_net|gate_on) − mean(pnl_net|all)` / v2 = `contrast = mean(pnl|state>0) − mean(pnl|state≤0)` (on vs **off**)。on-vs-off は on-vs-all より希釈が少なく検定として強い方向の変更 (悪化ではない) だが、凍結式の変更ではある。
2. **eligibility**: §4.2 = 各セル closed shadow N≥300・12-18 ヶ月 / v2 = active 4 セル名指し + forward N≥150 (13 週)。遡及前提の KILL に伴う置換であり、v2 の敵対的検証がその根拠。
3. **Bonferroni**: §4.2 の「セル数×3」の式は維持 (4×3=12) — 一致。
4. 本セッション案は 1. と 2. を凍結どおり維持していた (代償は §3 の通り first look 2027-05 と null の脆弱性)。

結論: 乖離はいずれも v2 側の敵対的検証で正当化される範囲であり、挑戦事由なし。ただし §4.2 を「凍結」と呼ぶ際の射程 (分析パラメータは維持されたが、統計量の定義と eligibility は置換された) はここに記録しておく。

## 5. P-10 整合の attestation (本セッション分)

SSOT v2 の P-10 ban =「first look まで gate×outcome ジョイント計算全面禁止 (蓄積センサス件数のみ可)」。本セッションの接触履歴:

- セル在庫調査 (2026-08-03): `/api/demo/trades` 全量取得 (15,008 行、per-trade pnl_pips 込み) → セル別 **N / first_exit / last_exit / span のみ**集計。trailing-K・gate 状態・gate 条件付き量・uplift/contrast は**一切未計算**。census 成果物 = `ec-gating-cell-inventory-2026-08-03.json` (メタデータのみ、敵対的検証 subagent が P&L 非含有を実査確認)。
- 生トレード抽出 (P&L 込み) は本セッションの敵対的検証 REQUIRED #5(iii) に従い **LOCK 前に scratchpad から削除済み** — v2 ban との整合維持に流用される。
- 敵対的検証 subagent: 文書読解 + メタデータ算術のみ。
- → **v2 の P-10 ban に対する違反なし**。first look (2026-11-06) までこの規律は全セッションが維持すること。

## 6. 残す成果物と処分

| 成果物 | 処分 |
|---|---|
| `ec-gating-cell-inventory-2026-08-03.json` (228 セル census、メタデータのみ) | **残置** — shadow book epoch (2026-04-02、purge なし append-only) の一次記録。v2 の将来 review でも有用 |
| `equity-curve-shadow-gating-prereg-draft-2026-08-03.json` | **SUPERSEDED-NEVER-LOCKED として残置** (ヘッダ書換済) — 独立収束の証跡 |
| `ec-gating-adversarial-verification-2026-08-03.md` | 同上残置 — superseded 案への検証だが REQUIRED #1-#8 の論点 (cutoff 算数一致・null 再連結仕様・censoring 保守性の解析・P-10 whitelist 設計) は v2 の first look 執行時にも参照価値 |
| 本セッションの LOCK 文書 (wiki/decisions/) + registry 2 エントリ + 台帳行更新 | **撤回・除去** — 競合 LOCK の並立防止 |

## 7. 教訓

- **台帳 item の pre-reg 作業は、着手宣言を main に先行コミットするか、起案前に同日並行ブランチ (`git branch -r` + PR 一覧) を確認する**。`HEAD..origin/main` 確認は push 前で機能したが (競合 LOCK の main 着地は防げた)、6 時間分の重複作業は防げなかった。台帳の「アクティブ 3 本」ルールに「着手 claim の main 先行記録」を足すのが構造解。
- 敵対的検証は合成データ実証 (偽陽性率の数値実測) まで踏むと、文書レビュー型では届かない欠陥 (K1 型) を検出できる — 次回 pre-reg 検証の水準として採用すべき。
