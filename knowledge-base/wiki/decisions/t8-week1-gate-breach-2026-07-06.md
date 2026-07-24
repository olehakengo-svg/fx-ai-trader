# T8 初週監視: pre-reg 拘束ゲート抵触 — R2 停止発動記録 (2026-07-06)

**Pre-reg**: [[sweep-hull-live-week1-prereg-2026-06-12]] (🔒 LOCKED, 発動 = R2 即時・裁量禁止)
**検証**: 2026-07-06 本番実測 (Render logs 30d + /api/demo/trades date_from=2026-06-12 全2,495行 + block-counts)

## 判定

### sweep_reversion_eurgbp_late (EUR_GBP) — ゲート① 下側抵触 (確定)
- live fill = 0 / shadow row = 0、**06-12 LIVE 化から 24 日間ゼロ** (期待 0.9件/週 → 3.4週で ~3.0件、実測 0 = 下限 0.3件/週 割れ)
- 原因特定済み: emit 4件/20日 (band 内 = 戦略ロジックは正常) が **HTF hard gate で 100% silent drop** (07-02 診断 app.py:2628 に明記)。移植バグ系 = ゲート①の想定シナリオ
- ゲート② (spread): fill 0 で実測不能。代理: 他戦略 EUR_GBP LATE 窓 entry N=1 で spread 5.0p > 3.5p (弱証拠、要監視)

### hull_donchian_fade (EUR_USD M15) — ゲート④ 該当 (候補層検出)
- 07-06 02:01-02:16Z: **同一 M15 バー内で 30 秒毎に再 emit** (~55行、2 mode スレッド)。初回は session_pair(Tokyo,WR20%) block、以降 recent_emit(<900s) が全吸収
- DB dedup_violation = 0、live 到達ゼロ (多層防御は機能)。ただし pre-reg ゲート④は「runaway パターン (同一バー複数 emit) を 1 件でも検出 — 即停止 + forensic」であり裁量禁止
- 参考: shadow 全履歴 5件/24日 ≈ 1.5/週 vs 期待 13.3/週 = 既に >3× 下側 (ゲート①も初週確定時に割れる見込み)
- ゲート③ (PnL): N/A (fill 0)。spread: shadow 実測 0.8p = BT 前提内

## 発動アクション (pre-reg 規定)

両戦略の **LIVE 転送停止 (Shadow は原則3で継続)**:
- `HULL_DONCHIAN_FADE_LIVE_ENABLE=0` (現 =1, 読取: modules/demo_trader.py:8423)
- `SWEEP_REVERSION_EURGBP_LIVE_ENABLE=0` (`SWEEP_REVERSION_EURGBP_ENABLE` は emit 全体の gate なので触らない)

**執行状態 2026-07-06 (更新)**: user 承認後、env 経路は権限層で通らず → **code pin で執行** (lesson「KV disable は pin にならない、不可逆化は code で」準拠):
`modules/demo_trader.py` の `_HULL_DONCHIAN_FADE_LIVE_ENABLE` / `_SWEEP_REVERSION_EURGBP_LIVE_ENABLE` を `False` 固定 + 回帰テスト
`tests/test_t8_week1_r2_stop_code_pin.py` (env=1 でも eligible=False を固定)。復帰はこのテストの変更を伴う PR のみ = レビュー必須。
env 2 キーは無参照化 (dashboard 削除は cosmetic、BB_RSI 2 キーと同時で可)。

## Forensic 起票 (audit-index 行き)

1. sweep: HTF hard gate live exemption (P-S1(a)) を認めるか、retire するか — **R1 user 決裁** (live 経路の filter 変更のため)
2. hull: 同一バー再 emit が「hull 固有の closed-bar/dedup 欠如」か「全戦略共通の poll 挙動」かの層別突合 → 固有なら strategy 内 dedup 追加 (R3)、共通なら pre-reg ゲート④の定義を order 層に補正して再 LOCK
   - **実装完了 2026-07-06 (R3)**: 共通 poll 挙動として order 層に per-bar dedup を追加。primary `_tick_entry` と `shadow_emit` DB insert path が `(entry_type, instrument, signal, closed_bar_ts)` を共有し、block_counts は `order_bar_dedup` で観測可能。`recent_emit` は併存。
