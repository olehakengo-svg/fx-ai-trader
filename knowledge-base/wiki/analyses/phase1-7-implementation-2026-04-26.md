# Phase 1.7 実装ログ — Empirical Toolkit + Friction v2 + Audit + Pre-reg (2026-04-26)

**Date**: 2026-04-26
**Phase**: Edge Reset Phase 1.7 (待機期間活用 — クオンツデヴェロッパーとして全 4 module)
**Plan**: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md` 拡張
**Status**: 全 4 module 実装完了、tests + KB + commit

## 1. Phase 1.7 の位置づけ

Phase 1 (Task 1+2) と Phase 1.5 (Task 3-7、shadow N≥100 蓄積後) の間の待機期間に、
独立 (orthogonal) な infrastructure を仕込む。クオンツデヴェロッパー視点で:
- 待機期間の機会損失を最小化
- Phase 1.5 の意思決定精度を上げる (validator + monotonicity test)
- Phase 3 新エッジ研究の前提整備 (friction v2 + pre-reg LOCK)
- 全 module は orthogonal (互いに confound しない)

## 2. Module A: Empirical Validator (`tools/empirical_validator.py`)

### 提供関数

- **`wilson_ci(n_success, n_total, alpha=0.05)`**: Wilson score interval (small N でも安定)
- **`bootstrap_ci(values, n_resample=1000, alpha=0.05, statistic=None, seed=None)`**: 任意統計量の bootstrap CI
- **`bootstrap_wr_ci(pnls)`**: WR の bootstrap CI
- **`monotonicity_test(bin_values, wr_values, n_permutations=1000)`**: Spearman + permutation
- **`top_k_drop_test(values, k=1)`**: 上位 K 件除いて統計が崩壊しないか (`partial_quant_trap` 要件)
- **`bonferroni_correct(p_values, alpha)`**: multiple testing 補正
- **`benjamini_hochberg(p_values, alpha)`**: FDR 制御 (Bonferroni より lenient)
- **`aggregate_3d(trades, axis1, axis2, axis3, pnl_key)`**: 3 軸で集計、各 cell に N/WR/EV/Wilson_CI
- **`sample_size_for_proportion_diff(p1, p2, alpha=0.05, power=0.80)`**: 必要 N 計算

### 設計

- numpy のみ依存 (scipy なしでも動く)
- 純粋関数群、副作用なし
- 戻り値は dict (JSON シリアライズ可)
- Permutation/bootstrap は 1000 回上限 (計算量制御)

### Tests: 24/24 PASS

`tests/test_empirical_validator.py`:
- Wilson CI (known value 50/100, edge cases 0/N, N/N, invalid)
- Bootstrap CI (known distribution coverage, WR proportion, empty)
- Monotonicity (strictly increasing, inverted-U, too-few-bins)
- Top-K-drop (stable, unstable with outlier, k too large)
- Bonferroni / BH (filter correctness, BH less restrictive)
- 3D aggregation (basic, missing pnl, empty)
- Sample size planner (real diff, no diff, larger effect needs less N, invalid input)

### Phase 1.5 での使い方 (例)

```python
from tools.empirical_validator import wilson_ci, monotonicity_test

# (entry_type, mtf_state) × WR 集計
cells = aggregate_3d(trades, "category", "mtf_state", "raw_adj_bin")

# TF aligned WR は本当に低いか?
tf_aligned_cells = [c for c in cells if c["category"] == "TF" and c["mtf_state"] == "aligned"]
wr_results = {c["raw_adj_bin"]: c["wilson_low"] for c in tf_aligned_cells}

