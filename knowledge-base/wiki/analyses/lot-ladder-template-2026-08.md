# ロット階段 R1 パケット標準テンプレ — 2026-08 事前凍結 (rule:R3)

- **Status**: 🔒 テンプレ凍結 (2026-08-05)。live 変更ゼロ — 本書は**手続きの標準化**であり、いかなるセルのロットも変更しない
- **根拠決裁**: セル・ポートフォリオ論 user 合意 2026-08-05 (執行項目② = テンプレ事前凍結) / [[track-c-capital-plumbing-decision-packet-2026-07-28]] D-d (解除ラダー原則) / [[shortest-path-decision-memo-2026-07-10]] D4 (実装 pre-reg 必須項目)
- **計算ツール**: `tools/lot_ladder_calc.py` (本書 §3〜§5 の全数値を機械生成 — パケット起案時は手計算禁止)
- **適用の入口**: セルが **G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster SL 0 件)** に到達 → R1 起案権が発生 (自動増額なし)。第 1 候補 = weekend_gap_fade (§9)

---

## §0 設計原則 (Asymmetric Agility の適用)

| 方向 | Rule | 手続き |
|---|---|---|
| **昇格 (rung-up)** | **R1** (Slow & Strict) | 段ごとに本テンプレでパケット新規起案 → user 最終承認 (SLA 48h)。**一括承認・自動昇格は禁止** (G3 は「起案権」であり増額ではない) |
| **降格 (rung-down)** | **R2** (Fast & Reactive) | §6 の条件成立で**自動・即時** (code 強制、人手判断を挟まない) |
| **テンプレ改定** | R1 | 本書の凍結値 (§4 制約定数 / §5 ゲート閾値 / §6 降格閾値) の変更は R1 + user 承認 |

- エッジの統計的証拠 (Bonferroni/OOS verdict) は**セル昇格時に既に確定済み** — ロット階段パケットは凍結 OOS に再接触しない (各セルの §8 再接触禁止条項を尊重)。階段が新たに検証するのは **(i) live での EV 持続 (累積 N)** と **(ii) サイズ増加時の執行品質 (at-rung N)** の 2 つだけ
- 台帳は **broker 実約定 (`oanda_trade_id != ''`) の JPY 建て**のみ (D-a/D-e 原則 — pip 台帳・shadow 混入・demo 残差は使用禁止)

## §1 標準階段 (rung 定義)

| rung | units | 位置づけ |
|---|---|---|
| **L0** | 1,000u | ベース (sentinel/min-lot 契約と同水準)。G3 到達までの既定値 |
| **L1** | 5,000u | 第 1 増額 (5×)。D-d 承認済みの 2 段ラダー上限と一致 |
| **L2** | 10,000u | 第 2 増額 (2×)。clean live 期の歴代最大 lot と同水準 |
| **L3** | 30,000u | 目標水準 (3×) — セル・ポートフォリオ論の +11〜16%/月 算数の前提 lot |

- **1 段ずつ**。L0→L2 の飛び級は禁止 (at-rung 執行品質データが存在しないため)
- 既存 `modules/edge_cell_promote.py` の `LADDER_LOTS = {1:5000, 2:7500, 3:10000}` は旧世代の段割り — **第 1 適用 R1 で本標準 (1000/5000/10000/30000) へ改定する** (それまで code 変更なし)
- **L3 は現行 code 制約と衝突する** (§4.5 exposure 20k cap)。L3 パケットは exposure cap 改定決裁を必ず同梱

## §2 入力仕様 (パケットの根拠数値 — 全て live 実績から)

| 入力 | 定義 | 出典 |
|---|---|---|
| N (累積) | live 執行済みイベント数 (`oanda_trade_id != ''`)。cap skip / no-fill / インフラ障害は分母外 (wg 前例の分母規律) | oanda_trades join |
| N (at-rung) | 現 rung での live 執行数 (rung 変更後にリセット) | 同上 + rung 履歴 |
| mean, σ | per-event 実現 pips (stressed-net = 実測 RT 摩擦込み) | 同上 |
| WR, avg_win, avg_loss | 勝率と条件付き平均 (pips、avg_loss は正の大きさ) | 同上 |
| disaster 件数 | `close_reason="disaster_sl"` 件数 (累積 / at-rung 別掲) | demo rows flag |
| slippage 系列 | OANDA 実 fill vs signal_price (`record_fill_slippage` 永続値) | bridge 実測 |
| セル DD 寄与 | ladder baseline からのセル単体 JPY 累積 DD (broker realized) | JPY 台帳 |
| NAV | パケット起案時点の実 NAV (JPY) | OANDA account |
| 頻度 | events/月 (live 分母基準) | 実測 |

