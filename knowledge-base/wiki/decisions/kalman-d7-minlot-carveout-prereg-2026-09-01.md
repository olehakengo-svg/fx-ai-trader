# kalman_d7 min-lot carve-out — pre-reg (2026-09-01, rule:R1 🔒 **LOCKED**)

**status: LOCKED — user 最終承認 2026-09-01 (「承認・マージ GO」)。**

## 問題 (整合性欠陥)
- kalman_d7 live 化は **2026-05-28 user option B 決裁済み** ([[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] §3、**SUCCESS 定義 = `oanda_audit is_live=1 AND bridge_status='filled' COUNT>=1`**)。08-09 PR #168 (R3) で経路開通。
- しかし送信直前の Aggregate Kelly gate (固定 cutoff 2026-04-16 累積、実測 -0.315〜-0.374 で恒久負 — [[shortest-path-decision-memo-2026-07-10]] §1a) に対し、kalman 3 type は
  1. `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` **非所属**
  2. 実効 lot が cascade (`_PAIR_LOT_BOOST` 0.5 × DD 0.2 → floor 0.3 → 3000u) → `OANDA_FORCE_FLAT_UNITS=5000` 上書きで **5000u > bypass 上限 1000u**
  の**二重不適格** → 決裁から 96 日、live fill **ゼロ** ([SHADOW_FIX] shadow 化、直近 14 日だけで 6 件 block をログ確認)。
- gate 衝突は 08-09 設計時に未認識 ([[dt-ctx-hour-utc-live-freeze-2026-08-09]] に言及なし)、初認識 = 2026-09-01 session。
- 07-10 決裁 D4 は carve-out 方式を正式な設計解として拘束: (i) per-cell carve-out 設計 (ii) R2 自動降格ゲート併設。

## 変更内容 (carry_dip と同型の 1000u 固定契約)
| # | 変更 | 箇所 |
|---|---|---|
| 1 | MIN lot 契約: kalman 3 type を cascade/FLAT に関係なく **1000u 固定** (`KALMAN_D7_MIN_UNITS`、`_sentinel_reason=KALMAN_D7_MIN_LOT`) | `_tick_entry` lot 上書き節 |
| 2 | FLAT 上書き遮断: `OANDA_FORCE_FLAT_UNITS` の対象外に kalman 3 type を追加 | FLAT bypass 条件 |
| 3 | `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` に 3 type 追加 (eligible ∧ units≤1000 の二条件は既存関数のまま — lot 昇格で bypass 自動失効) | bypass frozenset |

- instrument 制限 (USD_JPY のみ) は既存 `_kalman_d7_live_eligible` が担保。`_PAIR_LOT_BOOST` の 0.5 エントリは**削除しない** (削除すると sentinel 判定経路が変わる)。
- **リスクは削減方向**: 現行設計の実効 5000u (fill ゼロだが env 事故で発火し得る) → 1000u = テール 1/5。8 月 H1 ATR 中央値 14.5p 基準の SL(1.5×ATR) ≈ ¥217/trade、全敗仮定の月次テール ≈ ¥3,700 (+11〜17 fill/月見込み)。

## エビデンス (BT/実測)
- BT: kalman_d7_po_dn_flip PF=3.866 (v17 max winner ride、QUALIFIED_TYPES 登録時の根拠) — 05-28 pre-reg の裁定済み範囲。**本変更はエッジ主張の変更ではない** (シグナル・SL/TP・発火条件は不変更、lot と gate 所属のみ)。
- shadow 実測 (90d): po_dn_flip 12 行 (~19 件/月ペース)、9W/2L +13.5p — **N 極小の観測値であり判定には使わない**。判定は下記 R2 ゲートが fill 実測で行う。

## R2 自動降格ゲート (D4 必須項目 ii)
- 既存 registry **`t9-kalman-d7-live-n10-ev-check`** を binding として維持: **LIVE N≥10 到達で EV<0 → live 停止 (R2)** / 連続 3 SL → user review。
- deadline 2026-11-30 は backstop として据え置き (carve-out 着地後は ~19 件/月ペースで N=10 到達が先行する見込み)。**初 fill 確認時に deadline を「初 fill + 90 日」へ更新する** — その旨を registry message に本 PR で追記済み。初 fill が 2026-10-15 までに出ない場合は到達性の再監査 (本 pre-reg の検証手順) を先に行う。
- 撤退は env `KALMAN_D7_LIVE_ENABLE=0` のみで即時 (経路全体が env gate 下にあることは既存テストが pin)。

## 検証
- テスト 12 本 (`tests/test_kalman_d7_minlot_carveout.py`): bypass set 所属 / 1000u 通過 / >1000u 自動失効 / override set ⇄ bypass set 完全一致 / MIN_UNITS ≤ bypass 上限の実効性不変条件 / _tick_entry 到達性 pin。
- **counterfactual 実施済み (2026-09-01)**: set から po_dn_flip を外す → 3 本 fail、復元 → 12 本 green。
- デプロイ後の到達性確認手順: ① Render ログで `[SHIELD] ... BYPASS` に kalman が出る ② `oanda_trade_id != ''` の kalman 行の発生 ③ 初 fill で registry 再武装確認。

## user 最終承認で凍結する事項
1. 3 type の bypass set 追加 + 1000u 固定契約 (lot 増額は Live N≥30 の別 R1)
2. R2 ゲートの deadline 再武装 (初 fill + 90 日)
3. 本ドキュメントの DRAFT → LOCK 昇格
