# Remote Agent Failure — 2026-05-14

**Date**: 2026-05-14T00:06:33Z  
**Task**: QH Overlay Forensic re-run (2026-05-14)  
**Status**: ❌ API 取得失敗

## エラー詳細

```
HTTP 403 from https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000: Forbidden
```

## 原因・対処

- この実行環境 (Codex sandbox) は `fx-ai-trader.onrender.com` への outbound HTTP が allowlist でブロックされている。
- 本番 API 自体のダウンではなく、ネットワーク制限が原因。
- `tools/qh_overlay_forensic_api.py` はすでに作成済み。
  Render 環境または allowlist が通るホストから以下を実行してください:

  ```bash
  python3 tools/qh_overlay_forensic_api.py
  ```

- または GitHub Actions / Render cron で実行可。

## ベースライン (前回 2026-04-30)

- N_total=316, cells_N≥10=8, Venn: raw_only=0 / qh_only=0 / both=0 / neither=8
- dt_bb_rsi_mr × GBP_USD: N=10, raw_EV=+9.54, raw_Wlo=0.313, ΔEV=−4.04
- 全セル FORCE_DEMOTED でサンプル不足が主因の判定。

*このファイルは `tools/qh_overlay_forensic_api.py` の失敗時ハンドラが自動生成します。*
