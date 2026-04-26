# Pre-registration: Phase 4e — 15m HTF Neutrality Gate for BREAKOUT Scalp (2026-04-26)

**Locked**: 2026-04-26 (本 doc 確定後変更禁止)
**Rule classification**: R1 (Slow & Strict, 新フィルタ)
**Upstream**:
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (mtf_h4_label NEUTRAL × BREAKOUT dWR +20.5%/+18.9%)
- [[phase4d-v6-cell-edge-test-result-2026-04-24]] (live 16d power denial, BREAKOUT 戦略 N=86/93)
- [[phase5-secondary-2y-2026-04-26]] (5m Pure Edge structural failure)
- [[manifests/SPEC]] (EDGE.md routing infrastructure)

## 0. Rationale

Phase 4c Signal C で **mtf_h4_label NEUTRAL** が BREAKOUT 系戦略の WR を **+18.9–20.5%** 押し上げる effect を検出 (4 CANDIDATE cells, Bonferroni gap 50x で未通過). H4 は scalp に対し **48x scale** で entry latency 過大. 本 phase は同 effect の **15m scale (3x)** への転写可能性を検定する.

**Why 15m, not H4**:
- 5m vs 15m = 3x ratio → MTF rule-of-thumb 3-6x window 内 (Carter/Elder)
- σ_15m ≈ √3·σ_5m → noise scaling 緩, information loss 小
- 1 日 ~96 bar で scalp と同 grain → label 切替頻度整合
- Andersen-Bollerslev-Diebold-Labys (2001) 5-30 min realized vol sampling 帯域内
- H4 1500 bar/年 vs 15m 35,000 bar/年 → N efficiency 23x

**Why BREAKOUT-only**:
- Signal C で TREND 戦略は全 field null. 高 TF regime は redundant feature
- BREAKOUT 戦略は **早期 entry** が edge source、HTF NEUTRAL 中こそ "pre-trend" 段階を捕える理論的根拠あり
- Hypothesis space を広げると Bonferroni denominator 増 → power 喰い

## 1. Scope (LOCKED)

### Strategies (LOCKED)
本検定対象は **Live N≥50 を満たす BREAKOUT 戦略 2 種** のみ:
1. `bb_squeeze_breakout` (BREAKOUT, 5m/15m hybrid, post-cut N=41 EV=+1.55)
2. `vol_surge_detector` (BREAKOUT, 5m, Phase 4d N=93)

**除外** (LOCKED):
- TREND/RANGE 戦略 (Signal C で null 確認, 仮説範囲外)
- Phase 5 S5/S7/S9 SURVIVOR 兆候 (未実装 entry_type, Live N=0)

### Pairs (LOCKED)
- USD_JPY, EUR_USD (v6 classifier stability 確認済)

### Data (LOCKED)
- BT: OANDA 365 days × 2 pairs × 5m bars (entry signal 用)
- HTF label 計算: OANDA 365 days × 2 pairs × **15m bars**
- BT entry 関数は本番 signal 関数 (`backtest_mode=True`) を使用 (BT/Live 統一)

## 2. 15m HTF label definition (LOCKED)

```
ema20_15m = EMA(Close_15m, 20)
slope_15m = (ema20_15m[t] - ema20_15m[t-5]) / 5     # 5 bar slope
sigma_slope_15m = rolling_std(slope_15m, 100)        # 100-bar normalization
slope_z = slope_15m / sigma_slope_15m

if slope_z > +0.5:    htf_15m_label = "TREND_UP"
elif slope_z < -0.5:  htf_15m_label = "TREND_DOWN"
else:                  htf_15m_label = "NEUTRAL"
```

**LOCKED 詳細**:
- EMA period: **20**
- Slope lookback: **5 bars** (= 75 min)
- σ window: **100 bars** (= 25 hours, ≈ 1 trading day)
- Threshold: **±0.5** (Phase 4c Signal A と同値)
- 5m bar at time t inherits htf_15m_label from the 15m bar containing t

**ハードコード理由**: Phase 4c Signal A で同 parameter (period=20, k=5, σ window=100, threshold=0.5) を使用. 同一定義で scale (60m → 15m) のみ変更し、parameter tuning による HARKing 排除.

## 3. Cell axis (LOCKED)

**Test cell**: `(strategy, htf_15m_label)` の 2D cell
- Strategies: 2
- htf_15m_label: 3 (TREND_UP / NEUTRAL / TREND_DOWN)
- M = **2 × 3 = 6** combos

**Pair-pooled** (USDJPY + EURUSD aggregated). Pair-別内訳は **info-only**, 検定対象外.

## 4. Statistical tests (LOCKED)

各 (strategy, htf_15m_label) について BT 365d trades から:
- **N**: trade 数
- **WR**: Win rate (TP-hit / N)
- **WR_base**: 当該戦略の **HTF 全 label 平均** WR
- **dWR**: WR − WR_base
- **Wilson 95% CI**: 下限・上限
- **Cohen's h**: arcsine effect size (h = 2(arcsin√WR − arcsin√WR_base))
- **Fisher exact 2-tail p**: WR vs WR_base
- **Kelly fraction**: f* = max(0, (p − q/b)/b), b = avg_win/avg_loss
- **WF 2-bucket**: BT 期間前半/後半 split, 両方で h>0 (positive) or h<0 (negative)

