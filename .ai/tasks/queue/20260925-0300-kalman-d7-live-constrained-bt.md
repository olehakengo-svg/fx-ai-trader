---
id: 20260925-0300-kalman-d7-live-constrained-bt
title: "[M1 clean live] kalman_d7_po_dn_flip — live 制約 (hold≤8h + 金曜 21:45Z 強制決済) 付き BT で摩擦調整 EV を再計測"
owner: unclaimed
status: queued
created_at: 2026-09-25T03:00:00+0900
priority: P1
deadline: 2026-10-08 (registry `kalman-d7-live-exit-spec-mismatch-disposition`)
roadmap_gate: "M1 (clean live 月次符号転換)。今月唯一 LIVE 約定している戦略の live 仕様が BT と決定論的に不一致 = live は BT に無い戦略を走らせている状態。EV の符号が出れば R2 降格 / 維持 の分岐が機械的に決まる"
rule: R3 (計測のみ。tier / lot / live 配線の変更は本タスク範囲外。宣言通り保持 (override 120h + 週末保持) の live 導入は Rule 1 = user 決裁)
prereq_artifacts:
  - knowledge-base/wiki/strategies/kalman-d7-po-dn-flip.md (Overview / BT Performance / Exit Logic / 09-24 節「2026-09-25 確定」)
  - knowledge-base/wiki/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md (6. + 2026-09-25 追記)
  - bt-results/tv-overlays/kalman_d7_v18e_usdjpy_live_BACKUP.pine (live 版 Pine の参照。po_dn_flip v17 の canonical Pine は TV 側 — strategy card の Signal Logic / Exit Logic を仕様とする)
  - modules/demo_trader.py L3129-3173 (MAX_HOLD_SEC / _ENTRY_TYPE_MAX_HOLD) / L3135 (_is_pre_weekend) / L3702-3728 (適用箇所)
---

# 目的 (1タスク1目的)

`kalman_d7_po_dn_flip` の **BT (TV Pine、hold 無制限、480 bars ≈ 120h) と live (`daytrade` mode 8h cap
+ 金曜 21:45Z 全建玉クローズ) の仕様不一致**を、**live 制約を BT に入れて**同期間で再計測し、
摩擦調整 EV の符号を出す。分岐は registry entry に凍結済み: **EV ≤ 0 → R2 shadow 降格 / EV > 0 → live 維持 +
参照 BT を制約付きに差し替え**。

# 背景

- 宣言 max hold 480 bars (~120h)、BT edge は winner を ~458 bars (~115h) 保持することに依存 (WR 23.91% / PF 3.866 /
  W/L 12.3×、N=46、2025-07-01→2026-05-19 USDJPY uptrend)。
- live は `MAX_HOLD_SEC["daytrade"]=28800` に override 無し → 8h で `MAX_HOLD_TIME` 強制決済。負け側 (SL 1.5×ATR) は
  8h 内に決着するので**勝ち側だけが打ち切られる** (片側 censoring)。さらに金曜 21:45Z の全クローズで週末を跨げない。
- 実走 3 fill (hold 4h04m / 54m / 58m、1W-2L) はこの上限に触れていないが、N=10 監視では上限の効果は測れない
  (エンジンが産めない結果を測る計画だった — PR #299 review P1)。

# 実行手順

1. **eval canon = TV Pine** (MEMORY feedback_tv_edge_discovery_loop: Live > TV > Python BT)。TradingView MCP が使えるなら
   strategy card の Signal Logic / Exit Logic を実装した Pine に以下 2 制約を追加して同期間 (2025-07-01→2026-05-19、
   USDJPY M15) で走らせる:
   - (C1) `bar_index - entry_bar >= 32` (8h@15m) で成行決済 (`close_reason=MAX_HOLD_TIME` 相当)
   - (C2) 金曜 21:45Z 以降の最初の bar で全建玉成行決済
   - 制約なし (現行 BT の再現、N=46 / WR 23.91% / PF 3.866 に一致することを先に確認 = harness 検証) → C1 のみ → C1+C2 の 3 走
2. TV が使えない場合は Python port で同じ 3 走 (⚠️ Python BT は容疑者。BE/Trail 無しの生 exit で走らせ、
   制約なし走が TV の N / WR / PF を ±10% で再現できなければ結果を採用しない)。
3. **摩擦調整**: USD_JPY RT friction 2.14pip (wiki/analyses/friction-analysis.md) を 1 トレード当たり差し引く。
4. 出力: N / WR / PF / EV (pips、摩擦調整後) / Wilson 95% lower / MAX_HOLD_TIME 決済比率 / 金曜決済比率、3 走の表。
   **hold 分布 (winner の bars in trade) を制約なし走で出し、8h 以内に完結した winner の割合**を明記
   (これが「制約 EV が正に残る余地」の直接指標)。
5. KB: `knowledge-base/wiki/analyses/kalman-d7-live-constrained-bt-2026-10.md` に結果 + 分岐判定 (registry の凍結分岐に
   従い、**R2 降格の場合は判定のみ書き、執行は Claude が別 PR**)。strategy card 09-24 節 / registry entry に結果リンク。

# 禁止事項

- 制約付き BT の EV が負でも**制約を外す方向の live 変更 (override 120h / 週末保持) を提案・実装しない** (Rule 1、user 決裁)
- パラメータ (TP 5.0×ATR / SL 1.5×ATR / filters) の再最適化禁止 (カーブフィッティング禁止。制約 2 つを足すだけ)
- 制約なし走が現行 BT を再現できないまま制約付きの数字を出さない (harness 未検証の数字は引用禁止)

# 完了条件

- 3 走の表 + hold 分布 + 分岐判定が analyses/ に保存され、done ファイルに '## Claude Review' が付く
