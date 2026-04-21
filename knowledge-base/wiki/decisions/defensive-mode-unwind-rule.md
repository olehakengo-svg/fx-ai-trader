# Defensive Mode Unwind Rule — DD防御解除の条件化

**作成日**: 2026-04-21
**分類**: リスクポリシー（DD防御・Kelly昇格）
**ステータス**: ドラフト（コード変更は未実装。文書化＋品質ゲート提案）
**関連**: [[roadmap-v2.1]] / [[independent-audit-2026-04-10]]

---

## 問題設定

- 現在 DD=25.9% → `DD_LOT_TIERS` により lot×0.20 の防御モードで固着
- 月利100%目標に対し、このモードでは **月利47%** 推定。Kelly pool 拡大の最大ボトルネック
- 既存システムは DD%のみで自動昇降するが、**「DD回復だけで一気にフルロットに戻す」** と「汚染データで昇格 → 即再降格」のリスクがある
- 本ページは ①既存実装の正式化 ②品質ゲート追加提案 を行う

---

## 既存実装（`modules/risk_analytics.py`）

```python
DD_LOT_TIERS = [
    (0.08, 0.20),   # DD >= 8%: lot * 0.20
    (0.06, 0.40),   # DD >= 6%: lot * 0.40
    (0.04, 0.60),   # DD >= 4%: lot * 0.60
    (0.02, 0.80),   # DD >= 2%: lot * 0.80
]
# DD < 2%: lot * 1.0
```

- 対称設計: 減少時も回復時も同じ閾値（hysteresisなし）
- DD計算は `2026-04-13T15:00:00` 以降の FX-only, non-shadow trades に基づく（v8.9b Equity Reset）
- XAU除外

## ロードマップ上の Gate 構造

roadmap-v2.1 より:
| Gate | 条件 | 移行後 lot |
|------|------|-----------|
| Gate 1 | Aggregate Kelly > 0 | 0.2x → 0.3x |
| Gate 2 | Kelly>0.05, PnL>+50pip, 破産<70% | 0.3x → 0.5x（**月利100%相当**） |
| Gate 3 | PF>1.0, N≥100, 破産<30%, DSR>0.80 | → 1.0x |
| Gate 4 | DSR>0.95, 破産<10%, N≥200 | → **Kelly Half (3.0lot)** |

**構造的ギャップ**: 自動 `DD_LOT_TIERS` は DD%のみを見る。Gate 1〜4 の Kelly/PF/DSR 基準は現状 **手動判断** に依存。

---

## 提案: 三段階の unwind 条件（品質ゲート付き）

### 段階A: DD自動 unwind（既存、無変更）
- トリガー: DD% が閾値を下回る
- 挙動: `DD_LOT_TIERS` 表に従い lot_mult を段階的に戻す
- 用途: 短期的な損失回復（単純DD回復）

### 段階B: 品質ゲート付き加速 unwind（**新規提案**）
DD% だけでなく「直近の edge quality」を参照して加速または保留する。

**加速条件**（DD%閾値より早く上位 tier に移る）:
- 直近20 closed trades（FX-only, non-shadow, post-cutoff）で:
  - WR ≥ BEV + 3pp（ペア別BEVは [[friction-analysis]] 参照）
  - AND mean_pnl > +0.3pip/trade
  - AND 破産確率 < 50%

**保留条件**（DD%が閾値を下回っても昇格しない）:
- 直近20 trades で WR < BEV、または mean_pnl < 0
- 防御tierを保持（保留理由をログ）

### 段階C: Kelly Half への移行（1.0x → 3.0x）
**完全手動判断**。以下全てを満たす場合のみユーザー承認で移行:
- Gate 4 基準: DSR > 0.95, 破産 < 10%, N ≥ 200（roadmap準拠）
- AND クリーンデータ（post-cutoff, is_shadow=0, non-XAU）のみで判定
- AND 直近90日で drawdown ≤ 5%
- AND ELITE_LIVE 3戦略全てで Live Bayesian posterior P(WR>BEV) > 0.90

自動化は行わない。セッションでユーザーが明示承認すること。

---

## 実装優先順位

| # | 項目 | 種別 | 優先度 |
|---|------|------|--------|
| 1 | 既存DD_LOT_TIERSの正式文書化（本ページ） | 文書化 | 完了 |
| 2 | 段階B 品質ゲート実装（`check_unwind_quality_gate()` 追加） | コード | 高（ユーザー承認要） |
| 3 | 品質ゲート保留時の可視化（`/api/risk/dashboard` に `unwind_hold_reason` 追加） | コード | 中 |
| 4 | Kelly Half 移行判定の `tools/kelly_half_readiness.py` 新規作成 | ツール | 低（Gate 4到達まで不要） |

---

## 判断記録

- [DECISION 2026-04-21]: 既存 `DD_LOT_TIERS` 実装を unwind ルールの正典として採用。挙動変更なし。
- [DECISION 2026-04-21]: 段階B 品質ゲートは **提案段階**。コード実装はユーザー承認後に `modules/risk_analytics.py` へ `check_unwind_quality_gate()` を追加する形で進める。
- [DECISION 2026-04-21]: Kelly Half 自動昇格は **禁止**。Gate 4 全条件 + ユーザー明示承認が必須。

---

## Why: なぜこのルールが必要か
- **DDだけで戻すと汚染リスク**: 例えば特殊相場で一時的に PnL回復 → DD 2%未満 → フルロット → 次ドローダウンでさらに深いDDへ、という循環を防ぐ
- **Gate 4 自動化禁止の根拠**: Kelly Half (3.0lot) は DD=8%到達時に 0.6lot 相当の損失 = 大規模 drawdown 直結。人間チェックポイントを残す

## How to apply
- 次回セッションで本ページを参照し、段階B品質ゲートのコード実装許諾を得る
- 段階A挙動への変更は行わない（既存安定運用を壊さない）

## Related
- [[roadmap-v2.1]] — 月利100%ロードマップ全体像
- [[independent-audit-2026-04-10]] — 独立監査の DD防御勧告
- [[friction-analysis]] — ペア別BEV（品質ゲート判定に使用）
- [[edge-pipeline]] — 戦略 Stage 管理（Kelly pool 供給源）
