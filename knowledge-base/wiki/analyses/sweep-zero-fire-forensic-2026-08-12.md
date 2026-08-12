---
title: sweep_reversion_eurgbp_late 28日 zero-fire forensic — gbp_asia gate の rowless drop で P-S1(a) トリガ分母が silent 枯渇
date: 2026-08-12
type: analysis
rule: R3
status: 確定 (記録経路の修復のみ実施、live 変更なし、トリガ解釈は user 決裁待ち)
related: [[../decisions/sweep-reversion-ps1a-execution-runbook-2026-07-31]], [[../decisions/sweep-reversion-ps1a-decision-packet-DRAFT]], [[shadow-accumulation-blockage-diagnosis-2026-07-18]]
---

# sweep zero-fire forensic (2026-08-12) — 「発火していないのではなく、行が消されていた」

## 0. サマリ

- 最終 shadow row 2026-07-15 から **28 日間 rows ゼロ** (LOCK Withdrawal trigger 5 の 30 日 forensic 発動 2 日前)。
- **決定論的 replay** (凍結定義を忠実再実装、新鮮 MASSIVE 15m 06-25〜08-12 完備率 97.6%) で検証:
  記録期間の発火 6 日を **6/6 再現**した上で、zero-fire 期間に **4 イベントが発火すべきだった**と確定 —
  07-26(日) / **07-29(水)** / **08-06(木)** / 08-09(日)。07-29 は閾値を 7.1p 下回る sweep + 24.0p reclaim で
  feed 差では説明不能。
- **Render ログで直接確認**: 07-29 と 08-06 の 21:16 UTC 以降、
  `[SENTINEL_BLOCK_DIAG] sweep_reversion_eurgbp_late blocked at: gbp_asia_flash_crash(UTC21)` が反復 —
  **戦略は発火していた**。runbook §2.5 の第3ブロッカー (静的 gbp_asia gate、UTC21-06×GBP) が
  `_block + return` で **DB 行を残さず** 削っていた。
- 日曜 (07-26/08-09) は該当ログ自体ゼロ = market-closed gate で 21 時台の通常 tick が来ない
  (weekend_gap PR #117 の実装コメントと整合)。**日曜 LATE イベントは従来から live で構造的に観測不能**
  (7 月の記録にも日曜ゼロ — 整合)。

## 1. 機序 — なぜ 7 月は記録でき、7/16 以降は消えたか

| 期間 | EUR_GBP HTF regime | 経路 | 帰結 |
|---|---|---|---|
| 07-03〜07-15 | HTF Hard Block 発動 (counter-HTF) | engine で block → **HTF_BLOCK_SHADOW_RESCUE** → shadow row | 8 unique bars 記録 ✅ |
| 07-16〜 | **range 化** (ログ実測 08-06: mtf=range_wide d1=0 h4=1) → HTF block 不発 | primary `_tick_entry` へ → **gbp_asia_flash_crash hard block** | **rowless drop** ❌ |

つまり rescue (原則3 の実装) は HTF gate **だけ**に付いており、同じ cell を 100% 内包する gbp_asia gate には
付いていなかった。regime が変わった瞬間に計数器が壊れる構造 — T8 silent drop (execution-collapse 死類) の再演。
AMENDMENT §2.5 は第3ブロッカーを Option B 執行時の問題として特定済みだったが、**pre-Option-B の
トリガ計数への影響 (regime 依存で分母が消える) は未評価だった**。

## 2. 修復 (本 PR、rule:R3 — live 変更なし)

- `DemoTrader._GBP_ASIA_SHADOW_RESCUE_CELLS = {("sweep_reversion_eurgbp_late", "EUR_GBP")}` —
  gbp_asia gate で当該 cell のみ **shadow 退避 (is_shadow=1、OANDA 送信なし)**。
  HTF_BLOCK_SHADOW_RESCUE と同一の原則3設計。live 例外化は P-S1(a) Option B (user 決裁) のまま不変。
- pin tests `tests/test_gbp_asia_shadow_rescue.py` ×3 (修正前 FAIL → 修正後 PASS を実証済み):
  (1) rescue cell はゾーン内で shadow row + OANDA 送信ゼロ、(2) rescue 集合外 (同戦略×GBP_USD) は
  従来どおり rowless hard block = 防御縮小なし、(3) ゾーン外は gate 非適用。
- **BT 検証 hook への回答**: 本変更はシグナル/パラメータ非接触の記録経路修復。cell の統計根拠は
  pre-reg 済み 12.4y Bonferroni (N=543 / WR 59.7% / +6.22p / t=4.46、m=1728 唯一生存)。
  live リスク増分 = ゼロ (送信経路不変)。

## 3. 再構成台帳 (参考値 — 凍結トリガへの算入は §4 の user 決裁事項)

| 基準 | 記録済み | 消失分 (replay) | 合成 |
|---|---|---|---|
| unique N | 8 | +4 | **12 (≥10)** |
| spaced N (≥3h) | 6 | +4 | 10 |
| spaced EV | +2.47 p/t (net) | +2.87 p/t (gross: +4.1/−4.0/+14.6/−3.2) | ≈ +2.6 p/t (spread 1.5p 控除でも >0) |

## 4. 📋 user 決裁事項 (凍結文言に関わるため自走しない)

1. **トリガ解釈**: (a) 再構成 4 イベントを算入し unique N=12 ≥10 として Option B を即執行 /
   (b) 凍結文言の字義 (DB 行) を維持し、修復後の fresh 蓄積で N=10 到達を待つ (残り 2 イベント、
   直近実レート ~1.5/週 → 目安 1〜2 週)。**推奨 = (b)** — 「事後に計数基準を動かさない」(P-10 型規律)
   を優先。(a) は replay がイベント存在の証拠として十分強い場合の選択肢。
2. **retire 期日 (2026-09-30 N<5)**: 計数器故障期間 (07-16〜08-12、28 日) を期日から除外するか。
   推奨 = 28 日繰り延べ (→ 10-28) を registry `t8-sweep-defer-decision` の resolution 注記で。
3. **日曜イベントの恒久欠測**: 実イベントの ~15-30% が live で構造的に観測不能 (market-closed tick gap)。
   research 頻度帯 (runbook §5 ゲート①' 0.3〜2.6 件/週) の live 翻訳はこの分を割り引く必要 —
   初週再ゲート pre-reg LOCK 時に係数を明記するか。

## 5. 検証ログ

- replay: `fetch_massive_data.py --pair EUR_GBP --tf 15m --days 45` (97.6% 完備) + 凍結定義
  (L=96 / depth 0.05×ATR14 / LATE 21-24 / cooldown 12 bars) の忠実再実装。記録期間 6/6 日一致
  (bar offset 1 本 = live の closed=iloc[-2] 評価による設計どおりのズレ)
- Render logs (srv-d6va1of5r7bs73en10vg): 07-29 21:16:12Z〜 / 08-06 21:16:11Z〜 の
  SENTINEL_BLOCK_DIAG 反復、08-09 21:14-21:40 は EUR_GBP 系ログ皆無
- 本番 rows: `/api/demo/trades` mode=daytrade_eurgbp — sweep 14 rows (8 unique bars) 全て ≤07-15
- コード: `modules/demo_trader.py` gbp_asia gate (v8.6) / `strategies/daytrade/__init__.py`
  HTF_BLOCK_SHADOW_RESCUE / `tools/ps1a_execution_check.py` (verdict WAITING N=8/10、08-12 実測)