# bin 順で WR が単調増加するか
mono = monotonicity_test([0,1,2,3], [0.30,0.40,0.55,0.65])
# → 統計的に monotonic な場合のみ apply_policy() で boost を復活させる
```

## 3. Module B: Friction Model v2 (`modules/friction_model_v2.py`)

### データ (friction-analysis.md より構造化)

| Pair | Spread | Slippage | RT Friction | BEV WR |
|---|---|---|---|---|
| USD_JPY | 0.7 | 0.5 | 2.14 | 34.4% |
| EUR_USD | 0.7 | 0.5 | 2.00 | 39.7% |
| GBP_USD | 1.3 | 1.0 | 4.53 | 37.9% |
| EUR_JPY | 1.0 | 0.5 | 2.50 | 33.7% |
| GBP_JPY | 1.5 | 0.8 | 3.50 | 38.0% |

EUR_GBP / XAU_USD は stopped (unsupported=True 返却)。

### Mode multiplier
- DT: 1.0 (baseline)
- Scalp: 1.05 (entry race premium)
- Swing: 0.95 (long hold で実効小)

### Session multiplier (London 1.0 baseline)
- overlap_LN: 0.85
- London: 1.00
- NY: 1.20
- Tokyo: 1.45
- Asia_early: 1.55
- Sydney: 1.60
- default: 1.10

### API

```python
from modules.friction_model_v2 import friction_for, is_scalp_dead

# Asia 中盤の Scalp で USD_JPY
f = friction_for("USD_JPY", mode="Scalp", session="Tokyo", atr_pips=8.0)
# {
#   "rt_friction_pips": 2.14, "adjusted_rt_pips": 3.26, "expected_cost_pips": 3.26,
#   "friction_atr_ratio": 0.408, ...
# }