## §3 Kelly 導出 (サイジングの理論上限)

1. **Kelly fraction**: 本番実装 `modules.risk_analytics.kelly_fraction(WR, avg_win, avg_loss)` をそのまま使う (BT⇄本番の式同期原則 — 別式の再実装禁止)。**採用値は half-Kelly** (実装の `recommendation` と一致)
2. **units 換算** (f = half-Kelly, v = JPY/pip per 1000u):
   - 平常損失基底: `U_avg = f × NAV / (avg_loss × v) × 1000`
   - 破滅損失基底: `U_dis = f × NAV / (disaster_SL_pips × v) × 1000`
   - **Kelly 上限 = min(U_avg, U_dis)** — disaster SL が広いセルでは U_dis が桁で小さくなる (wg: 150p → §9)
3. **EV 下限ゲート (D-d 拘束)**: `Wilson_lo(WR, N) > BEV_WR = avg_loss / (avg_win + avg_loss)` ⟺ 凍結 payoff 下で EV 下限 > 0。payoff を固定した WR のみの区間推定であり、payoff 自体の推定誤差は覆わない — 診断として normal 下限 `mean − 1.96σ/√N` も併記する (ゲートには使わない: 小 N で過度に保守的)
4. **N_required**: 現在の (WR, payoff) が持続すると仮定した場合にゲートが開く最小 N をツールが逆算する。**G3 (N=30) 到達 ≠ ゲート開通** — 例: WR55% / payoff 1.5 のセルは N=41 まで L1 昇格不可。パケット verdict が HOLD の場合は必ず N_required を明記する

## §4 リスク制約 (推奨 rung = 全上限の min)

推奨 units = **min(次 rung, U_avg, U_dis, U_cellDD, U_margin, U_exposure)**。パケットには **binding constraint (どれが縛ったか)** を明記する。

| # | 制約 | 凍結値 | 定義 |
|---|---|---|---|
| 4.1 | Kelly 上限 | half-Kelly | §3.2 の min(U_avg, U_dis) |
| 4.2 | **セル単体 worst-case イベント損失** | **≤ 2.5% NAV** | `disaster_SL_pips × v × units/1000 ≤ 0.025 × NAV`。1 イベントの最大損失を NAV 比で拘束 |
| 4.3 | **セル単体 DD 予算** | **≤ 2% NAV** | MC 検証 (§5) と降格 D2/D3 (§6) の予算。DD_LOT_TIERS の第 1 段 (2%) にネスト |
| 4.4 | **証拠金使用率** | **worst-case 同時 ≤ 40% NAV** | レバレッジ 25x。`Σ(同時最大発火セルの notional_JPY) / 25 ≤ 0.40 × NAV`。multi-pair セル (wg の 3 ペア同時) は全ペア同時発火で評価 |
| 4.5 | **exposure cap (code)** | net 20,000u/通貨・同方向 3 件 | `modules/exposure_manager.py` の実装値。worst-case 同時 units が 20k を超える rung は**cap 改定 R1 同梱が必須** (改定しない場合、超過 leg の block = pre-reg 分母設計と衝突しうる — wg §2.4 全執行原則) |
| 4.6 | **ポートフォリオ合成 DD** | ladder 全セル合成で §6 D4 の段階制約 | 4%/6%/8% NAV (DD_LOT_TIERS の粒度と整合) |
| 4.7 | JPY 台帳整合 | パケットに感応度行を必記 | rung 変更後の `JPY/pip` 感応度 (= units/1000 × v) と worst-case イベント損失 JPY を JPY 台帳の想定に追記。母集団は broker realized のみ |

