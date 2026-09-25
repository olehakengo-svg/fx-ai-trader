# 二重エンジン (gunicorn master + worker) — dup 率実測・LIVE 二重送信評価・単一化設計 (2026-09-24、rule:R3)

> registry `dual-engine-master-worker-disposition` (期日 2026-10-06) の手続き (1)(2)(3) を前倒し執行。
> 母集団: 本番 `/api/demo/trades?status=all&date_from=2026-08-25` (取得 2026-09-24T03:4xZ、1,876 行) / `/api/oanda/audit` (17,734 行のうち直近 2,000) / Render app ログ (srv-d6va1of5r7bs73en10vg)。
> 前身: [[http-blind-fork-poisoning-2026-09-22]] §6 (二重起動の発見)。本稿は **観測と設計のみ** — 単一化 PR は本稿 §5 の手順で別 PR。

## 0. TL;DR

| 問い | 答え | 出所 |
|---|---|---|
| 今も 2 プロセスで走っているか | **はい**。2026-09-24T03:43–03:44Z の同一 instance (`6b67m`) に `[MainLoop] iter=810` / `iter=630` / `iter=840` の **2 カウンタ**、`[MainLoop/daytrade_eurjpy] tick #70` と `tick #50` が **1.0 秒差** | §1 |
| shadow の cross-process dup 率 | 近接ペア (同 type×pair×dir、Δ≤45s) **133 ペア / 30d**、kept 行 1,670 の **8.0%**。全取引日に 3–17 ペアで**恒常** | §2 |
| dedup=0 の N は膨張しているか | **していない**。133 ペア全てで片方が `dedup_violation=1` (両方 0 = **0 ペア**)。write-time フラグ (2026-09-02) が cross-process dup を全件捕捉 | §2 |
| LIVE 二重送信 | **0 件 / 30d**。live 11 行に 120 秒以内の twin なし、audit `sent` 12 / `filled` 11 (差 1 = 09-06 weekend_gap_fade の既知 sent-no-fill)、本日 kalman #893189 も sent 1 / filled 1 | §3 |
| 単一化の regime break (shadow 生成率) | **自然実験で検出されず**: master 単独だった HTTP 全盲窓 (09-15 / 09-22 00:15–03:33Z) の kept 行 **12 / 10 本** vs 二重の平日同窓 **平均 9.75、中央値 10** (20 日、0–17)。⚠️ N=2 日・3h 窓・記述級 | §4 |
| 何を変えたか | row reasons に `[EMIT_PROC] <role>:<origin>` marker (role = import/forked、origin = autostart/statusheal)、stdout ログに `pid=`/`role=`/`origin=`、status に `engine_pid`/`engine_process_role`/`engine_import_pid`/`engine_start_origin` (**record-only、取引挙動不変**) | §5 |
| 単一化の設計 | gunicorn `post_worker_init` hook で autostart (master は import のみ)。deploy 時刻 + marker で層別 | §6 |
| 副産物 | `docs(KB): daily report` commit が `data/monitoring/nav_floor_projection.csv` 経由で**本番を 1 日 4 回再デプロイ** (ignoredPaths 漏れ) → 別 PR | §7 |

## 1. 二重起動の証拠 (現行 instance、2026-09-24)