# ATR 比 30% を超えると Scalp 構造的 DEAD
is_scalp_dead("USD_JPY", atr_pips=5.0)  # True (Scalp 死亡判定)
```

### Tests: 21/21 PASS

`tests/test_friction_model_v2.py`:
- pair format (=X / 大小文字 / `/` 区切り)
- 数値整合 (USD_JPY 0.7+0.5+1.45session = 2.14)
- unsupported (XAU_USD, EUR_GBP)
- mode multiplier (Scalp 1.05× / Swing 0.95×)
- session ordering (overlap < London < NY < Tokyo < Asia_early < Sydney)
- ATR ratio 計算 / DEAD line 判定 (custom threshold)
- integrity check (spread+slippage 整合, BEV WR 範囲)

## 4. Module C: Mechanism Thesis Audit 着手

`wiki/syntheses/strategy-mechanism-audit-2026-04-26.md` で:

### 評価枠組み (3 段階)

- **VALID**: 1-2 行で価格メカニズム説明可、TAP-1/2/3 不含、学術引用 or 因果明示
- **WEAK**: 表面的 thesis、TAP-1 含有、または学術根拠あるが Live と乖離
- **NONE**: thesis なし、indicator combination のみ、TAP-2/3 含有

### 代表 5 戦略の判定 (本セッション)

| 戦略 | カテゴリ | 判定 | Action |
|---|---|---|---|
| ema_pullback | TF | WEAK | 改造案策定 (rejection 2段階) |
| bb_rsi_reversion | MR | WEAK | liquidity sweep ベースに改造案 |
| orb_trap | BR | VALID | shadow N≥30 後 promote 検討 |
| ema_trend_scalp | TF | NONE | shadow 除外候補 |
| engulfing_bb | MR | NONE | shadow 除外候補 |

残り 30 戦略は次セッション (Phase 2 継続) で同枠組み適用。

## 5. Module D: Phase 3 Pre-reg LOCK 2 件

ユーザー指定 TF/Range の第一候補を **HARKing 防止 LOCK** 文書化:

### `pre-reg-pullback-to-liquidity-v1-2026-04-26.md` (TF)

- Mechanism: HTF (H4) trend × M15 swing low/high pullback の流動性供給
- Entry: HTF EMA50/200 alignment + M15 swing touch + rejection (下髭 40%) + volume×1.2
- Validation: N≥200, Wilson lower>50%, PF>1.30, WF 5-fold, Bonferroni α/10, friction v2 cost
- 学術根拠: Time Series Momentum (Moskowitz 2012)

### `pre-reg-asia-range-fade-v1-2026-04-26.md` (MR / Range)

- Mechanism: アジア時間 (02-06 UTC) 低 vol で形成された range の touch + rejection MR
- Entry: range size ≤ 1.5×ATR, bars_in_range ≥ 80%, touch (5pip以内), rejection candle, RSI 30/70
- Validation: N≥200, Wilson lower>50%, PF>1.40, WF 5-fold, Bonferroni α/10, friction v2 Tokyo cost
- 学術根拠: Lo & MacKinlay (1988) 短期 MR

両 pre-reg は Phase 3 セッションで BT 実施、本日付け LOCK 後は閾値変更不可。

## 6. Verification

| Check | 結果 |
|---|---|
| 新規 tests/test_empirical_validator.py | **24/24 PASS** |
| 新規 tests/test_friction_model_v2.py | **21/21 PASS** |
| 既存 + Phase 1 tests (regression) | **316/316 PASS** |
| Total | **361/361 PASS** |
| Pre-commit consistency | ✅ 全チェック通過 |

## 7. Phase 1.7 完了後の状態

### 整備済 (Phase 1.5 / 2 / 3 で使用)

- `tools/empirical_validator.py`: Wilson / Bootstrap / Monotonicity / Top-K-drop / Bonferroni / BH / 3D-aggregate / Sample size
- `modules/friction_model_v2.py`: Pair × Session × Mode friction lookup + Scalp DEAD line
- `wiki/syntheses/strategy-mechanism-audit-2026-04-26.md`: 評価枠組み + 5 戦略判定済
- `wiki/decisions/pre-reg-pullback-to-liquidity-v1-2026-04-26.md`: TF Phase 3 候補 LOCK
- `wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md`: MR Phase 3 候補 LOCK

### 残タスク (次セッション以降)

| Phase | Task | 前提 |
|---|---|---|
| 1.5 Task 3 | MTF gate を category 別で復活 | shadow N≥100 蓄積待ち |
| 1.5 Task 4 | A/B 測定 (Wilson CI + Bonferroni) | Task 3 完了 |
| 1.5 Task 5 | app.py compute_daytrade_signal 統合 | Task 3+4 完了 |
| 1.5 Task 6 | _POLICY data-driven tuning | Module A の monotonicity / aggregate_3d を活用 |
| 1.5 Task 7 | OANDA native H4/D1 を本番経路に統合 | resample 経路と並行検証 |
| 2 (継続) | 残り 30 戦略の thesis audit | Module C 枠組み |
| 3.A | pullback_to_liquidity_v1 BT | Module B friction + Module A validator |
| 3.B | asia_range_fade_v1 BT | 同上 |

## 8. クオンツデヴェロッパー視点の意義

1. **検証の標準化**: Module A により今後の判断は「Wilson + Bonferroni + Top-K-drop」が
   default になる。pooled WR 罠 (`partial_quant_trap`) を構造的に防止
2. **コスト現実化**: Module B により Phase 3 BT は最初から実測 friction を反映、
   楽観バイアスを抑制
3. **HARKing 防止**: Module D の pre-reg LOCK は post-hoc 閾値変更を禁じ、
   `lesson-toxic-anti-patterns-2026-04-25` の TAP-1/2/3 再生産を構造的に阻止
4. **Phase 2 の効率化**: Module C 枠組みで残り 30 戦略の audit が並列可能
5. **Risk 0 実装**: 全 module 新規ファイル、既存 Live trade 経路に影響なし

## 9. References

- Plan: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`
- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換
- [[phase1-task1-2-implementation-2026-04-26]] — Phase 1 Task 1+2
- [[strategy-mechanism-audit-2026-04-26]] — Module C
- [[pre-reg-pullback-to-liquidity-v1-2026-04-26]] — Module D TF
- [[pre-reg-asia-range-fade-v1-2026-04-26]] — Module D MR
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]] — meta-lesson
- [[lesson-toxic-anti-patterns-2026-04-25]] — TAP-1/2/3
- [[friction-analysis]] — Module B 数値ソース
- [[bt-live-divergence]] — Scalp 5.4× 摩擦
- 関連 commit: `51b8cd2` (Phase 0), `72f1583` (Phase 1 Task 1+2)
