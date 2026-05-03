# Complex Gate Edge-Destruction Pattern — 2026-05-03

**Date**: 2026-05-03
**Rule**: R3 (meta-pattern observation across multiple Wave verdicts)
**Status**: VERDICT — Wave 2+ で gate-heavy 戦略は **default Reject** 扱い、simple structure 優先

## Bottom Line

複数 Wave で再現された pattern：**「複雑な gate / regime / filter ロジック」を持つ戦略は BT で映えても Live もしくは OOS で edge を破壊する**。Live で実際に正の edge を維持しているのは **simple session / breakout / pullback structure** のみ。

これは個別 lesson (`feedback_ma_filter_breaks_mr`, `feedback_hmm_gate_same_trap`) の集約ではなく、**roadmap-level な戦略選別ヒューリスティック**として roadmap-v2.1 と Wave 設計に反映する。

## Evidence — 4つの再現

| 戦略 | gate 種別 | BT verdict | Live / OOS | パターン |
|---|---|---|---|---|
| `bb_rsi_reversion` + H1 EMA200 整合 | MA trend filter | BT 維持 | Kelly 0.43 → **0** in Live | `feedback_ma_filter_breaks_mr` |
| S5 HMM regime gate v2 (W2-2r Phase 1) | HMM 状態 gate | BT USDJPY TF +478p | Live edge → -4p、Live で **gate 通過 0件** | `feedback_hmm_gate_same_trap` |
| S1 Tokyo Fix Reversal Wave 1 | Multi-condition session gate | NBER w22820 reproduce 不可 | 月末コホートのみ部分シグナル → **Reject** | gate 過剰でエッジ消失 |
| `mtf_regime_trend_cascade_scalp` USD_JPY 5m (A2 2026-05-03) | MTF (D1×H4×H1) cascade gate | IS PF=1.083 → OOS PF=0.571、max DD **364%** | (Live 未投入) | classic overfit |

**反例 (counter-example) — 機能している simple structure**:

| 戦略 | structure | Live status | EV |
|---|---|---|---|
| `session_time_bias` | UTC hour bucket のみ | ELITE_LIVE | EUR_USD +0.215, GBP_USD +0.113, USD_JPY +0.580 |
| `trendline_sweep` | trendline break | ELITE_LIVE | EUR_USD +0.927, GBP_USD +0.599 |
| `gbp_deep_pullback` | retracement depth | ELITE_LIVE | GBP_USD +1.064 |

**simple structure 共通点**：1〜2 indicator、no regime cascade、no HMM、no MA filter overlay。

## Mechanism (なぜ起きるか)

1. **Multiple testing in disguise**: regime/HMM/MTF cascade gate は本質的に「BT 中に多数の状態 × 多数の条件」を試して有意な subset を選んでいる。BT の見かけ上の edge は overfitting の産物
2. **Walk-Forward で簡単に崩れる**: A2 の OOS PF 0.571 (IS PF 1.083 から半減) はその典型。BT 期間のサブ regime が OOS に再現されない
3. **Live で gate が発火しない**: HMM v2 で「USDJPY 通過 gate 0件」が観測されたように、複雑 gate は Live 環境で意図したバケットに入らず、結果的に Live N=0 でエッジ検証不能
4. **Live で edge を失う**: gate が発火しても、BT 摩擦モデル外の要因（spread 拡大、slippage 非線形性、cohort drift）で edge が消える

## Decision (rule:R3)

### Wave 設計ルール

1. **simple-first 原則**: 新戦略提案時、まず最低限の structure（1〜2 indicator）で BT。複数 gate を重ねる前に simple version の edge を確認
2. **gate 追加は incremental に Bonferroni 補正**: 1 gate 追加で α/2、2 gate で α/4...のように multiple testing コストを明示。最終 LOCK 前に独立 OOS 期間で validation
3. **OOS PF 比較を必須化**: pre-registration thresholds に `OOS PF ≥ IS PF × 0.85` のような stability 制約を追加。半減なら Reject (今回 A2 の 1.083 → 0.571 = -47% は明確 fail)
4. **MTF cascade / HMM / multi-regime gate は default 懐疑**: 提案時 `feedback_hmm_gate_same_trap` を強制参照、code review で gate 必要性の正当化を要求

### 既存戦略の扱い

| 戦略カテゴリ | Action |
|---|---|
| ELITE_LIVE 3戦略 | 維持（Live edge 保有） |
| `mtf_regime_trend_cascade_scalp` | **No registration** (A2 verdict Reject 確定) |
| `mtf_regime_range_cascade_scalp` 他 MTF cascade scalp | A2 と同種のため、個別 BT 抜きに **default Shadow 据え置き** |
| HMM 系新戦略提案 | Wave 3+ で simple-first 原則適用、cohort 別 BT 必須 |
| 既存 PAIR_PROMOTED で複数 gate 含むもの | 次回 cell-level audit で OOS PF 確認 |

### roadmap-v2.1 への反映

- Track E (Scalp 改善) の戦略候補を **simple structure 優先**に再順位付け：
  1. `bb_squeeze_breakout` USD_JPY 5m (BT EV +1.030, simple BB band breakout)
  2. `engulfing_bb` USD_JPY 5m (BT EV +0.677, simple candle pattern)
  3. `fib_reversal` EUR_USD 1m (BT EV +0.426, simple retracement)
  4. `sr_channel_reversal` EUR_USD 5m (BT EV +0.231, simple SR bounce)
  5. ❌ MTF cascade scalp 系は除外
- Track C (HMM 2状態モデル並走) は **default skeptical**、Live cohort 別 N=30 達成までは promotion 議論しない

## Open Questions (Wave 3+ 検討)

- ELITE_LIVE 3戦略でも N が ELITE 認定根拠を満たしていない可能性（aggregate Kelly decomposition で `session_time_bias/GBP_USD` N=5 PnL=-17.6 を確認）→ ELITE 階層自体の閾値を Wilson lower で再評価
- 「simple」の operational 定義（gate 数 ≤ 2? indicator 数 ≤ 3?）を quant で定式化したい
- pure 機械学習戦略（features ≫ rules）は本パターンでどう扱うか — 現状提案は無いが Wave 3+ で出る可能性

## Related

- Roadmap: [[roadmap-v2.1]]
- Lessons:
  - `feedback_ma_filter_breaks_mr`
  - `feedback_hmm_gate_same_trap`
  - `feedback_partial_quant_trap`
  - `feedback_success_until_achieved`
- Decisions:
  - [[aggregate-kelly-decomposition-2026-05-03]] — Live N=29、Wilson CI [31.4%, 65.6%]、surgical demote 不可
  - [[regime-cascade-empirical-redesign-2026-04-30]] — regime cascade 実測再設計（v1 教科書仮説否定）
- BT evidence:
  - `raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.{md,json}` — A2 verdict
  - `wiki/learning/scalp-re-enable-pre-registration-2026-05-03.md` — A2 LOCKED pre-reg

## Why this matters

CLAUDE.md 原則#4「**攻撃は最大の防御 — 防御フィルターの積み上げよりデータ蓄積を優先**」と本パターンは整合的：
- 複雑 gate = 防御フィルターの積み上げ
- 結果 = Live で gate 発火せず、N=0、Aggregate Kelly=0、Gate 1 deadlock
- 解決 = simple structure で N 蓄積を加速

「kel リバランス」「regime gate 追加」「filter 強化」の方向は本日以降 **default 懐疑**。次の Scalp 候補は本決定に従い simple structure から開始する。
