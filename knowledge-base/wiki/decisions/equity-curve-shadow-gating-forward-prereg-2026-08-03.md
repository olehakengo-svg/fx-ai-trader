# 🔒 Pre-registration LOCK: #22 equity_curve_shadow_gating — 観測前 forward-completing pre-reg (wave-6 EA-b、rule:R1 登録アクション)

**🔒 LOCKED 2026-08-03 (self-LOCK) — 以降、estimand・K grid・閾値・null 仕様・eligibility・trigger の変更禁止。本コミットは登録アクションのみで測定ゼロ (BH/wave スロット非消費)。執行 = first look trigger 発火時 (データ cutoff 2027-05-06 / verdict 2027-05-13、registry 機械監視)。**

**起案日**: 2026-08-03
**起点**: [[ea-landscape-sweep-2026-07-31]] §4.2 (testable form 凍結元、GO score 55) / [[hypothesis-catalog-2026-07-24]] #22 (queued 2026-07-31 → 本日 LOCKED-FORWARD)
**様式踏襲**: [[e12-volume-forward-prereg-2026-07-29]] (forward 型 / P-10 計算 ban / registry 機械監視) / [[mof-intervention-forward-prereg-2026-07-24]]
**承認**: user ミッション委任 (2026-07-08) + 探索最大化指示 (2026-07-24) に基づく純研究。**live パラメータ・コード・shadow 構成の変更ゼロ**。live gate 化は verdict PASS 後に stage-2 別 pre-reg + Rule 1 全段 + user 最終承認。
**規範仕様 (normative)**: `knowledge-base/raw/analysis/equity-curve-shadow-gating-prereg-draft-2026-08-03.json` — 全凍結パラメータ・手続きの一次定義。本文書はガバナンスの要約。齟齬時は JSON が正。

---

## 0. なぜ「本日単一実行」でなく forward 化か (在庫調査の帰結)

セル在庫調査 (2026-08-03、`raw/analysis/ec-gating-cell-inventory-2026-08-03.json`):

- 本番 shadow book の全長 = **4.04 ヶ月** (最古 closed exit 2026-04-02 = Fidelity Cutoff と同一 epoch)。purge/retention 機構なし = append-only。
- §4.2 凍結 eligibility (**closed shadow N≥300 かつ span 12-18 ヶ月**) を満たすセル = **0**。§4.2 はデータ既存を暗黙仮定していたが、事実と矛盾 (KB 仮定の訂正)。
- N≥300 のみなら 5 セル存在するが、うち 3 (ema_trend_scalp×USD_JPY/EUR_USD、bb_rsi_reversion×USD_JPY) は**運用者が drawdown を見て emission 停止した censored series** — その上で equity-curve gating を測るのは条件付けの自己言及。
- **span 床を緩めて本日実行する案は棄却** (凍結の事後緩和 / censored 循環 / 単一レジーム / 単一クリーンショットの焼却 — JSON s0 参照)。「不成立クローズ」より、**分析パラメータ無変更のまま執行時点だけを繰り延べる forward 化**が優位 (登録コスト ~0、スロット非消費、他ライン E7/E1/E12 と並走)。

**forward-completing の正直な開示**: E12 の純 forward と異なり、first look window の ~4 ヶ月分は LOCK 時点で既実現 (R2 alert の 30d 集計として観測済み)。観測前性の根拠 = 分析パラメータが 2026-07-31 に内部データ非接触で凍結済み (候補選択 DoF ゼロ) + gate 条件付き量は誰も未計算 (attestation) + 本 LOCK で計算 ban 発効。

## 1. 敵対的検証の解決マップ

独立 subagent による敵対的検証 (`raw/analysis/ec-gating-adversarial-verification-2026-08-03.md`): **verdict = SURVIVES-WITH-REQUIRED-AMENDMENTS (KILL 欠陥なし)**。REQUIRED #1-#8 全反映 + OPTIONAL 5 件採用:

| # | 指摘 | 解決 (JSON 節) |
|---|---|---|
| 1 | cutoff 導出の算数破綻 (自称機械規則が期日を再生産しない) | s5 — cutoff = epoch 2026-04-08 + 28d + 365d = **2027-05-06** に修復 (検算一致) |
| 2 | null 再連結未特定 / block 長頑健性欠如 / 保有 ≪1日 仮定の暗黙性 | s4 — 再連結規則 1 文凍結、knife-edge (4) = 7 日 block permutation p<2×α_bonf、s3 — eligibility に p95 hold ≤24h 追加 |
| 3 | censoring 独立性主張が解析的に誤り | s6 — 撤回し「生存条件付けは交換可能性を破るがバイアスは uplift 押し下げ = H1 に保守的」に置換 |
| 4 | P-10 ban が本番モニタと初日から衝突する広さ | s7 — 禁止対象を gate 条件付き統計に限定列挙、R2 alert / watchdog / risk dashboard (live book のみ、`risk_analytics.py:532-544` 確認) / quant-eval を名指し whitelist |
| 5 | attestation 不足 + scratchpad 生 P&L 残置 | s7 — R2 alert cron を反復クラスとして列挙 (2026-05-07〜、349 回、`tools/shadow_promote_r2_alert.py`)、quant-eval 07-31 追加、**生抽出は LOCK 前に削除済み** |
| 6 | 台帳ハード条件 (exit-free / headroom 10x) からの無断逸脱 | s9 — 適用除外差分節を新設 (estimand が配分 counterfactual であるための非適用) |
| 7 | 「E12/MoF 同型」の過大主張 | s0 — forward-completing と正確に呼称し既実現 ~30% を開示 |
| 8 | registry 完全形 + demote 執行形態の記録義務 | s5 — doc/message 付き 2 エントリ、staleness review scope に demote 形態 (env 除去 vs registry) 追加 |

