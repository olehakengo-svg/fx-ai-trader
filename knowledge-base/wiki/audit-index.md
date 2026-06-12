# Audit Index

- 2026-06-12: [LIVE負け要因監査 + Roadmap v2.2 Win Conversion](syntheses/roadmap-v2.2-win-conversion.md) — 30d clean live N=84/-37.9p。核=EUR_USD SELL -49.7p (ECB前底固め×LDN朝MR)、counter-USD MR -28p、JPY系+44p (160介入キャップ整合)。E12 stage=0 demote 実行 (rule:R2)。rsk dedup「未修正」は stale (caec0e88 2026-05-01 修正済) と実コード検証。MEMORY: `project_live_loss_factor_audit_2026_06_12`。
- 2026-06-12: [Edge Factor Audit #1 — ema_trend_scalp KILL](learning/edge-factor-audit-2026-06-12-ema-trend-scalp.md) — clean N=1,117 全セル均一負け / MAFE 0.5p / 反転不成立 → `SHADOW_RETIRED_STRATEGIES` 恒久退役 (rule:R2)。USD_CHF HourlyEngine 漏れ封鎖。MEMORY: `project_edge_factor_audit_2026_06_12`。
- 2026-06-02: [Kalman D7 / ZZ Pivot v60 SR zero-fire root cause](../raw/audits/kalman-zz-zero-fire-2026-06-02.md) — Kalman `MARKET_WAIT`, ZZ Pivot `SILENT_DROP_V3` with diagnostic instrumentation.
