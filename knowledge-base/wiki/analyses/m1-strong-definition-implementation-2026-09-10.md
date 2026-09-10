# M1 強定義の実装 + M3 二定義分離 — 2026-09-10 (rule:R3)

**分類**: R3 (KPI 計測基盤の修復 — meta-audit 2026-09-07 §4.2 R4(a)/(b)、user 承認 2026-09-10)
**関連**: [[process-meta-audit-2026-09-07]] R4 / [[m1-kpi-readout-and-mechanical-flip-2026-09-04]] §8 / [[monthly-target-rederivation-2026-07-10]] §4 / [[roadmap-v2.3-payoff-friction-repair]] KPI 表
**実装**: `tools/m1_clean_live_monitor.py` (`--strong`) / 配線: `tools/quant_gate_status.py` + `render.yaml` Tier A cron / テスト: `tests/test_m1_strong_and_m3.py` 25 本 (全 suite 3,026 passed green)

---

## 0. 要約

1. **M1 弱定義 (30d rolling PnL 符号) は縮退 KPI** — 新規約定ゼロの機械的符号反転で「達成」表示になり、分母が縮むほど満たしやすい (09-04 実証)。承認済みの強定義が **59 日未実装**だった。
2. 本コミットで **弱定義 readout を残したまま** `--strong` を追加: M1 強定義 (**2 文書の定義を両方**) + M3a (throughput) / M3b (return) の分離 readout。Tier A cron (render.yaml `fx-ai-tier-a-gate-status`) を `--strong` 込みに**同一コミットで**更新 (読み手なしの計装禁止)。
3. **文書間矛盾は存在する (4 件、下記 §2)。裁定は user。** 実装は両方を計算して毎日併記する。
4. 2026-09-10 実測 (本番 read-only GET): **M1_STRONG = 未達 (全変種)**。M3a = 2/3 (累積、ただし稼働 0)、M3b = **−0.075%/月** vs 目標 +0.5%。
5. 副産物: 弱定義 M1 は 09-04 の +19.8p から **−85.0p へ再反転**しており、これも **MECHANICAL_FLIP** (勝ちの窓外脱落が主因)。rolling 符号の無内容さを 6 日で再実証した形。

---

## 1. 実装した定義

母集団 (全変種共通の clean live): `oanda_trade_id != ''` ∧ `dedup_violation != 1` ∧ `instrument != XAU_USD` ∧ `status = CLOSED` ∧ `pnl_pips` 非 null。セル = `entry_type × instrument × direction`。セル N は **cutoff 2026-04-08 以降の累積** (clean_n_tracker / api_demo_stats の FIDELITY_CUTOFF と同一)。

| 変種 | 定義 | 出典 | 達成条件 |
|---|---|---|---|
| M1_WEAK (存置) | clean live 30d PnL > 0 (+ verdict 3 状態 + flip_attribution + bootstrap P(sum≤0) 併記) | roadmap v2.3 KPI 表 | sum > 0 |
| **M1_STRONG_CELL** (主定義) | セル単位 clean live 累積 **N≥30 ∧ 平均 net EV ≥ +1.0 p/t ∧ Wilson95 下限(WR) > 0** | rederivation §4 系 + 2026-09-10 user 指示の閾値 | 該当セル ≥ 1 |
| M1_STRONG_BOOK | book 全体 30d sum > 0 ∧ bootstrap P(sum≤0) < 0.05 (= 既存 verdict `MET`) | m1-kpi-readout §8 案 | verdict = MET |
| M1_STRONG_FULL | M1_STRONG_CELL ∧ M1_STRONG_BOOK | rederivation §4 全文 (「book 全体 Wilson 下限 > 0 相当」の実装として bootstrap MET を使用) | 両方 |
| **M3a** (throughput) | clean live 累積 N≥30 のセル数 / 3。ETA = 直近 30d の N 蓄積レートから線形外挿、3 本目の到達日 | roadmap v2.3 KPI 表 M3 | 3 セル |
| **M3b** (return) | 摩擦調整後 (= live 実現 net pips) 正EVセルの直近 30d 寄与合計。一次単位 pips、JPY/%NAV は推定レイヤ (units=1000 仮定 + quote→JPY 概算、NAV は `/api/oanda/status` 実測) | rederivation §4 M3 return 版 + 2026-09-10 user 指示の分母 | ≥ +0.5%/月 (primary) |

