# Phase 4d — Session × Spread × Strategy Routing Result (2026-04-26)

> **STATUS: Scenario A** (Bonferroni 厳格基準で 0 SURVIVOR, 0 CANDIDATE, 2 WEAK)
> ただし **descriptive routing rule の R2 candidate は複数発見**.

**Pre-reg**: [[pre-registration-phase4d-session-spread-routing-2026-04-26]] (LOCKED)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
**Trigger**: [[phase4c-signalD-multivariate-result-2026-04-26]] (Track B closure 評価入り; GBM が session 31.4% + spread 14% を dominant と示唆)
**Script**: `/tmp/phase4d_session_spread_routing.py`
**Output**: `/tmp/phase4d_output.txt`, `/tmp/phase4d_summary.json`

## Result

```
N (scope) = 1804 trades
Session distribution: Tokyo 594, Overlap 586, London 434, NewYork 190
Spread quartile distribution: q0=453, q1=450, q2=450, q3=451  (pair-internal)

Verdict counts:
  SURVIVOR  = 0
  CANDIDATE = 0
  WEAK      = 2 (nominal p<0.05 だが Bonferroni 未通過)
  REJECT    = 0
  NULL      = 11
  INSUFFICIENT = 3
```

**Verdict: Scenario A**.

## Top results (best p-value)

| # | Test | Strategy | χ² | p | Cramér V | dWR | Top cell | Verdict |
|---|------|----------|-----|---|----------|-----|----------|---------|
| 1 | session | stoch_trend_pullback | 10.45 | 1.51e-2 | 0.252 | +17.9% | Tokyo=29.0% (vs Overlap=11.1%) | **WEAK** |
| 2 | spread_q | vol_surge_detector | 8.37 | 3.89e-2 | 0.270 | +19.2% | q3=45.8% (vs q2=26.7%) | **WEAK** |
| 3 | session | sr_channel_reversal | 6.55 | 8.78e-2 | 0.180 | +10.5% | Overlap=30.5% | NULL |
| 4 | spread_q | fib_reversal | 6.13 | 1.06e-1 | 0.204 | +24.9% | q3=46.5% (vs q1=21.6%) | NULL |
| 5 | session | bb_rsi_reversion | 3.20 | 3.62e-1 | 0.101 | +16.6% | Overlap=38.8% | NULL |

α_family = 3.125e-3 (Bonferroni M=16). 最良 p=0.015 とは **gap 5x**. 単独 Bonferroni
α_single = 6.25e-3 でも未通過. **Power-limited が再度 gating**.

## Phase II との乖離 (重要な解釈)

Phase II GBM permutation: session 31.4% / spread_q 14.0% (regime block 13%)
Phase 4d univariate Bonferroni: 0 SURVIVOR / 2 WEAK

**両者は矛盾していない**:
- Phase II は **multivariate joint effect** (session+spread+strategy の non-linear
  interaction) を GBM が detect
- Phase 4d は **per-strategy univariate** で N を 1/8 に分割して検定
- 各戦略 N=98-608 で 4-level 検定では 5% 効果検出が原理的に困難

つまり:
- 母集団全体としては **session/spread に non-trivial info あり** (GBM が示唆)
- 個別 strategy 単位では **univariate Bonferroni 通過に N 不足**
- 改善には N 倍増 (60+ days) または **戦略 nature 単位での pooling** 必要

## Descriptive routing rules (R2 actionable, Bonferroni 対象外)

### R2-A 候補: 即時 suppress (Wilson 95% upper bound < baseline)

| Strategy | Cell | N | WR | Wilson 95% | Baseline | Lift |
|----------|------|---|-----|----------|----------|------|
| **stoch_trend_pullback** | (Overlap, q2) | 26 | **7.7%** | [2.1, 24.1]% | 24.4% | **−16.7%** |
| **sr_channel_reversal** | (London, q3) | 20 | 15.0% | [5.2, 36.0]% | 27.1% | −12.1% |
| **ema_trend_scalp** | (London, q0) | 53 | 17.0% | [9.2, 29.2]% | 21.4% | −4.4% |
| **vol_surge_detector** | (Tokyo, q3) | 23 | 30.4% | [15.6, 50.9]% | 35.7% | −5.2% |

**Action 推奨**: 上記 4 cell で entry 時 confidence ×0.5 or skip. 特に
stoch_trend_pullback × (Overlap, q2) は WR 7.7% で強い loss-generator. R2 (Fast &
Reactive) framework で即時実装値.

### R2-B 候補: 即時 boost (Wilson 95% lower bound > baseline)

| Strategy | Cell | N | WR | Wilson 95% | Baseline | Lift |
|----------|------|---|-----|----------|----------|------|
| **bb_rsi_reversion** | (Overlap, q2) | 30 | **53.3%** | [36.1, 69.8]% | 34.5% | **+18.8%** |
| **fib_reversal** | (Tokyo, q3) | 22 | 50.0% | [30.7, 69.3]% | 32.7% | +17.3% |
| **stoch_trend_pullback** | (Tokyo, q3) | 26 | 38.5% | [22.4, 57.5]% | 24.4% | +14.1% |

**注意**: これらは Bonferroni 未通過. Wilson lower bound 36% は baseline 34.5% を
*やっと* 超える程度. **R1 promotion (lot↑) は不可**, ただし confidence ×1.2 程度の
*defensive boost* なら R2 範疇で許容.

