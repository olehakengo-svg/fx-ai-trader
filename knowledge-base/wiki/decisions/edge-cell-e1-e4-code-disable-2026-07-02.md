# Edge Cell E1/E4 code-level DISABLE + watchdog DECREMENT 床バグ修正 (2026-07-02)

**Rule**: E1/E4 pin = R2 (損失停止・KV再武装への止血)。watchdog 修正 = R3 (構造バグ、コード導出で即断)。
**発端**: [[bb-rsi-t10-kill-2026-07-02]] 拘束事項3「E1/E4 cell filter (stage=0) の掃除」の実装タスク。着手時の本番検証で **T10 KILL 済み bb_rsi_reversion が E4 経由で live 発火中** であることを発見し、単なる掃除から live-bleed 止血に昇格。

## 発見: E4 zombie 再武装 incident (2026-07-02)

### 事実 (本番 /api/demo/trades 12,005行 + Render request logs)
- E4 (bb_rsi_reversion NY SELL, **symbol 制約なし**) は 2026-06-04 CB で KV `edge_cell_stage:E4=0`。以降 06-05〜07-01 の live 発火ゼロ (disable 有効)。
- 2026-07-02 10:18Z、watchdog cron に API_AUTH_TOKEN が投入され (session Phase 5)、約5週間ぶりに POST /api/admin/edge_cell/state が 200 で通り始めた (UA: edge-cell-watchdog/2.0、15分毎 GET+POST を Render logs で確認)。
- **最初の有効 POST (10:18:22Z) が E4 を 0→1 に再武装**。E4 は NY セッションセルのため、NY 開始直後の **13:08:30 UTC から live 再発火** — NY セッション終了までに**計 11 件** (13:08〜19:55 UTC, 全て USD_JPY, oanda_trade_id あり)。net +9.0pip (7W4L) だが結果オーライに過ぎない — T10 確定の EV 負戦略の無許可 live 発火であり、DD 98% 下の資本露出。
- watchdog は「降格専用」のはずが再武装した。手動で 0 に戻しても 15 分後の次回実行で再度 1 になる自己持続ループ (zombie)。

### 根本原因: DECREMENT 床バグ (tools/edge_cell_watchdog.py)
```python
"new_stage": max(1, stage - 1)   # 旧コード — 床が 1
```
stage=0 のセルが DECREMENT 判定を受けると `max(1, -1) = 1` に**昇格**する。E4 の LOCK (05-26) 以降 live 実績は N=23 / WR 39.1% / EV -0.50p / PF 0.68 — **WR>28% かつ EV>-1.0 で両 DISABLE ゲートをすり抜け、PF<1 で DECREMENT に落ちる「ポケット」**にちょうど嵌まる。この組合せでは KV をどの値にしても watchdog が毎実行 stage=1 に戻すため、**KV ベースの disable は構造的に無効**。

### Blast radius (全12セル再計算, LOCK 05-26 以降 live CLOSED)
| cell | N | WR | EV | PF | 旧コードの帰結 |
|---|---|---|---|---|---|
| **E4** | 23→34 | 39.1% | -0.50 | 0.68 | **DECREMENT → 0→1 再武装 (本 incident, 発見時点 N=23 → NY 終了まで live 11 発追加)** |
| E10 | 10 | 20.0% | -5.93 | 0.07 | DISABLE 側 (0→0, 無害) + 既に code pin 済み |
| E8 | 8 | 37.5% | -3.51 | 0.10 | N<10 → HOLD (code pin 済みで新規 live 蓄積なし) |
| E1 / E12 他 | ≤4 | - | - | - | N<10 → HOLD (現時点は非該当、バグは潜在) |

E4 が唯一の現行該当だが、「stage=0 + 歴史的 N≥10 PF<1」を満たす将来の任意のセルで再発するため源泉修正が必須。

## 対処 (同一コミット)

1. **E4/E1 を `DISABLED_CELLS` に追加** (modules/edge_cell_promote.py, rule:R2) — force-live は `get_cell_lot()>0` ゲートのため、KV / watchdog / admin API がどの stage を書いても lot=0 が確定。E4 = T10 KILL 拘束事項3。E1 (dt_bb_rsi_mr ASN SELL, 同じく 06-04 CB で stage=0、LOCK 以降 live N=0) は同族セルの予防 pin。dt_bb_rsi_mr の通常 PAIR_PROMOTED USD_JPY live 経路には影響しない (E1 はクロスペア ASN force-live のみ)。
2. **watchdog DECREMENT 床バグ修正** (tools/edge_cell_watchdog.py, rule:R3) — DECREMENT は stage>=2 のときのみ `stage-1` を発行。stage<=1 は action なし (stage 1 は旧来も no-op、stage 0 は絶対に上げない)。DISABLE (0) 発行は不変。回帰テスト: tests/test_edge_cell_watchdog_decrement_floor.py (4件)。
3. **依存テスト付け替え**: R2/SAME_PRICE/slot bypass 機構検証は E4 → active cell E3 (dt_bb_rsi_mr EUR_USD SELL) へ。現行 registry には「SHADOW_RETIRED/demoted かつ active cell」の実在組合せが無いため、R2 bypass 経路は registry 合成 (monkeypatch) で維持。E4/E1 側は disabled 挙動固定テストを新設 (E8/E10 と同パターン)。

