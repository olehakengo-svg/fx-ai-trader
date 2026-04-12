# Wiki BT Long — 長期バックテスト実行＋KB自動保存

120-365日の長期BTをbacktest-long APIで起動し、結果をKnowledge Baseに保存する。

## 引数
$ARGUMENTS — ペア+期間 (例: "USDJPY 120" / "ALL 120" / "EURUSD 365")

## 手順

### Phase 1: BT起動
対象ペアごとにPOSTリクエスト:
```
POST https://fx-ai-trader.onrender.com/api/backtest-long?mode=daytrade&symbol={SYMBOL}&days={DAYS}&chunk=30
```

ALLの場合: USDJPY=X, EURUSD=X, GBPUSD=X, EURJPY=X の4ペアを並列起動

### Phase 2: ポーリング
30秒間隔でGETリクエスト:
```
GET https://fx-ai-trader.onrender.com/api/backtest-long?task_id={TASK_ID}
```
status="done" まで待機（最大10分）

### Phase 3: 結果保存
`knowledge-base/raw/bt-results/bt-long-{DAYS}d-{DATE}.md` に保存:
- 全ペアのN, WR, PF, EV, Sharpe
- 戦略別entry_breakdown（top 10 by EV）
- v3 55d BTとの比較テーブル

### Phase 4: DSR再計算
N増加後のDSRを再計算:
```python
from modules.stats_utils import deflated_sharpe_ratio
dsr = deflated_sharpe_ratio(sharpe, n_trades=N, n_trials=53)
```

### Phase 5: wiki更新
- wiki/index.md のBTデータを更新
- 該当戦略ページにlong-BT結果を追記
- wiki/log.md に記録

## 使い方
```
/wiki-bt-long ALL 120    # 全ペア120日BT
/wiki-bt-long USDJPY 365 # USD_JPY 365日BT
```
