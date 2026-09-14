# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-09-13

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しない (**9週連続**)。前週と同一の ad-hoc 再実装 (`_run_deepdive_2026_09_13.py` = `_run_deepdive_2026_09_06.py` の RUN_DATE 差分のみ、`cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` は非対応 (regime / hour_bin / mode 軸なし。cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD, HTTP 200 / 54.2MB)。ローカル demo_trades.db は STALE (memory rule 準拠)
- **Window**: 365d 指定、target clean rows の実 span **2026-04-28 → 2026-09-11T07:16Z**
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 17,589 (+423) / target raw 810 (+18) / dedup 除外 421 / non-WL 除外 22 / **clean N = 367 (+12)** / m_global v2 = 6, v3 = 1
- **前回比較基準**: 2026-09-06 run

## PAIR_PROMOTED Candidates

ツール出力上 **1 件** (3週連続で同一セル・同一数値)。**actionable candidate は 0 件** (pre-reg LOCK 抵触、理由は前週と同一)。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | **Tokyo** | (未分解) | (未分解) | (未分解) | BUY | 32 | 71.9% | 0.546 | +7.11 | 4.29 | 0.0133 | 0.551 | ✅ |

**前週差分ゼロ** (N/WR/Wilson_lo/EV/PF/p_bonf すべて同一)。このセルは 2026-08-28T05:01 を最後に **14日間 1本も追加されていない**。

昇格しない理由 (前週から不変):
1. **sub-cell 切りの明示禁止** — [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] の pre-reg は「セル = EUR_JPY × BUY。**Tokyo 条件は付けない**」と明記。本候補はその Tokyo sub-cell
2. **中間再計算の禁止 (P-10 型)** — 判定は「fresh N≥40 到達時に 1 回限り」。weekly deepdive が毎週再計算しており、ツール自体が LOCK と構造的に衝突
3. 多重性: `m_v3=1` ゆえ p_bonf=p_raw。探索族を v2∪v3 (m=7) で取れば p_bonf = 0.0931 → α=0.05 **FAIL**

## ⚠️ 前週レポートの 2 つの主張を今週データが falsify した

### ① 「`sr_anti_hunt_bounce` 固有の発火崩壊、発火経路の調査が必要」→ **誤り**

週次 raw 発火数 (XAU 除外):

| strategy | 07-20 | 07-27 | 08-03 | 08-10 | 08-17 | 08-24 | 08-31 | 09-07 |
|---|---|---|---|---|---|---|---|---|
| **sr_anti_hunt_bounce** | 31 | 14 | 9 | 62 | 25 | 12 | 3 | **15** |
| sr_liquidity_grab | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| cpd_divergence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| vdr_jpy | 1 | 7 | 1 | 5 | 0 | 0 | 4 | 0 |
| vsg_jpy_reversal | 1 | 3 | 1 | 0 | 2 | 1 | 2 | 3 |
| rsk_gbpjpy_reversion | 5 | 4 | 5 | 2 | 6 | 4 | 5 | 0 |
| mqe_gbpusd_fix | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| ALL STRATEGIES | 615 | 856 | 573 | 498 | 416 | 247 | 450 | 421 |

前週は 62→25→12→3 を「単調崩壊」と読み silent-drop 調査を推奨したが、09-07 週に **15 本へ回復**。**単なる 1 週の凪であり、発火経路の欠陥ではない。** 前週の推奨 (発火経路調査) は取り下げる。8週の系列で 3 は下限ではあるが、9→62 の振れ幅を見れば分散内。

ただし **pair mix は入れ替わっている**:

| week | EUR_JPY BUY | EUR_JPY SELL | EUR_USD | GBP_JPY | USD_JPY | GBP_USD |
|---|---|---|---|---|---|---|
| 08-24 | 4 | 0 | 0 | 0 | 0 | 2 |
| 08-31 | 0 | 2 | 0 | 1 | 0 | 0 |
| 09-07 | **0** | 1 | 7 | 0 | 1 | 0 |

pre-reg 母集団 (EUR_JPY × BUY) だけが **2週連続 0 本**。発火自体は EUR_USD へ移っている。

### ② 「直近の −19.8 / −23.5p は桁違い、SL 距離の実効値が変わった可能性」→ **誤り**

戦略レベル (dedup=0, WIN/LOSS, XAU 除外) の月次ペイオフ:

| month | N | WR | avg_win | avg_loss | R:R | EV_net | worst_loss |
|---|---|---|---|---|---|---|---|
| 2026-04 | 6 | 0.0% | — | 19.13 | — | −19.13 | −24.6 |
| 2026-05 | 48 | 33.3% | 19.03 | 8.28 | **2.30** | +0.82 | −36.1 |
| 2026-06 | 51 | 62.7% | 3.67 | 13.65 | 0.27 | −2.78 | −51.3 |
| 2026-07 | 56 | 73.2% | 3.54 | 14.05 | 0.25 | −1.17 | **−71.7** |
| 2026-08 | 66 | 51.5% | 5.86 | 8.30 | 0.71 | −1.01 | −20.2 |
| 2026-09 | 11 | 45.5% | 0.78 | 17.65 | 0.04 | −9.27 | −23.5 |

avg_loss は 4月以降ずっと 8〜19p、worst loss は −36.1 / −51.3 / **−71.7** が既に存在する。**−19.8 / −23.5p は歴史的損失分布の内側であり、異常ではない。** 前週が「桁違い」と判定したのは、比較基準を戦略の損失分布ではなく Tokyo BUY sub-cell の ±2〜3p 帯に取っていたため。**SL contract 乖離を示す証拠はない** — [[project_carrydip_sl_contract_and_slhit_label_2026_08_05]] 型のクロス確認推奨は取り下げる。

## 🔴 本当の構造的問題 — R:R 反転 (前週レポートが見落としていた本体)

上表の `R:R` 列が本質。**2026-05 の 2.30 を最後に 0.27 / 0.25 / 0.71 / 0.04 へ反転したまま戻っていない。**

- 06月・07月は **WR 62.7% / 73.2% と高い**のに EV は −2.78 / −1.17。勝率は出ているが 1 勝が 1 敗を取り返せない
- これは [[feedback_partial_quant_trap]] の典型 — WR だけ見れば健全、ペイオフを見ると破綻
- 戦略レベル累計も悪化継続: EV −1.71 → **−1.89** p、PF 0.66 → **0.63** (前週比)
- 構造は [[project_carrydip_sl_contract_and_slhit_label_2026_08_05]] の「R:R 反転でペイオフが裏返る」と**同型だが、原因は SL 距離ではない** (§②)。avg_win が 19.03 → 3.5〜5.9p へ縮んだ側の寄与が大きく、**利確側 (TP / early exit) の変化**を疑うべき

**推奨**: 次回 audit の主題を「セル昇格探索」から **「2026-05→06 で avg_win が 1/5 に縮んだ原因の実測特定」** へ切り替える。exit_reason 別の分解 (TP_HIT / SL_HIT / TIME_EXIT / 手動) が第一手。[[feedback_label_empirical_audit]] に従いコード演繹ではなくラベル×実測で。

## 候補セル自体の再検証 — 「2026-05 一山」説は今週データで支持されない

前週は本セルを「2026-05 一山型」としたが、月別内訳は **08月 11 / 05月 11 / 07月 7 / 04月 2 / 06月 1** で May 偏重ではない。May を落とした cut も gate を通る:

| 期間 | N | WR | Wilson_lo | EV | PF | R:R |
|---|---|---|---|---|---|---|
| 2026-05 (cell birth) | 11 | 72.7% | 0.434 | +16.41 | 11.43 | 4.29 |
| **2026-06 以降** | 19 | 78.9% | **0.567** ✅ | +4.15 | 4.93 | 1.31 |

**post-May 単独で Wilson_lo 0.567 > 0.50 を維持**。戦略全体が R:R 反転している中で、この sub-cell だけ R:R 1.31 を保っている点はむしろ注目に値する。

一方 pips 総額の集中は事実 (de-clustering、前週から数値変化なし):

| 母集団 | N | WR | Wilson_lo | EV_net | PF | gate (Wilson_lo>0.50) |
|---|---|---|---|---|---|---|
| Tokyo BUY 全体 | 32 | 71.9% | 0.546 | +7.11 | 4.29 | ✅ |
| − 最良単日 (2026-05-26, 5本 +118.1p) | 27 | 70.4% | 0.515 | +4.06 | 2.62 | ✅ |
| − hot-streak 2日 (05-25, 05-26) | 24 | 66.7% | 0.467 | +2.40 | 1.85 | ❌ |
| 1-trade-per-day cap | 17 | 58.8% | 0.360 | +3.42 | 2.46 | ❌ |

累計 +227.6p のうち 05-26 単日で +118.1p (52%)、上位2日で +170.0p (75%)。32本中 30本が shadow。

**総合**: 本セルを止めているのは統計的弱さではなく **手続き (pre-reg LOCK の sub-cell 禁止 + P-10)**。この非対称を次回 R3 決裁の論点として明示すべき。

## pre-reg forward 枠 enrollment

pre-reg 母集団 (`sr_anti_hunt_bounce × EUR_JPY × BUY`, dedup=0, shadow, entry_time ≥ 2026-08-05) — 件数のみ (P-10 に従い outcome 統計は判定根拠に使わない):

- **fresh OOS N = 32 / 40** (WIN/LOSS)。全 outcome では 33 (BREAKEVEN 1 が今週新たに確定)
- **今週の +1 は新規 enrollment ではなく既存 open trade の決済**。span は **2026-08-07T05:19 → 2026-08-28T05:01 で据え置き**
- 週次 enrollment: 20 (08-10週) → 8 → 4 → **0 → 0**
- **ETA 算出不能**。前週の「宙吊り」失敗モードが 2 週連続で継続

§①より、これは戦略の発火停止ではなく **EUR_JPY BUY だけが出なくなった** pair mix の変化。EUR_USD へ発火が移った理由 (価格構造か、pair 選択ロジックか) は未調査。

## 7 戦略サマリ (clean rows, 前週差分)

| strategy | raw | clean N | Δ | WR | Wilson_lo | EV_net | PF |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 450 | 238 | +9 | 53.8% | 0.474 | **−1.89** ↓ | **0.63** ↓ |
| sr_liquidity_grab | 4 | 2 | 0 | 100% | 0.342 | +1.95 | — |
| cpd_divergence | 0 | 0 | 0 | — | — | — | — |
| vdr_jpy | 42 | 26 | 0 | 65.4% | 0.462 | +1.80 | 1.24 |
| vsg_jpy_reversal | 78 | 49 | +3 | 65.3% | **0.513** | +0.55 ↓ | 1.12 ↓ |
| rsk_gbpjpy_reversion | 148 | 46 | 0 | 54.3% | 0.402 | −2.96 | 0.60 |
| mqe_gbpusd_fix | 88 | 6 | 0 | 66.7% | 0.300 | +5.85 | 2.53 |

- `cpd_divergence` は **通算 0 発火** (9週連続)。実装が生きているかの確認が必要
- `vsg_jpy_reversal` は Wilson_lo 0.513 で戦略レベル gate を通るが N=49、EV は +0.73 → +0.55 と希薄化中。**v2/v3 セル分解では N≥20 に届かず候補化せず**
- `rsk_gbpjpy_reversion` / `mqe_gbpusd_fix` は今週 clean 増分 0

## 次アクション

1. **(最優先)** `sr_anti_hunt_bounce` の avg_win 縮小 (19.03 → 3.5〜5.9p) を exit_reason 別実測で分解。セル探索より上位
2. pre-reg セルは **触らない** (P-10)。EUR_JPY BUY の発火停止 = pair mix 変化であることのみ記録
3. `cpd_divergence` の 0 発火を確認 (9週連続、経路断の可能性)
4. 前週レポートの §① §② は本レポートで訂正済。`wiki/audit-index.md` 側の参照があれば更新