- **MC ruin gate (>0.7 aggregate block) は edge-cell 経路にも適用され続ける** (`demo_trader.py` の v9.1 SHIELD は force-live を免除しない) — 階段はこの既存防御の内側で動く
- グローバル DD lever (0.2x 等) は carve-out 契約により rung units へ**乗算しない** (wg/ps 前例)。防御機能は §6 D4 のポートフォリオ降格が代替する — 「lever 免除 + 専用降格 gate 併設」が carve-out の標準形

## §5 昇格条件 (rung-up ゲート — 全て AND、1 つでも欠けたら HOLD)

| 遷移 | エッジ持続 (累積) | 執行品質 (at-rung) | リスク検証 | 手続き |
|---|---|---|---|---|
| **L0→L1** | G3 充足 ∧ **Wilson_lo(WR) > BEV_WR** (§3.3) | slippage rolling mean (N≥6) ≤ +2.0p | MC: P(セル DD > 2% NAV, 12 ヶ月) ≤ 5% @5000u ∧ §4 全制約充足 | R1 パケット + user 承認 |
| **L1→L2** | Wilson gate 再充足 (累積 N で再計算) | **at-rung N≥12** ∧ at-rung mean ≥ 0 ∧ at-rung slippage ≤ L0 実測 +1.0p ∧ at-rung disaster 0 | MC @10000u ≤5% ∧ §4 再計算 | R1 パケット + user 承認 |
| **L2→L3** | 同上 | **at-rung N≥20** ∧ 同上 | MC @30000u ≤5% ∧ §4 再計算 ∧ **exposure cap 改定決裁同梱** | R1 パケット + user 承認 (最大段差 3x — 明示裁可) |

- **at-rung N の意味を正直に**: N=12〜20 はエッジの再検証には無力 (検出力不足)。検証できるのは**サイズ増加で変わるもの = fill/slippage/market impact** のみ。エッジの証拠は常に累積 N の Wilson gate が担う — この分業をパケットに明記し、at-rung 統計から EV の結論を引かない
- at-rung slippage 比較は同一測定系 (`record_fill_slippage`) の rung 別平均差。悪化 +1.0p は wg L0 実測 RT (7.70p) の ~13% に相当する保守閾値
- MC 検証は `modules.risk_analytics.monte_carlo_ruin` (セル live pnl を JPY@目標 rung に変換、`initial_capital=NAV`、`ruin_dd_pct=0.02`、`n_trades_forward=12 ヶ月分イベント数`)。live N が浅いうちは分布の尾が細く出る (標本外の tail を含まない) — disaster SL 基底の解析制約 4.2 が下支えする設計

## §6 降格規則 (R2 自動 — 対称性の凍結)

| # | 条件 | アクション |
|---|---|---|
| **D1 slippage** | rolling N≥6 mean slippage > +2.0p | **−1 rung** (執行劣化はサイズ起因の可能性 — まず縮小) |
| **D2 at-rung 出血** | at-rung 直近 N=12 累積 net < **−60p** (wg G2 と同値。セル固有値に置換する場合はパケットで凍結) | **−1 rung** |
| **D3 disaster** | rung ≥ L1 で disaster SL 1 発 | **−1 rung 即時** + 原因レビュー |
| | disaster SL 累積 2 発 (rung 不問) | **L0 へ降格** + 再昇格は R1 全段やり直し |
| **D4 ポートフォリオ** | ladder 全セル合成 JPY DD (baseline 比) ≥ 4% NAV | **全セル −1 rung** |
| | 同 ≥ 6% NAV | **全セル L0** |
| | 同 ≥ 8% NAV | **全セル stop flag** (live 送信停止、shadow 継続) |
| **D5 エッジ減衰** | 月次 recheck で Wilson_lo(WR) < BEV_WR | rung 凍結 (up 禁止)。2 ヶ月連続 → **−1 rung** |

**実装要件 (第 1 適用 R1 で code 化 — wg G1/G2 パターンを踏襲)**:
- 送信前に毎回評価 (`_check_r2_gates` 型)。fire したら **kv flag latch + code に再武装経路なし**。解除 = 手動 kv 削除 + R1 のみ
- **KV default は fail-closed** — rung 状態 kv の欠損/リセット時は**下位 rung に落とす** (E4 の default="1" 再武装事故の再発防止: `edge_cell_stage` の `default="1"` 型は禁止)
- 降格発火時は `[ALERT][LOT_LADDER]` print + AlertManager 通知 + 監視 registry 記録 (T5 教訓: 監視主体なき pre-reg を作らない)
- 降格後の再昇格は「fresh at-rung 証拠の再充足 + R1 パケット再起案」— 降格前の実績は持ち越さない

