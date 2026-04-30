# MTF Regime Cascade v2.4 試案 — JPY クロス Transfer NULL Finding

## Status: NULL — _ALLOWED_PAIRS 拡張のみで JPY クロスに transfer 不可

`mtf_regime_trend_cascade_scalp` v2.3 を `_ALLOWED_PAIRS` 拡張のみで EUR_JPY/GBP_JPY に展開試行 → empirical で commit gate 不通過。**revert 済**, depth-test 別セッション (Phase A.2)。

## 動機 (Why)

v2.3 commit `83a9e10` で USD_JPY × NY (PF=1.98 Kelly+26.5%), EUR_USD × NY (PF=1.43 Kelly+13.5%) で Rule 1 PASS。同じ data 揃 + 摩擦特性を持つ JPY クロス (EUR_JPY BEV 33.7%, GBP_JPY BEV 38.0%) で同 cascade が transfer するか検証。

**仮説**: 15m moderate_trend regime + h1 macro alignment 構造は通貨横断的に成立 → `_ALLOWED_PAIRS` を 4 ペアに拡張するだけで edge 出るはず。

## BT 結果 (183d, cell=12, Bonferroni α=0.00417)

```
cell                              N    WR%  Wilson_lo   EV(p)     PF  Kelly%  Rule1
EUR_JPY × NY                     75  36.0%      26.1%  -0.43p  0.89   -4.6%  ❌ losing
EUR_USD × NY                     87  44.8%      34.8%  +1.31p  1.43  +13.5%  ✅ (existing)
USD_JPY × NY                     56  53.6%      40.7%  +3.15p  1.98  +26.5%  ✅ (existing)
USD_JPY × Sydney                  1   ─        ─       ─       ─     ─       (insufficient N)

Total trades: 219, Passing cells: 2/4
≥1 NEW pair (EUR_JPY/GBP_JPY) PASS: ❌ FAIL
```

**GBP_JPY × all sessions: N=0** — L0 spread_gate が 173541/177211 (98%) を block。

## Walk-Forward 結果 (3×60d × 4 pair = 12 sub-windows)

| Window | Pair | N | WR | PF | EV | Kelly | PASS |
|---|---|---|---|---|---|---|---|
| WF1 | USD_JPY | 21 | 33.3% | 0.95 | -0.24p | -1.9% | ❌ |
| WF1 | EUR_USD | 33 | 57.6% | 2.57 | +3.49p | +35.2% | ✅ |
| **WF1** | **EUR_JPY** | **24** | **25.0%** | **0.53** | **-2.05p** | **-21.9%** | **❌** |
| WF1 | GBP_JPY | N=0 | — | — | — | — | ❌ |
| WF2 | USD_JPY | 14 | 64.3% | 2.79 | +4.18p | +41.3% | ✅ |
| WF2 | EUR_USD | 32 | 34.4% | 0.78 | -0.86p | -9.7% | ❌ |
| **WF2** | **EUR_JPY** | **33** | **45.5%** | **1.21** | **+0.66p** | **+7.8%** | **✅** |
| WF2 | GBP_JPY | N=0 | — | — | — | — | ❌ |
| WF3 | USD_JPY | 27 | 51.9% | 1.91 | +3.09p | +24.6% | ✅ |
| WF3 | EUR_USD | 19 | 36.8% | 1.30 | +0.96p | +8.5% | ✅ |
| **WF3** | **EUR_JPY** | **17** | **23.5%** | **0.58** | **-1.94p** | **-17.0%** | **❌** |
| WF3 | GBP_JPY | N=0 | — | — | — | — | ❌ |

**Summary: 5/12 sub-windows PASS (41.7%, < 8/12 threshold) → ⚠️ UNSTABLE**

EUR_JPY 単独: 1/3 (WF2 only, WF1+WF3 lose) → temporally unstable edge

## 真因 2 つ

### 1. GBP_JPY: spread_gate 98% block

