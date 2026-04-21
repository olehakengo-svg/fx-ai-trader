# 次セッション引き継ぎ: Shadow 全戦略 TP/SL 条件分析 + 戦略分割

**作成**: 2026-04-21
**実行想定**: 次セッション以降 (cold-start OK、本文書単体で完結)

---

## 🎯 User が達成したい 4 つのこと

1. **全戦略 Shadow 走行時の TP-hit 条件**を数学的に抽出 (ペア・時間帯込み)
2. **N≥10 で WR が勝てる水準に上がる条件**を見つけ、該当を **LIVE 化**
3. **各戦略の SL hit 条件**を詳細分析
4. **SL 条件を排除した新戦略**として生まれ変われるか判定 (戦略分割候補化)

**全体方針**:
> 勝てる条件 → 閾値調整で強化 / 負ける条件 → 排除して新戦略化

---

## 🚫 Scope 明確化 (失敗から学んだ境界)

本日の作業で **scope creep** が何度か発生. 次回は以下を守る:

| やること | やらないこと |
|---|---|
| **Shadow data only** (is_shadow=1) | Live data を混ぜない (分析を汚染する) |
| 全 60 tier-master 戦略 + ghost 5 | L1 12 戦略だけにフォーカスしない |
| **ペア × 時間帯** を条件に必須 | 単一 feature 分析で止めない |
| Pre-registration で閾値を binding | 観測後に基準変更しない |
| production 変更は必ず pre-reg 経由 | data 見て即実装しない |

---

## 📋 Task 1: Shadow 全戦略 TP-hit 条件抽出

### 1.1 Input

- **データ**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2500`
- **Filter**: `is_shadow=1 AND outcome IN ("WIN","LOSS")`
- **期間**: 全 shadow (期間制限なし) — 過去分析との比較用
- **subset**: post-Cutoff (2026-04-16 以降) — 現状 regime 下の評価用

### 1.2 必須 feature 軸

以下を**すべて含めた条件組合せ**で集計:

| 軸 | 値 |
|---|---|
| **instrument** | USD_JPY / EUR_USD / GBP_USD / EUR_JPY / GBP_JPY / EUR_GBP |
| **_session** (UTC 時間) | tokyo (0-8) / london (8-13) / ny (13-22) / offhours (22-0) |
| **_hour** (1時間刻み) | 0-23 |
| **direction** | BUY / SELL |
| **mtf_regime** | range_tight / range_wide / trend_up_* / trend_down_* (84% missing 注意) |
| **mtf_vol_state** | squeeze / expansion / normal |
| **mtf_alignment** | aligned / conflict / neutral |
| **rj_adx** (quartile) | Q1-Q4 |
| **rj_atr_ratio** (quartile) | Q1-Q4 |
| **rj_close_vs_ema200** (quartile) | Q1-Q4 |
| **rj_hmm_regime** | trending / ranging |
| **confidence** (quartile) | Q1-Q4 |

### 1.3 必須 output 形式

各戦略ごとに出力:

```
## {strategy_name} (Shadow N={total}, WIN={w}, LOSS={l}, baseline WR={wr}%)

### A. WIN 条件 (TP hit 条件 — N_cell≥3 で報告)
| instrument × session × direction | N | WR | LR | Wilson CI |
|---|---|---|---|---|
| USD_JPY × NY × BUY | 8 | 62.5% | 2.3x | [30%, 87%] |
| ...

### B. LOSS 条件 (SL hit 条件)
| instrument × session × direction | N | cell WR | LR(loss) |
| GBP_USD × Tokyo × SELL | 12 | 8.3% | 2.5x |
| ...

### C. Split 候補 (WIN 条件で絞ると WR≥50% になるか?)
  Rule: if (instrument in [X,Y] AND session=Z AND direction=W) then fire
  Virtual filtered: N_post=?, WR_post=?, lift=?
