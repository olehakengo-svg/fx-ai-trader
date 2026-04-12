# Microstructure: Stop Hunting & Liquidity Sweeps

## Core Theory
機関投資家は個人投資家のSL注文が集中する価格水準（Swing H/L、ラウンドナンバー）を意図的にスイープし、その流動性を利用して大口ポジションを構築する。スイープ後、価格は急速に元のレンジに回帰する。

## Key Papers
- [[osler-2003]]: SL注文がスイングH/L直外に高密度で集中することを実証。1996-1998年の実データで個人投資家のSL配置パターンを分析
- [[kyle-1985]]: 情報を持つ大口投資家が流動性を搾取するメカニズムの理論モデル
- [[bulkowski-2005]]: False breakout後のリバーサルパターンWR=60-70%を経験的に確認

## Implemented Strategies
- [[liquidity-sweep]] (Stage 4: SENTINEL) — ウィック構造+ボリュームプロキシ+レジームフィルター
- [[orb-trap]] (Stage 6: PROMOTED) — セッションORのフェイクアウト特化版

## Unexplored Extensions
1. **ラウンドナンバー・スイープ**: Osler (2003)は.000/.500にSL集中を確認。現在のround_number SL avoidanceは防御のみ→攻撃に転用可能？
2. **時間帯依存のスイープ確率**: London Open (UTC 7-8)のスイープ頻度はAsia (UTC 0-6)の3倍（Andersen & Bollerslev 1998）→ セッション特化スイープ戦略
3. **Multi-level sweep**: 1つのスイングレベルだけでなく、複数レベルを連続スイープするパターン（「段階的流動性刈り取り」）
4. **Volume profile連動**: OANDAのtick volumeとスイープ検出の組み合わせ精度向上

## Related
- [[session-effects]] — スイープはセッション境界で頻発
- [[friction-analysis]] — スイープ戦略の摩擦耐性（15m DT: friction/SL=11-18%）
- [[edge-pipeline]] — Sentinel → Validated パス
