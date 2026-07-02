# Fable 5 大規模システム監査 (2026-07-02)

**実施**: Claude Fable 5 / 並列監査エージェント6体 (コア取引経路・リスク/Kelly・BTパリティ・Edgeパイプライン・DB/SSOT・インフラ衛生) + Semgrep + 主要クレームの手動裏取り
**状況**: DD=98.2% (過去最高) defensive mode 0.2x 稼働中 / branch `research/h4-level-edge` に E8止血の未コミット変更あり
**目的**: 全バグ・問題点の抽出と、改善作業を進めやすい優先度付きバックログ化

---

## サマリー

| 優先度 | 件数 | 内容 |
|---|---|---|
| **P0** (資金直結) | 2 | DD防御バイパス / 孤児クローズ年齢チェック欠如 |
| **P1** (統計判断・データ汚染) | 8 | Kelly汚染 / BT水増し残存 / restart毎is_shadow再汚染 / E8止血の不完全 / CI穴 ほか |
| **P2** (堅牢性) | 9 | silent except 資金経路 / env汚染 / 依存未ピン ほか |
| **P3** (軽微) | 6 | 破損wikilink 182件 / デッドテスト / 未追跡ハーネス ほか |

全件、担当エージェントの報告後に主要項目はコード直読で裏取り済み (CONFIRMED 表記)。

---

## P0 — 資金直結 (即時判断が必要)

### P0-1: Edge cell force-live 経路が DD defensive 0.2x を完全バイパス 【CONFIRMED / rule:R3 候補】
- **場所**: `modules/demo_trader.py:6103, 6170`
- **証拠**: 通常経路は `_eq_mult = self._dd_lot_mult` → `_boost_factor` → `_lot_ratio` で DD 係数が乗算されるが、`_edge_cell_force_live` 時は `_adjusted_units = _edge_cell_lot` の生値代入 (LADDER_LOTS 5000/7500/10000)。以降 `_dd_lot_mult` の再乗算なし (grep 確認済)。後段は SHIELD `_OANDA_LOT_CAP` のみ。
- **影響**: DD=98.2% の現況でも E1〜E12 マッチトレードは 5000〜10000u をフルサイズ送信。**最も資金が枯渇している局面で最大ロットが飛ぶ**。
- **備考**: SHIELD mode / aggregate Kelly gate のバイパスはテスト (`test_edge_cell_shield_oanda_mode_bypass.py` 等) で設計として固定されている。DD 係数バイパスが同じ「設計」なのか漏れなのかの判断が必要。テストは `trader._dd_lot_mult = 1.0` を明示セットしており defensive 時の挙動を検証していない。
- **修正案**: `_adjusted_units = int(_edge_cell_lot * self._dd_lot_mult)` (最低単位丸め維持) + defensive mode 時 units のテスト追加。

### P0-2: `_sync_demo_to_oanda` 孤児クローズに年齢/猶予チェックなし 【CONFIRMED】
- **場所**: `modules/demo_trader.py:2120-2166` (5秒毎に `_sltp_loop` から実行、起動ウォームアップなし)
- **証拠**: OANDA 側 open trade のうち `demo_trades.oanda_trade_id` + in-memory `_trade_map` に無いものを即 `close_trade()`。`openTime` チェックなし。
- **影響**: fire-and-forget の fill→DB write-back 完了前に**プロセス再起動/デプロイ**が挟まると、正規の live ポジションを再起動後 ~5 秒で強制クローズ。`pending_oanda_ops` の復旧機構がこの判定に伝播していない。テストカバレッジゼロ (裏取り済)。
- **修正案**: `openTime` が 5-10 分未満の trade はスキップ (既存の `_resend_pending_oanda_trades` / `recover_pending_ops` の 5 分カットオフと同パターン) + `pending_oanda_ops` の in-flight 照合。

---

## P1 — 統計判断・データ汚染

### P1-1: `_get_strategy_kelly` に FIDELITY_CUTOFF / XAU 除外がない 【CONFIRMED】
- **場所**: `modules/demo_trader.py:8677-8703`。呼び出し: line 5696 (Kelly 動的 boost) / 5721 (half-Kelly lot cap) — **実弾サイジングの中核2経路**。
- **証拠**: 姉妹関数 `_get_aggregate_kelly` / `_get_strategy_kelly_clean` は cutoff + XAU 除外あり。この関数だけ漏れ。CLAUDE.md「all-time data を Kelly に使わない」に直接抵触。
- **修正案**: 呼び出し元を `_get_strategy_kelly_clean` に差し替え (instrument 引数の扱い要確認) or 同一フィルタ追加。