boot 順序 (2026-09-23T05:28Z、deploy `dep-dapm6d7avr4c73epla70` / PR #295) — Render app ログ:

| UTC | ログ | プロセス |
|---|---|---|
| 05:28:57.798 | `[AutoStart] Waiting 5s for initialization... (PID=64)` | **master** (app.py を import した側) |
| 05:28:58.098 | `[INFO] Booting worker with pid: 131` | worker fork (+0.3 s) |
| 05:29:02–05:29:2x | `[AutoStart] Starting 24 modes` … `→ started` ×24 | master のエンジン |
| 05:29:40.406 | `[StatusHeal] MainLoop dead — restarting` / `Watchdog dead` / `SLTP dead` / `Mode * not running — restarting` ×24 | **worker** (最初の `/api/demo/status` で `get_status()` の self-heal が fork 後の空状態を「死亡」と判定) |

現行 instance (`6b67m`、deploy 03:02Z → `Booting worker with pid: 131` 03:04:12Z) の 03:43–03:44Z:

```
03:43:03.9  [MainLoop] iter=810 ... ticks={'daytrade': 68, ... 'daytrade_eurjpy': 68, ...} restart#0
03:43:38.7  [MainLoop/daytrade_eurjpy] tick #70 ok (0.6s)
03:43:39.8  [MainLoop/daytrade_eurjpy] tick #50 ok (2.5s)      ← 別カウンタ、1.0 秒後
03:43:52.9  [MainLoop] iter=630 ... ticks={'daytrade': 49, ... 'daytrade_eurjpy': 50, ...} restart#0
03:44:26.2  [MainLoop] iter=840 ...                              ← 810 側のカウンタ (+30 iter / 82 s)
```

- `iter` も `tick #` も **2 系列** (810→840 と 630)。`restart#0` が両方に付く = 同一プロセス内の再起動ではない。
- ログに PID が無いため**どの行がどちらか**は本稿時点では特定不能 → §5 の計装で解消。
- `/api/demo/status` の `main_loop_restarts=1` は worker 側の値 (master エンジンは API から不可視)。

### 1b. 計装デプロイ後の実測 (2026-09-24T04:43Z、deploy c5838f6b / PR #296)

計装 (§5) を載せた直後の boot で、二重起動が **PID・role・origin 付きで**確定した:

| UTC | ログ | 帰属 |
|---|---|---|
| 04:43:49.636 | `[AutoStart] Starting 24 modes (pid=62 role=import)` | master (import したプロセス) |
| 04:43:49.636〜 | `[MainLoop] iter=1..5 pid=62 role=import origin=autostart` | master のエンジン |
| 04:45:43.017 | `[StatusHeal] Healed: ['MainLoop', 'Watchdog', 'SLTP', 24 modes] | pid=131 role=forked` | worker (boot +1m54s、最初の status 呼び出し) |
| 04:45:45.016〜 | `[MainLoop] iter=1..150 pid=131 role=forked origin=statusheal` | worker のエンジン |
| 04:46〜04:52 | `iter=30/60/90/120/150/180 pid=62` と `iter=30/60/90/120/150 pid=131` が交互 | **2 系列が同時進行** |

- `/api/demo/status` (04:5xZ): `engine_pid=131` / `engine_import_pid=62` / `engine_process_role=forked` / `engine_start_origin=statusheal` / `main_loop_restarts=1`。**self-check 通過** (`engine_pid != engine_import_pid`) = 「master が import → worker へ fork」トポロジが実測どおり。`/healthz/http` の `serving_pid=131` と一致。
- PR #296 Codex review P1「gunicorn 既定では worker が import する」は本番トポロジでは**成立しない**ことがこれで直接確定 (worker 131 の `_MODULE_IMPORT_PID` は 62 = master)。ただし前提依存の設計リスクへの処方 (origin 軸 + self-check) はそのまま有効。
- 以後の row は `[EMIT_PROC] import:autostart` (master 由来) / `[EMIT_PROC] forked:statusheal` (worker 由来) の 2 値で層別できる。readout (10-01、registry `dual-engine-emit-proc-attribution-readout`) はこの 2 値の比 p_f を読む。

## 2. shadow の cross-process dup 率 (30d、2026-08-26T04:16Z → 09-24T03:37Z)

母集団 1,876 行 = live 11 (`oanda_trade_id` 非空、全て `is_shadow=0`) + shadow 1,865 (全て `is_shadow=1`)。shadow のうち `dedup_violation=1` **195 (10.5%)**、kept (=0) **1,670**。

**近接ペア** = 同 (entry_type, instrument, direction) で連続する 2 行の Δentry_time ≤ 45 s (30 s tick × 2 プロセスの位相差の上界 + 実行時間):

| Δ (s) | ペア数 |
|---|---|
| 0–15 | 68 |
| 15–30 | 40 |
| 30–45 | 25 |
| 45–60 | 7 |
| 60–120 | 5 |
| >120 (600 まで) | 散発 (1–5/15s bin) |

- **Δ≤45 s = 133 ペア**。同一プロセス内は `_maybe_reserve_signal_emit` (60 s 以上の TF 窓) が同 key の再 emit を止めるので、**45 s 以内のペアは cross-process 由来**と読む (in-memory 予約はプロセス境界を越えない — `modules/demo_trader.py` の "(Pre) Cross-thread reservation" コメント / MEMORY `project_engine_reconstruction_live_dedup_dead`)。
- **両方 `dedup_violation=0` のペア = 0**。`DemoDB.open_trade` の write-time cross-process dedup (2026-09-02、共有 SQLite を INSERT 直前に参照) が全件を捕捉している。→ **`dedup_violation=0` で読む N (全 pre-reg / R2 gate / Kelly) は二重エンジンで膨張していない**。
- `dedup_violation=1` 195 行の内訳: 直前 kept 行との Δ ≤45 s **132** / ≤60 s 138 / ≤120 s 141 / **>120 s 54**。後者 54 は同一プロセスの bar 内 re-emit (TF 窓) で、cross-process ではない。
- 日別 (取引日のみ): 08-26 4 / 08-27 9 / 08-28 17 / 08-31 4 / 09-01 3 / 09-02 6 / 09-03 4 / 09-04 5 / 09-07 7 / 09-08 7 / 09-09 9 / 09-10 7 / 09-11 3 / 09-14 7 / 09-15 9 / 09-16 3 / 09-17 4 / 09-18 4 / 09-21 10 / 09-22 7 / 09-23 4 — **全取引日に出現 = 恒常**、特定の boot/heal に依らない。
- mode 別 twin 率 (twin ペア / kept 行): daytrade 36/438 **8.2%** / daytrade_gbpusd 31/267 **11.6%** / daytrade_eur 24/168 **14.3%** / daytrade_eurjpy 12/194 6.2% / daytrade_audjpy 13/160 8.1% / daytrade_gbpjpy 10/120 8.3% / scalp 3/40 7.5% / scalp_eur 1/61 / scalp_5m 系 0–1 / 1h 系 0–1 / rnb_usdjpy 0/2。15m daytrade 系に集中、5m scalp 系はほぼゼロ (5 m 窓の在庫拘束が強い)。
- entry_type 別 dv=1: wick_imbalance_reversion 38 / sr_break_retest 24 / vix_carry_unwind 19 / dt_sr_channel_reversal 16 / sr_anti_hunt_bounce 16 / dt_bb_rsi_mr 16 / sr_weighted_break 9 / sr_weighted_bounce 5。

なぜ 8% しかペアにならないか (= 92% は solo): count ゲート (`max_per_mode_pair` / `hedge_block` / `max_open`) は **DB の `get_open_trades()`** を読むので、片方が INSERT した直後からもう片方は同セルで block される。ペアになるのは**両方が INSERT 前に評価を終えた race 窓**だけ。よって 2 本目のエンジンは「独立にもう 1 セット emit する」のではなく、race に勝った方が row を持つ。これが §4 の自然実験と整合する。

## 3. LIVE 二重送信の評価 — 0 件

| 検査 | 結果 |
|---|---|
| live 11 行 (08-26〜09-24) に対し、同 type×pair×dir で Δ≤120 s の row (shadow 含む) | **0 件** |
| `oanda_audit` 直近 2,000 行 (08-21〜09-24) の `bridge_status` | skipped 1,882 / blocked 95 / **sent 12 / filled 11** |
| sent−filled の差 1 | 2026-09-06T21:01:12 `weekend_gap_fade` USD_JPY (sent、fill なし) = 09-21 から既知の未切り分け事象 ([[2026-09-22-session]] / log.md 09-22)。二重送信ではない (同秒に sent 1 行のみ) |
| 本日 03:37:20Z `kalman_d7_po_dn_flip` USD_JPY BUY #893189 | sent 1 (03:37:22) / filled 1 (03:37:22) |

機構: LIVE 経路は DB-backed の open-trade ゲート + bridge 側 `max_per_mode_pair`/hedge に加え、`open_trade` → OANDA 側で fill されるまで数秒。race 窓 (両プロセスが INSERT 前) で live 適格セルが同時に signal を出す確率は shadow の 8% と同オーダーと見るべきだが、**live 適格セル (kalman ×3 / carry_dip / ps ×5 / wg) は 1h 系 + `_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS`** で発火頻度が低く、30d で 11 本 → 期待 twin ≈ 0.9 本、観測 0 は整合。**「起こり得ない」ではなく「観測されていない」**。単一化 (§6) は LIVE 側でも二重送信の芽を構造的に消す。

## 4. regime break (shadow 生成率) の自然実験

master 単独でエンジンが走った窓 = HTTP 全盲 3 件のうち平日 2 件 (09-15 / 09-22、いずれも 00:15–03:33Z、worker は request を 1 本も完了せず StatusHeal 未発火 — [[http-blind-fork-poisoning-2026-09-22]] §2/§6 証拠 A)。

| 窓 (00:15–03:33Z) | kept shadow 行 | dv=1 |
|---|---|---|
| 09-15 (単独) | **12** | 1 (bar 内 re-emit、Δ>45 s) |
| 09-22 (単独) | **10** | 0 |
| 二重の平日 20 日 | 平均 **9.75** / 中央値 10 / 0–17 | 合計 29 |

- 単独エンジン窓の生成率は二重の分布の中央にあり、**低下の兆候なし**。§2 末尾の機構 (DB-backed ゲートで 2 本目は大半 block) と整合。
- ⚠️ **N=2 日、3 時間、Tokyo 前半のみ、記述級**。30% 未満の差は検出できない。これを「regime break なし」の証明として引用しない — 判定は §5 の marker 読み出し (10-01) と単一化後の before/after 層別で行う。
- 含意: 単一化しても `dedup_violation=0` の N 会計・cadence 前提 (rnb 2.99/週 等) を書き直す必要は**おそらく無い**が、pre-reg 窓を跨ぐ LOCK は deploy 時刻で層別できるようにしておく (§6)。

## 5. 本 PR の計装 (record-only)

| 箇所 | 変更 |
|---|---|
| `modules/demo_trader.py` module | `_MODULE_IMPORT_PID = os.getpid()` を import 時に凍結、`engine_process_role()` = `import` (import したプロセス = gunicorn master) / `forked` (fork 後の子 = worker)、`emit_proc_marker(origin)` = `[EMIT_PROC] <role>:<origin>` |
| 起動経路 (origin) | `_engine_start_origin` = `autostart` (app.py `_auto_start_trader`、モード起動の**前**に刻む) / `statusheal` (`get_status` の MainLoop 再起動分岐) / `unknown`。**role は import 順序の前提 (master が import → fork) に依存するが、origin は「このプロセスのエンジンを誰が起こしたか」の事実**なので、前提が崩れても帰属が黙って壊れない (PR #296 Codex review P1 の消化) |
| 両方の `self._db.open_trade(` call site (shadow 永続化 `_open_shadow_emit_trade` / primary `_tick_entry`) | reasons に marker を 1 個 append (`[SHADOW_BYPASS]` / `[PROMO_BLOCK]` と同型)。**選択条件・gate・dedup では読まない** |
| stdout | `[MainLoop] iter=… pid=… role=…` / `[MainLoop/<mode>] tick #… pid=…` / `[StatusHeal] Healed: … | pid=… role=…` / app.py `[AutoStart] Starting … (pid=… role=…)` |
| `get_status()` | `engine_pid` / `engine_process_role` / `engine_import_pid` / `engine_start_origin` (常に worker 側の値 — master は不可視、という事実自体を露出)。**self-check**: worker で `engine_pid != engine_import_pid` なら「master が import → fork」トポロジが成立 (role 軸が使える)。等しければ worker 自身が import している (gunicorn `--preload` なし等) = role 軸は捨て origin 軸だけで読む |
| pin | `tests/test_dual_engine_process_attribution.py` 17 本 — role 2 値 (**実 fork** で親 import / 子 forked を検査) / marker に PID 桁なし / origin が autostart (モード起動前) と statusheal (MainLoop 再起動分岐) で刻まれる / **call site 2 箇所が対称に append** (片側を外すと 3 本落ちる、counterfactual 実測・sha 一致 restore) / record-only (述語として読まれていない) / ログ 4 行 / status 4 key / 永続 row の reasons に marker (import:unknown・forked:statusheal 両側) |

読み手 (10-01、registry `dual-engine-emit-proc-attribution-readout`):

```
python3 - <<'EOF'
import json,urllib.request,collections
rows=json.load(urllib.request.urlopen("https://fx-ai-trader.onrender.com/api/demo/trades?status=all&limit=20000&date_from=2026-09-24"))["trades"]
c=collections.Counter()
for t in rows:
    if t.get("oanda_trade_id") or t.get("dedup_violation")==1: continue
    r=t.get("reasons"); r=json.loads(r) if isinstance(r,str) else (r or [])
    tag=[x for x in r if str(x).startswith("[EMIT_PROC]")]
    c[tag[0] if tag else "none"]+=1
print(c)   # kept shadow 行の <role>:<origin> / none (marker 前の行)
st=json.load(urllib.request.urlopen("https://fx-ai-trader.onrender.com/api/demo/status"))
print({k:st.get(k) for k in ("engine_pid","engine_import_pid","engine_process_role","engine_start_origin")})
EOF
```

**self-check (先に読む)**: status の `engine_pid != engine_import_pid` ∧ `engine_process_role == forked` ∧ `engine_start_origin == statusheal` なら「master が import → worker へ fork」トポロジが実測どおり (§1)。もし `engine_pid == engine_import_pid` なら worker 自身が import しており、**role 軸 (import/forked) は無効** — origin 軸 (autostart/statusheal) だけで p_f を読む。Render ログの `[MainLoop] iter=` に `pid=` が 2 種類あることも併せて確認する。

判定表: 2 本目のエンジン (role `forked` ≡ origin `statusheal`) の比率 p_f。(a) p_f ≈ 0.5 → 対称 race winner、単一化の生成率影響は §4 どおり小 / (b) p_f ≪ 0.5 (例 <0.2) → worker エンジンは殆ど emit しておらず単一化の影響ほぼゼロ / (c) p_f ≫ 0.5 → master エンジンが劣後 (HTTP 全盲時のみ稼ぐ) — いずれでも**単一化 PR は起案**、違うのは layered N の読み方だけ。

## 6. 単一化の設計 (別 PR、R3 + deploy stamp)

現状: master が app.py を import → `_auto_start_trader` thread が master で 24 mode 起動 → worker は StatusHeal (30 s cadence の self-heal) で 2 セット目。

案 A (推奨): **worker hook で起動、master は import のみ**
1. `gunicorn.conf.py` を追加し `post_worker_init(worker)` で `app._auto_start_trader` を thread 起動。`render.yaml` startCommand に `-c gunicorn.conf.py`。
2. app.py の import 時 autostart は `RENDER` 環境では**起動しない** (`ENGINE_AUTOSTART_IN_IMPORT=0` 既定; ローカル `FORCE_AUTOSTART=1` は従来どおり) — master に thread を一切残さない = [[lesson-prefork-master-must-not-touch-db-2026-09-22]] と同じ原則の完成形。
3. StatusHeal は残す (worker 内の自己修復として本来の役割に戻る)。`/healthz/http` は StatusHeal 非接触のまま。
4. 検証: boot 後 `[AutoStart] Starting … role=forked` が 1 回、`[MainLoop] iter=` の pid が 1 種類、`tick #` が 1 系列。§2 の近接ペア (Δ≤45 s) が翌週 **0** に落ちる (今 8%/日 3–17 ペア → 0 が最強の検証、dv=1 は bar 内 re-emit の >120 s 群のみ残る)。
5. regime break の記録: registry に deploy 時刻 (二次キー) を書き、pre-reg 窓を跨ぐ LOCK (rnb-support-bounce-shadow-forward / ws3-stage2-underpowered-recheck / ws3-t11 / sr-anti-hunt-eurjpy 系) は resolution で before/after N を層別。一次キーは `[EMIT_PROC]` marker (単一化後は全行 `forked`) — [[rnb-shadow-lane-health-precheck-2026-09-22]] の「marker 一次 / deploy 時刻 二次」と同じ規約。

案 B (非推奨): master autostart を止め StatusHeal だけに任せる — 起動が「誰かが status を叩くまで」に依存 (cron 15 分) し、market open 直後の空白が生じる。

user 決裁は不要 (Rule 3 構造バグ、N 会計は §2/§4 で非膨張・非低下を確認済み)。統合決裁パケットには **record** として載せる (D16、返答不要)。

## 7. 副産物 — 日報 commit が本番を 1 日 4 回再デプロイしている

Render deploy 一覧 (09-23T05:27 → 09-24T03:02) の 5 件中 4 件が `docs(KB): daily report YYYY-MM-DD` (00:20Z / 03:02Z / 11:12Z / 19:22Z)。commit の内容は trade-logs / market-analysis (ignore 済み) + **`data/monitoring/nav_floor_projection.csv`** (F4 資金時計、`daily-report.yml` が `tools/nav_floor_projection.py --append` で追記) で、この 1 パスが `buildFilter.ignoredPaths` に無い。読み手は `tools/nav_floor_projection.py` / registry `project-falsification-f4-nav-floor-clock` (csv_row_match、cron 側) のみで、app.py / modules/ からの参照はゼロ (docstring 言及 2 箇所のみ)。

含意: 毎回の再デプロイ = 二重エンジンの再生成 + **00:20Z boot は fork 窓の hour-0 リスク** ([[http-blind-fork-poisoning-2026-09-22]] §3.3) の再露出 + 建玉/limit 予約の in-memory 状態のリセット。→ 別 PR で `data/monitoring/**` を ignoredPaths に追加 (`tests/test_render_build_filter.py` の runtime-read guard が pin)。sprint midpoint check (v) の「render.yaml ignoredPaths (data/external, data/monitoring) 着地」は **data/monitoring 側が未着地**だった。

## 8. 引用規律

- 「二重エンジンで shadow N が 2 倍」型の主張は**禁止** — `dedup_violation=0` の N は非膨張 (§2)。膨張しているのは `dedup_violation` 込みの生 row 数 (+8%) だけ。
- §4 の自然実験は記述級 (N=2)。「regime break なし」の証明として引用しない。
- 2026-09-24 以前の row には `[EMIT_PROC]` が無い (`none`)。marker で層別する分析は本 PR の deploy 時刻以降の行のみ。
- LIVE 二重送信 0 件は「観測されていない」であって「起こり得ない」ではない (§3)。

## 関連

- [[http-blind-fork-poisoning-2026-09-22]] §6 (発見) / [[lesson-prefork-master-must-not-touch-db-2026-09-22]]
- [[wait-tick-block-attribution-2026-09-23]] (count ゲートが DB-backed であること)
- [[pre-send-guard-observability-r3-2026-09-23]] (`[SHADOW_BYPASS]` / `[PROMO_BLOCK]` marker の規約)
- registry: `dual-engine-master-worker-disposition` (10-06) / `dual-engine-emit-proc-attribution-readout` (10-01、新設) / `http-blind-fix-verification-hour0-boots` (10-06)
