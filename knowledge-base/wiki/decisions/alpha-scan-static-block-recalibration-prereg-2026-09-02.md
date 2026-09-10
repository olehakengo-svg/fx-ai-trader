# Pre-reg: v8.9 alpha_scan 静的ブロック 10 件の再較正 (2026-09-02)

> **種別: R3 診断 (再較正の事実確認)。** 本 pre-reg 単体では**いかなるブロックも解除しない**。
> 解除は別途 R1 (365d BT or Live N≥30 + Bonferroni + pre-reg LOCK + user 最終承認)。
> **観測前凍結**: 本ファイルが main に到達した時点で §2-§5 を LOCK。以後の変更は §7 に追記形式でのみ記録。

**起案**: 2026-09-02 (autopilot session)
**動機**: 2026-09-01 セッションの live 頻度 readout。8 月の LIVE = 13 件、9 月 = 0 件。
London/NY 帯の live がセル構成の変化 (6 月世代の R2 demote) だけでなく
**2026-04-14 較正の静的ブロック**によっても削られている疑い。
根拠ページ: [[live-frequency-and-oanda-status-survival-2026-09-01]]

---

## §1 対象 — v8.9 alpha_scan / session_pair 静的ブロック 10 件

`modules/demo_trader.py` の LIVE 転送判定内。いずれも条件成立時に
`_is_shadow = True` (shadow eligible なら) / それ以外は `_block(...) + return`。
= **LIVE 転送を殺すが shadow 記録は残す**。この非対称が本研究を可能にする
(CLAUDE.md 原則3: 静的時間ブロックは Shadow に適用しない → **shadow 側が未処置対照群**)。

| # | ID | 条件 (コード上) | 較正値 (2026-04-14) | 行 |
|---|---|---|---|---|
| B1 | `session_pair(EUR_USD_Tokyo)` | `instrument==EUR_USD and hour<7` | WR=20% (N 未記録) | 5682 |
| B2 | `session_pair(EUR_USD_Late_NY)` | `EUR_USD and hour>=17` (weekend_gap_fade 免除) | WR=10% (N 未記録) | 5697 |
| B3 | `alpha_scan(EUR_USD_SELL)` | `EUR_USD and dir==SELL` | N=43 WR=11.6% EV=−2.714 | 5707 |
| B4 | `alpha_scan(RANGE_SELL)` | `regime==RANGE and SELL and conf<65` | N=89 WR=27.0% EV=−1.636 | 5730 |
| B5 | `alpha_scan(TREND_BULL_BUY)` | `regime==TREND_BULL and BUY and conf<65 and entry_type ∉ MR免除5種` | N=70 WR=31.4% EV=−0.776 | 5748 |
| B6 | `alpha_scan(H11_EUR_USD)` | `hour==11 and EUR_USD` | N=9 WR=22.2% EV=−4.489 | 5762 |
| B7 | `alpha_scan(H13_USD_JPY)` | `hour==13 and USD_JPY` | N=14 WR=28.6% EV=−2.486 | 5774 |
| B8 | `alpha_scan(H16-20_USD_JPY)` | `USD_JPY and 16<=hour<=20` | N=27 WR=18.5% EV=−2.4 | 5784 |
| B9 | `alpha_scan(BUY_TREND_BEAR)` | `BUY and regime==TREND_BEAR and conf<70` | N=19 EV=−1.67 | 5794 |
| B10 | `alpha_scan(H7-8_EUR_USD)` | `EUR_USD and hour ∈ {7,8}` | N=14 EV=−2.38 | 5806 |

いずれも `_is_live_tier_exempt` / `_is_slot_shadow_eligible` で分岐するが、
**条件そのものは行データ (instrument / entry_time UTC hour / direction / regime / confidence /
entry_type) から決定論的に再構成できる**。

**較正母体の性質**: 全て 2026-04-13〜14 時点の DT 戦略群を母体とする。
当時の主力 (bb_rsi_reversion / fib_reversal / xs_momentum / session_time_bias 等) は
**その後すべて R2 demote または KILL 済み**。現在ブロックを踏んでいるのは
carry_dip / kalman_d7 / donchian / tokyo_nakane 等の**別世代のセル**。
→ **estimand 不一致の疑いが本研究の主問**。

---

## §2 データ (観測前に凍結)

