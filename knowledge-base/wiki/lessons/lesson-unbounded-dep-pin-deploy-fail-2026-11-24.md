# 教訓: 上限なし依存 pin + fail-closed な監視初期化 = docs-only PR でも本番 deploy が落ちる (2026-11-24、rule:R3)

## 何が起きたか (時刻 UTC、出所 = Render `list_deploys` / `list_events` / `list_logs`、PyPI JSON)
- 10:20:23 PR #384 (docs + registry JSON のみ) merge → Render deploy `dep-dc2m9qc9v7es73b9o5pg` 開始。registry JSON は `render.yaml` ignoredPaths 外なので docs PR でも deploy が走る (既知)。
- 10:21:18 build 成功。`pip install -r requirements.txt` が **`sentry-sdk-3.0.0`** を解決 (`requirements.txt` は `sentry-sdk[flask]>=2.0.0` で**上限なし**)。前回 11-19 build は `2.75.0`。3.0.0 の PyPI 公開は **2026-11-23 09:30Z** = merge の 25 時間前。
- 10:21:38 旧 instance (w27xk、engine pid 130) に SIGTERM → worker exit。
- 10:22:04 新 instance (58cj5) で gunicorn が `app.py` を import → `sentry_sdk.init(... profiles_sample_rate=...)` が **`TypeError: Unknown option 'profiles_sample_rate'`** → exit 1 (再起動後も同じ、10:22:13)。
- 10:22:11 `deploy_ended` status failed (`nonZeroExit: 1`) → deploy **`update_failed`**。Render は前ビルド (PR #382) を新 instance (2mvvs) で再起動 → 10:22:5x `[AutoStart]` 24 modes、engine pid **105** (再起動 = `storm_guard` 状態消失 **16 例目**、material 0: open live 0)。
- HTTP 502 は 10:21:49〜10:22:52 の 5 回 (20 秒 poll)。**engine 空白 ≈ 80 秒、市場開場中 (10:22Z = London/NY 重複前)**。live 建玉 0 だったので約定・SL 管理への実害は 0。
- 本番は PR #382 のコードで生存したが、**修理するまで以後の全 deploy が同じ理由で失敗する**状態 (= main に merge した変更が本番に届かない)。

## なぜ検知器が全部黙っていたか
1. **CI は init 経路を通らない**: `SENTRY_DSN` が CI では空 → `if _SENTRY_DSN:` の中に入らない。pytest / check.py / flake8 は全 green (PR #384 CI 3/3 pass)。
2. **pin が「下限だけ」**: `>=2.0.0` は「2.0 以上なら何でも」= メジャーバージョンの破壊的変更をそのまま本番に通す宣言。Render build は毎回 fresh resolve なので、PyPI の公開タイミングで本番が決まる。
3. **監視の初期化が fail-closed**: `except ImportError: pass` は「入っていなければ無視」だが、「入っているが API が違う」は素通りして本体を落とした。Sentry は取引エンジンの付属物で、その初期化失敗がエンジンを止める設計は原則 1 (攻める) と逆。
4. **deploy 失敗の通知経路がない**: Render の `update_failed` は Discord / anomaly_watcher のどこにも流れない。autopilot が merge 後に `engine_pid` の変化を見ていたから気付いた (pid が変わった = 「deploy 成功」と読みかけた — **pid 変化は再起動の証拠であって新ビルドの証拠ではない**)。

## 修理 (PR 本 lesson と同梱、rule:R3)
- `requirements.txt`: `sentry-sdk[flask]>=2.0.0,<3` (一次防御、決定論)。3.x 移行 (profiling API 改名) は別 PR。
- `modules/sentry_boot.py`: `init` を fail-open に — `TypeError: Unknown option 'x'` なら `x` を外して再試行 (上限 3 回)、他の例外は記録して諦める。2.x では従来どおり 1 回で通る (本番挙動不変、`tests/test_sentry_boot_fail_open.py` で pin)。
- `app.py`: 冒頭の直書き `sentry_sdk.init(...)` を `modules.sentry_boot.boot()` に置換。
- tests 8 本: 3.0.0 の実エラー本文の再現 / 2.x 単発 / 名前が取れない TypeError の固定順 fallback / 非 TypeError の swallow / retry 上限 / DSN なし no-op / **requirements の `<3` pin** / **インストール済み SDK のシグネチャ突合** (pin を外した日に黙って本番 TypeError にならない)。

## 一般化 (次に同型を見たとき)
- **runtime 依存の pin は上限つき** (`>=a,<b`)。「最新を追う」のは CI で、本番 build ではない。`requirements.txt` の他の行 (`flask` / `gunicorn` / `pandas` / `numpy` など) も同じ露出を持つ — 本 PR では触らない (R3 は壊れた 1 本だけ、他は棚卸しの上で別 PR: registry `runtime-dep-upper-bound-audit` 12-08)。
- **付属物 (監視・テレメトリ・ダッシュボード) の初期化は fail-open**。本体を止めてよいのは本体の前提条件 (DB / OANDA 資格情報) だけ。
- **deploy の成否は `list_deploys.status == live` で読む**。`engine_pid` の変化・`/healthz` 200・tick ok は「何かが走っている」証拠で、「merge した commit が走っている」証拠ではない (本件は旧ビルドが新 pid で走っていた)。autopilot の Phase 5 手順に `list_deploys` の status 確認を固定する。
- 同型の既往: [[lesson-validity-check-pins-proxy-2026-09-02]] (性質でなく代理を pin) — 「pid が変わった」を「deploy 成功」の代理にしていた。

## 出所
- Render: `dep-dc2m9qc9v7es73b9o5pg` (`get_deploy` status update_failed、`list_events` deploy_ended nonZeroExit 1)、build log `bld-dc2m9qc9v7es73b9o5q0` "Successfully installed … sentry-sdk-3.0.0"、app log instance 58cj5 traceback 10:22:04Z、instance 2mvvs `[AutoStart]` 10:22:57〜10:23:26Z
- 11-19 build `bld-dbv6isijnfac739nhl1g` "sentry-sdk-2.75.0"
- PyPI `https://pypi.org/pypi/sentry-sdk/json`: 3.0.0 upload 2026-11-23T09:30Z、2.76.0 2026-11-23
- [[2026-11-24-session]] Phase 5
