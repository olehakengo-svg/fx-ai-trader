---
id: 20260518-1620-prime-reeval-and-candidates-retry
title: "[PRIME v2 re-evaluation RETRY] 6 PRIME 再評価 + 新候補抽出 (post-2026-05-15 freeze release)"
owner: codex
status: queued
priority: P1
depends_on: 20260518-1500-prime-gate-order-hotfix
created_at: 2026-05-18T15:30:00+0900
roadmap_gate: "`modules/prime_gate.py:11-13` の pre-reg freeze (2026-05-15) が 3 日 over。EDGES は 2026-04-16 cutoff の shadow N=1711 で固定されており、新 30 日分 (N≈1800 shadow + 40 LIVE) を反映していない。同期間で **PRIME base 外** に EV+ 6 戦略 (gbp_deep_pullback +7.75p, orb_trap +5.83p, ob_retest +2.68p, trend_rebound +2.28p, dt_sr_channel_reversal +1.13p, wick_imbalance_reversion +0.23p — 全て Wilson_lo≥10%) が観測され、永久 shadow ロック状態。本 task は (a) 既存 6 PRIME の再評価、(b) 新候補 6 戦略の cell 探索、(c) `prime_gate_v2.py` 案作成。実装ではなく **spec 提案** まで (LIVE 反映は別 task, pre-reg LOCK 必要)。"
rule: R1
related:
  - modules/prime_gate.py
  - modules/confidence_q4_gate.py
  - knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md
  - knowledge-base/wiki/sessions/prereg-6-prime-strategies-2026-04-21.md
  - knowledge-base/wiki/sessions/shadow-deep-analysis-prereg-2026-04-21.md
  - data/cache/massive/USD_JPY_M15.parquet
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_spread_basis_for_mafe
  - feedback_exclude_xau
  - feedback_codex_schema_hallucination
  - feedback_bt_must_use_massive
  - feedback_live_shadow_separation
  - feedback_shadow_first_quant_architecture
---

# 0. 背景

詳細: `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md`

## 0.1 入力データ

