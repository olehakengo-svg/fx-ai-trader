# Pre-registration: sweep_reversion_eurgbp_late + hull_donchian_fade LIVE 初週監視

**作成**: 2026-06-12 (roadmap v2.2 T8)
**Rule**: R1 pre-reg (撤退発動は R2)
**状態**: 🔒 LOCKED (観測期間: 2026-06-12 → 2026-06-19)
**対象**: 本日 LIVE 投入の 2 戦略 (R1 intentional exception, fixed 5000u, commits 42ba3fe3 / 4360ec99 / a7ccd437)

## 検証時の前提 (これが裏切られたら撤退)

| 戦略 | 検証根拠 | 発火頻度期待値 | spread 前提 |
|---|---|---|---|
| sweep_reversion_eurgbp_late (EUR_GBP 15m L96 BUY H48 LATE) | 12y grid 唯一生存 (N=543, +6.22p/trade, t=4.46, WFO全正, Bonferroni m=1728) | 543/12y ≈ **3.8件/月** (±3×で 1.3〜11件/月) | **1.5p 仮定**。実測 >3.5p で edge 消滅域 (感度検証済み) |
| hull_donchian_fade (EUR_USD M15 compression fade) | pre-reg C1-C4 全通過 (net +0.66p, PF1.07, 12.4y, N=8.5k) | 8,500/12.4y ≈ **57件/月** (±3×で 19〜171件/月) | EUR_USD 通常 spread (0.8-1.0p) |

## 撤退トリガー (発動 = R2 即時、裁量禁止)

1. **発火頻度乖離 >3×** (週次換算: sweep <0.3 or >2.6件/週、hull <4.4 or >40件/週) — 移植バグ or レジーム断絶のシグナル
2. **sweep 実測 spread_at_entry 中央値 > 3.5p** (EUR_GBP) — エッジ感度の崩壊域
3. **初週で PnL < -30p (どちらか単体)** — 12y 分布から逸脱した即時損失
4. **dedup_violation / runaway パターン** (同一バー複数 emit) を 1 件でも検出 — 即停止 + forensic

## 発動時アクション

- 該当戦略の LIVE 転送停止 (Shadow は継続、原則3)
- forensic: 発火ログ × 12y BT 同条件の突合を audit-index に記録

## 既知の caveat (観測対象)

- sweep のエッジは **2021-2026 に集中** (12y 中)。レジーム依存の可能性を per-trade で記録
- hull は net +0.66p の薄いエッジ — friction 実測 (spread+slippage) が BT 仮定を超えないか毎週確認

## 週次レビュー (毎金曜)

clean live (is_shadow=0, dedup除外) で N / WR / EV / 実測spread / slippage を本ページに追記。
