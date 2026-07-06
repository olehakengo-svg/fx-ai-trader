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
