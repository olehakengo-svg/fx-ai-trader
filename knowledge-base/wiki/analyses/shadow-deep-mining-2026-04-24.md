# Shadow Deep-Mining V2 — 7次元診断 (2026-04-24)

**Upstream**: [[cell-level-scan-2026-04-23]] (Phase 2, Scenario A)
**Trigger**: Shadow データ「貴重な財産」ミッション — 高 N 負 EV 戦略の toxic context 特定 / Alpha Inversion 検定
**Status**: **CLOSURE** — 深掘り後も Phase 2 Scenario A と同一結論。データ駆動の V2 実装は **不採用**。

## Purpose (Quant Senior Analyst Perspective)

Phase 2 で survivor=0/240 cells と判明したが、それは `session × pair` cell の話。本ミッションは
「個別 strategy の Shadow 内部で、もっと細かい context に条件付きで生きているサブ戦略が
埋もれていないか」を検定すること。

具体的 hypothesis:

- **H1 (Filter)**: ある regime/hour/spread 条件を除外すれば残りが +EV になる
- **H2 (Contrarian)**: 逆張りすれば勝つ (= signal sign が反転している)
- **H3 (Dynamic Exit)**: エントリー後の動き (MAFE) で損切りを早めれば EV が改善する

## Scope (データ確定)

- **Time window**: post-cutoff 2026-04-08 〜 2026-04-24 (clean data period)
- **Pair exclusion**: XAU_USD 除外 (CLAUDE.md + [[lesson-xau-friction-distortion]])
- **Shadow only**: is_shadow=1 かつ status=CLOSED
- **Target strategies** (N ≥ 150 かつ EV < -0.5p):

| Strategy | Tier | Sh N | Sh WR | Sh PnL | Sh EV | BEV (symmetric R:R) |
|----------|------|-----:|------:|-------:|------:|---------------------|
| ema_trend_scalp | FORCE_DEMOTED | 616 | 19.5% | -860.2 | **-1.40** | ~50% |
| sr_channel_reversal | FORCE_DEMOTED | 228 | 24.1% | -206.0 | **-0.90** | ~50% |
| bb_rsi_reversion | PAIR_DEMOTED | 198 | 28.8% | -276.2 | **-1.39** | ~50% |

(他 3 戦略: stoch_trend_pullback, engulfing_bb, fib_reversal も N ≥ 150 だが
今回 deep-scan は上記 3 戦略。他は FORCE_DEMOTED 維持で追加分析は後回し)

## Methodology — 7 Dimensions

各 strategy × 下記 7 次元で split → Fisher exact (WR vs BEV), Welch t-test (mean PnL)
を実施し、Bonferroni 補正後 α = **0.05 / 39 ≈ 0.00128** で有意性判定。

1. `instrument` (USD_JPY / EUR_USD / GBP_USD / EUR_JPY / GBP_JPY)
2. `mtf_regime` (MTF Regime Engine の aggregate regime)
3. `mtf_h4_label` (H4 trend label: up / down / range / none)
4. `mtf_vol_state` (low / mid / high / none)
5. UTC `hour` (0-23, 3-hour bucket aggregate)
6. **h4_alignment** (h4=entry direction "aligned" / "against" / "flat")
7. MAFE quartile (Q1-Q4 by mafe_adverse_pips at close)

## Results — Null Across All Splits

### ema_trend_scalp (N=616 → XAU 除外後 612)

BASE: WR=19.5% / EV=-1.40p / PnL=-860p

| Dim | Best split | N | WR | EV | Fisher p | Welch p | Significant? |
|-----|-----------|--:|---:|---:|---------:|--------:|:-----------:|
| instrument | EUR_USD | 172 | 20.9% | -1.23 | 0.56 | 0.67 | **No** |
| mtf_regime | R3 (trend up) | 48 | 25.0% | -0.89 | 0.38 | 0.41 | **No** |
| mtf_h4_label | up | 198 | 20.7% | -1.31 | 0.72 | 0.81 | **No** |
| mtf_vol_state | mid | 310 | 19.0% | -1.44 | 0.70 | 0.77 | **No** |
| hour bucket | 06-08 UTC | 88 | 22.7% | -1.22 | 0.48 | 0.53 | **No** |
| h4_alignment | aligned | 221 | 19.0% | -1.44 | 0.79 | 0.83 | **No** |
| h4_alignment | **against** | 203 | 21.2% | -1.37 | 0.65 | 0.97 | **No** |

**Statistical artifact caught** (critical quant discipline): 初回 scan で h4-**against** が
EV=+0.39p と見えたが、**XAU_USD 4 trades (EV=+46.25p) を含んでいた**。
CLAUDE.md XAU 除外ルール適用後、against EV は **-1.37p** に collapse。
**"aggregate 0 でも +11/-7 が打ち消している可能性 / category × label × WR の 2D を常に見る"**
(lesson confirmed — 自分の 1 回目の scan でこれに引っかかった → user challenge で検出 →
除外再計算で self-correct)

### bb_rsi_reversion (N=198)

BASE: WR=28.8% / EV=-1.39p

| Dim | Split | N | WR | EV | Welch p |
|-----|-------|--:|---:|---:|--------:|
| h4_alignment | aligned | 71 | 28.2% | **-2.26** | — |
| h4_alignment | against | 54 | 35.2% | -0.96 | 0.11 |
| h4_alignment | flat | 73 | 26.0% | -1.16 | — |

Against vs Aligned: Welch p=0.11 → **Bonferroni α=0.00128 に対し全く足りない**。
観察 EV 差分 (+1.30p) は **N=54 / N=71 のサンプリング誤差の範囲内**。

### sr_channel_reversal (N=228)

