# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-09-06

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しない (**8週連続**)。前週までと同一の ad-hoc 再実装 (`_run_deepdive_2026_09_06.py` = `_run_deepdive_2026_08_30.py` の RUN_DATE 差分 + 後述の window bug fix、`cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` は非対応 (regime / hour_bin / mode 軸なし。cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD, HTTP 200 / 52.7MB)。ローカル demo_trades.db は STALE (memory rule 準拠)
- **Window**: 365d 指定、target clean rows の実 span **2026-04-28 → 2026-09-04T00:16Z** (payload 全体では 2026-04-02 → 2026-09-04T17:33Z)
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 17,166 (+448) / target raw 792 (+14) / dedup 除外 415 / non-WL 除外 22 / **clean N = 355 (+12)** / m_global v2 = 6, v3 = 1
- **前回比較基準**: 2026-08-30 run

### 🔧 本 run で 1 件 bug fix (`window` フィールド)

前週までの runner は `"window": "365d (data span 2026-04-02 -> 2026-08-28)"` を**ハードコード文字列**で持っており、コピー元の日付が固定されたまま毎週出力されていた。今週この literal をそのまま信じると「PROD データが 08-28 で止まっている」と誤読する (実際は 09-04 まで新鮮)。`clean` 行から動的に min/max を計算するよう修正済。過去 run の `window` 値は信頼しないこと。

## PAIR_PROMOTED Candidates

ツール出力上 **1 件** (前週と同一セル)。ただし §「pre-reg LOCK 抵触」により **actionable candidate は 0 件**。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | **Tokyo** | (未分解) | (未分解) | (未分解) | BUY | 32 | 71.9% | 0.546 | +7.11 | 4.29 | 0.0133 | 0.551 | ✅ |

**前週差分: 完全にゼロ (N/WR/Wilson_lo/EV/PF/p_bonf すべて bit 単位で同一)。** このセルは 2026-08-28T05:01 を最後に **7日間 1本も追加されていない** (詳細は下記 🔴 セクション)。

### 🔴 昇格提案しない — 前週と同一の 2 点で pre-reg LOCK に抵触

[[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] が本セルの forward 確認枠を LOCK 済 (registry `sr-anti-hunt-eurjpy-buy-forward-confirm`)。

1. **sub-cell 切りの明示禁止** — pre-reg は「セル = EUR_JPY × **BUY**。**Tokyo 条件は付けない — さらなる sub-cell 切りは vix Overlap の selective inference 前例により禁止**」と明記。本候補はまさにその Tokyo sub-cell
2. **中間再計算の禁止 (P-10 型)** — 判定は「fresh N≥40 到達時に 1 回限り」。weekly deepdive は毎週この cell を再計算しており、**ツール自体が LOCK と構造的に衝突**

多重性でも独立には支持されない: `p_bonf = p_raw` は v3 grid の N≥20 セルが 1 個 (`m_v3=1`) で多重性ペナルティが実質ゼロだから。探索族を v2∪v3 (m=7) で取れば **p_bonf = 0.0133 × 7 = 0.0931 → α=0.05 FAIL**。親セルを見た後に Tokyo を切った順序を考えれば m=7 側が正しい。

**de-clustering: 3 検定中 2 つで gate 未通過** (単日クラスタ依存が継続、前週から数値変化なし):

| 母集団 | N | WR | Wilson_lo | EV_net | PF | gate (Wilson_lo>0.50) |
|---|---|---|---|---|---|---|
| Tokyo BUY 全体 | 32 | 71.9% | **0.546** | +7.11 | 4.29 | ✅ |
| − 最良単日 (2026-05-26, 5本 +118.1p) | 27 | 70.4% | 0.515 | +4.06 | 2.62 | ✅ |
| − hot-streak 2日 (05-25, 05-26) | 24 | 66.7% | 0.467 | +2.40 | 1.85 | ❌ |
| 1-trade-per-day cap | 17 | 58.8% | 0.360 | +3.42 | 2.46 | ❌ |

Tokyo cell 累計 +227.6p のうち **2026-05-26 単日で +118.1p (52%)**、05-25+05-26 の 2 日で +170p (75%)。「2026-05 一山型」構造は不変。32本中 30本が shadow。

## 🚨 今週の主要発見 — pre-reg forward 枠の enrollment が **停止**した (蓄積失速ではない)

pre-reg 母集団 (`sr_anti_hunt_bounce × EUR_JPY × BUY`, dedup_violation=0, shadow, **entry_time ≥ 2026-08-05**) の enrollment (件数のみ。P-10 に従い outcome 側統計は判定根拠に使用しない):

- **fresh OOS N = 32 / 40 — 前週から +0本**
- span 2026-08-07T05:19 → **2026-08-28T05:01 で打ち止め**。直近 7日間の新規 enrollment = **0**
- 週次実績の推移: 12.2本/週 (〜08-23) → 4.4本/週 (〜08-30) → **0本/週 (〜09-06)**
- 前週の再推定 ETA「N≥40 は 2026-09-13〜09-20」は**成立しない**。現在の到達速度では **ETA 算出不能 (無限大)**

### 根本原因: `sr_anti_hunt_bounce` 戦略そのものの発火崩壊 (システム全体の問題ではない)

週次 raw 発火数 (XAU 除外、week starting):

| strategy | 07-13 | 07-20 | 07-27 | 08-03 | 08-10 | 08-17 | 08-24 | 08-31 |
|---|---|---|---|---|---|---|---|---|
| **sr_anti_hunt_bounce** | 31 | 31 | 14 | 9 | **62** | 25 | 12 | **3** |
| sr_liquidity_grab | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| cpd_divergence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| vdr_jpy | 6 | 1 | 7 | 1 | 5 | 0 | 0 | 4 |
| vsg_jpy_reversal | 1 | 1 | 3 | 1 | 0 | 2 | 1 | 2 |
| rsk_gbpjpy_reversion | 2 | 5 | 4 | 5 | 2 | 6 | 4 | 5 |
| mqe_gbpusd_fix | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| **ALL STRATEGIES** | 653 | 615 | 856 | 573 | 498 | 416 | **247** | **448** |

**システム全体は 08-24 週の落ち込み (247) から 08-31 週に 448 へ回復している一方、`sr_anti_hunt_bounce` だけが 62→25→12→3 と単調崩壊。** 他 6 戦略は横ばい。したがってプラットフォーム側の停止ではなく本戦略固有の事象。**発火経路の調査が必要** (silent-drop の前例: [[project_kalman_d7_silent_drop_recovery_2026_05_28]] — 5 gate の silent drop で 8日間 0 fire、後に「設計通りの待機」と判明したケースもあるため、コード演繹でなく gate 別 reject カウントの実測が必要)。

### 🟡 併せて要注意: 直近 EUR_JPY 発火の損失スケールが桁違い

`sr_anti_hunt_bounce` の直近 3 発火 (08-31 以降) は全て BUY ではなく、うち EUR_JPY SELL 2本の損失が異常に大きい:

| entry_time | pair | dir | outcome | pnl_pips |
|---|---|---|---|---|
| 2026-08-31T06:16 | GBP_JPY | SELL | WIN | +2.6 |
| 2026-09-03T19:01 | EUR_JPY | SELL | LOSS | **−19.8** |
| 2026-09-04T00:16 | EUR_JPY | SELL | LOSS | **−23.5** |

当該セル群の典型 pnl は ±2〜3 pip 帯 (上記 08-28 の 6本は全て |pnl| ≤ 2.2p)。**−19.8 / −23.5p は 1桁大きく、SL 距離の実効値が変わった可能性**を示唆する。[[project_carrydip_sl_contract_and_slhit_label_2026_08_05]] の「宣言 SL と発注 SL の乖離」パターンと同型のリスクがあるため、この 2 本の宣言 SL vs 実発注 SL のクロス確認を推奨 (本 audit の対象外)。

## 🟡 pre-reg 判定条件の内部矛盾は未解消 (ただし期限圧力は消失)

「fresh N≥40 で 1 回限り判定」と条件③「凍結後月次符号 ≥3/4」(最低 4 ヶ月 = 最速 2026-11〜12) が両立しない構造は前週から不変。凍結後の月次バケットは 2026-08 の 1 ヶ月のみ (変化なし)。

**今週の変化**: enrollment が止まったことで「N≥40 が先に発火して ③ が自動 FAIL する」という差し迫った事故リスクは当面消えた。代わりに **「N トリガが永久に発火せず、セルが未決裁のまま宙吊りになる」**という逆方向の失敗モードが顕在化した。これは選択肢 (C) の相対価値をさらに高める:

- (A) トリガを「fresh N≥40 **かつ** 月次バケット≥4」の連言に改訂 → enrollment 停止下では**永久に発火しない**。今週の状況で最も危険
- (B) ③ を「凍結後月次符号 ≥2/2」等へ緩和し N≥40 で発火 → N≥40 自体が来ないので同じく宙吊り
- (C) **[推奨・前週から推奨度上昇]** N トリガを撤去し「**2026-12 月末 1 回限り**」の日付トリガへ置換 — 日付は outcome にも発火数にも依存しないため、enrollment が 0 のままでも決裁窓が必ず閉じる。selective inference 耐性も最高。③ を無改訂で維持できる

いずれも pre-reg の改訂 = 事前凍結の変更のため、**user の明示決裁と LOCK 再発行**が必要。今週時点では N が 40 を跨ぐ心配はないため決裁に時間的余裕はあるが、「発火が戻らない限り永久に閉じない」状態を放置しない判断が要る。

## 🔻 親セル (v2 EUR_JPY BUY): 前週から完全に不変、gate は依然 FAIL

| run | N | WR | Wilson_lo | EV_net | PF | p_bonf | wf_stable | promoted |
|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | 35 | 74.3% | 0.579 | +5.01 | 2.66 | 0.0081 | ✅ | ✅ |
| 2026-07-26 | 38 | 71.1% | 0.552 | +4.29 | 2.35 | 0.0378 | ✅ | ✅ |
| 2026-08-09 | 40 | 70.0% | 0.546 | +4.17 | 2.31 | 0.0456 | ✅ | ✅ |
| 2026-08-23 | 67 | 61.2% | 0.492 | +2.15 | 1.61 | 0.4012 | ❌ | ❌ |
| 2026-08-30 | 71 | 62.0% | 0.503 | +2.10 | 1.63 | 0.2618 | ❌ | ❌ |
| **2026-09-06** | **71** | **62.0%** | **0.503** | **+2.10** | **1.63** | **0.2618** | **❌** | **❌** |

新規 trade ゼロのため数値は前週と同一。**p_bonf 0.2618 と wf_stable ❌ の 2 ゲート未通過**という前週の判定は撤回されない。

## 全 eligible cells (N≥20)

### v2 (entry_type × pair × direction), m=6

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | wf_stable | promoted |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 71 | 62.0% | 0.503 | +2.10 | 1.63 | 0.2618 | ❌ | ❌ |
| rsk_gbpjpy_reversion \| GBP_JPY \| BUY | 29 | 65.5% | 0.473 | −0.88 | 0.87 | 0.5680 | ❌ | ❌ |
| sr_anti_hunt_bounce \| EUR_USD \| SELL | 26 | 65.4% | 0.462 | −5.13 | 0.31 | 0.7000 | ❌ | ❌ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 46 | 56.5% | 0.422 | −3.31 | 0.50 | 1.0000 | ❌ | ❌ |
| sr_anti_hunt_bounce \| USD_JPY \| BUY | 26 | 57.7% | 0.389 | −0.82 | 0.69 | 1.0000 | ❌ | ❌ |
| vsg_jpy_reversal \| EUR_JPY \| BUY | 22 | 59.1% | 0.387 | −2.33 | 0.56 | 1.0000 | ❌ | ❌ |

**WR > 50% なのに EV_net < 0 のセルが 6 個中 5 個** — [[project_cell_edge_deep_audit_2026_06_08]] の「勝ちは本物だが真因は friction / RR 非対称」構造が本 7 戦略でも継続している。

### v3 (+ session), m=1

| cell | N | WR | Wilson_lo | EV_net | p_bonf | promoted |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| Tokyo \| BUY | 32 | 71.9% | 0.546 | +7.11 | 0.0133 | ✅ (但し LOCK 抵触) |

## 戦略別サマリ (clean N ベース、前週差分)

| strategy | raw | clean_N | Δ | WR | Wilson_lo | EV_net | PF |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 435 | 229 | +3 | 53.7% | 0.472 | **−1.71** | 0.66 |
| sr_liquidity_grab | 4 | 2 | +0 | 100% | 0.342 | +1.95 | — |
| cpd_divergence | 0 | 0 | +0 | — | — | — | — |
| vdr_jpy | 42 | 26 | +2 | 65.4% | 0.462 | +1.80 | 1.24 |
| vsg_jpy_reversal | 75 | 46 | +2 | 65.2% | 0.508 | +0.73 | 1.16 |
| rsk_gbpjpy_reversion | 148 | 46 | +5 | 54.3% | 0.402 | **−2.96** | 0.60 |
| mqe_gbpusd_fix | 88 | 6 | +0 | 66.7% | 0.300 | +5.85 | 2.53 |

- **cpd_divergence は 8週連続で raw 0 件** — 発火経路が生きているか未確認のまま。task 前提の「2026-04-28 時点 0 件 → 修正反映後 4-6 週で N≥30」は本戦略については **4ヶ月経過しても未達**であり、shadow 蓄積待ちではなく**配線調査が必要**な段階
- **mqe_gbpusd_fix は raw 88 に対し clean 6 (93% が dedup/non-WL で脱落)** — dedup_violation の比率が異常に高く、[[project_r2_audit_dedup_contamination_2026_06_08]] 型の重複発注が疑われる
- **sr_liquidity_grab も実質未発火 (raw 4)**

## 結論

- **PAIR_PROMOTED actionable = 0 件** (ツール出力 1 件は pre-reg LOCK 抵触により昇格提案対象外、かつ前週から数値変化ゼロ)
- 今週の実質的な news は候補の統計ではなく **`sr_anti_hunt_bounce` の発火崩壊 (62→3本/週) と forward enrollment の完全停止**
- 7 戦略中 **3 戦略 (cpd_divergence / sr_liquidity_grab / mqe_gbpusd_fix) が実質未稼働**、稼働中の 4 戦略のうち 2 つ (sr_anti_hunt_bounce, rsk_gbpjpy_reversion) は集計 EV がマイナス