### P1-2: BE/Trail 同一バー楽観バイアス修正が daytrade エンジンのみ。scalp/1H×2 に残存 【R3】
- **場所**: `app.py:6019-6134` (`run_scalp_backtest`), `app.py:5443-5489` (`run_backtest` 1H), `app.py:7405-7449+` (`run_1h_backtest`)
- **証拠**: `run_daytrade_backtest` には `_BT_ABLATE_BE_TRAIL` (デフォルト off, 「+22.9pp inflate」コメント付) が実装済 (app.py:6440-6452)。同一構造のコードが上記3エンジンでは無ガードで稼働。同一バー内で favorable→adverse の順序を常に仮定 (BE 発動後に同バーの逆行 SL を tightened stop で判定 → 本来 LOSS のバーが WIN 化)。
- **影響**: MEMORY 確定事実「BE/Trail が Python BT WR を TV 比 +20pp 水増し」の発生源が3エンジンに残存。これら由来の EV/WR を昇格判断に使うと誤判定。
- **修正案**: 3エンジンに同じ ablation ガードを適用 (診断済み・修正実績ありのため R3 扱いで即修正可)。
- **付随 (P2)**: 同一バー TP+SL 同時ヒットの tie-break が `fut_close` 基準 (保守的 SL 優先でない) — 全エンジン共通の副次的楽観バイアス。

### P1-3: stale な v9.x SHADOW_MIGRATION が restart 毎に is_shadow を再汚染 【CONFIRMED】
- **場所**: `modules/demo_db.py:473-533`
- **証拠**: `_init_tables()` 内で毎起動、ハードコード `_force_demoted` 集合 (**現役の `dt_bb_rsi_mr`=edge cell E1/E3/E5/E7/E11、`bb_squeeze_breakout`=PAIR_PROMOTED を含む**) に対し `is_shadow=0→1` を一括 UPDATE。冪等マーカーなし、`oanda_trade_id` 安全チェックなし、全体が `except Exception: pass`。後続の drift backfill が `oanda_trade_id` 保持行を復元するため大半は自己修復するが、fill callback 喪失行は shadow に固定され Kelly/WR 集計から消える。
- **修正案**: 後継の `_backfill_force_demoted_leak_impl` (動的リスト+冪等+安全チェック) が存在するため、このブロックは削除。

### P1-4: E8 止血 (未コミット) が不完全 — fallback は Shadow でなく Sentinel LIVE、かつ無タグ化 【CONFIRMED】
- **場所**: `modules/edge_cell_promote.py` (DISABLED_CELLS) + `modules/demo_trader.py:5548-5560`
- **証拠**: (a) `session_time_bias` は `_UNIVERSAL_SENTINEL` 所属 → lot=0 で force-live が外れても Sentinel 1000u の**実弾**にフォールバック (コメントの「base tier=shadow」は誤り)。5000u→1000u の 5x 削減にはなるが止血未完 (Live EV=-3.51p の戦略が縮小継続)。(b) `_edge_cell_id` は `lot>0` 時のみセット → E8 残存トレードは `edge_cell_id=""` で記録され、`edge_cell_watchdog` の per-cell 監視が**盲目化**。「shadow N 蓄積で再昇格判定」も対象母集団が存在せず機能しない。(c) 参照先 decision doc `edge-cell-e8-demote-2026-06-25.md` が存在しない。(d) **7テスト/6ファイルが red** (`pytest -x` では1件しか見えない)。pre-commit が full pytest のため `--no-verify` 誘発状態。
- **修正案**: ① タグ付けを eligibility (match) 基準に変更し force-live のみ lot>0 で gate ② 真に Shadow 化するなら `SHADOW_DEMOTED_CELLS` に `("session_time_bias","EUR_USD")` 追加 ③ E8 依存 e2e を E3 等へ付替 or DISABLED を monkeypatch ④ decision doc 作成 → 全部まとめて R2 止血コミットを完結。

