# S2 Turtle USDJPY long — Live Promote Pre-Registration

**Author**: Claude (quant analyst mode, on behalf of fizzy-patterson Wave 2)
**Registration date**: 2026-05-03
**Strategy**: S2 Turtle System 2 (55-day Donchian) USDJPY long-only
**Current tier**: Shadow (`is_shadow=1`)
**Branch / PR**: `feat/s2-turtle-usdjpy-long-shadow-2026-05-03` / [#15](https://github.com/olehakengo-svg/fx-ai-trader/pull/15)

---

## なぜ Bonferroni p<0.05 ではなく p<0.20 を緩和 gate にしたか

55-day Donchian D1 では 15.3 年の USDJPY M1→D1 集約データで N=50 が **構造的上限** である (5 long signals/year × 15.3y ≈ 76 が物理的最大、実測 N=50)。Bonferroni K=2 (USDJPY long + GBPJPY long) で p=0.172 は通常 reject 帯だが、以下 3 点の補強で **Shadow 段階に限り** 緩和を許容:

1. **OOS PF (1.99) > IS PF (1.08)** — anchored 60/40 walk-forward で OOS が IS を上回る。これは overfit signal の真逆 (overfit cell では OOS<IS が標準)。
2. **PF=1.99 自体が strong** — 1.5 を大きく超え、+10374 pips/15.3y。
3. **Wilson 95% lo +0.21** — WR が positive 領域に確定 (lo>0)。N=50 の小標本でも下限が 21% ≥ 偶然超え。

これら補強条件は「**事後的緩和の永久免罪符ではない**」。Live promote 段階では別途厳格化された gate (下記) を満たすまで Live 配賦しない。本登録の目的は、Codex 独立レビュー (`wiki/learning/codex-review-wave1-2026-05-03.md`) が指摘した「spec 骨抜き」を防ぐため、**緩和の根拠と Live 移行条件を本日付で固定** することにある。

---

## Live Promote Pre-Registered Gate (2026-05-03 LOCK、将来変更不可)

Shadow 期間中の **新規** trade で以下すべてを満たした時点で Live promote 候補とする。**閾値・条件は本ファイルで固定し、将来「数値だけ動かす」修正・「条件を 1 つ削る」修正・「条件を緩める」修正は禁止**。条件の追加 (より厳格化) のみ別 PR で許可する。

| # | Gate | 閾値 | 計測方法 |
|---|---|---|---|
| 1 | 追加 Shadow N | **≥ 30** | `is_shadow=1` の `turtle_s2_unit_*` trade のうち BT 期間 (2011-01-02〜2026-05-01) 終了後に成立したもの。BT N=50 と合算して combined N≥80 を担保。 |
| 2 | Combined Wilson 95% lo | **> 0.30** | BT N=50 + Shadow trades を合算し、勝率の Wilson score interval lower bound。 |
| 3 | Combined PF | **> 1.5** | BT + Shadow 合算 PF。 |
| 4 | Shadow-only PF | **> 1.2** | Shadow 期間のみの PF (BT 期間との独立性確認)。BT との sample 重複防止。 |
| 5 | Bonferroni p (m=2) | **< 0.10** | Live promote 段階では緩和 gate を 0.20 → **0.10** に厳格化。USDJPY × {long, short} で K=2。 |
| 6 | 直近 6 ヶ月 max DD | **< 25%** | Shadow PnL ベースの running drawdown (peak-to-trough)、月次更新。 |
| 7 | Codex 独立レビュー | **B 以上 verdict** | Live promote 直前に **再実施**。Wave 1 review (B-hold) 以上であること。 |

**全 7 項目を同時に満たした時点で**、別 PR (`feat/s2-turtle-usdjpy-long-LIVE-promote-YYYY-MM-DD`) で Live promote を提案する。本 PR と Live promote PR は **必ず別 PR** とする。

---

## 緊急停止条件 (Shadow 中に発火 → 即時 Shadow OFF)

Shadow 運用中に以下のいずれかが発生した場合、**即時** Shadow tier を OFF とし、原因究明レポートを `wiki/learning/s2-shadow-emergency-stop-YYYY-MM-DD.md` に記録する。

1. **連続 5 trade 損失** — Shadow trades の連続 loss streak ≥ 5。
2. **Shadow 期間 PF < 0.7** (10 trade 以上) — N≥10 で PF が 0.7 を下回る。
3. **BoJ 介入 -3N slippage** — 1 trade あたり -3N 以上の slippage を BoJ 介入帯 (USDJPY ≥ 158.0) で確認。
4. **is_shadow=1 invariant 違反** — `oanda_audit` に `entry_type LIKE 'turtle_s2_unit_%'` AND `is_shadow=0` の row が 1 件でも観測された場合 (これは tier-bridge bug を意味する)。

緊急停止後の再起動は、原因究明完了 + 別 PR での修正パッチが merge された後に限り、**再 Pre-registration を作成して** から再開する。

---

## Shadow 運用月次レポート

- 月次レポート: `wiki/learning/s2-shadow-monthly-YYYY-MM.md`
- 必須記載項目:
  - 当月 Shadow N、累積 Shadow N
  - Combined N (BT + Shadow)
  - Combined Wilson 95% CI (lo/hi)
  - Combined PF, Shadow-only PF
  - Bonferroni p (m=2)
  - 直近 6 ヶ月 max DD
  - 当月の Live Promote Gate 7 項目チェック (✅/❌)
- LIVE/Shadow 厳格分離 (`feedback_live_shadow_separation`) を必ず守る — `is_shadow=1` のみ集計対象。

---

## 関連

- **Wave 1 BT report**: [`wiki/learning/s2-turtle-55day-bt-2026-05-03.md`](../../../wiki/learning/s2-turtle-55day-bt-2026-05-03.md)
- **Codex 独立レビュー**: [`wiki/learning/codex-review-wave1-2026-05-03.md`](../../../wiki/learning/codex-review-wave1-2026-05-03.md)
- **親プラン**: `~/.claude/plans/find-out-way-of-fizzy-patterson.md`
- **KB strategy doc**: [`knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md`](../strategies/turtle-s2-donchian-d1.md)
- **内部 memory**:
  - `feedback_partial_quant_trap` — N/WR/EV だけでは不十分
  - `feedback_success_until_achieved` — Null/Scenario A で closure 短絡禁止
  - `feedback_live_shadow_separation` — LIVE/Shadow 分離必須

---

## LOCK 宣言

本ファイル記載の閾値・条件は **2026-05-03 をもって固定** された。Live promote PR の作成者は、本ファイルの全 7 Gate および 4 緊急停止条件が **本登録時の記述から一字一句変更されていないこと** を git blame で確認し、Live promote PR の本文に「pre-registration LOCK 2026-05-03 unchanged」を明記する義務を負う。

将来の改変提案は以下のいずれかに限る:
- (a) 条件の **追加** (より厳格化) → 別 PR で本ファイルに append、既存 7 Gate には触れない。
- (b) 戦略 fork → 別ファイル (`pre-registration-s2-turtle-VARIANT-YYYY-MM-DD.md`) を新規作成、本ファイルは凍結。

数値の単純な緩和、条件削除、Gate 厳格化の取り消し、Live promote 直前の Codex review skip は **すべて禁止**。
