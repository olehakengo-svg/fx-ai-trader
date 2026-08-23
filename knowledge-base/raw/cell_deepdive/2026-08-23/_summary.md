# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-08-23

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しない。前週までと同一の ad-hoc 再実装 (`_run_deepdive_2026_08_23.py` = `_run_deepdive_2026_08_09.py` の RUN_DATE 差分のみ、`cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` は非対応 (regime / hour_bin / mode 軸なし。cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=50000` (PROD, HTTP 200 / 50.1MB)。ローカル demo_trades.db は STALE (memory rule 準拠)。`?limit` 明示必須
- **Window**: 365d 指定、実データ span 2026-04-02 → **2026-08-21T18:46Z**
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 16,471 / target raw 760 / dedup 除外 405 / non-WL 除外 22 / **clean N = 333** / m_global v2 = 6, v3 = 1
- **前回比較基準**: 2026-08-09 (commit `6b0f5ea4`, branch `research/trendline-sweep-12y-pairscope-2026-07-13` — **main 未 merge**)。**2026-08-16 の run は存在せず**、本 run は 2 週分の差分

## PAIR_PROMOTED Candidates

ツール出力上 **1 件**。ただし下記 §「🔴 pre-reg LOCK 抵触」により **actionable candidate は実質 0 件**。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | **Tokyo** | (未分解) | (未分解) | (未分解) | BUY | 28 | 71.4% | 0.529 | +7.94 | 4.25 | 0.0233 | 0.546 | ✅ |

### 🔴 この候補は pre-reg LOCK に抵触するため昇格提案しない

[[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] が 2026-08-05 に本セルの forward 確認枠を **LOCK 済** (registry `sr-anti-hunt-eurjpy-buy-forward-confirm`)。その凍結条項に本候補は 2 点で抵触する:

1. **sub-cell 切りの明示禁止** — pre-reg は「セル = EUR_JPY × **BUY** (方向はここで凍結)。**Tokyo 条件は付けない — さらなる sub-cell 切りは vix Overlap の selective inference 前例により禁止**」と明記。本候補はまさにその Tokyo sub-cell である
2. **中間再計算の禁止 (P-10 型)** — pre-reg は判定を「fresh N≥40 到達時に **1 回限り**」とし、それまで「本セル×outcome の中間再計算禁止」。weekly deepdive は毎週この cell を再計算しており、**ツール自体が LOCK と構造的に衝突している**

さらに多重性の観点でも支持されない: `p_bonf = p_raw` になっているのは v3 grid の N≥20 到達セルが 1 個しかなく `m_v3 = 1` だからで、**多重性ペナルティが実質ゼロ**。探索族を v2∪v3 (m=7) で取れば `p_bonf = 0.0233 × 7 = 0.163` → α=0.05 **FAIL**。親セルを見た後に Tokyo を切った順序を考えれば m=7 側が正しい。

**de-clustering でも gate 未通過** (単日クラスタ依存が継続):

| 母集団 | N | WR | Wilson_lo | EV_net | PF | gate (Wilson_lo>0.50) |
|---|---|---|---|---|---|---|
| Tokyo BUY 全体 | 28 | 71.4% | **0.529** | +7.94 | 4.25 | ✅ |
| − 最良単日 (2026-05-26, 5本 +118.1p) | 23 | 69.6% | 0.491 | +4.53 | 2.56 | ❌ |
| − hot-streak 日 (05-25, 07-17: 3本以上全勝) | 22 | 63.6% | 0.430 | +7.05 | 3.27 | ❌ |
| 1-trade-per-day cap | 16 | 62.5% | 0.386 | +3.69 | 2.51 | ❌ |

Tokyo cell 累計 +222p のうち **2026-05-26 単日で +118.1p (53%)**、05-25+05-26 の 2 日で +170p (76%)。pre-reg が記録した「2026-05 単月 +325.7p / 5月除外で残余 −53.3p の一山型」構造は本週データでも不変。28/28 中 26 本が shadow。

## 🔻 親セル (v2 EUR_JPY BUY) が今週 gate を喪失 — N 増で反転

3 週連続 promoted だった v2 親セルが今週 **初めて全ゲート FAIL**:

| run | N | WR | Wilson_lo | EV_net | PF | p_bonf | wf_stable | promoted |
|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | 35 | 74.3% | 0.579 | +5.01 | 2.66 | 0.0081 | ✅ | ✅ |
| 2026-07-26 | 38 | 71.1% | 0.552 | +4.29 | 2.35 | 0.0378 | ✅ | ✅ |
| 2026-08-09 | 40 | 70.0% | 0.546 | +4.17 | 2.31 | 0.0456 | ✅ | ✅ |
| **2026-08-23** | **67** | **61.2%** | **0.492** | **+2.15** | **1.61** | **0.4012** | **❌** | **❌** |

memory rule 「昇格根拠は N 増で反転」の再実証。**真因は session mix の変化**であり単なる noise ではない:

| session | N | WR | Wilson_lo | EV_net | PF |
|---|---|---|---|---|---|
| Tokyo | 28 | 71.4% | 0.529 | **+7.94** | 4.25 |
| overlap_LN | 14 | 64.3% | 0.388 | +0.83 | 1.41 |
| London | 8 | 50.0% | 0.215 | −1.54 | 0.42 |
| **NY** | **17** | **47.1%** | 0.262 | **−4.56** | **0.34** |

2026-08-10〜08-13 に NY/London/overlap へ発火が集中 (新規 27 本のうち Tokyo は 6 本のみ)。**負けセッションでの発火増が親セルの黒字を食った** — thesis (Tokyo 片側性) は生存、発火分布が悪化。

## Eligible cells (N≥20, v2, m=6)

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 67 | 61.2% | 0.492 | +2.15 | 1.61 | 0.401 | 0.232 | ❌ |
| rsk_gbpjpy_reversion \| GBP_JPY \| BUY | 22 | 68.2% | 0.473 | +0.35 | 1.06 | 0.529 | 0.036 | ❌ |
| sr_anti_hunt_bounce \| EUR_USD \| SELL | 26 | 65.4% | 0.462 | −5.13 | 0.31 | 0.700 | 0 | ❌ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 46 | 56.5% | 0.422 | −3.31 | 0.50 | 1.0 | 0 | ❌ |
| sr_anti_hunt_bounce \| USD_JPY \| BUY | 26 | 57.7% | 0.389 | −0.82 | 0.69 | 1.0 | 0 | ❌ |
| vsg_jpy_reversal \| EUR_JPY \| BUY | 20 | 60.0% | 0.387 | −2.53 | 0.56 | 1.0 | 0 | ❌ |

新規 eligible 2 件 (`rsk_gbpjpy_reversion|GBP_JPY|BUY`, `vsg_jpy_reversal|EUR_JPY|BUY`)。前者は **戦略集計が net-negative (PF0.63) なのに BUY cell だけ WR68.2%/PF1.06** — SELL 側が損失源という片側性の可能性。ただし EV +0.35p は friction 幅以下で実質 breakeven、Wilson_lo 0.473 で gate 未達。次週以降の watch 対象。

## 前週比 (2026-08-09 → 2026-08-23、2週分)

| strategy | clean_N | ΔN | WR | EV_net | PF | 前回PF |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 220 | +53 | 54.1% | −1.60 | 0.68 | 0.64 ↑ |
| sr_liquidity_grab | 2 | 0 | — | — | — | — (死蔵) |
| cpd_divergence | 0 | 0 | — | — | — | — (**20週連続0**) |
| vdr_jpy | 24 | +3 | 66.7% | +1.67 | 1.21 | 1.80 ↓↓ |
| vsg_jpy_reversal | 43 | +2 | 67.4% | +1.01 | 1.22 | 1.22 → |
| rsk_gbpjpy_reversion | 39 | +4 | 53.8% | −2.64 | 0.63 | 0.61 ↑ |
| mqe_gbpusd_fix | 5 | 0 | 60.0% | +6.76 | 2.48 | 2.48 (**7週停滞**) |

合計 clean N: 271 → 333 (**+62 / 2週 = +31/週**)。増分の **85% (53/62) が sr_anti_hunt_bounce** に集中し、うち EUR_JPY BUY への寄与 +27 の大半が負けセッション。

## Notable

- **vdr_jpy が急速に劣化** — 前週まで「最健全 / watch 筆頭」だったが N 21→24 で WR 71.4→66.7%、EV +4.68→+1.67、PF **1.80→1.21**。Wilson_lo も 0.500→0.467 で gate 割れ。N=3 増で PF が 33% 削れた = 前週の 1.80 自体が小標本の上振れだった可能性が高い。**watch 筆頭の地位は撤回**
- **rsk_gbpjpy_reversion は 4週連続悪化から反転** — PF 0.61→0.63、WR 51.4→53.8%。demote 検討水準ではあるが下降トレンドは止まった。判断は次週以降に持ち越しが妥当
- **発火枯渇 3 戦略は依然未解決 (5週連続提言)**: cpd_divergence 20週連続 0 発火 / mqe_gbpusd_fix clean N=5 で 7週停滞 (raw 87 の 94% が dedup/non-WL 除外) / sr_liquidity_grab raw 4・clean 2 で実質死蔵。**signal 発火経路調査の別タスク化が必要**
- **2026-08-16 run の欠落** — weekly cadence が 1 回抜けている。加えて 2026-08-09 の成果物は research branch にのみ commit され main に未 merge。**KB の週次系列が main 上で不連続**

## 🔴 最重要: pre-reg forward 確認枠の判定トリガが約1週後に到達、かつ判定条件が内部矛盾

pre-reg 母集団 (`sr_anti_hunt_bounce × EUR_JPY × BUY`, dedup_violation=0, shadow, **entry_time ≥ 2026-08-05**) の enrollment 状況 (件数のみ。P-10 に従い outcome 側の中間統計は判定根拠に使用しない):

- **fresh OOS N = 28 / 40** (2026-08-07T05:19 → 2026-08-20T15:31、全て shadow)
- 蓄積レート 28本/16日 = **12.2本/週** → **N≥40 は約1週後 (2026-08-30 の weekly run 時点) に到達見込み**
- 凍結後の月次バケット: **2026-08 の 1 ヶ月のみ**

**判定条件の内部矛盾**: pre-reg は「fresh N≥40 到達時に **1 回限り**」判定とし、条件③に「凍結後**月次符号 ≥3/4**」を課す。しかし ③ は最低 4 ヶ月のバケットを要し **最速でも 2026-11〜12 まで充足不能**。一方 N≥40 は約1週後に到達する。**この順序のまま one-shot を発火させると条件③が自動 FAIL し、証拠ではなく仕様不整合を理由に本セルが close される。**

→ **N が 40 を跨ぐ前 (= 次週 run まで) に user 決裁が必要** (R3 相当の pre-reg 仕様明確化)。取り得る選択:
- (A) 判定トリガを「fresh N≥40 **かつ** 月次バケット≥4」の連言に改訂 (③ を満たせる最速 = 2026-12)
- (B) ③ を「凍結後月次符号 ≥2/2 (観測済みバケット基準)」等へ緩和し N≥40 で予定通り発火
- (C) 期限 2027-02-28 を活かし、N トリガを撤去して「2026-12 月末 1 回限り」の日付トリガへ置換

いずれも **pre-reg の改訂 = 事前凍結の変更**なので、観測前に user が明示決裁し LOCK を再発行する必要がある (事後変更は selective inference)。推奨は **(C)** — 日付トリガは outcome を見ずに決まるため selective inference 耐性が最も高く、③ を無改訂で維持できる。

## 参考: 2026-08-05 BT の FAIL は判定材料にならない (既に KB で決着済)

本セルの Rule 1 昇格を止めた `sr-anti-hunt-eurjpy-cell-bt-2026-08-05.json` の gate FAIL (v2_off: N=82 / wins **0** / WR **0.0%** / EV_R **−8.30**) は、[[bt-harness-effective-stop-booking-2026-08-05]] で **ハーネス整合破綻**と原因確定済み (BE/Trail default 反転 + time-decay 疑似ストップを planned sl_m 6.5〜11 ATR のフル損失として記帳する phantom-loss)。修正 commit `c79f84b3` は **BT 実行 (04:08Z = 13:08 JST) の後 (15:49 JST)**。したがって:

- **この FAIL は「エッジが無い証拠」ではない** — 単に評価不能
- 同 KB の結論どおり Python BT は本セルの裁定者になれない (Live > TV > Python BT)。**shadow N 蓄積 (= 本 weekly audit) と TV Pine canon が唯一の証拠経路**
- 逆に「修正済ハーネスで再走すれば PASS するかも」という期待で BT を再走させるのは pre-reg の判定軸外。**再走は R1 再起案時の前提条件としてのみ意味を持つ** (pre-reg 本文が「その時点で BT ハーネス修復済みが前提」と規定)

## 判定

**actionable な PAIR_PROMOTED 候補は 0 件。** ツールが出した 1 件は pre-reg LOCK が明示禁止した sub-cell 切りであり、多重性 (m=7 で p_bonf=0.163) でも de-clustering (Wilson_lo 0.386〜0.491) でも独立には支持されない。親セルは今週 gate を喪失した。

推奨アクション (優先順):

1. **【要 user 決裁 / 期限=次週 run まで】pre-reg 判定トリガの仕様矛盾を解消** — fresh N が約1週後に 40 を跨ぐ。上記 (A)/(B)/(C) から選択し観測前に LOCK 再発行。推奨 (C)。放置すると仕様不整合による誤 close が発生する
2. **weekly deepdive ツールに pre-reg 抑制リストを実装** — LOCK 済セル (`sr-anti-hunt-eurjpy-buy-forward-confirm`) とその sub-cell を candidate 出力から除外し、代わりに「enrollment N / 40」のみ表示する。現状ツールは毎週 P-10 禁止の中間再計算を行い、禁止された sub-cell を候補として提示している (**ツール側の設計欠陥**)
3. **Live 昇格は不可 (据え置き)** — Rule 1 要件は 365d BT PASS (評価不能) / Live N≥30 (N=4 かつ負) いずれも未達。本週の親セル gate 喪失でむしろ後退
4. **vdr_jpy の watch 筆頭撤回** — PF 1.80→1.21 の急落。前週の「最健全」評価は小標本上振れだった可能性。次週も劣化継続なら candidate 母集団から外す
5. **`rsk_gbpjpy_reversion|GBP_JPY|BUY` を新規 watch に登録** — 戦略集計 net-negative 下で BUY cell のみ WR68.2%。SELL 側片側性の仮説として次週以降 N 追跡 (ただし EV +0.35p は friction 内、過度な期待は禁物)
6. **発火枯渇 3 戦略の signal 経路調査を別タスク化** (5週連続提言、未着手)
7. **weekly 系列の main 集約** — 2026-08-09 成果物の main への取り込みと 2026-08-16 欠落の記録
