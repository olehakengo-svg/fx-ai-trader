---
id: 20260518-1950-design-broken-redesign-diagnose
title: "[DESIGN_BROKEN diagnose] dt_sr_channel_reversal + wick_imbalance_reversion: 設計欠陥特定 + 再設計案 (実装は別 task)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T19:50:00+0900
roadmap_gate: "C audit で 2 戦略を **THESIS_VALID + DESIGN_BROKEN** 判定: (1) dt_sr_channel_reversal (N=106 WR=33% PF=0.44 WF=0/3 EV=-4.28p), (2) wick_imbalance_reversion (N=70 WR=38.6% PF=0.66 WF=1/3 EV=-2.88p)。両戦略とも spread-adj EV<0 で raw WR が friction を支払えていない → TP/SL geometry または direction filter の修正で edge 復活の可能性あり (THESIS_INVALID とは異なり、思想自体は valid)。両戦略は emit 継続中 (wick: 2026-05-18 07:06 active, dt_sr: 2026-05-15 16:56 → 直近 3 日小休止だが再開予測) で実弾 data flow は生きている。**本 task は diagnose のみ (実装ではない)**: 8 軸結果 + code path 検査で具体的欠陥を特定し、redesign 案を spec として出力。Codex は実装せず、`research/design_broken_redesign_proposal.md` を生成して終了。"
rule: R1
related:
  - strategies/daytrade/dt_sr_channel_reversal.py
  - strategies/scalp/wick_imbalance_reversion.py
  - research/prime_v2_audit_2026_05_18.md
  - knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md
  - feedback_w4_eda_audit_report_format
  - feedback_label_empirical_audit
  - feedback_audit_purpose_design_not_n
  - feedback_partial_quant_trap
  - feedback_spread_basis_for_mafe
  - feedback_codex_schema_hallucination
  - project_w4_eda_complete_2026_05_05
---

# 0. 背景

## 0.1 C audit 結果 (8 軸)

### dt_sr_channel_reversal

| 軸 | 値 | 評価 |
|---|---|---|
| Shadow N (21d) | 106 | 🟢 |
| WR | 33.0% | 🟠 |
| Wilson_lo | 0.248 | 🟠 |
| spread-adj EV | **-4.28p** | 🔴 |
| **PF** | **0.44** | 🔴 |
| Kelly | 0.000 | 🔴 |
| WF (3-fold) | 0/3 | 🔴 |
| best cell (ADXQ2) | N=10 WR=60% EV=+2.32p | 🟢 (small N) |
| 直近 emit | 2026-05-15 16:56 | 🟠 |

**思想 (Thesis)**: 15m 足の SR/parallel channel 境界で RSI/MACD-H 反転を伴うバウンスを狙う。

### wick_imbalance_reversion

| 軸 | 値 | 評価 |
|---|---|---|
| Shadow N (21d) | 70 | 🟢 |
| WR | 38.6% | 🟢 |
| Wilson_lo | 0.280 | 🟢 |
| spread-adj EV | **-2.88p** | 🔴 |
| **PF** | **0.66** | 🔴 |
| Kelly | 0.000 | 🔴 |
| WF (3-fold) | 1/3 | 🔴 |
| best cell | best _ALL N=70 WR=38.6% | 🔴 (no edge) |
| 直近 emit | **2026-05-18 07:06** | 🟢 (active) |

**思想 (Thesis)**: 上ヒゲ/下ヒゲ偏りが極端な場合、流動性消費後の反対方向への平均回帰を狙う。

## 0.2 司令塔仮説 (Codex はこれを検証)

両戦略の共通 failure mode:
- **PF<1 = TP より SL を頻繁に hit** → TP/SL ratio が不適切 (例: TP=1.0 ATR, SL=1.0 ATR で WR<50% → 必然的に PF<1)
- **spread-adj EV << raw EV** → spread 占有率が高い (M5/15m scalp で spread 1.0p が EV を支配)
- **direction filter 不在** → BUY/SELL 両方向で同じロジック → WR が 50% に retreat

## 0.3 Out-of-scope (本 task では行わない)

- 実装 (modules/demo_trader.py / strategies/ の書き換え)
- BT による検証 (新仕様の MASSIVE BT は別 task で起票)
- redesign 案の pre-reg LOCK (本 task は draft のみ)
- 他の DESIGN_BROKEN 戦略への波及

# 1. Pre-registered scope (LOCKED)

## 1.1 Task structure (各戦略について同じ手順)

### Phase 1: Code reading

両戦略の signal function + execution path を読み、以下を抽出:

1. **TP/SL geometry**:
   - TP は何 ATR か / 何 pips 固定か
   - SL は何 ATR か / 何 pips 固定か
   - TP:SL ratio (Risk-Reward)
2. **Direction filter**:
   - BUY/SELL 両方向か single direction か
   - 何で direction を決めるか (例: 直近 close < SMA? RSI<30?)
3. **Session filter**:
   - 24h ON か session 制限ありか
4. **Entry trigger 詳細**:
   - 何 bar 確定で発火か
   - bar 内 intrabar 発火か
