# kalman_d7 min-lot carve-out — R1 pre-reg DRAFT (2026-09-17)
## 前提訂正 + 09-01 LOCK 事後義務の執行 + L1 昇格条件の事前凍結

> **種別**: rule:R1 pre-reg DRAFT (user GO 決裁 2026-09-17 を受けた起案)
> **Status: DRAFT — user 最終承認待ち。§0 の前提監査により、GO brief が想定した「carve-out 新設」のコード diff は既に main に存在する (no-op)。本パケットの実 diff は registry / KB のみで、live コード変更ゼロ**
> 様式: [[d4-implementation-prereg-template-2026-07-16]] (D4 必須 4 項目 + 防御解除ラダー) / 形式前例: [[sweep-reversion-ps1a-decision-packet-DRAFT]] (cell-scoped carve-out packet)

## §0 前提監査 (feedback_audit_past_verdicts 準拠 — 起案 brief の前提 2 点が stale)

GO の根拠 brief ([[live-frequency-and-oanda-status-survival-2026-09-01]] kalman 節: 二重不適格 / live N=0 / ΔN +11-17/月 / テール ¥3,700/月 / 1000u 化 + bypass 追加案) を現 main (commit ec470cfa, 2026-09-17) と突き合わせた:

1. **「二重不適格で live 構造不能」は 2026-09-01 に解消済み。** 同一内容の pre-reg [[kalman-d7-minlot-carveout-prereg-2026-09-01]] が **LOCKED (user 最終承認 2026-09-01「承認・マージ GO」)**、実装は PR #218 で main 着地済み。コード実読で 3 変更すべて確認 (§2.1)。テスト 12 本 (`tests/test_kalman_d7_minlot_carveout.py`) + counterfactual 実施記録あり。
2. **「live N=0」は stale。** 初 live fill **#859468** = 2026-09-10T17:00:51Z USD_JPY BUY 1,000u → 同日 21:04:55Z STOP_LOSS 決済 (hold 4h04m)、**+8.2p (demo) / +¥91 = +9.1p (broker realized、差 0.9p 原因未判定)**。05-28 決裁の SUCCESS 定義 (`oanda_audit is_live=1 AND bridge_status='filled' COUNT>=1`) は**達成済み**。09-01 LOCK の「2026-10-15 まで fill ゼロなら到達性再監査」条項は消滅。
3. **新規の負の事実**: この唯一の fill が **storm 4** (trail SL replacement 16,837 回 / 33,675 tx / 2h51m @3.28 tx/s — 初の非 carry_dip 系 storm、欠陥は戦略共有の trail/bracket 管理層と確定、[[kalman-d7-po-dn-flip]] 09-11/09-14/09-16 節) を誘発した。storm guard 4 点セット (累積 tx breaker / 冪等ガード / 単調性アサート / dead-band) は **demo_trader.py に未実装** (2026-09-17 実読)。
4. **ΔN 実測**: carve-out 着地から 16 日で 1 fill (~2/月) — brief の +11-17/月を大幅に下回る (テール算術は据え置きで安全側、頻度期待は下方修正)。

**∴ 「bypass set に kalman 3 type を追加する」コード diff を再度書くことは no-op (最悪は二重起案事故)。user GO を実質化する非 no-op 内容は §1 の 3 点のみ。**

## §1 目的 (本パケットが決めること)

1. **09-01 LOCK の事後義務の執行**: 初 fill 確認時の R2 registry 期日再武装 (初 fill 2026-09-10 + 90 日 = **2026-12-09**) — LOCK 文書 §R2 が凍結済みの義務で、registry は現在も `deadline: 2026-11-30` のまま**未執行**。
2. **R2 判定 estimand の事前凍結**: `t9-kalman-d7-live-n10-ev-check` の「EV<0」を N=10 到達**前に** broker realized net (JPY→pip 換算) と凍結 — MEMORY `project_t8_week1_gate_breach` = [[ps1a-trigger-estimand-audit-2026-09-16]] (ps1a、2026-09-16: gross/net 不一致でトリガ成立が丸ごと無効化) の教訓の水平展開。初 fill で既に gross/net 0.9p 乖離を実測済み。
3. **拡張凍結 (storm 条件)**: storm guard 4 点セットが main 着地しテストで pin されるまで、kalman の lot 増額 (L1)・variant/pair 拡張のいかなる R1 起案も凍結。

**非目標 (変更しないこと)**: エッジ主張 (シグナル / SL / TP / 発火条件)、lot (1000u 契約)、bypass set メンバーシップ、OOS 凍結データへの再接触、storm guard の実装そのもの (別 R3 修理 PR の管轄) — すべて本パケット外。

## §2 変更内容 (diff レベル)