```

### 1.4 Implementation 指針

- 既存スクリプト流用可: `/tmp/shadow_only_coverage.py`, `/tmp/win_characterization.py`, `/tmp/win_conditions_mining.py`
- 新規要: pair × session × direction の 3-way cell mining
- **最小 cell N = 3** (2-way は N=5 以上、3-way は N=3 以上 — 個別 trade listing で補完)

---

## 📋 Task 2: LIVE 化候補の数学的基準 (binding pre-register)

### 2.1 Promotion gate (本 task で LIVE 昇格判断する条件)

| Gate | 基準 | 論理 |
|---|---|---|
| G1: N | 該当 condition cell で **shadow N ≥ 10** | 統計的意味 (Wilson CI が収束) |
| G2: WR | **cell WR ≥ 50%** | Break-even を確実に上回る |
| G3: Lift | **Lift = cell_WR / baseline ≥ 1.5** | 差別化力 |
| G4: Wilson 下限 | **95% CI 下限 > BEV_WR** (pair 依存) | 偶然性排除 |
| G5: Bonferroni | 多重検定後 **p < α/M** | Cherry-picking 防止 |

**全 5 gates パスで LIVE 昇格候補**.

### 2.2 Pair × Session gate の具体例

もし `bb_squeeze_breakout × USD_JPY × NY session × BUY` で N=12 WR=67% Lift=2.5x:
- G1 N=12 ≥10 ✓
- G2 WR=67% ≥50% ✓
- G3 Lift=2.5x ≥1.5 ✓
- G4 Wilson 下限 [38%, 88%] — 下限 38% > BEV 34.4% ✓ (USD_JPY)
- G5 Bonferroni — 探索空間 M により判定

→ **5 Gates パス なら「`bb_squeeze × USD_JPY × NY時間帯` のみ LIVE」** を pre-register

### 2.3 実装: 条件付き gate

`modules/demo_trader.py::_should_send_to_oanda` に condition-specific check を追加可能:

```python
_PAIR_SESSION_PROMOTED = {
    ("bb_squeeze_breakout", "USD_JPY", "ny"): {"directions": {"BUY"}},
    # ...
}
```

ただし**実装前に shadow で virtual filter simulation 必須** (本当に WR が上がるか cold data で確認).

---

## 📋 Task 3: SL-hit 条件の全戦略個別抽出

### 3.1 目的
各戦略の「負ける condition」を identifiable parts に分解.

### 3.2 方法

各戦略で LOSS 集団を独立に分析:

```
## {strategy} LOSS 条件 (Shadow LOSS 専用 characterization)

### LOSS が集中する pair × session × direction
  Top 3 cells where (LOSS count / total count) は高く、N≥5

### Feature Q4 で LOSS が enriched (Q4 cell WR 低)
  confidence Q4 WR=12%, ADX Q4 WR=14% など

### LOSS の共通 MAE/MFE pattern
  LOSS の mafe_favorable median はどの位置か?
  (本日の Phase 2 で確認済: LOSS は mafe_fav 0.7-2.0pip 止まり)
```

### 3.3 出力 format

```
## {strategy} SL condition fingerprint

