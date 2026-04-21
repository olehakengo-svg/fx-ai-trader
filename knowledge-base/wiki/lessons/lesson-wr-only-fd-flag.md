# Lesson: WR 単独基準の FD_FLAG は高 R:R 戦略を誤止血する

**日付**: 2026-04-21
**影響ツール**: `tools/bayesian_edge_check.py`
**関連ページ**: [[negative-strategy-stopping-rule]] / [[bb-squeeze-breakout]] / [[lesson-orb-trap-bt-divergence]]

---

## 何が起きたか

`tools/bayesian_edge_check.py` 初版の FORCE_DEMOTE 判定ロジック:

```python
force_demote_flag = (post["p_wr_above_bev"] < 0.10 and n >= 20)
```

これを初回実行（2026-04-21）で **11 FD_FLAG** が検出された。その中に:

- **bb_squeeze_breakout × USD_JPY** (post-cutoff is_shadow=1): N=35 WR=31.4% P(WR>BEV)=0.02 → FD_FLAG

しかし同戦略は:
- 365d BT: **N=43 WR=74.4% PF=1.818 Wilson CI [59.8%, 85.1%]** → PAIR_PROMOTED 維持（コミット 9918057）
- Shadow KB 記載: **N=41 EV=+1.55pip** 正 EV
- Live 実測: mean_pnl_pips **+1.55 pip** → 赤字ではない

**矛盾の原因**: 判定ロジックが WR 単独で、payoff 構造 (R multiple = 平均勝ち / 平均負け) を無視していた。

---

## 根本原因

**対称 R:R (=1:1) の暗黙前提**:
- BEV_WR は「スプレッド + スリッページ を勝率でカバー」を意味する
- しかし **mean win >> mean loss** の戦略 (BO, reversion, ORB 系) では WR < BEV でも EV > 0
- bb_squeeze_breakout は BO 系で R:R が 1:4 超の payoff 構造

**数学的に見れば**:
```
EV = WR * mean_win - (1-WR) * mean_loss
```
WR=31% で mean_win=6.5 pip, mean_loss=-0.7 pip なら:
```
EV = 0.31*6.5 - 0.69*0.7 = 2.015 - 0.483 = +1.53 pip ✅
```
これは KB 記載 +1.55 pip とほぼ一致。

---

## 誤診断のリスク

もし修正前の FD_FLAG リスト（11 cell）で Level A/B/C 止血ルールを運用していた場合:

- bb_squeeze_breakout × USD_JPY は PAIR_PROMOTED である一方で FD_FLAG 扱いされ、 **止血ルールと tier 運用が矛盾**
- 更に悪いシナリオ: 同様の高 R:R 戦略を **誤って Level B (shadow 全停止) 対象**に入れ、正エッジを消す

= **正エッジ戦略の誤殺 (false-positive shutdown)**

---

## 修正

```python
force_demote_flag = (
    post["p_wr_above_bev"] < 0.10
    and n >= 20
    and mean_pnl <= 0  # NEW: guard against high-R:R false positives
)
```

**再実行結果**: 11 FD_FLAG → **10 FD_FLAG**。bb_squeeze_breakout × USD_JPY は正しく除外。残 10 cell は全て実測 mean_pnl ≤ 0 = 真に赤字確定。

---

## Why (教訓の本質)

- **止血判定は EV 軸で行う。WR は補助指標に過ぎない**
- Break-even WR は対称 R:R 近似。BO / reversion / ORB 系には **そのまま適用できない**
- Bayesian posterior を使っても、**定義式に埋め込まれた暗黙仮定は posterior 自身が直してくれない**
- 「数学的に厳密」は「モデルが正しい」と同義ではない

---

## How to apply

- FD/PP を WR ベースで論じる前に **必ず mean_pnl の符号** を確認する
- `tools/bayesian_edge_check.py` を拡張する際は、判定式を WR に加えて **実測 PnL 条件** で AND 結合する
- 将来、より厳密には `P(EV > 0 | data)` を Bootstrap MC で計算するアップグレードを検討（本修正は応急処置）
- 戦略ページ (`wiki/strategies/*.md`) に **R:R 比**を明記しておくと、将来の FD/PP 判定で即参照可能

---

## Related

- [[negative-strategy-stopping-rule]] — 本 lesson を受けた改訂 §2.1 に記録済
- [[bb-squeeze-breakout]] — 高 R:R 戦略の具体例
- [[lesson-orb-trap-bt-divergence]] — BT-Live 乖離の別形態
- [[lesson-kb-blind-pp-proposal]] — 本 lesson と対（PP 側の盲点）
