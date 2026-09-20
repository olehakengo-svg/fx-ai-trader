# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-09-20

> 🔴 **訂正あり (2026-09-20、同日)** — 本レポートには 2 つの欠陥がある。数値を引用する前に
> [[deepdive-dedup-estimand-and-lock-redaction-2026-09-20]] と本文末尾の §訂正 を読むこと。
> 1. 「🔑 今週の主要発見」「🔴 N 枯渇の真因は…」節の **因果主張は falsified**
> 2. pre-reg LOCK 下の 3 セルの outcome 統計を印刷している (**P-10 違反**)
>
> 本ファイルは「実際に何が出力されたか」の記録として **as-run のまま保存**する
> (同じ統計は 08-23 以降 5 週分が既に main にコミット済みで、今週分だけ伏せても
> 封じ込めにはならない)。恒久修正は `tools/cell_deepdive_audit.py` の redaction 層。

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しない (**10週連続**)。前週と同一の ad-hoc 再実装 (`_run_deepdive_2026_09_20.py` = `_run_deepdive_2026_09_13.py` の RUN_DATE 差分のみ、`diff` で検証済) を Render PROD API に対して実行。`--regime-source` は非対応 (regime / hour_bin / mode 軸なし。cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000` (PROD, HTTP 200 / 55.9MB)。ローカル demo_trades.db は STALE (memory rule 準拠)
- **Window**: 365d 指定、target clean rows の実 span **2026-04-28 → 2026-09-18T14:52Z**
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 18,057 (+468) / target raw 834 (+24) / dedup 除外 427 (+6) / non-WL 除外 22 (+0) / **clean N = 385 (+18)** / m_global v2 = 7 (+1), v3 = 1
- **前回比較基準**: 2026-09-13 run
- **Scope**: Live + Shadow (371/385 clean rows が shadow)

## PAIR_PROMOTED Candidates

ツール出力上 **1 件** (**4週連続で同一セル**)。**actionable candidate は 0 件** (pre-reg LOCK 抵触、理由は前週と同一)。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | **Tokyo** | (未分解) | (未分解) | (未分解) | BUY | 33 (+1) | 72.7% | 0.558 | +6.96 | 4.32 | 0.0090 | 0.559 | ✅ |

前週差分は **+1 trade のみ** (N 32→33、WR 71.9%→72.7%、EV +7.11→+6.96)。

昇格しない理由 (前週から不変):
1. **sub-cell 切りの明示禁止** — [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] の pre-reg は「セル = EUR_JPY × BUY。**Tokyo 条件は付けない**」と明記。本候補はその Tokyo sub-cell
2. **中間再計算の禁止 (P-10 型)** — 判定は「fresh N≥40 到達時に 1 回限り」、期限 2027-02-28。weekly deepdive が毎週再計算しており、ツール自体が LOCK と構造的に衝突
3. 多重性: `m_v3=1` ゆえ p_bonf=p_raw。探索族を v2∪v3 (**m=8**, 前週 7) で取れば p_bonf = **0.0720** → α=0.05 **FAIL**

## 🔑 今週の主要発見: pre-reg LOCK の trigger まで残り 5 本

pre-reg 本体セル (sr_anti_hunt_bounce × EUR_JPY × **BUY**、dedup=0、shadow のみ、**2026-08-05 以降の fresh OOS**) の件数のみを計上 (LOCK 準拠で outcome 統計は再計算しない):

| week (Mon) | +N | cum |
|---|---|---|
| 2026-08-03 | +1 | 1 |
| 2026-08-10 | +19 | 20 |
| 2026-08-17 | +8 | 28 |
| 2026-08-24 | +4 | 32 |
| 2026-08-31 | 0 | 32 |
| 2026-09-07 | 0 | 32 |
| 2026-09-14 | +3 | **35** |

**fresh N = 35 / 40 → trigger 未達 (残り 5)**。直近 4 週 (08-24〜09-14) の実効 accrual は 7 本 = **1.75 本/週** ⇒ ETA **約 3 週間後 (2026-10 中旬)**。08-31/09-07 の 2 週連続ゼロを含むため下振れ余地あり。

➡️ **次アクション**: 次回以降の weekly run で **fresh N のみを見る**。N≥40 に到達したその回で pre-reg 判定 (①EV>0 片側 t p<0.05 ∧ ②Wilson_lo(95%) > 38.7%) を **1 回限り**実行する。到達前に EV/WR を覗くのは P-10 違反。

## 参考: v2 eligible cells (N≥20, m=7)

| cell | N (Δ) | WR | Wilson_lo | EV_net | PF | p_bonf | wf |
|---|---|---|---|---|---|---|---|
| vsg_jpy_reversal \| EUR_JPY \| SELL | 22 (**NEW**) | 0.727 | 0.518 | +1.22 | 1.40 | 0.2310 | ❌ |
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 74 (+3) | 0.622 | 0.508 | +1.94 | 1.58 | 0.2548 | ❌ |
| sr_anti_hunt_bounce \| EUR_USD \| SELL | 27 (+0) | 0.667 | 0.478 | −4.91 | 0.31 | 0.5829 | ❌ |
| rsk_gbpjpy_reversion \| GBP_JPY \| BUY | 31 (+2) | 0.613 | 0.438 | −2.20 | 0.72 | 1.0000 | ❌ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 49 (+3) | 0.571 | 0.433 | −3.13 | 0.51 | 1.0000 | ❌ |
| vsg_jpy_reversal \| EUR_JPY \| BUY | 24 (+1) | 0.583 | 0.388 | −2.35 | 0.58 | 1.0000 | ❌ |
| sr_anti_hunt_bounce \| USD_JPY \| BUY | 28 (+2) | 0.536 | 0.358 | −1.70 | 0.50 | 1.0000 | ❌ |

`vsg_jpy_reversal | EUR_JPY | SELL` が今週 N≥20 に到達し新規 eligible 化 (m_v2 6→7)。WR 72.7% / Wilson_lo 0.518 は見栄えするが **p_bonf 0.231 で有意性 FAIL、wf_stable=False**。watch 対象止まり — 高 WR + 低 PF は [[feedback_partial_quant_trap]] の典型形。

## 戦略別サマリ (365d clean)

| strategy | raw | clean N (Δ) | WR | Wilson_lo | EV_net | PF | 前週比 |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 462 | 247 (+9) | 0.538 | 0.476 | −1.92 | 0.63 | ほぼ不変 |
| sr_liquidity_grab | 4 | 2 (+0) | 1.000 | 0.342 | +1.95 | — | 停止 |
| cpd_divergence | 0 | 0 (+0) | — | — | — | — | **発火ゼロ継続** |
| vdr_jpy | 44 | 27 (+1) | 0.630 | 0.442 | +1.64 | 1.23 | やや悪化 |
| vsg_jpy_reversal | 84 | 55 (+6) | 0.673 | 0.541 | +0.77 | 1.17 | **改善** |
| rsk_gbpjpy_reversion | 152 | 48 (+2) | 0.521 | 0.383 | −3.73 | 0.53 | **悪化** |
| mqe_gbpusd_fix | 88 | 6 (+0) | 0.667 | 0.300 | +5.85 | 2.53 | 停止 |

- **vsg_jpy_reversal** が唯一の一貫改善 (EV +0.55→+0.77、PF 1.12→1.17、Wilson_lo 0.513→0.541)。N=55 で eligible 帯に近づきつつある
- **rsk_gbpjpy_reversion** は 2 週連続悪化 (EV −2.96→−3.73、PF 0.60→0.53)。[[project_rsk_gbpjpy_bar_close_gate_pending]] の bar-close 修正後も EV 回復なし ⇒ 設計側の再監査候補

## 🔴 N 枯渇の真因は発火数でなく dedup 除外率

| strategy | raw | dedup 除外 | 除外率 | clean |
|---|---|---|---|---|
| mqe_gbpusd_fix | 88 | 82 | **93.2%** | 6 |
| rsk_gbpjpy_reversion | 152 | 104 | **68.4%** | 48 |
| sr_anti_hunt_bounce | 462 | 195 | 42.2% | 247 |
| vsg_jpy_reversal | 84 | 28 | 33.3% | 55 |
| vdr_jpy | 44 | 16 | 36.4% | 27 |

`mqe_gbpusd_fix` は raw 88 本発火していながら 93% が dedup_violation で消え clean N=6。**最終発火は 2026-08-28T15:31 で以後 3 週間ゼロ**。outcome 自体は WIN 42 / LOSS 46 と拮抗しており「発火していないから N が貯まらない」のではなく「**発火が擬似反復なので統計に使えない**」構図。`rsk_gbpjpy_reversion` も 68% 除外。

➡️ これは [[project_r2_audit_dedup_contamination_2026_06_08]] と同根。**dedup 除外率が高い 2 戦略は、shadow をいくら回しても有効 N が線形に貯まらない** — signal 生成側の重複抑制 (cooldown / bar-close gate) を見ないまま「4-6 週で N≥30」を期待するのは誤り。

## 判定

- **PAIR_PROMOTED (actionable): 0 件**。ツール出力の 1 件は pre-reg LOCK 違反 sub-cell につき不採用 (4 週連続)
- **Pre-reg LOCK trigger: fresh N 35/40、ETA 約 3 週間**
- 引き続き shadow 蓄積継続。ただし mqe / rsk は dedup 構造の是正なしに N は貯まらない

---

## 訂正 (2026-09-20、rule:R3)

詳細: [[deepdive-dedup-estimand-and-lock-redaction-2026-09-20]]

### 訂正 1 — 「N 枯渇の真因は発火数でなく dedup 除外率」は **falsified**

`dedup_violation=1` は **既に記録済みイベントの tick 単位の重複コピー**に付く
(`modules/demo_db.py` は「直前の採用行から TF 窓以内」だけを flag し、各窓の先頭は必ず残す)。
実測でも flag 行は直前の採用行から中央値 14〜25 秒 (p90 ≤ 50 秒、窓 900 秒) の位置にあり、
採用行どうしの間隔は **1 件も窓を下回らない** (過剰抑制なし)。
⇒ **dedup 除外は独立観測を 1 件も取り除かず、unique N の蓄積速度に影響しない。**
除外率を枯渇の原因に使ったのは分母 (raw) の取り違え。

`mqe_gbpusd_fix` の 93.2% は **ゲート導入 (2026-04-30T02:42Z) 以前の 86/88 行**が占める
凍結アーティファクトで、**post-fix の除外率は 0.0%** (post-fix raw = 2 行)。
真因は本レポートが否定した側、すなわち **発火の枯渇そのもの**
(unique 90d = 1 本 = 0.08 本/週、最終 unique 発火 2026-08-28T15:31)。
「outcome は WIN 42 / LOSS 46 と拮抗」も大半が 4 月バースト由来のため現状記述に使えない。

`rsk_gbpjpy_reversion` の 68.4% は post-fix でも高いが月次で 90% → 22% へ減衰済みであり、
いずれにせよ unique N には効かない。

**正しい指標 = unique 蓄積速度** (`_summary.json` の `unique_accrual`):
sr_anti_hunt 13.22 / rsk 2.57 / vsg 2.49 / vdr 1.48 / mqe **0.08** 本/週 (90d)。

### 訂正 2 — LOCK セルの outcome 統計を印刷していた (P-10 違反)

本レポートの以下 3 セルは active な pre-reg LOCK 下にあり、outcome 統計の中間再計算は禁止:

| 公表箇所 | セル | registry |
|---|---|---|
| PAIR_PROMOTED Candidates | `sr_anti_hunt_bounce × EUR_JPY × Tokyo × BUY` N=33 | `sr-anti-hunt-eurjpy-buy-forward-confirm` (sub-cell) |
| v2 eligible 表 | `sr_anti_hunt_bounce × EUR_JPY × BUY` N=74 | 同 (本体セル) |
| v2 eligible 表 | `sr_anti_hunt_bounce × USD_JPY × BUY` N=28 | `ws3-t11-anti-hunt-usdjpy-recheck` |

本レポートは衝突を散文で認識していた (「ツール自体が LOCK と構造的に衝突」) が数値は印刷された。
**露出は今週分だけではない — 08-23 / 08-30 / 09-06 / 09-13 / 09-20 の 5 週分が main にある。**
⇒ 「1 回限り判定」の前提は既に崩れており、LOCK 妥当性の disposition は user 決裁
(registry `sr-anti-hunt-eurjpy-lock-validity-disposition`、期日 2026-10-12)。

恒久修正: `tools/cell_deepdive_audit.py` が registry から LOCK セルを読み、
一致セルと **その refinement (sub-cell)** の outcome を出力から除去し **`n` のみ残す**。
同スナップショットで再実行すると **3 セルが redact され `candidates` は 1 → 0**
(⚠️ **初版では meta 計数が本レポートと完全一致したが、その後のレビュー対応で
LOCK 行を outcome 読み取り前に分岐する修正を入れたため `clean_N` は 385 → **273**
= LOCK 行 215 を routing 除外。**現在「ad-hoc 版と同一」は成立しない** — 同一なのは
非 LOCK セルの統計と `m_v2`=7 / `m_v3`=1 / `candidates`=0)。
pin: `tests/test_cell_deepdive_lock_redaction.py` (8 件、NG 入力と counter-pin を対で保持)。

### 訂正 3 — fresh N の計数基準が読み手間で不一致 (未解決)

`prereg_trigger_watch` は **36** (registry `closed_only: true` = CLOSED 全件)、
本レポートは **35** (`outcome ∈ {WIN, LOSS}`)。差 1 行は `outcome=BREAKEVEN`。
pre-reg 原文は BREAKEVEN の扱いを規定していない。判定式 ② `Wilson_lo > 38.7%` は
WIN/LOSS の二値分母を要するため、**トリガが N=40 で発火しても ② の実 N は ≤39** になる。
outcome 到達前に確定すべき問題として user 決裁へ
(registry `sr-anti-hunt-eurjpy-count-basis-declaration`、期日 2026-10-12)。

### ツール note の訂正

本レポート冒頭の「`tools/cell_deepdive_audit.py` は repo に存在しない (**10週連続**)」は
**2026-09-20 に解消**。以後は in-repo ツールを使うこと:

```bash
curl -sS "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" -o /tmp/prod_trades.json
python3 tools/cell_deepdive_audit.py /tmp/prod_trades.json --run-date $(date -u +%F)
```
