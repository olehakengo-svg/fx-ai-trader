# Market Analysis — 市場分析の生データ

## 用途
特定の市場イベント・異常値・パターンの分析生データを保存する。

## 保存すべきもの
- 週次/月次の市場構造分析（ボラティリティ変化、セッション特性）
- 異常イベントの事後分析（フラッシュクラッシュ、NFP後の動き等）
- ペア別ミクロ構造分析（Spread/ATR推移、Noise Ratio変動）
- 時間帯別パフォーマンス分析（UTC別WR/EV）
- カレンダーイベント影響分析（FOMC、BOJ、ECB等）

## ファイル命名規則
`{topic}-{date}.md` 例: `weekly-vol-2026-04-14.md`, `nfp-impact-2026-04-04.md`

## 活用フロー
1. daily_report.py のレポートで異常検知
2. 深掘り分析をここに保存
3. 知見が戦略に影響する場合 → wiki/concepts/ にサマリ作成

## Related
- `raw/trade-logs/` — トレードログ（個別トレードデータ）
- `wiki/concepts/friction-analysis.md` — 摩擦分析のサマリ
