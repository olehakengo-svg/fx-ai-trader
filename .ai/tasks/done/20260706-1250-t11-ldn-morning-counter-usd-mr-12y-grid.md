---
id: 20260706-1250-t11-ldn-morning-counter-usd-mr-12y-grid
title: "[T11/WS3] LDN朝(UTC07-09)×counter-USD MR クラス禁止仮説 — 12y MASSIVE grid 検証 (R1)"
owner: codex
status: done
priority: P1
created_at: 2026-07-06T12:50:00+0900
roadmap_gate: "roadmap-v2.2 WS3 T11 — 通過すれば戦略横断 SIZE lever に昇格"
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/syntheses/roadmap-v2.2-win-conversion.md
  - knowledge-base/wiki/analyses/friction-analysis.md
related:
  - knowledge-base/wiki/lessons/lesson-asymmetric-agility-2026-04-25.md
---

# 0. なぜこのタスクか

roadmap v2.2 の 30d 実測で **LDN 朝 (UTC07-09) の counter-USD Mean-Reversion クラスが -71.8pip** と負けの核だった (2026-06-12 監査)。
T4 で SIZE lever 0.5x (E5/E7/E10, env kill switch 付き) は適用済み。本タスクは「この 30d 観測が **一般化可能な構造** か」を 12y MASSIVE データで検証する。

# 1. 仮説 (pre-reg)

H1: 「USD 一方向レジーム下の LDN 朝 (UTC07-09) に USD に逆らう MR エントリは、摩擦込み EV が有意に負」
- 帰無: EV(LDN朝×counter-USD MR) = EV(その他時間帯×同クラス)

# 2. 検証設計

- データ: MASSIVE 12y、USD_JPY / EUR_USD / GBP_USD / EUR_JPY (XAU 除外)
- クラス定義: MR 系シグナル (BB/RSI/pullback 系) × エントリー方向が DXY プロキシ (USD index 合成 or UUP) の 20d トレンドと逆
- Grid: 時間帯 (UTC07-09 vs 他) × USD レジーム (トレンド/レンジ、20d ADX or 符号) × ペア
- 統計: セル毎 Wilson lower + Bonferroni (グリッド全セル数で補正)。EV 軸で判定 (WR は補助 — 教訓: 止血判定は EV 軸)
- 摩擦: friction-analysis.md の per-pair RT を適用

# 3. 合否と次アクション

- PASS (Bonferroni 有意で負 EV 構造確認) → 戦略横断 SIZE lever 昇格の pre-reg を decisions/ に起案 (SKIP フィルタは作らない — SIZE lever 優先原則 2026-05-28)
- FAIL → 30d 観測はレジーム一過性と結論、T4 の解除条件 (USD 一方向レジーム終了) の監視のみ継続

# 4. 成果物

- knowledge-base/wiki/learning/t11-ldn-morning-counter-usd-mr-12y-{date}.md (rich report: N/EV/PF/Wilson/Bonferroni 全数値)
- verdict を roadmap-v2.2 T11 行に反映


## Result (2026-07-06T06:40:00Z)

- Codex companion job task-mr8sv8dq-1874n6 (11m35s): 初回判定 PASS (aggregate Bonferroni p=0.0497, pass cell EUR_JPY|TREND|LDN)
- **同日 Claude 敵対的検証で REJECT**: ①EUR_JPY は USD ネットエクスポージャ 0 (メカニズム不成立、USD 3ペア pooled p=0.33) ②擬似反復補正で aggregate p≈0.15 ③TREND 閾値 in-sample median リーク (walk-forward ×16=0.089)。2026 YTD 効果逆転 (+12.6p)
- 適用分岐 = §3 FAIL: 30d 観測はレジーム一過性。戦略横断 SIZE lever は起案せず、T4 解除条件監視のみ継続
- 成果物: knowledge-base/wiki/learning/t11-ldn-morning-counter-usd-mr-12y-2026-07-06.md (敵対的検証セクション含む) / bt-results/t11-*.{json,md} / tools/t11_ldn_morning_counter_usd_mr_12y_grid.py
