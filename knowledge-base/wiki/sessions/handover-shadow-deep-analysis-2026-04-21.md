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

## 📋 Task 2: 勝ち戦略の閾値調整と LIVE 化 (Branch 1 相当)

### 2.0 「閾値調整」の 3 つの意味

ユーザー要求「勝てるものは閾値調整を行い勝率を上げる」の **具体的な操作**:

| 調整軸 | 具体内容 | 例 |
|---|---|---|
| **a. Condition gate** | WIN 集中 cell のみ発火許可 | `bb_squeeze × USD_JPY × NY ∧ BUY` のみ LIVE |
| **b. Lot multiplier** | WIN 確度に応じ lot 増 | Kelly Half = 1.3-1.5x for PAIR_PROMOTED |
| **c. Confidence 閾値変更** | scoring threshold の上下 | 逆向き signal 戦略は閾値引き下げ |

Task 2 は主に **(a) condition gate** による閾値調整. (b) は Branch 1 の lot boost, (c) は別 audit (confidence 逆向き signal 調査) に分岐.

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

## 📋 Task 4: 負け条件排除 → 勝ち戦略化 (3-branch decision)

### 4.0 **CORE の数学的問い** (本 task の本質)

> **「LOSS 条件を排除したとき、残りの trade の WR は 50% 以上になるか?」**
>
> YES → 新戦略 / 既存戦略強化 の 2 パス
> NO → 統計的に救えない戦略. 継続 shadow or FORCE_DEMOTE

ここが本 session の**最大の価値創出ポイント**. LOSS 条件排除による戦略救済が成立するかを戦略ごとに判定する.

### 4.1 3-Branch Decision Tree

全 65 戦略 × すべての条件 cell を以下で分岐:

```
戦略 S の baseline WR = W_0
│
├── Branch 1: 勝ち戦略の閾値調整 (strengthening winners)
│   条件: W_0 ≥ 40% or 既に PAIR_PROMOTED/ELITE_LIVE
│   Action: WIN 集中 cell で lot boost / confidence 閾値緩和
│   例: bb_squeeze × USD_JPY × NY で lot 1.3x 昇格 (本日 pre-reg 済)
│
├── Branch 2: 負け条件排除 → 新戦略 split (conversion)  ← ここが本 task の核心
│   条件: W_0 < 40% で LOSS 条件を特定可能
│   手順:
│     (1) LOSS が集中する cells を Fisher/LR で抽出 (LOSS_LR ≥ 2.0)
│     (2) それらの cells を exclude filter として定義
│     (3) filter 後の残り trades で WR を再計算 = W_post
│     (4) W_post ≥ 50% かつ N ≥ 30 ならば ★新戦略 {S}_PRIME として split★
│     (5) W_post < 50% or N < 30 → Branch 3 へ
│
├── Branch 3: 継続 shadow / 廃止
│   条件: Branch 1/2 いずれも成立せず
│   Action: shadow 継続 (N 蓄積) or FORCE_DEMOTE (救えない)
│
└── Branch 0: 既に LIVE で勝っている戦略
    Action: 現状維持, 観察のみ
```

### 4.2 Branch 2 の具体手順 (LOSS → WIN conversion algorithm)

**入力**: 戦略 S の全 shadow trades
**出力**: 新戦略 split 提案 or "救済不可" 判定