5. **Exit logic**:
   - SL hit / TP hit 以外の exit (time stop / reverse signal / 等)

### Phase 2: Shadow data dissection

Render API から該当戦略の shadow trade を抽出し:

1. **TP hit rate vs SL hit rate**:
   - close_reason 別 N + 平均 P/L
   - 期待 hit rate (BE_WR = SL/(SL+TP)) vs 実測 WR
2. **Wing analysis (asymmetry)**:
   - BUY trades の WR/EV vs SELL trades の WR/EV
   - 大きく非対称なら direction filter で片側 only 採用
3. **MAFE / MFE 分析**:
   - 平均 MAFE (Maximum Adverse Excursion) vs SL 距離
   - 平均 MFE (Maximum Favorable Excursion) vs TP 距離
   - **[feedback_spread_basis_for_mafe](memory/feedback_spread_basis_for_mafe.md)**: entry_price 基準で計算 (signal_price ではない)
4. **Spread-adj contribution**:
   - raw EV vs spread-adj EV の差分
   - spread 占有率 (差分 / N / spread_avg)

### Phase 3: Redesign hypothesis (各戦略 ≤ 3 案)

各戦略について **最大 3 redesign 案** を提案。各案は:

1. **修正点の specificity** (例: "TP を 1.0 ATR → 1.5 ATR に拡張")
2. **修正理由** (Phase 2 の data 根拠)
3. **expected impact** (raw EV / spread-adj EV / PF / WR 予測)
4. **MASSIVE BT で検証可能な仕様** (cell grid 設計、Bonferroni m)

### Phase 4: 出力

`research/design_broken_redesign_proposal.md` を作成:

```markdown
# DESIGN_BROKEN Redesign Proposal (2026-05-18)

## Strategy 1: dt_sr_channel_reversal

### Code path summary
- TP/SL: <extracted>
- Direction filter: <extracted>
- Session: <extracted>
- Entry: <extracted>
- Exit: <extracted>

### Shadow dissection (N=106)
- TP hit: N=X (WR=X%, avg P/L=X.Xp)
- SL hit: N=X (avg P/L=X.Xp)
- BUY: N=X WR=X% EV=X.Xp
- SELL: N=X WR=X% EV=X.Xp
- avg MAFE: X.Xp / avg MFE: X.Xp
- Spread-adj contribution: -X.Xp/trade

### Redesign hypotheses
1. **<title>**: <修正点> | <理由> | <expected impact> | <BT spec>
2. **<title>**: ...
3. **<title>**: ...

## Strategy 2: wick_imbalance_reversion
(同じ構造)

## Recommended next steps
- 採用候補 N: <数>
- 推奨実行順: ...
- BT 起票 task 候補: ...
```

# 2. テスト要件

実装変更が無いので回帰 test は無し。ただし:

```bash
python3 -m pytest tests/ -x -q   # 既存 PASS 確認 (regression なし)
```

新規 test 不要 (research/ output のみ、testable code ではない)。

# 3. KB 更新 (同一 commit)

- `knowledge-base/wiki/sessions/design-broken-diagnose-2026-05-18.md` (新規) — Phase 1-4 全結果サマリ
- `research/design_broken_redesign_proposal.md` (新規) — formal proposal
- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md` に "DESIGN_BROKEN diagnose 完了 ✓" 追記

# 4. 完了条件 (DoD)

- [ ] dt_sr_channel_reversal の Phase 1-4 完了
- [ ] wick_imbalance_reversion の Phase 1-4 完了
- [ ] `research/design_broken_redesign_proposal.md` 生成 (2 戦略各 ≤ 3 案)
- [ ] `knowledge-base/wiki/sessions/design-broken-diagnose-2026-05-18.md` 生成
- [ ] decision doc 追記
- [ ] `python3 -m pytest tests/ -x -q` regression なし
- [ ] git commit + push

# 5. Out of scope

- `modules/demo_trader.py` / `strategies/` の実装変更 (別 task: `20260518-XXXX-design-broken-implement-<n>` を redesign 案承認後に起票)
- MASSIVE BT (別 task; spec のみ生成)
- 他 4 戦略 (gbp_deep_pullback / orb_trap / ob_retest / trend_rebound) への波及
- PRIME v2 への組込み (採用候補が出た場合は別 add-PRIME task)

# 6. 注意 (Codex)

- [feedback_w4_eda_audit_report_format](memory/feedback_w4_eda_audit_report_format.md): 🔴🟠🟢 emoji + 太字 evidence + Gate 状態テーブル
- [feedback_label_empirical_audit](memory/feedback_label_empirical_audit.md): code 演繹禁止、shadow data 実測クエリで evidence 提示
- [feedback_partial_quant_trap](memory/feedback_partial_quant_trap.md): N/WR/EV だけで結論禁止
- [feedback_spread_basis_for_mafe](memory/feedback_spread_basis_for_mafe.md): MAFE 計算は **entry_price 基準** (signal_price でない、spread 1.0p 分の擬陰性回避)
- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): 戦略 code は実ファイル参照、推測禁止
- redesign 案は **最大 3 / 戦略** (多重検定 inflation 回避)
