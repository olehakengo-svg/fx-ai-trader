# WS3 外部仮説 — 価格ベース lead-lag feasibility 診断 (rule:R3)

> read-only feasibility probe。verdict ではない。OOS 窓非消費。
> 起点: 内部探索 2 周 FAIL → 外部仮説転進 (ws3-round2-explore-prereg §3)

## A. 内部 cross-pair lead-lag (1h, 13 pair)
- 窓: 2023-01-01 21:00:00+00:00 → 2026-05-15 13:00:00+00:00 (N=20443 bars, 156 ordered pairs)
- **naive scan**: max|IC lag1| = 0.3731 (EUR_GBP→AUD_JPY), Bonferroni-sig = 50 pairs (r_crit=0.0252)
- **adversarial (Lo-MacKinlay 非同期取引 check)**: top hit を liquid-hours+destale で再計測 → IC = 0.0041 (崩壊)
- own lag-1 autocorr: EUR_GBP -0.405, AUD_JPY -0.323 (強い負値 = bid-ask bounce / stale-quote シグネチャ)
- **liquid majors only**: max|IC lag1| = 0.0273 (friction 2-4.5p 未満)
- **判定**: NULL — naive lead-lag は非同期取引 (Lo-MacKinlay) artifact。liquid-hours+destale で IC 崩壊、liquid majors max|IC| は friction 未満

## B. cross-asset lead (ZN 10y T-note fut → USD_JPY, 1h)
- ZN cache: 2026-03-27 10:30:00+00:00 → 2026-04-27 10:15:00+00:00 (N=438 — 短期、feasibility のみ)
- contemporaneous IC = -0.5848 (強い、符号整合: yields↑=ZN↓⇒USDJPY↑)
- **lag-1 lead IC (ZN→USDJPY) = 0.0075** (tradeable 先行なし)
- rev IC (USDJPY→ZN) = 0.1155
- **判定**: cross-asset linkage は contemporaneous で強い (IC~-0.58, 符号正) が lag-1 lead は ~0 → tradeable 先行なし。divergence-reversion 構成で要再評価

## 帰結
価格ベースの先行構造は OHLCV 内部でも cross-asset でも ≥1h バーで裁定消滅 (liquid 電子市場では情報は同時反映)。tradeable エッジは (a) 非先行構成 (contemporaneous linkage を使った divergence-reversion) か (b) 非価格モダリティ (positioning/flow/sentiment) が必要。→ [[external-hypothesis-scan-2026-07-13]] のスクリーン結論を実証的に支持。