- **ソース**: Render 本番 `/api/demo/trades?status=closed`、`date_from`/`offset` ページング
- **窓**: entry_time ∈ **[2026-04-15T00:00Z, 2026-09-01T23:59Z]**
  (較正日 04-14 の翌日以降 = 較正データと非重複 = 較正に対する OOS)
- **除外**: `dedup_violation==1` / XAU_USD / `outcome ∉ {WIN, LOSS}` (未決済・不明)
- **勝敗判定**: `outcome` 列のみ (`close_reason` 禁止 — MEMORY `project_sl_hit_label_collision_2026_08_07`)
- **LIVE / shadow 厳格分離**: LIVE = `oanda_trade_id != ''`。`is_shadow==0` 単独は使わない
  (MEMORY `feedback_live_vs_shadow_strict_separation`)。**両者を混ぜた集計は作らない**
- **主母集団 = shadow** (ブロックの未処置対照群)。LIVE は N が極小のため参考表示のみ

**時刻**: `entry_time` を UTC に正規化して hour を取る。コード側 `_utc_hour` と同一定義。

---

## §3 測定 (観測前に凍結)

### P0 — 再構成妥当性チェック (これが落ちたら P1/P2 は読まない)
LIVE 行 (`oanda_trade_id != ''`) のうち B1..B10 のいずれかの条件を満たすものの件数と
その `entry_type`。再構成が正しければ、これらは **`_is_live_tier_exempt` に該当するセルに
ほぼ限られる**はず。exempt でないセルの LIVE 行が条件を満たして多数出るなら、
**条件の再構成が誤っている** (regime の出所違い等) → 本研究は測定不能として中止し、
その旨を verdict に書く。

### P1 — 母集団オーバーラップ (主測定、構造)
各 B_i について、窓内 shadow 行のうち条件成立行を集め、
`overlap_i = (較正母体に存在した entry_type の行数) / (条件成立行数)`。
較正母体の entry_type 集合は **2026-04-08〜04-14 窓の実データから機械的に取得**する
(記憶や記述からではなく、同一 API の同一パイプラインで抽出)。

### P2 — 新窓 EV (副測定、統計)
各 B_i について、窓内 shadow 条件成立行の
`N_in` / `WR_in` / `EV_in` (mean pnl_pips) / bootstrap 95% CI (B=10,000, seed=20260902) /
片側 t 検定 p (H0: EV_in ≥ 0 に対する「負である」の検定)。

**多重性**: Bonferroni m=10 → α = 0.05/10 = **0.005**。

**摩擦調整**: `EV_net_in = EV_in − friction_RT(pair)`。
`friction_RT` は CLAUDE.md の per-pair 表 (USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 /
EUR_JPY 2.50 / EUR_GBP 3.00) を使用。複数ペアが混じる B4/B5/B9 は行ごとのペア摩擦で調整。

**既知バイアス (方向を先に宣言)**: shadow EV は BE/Trail により live 比で**楽観**
(MEMORY `project_be_trail_inflates_python_bt_wr`, `friction-adjusted-ev-map-2026-07-07`)。
したがって —
- shadow EV_net_in が**負** → live はさらに負 → ブロック維持の結論は **a fortiori で堅い**
- shadow EV_net_in が**正** → live に伝わる保証はゼロ (T4 で実証済み) → **解除の根拠にはならない**

この非対称ゆえ、本研究は**ブロック解除を主張できない設計**である。主張できるのは
「較正時の前提が現母集団で再現するか」だけ。これは意図した設計であって限界ではない。

---

## §4 判定表 (観測前に凍結)

各 B_i に以下のいずれか 1 つを付す。

| verdict | 条件 | 帰結 |
|---|---|---|
| **UNDERPOWERED** | `N_in < 30` | 判定不能。**ブロック維持**。N を記録し次回再測 |
| **PREMISE-INTACT** | `N_in ≥ 30` かつ `EV_net_in < 0` かつ 片側 p < 0.005 | 較正前提は現母集団でも成立。**ブロック維持**。較正値を新実測へ更新 (docstring/コメント) |
| **PREMISE-STALE** | `N_in ≥ 30` かつ `overlap_i < 0.20` かつ p ≥ 0.005 | 前提は現母集団で再現せず、かつ母集団が入替わっている。**ブロックは維持したまま R1 起票**  (解除案は別 pre-reg + user 承認) |
| **PREMISE-WEAK** | `N_in ≥ 30` かつ `overlap_i ≥ 0.20` かつ p ≥ 0.005 | 母集団は連続だが有意な負を再現せず。**ブロック維持**、registry に再測エントリのみ |