## §7 配管 (実装経路 — 第 1 適用 R1 のスコープ)

| rung | 経路 | 既知の病理と対策 |
|---|---|---|
| L0 | `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` + code 固定 units (wg/ps 前例) | bypass は `≤1000u` 条件 — L0 専用 |
| L1+ | `edge_cell_promote` force-live (agg-Kelly gate を bypass、MC ruin gate は適用継続) + KV stage | ① KV default 再武装 (E4) → fail-closed default 必須 ② watchdog DECREMENT floor 前例 → 降格は floor 0 まで ③ 停止の恒久化は `DISABLED_CELLS` 型 code pin |
| L3 | 同上 + `exposure_manager` cap 改定 | 20k cap は他戦略の防御でもある — 改定は「ladder セル限定の carve-out」形式とし、グローバル引き上げはしない |

- wg 固有: `WEEKEND_GAP_FADE_MIN_LOT` は lot 乗算系を code で全遮断した固定契約 — L1 適用時は「固定 units の値を上げる」のではなく edge_cell 経路へ載せ替えるか、wg 専用 rung 定数 + §6 gate 群を同一 PR で実装 (「発火するが測れない/止まらない」状態を作らない — D-c-1 の同時執行原則)

## §8 R1 決裁パケット雛形 (1 ページ様式)

パケットは `tools/lot_ladder_calc.py --packet` で機械生成し、`wiki/decisions/lot-ladder-{cell}-{rung}-{date}.md` として起案する。様式:

```markdown
# ロット階段 R1 パケット — {cell_id} L{n}→L{n+1} ({date})

## 1. 遷移
{strategy}×{pair} : {現 units}u → {目標 units}u (rule:R1、テンプレ [[lot-ladder-template-2026-08]] 準拠)

## 2. 凍結根拠数値 (live 実績 — oanda_trade_id != '' のみ)
| N累積 | N at-rung | mean | σ | WR | avg_win | avg_loss | disaster | slippage mean |
|---|---|---|---|---|---|---|---|---|

## 3. ゲート判定 (ツール出力貼付 — 手計算禁止)
- Wilson_lo(WR) = X vs BEV_WR = Y → PASS/FAIL (FAIL なら N_required = Z)
- at-rung 執行品質: N=X, mean=Y, slippage Δ=Z → PASS/FAIL
- MC: P(セル DD>2% NAV, 12mo) = X% @目標 rung → PASS/FAIL
- Kelly 上限 U_avg/U_dis、制約 U_cellDD/U_margin/U_exposure → **binding = {どれ}**

## 4. counterfactual (機会費用 vs 追加リスク)
- 昇格しない場合の機会費用: Δunits × mean × events/月 × v = +X JPY/月 (+Y% NAV)
- 昇格する場合の追加 tail: worst-case イベント損失 X→Y JPY (Z% NAV)、合成 worst-case 同時 = W JPY

## 5. 停止条件 (R2 自動 — instantiated 値)
D1: slippage>+2.0p→L{n} / D2: at-rung N12 < −60p→L{n} / D3: disaster 1発→L{n}, 2発→L0
D4: 合成 DD 4/6/8% NAV / D5: Wilson gate 割れ→凍結
latch kv: `LOT_LADDER_{cell}_DEMOTED` (再武装経路なし、解除は R1)

## 6. rollback
kv 削除 1 操作で L{n} へ復帰 + code pin 候補列挙。live 送信停止しても shadow 蓄積は不変

## 7. 動機記録
データ駆動 (G3 + ゲート全通過) / 感情起因でないことの確認: {直近負けイベント直後の起案でないか}

## 8. 参照
戦略カード / OOS verdict / 本テンプレ / JPY 台帳感応度更新行

## 9. user 承認 (SLA 48h)
[ ] 承認 / [ ] 却下 / [ ] 保留 — 日付・条件:
```