| Rank | 条件 | N | WR | 解釈 |
|---|---|---|---|---|
| 1 | GBP_USD × Tokyo × SELL | 15 | 6.7% | "GBP_USD の Tokyo SELL で死" |
| 2 | EUR_JPY × any × any | 46 | 13.0% | "EUR_JPY 全般で機能せず" |
| 3 | confidence Q4 (high) | 28 | 14.3% | "高 confidence ほど負ける 逆説" |
```

---

## 📋 Task 4: 戦略分割判定 (loss 条件排除 → 勝ち戦略化?)

### 4.1 核心の数学的問い

> 「LOSS 条件を完全排除した残りの trade の WR は 50% 以上か?」

これが成立すれば: **既存戦略 → "LOSS 条件を避けた部分戦略" に split**

### 4.2 Decision tree

```
既存戦略 (baseline WR 25-35%)
├─ LOSS 条件を排除 (pair × session × direction フィルター)
│  ├─ 残り N ≥ 30 かつ WR ≥ 50% ？
│  │  ├─ YES → 新戦略 "{strat}_filtered" として separation
│  │  └─ NO → filter 効果が不十分, continuation
│  └─ 残り N < 30 → N 不足, shadow 蓄積待ち
└─ (何もしなければ) 現状維持
```

### 4.3 Split の実装 (概念)

```python
# 例: bb_rsi_reversion を split
# オリジナル: 広範囲に発火 (baseline WR 29%)
# Split:
#   bb_rsi_reversion_PRIME: USD_JPY × NY_hours × BUY (WR 55%想定) → LIVE
#   bb_rsi_reversion_SHADOW: 他の全条件 (WR 20%想定) → 継続 shadow
```

コード上は 2 signal function を分岐 or 既存 function 内で conditional return.

### 4.4 統計的妥当性

分割操作は **post-hoc 探索なので multiple testing 補正必須**:

- 60 戦略 × 6 pair × 4 session × 2 direction = 2880 cells 探索空間
- Bonferroni α/2880 = 1.74e-5 が必要
- ほぼすべての "golden cell" が Bonferroni で非有意 → **確実性を要求しない hypothesis として扱う**
- 分割後は必ず **shadow 追加蓄積で out-of-sample 検証**

---

## 🧮 数学的 Framework (クオンツ視点)

### a. Metrics 統一

| 指標 | 式 | 閾値 |
|---|---|---|
| WR_cell | wins_in_cell / total_in_cell | — |
| Lift | WR_cell / WR_baseline_strategy | ≥ 1.5 |
| Wilson CI 95% | `p ± z*sqrt(p(1-p)/n + z²/(4n²))/(1+z²/n)` | 下限 > BEV |
| LR (likelihood ratio) | P(cell \| WIN) / P(cell \| LOSS) | ≥ 2.0 |
| Fisher exact | 2x2 table: cell_W/cell_L vs other_W/other_L | p < α/M |
| PLR positive | LR_WIN / LR_LOSS | 分離力 |

### b. Binary decision rule (確認プロセス)

```
for strategy in all_strategies:
  for (instr, sess, dir, ...) in search_space:
    cell = filter_shadow_trades(strategy, instr, sess, dir, ...)
    if N(cell) < 10: skip
    if cell_WR < 0.5: continue
    if Lift < 1.5: continue
    if Wilson_lower(cell) < BEV(instr): continue
    if Bonferroni_p > alpha/M: continue
    PROMOTION_CANDIDATE.add(strategy, condition)
    
  for (neg_instr, neg_sess, neg_dir, ...) in search_space:
    loss_cell = ...
    if N(loss_cell) < 10: skip
    if loss_cell_WR > 0.2: continue  # まだ希望がある
    if Loss_LR > 2.0:
      DEMOTION_CANDIDATE.add(strategy, condition)
```

### c. 分割戦略の criterion

```
strategy_split_OK(S) iff
  exists condition C such that:
    WR(S | C) ≥ 0.5
    AND Lift(S | C) ≥ 1.5
    AND N(S | C) ≥ 30
    AND Wilson_lower(S | C) > BEV
    AND Bonferroni passes