```python
def loss_to_win_conversion(strategy_trades):
    baseline_WR = count_wins(trades) / count_all(trades)
    
    # Step 1: LOSS 条件抽出
    loss_cells = []
    for condition in all_conditions:  # pair × session × direction × feature Q4 etc.
        cell_trades = filter(trades, condition)
        if len(cell_trades) < 5: continue
        cell_WR = count_wins(cell_trades) / len(cell_trades)
        loss_LR = P(condition | LOSS) / P(condition | WIN)
        if cell_WR <= 0.15 and loss_LR >= 2.0 and cell_has_significance:
            loss_cells.append(condition)
    
    # Step 2: 排除 filter 定義
    exclude_filter = OR(loss_cells)  # いずれか該当で除外
    
    # Step 3: filter 後 WR 再計算
    surviving = [t for t in trades if not exclude_filter.matches(t)]
    n_post = len(surviving)
    wr_post = count_wins(surviving) / n_post if n_post > 0 else 0
    
    # Step 4: 判定
    if wr_post >= 0.50 and n_post >= 30:
        return "NEW_STRATEGY", {
            "name": f"{strategy_name}_PRIME",
            "fire_condition": f"NOT ({exclude_filter})",
            "expected_WR": wr_post,
            "expected_N_per_period": n_post * (current_period / total_period),
            "lift_vs_baseline": wr_post / baseline_WR,
        }
    else:
        return "UNSALVAGEABLE", {"reason": f"W_post={wr_post}, N_post={n_post}"}
```

### 4.3 新戦略の naming convention

| Pattern | 名前例 | 意味 |
|---|---|---|
| 勝ち条件に絞る | `{S}_PRIME` | WIN 集中 cell のみ発火 |
| 負け条件排除 | `{S}_FILTERED` | LOSS cell を exclude |
| Pair 限定 | `{S}_USDJPY`, `{S}_GBPUSD` | pair-specific |
| Session 限定 | `{S}_NY`, `{S}_TOKYO` | session-specific |
| 複合 | `{S}_USDJPY_NY_BUY` | pair × session × direction |

### 4.4 Split 実装の技術パス

#### Path A: Pair/Session/Direction filter (軽量)

既存コードの `_should_send_to_oanda` に condition check を追加:

```python
_CONDITION_GATES = {
    ("bb_rsi_reversion_PRIME", "USD_JPY"): {
        "sessions": {"ny"}, "directions": {"BUY"}, "hour_range": (13, 20),
    },
}
```

既存 `bb_rsi_reversion` signal は変更せず、OANDA 送信段階で条件 filter. コード変更最小.

#### Path B: Signal function 内 conditional return (構造変更)

```python
def bb_rsi_reversion_signal(ctx):
    # ... 既存ロジック ...
    if signal_fires:
        if is_prime_condition(ctx):  # USD_JPY NY BUY
            return {"entry_type": "bb_rsi_reversion_PRIME", ...}
        else:
            return {"entry_type": "bb_rsi_reversion_SHADOW", ...}  # 元戦略継続
```

**推奨**: Path A (既存ロジック不触、gate 層で filter). コード review しやすく roll back 容易.

### 4.5 期待される output deliverable (具体例)

次 session が出力すべき表:

```
## 戦略救済候補リスト (LOSS→WIN conversion results)

| 既存戦略 | baseline WR | LOSS 条件 | filter 後 WR | N_post | 判定 | 新戦略名 |
|---|---:|---|---:|---:|---|---|
| sr_channel_reversal | 23.8% | USD_JPY×Tokyo×SELL除外 | 38.5% | 78 | NEEDS_MORE_N (N<30)|  保留 |
| bb_rsi_reversion | 29.2% | EUR_JPY全排除 + SELL 13-18h 除外 | 52.1% | 41 | ★NEW_STRATEGY | bb_rsi_reversion_PRIME |
| ema_trend_scalp | 24.3% | confidence Q4 除外 | 31.2% | 185 | UNSALVAGEABLE (WR<50%) | — |
| fib_reversal | 35.5% | EUR_JPY×BUY除外 | 42.0% | 150 | UNSALVAGEABLE (WR<50%) | — |
| ...
```

### 4.6 統計的妥当性

分割操作は **post-hoc 探索なので multiple testing 補正必須**:

- 60 戦略 × 6 pair × 4 session × 2 direction = 2880 cells 探索空間
- Bonferroni α/2880 = 1.74e-5 が必要
- ほぼすべての "golden cell" が strict Bonferroni で非有意 → **確実性を要求しない hypothesis として扱う**
- 分割後は必ず **shadow 追加蓄積で out-of-sample 検証**
- **新戦略は必ず pre-registration** ([[shadow-validation-preregistration-2026-04-21]] 形式で) してから shadow で validate → Live 昇格