## 判明した KB 上の不整合 (記録)

- **T10 拘束事項2「Shadow 収集は継続」は現行実装と不一致**: bb_rsi_reversion は 2026-06-12 の `SHADOW_RETIRED_STRATEGIES` (shadow_demote_registry.py) で shadow row も全ペア停止済み (最終 shadow row は 2026-06-04 USD_CHF)。本タスクは挙動変更なし原則により復活させない。復活には registry 解除の別判断 (T10 再評価トリガー: スプレッド構造の恒常的低下 or regime 転換のみ) が必要。→ [[bb-rsi-t10-kill-2026-07-02]] に補記済み。
- bb_rsi.py の env レバー (`BB_RSI_REVERSION_PAIR_WHITELIST_V1` / `BB_RSI_REDESIGN_V2(_SHADOW_PROMOTE)`) は調査の結果 **撤去せず残置**: whitelist は封じ込め現役 (E4→USD_CHF 漏れの教訓)、REDESIGN_V2 は default-off だが本番 env の設定状態を外部から検証できず (Render env 読取ツールなし)、撤去は「挙動変更なし」を証明できない。SHADOW_PROMOTE 経路は retirement により consumer (`[R2_SHADOW_DEMOTE] skipped shadow_emit`) で不達なことをコード確認済み。撤去は本番 env 目視確認とセットの別タスク。

## bb_rsi_reversion の最終状態 (本コミット後)

候補生成 (score race 参加) のみ。row 経路: live=なし (E4 pin)、shadow=なし (06-12 retirement)、loser shadow_emit=なし (同)。**OANDA 到達経路ゼロ**。再評価は T10 拘束事項の R1 トリガーのみ。

## 再有効化条件 (R1)

E1/E4 とも: Shadow Wilson_lo >= 0.55 (WILSON_LO_THRESHOLD) + pre-reg LOCK + `DISABLED_CELLS` からの明示除去 (コードレビュー必須)。E4 は加えて T10 KILL の再評価トリガー成立が前提 (セル分割・フィルタ再生の再試行は禁止クラス)。

## 追記 2026-07-03: KV 残置 stage の自動同期 (CODE_PIN_SYNC, rule:R3)

incident の再武装で E4 の KV `edge_cell_stage:E4` は **1 のまま残置**されていた —
床バグ修正後の watchdog は DECREMENT を stage>=2 にしか発行しないため自然回復しない
(07-03 10:48Z run の cron ログで確認: E4 のみ stage=1、verdict=DECREMENT/PF_BELOW_1
が毎 run 空転。E1/E8/E10 は KV=0 同期済み)。code pin が SSOT のため実害ゼロだが、
「eligible と effective を区別する」教訓に反する認知負債。

**対処**: watchdog に CODE_PIN_SYNC を実装 — `CODE_PINNED_CELLS` (DISABLED_CELLS の
ミラー定数。watchdog は cron で stdlib-only 実行のため modules/ を import できず、
CI の equality テストで乖離を固定) の cell が KV stage!=0 なら new_stage=0 を発行。
一度同期すれば以後 no-op (self-quiescing)。今後 pin cell の KV がどの経路で汚れても
15 分以内に自動同期される恒久対応。pin cell は metric 判定 (DISABLE/DECREMENT) より
前に short-circuit し、sync と喧嘩する action を出さない。
admin API 直叩き (POST + EDGE_CELL_ADMIN_TOKEN) は session の permission 制約で
不可だったため、cron が自身の credential で同期するこの経路を選択。
テスト: tests/test_edge_cell_watchdog_code_pin_sync.py (5件)。

- [ ] デプロイ後の初回 watchdog run で `applied: E4 S1 -> S0` を確認したら本行を更新

## 教訓

- **「降格専用」ツールの clamp 境界は昇格方向に漏れる**。`max(floor, x-1)` の floor が「現在より上」になり得る入力域 (x < floor) を必ず確認する。単調性 (new_stage <= stage) を不変条件としてテストで固定した。
- **token/credential 投入は「休眠していた書込み経路の一斉開通」**。5週間死んでいた watchdog の復旧 (良い変更) が、潜伏していた床バグを同時に開通させた。credential 投入時は「その経路が書く先の全アクション」を再監査する。
- disable の SSOT を KV に置く設計は、KV に書ける他プロセスが存在する限り pin にならない。不可逆 disable は code-level (`DISABLED_CELLS`) で。

**関連**: [[bb-rsi-t10-kill-2026-07-02]] / [[edge-cell-e8-demote-2026-06-25]] / [[live-bleeder-demotions-2026-07-02]] / [[edge-cells-stage3-wilson-lo-restoration-2026-06-07]]
