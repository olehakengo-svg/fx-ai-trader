# Wiki Quant Eval — 本番ログからの定量評価 + KB自動更新

本番トレードログを取得し、全戦略の定量評価を実行。結果をraw/に保存しwiki/を更新する。

## 引数
$ARGUMENTS — 評価対象期間 (例: "2026-04-08 to 2026-04-12") またはデフォルト (post-cutoff全期間)

## Phase 1: データ収集 → raw/に保存

### API取得
```
GET /api/demo/stats?date_from=2026-04-08     → 戦略別N/WR/PnL
GET /api/demo/learning                        → by_type/by_hour/by_regime/by_conf
GET /api/risk/dashboard                       → Kelly/VaR/CVaR/MC ruin/相関
GET /api/oanda/audit?limit=100               → OANDA約定状況
GET /api/demo/trades?limit=500               → 個別トレード(MAFE含む)
```

### raw/保存
結果を `knowledge-base/raw/trade-logs/quant-eval-YYYY-MM-DD.md` に以下フォーマットで保存:
```markdown
# Quant Evaluation: YYYY-MM-DD
## Raw Stats
[API結果のテーブル]
## MAFE Distribution
[戦略別のMAE/MFE集計]
## Kelly Per Strategy
[N>=10戦略のKelly/edge/CI]
```

## Phase 2: 定量分析

### A. 戦略別 Scorecard
各戦略について以下を算出:
| Metric | Formula |
|--------|---------|
| WR | wins / (wins + losses) |
| PF | gross_profit / abs(gross_loss) |
| EV/trade | total_pnl / N |
| Kelly | (p × b - q) / b, where b=avg_win/avg_loss |
| Instant Death % | count(MFE=0 losses) / total losses |
| Friction Ratio | avg(spread_entry + spread_exit + slippage) / avg(abs(pnl)) |
| BEV Margin | actual_WR - BEV_WR |
| Sharpe (approx) | mean(pnl) / std(pnl) |

### B. ポートフォリオ集約
- 正EV戦略のみの合計PnL
- 負EV戦略の損失額（=停止で回避できた額）
- XAU vs FX分離（v8.4でXAU停止済みだが効果測定）

### C. v8.3 確認足フィルターのOOS検証
- v8.3デプロイ日以降のbb_rsi/fib/ema_pullbackのみ抽出
- 即死率 (保有<2min + SL_HIT) を v8.3前後で比較
- WR変化の統計的有意性 (二項検定)

### D. Edge Pipeline Stage昇格判定
`knowledge-base/wiki/edges/edge-pipeline.md` の各エッジについて:
- Gate条件の充足チェック (N, WR, BEV margin, 相関)
- 昇格/保留/棄却の判定

## Phase 3: wiki/ 更新

### 更新対象
1. **wiki/index.md**: Tier分類テーブルをスコアカードベースで更新
2. **wiki/strategies/*.md**: 各戦略ページのPerformanceテーブルに最新行追加
3. **wiki/edges/edge-pipeline.md**: Stage更新
4. **wiki/concepts/**: 新しい知見があればページ作成 or 既存ページ更新
5. **wiki/log.md**: 評価結果サマリーを記録

### 矛盾検出
- index.mdのWRと個別戦略ページのWRが一致するか確認
- 前回評価からの急変（WR±10pp以上）を⚠️フラグ

## Phase 4: 出力サマリー

```markdown
## Quant Eval Summary: YYYY-MM-DD

### Portfolio Health
- Total N: XX (post-cutoff, shadow-excluded)
- WR: XX% | EV: XX pip/trade | Ruin prob: XX%
- FX-only PnL: +/-XX pip (XAU-excluded)

### Strategy Scorecard (top 5 by EV)
| Strategy | N | WR | EV | Kelly | Instant Death | Tier Change |
|----------|---|-----|-----|-------|-------------|-------------|

### v8.3 Confirmation Candle OOS Result
- bb_rsi instant death: XX% (pre-v8.3: 77.6%)
- fib_reversal instant death: XX% (pre: 75.9%)

### Edge Pipeline Updates
- [edge-name]: Stage X → Stage Y (reason)

### ⚠️ Warnings
- [any contradictions, rapid degradation, or anomalies]

### Next Actions
- [data-driven recommendations]
```

## ルール
- 全ての数値はAPI実測値に基づく（推測禁止）
- Shadow除外: is_shadow=0 のみ使用（v8.4フィルター）
- XAU除外: XAU_USDトレードは分離集計（停止効果の測定用）
- [[内部リンク]]で関連wiki/ページに接続
- 前回評価との差分を明示