### §2.1 コード: **変更ゼロ** (no-op 確認 — 現 main の実装位置)
| 09-01 LOCK の変更 | 実装位置 (`modules/demo_trader.py`) | pin |
|---|---|---|
| ① MIN lot 契約 1000u | L94 `KALMAN_D7_MIN_UNITS = 1000` / L7227-7237 `_tick_entry` 上書き (`_sentinel_reason="KALMAN_D7_MIN_LOT"`) | `test_tick_entry_has_min_lot_block_and_flat_shield` |
| ② FLAT 上書き遮断 | L7275-7277 `and entry_type not in self._KALMAN_D7_LIVE_OVERRIDE` (`OANDA_FORCE_FLAT_UNITS` 条件節) | 同上 |
| ③ bypass set 追加 | L10568-10570 (`_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` 内)、上限 L10572 `_AGG_KELLY_GATE_MINLOT_MAX_UNITS = 1000`、判定 L10593-10599 (`eligible ∧ 0<units≤1000` — lot 昇格で bypass 自動失効) | `test_kalman_in_agg_kelly_bypass_frozenset` ほか計 6 関数 |

3 type の SSOT は L9978-9982 `_KALMAN_D7_LIVE_OVERRIDE`。instrument 制限 (USD_JPY) は L10047-10058 `_kalman_d7_live_eligible`。撤退経路 = env `KALMAN_D7_LIVE_ENABLE=0` のみで即時 (既存テスト pin)。

### §2.2 registry (唯一の実 diff): `knowledge-base/wiki/decisions/prereg-trigger-registry.json`
- `t9-kalman-d7-live-n10-ev-check`: `"deadline": "2026-11-30"` → **`"2026-12-09"`** (初 fill 2026-09-10 + 90 日)。
- message 追記: 「初 fill #859468 (2026-09-10) 確認・+90d 再武装 2026-09-17 執行。EV 判定 estimand = broker realized net (JPY→pip 換算)、demo pnl_pips (gross) との混用禁止」。

### §2.3 KB 追記 (同一コミット、KB 運用ルール準拠)
- [[kalman-d7-minlot-carveout-prereg-2026-09-01]] に追記節: 初 fill 実測 (到達性確認 ①〜③ の消込)、期日再武装の執行記録、storm 4 caveat。
- 本 DRAFT を `wiki/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md` として保存し、user 承認で LOCK 昇格。

## §3 凍結する成功・撤退基準 (D4 項目 ii/iii)

**09-01 LOCK から継承 (変更なし)**:
- **R2 自動降格**: LIVE N≥10 (`oanda_trade_id != ''`、3 variant prefix 合算、USD_JPY) 到達時 **EV<0 → live 停止** (env `KALMAN_D7_LIVE_ENABLE=0`、即時・裁量なし)。
- **即時 user review**: 連続 3 SL (3 variant 合算)。
- **判定はセル単位・TRUE_LIVE のみ** (is_shadow=0 単独禁止、shadow/demo 残差の混入禁止 — Live vs Shadow 厳格分離)。

**本パケットで追加凍結**:
- **期間**: deadline **2026-12-09**。到達時 N<10 なら stale review (T5 教訓: 監視主体併設) — その場で EV 判定せず、頻度前提 (~2/月実測) の再監査を先行。
- **EV estimand**: **broker realized (JPY) の pip 換算 net** を正とする。demo `pnl_pips` (gross mid-fill) は参考値。gross/net の混用・途中変更禁止 (ps1a 教訓の pin)。
- **L1 (5000u) 昇格条件の事前凍結** ([[lot-ladder-template-2026-08]] 準拠。1000u = **L0** 段): 起案権発生 = **G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster SL 0 件)** + `tools/lot_ladder_calc.py` の Wilson_lo > BEV_WR ゲート (手計算禁止)。一括承認・飛び級禁止。⚠️ 構造的注意: 本セルは BT WR 23.91% の payoff 型 (W/L 12.3×) で **G3 の WR≥35% に構造的に届かない可能性が高い** — その場合のテンプレ凍結値改定は独立の R1 であり、本パケットは先取りしない。
- **storm 拡張凍結**: storm guard 4 点セット (累積 tx breaker → 冪等ガード → 単調性アサート → dead-band、[[kalman-d7-po-dn-flip]] 09-16 訂正版の直交セット) が main 着地しテスト pin されるまで、L1 起案・variant/pair 拡張・`KALMAN_D7_MIN_UNITS` 変更を全て凍結。