**ナイフエッジ規律**: p が [0.003, 0.008] に入った B_i は敵対的検証 3 点
(メカニズム整合 / クラスタ補正 (日次クラスタで block bootstrap) / 閾値 OOS 化) を必須とし、
通過しない限り PREMISE-INTACT を名乗らせない。

**この pre-reg が許す最大の行動 = 「R1 起票」まで。** コードの条件変更・閾値変更・
セル免除の追加は本 pre-reg の範囲外。

---

## §5 事前の期待 (書いておかないと後付けになる)

- B6 (N=9) / B7 (N=14) / B10 (N=14) は較正 N が二桁未満〜十数で、**そもそも較正が薄い**。
  新窓で PREMISE-STALE か UNDERPOWERED になる確率が高いと予想する。
- B3 (EUR_USD SELL 全面) / B4 / B5 は較正 N が 43-89 と比較的厚く、条件も広いので
  新窓 N も厚いはず。ここが PREMISE-INTACT なら**ブロック体系の中核は健全**という
  安心材料になる (それも本研究の価値)。
- B8 (H16-20 USD_JPY) は 2026-09-01 readout で NY 帯 live を削る主犯として名指しされた。
  ここが PREMISE-INTACT なら **「NY に実弾が無いのは正しい防御」**が結論になり、
  頻度問題の原因はセル構成のみに帰着する。**この分岐こそが本研究の意思決定価値**。

予想が外れること自体は問題ではない。予想を書かずに結果を見ることが問題である。

---

## §6 成果物

1. 本ファイル §7 に verdict を追記 (全 10 ブロック分)
2. `knowledge-base/wiki/analyses/` に数値根拠 (N/WR/EV/CI/p/overlap の全表)
3. PREMISE-STALE が出た場合のみ `decisions/prereg-trigger-registry.json` に R1 起票エントリ
   (到達経路を message に明記 — MEMORY `project_trigger_reachability_evaluator_fix_2026_08_19`)
4. 測定スクリプトを `tools/` に置き、**再実行で同じ数字が出ること**を verdict 内で示す

---

## §7 Verdict (2026-09-02、観測後に追記)

**測定日**: 2026-09-02 (B1 修正後の再測定を反映) / **窓**: 2026-04-15〜2026-09-01 / **clean 行**: 11,840 (shadow 11,548 / LIVE 292)
**較正母体 entry_type**: 35 種 (2026-04-08〜04-14 の実データから機械抽出)
**再現**: `python3 tools/alpha_scan_block_recalibration.py --fetch --cache <path>`
数値 artifact: `knowledge-base/raw/bt-results/alpha-scan-block-recalibration-2026-09-02.json`

### 総括: **10/10 が PREMISE-INTACT。ブロック体系は現母集団でも正当。**

§5 で書いた事前予想 (「較正 N が薄い B6/B7/B10 は STALE か UNDERPOWERED になるだろう」)
は **外れた**。新窓 N は 146〜1,404 で較正 N の 10〜100 倍、全件が Bonferroni α=0.005 を
大きく下回る片側 p (全て <0.0001) で摩擦調整後 EV が負。母集団オーバーラップも
70.0〜93.8% で、「別世代のセルに適用されている」という主問の仮説自体が
**全 shadow 母集団では否定された**。