- **Shadow (Render demo_trader API)**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000` で `is_shadow=1` を抽出
  - 期待: 2026-03-01 → 2026-05-18 の shadow N≈4000+
  - [feedback_live_shadow_separation](memory/feedback_live_shadow_separation.md): `is_shadow=0` (LIVE) と必ず分離
  - [feedback_exclude_xau](memory/feedback_exclude_xau.md): `instrument != XAU_USD` フィルタ
- **MASSIVE parquet** ([feedback_bt_must_use_massive](memory/feedback_bt_must_use_massive.md)): regime/quartile 再計算用に `data/cache/massive/*.parquet` を参照

# 1. Pre-registered scope (LOCKED)

## 1.1 Task A: 既存 6 PRIME 再評価

`modules/prime_gate.py:_PRIMES` の 6 entries について shadow 全期間 (2026-03-01〜2026-05-18) を以下で評価:

| 評価軸 | 閾値 |
|---|---|
| N | ≥ 20 (現状 freeze 時 9-24) |
| Wilson_lo (95% CI) | ≥ 0.40 |
| Fisher exact p (vs baseline) | < 0.05 (Tier B 維持), < 0.0083 (Tier A 維持) |
| Bonferroni m=6 | A 維持なら p×6 < 0.05 必須 |
| Walk-Forward (3 fold) | EV+ 維持 ≥ 2/3 |
| Kelly half | ≥ 0.05 (lot_mult=0.1 normalize 後) |
| spread/slippage-adjusted EV | entry_price 基準 ([feedback_spread_basis_for_mafe](memory/feedback_spread_basis_for_mafe.md)) |

### 1.1 出力フォーマット (Codex 報告書)

各 PRIME について `KEEP / DEMOTE / PROMOTE / TIER_CHANGE` を判定:

| name | tier (current) | N | WR | Wlo | Fisher p | Bonf p×6 | WF (3-fold) | Kelly | spread-adj EV | verdict |
|---|:---:|---:|---:|---:|---:|---:|---|---:|---:|:---:|
| stoch_trend_pullback_PRIME | A | … | … | … | … | … | … | … | … | KEEP / B / DEMOTE |
| stoch_trend_pullback_LONDON_LOWVOL | B | … | … | … | … | n/a | … | … | … | KEEP / A / DEMOTE |
| fib_reversal_PRIME | A | … | … | … | … | … | … | … | … | KEEP / B / DEMOTE |
| bb_rsi_reversion_NY_ATRQ2 | B | … | … | … | … | n/a | … | … | … | KEEP / A / DEMOTE |
| engulfing_bb_TOKYO_EARLY | C | … | … | … | … | n/a | … | … | … | KEEP / B / DEMOTE |
| sr_fib_confluence_GBP_ADXQ2 | B | … | … | … | … | n/a | … | … | … | KEEP / A / DEMOTE |

## 1.2 Task B: 新候補 6 戦略の cell 探索

下記 6 戦略について shadow 全期間で **best cell** を grid 探索 (post-hoc bias 警戒: [project_w3_3_s4_connors_raschke_queued](memory/project_w3_3_s4_connors_raschke_queued.md)):

| 戦略 | 30d aggregate (確認済み, 参考値) |
|---|---|
| gbp_deep_pullback | N=11 WR=27.3% Wlo=9.7% EV=+7.75p PF=1.93 |
| orb_trap | N=14 WR=50.0% Wlo=26.8% EV=+5.83p PF=3.59 |
| ob_retest | N=40 WR=42.5% Wlo=28.5% EV=+2.68p PF=1.40 |
| trend_rebound | N=13 WR=46.2% Wlo=23.2% EV=+2.28p PF=2.10 |
| dt_sr_channel_reversal | N=38 WR=34.2% Wlo=21.2% EV=+1.13p PF=1.18 |
| wick_imbalance_reversion | N=32 WR=37.5% Wlo=22.9% EV=+0.23p PF=1.04 |

### 1.2.1 Grid axes (固定 — post-hoc 探索数を制御)

```
axis 1: instrument          ∈ {USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, AUD_USD}
axis 2: session             ∈ {tokyo, london, ny, overlap}
axis 3: ATR quartile        ∈ {Q1, Q2, Q3, Q4}     (`modules/prime_gate.py:EDGES` 同一 binning)
axis 4: ADX quartile        ∈ {Q1, Q2, Q3, Q4}
axis 5: direction           ∈ {BUY, SELL}
```

= 6 × 4 × 4 × 4 × 2 = 768 cell × 6 戦略 = **4608 hypotheses**。
**Bonferroni α** = 0.05 / 4608 = **1.085e-5**。
**FDR (BH q=0.10)** も併記 (より緩い、補助指標)。

### 1.2.2 Cell 採用閾値 (LOCKED, 全 AND)

| 閾値 | 値 |
|---|---|
| N | ≥ 20 |
| WR | ≥ 50% |
| Wilson_lo (95%) | ≥ 0.40 |
| spread-adj EV | ≥ +1.0 pip/trade |
| PF | ≥ 1.20 |
| Bonferroni-corrected p | < 1.09e-5 |
| WF (3-fold) | EV+ ≥ 2/3 |
| Kelly half | ≥ 0.05 |

複数 cell が pass した戦略は **最も Bonferroni p が小さい 1 cell のみ** 採用 (post-hoc selection の最小化)。

### 1.2.3 出力 (新 PRIME 候補)

```python
# Tier 判定:
# Bonferroni p < 1.09e-5 (4608 補正) AND WF 3/3 → Tier A (lot 0.3x)
# Bonferroni p < 1.09e-5 AND WF 2/3 → Tier B (lot 0.1x)
# それ以外 → 不採用 (引き続き shadow)

# 出力例:
("orb_trap_NY_ATRQ2",
 "orb_trap",
 "B", 0.1,
 lambda f: (f["session"]=="ny" and f["_atr_q"]=="Q2")),
```

## 1.3 Task C: `prime_gate_v2.py` 案

`modules/prime_gate.py` のドラフト v2 を `research/prime_gate_v2_proposal.py` に出力。

### 1.3.1 必須事項

- `EDGES` を **新 90d shadow** で再計算 (current freeze: 2026-04-16 cutoff N=1711 → new: 2026-05-18 cutoff N≈4000)
- `_PRIMES` リストは Task A verdict + Task B 採用 cell をマージ
- 各 entry に `# Pre-reg LOCK 2026-05-18: N=X WR=X.X% Wlo=X.X% Bonf_p=X.XXe-X` コメント
- Tier C entries (never promote) も維持 (shadow data 記録用)

### 1.3.2 LIVE 反映条件

本 task では `prime_gate.py` を**書き換えない**。
- 出力は `research/prime_gate_v2_proposal.py` + Codex 報告書のみ
- LIVE 反映は別 task で pre-reg LOCK 文書 (`prereg-prime-v2-2026-05-XX.md`) を起こした後

# 2. テスト要件

[feedback_codex_mock_test_trap](memory/feedback_codex_mock_test_trap.md): mock-only test は禁止。

## 2.1 Sanity (REAL data)

`tools/prime_reeval_sanity.py`:
- 現行 6 PRIME を新データで再計算した結果が **freeze 時の値と乖離していないか** を 1 件以上抽出
  - 例: `fib_reversal_PRIME` (freeze: N=12 WR=75.0% EV=+2.96p, Fisher p=0.0046)
  - 新データで N≥12 WR±10pp EV±2p 以内に収まること (Hong & Klabjan 風 rolling stability check)
- 乖離 ≥ 1 戦略あれば「PRIME drift detected」を verdict に記載

## 2.2 Replay

Task A の verdict を新 gate (hot-fix 後) で適用した場合の **想定 30d LIVE fire 数** を出力。
hot-fix task (`20260518-1500-prime-gate-order-hotfix`) の dry-run 結果と integer 一致確認。

# 3. KB 更新 (同一 PR)

- `knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md` (新規) — Task A/B/C 全結果 + verdict
- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md` に「Codex re-eval 完了」セクション追記
- 新候補が 1 件以上採用された場合は `knowledge-base/wiki/decisions/prereg-prime-v2-{date}.md` を**ドラフトのみ**作成 (LOCK は user 承認後)

# 4. 完了条件 (DoD)

- [ ] Task A 6 PRIME 全件 verdict 出力
- [ ] Task B 6 戦略 × 768 cell 全探索完了、Bonferroni 補正後採用 cell 数を明示
- [ ] Task C `research/prime_gate_v2_proposal.py` 作成
- [ ] `tools/prime_reeval_sanity.py` 出力で freeze drift ≤ 10pp/2p
- [ ] `knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md` 作成
- [ ] verdict が「current 6 PRIME 維持 / 新候補なし」の場合も Bonferroni p 全件表で完了報告 (NULL も成果)
- [ ] git commit & push (origin/main) — final.md ではなく `git diff origin/main..HEAD` で実 verify

# 5. Out of scope

- `prime_gate.py` 本体の書き換え (本 task は提案のみ)
- demo_trader.py の gate 順序変更 ([20260518-1500-prime-gate-order-hotfix](20260518-1500-prime-gate-order-hotfix.md) で別 task)
- 5 経路統合 (PAIR_PROMOTED / ELITE_LIVE / GRAIL / C1 / PRIME)
- emergency_trip の解除 (binding 解除条件未達)
- 新規 EDGES 列の追加 (RSI / volume / MACD 等 — 現行 4 列を維持)

# 6. 注意 (Codex)

- [feedback_partial_quant_trap](memory/feedback_partial_quant_trap.md): N/WR/EV だけで結論禁止。PF/Wilson_lo/Bonferroni/WF/Kelly 全列必須
- [feedback_label_empirical_audit](memory/feedback_label_empirical_audit.md): 「ロジック問題ない?」演繹禁止、shadow data × cell 実測クエリで答える
- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): `prime_gate.py` の EDGES 構造を必ず実ファイル参照
- [feedback_success_until_achieved](memory/feedback_success_until_achieved.md): NULL 結果 (新候補 0 件) でも別 angle で深掘りを試みること (Wave 6 風 pivot)