3. 12y BT 同条件突合 (発火ログ × BT bar): 次セッション以降、両戦略とも emit→fill 変換率を BT 側と比較

## 関連発見 (同日)

- T7: QUALBAR `logger.info` は本番不可視 (handler 未設定) — fix PR 提出済み ([[rnb-wait-entry-zero-forensic-2026-07-06]] 同梱)。**T8 の週次レビューも logging 経由テレメトリに依存しないこと**


---

## Forensic #2 結果 (2026-07-06 同日): hull 同一バー再emit = 全戦略共通挙動

**Verdict: 共通** (hull 固有ではない) — ただし当初想定と根本原因が異なる。

- hull_donchian_fade は closed-bar guard (`closed_idx=-2`) と per-bar dedup (`_last_emit_bar_ts`, instance dict) を**正しく実装している** (strategies/daytrade/hull_donchian_fade.py:80, 131-139)
- しかし `compute_daytrade_signal` が **poll 毎 (30秒毎) に `DaytradeEngine()` を再構築** (app.py L2597 相当) するため、strategy instance の dedup 状態は毎 tick 消滅 → per-bar dedup は live で一度も効かない。**HourlyEngine も同型** (app.py:4520) — carry dip の 12h cooldown も live 無効
- つまり **全 daytrade/hourly 戦略の instance-state ベース guard (per-bar dedup / multi-bar cooldown) は live でデッドコード**。live の dedup 層は recent_emit (tf-aware 900s/3600s) のみ。07-06 02:01-02:16Z の hull ~55 行 (2 mode スレッド × 30 秒 poll) はこれで完全に説明がつく
- **BT 側との突合は未了** (forensic #3 と統合): BT ハーネスが engine を bar 跨ぎで永続させる場合、BT は cooldown/dedup を執行し live は執行しない = BT/Live 構造乖離 (EV/頻度両方に影響)。sweep の 12-bar cooldown が 12y grid BT で効いていたかは要確認
- **pre-reg ゲート④ の帰結**: 「共通なら order 層に補正して再 LOCK」の分岐を適用。**order 層 per-bar dedup (key=entry_type×instrument×signal×bar_ts) は実装済み** (PR #49 fix/order-layer-bar-dedup-20260706、task 記録 = `.ai/tasks/done/20260706-1600-order-layer-bar-dedup.md`, R3 構造 fix)。ゲート④ 定義の order 層への補正 + 再 LOCK は **user R1 決裁待ち**


---

## 裁定 (2026-07-06 追記, user 包括指示「全て進めてください」による)

### Forensic #1 sweep P-S1(a): **DEFER** (機械的決定点を pre-reg 化)

07-01 以降の HTF shadow rescue 実測 N=0 (期待 ~0.9件/週 band 内だが証拠ゼロ)。R1 の live filter 変更 (HTF exemption) は新証拠なしでは付与できない。retire は不可逆でこれも根拠不足。よって:
- **現状維持**: LIVE code pin OFF 継続 + HTF_BLOCK_SHADOW_RESCUE で shadow N 蓄積継続 (原則3、コストゼロ)
- **決定点 (機械的、裁量禁止)**:
  1. HTF-rescued shadow N≥10 到達 → その EV/WR/PF で exemption (EV>0) or retire (EV≤0) を判定 (R1、user 決裁)
  2. **2026-09-30 までに shadow N<5** → 発火頻度が 12y 検証時 band を持続的に割っている = live 翻訳失敗として **retire** (R2)
- 監視主体: pre-reg trigger monitor (2026-07-06 導入、tools/prereg_trigger_watch 参照) に登録
  - ⚠️ 2026-07-24 判明: この監視は limit=800 truncation で N=0 誤報告中 (実測 unique N=8/row N=14)。修正前は 09-30 retire 分岐を執行しないこと。決裁パケット: [[sweep-reversion-ps1a-decision-packet-DRAFT]] §1.5
- **復帰の追加前提 (forensic #3, 2026-07-06)**: N≥10 EV>0 でも、再有効化には **order 層での 12-bar min-spacing 実装が必須** — 検証済み N=543 は grid ハーネスが 12-bar dedup を一括執行した estimand であり、本番経路はこれを執行しない (per-bar dedup PR #49 では不足)。spacing なしの再有効化 = 検証と別物の運用

### ゲート④ 再定義 (🔒 LOCKED — 2026-07-06 発効)

Forensic #2 の verdict (共通挙動、instance-state guard は live 無効) を受け、pre-reg ゲート④を以下に補正した:

> **ゲート④ (改)**: 「order 層 (demo_trader signal 受理点) で同一 (entry_type, instrument, signal, bar_ts) の DB insert が 2 件以上検出された場合 — 即停止 + forensic」。strategy 内部の re-emit は監視対象から除外 (engine 再構築による全戦略共通挙動であり、多層防御の内側で吸収される限り異常ではない)。

- **発効条件 (成立済み)**: order 層 per-bar dedup (`20260706-1600-order-layer-bar-dedup`) が main に到達し、`order_bar_dedup` block counter が観測可能になった時点
- **発効判定 (2026-07-06)**: PR #49 (`fix/order-layer-bar-dedup-20260706`) が **commit dc17eb64 で main 到達**、本番デプロイで order dedup 08:14 UTC live 確認済み ([[2026-07-06-session]] Phase 4)。→ **発効条件成立、本セクションを 🔒 LOCKED に確定** (発動 = R2 即時・裁量禁止、解除はこのセクションの変更を伴う PR = レビュー必須)
- **承認記録**: user 指示 2026-07-06「全て進めてください」→ ゲート④(改) 定義を承認。発効化は handoff タスク (`fx-roadmap-v23-handoff`, 2026-07-06) で執行
- hull の復帰: ゲート④(改) 発効後、hull は「order 層 dedup 下で 1 バー 1 emit」が構造保証されるため、ゲート④抵触は解消扱い。ただし復帰自体はゲート① (発火頻度 band、shadow 実測 1.5/週 vs 期待 13.3/週で既に下側割れ見込み) の再評価が別途必要 — 頻度 band 割れが確定した場合は sweep と同じ retire 経路


---

## Forensic #3 結果 (2026-07-06 同日): BT 側 cooldown 執行の突合

- **汎用 BT (app.py backtest_daytrade) は live と対称**: BT ループ (app.py L6527) も bar 毎に `compute_daytrade_signal` → `DaytradeEngine()` 再構築 (L2597)。instance-state cooldown は **BT でも執行されない** → 「BT だけ cooldown が効き live で効かない」仮説は棄却 (forensic #2 の未確定事項を解消)
- **真の estimand 不一致 = 検証ハーネス vs 本番経路 (sweep)**: N=543 を出した 12y grid (`tools/research_sweep_reversion_grid_12y.py` L140-173) は strategy class を使わず inline 実装で、`dedup_indices(ev, DEDUP_GAP=12)` を bar 配列全体に一括適用 — **12-bar spacing は検証済みエッジの定義の一部**。本番経路 (live / 汎用 BT とも) はこれを執行しない。sweep を spacing なしで再有効化すると、ゲート① (HTF gate 未検証) と同型の「検証と運用の estimand 不一致」を別軸で再演することになる
- **hull**: inter-bar cooldown なしの設計 (per-bar dedup のみ)。検証 (外部 1m validation、holdout N=1,833/4y ≈ 8.8/週) と本番で spacing 前提の不一致なし。頻度 band 割れ (shadow 実測 1.5/週) は独立の問題として残存
- その他の既知乖離源: `closed_idx` BT=-1 vs live=-2 の 1-bar タイミングシフト / BT ループ内 session filter (EUR_GBP 全停止・EUR_USD 時間帯 gate)
- **帰結**: (1) sweep 復帰条件に 12-bar min-spacing 実装を追加 (上記 DEFER 裁定に反映済み)。(2) multi-bar cooldown の order 層実装は「sweep を復帰させる場合のみ」必要 — 現状 code pin OFF のため新規実装は保留。(3) emit→fill 変換率の実測突合は shadow N 蓄積待ち (現状 N=0 で比較不能)