| blk | 条件 | 較正 N/EV | 新 N | WR | EV_gross | **EV_net** | CI95(net) | p | overlap | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | EUR_USD Tokyo | – / – | 241 | 45.2% | −1.13 | **−3.13** | [−3.89, −2.39] | <1e-4 | 86.7% | PREMISE-INTACT |
| B2 | EUR_USD Late NY | – / – | 183 | 37.2% | −0.91 | **−2.91** | [−3.58, −2.23] | <1e-4 | 87.4% | PREMISE-INTACT |
| B3 | EUR_USD SELL | 43 / −2.71 | 1404 | 42.9% | −0.97 | **−2.97** | [−3.33, −2.61] | <1e-4 | 87.3% | PREMISE-INTACT |
| B4 | RANGE SELL conf<65 | 89 / −1.64 | 959 | 34.6% | −1.48 | **−4.13** | [−4.63, −3.60] | <1e-4 | 85.8% | PREMISE-INTACT |
| B5 | TREND_BULL BUY conf<65 | 70 / −0.78 | 606 | 39.6% | −1.61 | **−4.21** | [−4.85, −3.58] | <1e-4 | 70.0% | PREMISE-INTACT |
| B6 | H11 × EUR_USD | 9 / −4.49 | 146 | 37.7% | −0.95 | **−2.95** | [−4.05, −1.81] | <1e-4 | 93.8% | PREMISE-INTACT |
| B7 | H13 × USD_JPY | 14 / −2.49 | 327 | 44.0% | −0.21 | **−2.35** | [−3.44, −1.28] | <1e-4 | 74.0% | PREMISE-INTACT |
| B8 | H16-20 × USD_JPY | 27 / −2.40 | 675 | 37.0% | −1.12 | **−3.26** | [−3.85, −2.67] | <1e-4 | 77.5% | PREMISE-INTACT |
| B9 | BUY TREND_BEAR conf<70 | 19 / −1.67 | 875 | 39.7% | −1.34 | **−4.07** | [−4.55, −3.58] | <1e-4 | 80.5% | PREMISE-INTACT |
| B10 | H7-8 × EUR_USD | 14 / −2.38 | 423 | 38.8% | −0.79 | **−2.79** | [−3.41, −2.17] | <1e-4 | 75.2% | PREMISE-INTACT |

**ナイフエッジ検査は不要** — p が [0.003, 0.008] に入った B_i はゼロ (全て <1e-4)。

**§5 の決定価値分岐の解決**: 「B8 (H16-20 USD_JPY) が PREMISE-INTACT なら
**『NY に実弾が無いのは正しい防御』**が結論」と事前に書いた。B8 は N=675 で
EV_net −3.26 [−3.85, −2.67] = **INTACT**。よって **2026-09-01 readout の
「静的 hour block が NY live を不当に削っている」という疑いは、全 shadow 母集団の
水準では支持されない。** 頻度問題の原因はセル構成に帰着する。

### P0 — 再構成妥当性: **PASS (ただし pre-reg のチェック設計自体に欠陥があった)**

§3 の P0 は「exempt でないセルの LIVE 行が条件を多数満たすなら再構成が誤り → 中止」
と凍結していた。**実測は 104 行**で、字義どおりなら中止条件に該当する。

しかし原因を追ったところ、**誤っていたのは再構成ではなく P0 チェックの方**だった:

1. `_is_live_tier_exempt` は **時変**である (ELITE_LIVE / PAIR_PROMOTED は demote で変わる)。
   P0 は**現在の**ポートフォリオを静的集合として使っており、
   当時 exempt だった bb_rsi_reversion / session_time_bias / fib_reversal / vix_carry_unwind
   (Overlap pilot の承認済み carve-out) 等を「違反」と数えていた。
2. 違反行の**時間分布が決定的**: 2026-04 で 26/84 (31.0%) → 06 で 58/115 (50.4%)
   → 07 で 10/27 (37.0%) → **2026-08 で 0/12 (0.0%)**。
   基準率 ~35% のもとで 12 行連続ヒットゼロの確率は ≈0.6% = 偶然ではない。
   違反セルの最終出現日は全て demote 時期と一致する (vix 07-30 / ny_close 07-08 /
   bb_rsi 07-02 / session_time_bias 06-04 …)。
3. **再構成は engine の読み出し経路と同一であることをコードで直接確認した**:
   `_regime_type_r = sig["regime"]["regime"]` (`demo_trader.py:5139`) ↔
   本ツールの `_regime_type()` ↔ 読み戻し側 `demo_db.py:2135-2136`
   (`json.loads(t["regime"]).get("regime")`) が三者一致。
   regime 非依存の 7 ブロック (B1/B2/B3/B6/B7/B8/B10) は instrument/hour/direction のみで
   曖昧性ゼロ。加えて本番 `block_counts` に `daytrade_eur:session_pair` が計上されており
   B1/B2 が現に発火していることも確認。

→ **P0 は PASS と判定する。** ただしこれは pre-reg の字義を私が上書きしたのではなく、
**チェックの前提 (exempt 集合が時不変) が誤りだったことを独立証拠で示した**上での判定である。
判断の可否を読者が再検証できるよう、生の 104 行と月次分布を上記に残す。