## §9 適用第 1 候補 = weekend_gap_fade (事前充填)

**現況 (2026-08-05)**: live 執行 N = **0/2 イベント** (07-26 インフラ障害 / 08-02 FOK MARKET_HALTED — いずれも分母外)。**fill 修復が全ての前提** — 08-09 観測で不成立なら執行契約変更 R1 が先行する。G3 (N=30) ETA ≈ 2027-05 (3.28 events/月ペース)。

**feasibility 事前計算 (NAV ≈ 326,473 JPY = D-a 再構成値。パケット時に実 NAV で再計算)**:

| rung | 証拠金 (USD_JPY@147) | worst-case 1 イベント (disaster 150p) | 判定 |
|---|---|---|---|
| L0 1000u | 5,880 JPY (1.8% NAV) | 1,500 JPY (0.5% NAV) | 現行 |
| **L1 5000u** | 29,400 (9.0%) / 3ペア同時 ≈ 82.6k (25.3%) | 7,500 (2.3%) | **可 — 制約 4.2 (≤2.5%) ギリギリ内側。U_cellDD ≈ 5,441u が binding** |
| L2 10000u | 58,800 (18.0%) | 15,000 (4.6%) | **不可 @現 NAV** — 制約 4.2 違反。NAV ≥ 600k で 4.2 は開通するが、**3 ペア同時セルは 4.5 (20k/3 ≈ 6.6k) が引き続き縛る** → wg の L2 は exposure cap 改定 R1 同梱が必須。または disaster SL 再設計 (live MAE 分布 N≥30 を根拠に幅を詰める R1) が先 |
| L3 30000u | 176,400 (54.0%) | 45,000 (13.8%) | **不可** — 4.2/4.4/4.5 の 3 重違反 @現 NAV。NAV ≥ 1.8M 相当で再評価 |

- **wg の binding constraint は Kelly ではなく disaster SL 幅 (150p)**。placeholder 統計 (WR55%/payoff1.5) では half-Kelly ≈ 0.125 → U_dis ≈ 27k だが、制約 4.2 が 5.4k で縛る。ロット成長の律速 = NAV 成長 × disaster SL 設計 — この構造は「セル 2〜5 本」の合成が必要な理由そのもの (単一セルの垂直增額では届かない)
- L0→L1 の機会費用: Δ4,000u × 7.9p × 3.28 events/月 × 10 JPY/p/1000u ≈ **+1,036 JPY/月 (+0.32% NAV)** — 1 セル 1 段では小さいが、5 セル × L2 で thesis の +11〜16%/月へ接続する
- exposure: L1 3 ペア同時でも USD net ≈ 15k < 20k で衝突なし。L2 以上で cap 改定が必要
- Wilson gate: wg 級統計 (WR55%/1.5) の場合 **N_required = 41 > G3 の 30** — G3 到達時にゲートが開かない可能性をあらかじめ織り込む (その場合パケット verdict = HOLD、L0 のまま N 蓄積継続)

## §10 参照

- [[track-c-capital-plumbing-decision-packet-2026-07-28]] — D-a JPY 台帳実測 (実 DD 9.14% / NAV 再構成) / D-d 解除ラダー原則
- [[shortest-path-decision-memo-2026-07-10]] — agg-Kelly gate 恒久閉鎖 / D4 pre-reg 必須項目 / 「30d EV>0 単独禁止」
- [[weekend-gap-fade]] — G1/G2/G3 ゲート構造 (§6 実装パターンの原器)
- [[edge-cells-stage3-wilson-lo-restoration-2026-06-07]] — Wilson_lo ゲートの Bonferroni 較正前例
- `modules/risk_analytics.py` — kelly_fraction / monte_carlo_ruin / DD_LOT_TIERS (式の SSOT)
- `modules/edge_cell_promote.py` — L1+ 配管 / DISABLED_CELLS code pin パターン
- `modules/exposure_manager.py` — 20k/3 件 cap 実装値
- MEMORY: `project_watchdog_decrement_rearm_bug` (KV 再武装) / `project_t5_jpy_cap_prereg_executed` (監視主体) / `feedback_cell_portfolio_thesis_2026_08_05` (本テンプレの発注元)
