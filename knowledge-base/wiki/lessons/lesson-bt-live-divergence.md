### [[lesson-bt-live-divergence]]
**発見日**: 2026-04-21 | **修正**: Tier 1 部分着手 (`_BT_SLIPPAGE` 公称実測値更新済み, app.py L4604) / 残バイアスは継続調査
- 教訓: **BT 結果は Live と乖離する。BT 正 EV ≠ Live 正 EV**。BT-Live divergence の 6 つの構造的楽観バイアス (摩擦, fill ratio, latency, slippage 分布, regime mix, survivor) を念頭に置かない判断は規律違反。
- 包括的分析: [[bt-live-divergence]] (DT/Scalp で摩擦構造が 5.4× 異なる発見, 戦略別乖離マトリクス, 6 バイアス内訳)
- 関連セッション: [[bt-live-divergence-scan-2026-04-22]] / [[bt-live-divergence-v3-full-stack-2026-04-22]]
- 適用範囲: 新戦略 promote 判断 / lot↑ / pair promotion 全てで「BT EV を Live で何 pip 失うか」の見積もりを必須にする
- 参照ノート: 4 箇所 (external-audit-2026-04-24, ema-tr-365d-bt-2026-04-20, shadow-baseline-2026-04-20)
