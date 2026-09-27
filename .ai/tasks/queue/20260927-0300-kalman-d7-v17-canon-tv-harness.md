---
id: 20260927-0300-kalman-d7-v17-canon-tv-harness
title: "[M1 clean live] kalman_d7_po_dn_flip — v17 canon Pine の再構築 + TV 同 feed で走 0 harness を閉じ、制約付き走 (C0〜C6) を Pine 側で再現する"
owner: unclaimed (対話セッション限定 — TV desktop 起動 = user 操作が前提。autopilot は着手不可)
status: queued
created_at: 2026-09-27T03:00:00+0900
priority: P1
deadline: 2026-10-08 (registry `kalman-d7-live-exit-spec-mismatch-disposition`) — 期日までに閉じなければ packet は「harness 未検証・順位のみ」で組む (前タスク done ファイル参照)
roadmap_gate: "M1 (clean live 月次符号転換)。前タスク 20260925-0300 (Python port、done 2026-09-27) は走 0 harness が Massive データで FAIL (flip 変種 N 60 / PF 2.27 vs canon 46 / 3.866、flip 定義 5 候補すべて ±10% 外)。制約付き走の数値を packet で引用可にする唯一の経路 = TV canon の再走"
rule: R3 (計測のみ。tier / lot / live 配線 / パラメータ再最適化は範囲外。宣言保持の live 導入は Rule 1 = user 決裁)
prereq_artifacts:
  - .ai/tasks/done/20260925-0300-kalman-d7-live-constrained-bt.md (実行結果 + Claude Review)
  - knowledge-base/wiki/analyses/kalman-d7-live-constrained-bt-2026-09-27.md (§0 算術 / §1 harness FAIL / §4 packet 所見)
  - tools/kalman_d7_live_constrained_bt.py (Python 側の C0〜C6 実装 = Pine へ移す仕様の SSOT、定数は live コードの写し)
  - bt-results/tv-overlays/kalman_d7_v18e_usdjpy_live_BACKUP.pine (entry ロジックの Pine 実体。exit だけが v17 と違う)
  - knowledge-base/wiki/strategies/kalman-d7-po-dn-flip.md (BT Performance / 09-27 節)
---

# 目的 (1タスク1目的)

前タスクで **canon の exit は PO-DN flip (aggregate payoff 12.3×、winner ~458 bars) であって宣言 TP 5×ATR ではない可能性が高い**
ことが aggregate payoff の算術から示唆された (analyses §0 — ⚠️ 確定ではない: ATR の entry 間異質性と 480 bars cap の早期クローズ loser
があれば固定 TP/SL でも 3.33× を超え得る、PR #302 review P1。**確定は本タスクの手順 1 で winner ごとの entry ATR / exit 種別を読む**)。しかし v17 Pine はリポジトリに無く (TV slot は 2026-05-21 上書き)、Massive データの Python port では flip 定義 5 候補の
いずれも canon (N=46 / WR 23.91% / PF 3.866 / avg winner bars 458) を ±10% で再現できなかった。
本タスクは **TV desktop (OANDA feed) 上で v17 canon を再構築して走 0 を一致させ、その Pine に C0〜C6 を累積で足して**
制約付き走を「harness 検証済み」の状態にする。packet 10-08 の (a) 再定義 (flip exit + SL 1.5×ATR + 市場 bar 480 本) の根拠数値になる。

# 前提 (autopilot 不可の理由)

- `tv_health_check` は CDP 接続を要求 = TradingView desktop が起動していること。自走 (scheduled) セッションでは起動しない
  (2026-09-27 実測: `CDP connection failed`)。**対話セッションで user に TV 起動を依頼してから着手**
- TV 側で v17 のオリジナルが `pine_list_scripts` に残っているか先に確認する (残っていれば再構築不要、`pine_get_source` で
  取得して `bt-results/tv-overlays/kalman_d7_v17_usdjpy_po_dn_flip.pine` に BACKUP する — v18e BACKUP と同じ形式)

# 実行手順

1. `pine_list_scripts` → v17 (po_dn_flip) の有無。有: 取得・BACKUP・`data_get_strategy_results` で N/WR/PF/avg bars を読み、
   カード値と一致することを確認 (= 走 0 canon 確定)。無: v18e BACKUP の entry ブロックを流用し、exit を候補 5 種
   (`perfect_dn` / `not perfect_up` / `close < ema75` / `close < ema200` / `ema25 < ema75`) × SL 1.5×ATR × 480 bars cap で
   走らせ、**カード値に ±10% で一致する定義だけ**を canon とする (一致が無ければ「canon 再現不能」で終了し packet にそう書く。
   定義の探索は canon の同定であり exit の最適化ではない — entry / SL / cap は不変)
2. canon Pine に C0〜C6 を累積で足す (`tools/kalman_d7_live_constrained_bt.py` の定数・順序をそのまま Pine へ)。
   走 0′ (C0 近似: ATR×1.0 / clamp / lowliq / rn / broker 0.85 / MTF 1.0 と 1.3 の 2 値) → 走 1 (+8h) → 走 2 (+金曜 21:45Z)
   → 走 3 (+BE 0.8 / trail 1.5→0.5) → 走 4 (+4h 含み損) → 走 5 (+C6 PO 崩れ近似、参考値)。
   Pine は bar 内順序を自動で決めないので、`strategy.exit` の stop/limit 同時ヒット既定 (保守側) を「adverse_first 相当」と明記し、
   favorable_first は Python 側の値を併記する
3. 摩擦 2.14 pip/trade を commission で近似 (`commission_type=strategy.commission.cash_per_order` 等) か、結果に事後差し引き
4. 出力: 走 0〜5 の N / WR / PF / EV (net) / exit 種別 / winner・loser 別 bars 分布 / winner の 8h 内完結率 を
   `knowledge-base/wiki/analyses/kalman-d7-live-constrained-bt-2026-09-27.md` の §2 に「TV 検証済み」列として追記し、
   Python 側との差 (ベンダー差) を記録。JSON は `raw/bt-results/kalman_d7_live_constrained_bt_tv_<date>.json`
5. registry `kalman-d7-live-exit-spec-mismatch-disposition` message 追記 + カード 09-27 節に「harness 検証済み」へ更新

# 判定の扱い (前タスクから継承、凍結)

- 本タスクの数字から keep / demote を決めない。C6 は BT 再現不能 (サロゲート参考値)。走 0′〜4 は「C0 近似 + intrabar 順序近似」
- autopilot が単独で取れる処置は通常の live 損失停止規律 (Rule 2、realized N ベース) のみ

# 禁止事項

- 制約を外す方向の live 変更 (市場 bar 数 override / 週末保持 / exempt 登録 / BE・trail 免除) を提案・実装しない (Rule 1、user 決裁)
- TP/SL/filter の再最適化禁止。flip 定義の同定は「カード値 ±10% 一致」だけを基準にし、EV で選ばない
- 走 0 が一致しないまま制約付きの数字を「検証済み」と書かない

# 完了条件

- 走 0 がカード値に ±10% で一致 (or 「再現不能」の確定) + 走 0′〜5 の表 (両順序仮定) + winner/loser 別分布 + 8h 内完結率 が
  analyses 頁に「TV 検証済み」ラベルで保存され、done ファイルに '## Claude Review' が付く
