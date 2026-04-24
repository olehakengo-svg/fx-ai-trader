# Pre-registration: MAFE Dynamic Exit (Time-Decay / Early Stop-out) — 2026-04-24

**Locked**: 2026-04-24 (本 doc 確定後 binding criteria 変更禁止)
**Upstream**: [[shadow-deep-mining-2026-04-24]] (Option C 経路)
**Rationale**: Option A (filter) と Option B (contrarian) は deep-mining で null。
  残された forward-usable 仮説は「動的 exit で損失分布を左シフトできるか」のみ

## 0. TL;DR

Shadow で死んでいる mean-reversion 系戦略の損失は、**エントリー後早期に順行 (MFE) が
僅少 or 逆行 (MAE) が閾値超過** で判定可能な「失敗パターン」が支配している可能性。
SL 到達を待たずに `X 本以内に MFE ≥ Y pips 未達 or MAE ≥ Z pips 超過` で強制撤退すれば、
**平均損失縮小 → EV 改善** が期待できる。
これを **365 日 BT で pre-registered parameter search** → 事前 LOCK した success criteria で
GO/NO-GO 判定。

## 1. Hypothesis (Forward-Usable Form — 再定式化)

### Primary Hypothesis (H_primary)

> **"エントリー後 X 本 (5m bar) 以内に、累積 MFE (favorable excursion) が Y pips に達しない、
> または累積 MAE (adverse excursion) が Z pips を超えた場合、
> その trade の最終 WR は極めて低い。SL 到達を待たずに即時撤退することで
> **戦略全体の EV が有意に改善する** (BT EV delta ≥ +0.5p)"**

### なぜ forward-usable か

- MFE/MAE は **bar close ごとに計算可能** (その時点までの max favorable/adverse excursion)
- エントリー時点で未来を見ていない — bar ごとに state が更新され、閾値突破で exit signal
  が発生する
- [[shadow-deep-mining-2026-04-24]] の H3 で指摘した look-ahead bias (close 時点の
  `mafe_adverse_pips` を entry filter に使う誤り) を回避

### Mechanism (quant 的に想定する因果)

1. 順行が早期に発生しない trade は **market が mean-reversion setup を reject** している
2. その場合、SL まで待つと追加で ~3-5 pips 損 (平均 MAE 増加)
3. 早期微損 exit に切り替えれば **損失分布を左シフト** → EV 改善
4. 逆に、早期に MFE が出る trade は setup が valid で TP まで伸ばせる
   (本 hypothesis は winners を cut しない設計)

## 2. Target Strategy (LOCKED)

**Primary: `bb_rsi_reversion`**

| 指標 | 値 | 選定理由 |
|------|---:|----------|
| Shadow N | 198 | 統計的 power 十分 (Fisher detectable at p<0.00128 with ~Δ15pp) |
| Shadow WR | 28.8% | BEV (~50%) との gap が ~20pp — dynamic exit で 5-10pp 縮められれば GO |
| Shadow EV | -1.39 | Target: +0.5p 以上改善 → **-0.89 以下に抑制** |
| Tier | PAIR_DEMOTED | ELITE に影響しない / Shadow-only 検証可 |
| Signal family | RANGE (mean-reversion) | hypothesis と aligned (MR は早期順行で確度判断できる典型) |

**Secondary (parallel test if resources permit): `ema_trend_scalp`**

- N=616 で power 最高
- ただし TREND family は mean-reversion と exit dynamics が異なる — primary
  結果を見てから secondary BT 実行
- **primary で NULL なら secondary は実行しない** (multiple comparison を避ける)

### 除外

- XAU_USD: 全 BT から除外 (CLAUDE.md + feedback_exclude_xau)
- sr_channel_reversal: N=228 だが WR/EV 差分が他 2 戦略より小さく弁別力低い
  (primary の 1 戦略に集中)

## 3. Parameter Grid (LOCKED)

3 次元グリッド:

| Param | Symbol | Grid | 物理的意味 |
|-------|--------|------|------------|
| Time limit | **X** (bars) | {3, 5, 8, 12} | 5m 換算で 15 / 25 / 40 / 60 分 |
| MFE minimum | **Y** (pips) | {0, 1, 2, 3} | X 本時点までの累積 MFE 最小閾値 |
| MAE limit | **Z** (pips) | {3, 5, 8} | 累積 MAE が超えたら即撤退 |