### 4.7 Danger zone: 避けるべき pattern

1. **Overfit split**: 1-2 trades の極端な分岐に基づく split → N 不足で再現しない
2. **Circular logic**: "WIN を集めた cell" を "WIN profile" と呼んで split → 結果論
3. **Signal integrity 破壊**: 既存戦略のロジックを根底から変更 (Path B の危険)
4. **Multiple testing ignored**: 2880 cells 探索なのに Bonferroni せず報告

### 4.8 数値例 (本日の data で模擬)

仮に次セッションで **bb_rsi_reversion** を対象とした場合 (shadow WR 29.2%, N=130):

```
LOSS 条件抽出 (LOSS_LR ≥ 2.0 の cells):
  - EUR_JPY × any: LR=3.5, cell WR=8%
  - confidence Q4 × any: LR=2.3, cell WR=12%
  - SELL × Tokyo: LR=2.8, cell WR=10%

Exclude filter = (EUR_JPY) OR (confidence Q4) OR (SELL × Tokyo)

Filter 後 trades:
  N_post = 130 - (30 + 20 + 15, deduplicated) ≈ 80
  WIN in surviving = 30 (仮定)
  W_post = 30/80 = 37.5%  ← 50% 未達

判定: UNSALVAGEABLE at current filter
Next step: 更に条件追加 or Branch 3 (FORCE_DEMOTE 候補)
```

逆に **stoch_trend_pullback** (shadow WR 29.2%, N=144) で:

```
LOSS 条件:
  - confidence Q4: LR=2.5, cell WR=10%
  - ADX Q4 (極高ADX): LR=2.2, cell WR=13%
  - GBP_USD × Tokyo: LR=3.0, cell WR=8%

Filter 後:
  N_post ≈ 65
  WIN = 34
  W_post = 52.3%  ← 50% 達成
  判定: ★NEW_STRATEGY = stoch_trend_pullback_FILTERED

実装案:
  既存の stoch_trend_pullback (shadow 継続)
  + 新 stoch_trend_pullback_FILTERED (Branch 1 LIVE 候補)
```

**このようにして、各戦略を "救済成功" か "UNSALVAGEABLE" に分類**するのが Task 4 の核心成果物.

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

### 必須 output (5 tables)

#### Deliverable 1: 全 65 戦略 TP-hit condition table (Task 1)
```
| Strategy | Top WIN cell | N | WR | Lift | Wilson 下限 |
```

#### Deliverable 2: Branch 1 Threshold Adjustment リスト (勝ち戦略強化)
```
| Strategy | 既存 tier | 調整内容 | 変更後 tier | 期待 WR 改善 |
|---|---|---|---|---|
| bb_squeeze_breakout | PAIR_PROMOTED USD_JPY | NY-only filter 追加 | Session-gated | +8pp |
| ...
```

#### Deliverable 3: Branch 2 戦略救済結果 (loss 条件排除 → 新戦略化)
```
| 既存戦略 | LOSS 条件 | filter 後 WR | N_post | 判定 | 新戦略名 |
|---|---|---|---|---|---|
| stoch_trend_pullback | confQ4 + ADXQ4 + GBP_USD×Tokyo | 52.3% | 65 | ★NEW | stoch_trend_pullback_FILTERED |
| bb_rsi_reversion | EUR_JPY + conf Q4 + SELL Tokyo | 37.5% | 80 | UNSALVAGEABLE | — |
| ...
```

#### Deliverable 4: 戦略別 SL-hit fingerprint (Task 3 詳細)
各戦略について LOSS 集中 top 3 condition + 解釈

#### Deliverable 5: Binding pre-registration 更新
- Branch 1 昇格候補を [[pre-registration-2026-04-21]] 形式で binding
- Branch 2 新戦略候補を [[shadow-validation-preregistration-2026-04-21]] 形式で binding
- 2026-05-05 再評価条件を事前宣言

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
