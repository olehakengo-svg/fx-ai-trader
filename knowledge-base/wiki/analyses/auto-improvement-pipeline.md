# 自動改善パイプライン設計 — 人間の指摘なしで問題を検知→修正する

## なぜ必要か
セッション中にユーザーが繰り返し指摘しなければ動かない状態はAIエージェントとして失格。
以下のパターンが全て「ユーザーの指摘」でしか検出されなかった:
- xs_momentumの全敗(TPが遠すぎる)
- EUR_USD SELLの毒性(数時間放置)
- BT乖離パーサーのバグ(0件出力)
- Lessons注入が0件

## 自動検知すべきパターンと対応

### Pattern 1: TPが遠すぎて利確できない
**検知方法**: MFE > 0 かつ outcome=LOSS のトレードで、MFE / (TP - entry) < 0.5 の割合が高い戦略
**意味**: 利益方向に動いたのにTP未達で反転。TPが遠すぎる証拠
**自動対応**: Discord通知「{strategy}: MFE到達率{rate}% — TP縮小またはQH適用を検討」
**実装先**: trade_monitor.py の check_strategy_performance()

### Pattern 2: 特定時間帯で全敗
**検知方法**: /api/demo/factors?factors=strategy,hour で EV<-1.0 & N≥5 のセルを検出
**意味**: その時間帯で構造的に負けている
**自動対応**: Discord通知 + demo_trader.py の session_pair ブロックに自動追加候補として提案
**実装先**: alpha_scan.py (毎日22:03実行)

### Pattern 3: Quick Harvestが効いていない
**検知方法**: QH適用済み(非exempt)なのに WR < 30% の戦略×ペア
**意味**: TPを0.85xに短縮してもなお負ける = そもそも方向が間違っているかSLがタイトすぎる
**自動対応**: Discord通知 + FORCE_DEMOTED候補として提案
**実装先**: trade_monitor.py

### Pattern 4: エントリー直後の即死(MFE=0)
**検知方法**: MFE=0のLOSSが全LOSSの80%以上の戦略
**意味**: エントリー方向/タイミングが根本的に間違っている (mfe-zero-analysis.md参照)
**自動対応**: 即座にFORCE_DEMOTED候補としてDiscord通知
**実装先**: trade_monitor.py

### Pattern 5: Shadowデータから正EV浮上
**検知方法**: Shadow trades (is_shadow=1) で N≥20 & EV>+0.5 の戦略×ペア
**意味**: FORCE_DEMOTED/Shadow化されたが、データが改善している = 復帰候補
**自動対応**: Discord通知「{strategy}×{pair}: Shadow EV={ev} — PROMOTE検討」
**実装先**: alpha_scan.py

## 実装優先度

| # | Pattern | 影響 | 実装コスト | 優先度 |
|---|---------|------|-----------|--------|
| 1 | TP遠すぎ | xs_momentum全敗を防げた | 中 | ★★★ |
| 2 | 時間帯全敗 | Tokyo xs_momentum全敗を防げた | 低(alpha_scanに追加) | ★★★ |
| 3 | QH無効 | - | 低 | ★★ |
| 4 | MFE=0即死 | bb_rsi/stoch等の早期検知 | 低 | ★★ |
| 5 | Shadow復帰 | ema_pullback等のPROMOTE加速 | 低(alpha_scanに追加) | ★★ |

## リンク
- [[claude-harness-design]] — ハーネスv2
- [[mfe-zero-analysis]] — MFE=0分析
- [[alpha-scan-2026-04-13]] — Alpha Scan結果
- [[session-decisions-2026-04-13]] — 意思決定記録
