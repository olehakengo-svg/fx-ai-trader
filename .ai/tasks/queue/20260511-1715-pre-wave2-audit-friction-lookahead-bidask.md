---
id: 20260511-1715-pre-wave2-audit-friction-lookahead-bidask
title: "[Pre-Wave2 Audit] session-mr-cross Wave 1 の TOO_GOOD verdict を 3 監査 (friction/look-ahead/bid-ask) で再検証"
owner: codex
status: queued
priority: P0
created_at: 2026-05-11T17:15:00+0900
roadmap_gate: "Gate 1 (Aggregate Kelly > 0) — Wave 2 shadow 投入の可否確定。Curve-fit promotion を 76 戦略中で 91% 発生させた失敗を Live overall edge NEGATIVE の根因とする shadow-first 規律の徹底"
rule: R3
related:
  - .ai/runs/20260511-165153-20260511-1330-session-mr-cross-wave1/final.md
  - knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.{md,json}
  - modules/strategies/session_mr_cross.py
  - scripts/run_session_mr_cross_wave1_bt.py
  - tools/lib/trade_sim.py
  - modules/friction_model_v2.py
  - knowledge-base/.claude/memory/feedback_partial_quant_trap.md (司令塔規律)
---

# 0. 背景

## 0.1 Wave 1 verdict の異常
session-mr-cross Wave 1 BT (`task-mp0wldwd-p08k7h`, 完了 2026-05-11 17:00) は 10 cell 中 9 を ACCEPT、verdict=Wave 2 GO を返した。しかし結果が **TOO GOOD TO BE TRUE**:

| 指標 | 観測値 | 業界 baseline | 異常度 |
|---|---|---|---|
| WR (平均) | 86.3% | 60-75% (winning EA) | 🔴 異常高 |
| PF (平均) | 2.04 | 1.2-1.6 | 🔴 異常高 |
| TP/SL = 0.33 (R:R) | WR 期待値 75% | 実測 90% | 🔴 overshoot |
| WF 4-fold 全勝率 | 8/10 cell | 通常 1-2 cell | 🔴 同質性過剰 |

これは feedback memory `feedback_partial_quant_trap.md` (N/WR/EV/PF だけでは不十分) の典型パターン。Codex の verdict は構造バイアスを反映している可能性が**極めて高い**。Live overall edge NEGATIVE (76 戦略 91% が「思想正・設計誤」) の根因は同種の curve-fit promotion だった可能性があり、ここで規律を守る判断が司令塔の責務。

## 0.2 3 つの疑念

| 疑念 | 説明 | 検証手段 |
|---|---|---|
| **D1: Friction 過小評価** | `entry_cost_pips=0.6` 固定。AUD_NZD/NZD_CAD/EUR_NZD の実 OANDA spread は 2.5-5.0 pip。**5-8倍の過小評価** → EV 全 cell 負転換の可能性 | 実 spread で再 BT |
| **D2: Look-ahead bias** | 同 bar 内で TP/SL 両方 hit した場合の解決順序。OHLC bar データでは "先に touch" は判定不能。Codex は SL-first conservative と報告したが、WR 90% と矛盾 → 楽観的実装の可能性 | `tools/lib/trade_sim.py` の TP/SL ordering ロジックを独立 audit |
| **D3: bid/ask spread 非控除** | BT runner が close price で entry/exit してる。実取引では entry=ask, exit=bid (BUY 時) で half-spread を双方控除する必要 | entry/exit に half-spread 控除して再評価 |

---

# 1. 仮説 (Hypothesis)

**H1 (Primary)**: 3 audit (D1+D2+D3) を反映すると、Wave 1 で ACCEPT した 9 cell のうち **>=70% は EV/PF 基準を満たさなくなる**。残るのは多くて 2-3 cell。

**H2 (Stronger)**: D1 (friction) のみで 6 cell 以上が REJECT になる。D2/D3 は更に絞る。

**Null**: 3 audit 全反映後も 5 cell 以上が ACCEPT を維持。これは Wave 1 verdict が真のエッジを捕捉していたことを示し、Wave 2 GO 妥当。

何が正しければロードマップが前進するか:
- H1 立てば: Wave 2 投入は厳格に絞った cell のみ → safer shadow 投入
- H2 立てば: 本族の thesis は正しいが parameter tuning が要 (Wave 1 重新) → 数週 delay だが構造的に正しい
- Null 立てば: 真のエッジ → 即 Wave 2 GO

---

# 2. 対象データ・分離

