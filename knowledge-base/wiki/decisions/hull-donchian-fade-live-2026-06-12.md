# Decision: hull_donchian_fade LIVE 投入 (rule:R1 意図的例外)

- **Date**: 2026-06-12
- **Decision**: EUR_USD M15 圧縮ゲート二重確認フェードを shadow 経由せず MIN lot LIVE 投入
- **Authority**: User 判断 (「shadowではなく実弾検証を行いたい」「コーディングはClaude、Codexはレビューのみ」)
- **Precedents**: Kalman D7 (2026-05-20) / usdjpy_carry_dip (2026-06-08) / ZZ v60 (2026-05-28) / sweep_reversion_eurgbp_late (2026-06-12 同日)

## 検証チェーン (検証 repo: /Users/jg-n-012/test/hull-donchian-1m-validation)

1. **起源**: TV「Hull Suite + Donchian Trend Ribbon 1m で勝てる方法」(2026-06-10)
2. **1m momentum**: THESIS_INVALID — 3ペア全ホライズン forward return 負 (hit 0.45-0.48)
3. **1m fade**: 方向エッジ実在 (WR 0.55-0.59) だが friction-killed (gross+0.5p < spread)
4. **TF sweep (探索)**: fade gross は TF と共に成長、15m で spread の壁を超える
5. **15m fade pre-reg**: EUR_USD/GBP_USD 両方 C1-C4 通過 (BH-FDR m=2)
6. **深掘り** (train 2014-2022 → holdout 2022-2026 一発): width≤train-q33 + basis exit が
   唯一 transfer。EUR_USD: N=2133 WR=0.692 net+0.903p PF=1.156 p=0.0146。GBP_USD は不 transfer → 除外
7. **忠実度BT** (本番メカニクス TP=static basis / SL=4xATR intrabar SL-first / hold96):
   holdout N=1833 **WR=0.780 net+1.342p PF=1.191 p=0.0005**、LONG+1.05p/SHORT+1.57p 両side正
8. **TV 独立再現**: OANDA feed 365d WR 68.5% PF 1.167 (Python とほぼ一致)

## 統計的弱点 (隠さない)

- width ルールは train 6セル×2side×2pair からの**事後選択**を holdout で confirm — 真 OOS は LIVE のみ
- holdout は焼却済み (この窓での再 tuning 禁止)
- SHORT × macro-UP cell: holdout EV −0.10p (フラット)。監視対象
- スワップ未モデル (中央値保有 ~5h、>20h は ~4%)

## 統制

| 項目 | 値 |
|---|---|
| LIVE gate | env `HULL_DONCHIAN_FADE_LIVE_ENABLE=1` (default OFF) |
| lot | 固定 5000u 強制 (cascade 非依存、2026-06-12 user 指示) |
| mode 遮断 bypass | `_SHIELD_EUR_DT_WHITELIST` 登録 (silent-drop 対策) |
| CB | 既存 日次 -30pip / DD ゲート優先 |

## Pre-reg 撤退条件 (後出し変更禁止)

1. Live N≥10 ∧ net EV<0 → demote (Rule 2)
2. Live N≥30 ∧ (WR<55% ∨ PF<1.0) → demote
3. SHORT×macro-UP N≥30 ∧ EV<−0.5p → SHORT lot 0.5x (SIZE lever、SKIP 禁止)
4. 発火頻度逸脱: 30日で N<15 or N>80 (期待 ~40/月) → 配線/レジーム調査

## 実装メモ

- Claude 直接実装、Codex はレビューのみ ([[feedback_codex_as_review_layer_2026_06_05]])
- 並行セッション (sweep_reversion 42ba3fe3) と同日衝突 → commit 順序調整で解決
- E2E: tests/test_hull_donchian_fade.py 19 tests (発火/意味論/dedup/env gate/tier/whitelist/登録/契約pin)

## 契約保存レイヤ (2026-06-12, 32c65bc6 + b5b637cf)

共有 DT 経路には凍結スペックを書き換える変換ゲートが多数あり、全て監査して
免除/登録した。**初回 env flip 直後に sweep の Codex レビュー (c3b9f06e) で同型 gate の
存在が判明 → env を即 OFF に戻しリスク窓ゼロで修正** (発火前に検出)。

| Gate | 影響 (未対応時) | 対応 |
|---|---|---|
| SL/TP SR-ATR 再計算 | SL=4xATR → ~1xATR (MR 破壊) | _1H_PRESERVE_SLTP 登録 |
| RR≥1.2 / 0.8 床 | RR~0.25 契約が全 block | 本戦略のみ免除 (C-1) |
| **app.py RR1.3 TP リライト** | **TP=basis → 7.2xATR (別戦略化)** | _dte_preserve_sltp guard (I-1) |
| C1 半分時点早期損切り | basis 回帰前 loser を実損化 | 免除 |
| MAX_HOLD 8h (mode default) | p90=11.5h の尾を切断 | 24h 登録 |
| Quick-Harvest TP x0.85 | TP 意味論改変 | EXEMPT 登録 |
| MTF x1.3 TP 拡大 | TP=basis 改変 | 中和 |
| select_best 敗北 (score 3-5) | prod fires=0 (4回再発した既知バグ) | LIVE_PROMOTE_LOSERS 登録 (I-3) |
| OANDA_FORCE_FLAT_UNITS | MIN lot 上書き | bypass (I-4) |
| SL ワイドニング系 | SL が遠くなる方向のみ | **受容** (テール限定、締める方向ではない) |
| RANGE MR BB_mid TP | TP=basis → BB_mid | 非加入 pin (_RANGE_MR_STRATEGIES) |

教訓: **LIVE 例外戦略の本体実装より、共有経路の契約監査の方が工数も リスクも大きい**。
新規 LIVE 例外時はこの表をチェックリストとして使うこと。
