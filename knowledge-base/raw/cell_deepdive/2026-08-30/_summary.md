# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-08-30

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しない (7週連続)。前週までと同一の ad-hoc 再実装 (`_run_deepdive_2026_08_30.py` = `_run_deepdive_2026_08_23.py` の RUN_DATE 差分のみ、`cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` は非対応 (regime / hour_bin / mode 軸なし。cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD, HTTP 200 / 51.0MB)。ローカル demo_trades.db は STALE (memory rule 準拠)
- **Window**: 365d 指定、実データ span 2026-04-02 → **2026-08-28T20:54Z**
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 16,718 (+247) / target raw 778 (+18) / dedup 除外 413 / non-WL 除外 22 / **clean N = 343 (+10)** / m_global v2 = 6, v3 = 1
- **前回比較基準**: 2026-08-23 run

## PAIR_PROMOTED Candidates

ツール出力上 **1 件** (前週と同一セル)。ただし §「pre-reg LOCK 抵触」により **actionable candidate は 0 件**。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | **Tokyo** | (未分解) | (未分解) | (未分解) | BUY | 32 | 71.9% | 0.546 | +7.11 | 4.29 | 0.0133 | 0.551 | ✅ |

前週差分: N 28→32 / WR 71.4→71.9% / Wilson_lo 0.529→0.546 / EV +7.94→+7.11 / PF 4.25→4.29。

### 🔴 昇格提案しない — 前週と同一の 2 点で pre-reg LOCK に抵触

[[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] が本セルの forward 確認枠を LOCK 済 (registry `sr-anti-hunt-eurjpy-buy-forward-confirm`)。

1. **sub-cell 切りの明示禁止** — pre-reg は「セル = EUR_JPY × **BUY**。**Tokyo 条件は付けない — さらなる sub-cell 切りは vix Overlap の selective inference 前例により禁止**」と明記。本候補はまさにその Tokyo sub-cell
2. **中間再計算の禁止 (P-10 型)** — 判定は「fresh N≥40 到達時に 1 回限り」。weekly deepdive は毎週この cell を再計算しており、**ツール自体が LOCK と構造的に衝突**

多重性でも独立には支持されない: `p_bonf = p_raw` は v3 grid の N≥20 セルが 1 個 (`m_v3=1`) だからで多重性ペナルティが実質ゼロ。探索族を v2∪v3 (m=7) で取れば **p_bonf = 0.0133 × 7 = 0.0931 → α=0.05 FAIL** (前週 0.163 から改善したが依然不通過)。親セルを見た後に Tokyo を切った順序を考えれば m=7 側が正しい。

**de-clustering: 3 検定中 2 つで gate 未通過** (単日クラスタ依存が継続):

| 母集団 | N | WR | Wilson_lo | EV_net | PF | gate (Wilson_lo>0.50) |
|---|---|---|---|---|---|---|
| Tokyo BUY 全体 | 32 | 71.9% | **0.546** | +7.11 | 4.29 | ✅ |
| − 最良単日 (2026-05-26, 5本 +118.1p) | 27 | 70.4% | 0.515 | +4.06 | 2.62 | ✅ (前週 0.491 → 今週 PASS) |
| − hot-streak 日 (05-25, 07-17) | 26 | 65.4% | 0.462 | +6.17 | 3.32 | ❌ |
| 1-trade-per-day cap | 17 | 58.8% | 0.360 | +3.42 | 2.46 | ❌ |

Tokyo cell 累計 +227.6p のうち **2026-05-26 単日で +118.1p (52%)**、05-25+05-26 の 2 日で +170p (75%)。「2026-05 一山型」構造は不変。32本中 30本が shadow。

## 🟡 pre-reg forward 枠: 予測された N≥40 到達は起きなかった — 決裁窓はまだ開いている

pre-reg 母集団 (`sr_anti_hunt_bounce × EUR_JPY × BUY`, dedup_violation=0, shadow, **entry_time ≥ 2026-08-05**) の enrollment (件数のみ。P-10 に従い outcome 側統計は判定根拠に使用しない):

- **fresh OOS N = 32 / 40** (2026-08-07T05:19 → 2026-08-28T05:01、全て shadow)
- 前週予測「12.2本/週 → 2026-08-30 run で N≥40 到達」は **外れ**。実績は 8日で +5本 = **4.4本/週へ失速**
- 再推定 ETA: **N≥40 到達は 2026-09-13 〜 09-20 頃** (約 2〜3 週後)
- 凍結後の月次バケット: 2026-08 の 1 ヶ月のみ (変化なし)

→ 前週提起した**判定条件の内部矛盾は未解消のまま有効**: 「fresh N≥40 で 1 回限り判定」と条件③「凍結後月次符号 ≥3/4」(最低 4 ヶ月 = 最速 2026-11〜12) が両立しない。このまま N≥40 で one-shot 発火すると ③ が自動 FAIL し、**証拠ではなく仕様不整合を理由に本セルが close される**。

**幸い蓄積失速により決裁期限が約 2 週延びた。** 選択肢 (前週提示、変更なし):
- (A) トリガを「fresh N≥40 **かつ** 月次バケット≥4」の連言に改訂 (充足最速 = 2026-12)
- (B) ③ を「凍結後月次符号 ≥2/2 (観測済みバケット基準)」等へ緩和し N≥40 で予定通り発火
- (C) **[推奨]** N トリガを撤去し「2026-12 月末 1 回限り」の日付トリガへ置換 — 日付は outcome を見ずに決まるため selective inference 耐性が最も高く、③ を無改訂で維持できる

いずれも pre-reg の改訂 = 事前凍結の変更のため、**N が 40 を跨ぐ前に user が明示決裁し LOCK を再発行**する必要がある (事後変更は selective inference)。

## 🔻 親セル (v2 EUR_JPY BUY): Wilson_lo は 0.50 を回復したが gate は依然 FAIL

| run | N | WR | Wilson_lo | EV_net | PF | p_bonf | wf_stable | promoted |
|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | 35 | 74.3% | 0.579 | +5.01 | 2.66 | 0.0081 | ✅ | ✅ |
| 2026-07-26 | 38 | 71.1% | 0.552 | +4.29 | 2.35 | 0.0378 | ✅ | ✅ |
| 2026-08-09 | 40 | 70.0% | 0.546 | +4.17 | 2.31 | 0.0456 | ✅ | ✅ |
| 2026-08-23 | 67 | 61.2% | 0.492 | +2.15 | 1.61 | 0.4012 | ❌ | ❌ |
| **2026-08-30** | **71** | **62.0%** | **0.503** | **+2.10** | **1.63** | **0.2618** | **❌** | **❌** |

Wilson_lo は 0.50 をわずかに回復したが、**p_bonf 0.2618 と wf_stable ❌ で 2 ゲート未通過**。前週の gate 喪失は撤回されない。

session 別内訳 (mix 悪化の継続を確認):

| session | N | WR | Wilson_lo | EV_net | PF |
|---|---|---|---|---|---|
| Tokyo | 32 | 71.9% | 0.546 | **+7.11** | 4.29 |
| NY | 17 | 47.1% | 0.262 | **−4.56** | 0.34 |
| overlap_LN | 14 | 64.3% | 0.388 | +0.83 | 1.41 |
| London | 8 | 50.0% | 0.215 | −1.54 | 0.42 |

thesis (Tokyo 片側性) は生存、**負けセッション (NY/London) での発火が親セルの黒字を食う構造も不変**。

## 7 戦略別サマリ (前週差分付き)

| strategy | raw (Δ) | clean N (Δ) | WR | Wilson_lo | EV_net | PF | 状態 |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 432 (+12) | 226 (+6) | 54.0% | 0.475 | **−1.56** | 0.68 | 集計は net-negative。黒字は Tokyo BUY のみ |
| vsg_jpy_reversal | 73 (+1) | 44 (+1) | 68.2% | 0.534 | +1.05 | 1.23 | 最健全。N≥20 で v2 未 eligible の pair 分散 |
| rsk_gbpjpy_reversion | 143 (+4) | 41 (+2) | 56.1% | 0.410 | −2.25 | 0.66 | 集計は負。BUY cell のみ後述 |
| vdr_jpy | 38 (**+0**) | 24 (+0) | 66.7% | 0.467 | +1.67 | 1.21 | **2週連続 発火ゼロ** |
| mqe_gbpusd_fix | 88 (+1) | 6 (+1) | 66.7% | 0.300 | +5.85 | 2.53 | raw 88 中 82 が除外 (dedup/未決済) — 歩留まり 6.8% |
| sr_liquidity_grab | 4 (+0) | 2 (+0) | — | — | — | — | 実質デッド |
| cpd_divergence | **0 (+0)** | 0 | — | — | — | — | **6週連続 発火ゼロ** |

**watch: `rsk_gbpjpy_reversion | GBP_JPY | BUY`** — N 22→24 / WR 68.2→70.8% / Wilson_lo 0.473→0.508 / EV +0.35→**+0.77** / PF 1.06→1.14 / p_bonf 0.2474 / wf_stable ❌。前週登録した「SELL 側片側性」仮説は N 増でも維持。ただし **EV +0.77p は friction 内、PF 1.14 と wf ❌** で昇格軸には遠い。追跡継続。

## 判定

**actionable な PAIR_PROMOTED 候補は 0 件。** ツール出力の 1 件は pre-reg LOCK が明示禁止した sub-cell 切りであり、多重性 (m=7 → p_bonf 0.0931) でも de-clustering (3検定中2つ FAIL) でも独立には支持されない。親セルは Wilson_lo こそ 0.50 を回復したが p_bonf / wf_stable の 2 ゲートで FAIL。

推奨アクション (優先順):

1. **【要 user 決裁 / 新期限 ≈ 2026-09-13】pre-reg 判定トリガの仕様矛盾を解消** — 蓄積失速 (32/40, 4.4本/週) により窓が約2週延びた。(A)/(B)/(C) から選択し**観測前に** LOCK 再発行。推奨 (C)
2. **weekly deepdive ツールに pre-reg 抑制リストを実装** (2週連続提言、未着手) — LOCK 済セルとその sub-cell を candidate 出力から除外し「enrollment N / 40」のみ表示する。現状ツールは毎週 P-10 禁止の中間再計算を行い、禁止された sub-cell を候補として提示している (**ツール側の設計欠陥**)
3. **Live 昇格は不可 (据え置き)** — Rule 1 要件は 365d BT PASS (ハーネス破綻で評価不能) / Live N≥30 (N=4 かつ負) いずれも未達
4. **vdr_jpy を candidate 母集団から外す判断** — 2週連続で発火ゼロ、N=24 のまま固定。前週提言どおり watch 筆頭から撤回
5. **mqe_gbpusd_fix の歩留まり調査** — raw 88 → clean 6 (93% 除外)。dedup_violation の異常多発か未決済滞留かの切り分けが必要
6. **発火枯渇 3 戦略 (cpd_divergence / sr_liquidity_grab / vdr_jpy) の signal 経路調査を別タスク化** (6週連続提言、未着手)
7. **weekly 系列の main 集約** — 本 run 含む成果物が main 未 merge

## Related
- [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] — 本セルの pre-reg LOCK 本文
- [[bt-harness-effective-stop-booking-2026-08-05]] — 2026-08-05 BT FAIL は評価不能 (エッジ不在の証拠ではない)
- `knowledge-base/raw/cell_deepdive/2026-08-23/_summary.md` — 前週 run
