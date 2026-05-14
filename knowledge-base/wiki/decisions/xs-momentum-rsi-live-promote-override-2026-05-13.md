# xs_momentum_rsi Live Promote — User Override (Bonferroni 未到達)

**Date**: 2026-05-13
**Rule**: R2 (Fast & Reactive promotion) + explicit user override
**Strategy**: `xs_momentum_rsi` × USD_JPY
**Tier**: PAIR_PROMOTED USD_JPY (Live, OANDA 転送)

## Decision

新規 variant 戦略 `xs_momentum_rsi` を **Bonferroni gate 未到達のまま** USD_JPY
PAIR_PROMOTED として Live OANDA 転送経路に乗せる。Shadow 段階を経由しない。

通常運用ルール ([[../lessons/lesson-asymmetric-agility-2026-04-25]] Rule R1)
では「365日 BT or Live N≥30 + Bonferroni + Pre-reg LOCK」を要求するが、
本判断はそれを **意図的に waive** する。

## User instruction (一次根拠)

2026-05-13 セッションで以下の発言:

> 「新variantでliveも通るようにしちゃおう、これだけのEVが出る戦略は
> 珍しいのでOANDA転送を早めないとロードマップ達成できない」

直前のアシスタント案 (SHADOW-only) を明示的に上書きしたもの。

## Evidence (現時点で揃っているもの)

- TV Strategy Tester (USD_JPY 15m 全期間, friction=0):
  - Config 3 (= xs_momentum_rsi 等価): N=290, WR=46.55%, PF=1.199, Net=+31.92, MaxDD=25.35
  - Baseline (= xs_momentum): N=501, WR=43.51%, PF=1.04, Net=+11.83
- フィルター効果: N が約 ½ に減ったが PF が 1.04 → 1.20 に明確改善
- 詳細: [[../analyses/xs_momentum-tv-phase1]] Phase 2 セクション

## What is NOT yet done (deliberate gaps)

1. **Friction 反映の Python BT 未実施** — USD_JPY 2.14pip RT を入れた
   独立 BT で TV BT と整合するか未検証
2. **Bonferroni multi-test correction 未実施** — Phase 2 で 4 config を
   比較しているため α=0.05/4 のレベル評価が未完
3. **Live N≥30 未達** — 本判断時点で N=0
4. **他ペア (EUR_USD / GBP_USD) 未検証** — pair lock USD_JPY のみ

## Why override is acceptable (リスク評価)

- **Pair lock**: `_enabled_symbols=("USDJPY",)` で USD_JPY のみ。EUR/GBP に
  漏れない設計
- **Lot scale**: 通常 lot。Kelly Half 未適用 (N<30 のため自動的に gated)
- **Variant separation**: 親戦略 `xs_momentum` (USD_JPY BT EV=-0.129) は
  別 entry_type のため、変動が混ざらない
- **既存 OANDA 路の検証済み skin**: registration 4-point sync 経由なので
  fire-and-forget 経路の bug 混入リスクは新規ゼロ
- **R2 demotion 用意**: 数 trade 〜 N=10 で EV<0 確認時に即 disable 可
  (env flag や enabled=False patch で停止)

## Lesson awareness (これは知って踏み越えた線)

以下の lesson に意図的に違反している:

- [[../lessons/lesson-cell-audit-bt-required-2026-04-27]]
  — 「促進判定 (Kelly) も逆校正判定 (Bonferroni) も同じ統計厳格さで行う」
- [[../lessons/lesson-asymmetric-agility-2026-04-25]] R1
  — 「新戦略 / lot↑ / pair promotion → 365日 BT or Live N≥30 + Bonferroni 必須」

これは未知の bug ではなく、**ロードマップ目標 (月利100% → 年利1,200%) と
時間制約を理由とした明示的 trade-off**。アシスタントの自己判断ではなく
ユーザーの roadmap 駆動判断による override。

## Monitoring obligation (本決定の条件)

Live 転送開始後、以下を継続監視:

1. **N=10 時点で EV 中間レビュー** — EV<0 ならアシスタント側から即時
   demote 提案 (R2 fast demotion)
2. **N=30 達成時点で Bonferroni 評価** — `tools/bonferroni_pre_reg.py`
   を回し、α=0.05/8=0.00625 未通過なら lot↑ 禁止継続
3. **Friction 反映 Python BT を ASAP 実施** — Phase 3 plan
   ([[../strategies/xs-momentum-rsi]] Phase 3 plan 参照)
4. **他ペア拡張は別 decision で評価** — USD_JPY のみで完結する間は
   このページの範囲内

## Reversal triggers (どうなったら止めるか)

- N≥10 で EV<0 → 即 R2 demote
- N=30 で Bonferroni 未通過 → lot↑ せず、disable 検討
- USD_JPY friction 込みの Python BT で PF<1.0 → 即 disable
- 他の本番戦略の Kelly 配分を不当に減らす場合 → 一時停止 + 再評価

## Related
- [[../strategies/xs-momentum-rsi]] — 戦略カード
- [[../strategies/xs-momentum]] — 親戦略
- [[../analyses/xs_momentum-tv-phase1]] — TV Phase 1+2 BT evidence
- [[../analyses/tv-pine-edge-discovery-framework]] — Pine edge 検証フレーム
- [[../lessons/lesson-asymmetric-agility-2026-04-25]] — Rule R1/R2/R3
- [[../syntheses/roadmap-v2.1]] — 月利100% 目標