## 2. 凍結 testable form (§4.2 無変更 — 要約、正は JSON s2-s4)

- **データ**: Render 本番 `/api/demo/trades?status=closed` 全量。フィルタ = is_shadow=1 / pnl_pips NOT NULL / dedup_violation≠1 / XAU 除外 / hold≥5s。セル = entry_type×instrument (生文字列、改名系列の合成禁止)。pnl_net = 記録値そのまま。執行時抽出は sha256 凍結。
- **eligibility (cutoff 時機械評価)**: window 548d 内 N≥300 ∧ span≥365d ∧ p95 hold≤24h。
- **gate**: トレード i の直近 K 件 (exit < entry(i)、real-time・オーバーラップ排除) の pnl 合計 > 0。**K∈{5,10,20} のみ、閾値 0 固定**。
- **統計量**: uplift = mean(pnl_net|gate_on) − mean(pnl_net|all)。**null** = within-cell 日ブロック置換 (n_perm 5000、seed 20260803、再連結規則凍結)。片側 p、add-one。
- **Bonferroni**: m = eligible セル数 × 3。α_bonf = 0.05/m。degenerate 組も m に算入 (保守)。
- **PASS** = ≥1 (cell,K) で uplift>0 ∧ p<α_bonf ∧ knife-edge 4 点 (隣接 K 整合 / top-1 除去 / 時間半割両半 ≥0 / 7 日 block p<2×α_bonf)。
- **FAIL** = 上記ゼロ → family クローズ、trailing-window 自己 P&L gating 全変種の再試行禁止。

## 3. スケジュールと分岐 (registry 機械監視)

| 期日 | イベント | registry id |
|---|---|---|
| 2027-01-15 | 陳腐化 review (メタデータのみ、demote 執行形態記録) | `ec-gating-prereg-staleness-review` |
| **2027-05-06** | first look データ cutoff (= epoch + 28d + 365d、機械導出) | — |
| **2027-05-13** | first look verdict 期日 | `ec-gating-first-look-deadline` |
| (PASS 時) 2027-08-04 | OOS cutoff (cutoff 後 90d shadow forward、PASS 組のみ m_oos) | verdict 時に登録 |
| (eligible<2 時) 2027-11-06 | UNDERPOWERED-BLOCKED re-arm (1 回限り) | verdict 時に登録 |

- 期日前執行 = peeking として禁止。eligible 予測 = 3-7 セル (demote シナリオ依存、敵対的検証 F の独自検算で下方修正済み)。堅い 3 = session_time_bias×GBP_USD/×EUR_USD、dual_sr_bounce×EUR_JPY。
- **P-10 計算 ban (LOCK〜first look)**: セル別 trailing-K (または <90d rolling) の gate 条件付き P&L 統計・uplift 型対比・gate 状態系列の計算を全主体に禁止。既存運用モニタは名指し whitelist で継続 (JSON s7)。

## 4. 交絡遮断 (§4.2 必須項目 — 正は JSON s6)

- **live 転送交絡**: 測定は shadow book 内 counterfactual 対比のみ — watchdog/R2 の live 転送変更は構造的に非混入。
- **emission gap**: gate は real-time 定義で gap を跨いで参照。gap 分布は verdict に記録 + >7d 跨ぎ除外感度を secondary 併記。
- **生存条件付け**: 交換可能性を破るがバイアスは保守方向 (uplift 押し下げ) — type-I 保持、power 犠牲。verdict 解釈節に固定転記。
- **既存 one-sided 機構との差分**: 本 gate は対称・事前登録・counterfactual。R2 損失停止/watchdog は片側・恒久・ad hoc の先行実装であり、二重ゲート交絡は「既存機構は gap/censoring 経路としてのみ影響」で遮断。

## 5. 除外・禁止

- live パラメータ・コード・shadow 構成・Kelly・tier の変更ゼロ (全工程)。**PASS ≠ edge claim ≠ live 昇格** — live gate 化は stage-2 R1 + user 承認。
- LOCK 後の設計変更・verdict 後の再計算・grid 拡張禁止 (exit-repair §7 拘束と同文)。
- 台帳ハード条件 (exit-free 固定ホライズン / headroom≥10x) は estimand 非適用 — 差分節 JSON s9。
- LOCKED 4 本 (E1/E7/E12/MoF) 非接触 (shadow book 内部 P&L のみ)。並列アクティブ枠 #21+#22 = 2/3。