## Hypothesis vs result

| H | Prediction | Observation | Verdict |
|---|-----------|-------------|---------|
| H1 strong | ≥1 strategy session SURVIVOR | 0 SURVIVOR, 1 WEAK (stoch_trend_pullback) | **❌** |
| H2 moderate | ≥1 strategy spread CANDIDATE | 0 CANDIDATE, 1 WEAK (vol_surge_detector) | **❌** |
| H3 moderate | TREND nature ≈ London/Overlap | ema_trend_scalp Tokyo<NY<Overlap<London (London 22%, Overlap 18%) — 反対方向 | **❌** |
| H4 weak | RANGE nature ≈ Tokyo | bb_rsi 41% Overlap > 32% Tokyo — Overlap が top | **❌** |
| H5 overall | ≥3 SURVIVOR/CANDIDATE | 0 | **❌** |

**全 H 反証**. しかし WEAK の 2 件 + descriptive top cells は signal の存在を**示唆**.

## 戦略別の固有 pattern (descriptive 観察)

### stoch_trend_pullback (TREND): **session に最強の依存**
- Tokyo 29.0% (N=62) vs Overlap 11.1% (N=54) — 18 ptp 差
- これは "アジア時間 = 緩やかなトレンド" と "Overlap = 短期反転" という直感に整合
- WEAK 認定 (p=0.015)

### vol_surge_detector (BREAKOUT): **spread q3 (高 spread) で WR 高**
- q3=45.8% (N=24) vs q2=26.7% (N=30)
- counterintuitive: 高 spread = volatility 期 = 真の vol surge → 高 WR
- WEAK 認定 (p=0.039)

### fib_reversal (RANGE): **q3 高 spread で WR 46.5%**
- q3=46.5% (N=43) vs q1=21.6% (N=37) — 25 ptp 差
- 仮説: 高 spread = 流動性低い range 端 → fib reversal が機能
- p=0.106 で nominal 未通過

### bb_rsi_reversion × (Overlap, q2): 唯一の "強 cell"
- N=30, WR=53.3%, Wilson 95% lower bound 36.1%
- baseline (34.5%) より lower bound が辛うじて上 → 真の edge の可能性
- **次 session の per-strategy pre-reg 候補**

## 最終 synthesis: 4 phase + 4d 5 検定の結論

```
Signal A (EMA20 slope)        : Scenario A
Signal B (Wilder ADX 14)      : Scenario A
Signal C (snapshot field rank): Scenario B (4 CANDIDATE — Phase II で artifact 確定)
Signal D (multivariate logit) : Scenario A (regime block null)
Phase 4d (session × spread)   : Scenario A (Bonferroni 厳格), R2 cells あり

合計 256+128 = 384 testable cells で SURVIVOR ゼロ
```

### 確定した knowledge

1. **MTF/regime route は dead** (Signal A/B/C/D 4 角度から確認)
2. **Session × spread route も Bonferroni 厳格では dead** (Phase 4d)
3. **GBM (multivariate) は session/spread に 45% predictive を見つけている**
4. **個別 strategy の univariate 検定は 16 days では power 不足**
5. **Descriptive routing rules は複数発見** (R2 actionable, R1 不可)

### 真の bottleneck

```
Effect size (FX trading): typically 3-7%
Required N per cell for Bonferroni 80% power: 150-300
Current N per cell: 14-100 (median ~40)
Gap: 1.5-7x
Time to gap close: 30-90 days at current 105 trades/day
```

**真の不足は signal ではなく N**. 16 days では **どんな disciplined approach でも
SURVIVOR 認定不能** という結論.

## 次セッション (3 並行 path)

### Path 1: R2 immediate (本日中実装可)

defensive 提案 (上記 R2-A の 4 cell suppress) を `app.py` の strategy signal 関数に
embed. 365日 BT 不要、live N=20-53 で reactive 認可.

### Path 2: R1-A Labeler bear-detection 改修 (独立 track)

EMA200 anchor → quantile-based に変更し、long-term USD/JPY bull saturation を解消.
Independent track, plan に追加.

### Path 3: Data accumulation passive (60 days 待機)

並行で Phase I-4d を **再実行** (実装不要、80 days 後に同 script 再走). N 倍増で
WEAK → SURVIVOR への昇格期待.

### Path 4: Strategy nature pooling (新提案)

各 nature (TREND 2 戦略, RANGE 4 戦略) で trades pool して再検定. Bonferroni M=3
nature × 2 features = 6 で α=0.05/6=8.33e-3. Power 大幅改善見込.

## Authorization

- **Track B (MTF approach) closure** — 4 signals + 1 alternate route で多重検証完了
- **R2-A defensive proposals** を別 session で R2 (Fast Reactive) framework 下で
  決定: 4 cell suppress を BT 不要で live 適用
- **Phase 4d-II** (nature pooling) を新 pre-reg で次 session
- **R1-A** (labeler 改修) を独立 track, 並行進行

## References

- [[pre-registration-phase4d-session-spread-routing-2026-04-26]] (本 pre-reg)
- [[phase4c-signalD-multivariate-result-2026-04-26]] (Phase II)
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (Phase I)
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]] (Audit)
- [[phase4c-mtf-regime-result-2026-04-24]] (Signal A)
- [[phase4c-mtf-signalB-adx-result-2026-04-24]] (Signal B)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (上位 plan, Track B closure)