### P1-5: DD% ダッシュボード分母がハードコード 1000 【要実測確認】
- **場所**: `app.py:14878` vs `modules/demo_trader.py:794-795` (`OANDA_EQ_BASE_PIPS` env、コメント例 4548)
- **影響**: 本番 env が 1000 以外なら、**表示上の DD=98.2% と実際に lot 縮小を駆動している DD% が別物**。defensive mode の妥当性判断自体が誤った数値に基づく可能性。→ Render env の `OANDA_EQ_BASE_PIPS` 実値確認が先決。
- **修正案**: 分母を共有ヘルパーに統一。

### P1-6: `_resend_pending_oanda_trades` の再送ガードが FORCE/PAIR_DEMOTED のみ
- **場所**: `modules/demo_trader.py:1174-1232`
- **影響**: Q4/Kelly/MC-ruin/SHIELD を再チェックせず再送。現状は insert 時 `enforce_oanda_live_invariant` で守られているが、`is_shadow` 反転バグ1つで直通する defense-in-depth 欠如。
- **修正案**: 再送前に promote gate 共通ヘルパーを再実行。

### P1-7: 品質ゲートの構造的穴 — CI path filter / hip1 holdout ガード未実行 / `--no-verify` 常用
- **証拠**: ① `ci.yml` push trigger の `paths` が `tests/`, `tools/`, `agents/`, `knowledge-base/` を除外 (PR は無条件)。② `.git/hooks/pre-commit` はカスタムスクリプト symlink で pre-commit フレームワーク (`hip1-holdout-manifest`) を**どこも実行していない** — HIP-1 holdout 改変ガードが実質ゼロ。③ `agents/cma/dev.agent.yaml` の `--no-verify` 必須ルールの根拠「hip1 が full pytest を走らせる」は**誤認** (full pytest はカスタムスクリプト側、hip1 自体は数秒)。
- **影響**: holdout 検証の統計的独立性主張が監査不能。CMA agent + 直接 push でテスト変更が無検証で main に入る経路。
- **修正案**: hip1 チェックを CI job 化 (数秒) / paths filter 撤廃 / dev.agent.yaml の記述訂正。

### P1-8: scalp BT の QUALIFIED_TYPES 同期に機械的保証なし
- **証拠**: `mtf_trend_follow_scalp` / `mtf_counter_trend_scalp` / `mtf_regime_trend_cascade_scalp` は本番 enabled だが `run_scalp_backtest` 内 inline set (app.py:5865-5902) に不在 (vec harness 必須のため意図的の可能性が高いが未文書化)。`scripts/check.py` はこの inline set を検査しない。
- **修正案**: 意図的除外の文書化 + check.py に drift 検査追加 (DT_QUALIFIED の step 4 と同型)。

---

## P2 — 堅牢性

| # | 場所 | 内容 | 修正方針 |
|---|---|---|---|
| P2-1 | `risk_analytics.py:391-406` | DD_LOT_TIERS が DD≥8% で一律 0.20x、DD 100% 超でもフルストップなし (`_check_drawdown` 側の別ゲート未検証) | DD≥閾値で lot=0 tier 追加を検討 |
| P2-2 | `demo_trader.py:8604` | cell_routing BLOCK 判定が silent fail-open — routing 破損時 BLOCK セルが無音発火 | fail-open 維持でも初回 WARN 必須 |
| P2-3 | `demo_db.py:532,558` | SHADOW_MIGRATION/DRIFT_BACKFILL の失敗が silent — Live/Shadow 分離修復の故障が検知不能 | WARN ログ追加 (P1-3 の削除で 532 は消滅) |
| P2-4 | `demo_trader.py:3770,6614` | entry/close の bid/ask 取得失敗が silent でステール価格へ | WARN + 摩擦忠実性カウンタ |
| P2-5 | tools/ 77ファイル/215箇所 | モジュールトップ `os.environ` 代入 (明文化ルール違反)。conftest の autouse fixture が対症療法中 | `tools/bt_common.py` へ集約 + check.py に lint |
| P2-6 | `agents/cma/worker.py:33` | `unrestricted_paths=True` が6/18から未コミット稼働 (リスク評価自体は妥当) | rationale 付きコミット |
| P2-7 | `requirements.txt` | 全15依存 `>=` レンジ、lockfile なし。ローカル py3.9 vs CI py3.11 乖離 | pandas/numpy/scipy 上限ピン or lockfile |
| P2-8 | `edge_cell_promote.py:121` | `LADDER_LOTS.get(stage, 5000)` fail-open — 不正 stage 値で最大ロット (現状 API 検証で到達不能) | default を 0 (fail-closed) へ |
| P2-9 | `edge_cell_promote.py:113` | 死んだ `kv_get` fallback (コードベースに未定義) | `get_system_kv` 直呼びへ |

