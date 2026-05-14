# xs_momentum_rsi

## Overview
- **Entry Type**: `xs_momentum_rsi`
- **Mode**: daytrade (15m)
- **Pair**: USD_JPY only (Live, OANDA 転送)
- **Status**: PAIR_PROMOTED USD_JPY (2026-05-13, Bonferroni 未到達 user override)
- **Stage**: PAIR_PROMOTED — Live OANDA transfer USD_JPY only
- **Parent**: [[xs-momentum]] v8.9 + H1 RSI direction filter

## Edge thesis
TV Strategy Tester (USD_JPY 15m, 2026-05-13 取得) で H1 RSI が
方向と一致しているときだけ xs_momentum をエントリーすると、PF と
WR が体系的に改善することを発見した。

| Config | N | WR | PF | Net (price) | Max DD% |
|---|---|---|---|---|---|
| 1 Baseline (xs_momentum) | 501 | 43.51% | 1.04 | +11.83 | — |
| 2 Tokyo gate ON | 1,095 | 43.01% | 0.985 | -9.52 | — |
| **3 RSI filter ON (= xs_momentum_rsi)** | **290** | **46.55%** | **1.199** | **+31.92** | 25.35 |
| 4 Both ON | 576 | 46.53% | 1.186 | +57.37 | 23.42 |

Phase 2 詳細: [[xs_momentum-tv-phase1]] (Phase 2 セクション)

## Logic (xs_momentum との差分のみ)

xs_momentum v8.9 と完全に同一のモメンタム計算・ADX・EMA・確認足・
SL/TP・London-NY セッションゲート (UTC 12-18) に、以下の **H1 RSI
direction filter を追加**:

```
BUY:  rsi_h1 >= 60
SELL: rsi_h1 <= 40
```

H1 RSI は `ctx.df` (15m) を `resample_df(df, "1h")` で 1H 化したのち
`RSIIndicator(close, 14)` で計算する。現在足は除外して look-ahead を
排除。`ctx.htf["h1"]` は DT context では実際には H4 を返す ([app.py:4921](../../../app.py#L4921))
ため使えないので、戦略内で直接計算する。

不足時 (データ不足 / リサンプル失敗 / NaN) は `None` を返して
**fail-closed** (= エントリーしない)。

## Why Live, not Shadow

User explicit override (2026-05-13):
> 「新variantでliveも通るようにしちゃおう、これだけのEVが出る戦略は
> 珍しいのでOANDA転送を早めないとロードマップ達成できない」

詳細: [[../decisions/xs-momentum-rsi-live-promote-override-2026-05-13]]

## Risk containment

- **Pair lock**: `_enabled_symbols = ("USDJPY",)` — TV BT 検証範囲のみ
- **Lot scale**: 通常 lot (Kelly Half は N≥30 まで未適用)
- **既存 xs_momentum と並列稼働**: 本 variant は独立 entry_type で発火。
  USD_JPY では `xs_momentum` 本体 (BT EV=-0.129 で PAIR_PROMOTED 残置中) と
  `xs_momentum_rsi` の両方が候補に出る場合は `select_best` で score 比較。
- **Bonferroni gate**: 未到達。Live N≥30 + Bonferroni 通過まで lot↑ 禁止。
- **R2 demotion 用意**: 数 trade 〜 N=10 で EV<0 確認時に即 disable 可。

## Phase 3 plan (KB から拘束されるTODO)

1. **friction 反映 BT**: spread 0.7 + slip 0.5 を入れた Python BT で
   USD_JPY 15m 全期間を回し、TV BT と整合 (PF≥1.0) を確認。
2. **Live N 蓄積**: USD_JPY OANDA で N=30 まで蓄積。
3. **Bonferroni 評価**: `tools/bonferroni_pre_reg.py` で
   α=0.05/8=0.00625 ゲートを評価。通過したら Sentinel から外す。
4. **拡張判断**: EUR_USD / GBP_USD への適用は Python BT で個別評価。

## Related
- [[xs-momentum]] — 親戦略
- [[xs_momentum-tv-phase1]] — TV Phase 1+2 BT 結果
- [[tv-pine-edge-discovery-framework]] — Pine edge 検証フレーム
- [[../decisions/xs-momentum-rsi-live-promote-override-2026-05-13]] — Bonferroni 未到達 override
- [[../lessons/lesson-asymmetric-agility-2026-04-25]] — Rule R2 fast promotion
- [[../analyses/friction-analysis]] — USD_JPY 2.14pip RT
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
