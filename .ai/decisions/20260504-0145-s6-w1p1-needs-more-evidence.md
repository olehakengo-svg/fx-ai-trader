# S6 W1P1 Signal Validity Audit — NEEDS_MORE_EVIDENCE (constructive)

- Date: 2026-05-04 01:45 JST
- Rule: R1 (Wave 1 Phase 1 — chart pattern signal predictive power 計測)
- Source: `.ai/tasks/done/20260504-0125-s6-w1p1-signal-validity-audit.md` (Result section, 2026-05-03T16:49:38Z, 336s, exit 0)
- Worker commit: `67ddc5c feat(codex): complete 20260504-0125-s6-w1p1-signal-validity-audit` on origin/main
- Verdict (Claude review): **NEEDS_MORE_EVIDENCE** — Codex 自己判定一致
- Path forward: 構成的 (= 修正後すぐ W1P2 へ進める)

## Pre-registered verdict matrix vs 実測

| 条件 | ACCEPT 閾値 | 実測 | 判定 |
|---|---|---|---|
| Labeled (DM ≤ 1%) | ≥ 99% | 22094/22094 = 100% (DM=1, 0.0045%) | ACCEPT |
| TP+SL+TO | ≥ 21,800 | 22,093 | ACCEPT |
| hit_rate > 50% pattern count | ≥ 6 / 12 | **10 / 12** | ACCEPT |
| bull/bear pair symmetry (diff ≤ 10pp) | 全 6 pair | **5 / 6 pair** (NEEDS band 4-5) | **NEEDS_MORE_EVIDENCE** |
| pnl_pips median 正 | > 0 | +6.30 pips | ACCEPT |

5 条件中 4 ACCEPT、1 NEEDS。pre-reg rule "ACCEPT = 全条件クリア" のため overall = **NEEDS_MORE_EVIDENCE**。

## 失敗 driver の同定

bull/bear symmetry の失敗ペアは **triple_top SELL (~53.5%) vs triple_bottom BUY (63.9%) = diff 10.4pp** が最有力 (低 N なので診断ノイズが大きい):

| pair | BUY hit | SELL hit | diff | 内訳 |
|---|---|---|---|---|
| triple_top/triple_bottom | 63.9% (155) | 53.5% (142) | **10.4pp** | small N, 失敗候補 |
| double_top/double_bottom | 59.5% (4666) | 57.4% (4869) | 2.1pp | OK |
| inv_HS / HS | 58.1% (999) | 58.0% (1017) | 0.1pp | OK |
| asc_tri / desc_tri | 53.9% (3772) | 55.2% (2839) | 1.3pp | OK |
| rising_w / falling_w | 54.0% (1747) | 55.9% (1251) | 1.9pp | OK |
| bull_flag / bear_flag | 44.9% (376) | 42.1% (261) | 2.8pp | OK (両者 <50%) |

triple_top/triple_bottom は **N=142/155 と最小**で W1P0 時点から W1P2 除外候補と認識済み (task spec L207-208 にも記載)。10.4pp は小 N 由来のノイズで構造的非対称性を示唆しない (95% Wilson CI が広い)。

## hit_rate < 50% 帯

- **bull_flag BUY 44.9% (N=376)**, **bear_flag SELL 42.1% (N=261)** — 両者 50% 未達。flag pattern family は **TP/SL 比率 (1pip:1.4pip) で raw hit が 50% 未達でも EV 正となる可能性**があるため W1P2 BT で確認余地あり
- それ以外の 10 patterns はすべて hit_rate > 50%

## データ分離・操作安全性

- 出力先: `chart_pattern_outcomes` 新テーブル追加のみ。`chart_pattern_signals` は read-only 維持
- 本番 DB / `.env` / OANDA 無接触 (Codex 実装は `tools/s6_w1p1_outcome_audit.py` の新規追加のみ)
- 新規ファイル 3 件: tool / SQLite (20.8MB) / task done。`modules/` `app.py` `strategies/` 無編集
- Codex 自己申告: target SQLite が checkout 不在 → W1P0 を再生成 (signals N=22094 で pre-reg 一致確認済)、その後 chart_pattern_outcomes のみ追加。再現性 OK

## ロードマップ寄与

- **W1P2 への引き継ぎは可能**。NEEDS_MORE_EVIDENCE は構成的で、triple_top/triple_bottom を W1P2 grid から除外することで 4 / 5 → 5 / 5 pair symmetry を回復
- Bonferroni m: 12 patterns × 2 directions = 24 → triple_top/triple_bottom 除外後 = **20** (検出力 up)
- bull_flag / bear_flag は EV 評価次第で残す (raw hit < 50% でも TP/SL 比次第)
- chart pattern family の Wave 4 promotion path (Gate 1 Kelly Half 寄与候補) は **継続**

## Validity-of-evidence

- Pre-reg LOCK 遵守: MAX_HORIZON_BARS=288, outcome 定義変更なし、DM threshold 変更なし → verdict valid
- post-hoc cherry-pick の兆候なし (matrix の全 5 条件を pre-reg 通り評価)
- N=22,093 の labelled dataset は W1P2 BT に直接利用可能

## Next

- 次タスクキュー: **W1P2 — Chart Pattern Full BT** (USDJPY M5 12.3y)
  - Grid: 10 patterns × 2 directions (triple_top/triple_bottom 除外) = 20 cells
  - Bonferroni m = 20 (LOCK)
  - Pre-reg primary: 各 pattern の "default entry/SL/TP at signal" cell — chart_pattern_signals 行内 entry/sl/tp を流用
  - 統計指標: PF / Wilson_lo / Bonferroni p / Sharpe / Kelly / OOS-WF (50/50 pre-reg) / Null bootstrap 1000 / max_year_share
  - 本決定ドキュメントを `related:` に含める