補足: modules/ の silent except 全87箇所 (demo_trader 39 / demo_db 28)、tools/ 64箇所。大半は良性 (ALTER TABLE イディオム等)。**一括修正は不要** — 上記の資金/分離経路4箇所に限定するのが低リスク。

## P3 — 軽微

- 破損 wikilink 182件 / Edge Stage 不整合1件 (london-fix-reversal) / index 未リンク1件 (check.py 出力)
- `tests/test_session_mr_cross_audit.py` — un-merged refactor 依存の恒久 skip (デッドテスト)
- 未追跡ファイル4点 (`tools/zigzag_swing_ic_explore.py`, `session_bias_explore.py`, `limit_fill_predictor.py`, `agents/cma/redesign_2026-06-22/`) — falsified ハーネス流用資産がマシン喪失で消えるリスク
- flake8 が requirements にあるが CI 未実行
- `demo_trader.py:7054` strategy N cache の永続化失敗 silent (deploy 跨ぎで昇格カウンタ巻き戻り)
- `candidate_logger.py` の raw connection (busy_timeout なし) — 観測テーブル限定なので許容

## 問題なしと確認された項目 (再監査不要)

- `set_oanda_trade_id` の同一 statement 更新 (oanda_trade_id + is_shadow=0) — SSOT 修正は健在
- 新系統 backfill 3種 (dedup/force_demoted_leak/flag_drift) の冪等マーカー + 安全チェック
- `_safe_conn` (WAL + busy_timeout + liveness check) / OandaBridge のロック規律 / dedup gate の共有
- Kelly 学習系の is_shadow 除外 (`get_all_closed` / `get_trades_for_learning` / exposure_manager)
- Wilson/kelly_criterion の数式・ゼロ除算防御 / learning_engine の cutoff 適用
- BT の friction 値 ⇄ wiki テーブル整合 / エントリーの next-bar open (シグナル lookahead なし) / SR・HTF キャッシュの forward-leak なし
- spread_gate は動的閾値のみ (4原則整合) / シークレット平文なし (ids.env は gitignore + ID のみ)
- Semgrep 6件は全て parameterized placeholder の誤検知

---

## 改善ロードマップ (推奨実行順)

**Phase A — 即時 (R2/R3、365日BT不要の構造バグ)**
1. E8 止血の完結: タグ付け修正 + Shadow 化判断 + テスト7件修復 + decision doc → **1コミットで R2 完結** (P1-4)
2. DD 0.2x の edge cell 適用 (P0-1) — 「設計かバグか」の user 判断1点のみ挟む
3. 孤児クローズ年齢チェック (P0-2)
4. `_get_strategy_kelly` cutoff 統一 (P1-1)
5. `OANDA_EQ_BASE_PIPS` 本番実値確認 → DD 98.2% の真偽確定 (P1-5)

**Phase B — 今週中 (統計インフラ)**
6. BE/Trail ablation を scalp/1H×2 エンジンへ展開 (P1-2, R3)
7. stale SHADOW_MIGRATION ブロック削除 (P1-3)
8. CI: hip1 job 追加 + paths filter 撤廃 + dev.agent.yaml 訂正 (P1-7)
9. 再送ガード共通化 (P1-6) / scalp QUALIFIED_TYPES check (P1-8)

**Phase C — 順次 (衛生)**
10. 資金経路 silent except 4箇所に WARN (P2-2/3/4)
11. fail-closed 化 (P2-8) + dead code 除去 (P2-9) + worker.py コミット (P2-6)
12. tools/ env 集約 + lint (P2-5) / 依存ピン (P2-7) / P3 一掃

**進め方**: Phase A は全て「診断済み構造バグ」で R3/R2 該当 — 365日BT不要、ただし各修正に回帰テストを同コミットで付ける。Phase B 6 (BT修正) 後は既存 BT 結果の再解釈が必要になる点に注意 (scalp 系の過去 verdict は水増し込み)。