```

---

## 🔗 前提となる本日の成果物

次セッション開始時に必ず参照:

### 必読 (順番に)
1. **[[shadow-only-coverage-2026-04-21]]** — 全 65 戦略 shadow 分類 (L1-L4). 本 task の starting point
2. **[[win-characterization-2026-04-21]]** — L1 12 戦略の既存 winner profile (extend 対象)
3. **[[win-conditions-unfiltered-2026-04-21]]** — portfolio-wide null finding (特に regime data 84% 欠損)
4. **[[shadow-tp-sl-causal-2026-04-21]]** — MAE/MFE decomposition (既存 LOSS 知見)
5. **[[audit-b-promoted-strategies-2026-04-21]]** — vwap_mean_reversion red flag と Audit B 手順
6. **[[negative-strategy-stop-conditions-2026-04-21]]** — 既存 stop 基準

### 既存スクリプト (流用推奨)
- `/tmp/shadow_only_coverage.py` — 65 戦略 accounting
- `/tmp/win_characterization.py` — L1 戦略 A-E 分析
- `/tmp/win_conditions_mining.py` — 2-way cell mining (golden cell 探索)

---

## 🚨 重要な data 限界 (分析設計時の制約)

1. **Regime data 84% missing**: mtf_regime, mtf_vol_state, mtf_alignment は v9.2.1 (2026-04 以降) の trades のみに populated. 古い shadow では使用不可.
2. **Pre-v9.x artifact**: 古い trades は現在と異なるロジックで生成. 現在の fire 条件と一致しない可能性.
3. **Shadow ≠ Live**: dt_fib_reversal 事例のように Shadow WR と Live WR が乖離することがある. 必ず Live 追加検証.
4. **Post-Cutoff N 限界**: 5日で N=840. pair × session × direction = 48 cells だと平均 N=17. 多くの cell で N<10.
5. **Bonferroni 脆弱性**: 探索空間大きいため、strict FWER 制御では ほぼすべての cell が非有意. 報告は "hypothesis" として扱う.

---

## 🎯 次セッション deliverables

### 必須
1. **戦略別 TP-hit condition table** (全 65 戦略 × pair × session × direction)
2. **LIVE 化候補リスト** (G1-G5 全 pass)
3. **戦略別 SL-hit condition fingerprint**
4. **戦略分割候補リスト** (split criterion 満たすもの)
5. **Shadow validation pre-registration 更新** ([[shadow-validation-preregistration-2026-04-21]] の追加 hypothesis 登録)

### optional (time permits)
6. 5 ghost 戦略の tier-master 反映
7. vwap_mean_reversion Audit B (第二弾)
8. Confidence 逆向き signal の構造 audit (bb_rsi / bb_squeeze / ema_cross / vol_surge)

---

## ⚠️ Production 変更の前に必ず守るプロトコル

1. **Shadow で virtual filter simulation**: 提案条件でどれだけ trade 数が減り、WR が上がるか先に計算
2. **Pre-registration**: 事前に基準を binding 登録 (本日の [[pre-registration-2026-04-21]] と同形式)
3. **Tier_integrity_check + pre-commit tests** パス必須
4. **Small-lot trial → 観察 → 本昇格** の 3 段階. 直接 full-lot promotion は禁止
5. **Audit B と対称**: 昇格 = pre-reg, 降格 = audit B. 両輪で管理

---

## 📦 本日までの累積 commit (新セッション開始時に `git log` 参照)

```
d55b316 Shadow-ONLY coverage (訂正版) ← 本 handover の前提
997be09 Coverage audit (Live混在で誤り — 訂正済)
ea1d79f WIN 条件 characterization (L1 12戦略)
748c59f Shadow validation pre-registration
00283f7 WIN conditions filtered + unfiltered
3d1e6d8 Shadow TP vs SL 深部因果分析
db160b2 dt_fib_reversal×GBP_USD Audit B 撤回
6c5a516 vol_surge_detector×USD_JPY PAIR_DEMOTED 撤回
db12a07 bb_squeeze_breakout×USD_JPY PAIR_PROMOTED 復活
a22fa14 _BT_SLIPPAGE Tier 1
```

---

## ❓ 次セッション開始時の最初の質問

新セッションで Claude に尋ねるべきこと:

```
本文書 [[handover-shadow-deep-analysis-2026-04-21]] に従い、
Task 1 (全戦略 Shadow TP-hit 条件抽出) から開始してください。

特に重要:
- Shadow only (is_shadow=1)
- pair × session × direction を軸に含めて
- N≥10 の条件で WR≥50% Lift≥1.5 を探索
- 結果を binding pre-register した上で、
  LIVE 化候補と新戦略 split 候補の両方をリスト化
```