> **教訓 (lessons へ): 妥当性チェックは「性質」を pin せよ、「代理」を pin するな。**
> P0 は「再構成が engine と一致するか」という**性質**を検証したかったのに、
> 「今日の exempt 集合に入っているか」という**時変の代理**を pin していた。
> PR #209 の「構造 pin は構文でなく性質を書け」と同型の誤りが、
> 今度は**統計の妥当性チェック側**で再発した (通算 2 領域目)。

### Post-hoc 観察 (**claimable ではない / §3 の測定リストに無い**)

上記 PREMISE-INTACT は **全 shadow 母集団 (N=11,548)** の判定である。しかし
そのうち **live 転送が現に可能なセル (min-lot bypass 9 + kalman 3 + PAIR_PROMOTED 3)
は 462 行 = 4.0% にすぎない**。この層に限ると像が変わる:

| blk | N | WR | EV_gross | EV_net | p |
|---|---|---|---|---|---|
| B3 | 26 | 19.2% | −2.45 | −4.45 | <1e-4 |
| B4 | 22 | 27.3% | +0.45 | −1.85 | 0.292 |
| B5 | 18 | 33.3% | −2.14 | −4.37 | 0.007 |
| **B7 (H13 USD_JPY)** | **17** | **64.7%** | **+1.27** | **−0.87** | **0.385** |
| **B8 (H16-20 USD_JPY)** | **26** | **57.7%** | **+1.09** | **−1.05** | **0.272** |
| B9 | 9 | 77.8% | +2.99 | +0.10 | 0.534 |
| B10 | 10 | 20.0% | −2.25 | −4.25 | 0.0005 |
| B1/B2/B6 | 6/3/5 | — | — | — | — |

**B7/B8 — 2026-09-01 readout が名指しした 2 件 — は live 可能セルに限ると
gross EV が正 (+1.27 / +1.09)、WR 57.7〜64.7% に反転し、p は有意でない。**

**この観察では何も動かせない。** 理由を明示する:
1. **N=17/26 は本 pre-reg 自身の N≥30 に届かない** (§4 の UNDERPOWERED に相当)
2. **post-hoc** である — §3 の測定リストに層別は無く、
   全母集団の結果を見た後に定義した層である (top-by-EV 凍結が最過学習セルを選ぶのと
   同じ選択バイアス構造: [[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]])
3. **shadow EV は BE/Trail で楽観**。§3 で先に宣言したとおり、
   shadow が正でも live に伝わる保証はゼロ ([[friction-adjusted-ev-map-2026-07-07]] で実証済)
4. 層の中身は donchian 182 / vix 107 / bb_squeeze 91 が主で、
   **vix は demote 済・donchian は gate block 中** = 「live 可能」の定義自体が緩い

→ **B7/B8 のブロックは維持。** 本観察は次の pre-reg の estimand として登録するに留める
(registry `alpha-scan-b7-b8-livecell-recheck`)。

### 測定ツール自身の欠陥を 1 件検出・修正した

§6.4 の「再実行で同じ数字が出ること」を満たすため境界値テスト
(`tests/test_alpha_scan_block_recalibration.py`) を書いたところ、**初回実行で落ちた**。

原因は本ツールの B1 条件 `(_utc_hour(r) or 99) < 7` — **hour==0 が falsy** なので
東京時間 0 時台の EUR_USD 行が丸ごと条件から漏れていた。
修正後 B1 は **N 174 → 241 / EV_net −2.85 → −3.13**。verdict は PREMISE-INTACT のまま不変。

同型の書き方をしていた B2/B8 も `h is not None` 形へ統一した (両者は元から
`-1` 既定で正しく動いていたが、書き方が揃っていないこと自体が次の事故の温床)。

**counterfactual**: テスト suite に意図的欠陥 3 種 (B9 閾値 70→65 の取り違え /
B7 の instrument scoping 除去 / `BONFERRONI_M` をブロック数と乖離させる) を注入し、
**3/3 が所望どおり失敗**することを確認した。B1 の実欠陥検出と合わせて 4/4。

### 帰結

- **コード変更ゼロ。** 10 ブロックすべて現状維持
- 較正値コメント (2026-04-14 の N=9〜89) は**新実測に更新**してよい (docstring のみ、挙動不変)
- **2026-09-01 の「静的 hour block が NY live を削っている」仮説は、全母集団水準では反証された**。
  live 頻度問題の主因はセル構成 (6 月世代の R2 demote) に確定し、
  hour block は容疑者リストから外れる — ただし live 可能セル層 (N=17/26) は未決着