## 2. 文書間矛盾 (両方実装済み — 裁定は user)

1. **資格の母集団が違う**: m1-kpi-readout **§8** は book 全体の bootstrap 資格 (sum>0 ∧ P(sum≤0)<0.05)、rederivation **§4** はセル単位資格 (live N≥30 の正EVセル ≥1) + book 全体の統計確認。→ `M1_STRONG_BOOK` / `M1_STRONG_CELL` / `M1_STRONG_FULL` を全部出す。
2. **EV 閾値**: rederivation §4 literal は「**正EVセル**」(EV>0)、2026-09-10 修復指示は **EV≥+1.0 p/t**。→ 主定義は +1.0、literal (EV>0) カウントを毎回併記。
3. **Wilson 下限 > 0 は win-rate 解釈では非拘束**: WR の Wilson95 下限 > 0 ⇔ 勝ち ≥1 件 ⇔ EV>0 が必ず含意する。条件はコード上拘束として実装 (`_cell_is_strong`、テストで pin) しつつ、repo の R1 gate 慣例 (`wilson_lo ≥ 0.50`、bb_2sigma_fade G2 等) での保守カウントも併記 — 「>0」の文言をどちらに読むかは user 裁定。
4. **M3b の目標値**: 2026-09-10 指示の分母は **+0.5%/月** (= rederivation の M2 と同値)、rederivation §4 の M3 return 版は **+2〜3%/月**。→ +0.5% を primary、+2〜3% を併記 (定義併存を出力に明示)。

追加で実測から発覚した二母集団問題 (矛盾 5): **M3a の「N≥30 セル」には休眠 legacy セルが混じる** — 累積では `bb_rsi_reversion×USD_JPY` の SELL (N=44) / BUY (N=32) が該当するが、両方とも直近 30d 発火 0 (R2 停止系)。09-04 再計測の「0 個」は稼働ロースタ側の読み。→ `cells_done` (累積) と `cells_done_active` (直近 30d 稼働) を分けて出力 (ps capture 教訓: 分子と分母の母集団を混ぜない)。

## 3. 2026-09-10 実測 (本番 API read-only GET、anchor 2026-09-10T06:49 UTC)

**M1 (弱定義、存置)**: 🔴 **NOT_MET** — N=17 / sum **−85.0p** / EV −5.00p/t / WR 47.1% / bootstrap 95% CI [−284.0, +83.9] / P(sum≤0) = **0.817**。
**flip_attribution**: 直近 7d で新規 N=5 (−9.1p) / 窓外脱落 N=2 (**+92.7p**) → Δ=−101.8p = 🚨 **MECHANICAL_FLIP** (主因: 2026-08-09 carry_dip **+63.7p** の脱落)。09-04 の「文言上達成 (+19.8p)」は 6 日で機械的に消えた — 弱定義の符号は往復とも無内容。

**M1_STRONG**: 🔴 **全変種 未達**
- セル定義 (N≥30 ∧ EV≥+1.0 ∧ w_lo>0): **0 セル** (全 117 セル中)
- rederivation literal (EV>0, N≥30): **1 セル** — `bb_rsi_reversion×USD_JPY×SELL` (N=44, EV +0.29p, w_lo 0.36、**休眠**・直近 30d 発火 0)
- wilson_lo≥0.50 保守: 0 セル / book 定義 (§8): NOT_MET / FULL: 未達

**M3a (throughput)**: 🔴 **2/3 セル (累積)、稼働 0/3** — 到達済み 2 は休眠 legacy (`bb_rsi_reversion` SELL/BUY)。3 本目 ETA = **2026-10-26** (`usdjpy_carry_dip_accumulator×USD_JPY×BUY` N=13、+11/30d の線形外挿)。稼働セルだけで 3 本なら (現行 3 セル体制のレートで) ps_eur_gbp / ps_aud_jpy が律速のまま = 09-04 の ~14 ヶ月推定と整合。