**総セル数**: 4 × 4 × 3 = **48 parameter combinations**

### Exit rule (at each 5m bar close after entry)

```
bar_index = ceil((now - entry_time) / 5min)

if MAE_cumulative >= Z:
    exit_reason = "mae_breach"
    close_position_at_market()

elif bar_index >= X and MFE_cumulative < Y:
    exit_reason = "time_decay_low_mfe"
    close_position_at_market()

elif bar_index >= X and MFE_cumulative >= Y:
    # setup is valid — keep position until TP/SL (baseline behavior)
    pass
```

### Exit cost

- Market order exit at bar close → exit slippage = per-pair default slippage (既存 BT と同じ)
- Spread cost = per-pair friction (ROUND-trip cost は BT v3 friction model に合致)

## 4. Statistical Test Design (LOCKED)

### Multiple-comparison correction

- Bonferroni α_family = 0.05
- M = 48 (parameter grid) → α_cell = 0.05 / 48 ≈ **1.04e-3**

### Per-cell tests (each of 48 params)

1. **ΔEV (pip per trade)**: V2_EV − BASE_EV
2. **Fisher exact (WR vs BASE)**: two-tailed
3. **Welch t-test (mean PnL vs BASE)**: unequal variance
4. **Wilson 95% lower bound on V2_WR**
5. **Walk-forward stability (WF)**: 365 日を 2 分割、両 bucket で EV delta > 0 かつ同符号

### Binding Success Criteria (SURVIVOR — 一次採択)

**全条件 AND:**

- [ ] ΔEV ≥ **+0.5 p/trade** (primary objective)
- [ ] ΔEV の Welch p < **1.04e-3** (Bonferroni 補正後有意)
- [ ] Fisher WR p < **1.04e-3** (WR 変化が有意)
- [ ] Wilson 95% lower bound on V2_WR > **BEV + 3pp** (= ~53%)
- [ ] WF 2-bucket の両方で ΔEV > 0 (同符号安定性)
- [ ] V2_N (V2 ルール下でのエントリー数) ≥ **80** (power 保持 — original N=198 の 40%)
- [ ] exit_reason 分布が極端でない — "time_decay" と "mae_breach" の比率が 20:80 〜 80:20 の範囲

### CANDIDATE (二次 — Shadow 延長観察)

- ΔEV ≥ +0.3 p/trade **かつ** Welch p < 0.01 (uncorrected) **かつ** WF 2-bucket 同符号
- 本 criteria に合致したものは、Bonferroni に届かないが **Phase holdout 2026-05-07 以降の
  追加 N** で再検定 ([[pre-registration-label-holdout-2026-05-07]] 枠)

### REJECT (明示的 null)

- 48 cells すべて SURVIVOR criteria 未達
- → hypothesis H_primary は **棄却** として [[shadow-deep-mining-2026-04-24]]
  に closure 記録、[[lessons/index]] に教訓ページ追加

## 5. BT Execution Plan

### Data source

- 365 日 OHLCV (5m) — Massive API primary
- Pairs: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY (XAU 除外)
- Post-cutoff date: 2026-04-08 以降は **holdout として除外**
  (Live Shadow data と独立性保持 → data leakage 防止)
- BT window: **2025-04-09 〜 2026-04-08** (exactly 365 days pre-cutoff)

### Friction model

- BT v3 (現行) — per-pair RT friction を exit cost に加算
- Market-order exit を想定するため、TP/SL でなく市場執行の slippage を適用

### Implementation outline

```python
# /tmp/mafe_dynamic_exit_bt.py (script to be authored post-LOCK)

BASELINE_STRATEGY = "bb_rsi_reversion"
X_GRID = [3, 5, 8, 12]
Y_GRID = [0, 1, 2, 3]
Z_GRID = [3, 5, 8]
BT_FROM = "2025-04-09"
BT_TO   = "2026-04-08"
PAIRS = ["USD_JPY","EUR_USD","GBP_USD","EUR_JPY","GBP_JPY"]
FRICTION = {"USD_JPY":2.14, "EUR_USD":2.00, "GBP_USD":4.53, "EUR_JPY":2.50, "GBP_JPY":3.0}

# Step 1: replay baseline bb_rsi_reversion entries on historical 5m bars
# Step 2: for each entry, simulate per-bar MFE/MAE evolution
# Step 3: apply exit rule at each (X,Y,Z) combination
# Step 4: compute V2 PnL vs BASE PnL per param-cell
# Step 5: Fisher/Welch/Wilson/WF per cell
# Step 6: output /tmp/mafe_dynamic_exit_results.csv
```

