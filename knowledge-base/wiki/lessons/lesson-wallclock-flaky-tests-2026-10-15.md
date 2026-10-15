# Lesson: 「CI flaky」と呼んでいた失敗は壁時計とプロセス共有状態に決定論的だった (2026-10-15)

**発見日**: 2026-10-15 | **rule**: R3 | **PR**: autopilot 2026-10-15 (branch `autopilot/registry-due-2026-10-15`)

## 何が起きたか

main の CI `test` job が 2026-10-14T22:45Z 〜 10-15T03:13Z の 12 run 中 **5 回失敗**した。10-13 のセッション記録と
MEMORY は「`test_bt_htf_m15_m5_inject` / `test_api_oanda_stats_range` が assert 0 == 1 で落ちる = flaky、
push し直せば通る」と書いており、rerun で済ませる運用が 2 日続いていた。

失敗した run の **時刻と test 名を並べる**と、ランダムではなく 3 つの決定論的な原因に分かれた:

| 失敗 run (UTC) | test | 真因 |
|---|---|---|
| 10-14 22:45 / 23:54 | `test_dt_ctx_hour_utc_live[3]` (ctx None) | `compute_daytrade_signal(bar_time=None)` の Layer 0 `is_trade_prohibited` が **壁時計 now(UTC)** で評価され、22:00–23:59 は深夜禁止 → engine 前に WAIT 早期 return。test は engine 到達を前提にしていた。`-x` なので最初の param (hour=3) だけが見える |
| 10-15 00:17 / 00:22 | `test_api_oanda_stats_range` (`today["total"]` 0 == 1) | test の today 行 = `now − 1h` が **00:00–00:59 UTC の run で前日**に落ちる。`range=today` は UTC 当日 00:00 以降 |
| 10-15 03:13 | `test_win_side_exit_decomposition::test_freeze_dir…` (`startswith` 不成立) | 昨日 (PR #328) 入れた `main()` の `contextlib.redirect_stdout` が **プロセス全体の sys.stdout** を差し替え、先行 test が起動した demo_trader の daemon MainLoop の `[MainLoop/scalp] tick #1 ok (0.8s) pid=2385` が report.md の先頭に混入 |
| 10-13 (PR #326 CI / main ×3) | `test_bt_htf_m15_m5_inject::…reuses_cached…` (counted 0 == 1) | cache key が `(id(df), len, index[0], index[-1])` = **オブジェクト id を同一性の代理**にしており、先行 test の同形 df が GC された後に id が再利用されると cache hit して counted が呼ばれない (メモリアロケータ依存 = 非決定的に見える) |

## なぜ見逃したか

- 「flaky」というラベルを付けた時点で**原因調査が止まった**。失敗の時刻分布 (22–00 時台に集中) を見れば壁時計依存は一目で分かったが、誰も時刻を並べなかった
- rerun で通る = 修正不要、と解釈した。壁時計依存のテストは**特定の時刻帯の push が全部落ちる**ので「通るまで push」は夜間の autopilot / cloud job で高コスト
- 自分で入れた pin (`startswith`) が自分の `redirect_stdout` を検知したケースも、レビュー 4 巡を経て合格した直後の main で落ちた — **pytest の同一プロセスに daemon スレッドが生き残る**ことを前提にしていなかった

## 修正 (本 PR)

1. `tools/win_side_exit_decomposition.py`: `_run(args, out=None)` が report 本文を明示ストリームにだけ書く (`functools.partial(print, file=out)`)。`main()` から `redirect_stdout` を撤廃。pin: 本体実行中に第三者が sys.stdout に書いた行は report.md に入らず通常 stdout へ出る (反事実: 旧ツール + 新 pin = FAIL を確認)
2. `tests/test_api_oanda_stats_range.py`: today 行を `max(now − 1h, 当日 00:00:01)` に固定 (UTC 同日を assert)
3. `tests/test_dt_ctx_hour_utc_live.py`: `_capture_dt_ctx` で `app.is_trade_prohibited` を壁時計非依存の stub に差し替え (estimand は ctx.hour_utc の追従であって layer0 ではない)。壁時計 22:45 固定の再現で engine 到達 (hour_utc=3) を確認
4. `tests/test_bt_htf_m15_m5_inject.py`: test 開始時に `app._bt_scalp_mtf_precompute_cache.clear()` で前提を固定

BT 本体側の id(df) 再利用ハザード (同形 df を別内容で作り直す経路があれば古い特徴量を黙って再利用) は registry
`bt-scalp-mtf-cache-key-id-reuse-r3` (期日 2026-10-29) で別途裁定する。

## 教訓

1. **「flaky」は診断ではなくラベル**。失敗 run の **UTC 時刻 × test 名** を表にしてから呼べ — 時刻帯に集中していれば壁時計、同一プロセス順序に依存していれば共有状態 (cache / daemon スレッド / グローバル stdout)
2. **test の時刻は壁時計から作らない**。`now − Δ` で「今日」を作ると日付境界で落ちる。境界が仕様 (UTC 00:00) なら境界を跨がない値を明示して assert する
3. **プロセス共有状態を差し替える API (`redirect_stdout` / 環境変数 / モジュール cache) を本体コードで使わない**。他スレッドの出力を拾う・他 test の状態を引き継ぐ。本体は明示ストリーム / 明示 cache を受け取る設計にし、test は前提を自分で固定する
4. 同型の兄弟を同じ PR で grep する ([[lesson-defect-family-sweep-siblings-2026-09-17]]): 本件は 1 件の調査が 4 件に広がった。`compute_daytrade_signal` を呼ぶ他の test 2 本 (`test_streak_reversal_htf_soft_penalty` / `test_vwap_mean_reversion_shadow_redesign_v2`) は `bar_time=df.index[-1]` を渡す BT 経路で、前者は `is_trade_prohibited` も自前で stub 済み (影響なし)

## 関連

- [[lesson-import-time-env-pollution-2026-05-13]] (pytest プロセス内の環境汚染、同型)
- [[lesson-defect-family-sweep-siblings-2026-09-17]]
- MEMORY `project_autopilot_2026_10_13_pr326_asof_and_readouts` の「CI は flaky、push し直せば通る」は本 lesson で**撤回**