**M3b (return)**: 🔴 **−0.075%/月** — 正EV 44 セル (うち N≥30 は 1) の直近 30d 寄与 = **−20.8p** ≈ ¥−208 (units=1000 仮定、NAV 実測 ¥275,486.30) vs 目標 +0.5%。ETA = **現行ペースで到達不能** (線形 N 外挿では月次寄与レートは一定 — 新セル追加か lot 変更なしに達成日は存在しない。これは外挿手法の含意であって推定エラーではない)。
⚠️ 正EVセル集合の 30d 寄与が負なのは、cumulative EV>0 の carry_dip が直近 30d は −20.8p だったため — 「正EV」の認定窓 (累積) と寄与の測定窓 (30d) が違うことによる正しい挙動 (混ぜない)。

## 4. 実装詳細

| 種別 | パス | 内容 |
|---|---|---|
| 読み手 | `tools/m1_clean_live_monitor.py` | `--strong` で M1_STRONG (3 変種) + M3a/M3b を弱定義 readout に追記。`wilson_lower` / `cumulative_cell_stats` / `strong_summary` / `m3_summary` / `fetch_nav_jpy` 新設。弱定義パス (`summarize` 等) は**無変更** |
| 配線 1 | `tools/quant_gate_status.py` | `--strong` フラグ → `m1.build_report(strong=True)`。Discord 送信を **1 メッセージ 1900 字 hard-cut → セクション境界で最大 4 分割**へ変更 (strong 追加で先頭ブロックが ~1900 字となり、旧実装では Readiness / prereg watch が毎日切り落とされる = 既存読み手を殺すため) |
| 配線 2 | `render.yaml` | Tier A cron `fx-ai-tier-a-gate-status` の startCommand を `--to-discord --strong` へ (同一コミット) |
| テスト | `tests/test_m1_strong_and_m3.py` | 25 本: N=29/30 境界 / EV 0.99/1.00 境界 / Wilson 下限 0 跨ぎ (+ 条件拘束の直接 pin) / cutoff 混入 / book・full の独立性 / flip 分解の恒等式 (sum_added − sum_aged = sum_now − sum_prev) / M3a ETA 算術・3本目選択・二母集団分離 / M3b 正EV フィルタ・0.5% 含む境界・NAV 欠損時の非捏造 / cron `--strong` 配線 / qgs 引き渡し / Discord 分割 |

NAV 取得の実装ノート: `/api/oanda/status` の `account` は OANDA v20 応答 `{"account": {...}}` を**そのままネスト**して返す (2026-09-10 実測)。flat/nested 両対応 + 取得失敗時は M3b を pips 一次単位で成立させ % のみ `UNKNOWN` (fetch_json が失敗を `{}` に潰した 08-30 監視 blind の再発防止 — 欠損は欠損と言う)。

## 5. roadmap KPI 表への反映提案 (roadmap 本体は本コミットで変更しない — 変更禁止規律)

- M1 行: 弱定義の現況を「NOT_MET (再反転、MECHANICAL_FLIP)」へ更新し、M1_STRONG 3 変種の行を追加 (現況: 全て未達)。定義裁定 (§2 の 4 件) を user 決裁として起票。
- M3 行: M3a (throughput、累積/稼働の 2 カウント) と M3b (return、+0.5% primary / +2〜3% 併記) へ正式分離。
- 反映の執行は user 裁定後に別コミットで。

## 6. 未解決 / 次アクション

- [ ] §2 の定義矛盾 4 件の裁定 — **user 決裁** (特に: M1_STRONG の正式変種はどれか / Wilson「>0」の読み / M3b の目標値)
- [ ] M3a「稼働」の定義精緻化 — 現実装は「直近 30d に発火 ≥1」の機械判定。live-enable フラグ / tier 状態との突合は `tools/live_roster_attrition.py` と統合余地
- [ ] M3b の JPY 換算を実 units で行うには `oanda_trades` (units 保持) との join が必要 — 現状は units=1000 仮定の推定レイヤ (一次単位は pips)
- [ ] Tier A cron 初回実行 (デプロイ後 UTC 00:20) で Discord 4 分割送信の実挙動確認