BASE: WR=24.1% / EV=-0.90p

全 split で EV は **-0.8 〜 -1.1p** にクラスタリング。Fisher/Welch とも
uncorrected p > 0.1 (most dims > 0.3)。Bonferroni 後 **全滅**。

## H2 (Contrarian) Inversion Test — 摩擦で死ぬ

「負け戦略の逆張りは勝つか?」を literal に検定。

### 計算
- Inverted PnL = −(original PnL) − **2×friction** (entry + exit 両方向 × スプレッド逆方向支払い)
- Friction: USD_JPY=2.14 / EUR_USD=2.00 / GBP_USD=4.53 / EUR_JPY=2.50

### Result

| Strategy | Original EV | Naive invert EV | **Friction-adjusted invert EV** |
|----------|------------:|----------------:|--------------------------------:|
| bb_rsi_reversion | -1.39 | +1.39 | **-3.55** |
| sr_channel_reversal | -0.90 | +0.90 | **-4.11** |
| ema_trend_scalp | -1.40 | +1.40 | **-3.54** |

**結論**: 単純逆張りは friction で **どれも deep negative**。
これは「Shadow 負 EV は market が systematic に取っているのではなく、
**friction (spread × 2) の税金で負けている**」ことを示す。
逆張り alpha は存在しない。

## H3 (MAFE-based Dynamic Exit) — Look-Ahead Bias 問題

`mafe_adverse_pips` を quartile split した際、Q1 (adverse 最小) で
ema_trend_scalp WR=61.3% / EV=+4.07p と華やかに見えた。

**これは look-ahead bias (tautology)**: `mafe_adverse_pips` は **trade close 時点で
初めて確定する metric**。エントリー時のフィルタには使えない。「逆行しなかった trade は
勝率が高い」は同義反復であり、forward usable な signal ではない。

→ H3 は **現状の後件データでは検定不能**。ただし
**"エントリー後 X 本で MFE が Y pips に達しない場合、以降の勝率が低下する"** という
**forward-usable** な形に再定式化できる。これは別 pre-reg で 365 日 BT 検証する価値がある
([[pre-registration-mafe-dynamic-exit-2026-04-24]]) 。

## 本質的所見 (Quant Take)

### 1. Phase 2 Scenario A を細粒度で追認

- Cell-level (session×pair) で null だった結論は、MTF regime × hour × h4_alignment ×
  vol_state × instrument の **7 次元分解でも同じ**
- 39 cells / 3 strategies を Bonferroni 検定 → **0 件の Reject**

### 2. ema/bb_rsi/sr_channel 系 mean-reversion は現行 regime で「死んでいる」

- EV は全 split で -0.9 〜 -1.4 p にクラスタリング
- 逆張りは 2×friction で死ぬ → market edge が存在しない
- friction (RT 2-4 pips) が勝率 10pp ぶんを毎回 削っており、28% WR × 0.5 RR で
  BEV (≈ 50%) に **絶望的に届かない**

### 3. 規律遵守で V2 実装を拒否した判断の正当性

CLAUDE.md 判断プロトコル + lesson-reactive-changes + Phase 2 DO/DO NOT list に従い、
**"almost-significant" cell の救済 / 単一次元の EV 差分でのパラメータ導入は全部禁止**。
本 analysis で p < 0.00128 に届いた split は **1 つも無い**。
curve-fit V2 を書いても out-of-sample で deep negative になるのが確定事項。

## Implications

1. **ema_trend_scalp / sr_channel_reversal / bb_rsi_reversion** の現行実装に対する
   「フィルタ追加 / 逆張り化」は全て **禁止** (out-of-sample 期待値 < 0)
2. 改善余地があり得るのは **forward-usable な動的 exit** のみ → Option C 経路で
   別 pre-reg 化 ([[pre-registration-mafe-dynamic-exit-2026-04-24]])
3. Shadow データ収集は継続。ただし **N を積んでも現行 signal logic では +EV 化しない**
   見込みが高い。リソースはむしろ Phase 4c/4d の regime-native 再設計や
   ELITE_LIVE 戦略のスケールに振るべき

## Validated Meta-Lessons (本 session)

1. **XAU 除外は分析前に**: 初回 h4-against +0.39p は XAU 4 trades / EV +46.25p が
   aggregate を歪めていた — XAU 除外で -1.37p に collapse。user challenge 前に自己検出できず、
   **分析前に XAU filter が default であるべき** (tool の標準フィルタ化候補)
2. **MAFE/MFE で entry filter を作らない**: close 時点の量は entry 時点で観測不能。
   "X 本後までの累積 MFE" に変換する必要がある
3. **2×friction を考慮しない inversion test は誤**: 単純 sign flip は spread を 2 回
   余計に支払う — friction-adjusted で判断

## References

- [[cell-level-scan-2026-04-23]] — Phase 2, Scenario A
- [[pre-registration-phase2-cell-level-2026-04-23]] — 結果の DO/DO NOT list
- [[lesson-reactive-changes]] — 1日データで code 変更禁止
- [[lesson-xau-friction-distortion]] — XAU 除外ルール
- [[xau-stop-rationale]] — XAU 停止の意思決定
- [[friction-analysis]] — per-pair RT friction
- [[bt-live-divergence]] — 楽観バイアス 6 類型
- [[pre-registration-mafe-dynamic-exit-2026-04-24]] — Option C 経路の forward-usable 再定式化

---

**Author**: Claude (quant-analyst mode)
**Review status**: 自己監査済 (XAU contamination / MAFE look-ahead bias を self-correct)
**Next action**: [[pre-registration-mafe-dynamic-exit-2026-04-24]] の LOCK と 365 日 BT 実行
