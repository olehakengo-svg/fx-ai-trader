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
  - modules/demo_trader.py L3129-3173 (MAX_HOLD_SEC / _ENTRY_TYPE_MAX_HOLD) / L3135 (_is_pre_weekend) / L3702-3728 (適用箇所) / L3328-3372 (ATR BE 0.8 / trail 1.5→0.5) / L3732-3766 (TIME_DECAY_EXIT 半分時点) / L8439-8572 (_check_signal_reverse)
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

# live exit スタック (全部入れる — PR #299 review P1 2 巡目 4100301156)

live の `daytrade` 建玉に掛かる exit は 8h cap と金曜クローズだけではない。**以下 6 経路すべて**を BT に
入れないと「live 制約付き」を名乗れない (`modules/demo_trader.py` の行番号は 2026-09-25 origin/main):

| # | 経路 | 仕様 (live 実装) | 出典 |
|---|---|---|---|
| C1 | MAX_HOLD | entry から **28,800s (8h)** 超で成行決済 `MAX_HOLD_TIME` | L3130 / L3705-3728 |
| C2 | 金曜クローズ | 金曜 **21:45Z 以降**の最初の tick で全建玉成行決済 | L3135 / L3702 |
| C3 | ATR BE | MFE が **entry ATR × 0.8** 到達で SL → 建値 (+spread) | L3328-3340 (共通建値ガード) |
| C4 | ATR trail | MFE が **entry ATR × 1.5** 到達後、SL = price − **ATR × 0.5** で追随 (BUY) | L3358-3372 |
| C5 | TIME_DECAY_EXIT (C1 半分時点損切り) | hold > **14,400s (4h = 8h × 0.5)** かつ含み損なら成行決済 | L3732-3766 (kalman は免除リストに無い) |
| C6 | SIGNAL_REVERSE | hold ≥ **600s** 後、反対方向シグナルが confidence ≥ `confidence_threshold + 10` (下限 50) で成行決済 | L8439-8572 `_check_signal_reverse` |

- ATR の定義は live と同じもの (entry 時点の `_entry_atr`、14 期間 15m を確認して記載)。
- C6 の「反対方向シグナル」= 本戦略の PO-DN 側 flip か、同 mode の他戦略シグナルか — live では **同 mode で評価される全戦略の
  反対シグナル**が対象 (kalman 固有ではない)。TV で完全再現は不可能なので、**C6 は「PO 崩れ (close < EMA25 or EMA25 < EMA75) で成行」
  を下限近似**とし、近似であることを結果表に明記する。
- ⚠️ 前版の「Python fallback では BE/Trail を無効化」は**撤回** — 無効化すると live と別の exit 分布になる。

# 実行手順

1. **eval canon = TV Pine** (MEMORY feedback_tv_edge_discovery_loop: Live > TV > Python BT)。strategy card の Signal Logic / Exit Logic
   (TP 5.0×ATR / SL 1.5×ATR) を実装した Pine に C1〜C6 を**累積**で足し、同期間 (2025-07-01→2026-05-19、USDJPY M15) で走らせる:
   - 走 0: 制約なし (現行 BT の再現 — N=46 / WR 23.91% / PF 3.866 に一致することを先に確認 = harness 検証)
   - 走 1: +C1 ／ 走 2: +C1+C2 ／ 走 3: +C1+C2+C3+C4 ／ 走 4: +C5 ／ 走 5: +C6 (= **full live stack**)
   - 累積にする理由: どの overlay が EV を削るかを分解する (処置 (b) Rule 1 packet を書く場合の根拠になる)
2. TV が使えない場合は Python port で同じ 6 走 (⚠️ Python BT は容疑者。走 0 が TV の N / WR / PF を ±10% で再現できなければ
   結果を採用しない。BE/Trail は **無効化せず C3/C4 として実装**)。
3. **摩擦調整**: USD_JPY RT friction 2.14pip (wiki/analyses/friction-analysis.md) を 1 トレード当たり差し引く。
4. 出力: 走 0〜5 の N / WR / PF / EV (pips、摩擦調整後) / Wilson 95% lower / exit 種別比率 (TP / SL / MAX_HOLD_TIME / 金曜 /
   BE / trail / TIME_DECAY / SIGNAL_REVERSE)。走 0 の **winner hold 分布 (bars in trade) と 8h 以内に完結した winner の割合**を明記
   (「制約 EV が正に残る余地」の直接指標)。
5. KB: `knowledge-base/wiki/analyses/kalman-d7-live-constrained-bt-2026-10.md` に結果 + 分岐判定。strategy card 09-24 節 /
   registry entry に結果リンク。**R2 降格の判定が出ても執行は Claude が別 PR**。

# 分岐の非対称 (凍結)

- **走 5 (full stack) の摩擦調整 EV ≤ 0 → R2 shadow 降格** (autopilot 執行可)
- **走 5 の EV > 0 → live 維持 + 参照 BT を走 5 に差し替え** — ただし **C1〜C6 のいずれかが再現できていない (近似のまま) 場合、
  「維持」の分岐は取れない**。不完全なシミュレーションが正当化できるのは保守側 (降格) だけで、live が産めない exit 分布で
  live を維持する判断はしない (PR #299 review P1)。その場合は「判定保留 + 未再現 overlay の列挙」を書き、Claude が処置を再起案
- 走 1〜4 の中間結果は分解の参考であり、**分岐判定には走 5 のみ**を使う

# 禁止事項

- 制約付き BT の EV が負でも**制約を外す方向の live 変更 (override 120h / 週末保持) を提案・実装しない** (Rule 1、user 決裁)
- パラメータ (TP 5.0×ATR / SL 1.5×ATR / filters) の再最適化禁止 (カーブフィッティング禁止。制約 2 つを足すだけ)
- 走 0 が現行 BT を再現できないまま制約付きの数字を出さない (harness 未検証の数字は引用禁止)
- overlay を一部省いた走の EV > 0 を「維持」の根拠にしない (上記 分岐の非対称)

# 完了条件

- 走 0〜5 の表 + hold 分布 + exit 種別比率 + 分岐判定が analyses/ に保存され、done ファイルに '## Claude Review' が付く
