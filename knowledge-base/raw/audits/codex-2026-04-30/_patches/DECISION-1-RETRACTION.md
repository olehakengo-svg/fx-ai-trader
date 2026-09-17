# Decision 1 訂正: bb_rsi_reversion ELITE_LIVE 昇格提案 → 取り下げ

> 作成日: 2026-04-30 13:30
> 元提案: 99-senior-quant-memo.md v2 Decision 1

## 取り下げの根拠

bb_rsi_reversion の LIVE 22 件 (+192pip) のタイムスタンプを精査した結果、以下が判明:

1. **22 LIVE 全件が 2026-04-02 〜 2026-04-15 の期間に集中**
2. その後 **2026-04-25** に `_BB_RSI_OANDA_TRIP` 緊急停止 (`modules/demo_trader.py:4485`)
3. **2026-04-28** に PAIR_DEMOTED 化 (`modules/demo_trader.py:5938-5975`)
4. demote 根拠は "Post-cut N=76 WR=38.2% EV=-0.28 Kelly=-5.5%" ← **より長い窓の実績で edge decay を確認**
5. Shadow N=14 -37pip (post-demotion) が現状値、edge decay と整合

つまり **既にシステムは正しく対応済み** で、私の v2 提案は時間的コホートの混同による誤り。

## 振動パターン認識

CLAUDE.md memory の同パターン再発:
> Q1' の cell-level Bonferroni-significant 発見を出した後、ユーザー指摘でまた KB 全面服従して「C1 撤退」発言

今回は逆方向 (KB の demote を覆して promote 提案) だが、**「cell 数値だけ見て時間軸を無視」** の構造は同じ。

## 真の正しい提言 (Decision 1 差し替え)

### 1-A. fib_reversal の C1_PROMOTE 経路を追跡
- `_C1_PROMOTE_CANDIDATES` に既登録: USD_JPY × Tokyo × q0 × scalp (N=24 WR=87.5% Wlo=69.0% p_bonf=0.0007)
- Pre-reg LOCK 体制で運用されている (`pre-reg-cell-promotion-2026-04-27.md`)
- **Claude が追加すべき提言は無い** — システムが正しく処理中

### 1-B. tier_live_drift.py を nightly 化
- Decision 4 で実装した tools/tier_live_drift.py を CI/cron に組み込み
- ELITE_LIVE / PAIR_PROMOTED の Live drift を毎日検出
- 検出ルール (現状の lesson-asymmetric-agility-2026-04-25 と整合):
  - **Rule 2 (Fast & Reactive)** → 損失停止/Shadow降格 (現運用と整合)
  - 自動 demote 提案を Slack/通知に流す
- これが「Tier の Live drift 自動是正」の真の実装

### 1-C. 既存の demote/promote 運用が正しく機能しているかの監査
- 過去 30日 で発生した demote (bb_rsi_reversion 含む) の根拠データを `decisions/` に集約
- 各 demote について「demote 後 30日の Shadow EV」を追跡し、demote が早すぎ/遅すぎを評価
- 結果: tier_live_drift.py のしきい値チューニング根拠を作成

## 行動変更

私 (Claude) の今後の行動規範:
1. **時間的コホート分離**: cell-level 統計を見るときは「いつのデータか」を必ず確認
2. **既存運用の理解優先**: tier-master.md の demote/promote 履歴を**時系列で**読むことを最初に行う
3. **「KB を絶対視」も「自分の分析を絶対視」もしない**: cell 数値で promote 提案する前に、demote 経路を確認

## ガバナンス課題

これは Sub 8 で指摘した「lesson が code に内部化されていない」と同型:
- lesson-asymmetric-agility-2026-04-25 が Rule 2 (Fast & Reactive) を定義済み
- しかし audit 分析時に「demote コホート分離」をチェックする仕組みがない
- → tier_live_drift.py に **demote 履歴と LIVE データのコホート整合チェック**を追加すべき