| 種別 | 用途 |
|---|---|
| **BT (既存 MASSIVE 365d M5 parquet)** | data/cache/massive/*.parquet を再利用、追加 fetch 不要 |
| **既存 BT runner** | `scripts/run_session_mr_cross_wave1_bt.py` をベースに、3 audit 変種を実装 |
| BT のみ。**Live / Shadow / OANDA は触らない** | |

---

# 3. 仕様

## 3.1 Audit-A: Realistic friction

`tools/lib/trade_sim.py` または `scripts/run_session_mr_cross_wave1_bt.py` で friction を **pair-aware** に拡張。

実 OANDA spread (Asian session, Sept-May average を保守的に):

| Pair | Asian session avg spread (pip) | BT 控除値 |
|---|---|---|
| EUR_NZD | 2.5-4.0 | **3.0** |
| AUD_NZD | 2.0-3.0 | **2.5** |
| AUD_CAD | 2.0-3.0 | **2.5** |
| NZD_CAD | 4.0-6.0 | **5.0** |
| EUR_GBP | 0.8-1.5 | **1.2** |

実装:
- `PAIR_SPREAD_PIPS = {"EUR_NZD": 3.0, "AUD_NZD": 2.5, ...}` を BT runner に追加
- 既存の `entry_cost_pips=0.6` を `PAIR_SPREAD_PIPS[pair]` で上書き
- friction model v2 (`modules/friction_model_v2.py`) に当該ペアがあるなら、そちらを優先採用 (`pair_spread_lookup()` 等の API がある場合)

## 3.2 Audit-B: Look-ahead bias audit

`tools/lib/trade_sim.py` の同 bar TP/SL 判定ロジックを Codex に **独立 audit** させる。

監査の質問:
1. 5m bar で entry した直後、その bar の low が SL に touch して、high が TP に touch したケースで、現実装はどちらを採用しているか?
2. 採用が close price ベースなら、これは **look-ahead** (close 時点で判定するが、close 前に SL hit していたかは不明)
3. 採用が SL-first conservative なら、WR 90% は **どこから来ているか**

audit deliverable: `knowledge-base/raw/audits/session-mr-cross-wave1-lookahead-audit.md`
- 現実装の TP/SL ordering ロジックの抜粋 (line 番号付き)
- 同 bar 両 hit ケースの割合 (full BT で何 % あったか)
- 楽観的解決 (TP-first) と保守的解決 (SL-first) の verdict 差分

## 3.3 Audit-C: bid/ask spread 控除

BUY signal:
- Entry: 現 close + half_spread_pips
- Exit (TP/SL): TP target - half_spread_pips, SL trigger は変えない (broker hits SL 後に bid で約定)

SELL signal:
- Entry: 現 close - half_spread_pips
- Exit (TP/SL): TP target + half_spread_pips

half_spread = `PAIR_SPREAD_PIPS[pair] / 2`

これは Audit-A と統合してよい (実質、entry/exit に full spread 控除と同等)。**重複控除に注意** (PAIR_SPREAD_PIPS を spread 全体、half_spread を入退分配で計算)。

## 3.4 統合 BT 実行

新 BT runner: `scripts/run_session_mr_cross_wave1_audit_bt.py` を新規 (既存を破壊しない):

10 cell 全部について以下 4 variant を計算:

| Variant | Audit-A (friction) | Audit-B (lookahead) | Audit-C (bid/ask) |
|---|---|---|---|
| `baseline` | OFF (`entry_cost_pips=0.6`) | OFF (現実装) | OFF |
| `audit_a` | ON | OFF | OFF |
| `audit_ab` | ON | ON (SL-first hard) | OFF |
| `audit_abc` | ON | ON | ON |

各 variant について各 cell の N/WR/EV/PF/Wilson/Bonferroni-p (m=10, α=0.005)/WF を出力。

## 3.5 出力

- `knowledge-base/raw/bt-results/session-mr-cross-wave1-audit-2026-05-11.json` (機械可読、4 variant × 10 cell)
- `knowledge-base/raw/bt-results/session-mr-cross-wave1-audit-2026-05-11.md` (人読み、verdict まとめ)
- `knowledge-base/raw/audits/session-mr-cross-wave1-lookahead-audit.md` (D2 詳細)

---

# 4. ACCEPT / NEEDS_MORE_EVIDENCE / REJECT (audit_abc variant で評価)

`audit_abc` (3 audit 全反映) でセル毎に判定:

## ACCEPT (Wave 2 真の候補)
**すべて満たす**:
- N >= 30
- post-friction-and-bid-ask EV > 0.10 pip/trade
- PF >= 1.15
- Wilson lower (WR) > 0.50
- WF 4-fold で EV 符号一致 fold >= 3

## NEEDS_MORE_EVIDENCE
- PF >= 1.05 かつ EV >= 0
- Wilson lower > 0.45
- WF >= 2/4

## REJECT
上記いずれも非該当

## Wave 1 全体 verdict (audit_abc で評価)

| ACCEPT cell 数 | Verdict |
|---|---|
| **>= 5** | TRUE_WAVE_2_GO (Wave 2 spec 起草) |
| **2-4** | LIMITED_WAVE_2 (絞った cell のみ shadow 投入) |
| **1** | DOWNGRADE_SHADOW_ONLY (Wave 2 規模縮小、N 蓄積モード) |
| **0** | REJECT (Wave 1 verdict は curve-fit 確定、本族 academic only Tier 3) |

🔒 **Pre-reg LOCK**: audit_abc が ACCEPT 数 4 以下なら、それを覆す事後緩和 (Bonferroni m 縮小 / Wilson threshold 0.45 引き下げ / PF 1.10 引き下げ) は**禁止**。緩和したくなったら本タスク後の新 R1 task として pre-reg やり直し。

---

# 5. 月利100%ロードマップへの寄与

**進める Gate**: Gate 1 (Aggregate Kelly > 0) — Wave 2 shadow 投入の品質ゲート。

これは「速さ」より「規律」のタスク。Wave 2 投入後に live で崩壊させて Kelly を更に悪化させるリスクを事前に断つ。Codex 自動 promotion の罠を司令塔が止める典型例として fx-ai-trader 全体の規律強化の資産になる。

---

# 6. 検証コマンド (Codex が実行)

```bash
# 1. 既存 Wave 1 結果との比較ベースライン確保
cat knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.json | jq '.cells[].verdict'

# 2. friction lookup の存在確認 (modules/friction_model_v2.py に cross-minor がない場合は task 内で実装)
python3 - <<'PY'
from modules.friction_model_v2 import friction_for_pair_or_default  # 想定 API
for p in ["EUR_NZD","AUD_NZD","AUD_CAD","NZD_CAD","EUR_GBP"]:
    print(p, friction_for_pair_or_default(p))
PY

# 3. 監査統合 BT 実行
python3 scripts/run_session_mr_cross_wave1_audit_bt.py \
  --pairs EUR_NZD AUD_NZD AUD_CAD NZD_CAD EUR_GBP \
  --windows NY_LATE TOKYO_OPEN \
  --variants baseline audit_a audit_ab audit_abc \
  --days 365 \
  --out knowledge-base/raw/bt-results/session-mr-cross-wave1-audit-2026-05-11

# 4. 結果 sanity
python3 tools/sanity_check_bt_report.py \
  knowledge-base/raw/bt-results/session-mr-cross-wave1-audit-2026-05-11.json

# 5. unit test for new audit BT runner
python3 -m pytest tests/test_session_mr_cross_audit.py -x -v

# 6. 全 regression (既存 vix_carry_unwind routing test 失敗は別作業由来。本タスクは触らない)
python3 -m pytest tests/ -x -q --deselect tests/test_volume_live_promote_routing.py
```

---

# 7. 受け入れ条件

1. `scripts/run_session_mr_cross_wave1_audit_bt.py` 新規追加 (既存 BT runner は触らない)
2. `tests/test_session_mr_cross_audit.py` 新規、>= 5 case
   - PAIR_SPREAD_PIPS lookup
   - SL-first hard ordering 強制テスト
   - bid/ask 控除の単方向テスト (BUY と SELL で entry/exit 符号正しい)
   - 4 variant の出力 schema 確認
   - regression: 既存 BT runner の baseline と新 BT runner の baseline で結果一致
3. `knowledge-base/raw/bt-results/session-mr-cross-wave1-audit-2026-05-11.{md,json}` 生成
4. `knowledge-base/raw/audits/session-mr-cross-wave1-lookahead-audit.md` 生成 (D2 詳細)
5. 各 variant × 各 cell に N/WR/EV/PF/Wilson/Bonf-p/WF が記載
6. audit_abc verdict (ACCEPT 数別) で全体 verdict 明示 (TRUE_WAVE_2_GO / LIMITED / DOWNGRADE / REJECT)
7. 既存 `python3 -m pytest tests/test_session_mr_cross.py -x -q` regression なし
8. `scripts/check.py` PASS
9. **commit するが push しない**。司令塔レビュー後に手動 push

未達なら `status: changes_requested`。

---

# 8. 禁止事項

- **既存 `scripts/run_session_mr_cross_wave1_bt.py` 改変禁止** (baseline 保護のため新ファイルで分離)
- **既存 `modules/strategies/session_mr_cross.py` 改変禁止** (Wave 1 で固定された signal 仕様の維持)
- **既存 Bonferroni m=10 / Wilson threshold / PF threshold 緩和禁止** (audit_abc で出た数字をそのまま採用、事後緩和は本タスク終了後の別 R1 で)
- **Live / Shadow / OANDA / .env への接続禁止**
- **`modules/demo_trader.py` 変更禁止**
- **MASSIVE 追加 fetch 禁止** (既存 cache 利用、MASSIVE_API_KEY は使わない)
- **既存未コミット変更を上書きしない**
- **`test_volume_live_promote_routing.py` の test 修正禁止** (別タスク、本タスクは `--deselect` で回避)
- **XAU / 24h trading 前提の friction 値使用禁止**

---

# 9. 完了後の司令塔アクション

ACCEPT cell 数別に分岐:

| Verdict | 次タスク |
|---|---|
| TRUE_WAVE_2_GO (>=5) | Wave 2 shadow spec を別 R1 task で起草 (Tier promotion gate / lot 0.01 / monitoring) |
| LIMITED_WAVE_2 (2-4) | 残った cell のみで Wave 2 spec、絞った lot |
| DOWNGRADE_SHADOW (1) | shadow 単独運用 (Live 昇格保留)、N 蓄積監視 |
| REJECT (0) | lesson markdown 作成、tier-master と W4-EDA カタログを更新、本族は academic only Tier 3 |

---

**司令塔承認**: 2026-05-11 17:15 JST (Claude as Quant)
**Codex 着手承認待ち**: queued
