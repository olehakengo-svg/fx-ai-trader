# Negative Strategy Stopping Rule — 負戦略の止血条件

**作成日**: 2026-04-21
**分類**: 分析プロトコル（Shadow/Live 監視）
**関連**: [[edge-pipeline]] / [[defensive-mode-unwind-rule]] / [[lesson-orb-trap-bt-divergence]]
**ツール**: `tools/bayesian_edge_check.py`

---

## 問題設定

Shadow 観察は「データ蓄積」の名目で **無限に続けられてしまう** 構造欠陥がある:
- 明確に failing している戦略（posterior P(WR>BEV) < 0.05）が N=50, 70, 100 と累積しても止まらない
- コンピュート・DB・UI 占有コストが累積
- FORCE_DEMOTED の「復活観察」が事実上の永久延命に化ける

本ページは **データ駆動の止血ルール** を明文化し、Shadow を「仮説検証」に戻す。

---

## 現状（2026-04-21 Bayesian 出力、FIDELITY_CUTOFF 以降）

`tools/bayesian_edge_check.py --min-n 15` より:

| strategy | pair | N | WR | P(WR>BEV) | flag |
|----------|------|---|-----|-----------|------|
| ema_trend_scalp | USD_JPY | 125 | 20.8% | 0.00 | FD_FLAG |
| ema_trend_scalp | EUR_USD | 68 | 20.6% | 0.00 | FD_FLAG |
| bb_rsi_reversion | USD_JPY | 77 | 26.0% | 0.00 | FD_FLAG |
| stoch_trend_pullback | USD_JPY | 54 | 22.2% | 0.00 | FD_FLAG |
| ema_trend_scalp | GBP_USD | 37 | 13.5% | 0.00 | FD_FLAG |
| bb_squeeze_breakout | USD_JPY | 35 | 31.4% | 0.02 | FD_FLAG |
| fib_reversal | USD_JPY | 35 | 31.4% | 0.02 | FD_FLAG |
| sr_channel_reversal | USD_JPY | 33 | 27.3% | 0.01 | FD_FLAG |
| engulfing_bb | USD_JPY | 30 | 26.7% | 0.01 | FD_FLAG |
| bb_rsi_reversion | EUR_USD | 25 | 28.0% | 0.02 | FD_FLAG |
| fib_reversal | EUR_USD | 21 | 14.3% | 0.00 | FD_FLAG |

全 11 cell が Bayesian posterior で **「BEV を超える確率 < 10%」** = 統計的に failing 確定。

---

## 止血ルール（提案）

### Level A: Shadow-to-FORCE_DEMOTED 固定
**条件**:
- N ≥ 20 AND P(WR > BEV | data) < 0.10 （Beta(2,2) prior）
- OR 直近30日 mean_pnl < -0.5pip/trade（連続失敗）

**挙動**:
- `tier-master.json` 側で FORCE_DEMOTED を維持（PP 復活候補から外す）
- shadow 観察は継続可能だが **リソース優先度は最低**
- 次の 365d BT scan で再評価。BT EV が維持されていれば復活候補に戻す

### Level B: Shadow 停止候補（全停止）
**条件**:
- Level A 条件 AND
- N ≥ 50 で P(WR > BEV) < 0.05 持続（3週連続）AND
- 365d BT も負EV（or N不足で検証不能）

**挙動**:
- `DaytradeEngine/__init__.py` の `_UNIVERSAL_SENTINEL` から削除提案（ユーザー承認要）
- shadow シグナル生成も停止し、DB 占有を止める
- 削除は **ユーザー明示承認** が必要（自動化禁止）

### Level C: 監視モードのまま継続（shadow 温存）
**条件**:
- P(WR > BEV) が 0.10〜0.50 のグレーゾーン AND
- 365d BT で positive EV AND
- Live への橋渡し候補

**挙動**:
- 追加データ蓄積を継続
- 月次レビューで状態変化を確認

---

## 運用フロー

```
週次（cron） or 手動:
  python3 tools/bayesian_edge_check.py --min-n 20 --json > /tmp/bayes.json
  └→ FD_FLAG 戦略を抽出
  └→ Level A/B/C 分類
  └→ Level B 候補が出た場合、判断セッション
```

### ユーザー承認フロー（Level B 到達時）
1. Claude が候補リスト提示（本ページの形式）
2. ユーザーが戦略ごとに approve / hold / reject
3. approve → `DaytradeEngine/__init__.py` 修正 + session decision 記録
4. hold → 3週間後の再評価

---

## 判断記録

- [DECISION 2026-04-21]: 止血ルール Level A/B/C を正式採用
- [DECISION 2026-04-21]: 本日の 11 FD_FLAG は全て **Level A（FORCE_DEMOTED 維持）** に該当。全て既に FORCE_DEMOTED または PAIR_DEMOTED 済みのため追加アクション不要
- [DECISION 2026-04-21]: Level B (shadow 全停止) 判定は **未実施**。3週連続の posterior 確認が必要

---

## Why
- **無限 shadow 問題**: データ蓄積原則は健全だが、明確な failing 戦略の無限延命は監視コストの浪費
- **Bayesian 基準の優位性**: 「WR < 50%」のような点推定ではなく、信用区間から「有意に failing」を判定可能
- **Level B の承認要件**: 戦略の削除は不可逆に近い（再追加には再実装+再BT）。人間チェックポイント必須

## How to apply
- 次セッション以降、週次で `bayesian_edge_check.py --min-n 20 --json` を実行
- Level B 候補検出時は本ページの承認フローに従う
- Level A の FD_FLAG は `lessons/lesson-kb-blind-pp-proposal` 遵守: 「+EV 出た」で PP 復活提案する前に、まず FD_FLAG リストで除外されていないか確認

## Related
- [[defensive-mode-unwind-rule]] — DD 解除時の品質ゲート（本ルールと対の「昇格」側）
- [[edge-pipeline]] — Stage 管理
- [[lesson-orb-trap-bt-divergence]] — 短期 BT 楽観の回避
- [[lesson-kb-blind-pp-proposal]] — KB 照合なしの PP 提案回避
