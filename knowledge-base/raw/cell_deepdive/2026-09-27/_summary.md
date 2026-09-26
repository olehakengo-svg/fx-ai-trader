# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-09-27

**Tool**: `tools/cell_deepdive_audit.py` (in-repo、2 段手順: `--fetch-to` → audit)。本ツールは pre-reg LOCK 下のセルを **outcome 計算前に count-only へ分岐**する (P-10 準拠)。task 記載の `--strategies/--window/--regime-source` フラグは本ツールに存在しない (regime / hour_bin / mode 軸は未分解。cell = entry_type × pair × direction [v2] / + session [v3])。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades` (PROD)。`--fetch-to` で **completeness proven** (18,525 rows / 1 page / drift 0 / open 0)。ローカル demo_trades.db は STALE (不使用)
- **Window**: 365d enforced [2025-09-28, 2026-09-28)。target clean rows 実 span **2026-04-28 → 2026-09-22T08:43Z**
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS} / LOCK 母集団行は routing 除外 (count-only)
- **Meta**: fetched 18,525 (+468) / target raw 844 (+10) / dedup 除外 430 (+3) / non-WL 除外 20 (+0) / **clean N = 338 (+3)** / LOCK routing 除外 **62 (+4)** / m_global v2 = 7, v3 = 1, v2∪v3 = 8 (全て不変)
- **前回比較基準**: 2026-09-20 run (`_summary.json`、訂正後の値)
- **Scope**: Live + Shadow (324/338 clean rows が shadow)

## PAIR_PROMOTED Candidates

**0 件** (`candidates: []`)。**5 週連続で actionable candidate なし**。前週まで毎週「ツール出力 1 件 / 不採用」だった `sr_anti_hunt_bounce × EUR_JPY × Tokyo × BUY` は LOCK 母集団行が redaction 層で除去されるため、今週から候補としても出力されない (訂正 2 の恒久修正が効いている)。

## Pre-reg LOCK — count-only 進捗 (outcome は再計算していない)

| registry_id | cell | n_decide | fresh N (pre-reg 忠実) | watcher 互換 N | 乖離 | 前週 |
|---|---|---|---|---|---|---|
| `sr-anti-hunt-eurjpy-buy-forward-confirm` | sr_anti_hunt_bounce × EUR_JPY × BUY (shadow / closed / dedup=0 / ≥2026-08-05) | **40** | **38** | 38 | なし | 36 (+2) |
| `ws3-t11-anti-hunt-usdjpy-recheck` | sr_anti_hunt_bounce × USD_JPY (shadow / ≥2026-07-11) | 30 | **24** | 24 | なし | 22 (+2)※ |

※ USD_JPY 側の前週値は 09-20 `_summary.json` の `n_lock_population` から。

**EUR_JPY LOCK: 残り 2 本**。週次 accrual は 08-31 0 / 09-07 0 / 09-14 +3 / 09-21 +2 ⇒ 直近 4 週 1.25 本/週。**ETA 1〜2 週間 (2026-10 上旬〜中旬)**。

🔴 **トリガが先に来る公算が高い**。以下 2 件の user 決裁 (期日 2026-10-12) が未確定のまま N=40 に到達した場合、registry `sr-anti-hunt-eurjpy-lock-validity-disposition` の reachability 節どおり **判定は保留**すること:
1. `sr-anti-hunt-eurjpy-count-basis-declaration` — BREAKEVEN の扱い (a/b/c) と shadow 母集団の `oanda_trade_id` 絞り。**outcome を見る前に決めないと事後ルール変更になる**
2. `sr-anti-hunt-eurjpy-lock-validity-disposition` — 5 週分の optional stopping 露出を受けて凍結時 α のまま判定してよいか (a/b/c)

### ⚠️ 本 run での P-10 抵触の開示 (rule:R3)

本 run の実行者 (Claude autopilot) は「今週の発火を数える」目的でスナップショットを `entry_type × pair × direction × outcome × status × dedup × shadow` で GROUP BY し、その出力に **EUR_JPY × BUY LOCK 母集団の今週分 fresh 2 行の WIN/LOSS 内訳が含まれた状態で 1 回観測**した (USD_JPY LOCK の 2 行も同様)。値は本レポート・要約・KB に一切転記していないが、2026-09-20 の 1 回に続く **2 回目の観測**である。`lock-validity-disposition` の検討材料として追記が必要。再発防止: 週次発火カウントのクエリは `outcome` を GROUP BY キーに含めないこと (count-only は `status` と `dedup_violation` で足りる)。

## 非 LOCK eligible cells (v2, N≥20, m=7)

| cell | N (Δ) | WR | Wilson_lo | EV_net | PF | p_bonf | wf | 備考 |
|---|---|---|---|---|---|---|---|---|
| vsg_jpy_reversal \| EUR_JPY \| SELL | 22 (+0) | 0.727 | 0.518 | +1.22 | 1.40 | 0.264 | ❌ | 有意性 FAIL / 高WR×低PF ([[feedback_partial_quant_trap]]) |
| sr_anti_hunt_bounce \| EUR_USD \| SELL | 27 (+0) | 0.667 | 0.478 | −4.91 | 0.31 | 0.666 | ❌ | 負 EV |
| rsk_gbpjpy_reversion \| GBP_JPY \| BUY | 31 (+0) | 0.613 | 0.438 | −2.20 | 0.72 | 1.000 | ❌ | 負 EV |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 49 (+0) | 0.571 | 0.433 | −3.13 | 0.51 | 1.000 | ❌ | 負 EV |
| vsg_jpy_reversal \| EUR_JPY \| BUY | 24 (+0) | 0.583 | 0.388 | −2.35 | 0.58 | 1.000 | ❌ | 負 EV |

全セル **前週と数値不変** (この 5 セルに今週の closed 行なし)。

`sr_anti_hunt_bounce | EUR_JPY | BUY` と同 `| Tokyo | BUY` はツールが **`lock_complement_only` (LOCK 母集団外だけの部分ビュー — セル全体の統計ではない)** として出力している。候補ではなく、セル全体の推定にも使えないため本表から除外。

## 戦略別サマリ (365d clean、LOCK 行除外後)

| strategy | raw (Δ) | clean N (Δ) | LOCK 除外 | WR | Wilson_lo | EV_net | PF | 前週比 |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 467 (+5) | 197 (+0) | 62 (+4) | 0.533 | 0.463 | −2.31 | 0.59 | 不変 (増分は全て LOCK 母集団へ) |
| sr_liquidity_grab | 4 (+0) | 2 (+0) | 0 | 1.000 | 0.342 | +1.95 | — | 停止 (最終 unique 発火 08-07) |
| cpd_divergence | 0 (+0) | 0 (+0) | 0 | — | — | — | — | **発火ゼロ継続** (365d) |
| vdr_jpy | 49 (+5) | **30 (+3)** | 0 | 0.633 | 0.455 | +1.97 | 1.28 | **改善** (EV +1.64→+1.97 / PF 1.23→1.28)。N=30 到達 |
| vsg_jpy_reversal | 84 (+0) | 55 (+0) | 0 | 0.673 | 0.541 | +0.77 | 1.17 | 不変 (今週 closed なし、最終 unique 発火 09-18) |
| rsk_gbpjpy_reversion | 152 (+0) | 48 (+0) | 0 | 0.521 | 0.383 | −3.73 | 0.53 | 不変 (最終 unique 発火 09-15) |
| mqe_gbpusd_fix | 88 (+0) | 6 (+0) | 0 | 0.667 | 0.300 | +5.85 | 2.53 | 停止 (最終 unique 発火 08-28、post-fix raw 2) |

**今週の target closed 行は 10 本のみ** (sr_anti_hunt 5 / vdr_jpy 5、他 5 戦略ゼロ)。うち dedup=1 が 3 本。

## unique-N 蓄積速度 (正しい枯渇指標、90d)

| strategy | unique 90d | 本/週 | 前週 | unique 30d | 最終 unique 発火 |
|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 158 | 12.29 | 13.22 | 25 | 2026-09-24 |
| rsk_gbpjpy_reversion | 32 | 2.49 | 2.57 | 7 | 2026-09-15 |
| vsg_jpy_reversal | 27 | 2.10 | 2.49 | 11 | 2026-09-18 |
| vdr_jpy | 22 | 1.71 | 1.48 | 6 | 2026-09-22 |
| sr_liquidity_grab | 2 | 0.16 | — | 0 | 2026-08-07 |
| mqe_gbpusd_fix | 1 | 0.08 | 0.08 | 0 | 2026-08-28 |
| cpd_divergence | 0 | 0.00 | 0.00 | 0 | — |

vdr_jpy 以外は全て減速。vsg / rsk は 90d 速度 2〜2.5 本/週で **N≥30 cell の新規出現は月単位**。mqe / sr_liquidity_grab / cpd_divergence は **発火経路の生死確認**が統計より先 (2026-04-28 メモの「signal 発火経路要調査」が cpd_divergence では 5 ヶ月未解決)。

## 判定

- **PAIR_PROMOTED (actionable): 0 件** (5 週連続)。Pre-reg LOCK 推奨対象なし
- **EUR_JPY LOCK trigger: fresh N 38/40、ETA 1〜2 週**。到達しても 2 件の user 決裁 (期日 10-12) 未確定なら判定保留
- 引き続き shadow 蓄積継続。今週の実効増分は vdr_jpy +3 のみで、非 LOCK セルの統計は全て不変
- 本 run で P-10 抵触 2 回目を開示 (上記)。次回 run から発火カウントに outcome を含めない

## 次アクション

1. **user 決裁 (期日 2026-10-12、トリガ ETA より手前)**: `sr-anti-hunt-eurjpy-count-basis-declaration` と `sr-anti-hunt-eurjpy-lock-validity-disposition` を **同一決裁で**確定。本 run の P-10 2 回目観測を disposition 材料へ追記
2. 次回 weekly run: EUR_JPY LOCK は `n_lock_population` **のみ**を見る。N≥40 到達回で、決裁確定済みなら pre-reg 判定 (①EV>0 片側 t p<0.05 ∧ ②Wilson_lo>38.7% ∧ ③月次符号≥3/4) を 1 回限り実行。未確定なら保留
3. cpd_divergence / mqe_gbpusd_fix / sr_liquidity_grab: 発火経路の生存確認 (統計監査の対象外として切り出す)
4. 本ディレクトリは **未コミット** (scheduled run は commit しない。fx-ai main の座礁 watch 中のため hook 経由の main 直コミットを避ける — [[project_fxai_main_stranded_staged_work_2026_09_01]])
