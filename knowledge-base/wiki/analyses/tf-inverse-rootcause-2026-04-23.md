# TF Inverse Calibration Root Cause (Beyond VWAP)

**Date**: 2026-04-23
**Trigger**: A2 baseline で TF Delta WR **-9.0pp** vs MR -2.8pp。VWAP 修正だけでは説明不可。
**Scope**: TF 戦略群 (N=568, shadow post-cutoff) を他の signal component で decompose
**Script**: `/tmp/tf_inverse_rootcause.py`

## 核心発見: **複数の signal enhancer が逆校正している**

### Reasons-tag 含有フラグ別 WR (TF only, N=568)

| フラグ | has N | has WR | no N | no WR | **Delta** | 判定 |
|---|---|---|---|---|---|---|
| **方向一致** | 464 | 19.4% | 104 | 35.6% | **-16.2pp** | 🚨 最大の逆校正 |
| **機関フロー** | 161 | 14.9% | 407 | 25.3% | **-10.4pp** | 🚨 強い逆校正 |
| **HVN** | 338 | 19.8% | 230 | 26.1% | **-6.3pp** | 🚨 逆校正 |
| VWAP下位 | 214 | 19.2% | 354 | 24.3% | -5.1pp | 既修正 (b37ee8b) |
| HTF逆行 | 123 | 21.1% | 445 | 22.7% | -1.6pp | ほぼ中立 |
| VWAP上位 | 207 | 21.7% | 361 | 22.7% | -1.0pp | 既修正 |
| LVN | 57 | 24.6% | 511 | 22.1% | +2.4pp | 正方向 (弱) |
| 方向不一致 | 177 | 25.4% | 391 | 21.0% | +4.5pp | **正方向** |
| **RR不足** | 39 | 33.3% | 529 | 21.6% | **+11.8pp** | 正方向 (強) |

### MTF alignment

| Label | N | WR | EV_cost |
|---|---|---|---|
| **aligned** | **30** | **10.0%** 🚨 | -3.59p |
| conflict | 282 | 20.2% | -1.98p |
| unknown | 18 | 33.3% | -1.27p |
| (blank) | 238 | 25.6% | -1.90p |

MTF **aligned ラベル = WR 10%** という壊滅的な逆校正。gate_group `mtf_gated` (N=171, WR 22.2%) と `label_only` (N=159, WR 17.6%) でも mtf gate 通過が本来無効〜有害。

### Vol state (TF内)

| state | N | WR | EV_cost |
|---|---|---|---|
| expansion | 215 | 18.6% | -2.80p |
| squeeze | 283 | 24.0% | -1.51p |
| normal | 70 | 27.1% | -1.58p |

TF 戦略は本来 **expansion (ブレイクアウト)** で機能するはずが、squeeze のほうが WR 高い → TF 設計自体が逆か、または expansion ラベル定義が誤っている。

### Session × TF

| Session | N | WR | EV_cost |
|---|---|---|---|
| Tokyo | 79 | **12.7%** 🚨 | -3.34p |
| NY | 83 | 16.9% | -2.79p |
| London | 173 | 24.3% | -1.45p |
| Overlap | 231 | 26.4% | -1.64p |

Tokyo × TF は使用禁止レベル。London/Overlap は許容。

### Instrument × TF

| Pair | N | WR | EV_cost |
|---|---|---|---|
| GBP_USD | 98 | **13.3%** 🚨 | -3.57p |
| USD_JPY | 283 | 24.0% | -1.51p |
| EUR_USD | 177 | 24.9% | -1.76p |

GBP_USD × TF は即撤退候補。

### Entry type × confidence zone

| Entry × Zone | N | WR | EV_cost |
|---|---|---|---|
| **ema_trend_scalp: high-conf** | **163** | **14.7%** 🚨 | -3.07p |
| ema_trend_scalp: mid-conf | 242 | 21.5% | -2.04p |
| ema_trend_scalp: low-conf | 80 | 26.2% | -1.57p |
| **trend_rebound: low-conf** | 19 | **36.8%** ⭐ | +0.48p |

`ema_trend_scalp` は high-conf で最悪、low-conf で最良という完全逆転。戦略内の confidence 計算が壊れている。

## クオンツ結論

VWAP は氷山の一角。MassiveSignalEnhancer + MTF gate 全体が **TF-biased labels を "aligned/positive" と誤認**して加点する構造欠陥を持つ。全体の分布:

- TF で 5 フラグ以上が逆校正
- 「方向一致」(Δ-16.2pp) が最強の負の寄与 — **同系統のラベル集合**(VWAP 方向一致、機関フロー方向、HVN bias、MTF aligned)が全て同じ向きに誤動作

## 推奨アクション (優先順)

### 即時 (Phase 2 加速)

| # | アクション | 期待 EV |
|---|---|---|
| 1 | MTF alignment `aligned` ラベルの conf 加点を中立化 | +3-5p/TF trade |
| 2 | 「機関フロー」系 signal の conf_adj を中立化 | +2-4p/TF trade |
| 3 | HVN-bias の conf_adj を中立化 | +1-2p/TF trade |
| 4 | `ema_trend_scalp` 戦略は高 conf 帯のみ **逆手 (符号反転)** で再運用 or 撤退検討 | 大 |

### 中期

| # | アクション | 根拠 |
|---|---|---|
| 5 | 戦略カテゴリ別 conf_adj を `modules/strategy_category.py` 経由で再構成 | VWAP + 他フラグ全て同じ |
| 6 | Tokyo×TF / GBP_USD×TF を FORCE_DEMOTED 追加 | WR < 15% |
| 7 | 「方向一致」などの断定的ラベル文言を全て神経活用 | 自己成就する誤認を防止 |

## 根本仮説 (Phase 2 で検証)

**「Signal enhancer は全て TF 前提の aligned-labeling で書かれているが、shadow データは MR dominant で逆相関する」**

この仮説が正しければ、単なるカテゴリ別分岐で大部分が解決する。ただし:

- **反証**: 今回の TF-only 分析で「方向一致」「機関フロー」が TF 戦略に対しても逆校正 (Δ-16pp, -10pp)
- → TF 戦略にとっても aligned-labeling が **間違って加点されている**
- → 根本は「aligned という判定自体が過剰に楽観」(noise に追従している)

つまり **TF/MR 分岐では不十分**。enhancer ごとの raw conf_adj 設計が mis-calibrated。

### 推奨最終形 (Phase 3)

1. すべての enhancer の conf_adj を 0 に中立化
2. reasons タグだけログに残す (分析・観察用)
3. **Probabilistic calibration (Platt / Isotonic)** で過去 shadow データから WR 回帰をフィット
4. gate は calibrated probability > threshold で一元化

## References

- Baseline: [[vwap-calibration-baseline-2026-04-23]]
- Lesson: [[lesson-vwap-inverse-calibration-2026-04-23]]
- Script: `/tmp/tf_inverse_rootcause.py`
- Registry (pre-design): `modules/strategy_category.py`
