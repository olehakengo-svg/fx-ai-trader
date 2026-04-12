# Audits — 監査生データ

## 用途
独立監査・定期レビューの**生データと元ファイル**を保存する。
wiki/decisions/ が判断結果のサマリであるのに対し、ここは元データ。

## 保存すべきもの
- 独立クオンツ監査の全文レポート（LLM生成含む）
- Risk Dashboard スナップショット（JSON/CSV）
- OANDA Audit ログのエクスポート
- Fidelity Cutoff前後のデータ比較レポート

## ファイル命名規則
`{type}-{date}.md` 例: `quant-audit-2026-04-10.md`, `risk-snapshot-2026-04-14.json`

## Related
- `wiki/decisions/` — 監査結果に基づく判断サマリ
- `/api/risk/dashboard` — リスクダッシュボードAPI
- `/api/oanda/audit` — OANDA監査API