### Bonferroni correction
```
M = 2 strategies × 3 labels = 6
α_family = 0.05
α_cell = 0.05 / 6 = 8.33e-3
```

### N_MIN (LOCKED)
- N_MIN_CELL = **30** (cell-level testability)
- N_MIN_STRATEGY = **300** (strategy-level reliability, BT 365d で達成想定)

## 5. Authorization rules (LOCKED)

### SURVIVOR (positive edge authorize)
- N ≥ 30
- dWR ≥ +0.05 (5pp)
- Cohen's h ≥ +0.20
- Fisher p < α_cell (8.33e-3)
- Kelly > 0.05
- WF same-sign positive

### CANDIDATE (provisional, BT-only)
- N ≥ 30
- dWR ≥ +0.05
- Cohen's h ≥ +0.10
- Fisher p < 0.05 (uncorrected)
- WF same-sign positive

### REJECT (negative edge, EDGE.md BLOCK 候補)
- N ≥ 30
- dWR ≤ -0.05
- Cohen's h ≤ -0.20
- Fisher p < α_cell
- Kelly < -0.05
- WF same-sign negative

### INSUFFICIENT
- N < 30 OR conflicting criteria

## 6. Scenario declarations (LOCKED)

- **Scenario A** (null): SURVIVOR=0 AND CANDIDATE<2 → 仮説 falsified, 本 phase closure (ただし MTF approach 全体 closure ではない)
- **Scenario B** (limited): SURVIVOR=1 OR CANDIDATE≥2 → EDGE.md に CANDIDATE 登録 (routing=NONE で情報のみ), Live observation 60-90 days
- **Scenario C** (full): SURVIVOR≥2 → EDGE.md に SURVIVOR 登録 (routing=KELLY_HALF), Live monitoring + monthly re-check

REJECT は scenario 判定に影響しない (negative-knowledge として保持).

## 7. Pre-registered hypotheses

**H1 (primary, moderate)**: `(bb_squeeze_breakout, NEUTRAL)` で dWR ≥ +10pp, h ≥ +0.20.
H4 で +20.5% の effect が 15m で 50-100% 維持されると仮定 (RV scaling 数学から effect は scale-invariant に近い).

**H2 (primary, moderate)**: `(vol_surge_detector, NEUTRAL)` で dWR ≥ +8pp, h ≥ +0.16.
H4 +18.9% を 80% 維持と仮定.

**H3 (secondary, weak)**: BREAKOUT × TREND_UP/DOWN は negative direction (dWR ≤ −0.03).
理由: HTF trend 確定後の breakout は late entry, 摩擦負け予想.

**H4 (null)**: NEUTRAL 滞在率 < 30%. NEUTRAL cell の N が 30 未満.
理由: ±0.5σ threshold は中央 ~38% (正規分布近似) 想定だが 15m slope は fat-tail で NEUTRAL 域が狭い可能性.

**H5 (overall null)**: Scenario A.
理由: Phase 4d で live 16d INSUFFICIENT 95%, BT でも N 効率改善はあるが Bonferroni 通過は H1/H2 共に hard.

## 8. Disallowed (post-hoc 禁止)

- HTF label parameter 調整 (EMA period 20, slope lookback 5, σ window 100, threshold 0.5 LOCKED)
- 戦略追加 (本 phase は BREAKOUT 2 戦略限定)
- M denominator reduction (cells 削除して α 緩和禁止)
- N_MIN 切下
- pair-別検定への分割 (pair-pooled LOCKED)
- BT 期間 365d 短縮
- WF bucket 数変更 (現: 2)

## 9. Execution

1. `/tmp/phase4e_htf15m_neutrality_gate.py` 作成
2. **Step A** (descriptive, pre-reg 違反なし): 15m label distribution check
   - USD_JPY/EUR_USD 各 365d で htf_15m_label の {TREND_UP, NEUTRAL, TREND_DOWN} 滞在率
   - 滞在率 < 20% なら H4 trigger, BT は実行するが N 不足 likely と認知
3. **Step B**: BT 365d × 2 strategies × 2 pairs を実行 (本番 signal 関数で trade_log 生成)
4. **Step C**: trade_log を 15m label で bucketing, per-cell metrics 計算, Bonferroni 判定
5. 結果を [[phase4e-htf15m-neutrality-gate-result-2026-04-26]] に記録
6. Scenario B/C なら EDGE.md に該当 edge 追加 + 別 commit

## 10. Out of scope (本 phase で扱わない)

- 5m + 15m + H4 multi-layer composite
- 15m squeeze synergy (#2 候補, 別 phase)
- 15m range pivot S/R for fib_reversal (#3 候補, fib_reversal 削除判断後)
- Dynamic TF switching (#4 候補, Phase 7+)
- Routing mechanism (本 phase は edge detection のみ. EDGE.md routing=NONE で記録)

## 11. References

- [[phase4c-signalC-field-ranking-result-2026-04-26]]
- [[phase4d-v6-cell-edge-test-result-2026-04-24]]
- [[phase4c-mtf-regime-result-2026-04-24]] (Track B closure, 失敗事例)
- [[manifests/SPEC]] (EDGE.md routing infrastructure)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule R1 適用根拠)
- [[feedback_success_until_achieved]] (closure 短絡禁止 memory)
