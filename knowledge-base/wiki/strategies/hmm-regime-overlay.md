# HMM Regime Overlay — レジーム検出オーバーレイ

## Stage: SENTINEL (v8.5, 防御オーバーレイ)

## Hypothesis
HMM（隠れマルコフモデル）2状態（calm/turbulent）でFXボラティリティレジームを検出。turbulentレジームではポジションサイズ縮小しMaxDDを半減（Charles U 2024, Nystrup 2024）。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| Charles U Prague 2024 | HMM 2状態がFX日次リターンで有意に検出可能 | ★★★ |
| Nystrup et al 2024 | Statistical Jump ModelがHMM超え。MaxDD大幅削減 | ★★★★ |

## これはアルファではない — リスクフィルター
**正直な評価**: リターン向上ではなくリスク調整後リターンの改善。MaxDD 24%→56%削減のデータあり。

## Quantitative Definition
```python
from hmmlearn import GaussianHMM
# 2状態HMM on 日次log returns (30-60日ウィンドウ)
# State 0: calm (低ボラ) → full position (1.0x)
# State 1: turbulent (高ボラ) → reduced position (0.3x)
# Walk-forward: 60日学習 → 1日推論 → ローリング
# 重要: 状態数は2に固定（3以上はオーバーフィット）
```

## Implementation Complexity: 3/5
hmmlearn (Python) で数十行。ウォークフォワード検証が必須。

## Key Risk
- レジーム判定に数日の遅延（急変に追いつけない）
- パラメータ選択（状態数、学習ウィンドウ）にオーバーフィットリスク
- 2状態固定+ウォークフォワードが鉄則

## Integration
全戦略のメタオーバーレイとして。defensive_mode (0.2x lot)のデータ駆動版。
現在のDD-based lot_multiplierを補完/置換する可能性。

## Related
- [[research/index]]
- [[vol-momentum-scalp]] — ボラレジームと直結
- [[independent-audit-2026-04-10]] — 破産確率85%への対処