### Output artifacts

- `/tmp/mafe_dynamic_exit_results.csv` (48 rows × metrics)
- `raw/bt-results/mafe-dynamic-exit-2026-04-24.json` (machine-readable)
- `wiki/analyses/mafe-dynamic-exit-result-2026-04-24.md` (human-readable, post-BT)

## 6. Post-BT Decision Tree (LOCKED before data look)

```
     ┌── ≥1 cell SURVIVOR ──▶ GO path (§6.1)
     │
[BT run]─┼── only CANDIDATE cells ──▶ Extended Shadow path (§6.2)
     │
     └── 48/48 REJECT ──▶ Closure path (§6.3)
```

### §6.1 GO path (SURVIVOR ≥ 1)

1. SURVIVOR cell が複数ある場合、**最小 param 複雑度 の cell を選ぶ** (X 最小優先 → Y=0 優先)
2. `modules/` の bb_rsi_reversion signal logic に `_dynamic_exit()` を追加 — Shadow-only
   deploy (is_shadow=1) で N≥30 再検証
3. Shadow-only で **N≥30 かつ ΔEV 同符号 維持** を確認 → Live 展開を**別 pre-reg で** LOCK
4. 本 pre-reg の scope はここまで — Live 展開は独立した意思決定

### §6.2 Extended Shadow path (CANDIDATE only)

1. [[pre-registration-label-holdout-2026-05-07]] の枠で追加 N を取得
2. **current pre-reg の binding criteria は hold** — 追加 N で再検定
3. 2026-05-14 時点 (2 週後) で再集計。SURVIVOR 到達で §6.1、未達で §6.3

### §6.3 Closure path (全 REJECT)

1. `wiki/analyses/mafe-dynamic-exit-result-2026-04-24.md` に full result 格納
2. `wiki/lessons/` に lesson 追加: "bb_rsi_reversion の動的 exit は 48 cell 検定で null.
   現行 regime の MR 系は structural に dead (friction>edge)"
3. ema_trend_scalp secondary は **実行しない** (primary null なら family-level で null と判断)
4. bb_rsi_reversion は FORCE_DEMOTED 扱いを維持 (実質 stop)

## 7. Anti-Pattern Guard (LOCKED)

本 pre-reg の binding は以下を明示的に禁止:

- [ ] **Post-hoc parameter 追加**: 48 cell が null なら「あと 1 パラメータ増やせば...」は禁止
- [ ] **Target strategy swap**: primary null でも sr_channel_reversal に流用 禁止
  (別 pre-reg で LOCK 必要)
- [ ] **BT window swap**: 365 日が null なら「180 日で見れば...」は禁止
- [ ] **Bonferroni loosening**: α_cell を 1.04e-3 から緩めることは禁止
- [ ] **XAU rescue**: XAU を含めれば +EV に見える場合でも XAU 除外を維持
  ([[shadow-deep-mining-2026-04-24]] §"Statistical artifact caught" 参照)
- [ ] **"almost significant" 救済**: p = 1.05e-3 でも REJECT

違反時: [[lesson-reactive-changes]] に倣い、次 session 開始時の injection で再発防止

## 8. References

- [[shadow-deep-mining-2026-04-24]] — 本 pre-reg の直接 upstream
- [[cell-level-scan-2026-04-23]] — Phase 2 Scenario A
- [[pre-registration-phase2-cell-level-2026-04-23]] — DO/DO NOT list の原典
- [[lesson-reactive-changes]] — 1 日データ実装禁止
- [[friction-analysis]] — RT friction per pair
- [[bt-live-divergence]] — 6 類型 bias の警戒リスト
- [[pre-registration-label-holdout-2026-05-07]] — CANDIDATE 延長枠
- CLAUDE.md 判断プロトコル — 全 criteria はこれに準拠

---

**Author**: Claude (quant-analyst mode)
**Review status**: LOCKED — data look 前
**Execution owner**: 次 session (BT script 作成 + 実行)
**Max allowed session effort**: BT 実行 + result doc 1 本 (code deploy は別 pre-reg)
