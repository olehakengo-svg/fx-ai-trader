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
- **pre-reg ゲート④ の帰結**: 「共通なら order 層に補正して再 LOCK」の分岐を適用。**order 層 per-bar dedup (key=entry_type×instrument×signal×bar_ts) の実装タスクを queue 投入済み** (`.ai/tasks/queue/20260706-1600-order-layer-bar-dedup.md`, R3 構造 fix)。ゲート④ 定義の order 層への補正 + 再 LOCK は **user R1 決裁待ち**


---

## 裁定 (2026-07-06 追記, user 包括指示「全て進めてください」による)

### Forensic #1 sweep P-S1(a): **DEFER** (機械的決定点を pre-reg 化)

07-01 以降の HTF shadow rescue 実測 N=0 (期待 ~0.9件/週 band 内だが証拠ゼロ)。R1 の live filter 変更 (HTF exemption) は新証拠なしでは付与できない。retire は不可逆でこれも根拠不足。よって:
- **現状維持**: LIVE code pin OFF 継続 + HTF_BLOCK_SHADOW_RESCUE で shadow N 蓄積継続 (原則3、コストゼロ)
- **決定点 (機械的、裁量禁止)**:
  1. HTF-rescued shadow N≥10 到達 → その EV/WR/PF で exemption (EV>0) or retire (EV≤0) を判定 (R1、user 決裁)
  2. **2026-09-30 までに shadow N<5** → 発火頻度が 12y 検証時 band を持続的に割っている = live 翻訳失敗として **retire** (R2)
- 監視主体: pre-reg trigger monitor (2026-07-06 導入、tools/prereg_trigger_watch 参照) に登録

### ゲート④ 再定義 (再 LOCK 案 — 発効条件付き)

Forensic #2 の verdict (共通挙動、instance-state guard は live 無効) を受け、pre-reg ゲート④を以下に補正する:

> **ゲート④ (改)**: 「order 層 (demo_trader signal 受理点) で同一 (entry_type, instrument, signal, bar_ts) の DB insert が 2 件以上検出された場合 — 即停止 + forensic」。strategy 内部の re-emit は監視対象から除外 (engine 再構築による全戦略共通挙動であり、多層防御の内側で吸収される限り異常ではない)。

- **発効条件**: order 層 per-bar dedup (`20260706-1600-order-layer-bar-dedup`) が main に到達し、`order_bar_dedup` block counter が観測可能になった時点
- **承認記録**: user 指示 2026-07-06「全て進めてください」。発効時に本セクションを LOCKED に更新し、hull 復帰判断の前提とする
- hull の復帰: ゲート④(改) 発効後、hull は「order 層 dedup 下で 1 バー 1 emit」が構造保証されるため、ゲート④抵触は解消扱い。ただし復帰自体はゲート① (発火頻度 band、shadow 実測 1.5/週 vs 期待 13.3/週で既に下側割れ見込み) の再評価が別途必要 — 頻度 band 割れが確定した場合は sweep と同じ retire 経路