## §4 テール算術 (09-01 導出の再検証 + 更新)
- 1,000u 固定 / SL 1.5×ATR / 8 月 H1 ATR 中央値 14.5p → **≈¥217/trade**。全敗仮定 +11-17 fill/月 → **月次テール ≈¥3,700** (09-01 LOCK 値、上限として据え置き)。
- 実測更新: ~2 fill/月 → 実測ベース月次テール ≈**¥434** (全敗仮定)。実現 +¥91。5000u FLAT 時代比リスク 1/5 は不変。NAV 床 ¥250k バッファ (¥28k) への寄与は無視可能水準。
- ⚠️ **金銭外テール**: storm 型 tx 負荷 (storm 4 = 33,675 tx、直接 PnL ¥0)。OANDA Gold status / REST アクセス存続 ([[live-frequency-and-oanda-status-survival-2026-09-01]]: 9 月は keeper が $520k/$500k 到達済み (2026-09-17 実測) だが条件は毎月) に対する broker 側リスクで、§3 の拡張凍結が本パケットで取れる唯一の緩和策 (guard 実装は別 R3)。

## §5 監視読み手 (D4: pre-reg には監視主体を必ず併設)
| 層 | 読み手 | 内容 |
|---|---|---|
| binding (セル) | registry `t9-kalman-d7-live-n10-ev-check` (`tools/prereg_trigger_watch.py`, live_count_decision, n_decide=10) | §3 R2 判定。期日 2026-12-09 |
| info (発火) | registry `t9-kalman-d7-fire-info` (shadow_count_info, 期待 3.9/週) | 分子ゼロ時は Render `[kalman_d7] QUALBAR` 行と突合 |
| class 層 | registry `hourblock-class-exempt-r2-rollback` ([HOURBLOCK_CLASS_EXEMPT] marker 付き pooled N≥10) | kalman fill も母集団に入る (§6-2) |
| broker 層 | status_volume_keeper / OANDA status watch | Gold $500k / 残高床 ¥250k |
| **欠落 (提案・別 R3 PR)** | storm 検知器なし — OANDA transactions の replacement レート/累積カウンタの読み手 | 現状 storm 検知は事後の人手トレースのみ (検知器ゼロ状態、write-only 以前) |

## §6 リスクと相互作用 (起案時明示)
1. **二重起案事故**: 本 GO をコード変更として執行すると no-op PR か 09-01 LOCK と矛盾する二重凍結。§0 前提訂正の承認が最初の決裁事項。
2. **hourblock class exemption との同一実体**: `_STATIC_HOURBLOCK_CLASS_EXEMPT = _AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` (L10591 alias、`tests/test_hourblock_class_exemption.py` が identity を pin)。kalman の低 WR payoff 形状は class rollback ゲート (pooled N≥10 EV<0) を負側に引っ張りやすく、成立すると既存 9 セル (carry_dip / sweep / vix / weekend_gap / price_shock ×5) を巻き込んで免除撤去。set からの除去は identity テスト 2 本の同時更新必須。
3. **agg-Kelly gate 母集団への流入**: kalman fill は clean live 累積 (固定 cutoff 2026-04-16〜) に入り gate 値 (-0.315〜-0.374) / rolling Kelly (+0.256) の組成を変える。payoff 型ゆえ初期は負寄与が先行しやすい — gate 悪化を見たら組成効果を先に疑う。
4. **estimand 未凍結のまま N=10 到達** = ps1a と同型の判定不能化 → §3 で凍結。
5. **頻度乖離**: brief の ΔN +11-17/月を M1 算数 (必要 N=385 の短縮) に引用しない。実測 ~2/月。
6. **BT 前提と実走 exit の乖離**: 初 fill は 4h04m SL 決済 (BT edge は ~115h winner ride 依存) + 宣言に存在しない trail 挙動が実走。exit 実装監査 (別タスク) 完了まで promo_wr/promo_ev (N=1) を判断に使わない。
   - **2026-09-25 追記 (rule:R3、PR #299)**: exit 実装監査の結論 — 乖離は**決定論的な仕様非同期**。live は `MAX_HOLD_SEC["daytrade"]=8h` (override 無し) + 金曜 21:45Z 全クローズで、宣言 480 bars (~120h) の保持を構造的に再現できない (勝ち側のみ censoring)。処置分岐は [[kalman-d7-po-dn-flip]] 09-24 節 / registry `kalman-d7-live-exit-spec-mismatch-disposition` (期日 10-08)。宣言通りの保持を live に入れるのは Rule 1 (user 決裁)。

## §7 user 最終承認欄 (承認で凍結する事項)
1. [ ] §0 前提訂正の承認 — 2026-09-17 GO は 09-01 LOCK により**既に充足済み**と認定 (新規コード変更なし)
2. [ ] §2.2 registry 期日再武装 (2026-11-30 → 2026-12-09) + message 追記の執行
3. [ ] §3 EV estimand = broker realized net の凍結 (gross/net 混用禁止)
4. [ ] §3 storm 拡張凍結 (guard 4 点セット main 着地まで L1 / variant / pair の R1 起案禁止)
5. [ ] 本 DRAFT の `wiki/decisions/` 保存 + LOCK 昇格

承認: user ________ / 日付 ________ / rule:R1

