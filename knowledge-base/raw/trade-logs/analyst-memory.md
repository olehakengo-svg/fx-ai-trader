# FX Analyst Memory — Multi-Pair Trading System (v8.9)

> このファイルはFXアナリストエージェントの長期記憶です。
> daily_report.py (GitHub Actions) により自動更新されます。
> 学術的知見は [[research/index]] を参照。

---

## デプロイ情報

| 項目 | URL |
|------|-----|
| 本番環境 (Render) | https://fx-ai-trader.onrender.com/ |
| デモ分析ページ | https://fx-ai-trader.onrender.com/demo-analysis |
| GitHub リポジトリ | https://github.com/olehakengo-svg/fx-ai-trader |

---

## 現在のシステム状態 (v8.9, 2026-04-13)

- **目標**: 月利100% (Kelly Half到達で594%)
- **防御モード**: 1.0x (Equity Reset済, v8.4以降クリーンデータ起点, DD=0.8%)
- **XAU**: 停止 (v8.4) — post-cutoff XAU loss = -2,280pip (損失の102%)
- **FX-only**: +96.8pip (黒字)
- **BT摩擦モデル**: v3 (Spread/SL Gate + RANGE TP + Quick-Harvest)
- **DSR**: 実装済み (Bailey & Lopez de Prado 2014, 多重検定補正)

---

## 戦略評価ログ

| 日付 | 戦略 | タイムフレーム | WR | EV/trade | 判定 | メモ |
|------|------|--------------|-----|---------|------|------|

---

## 確立された知見 (v8.9時点)

### Tier 1 Core Alpha
- **bb_rsi_reversion**: WR=36.4% (N=77), v8.3 confirmation candle で改善傾向
- **orb_trap**: BT WR=79%, 実績N=2で蓄積中
- **session_time_bias**: BT WR=69-77%, 学術★★★★★ (Breedon & Ranaldo 2013)
- **london_fix_reversal**: GBP_USD BT WR=75%, 学術★★★★★

### 重要な教訓
- **Shadow汚染**: get_stats()がis_shadow=0フィルターなしでWR算出 → v8.4修正
- **XAU摩擦歪み**: FX friction=2.14pip, XAU=217.5pip。XAUが平均を30倍に歪めた
- **集計値は必ずセグメント分解** — 平均値は嘘をつく
- **BT before deploy** — 必ず120日+BTでOOS検証してからPromotion

### ペア別知見
- **USD_JPY**: london_fix_reversal ❌ (WR=28.6%), xs_momentum ❌ (EV=-0.129)
- **EUR_USD / GBP_USD**: DSR>0.95で統計的有意 (120日BT v3)
- **EUR_JPY**: scalp ❌ (friction/ATR=43.6%, 構造的不可能)

---

## アナリストノート

*（daily_report.py により自動追記）*

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