`spread_gate.should_block` の 4 重ハードゲート (hour_mult≤0.85 + spread_pips≤1.2 + tick_volume>40% + ATR/spread≥3.0) のいずれかが GBP_JPY で常時 fail。

最有力仮説: GBP_JPY は **spread 1.5pip + slippage 0.8pip = 2.3pip 摩擦** で `spread_pips ≤ 1.2` ハードゲートに弾かれる。USD_JPY/EUR_USD (0.7pip) 用に calibrate された閾値が、JPY クロスに transfer しない。

**修正方針** (Phase A.2): `spread_gate` を pair-aware に拡張、ペア別 spread floor 設定。

### 2. EUR_JPY: edge 弱い + 時間不安定

EUR_JPY × NY aggregate: PF=0.89 (BEV 周辺) — 構造的 break-even。Walk-Forward では:
- WF2 のみ PF=1.21 (border)、WF1/WF3 で PF<0.6 (clearly losing)
- → temporal instability

**仮説**: EUR_JPY は EUR + JPY の両方の macro driver の影響を受け、moderate_trend regime gate (15m EMA/ADX/Hurst) が EUR_JPY 固有の vol skew を捉えきれない。

**修正方針候補** (Phase A.2):
- EUR_JPY 専用 ADX threshold (15-22 等、低めにシフト)
- Hurst band 緩和 (0.40-0.60)
- 1H pullback layer 追加 (15m → 1H で fundamental driver smooth)

## Action Taken (本セッション)

1. `_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}` に revert (commit せず)
2. docstring に v2.4 NULL 記録 + KB 参照
3. 本 KB ファイル作成 (empirical record)

## 次セッション推奨アクション (Phase A.2)

### A.2.1 spread_gate pair-aware calibration
- `modules/spread_gate.py` に pair-specific threshold table 追加
- GBP_JPY: spread_pips ≤ 2.5 (vs USD_JPY 1.2)、ATR/spread ≥ 2.5 等
- 副作用検証: USD_JPY/EUR_USD 既存 cell が degrade しないこと

### A.2.2 EUR_JPY parameter sensitivity sweep
- ADX band: {15-22, 18-25, 18-30, 20-28}
- Hurst band: {0.35-0.60, 0.40-0.60, 0.40-0.55}
- 各組み合わせで N + PF + Walk-Forward stability 評価
- いずれかが Rule 1 PASS なら EUR_JPY 専用設定として導入

### A.2.3 GBP_JPY 構造仮説検証
- A.2.1 で spread_gate 緩和後 N>0 になるか
- GBP_JPY 高 vol (vs EUR_JPY) を活かせる cell が存在するか
- 不可なら Phase C (vol-skew MR cascade) に振り替え

## 教訓 — Filter Calibration は通貨横断的でない

v2.3 で確立した「moderate_trend gate + h1 macro + price-action L3」の **filter ensemble は USD_JPY/EUR_USD に calibrate された設計** であり、JPY クロスへの単純 transfer は不可。各 filter の閾値 (spread floor, ADX band, hour_mult cutoff) はペア毎の vol structure と摩擦に依存する。

**正しい transfer protocol** (next session の指針):
1. 上流 filter (spread_gate) を pair-aware に
2. 中流 filter (regime gate ADX/Hurst) を pair sensitivity sweep で再 calibrate
3. 下流 filter (L3 candle/bounce) は通貨横断で transfer 可
4. cell-level Bonferroni + Walk-Forward で再検証

## Cross-references

- 本 cascade strategy: `strategies/scalp/mtf_regime_trend_cascade_scalp.py`
- 親 KB: `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md`
- 摩擦定義: `modules/friction_model_v2.py:_FRICTION_PIPS`
- spread_gate 実装: `modules/spread_gate.py:should_block`
- Plan ロードマップ: `~/.claude/plans/shimmering-enchanting-bentley.md`
