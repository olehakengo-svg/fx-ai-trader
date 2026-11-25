# runtime 依存の上限なし pin 棚卸し — 全 15 行に `<次メジャー` を付ける (2026-11-25、rule:R3、autopilot)

registry `runtime-dep-upper-bound-audit` (期日 12-08) の執行。前倒しの根拠: 棚卸しは観測を待たない (requirements.txt + Render build log + PyPI JSON で閉じる) ため、残り期間に判定が変わる要素がない。逆に放置する 1 日ごとに「次の PyPI メジャー公開 → docs-only PR の deploy が落ちる」露出が続く ([[lesson-unbounded-dep-pin-deploy-fail-2026-11-24]])。

## 1. 問い
`requirements.txt` の各行について (a) 上限の有無 (b) 本番 build が最後に解決した版 (c) 直近メジャー公開の履歴・頻度を表にし、上限を付ける行と付けない行を決める。付属物 (監視・テレメトリ) の初期化が fail-closed になっている箇所も列挙する。

## 2. 出所 (全て機械読み)
- **(b) 本番解決版**: Render build `bld-dc2mis6q1p3s73dkjmi0` (deploy `dep-dc2mis6q1p3s73dkjmhg`、2026-11-24T10:40:20Z、`list_logs type=build text=Successfully`)。`==> Using Python version 3.11.0 via environment variable PYTHON_VERSION`。同日 10:21:18Z の失敗 build `bld-dc2m9qc9v7es73b9o5q0` との差分は sentry-sdk 3.0.0 → 2.76.0 の 1 行のみ (他 14 行は同一版)。
- **(c) PyPI**: `https://pypi.org/pypi/<pkg>/json` (2026-11-25T02:1xZ 取得)。`releases` の各メジャーの初出 upload 日と `info.version`。
- CI: `.github/workflows/ci.yml` は Python 3.11 + `pip install -r requirements.txt` (fresh resolve) = Render と同じ解決器・同じ Python minor。

## 3. 棚卸し表

| 行 | 旧 spec | 上限 | Render 解決版 (11-24) | PyPI latest (公開日) | 直近メジャー初出 | 採用 spec | 根拠 |
|---|---|---|---|---|---|---|---|
| flask | `>=2.3.0` | なし | 3.1.3 | 3.1.3 (2026-02-19) | 3.0.0 2023-09-30 (2.0 2021-05) | `>=2.3.0,<4` | web 本体。メジャー間隔 2 年超、4.0 未公開 |
| gunicorn | `>=21.2.0` | なし | 27.0.1 | 27.0.1 (2026-11-12) | **24 → 25 → 26 → 27 が 2026 年内** (01-23 / 02-01 / 05-05 / 11-10) | `>=21.2.0,<28` | 起動コマンド (`--worker-class gthread --threads 8 --timeout 120`) と fork 挙動に直結。メジャーが年 4 回なので上限更新 PR の固定費が最大 (§5) |
| yfinance | `>=0.2.28` | なし | 1.8.0 | 1.8.0 (2026-11-03) | 1.0 2025-12-22 | `>=0.2.28,<2` | 価格取得 (modules/data.py)。1.0 でスキーマ変更済み、2.0 未公開 |
| pandas | `>=2.0.0` | なし | **3.1.1** | 3.1.1 (2026-11-04) | 3.0.0 2026-01-21 | `>=2.0.0,<4` | **本番はすでに 3.x で稼働** (上限なし pin が 2026-01 以降に黙って 2.x → 3.x を通した実例)。3.x で動いている事実を保存、4.0 未公開 |
| pyarrow | `>=15.0.0` | なし | 26.0.1 | 26.0.1 (2026-11-03) | 23 / 24 / 25 / 26 が 2026 年内 (01 / 04 / 07 / 10 月) | `>=15.0.0,<27` | parquet cache。四半期メジャー (gunicorn と同じ固定費) |
| numpy | `>=1.24.0` | なし | 2.4.6 | 2.5.5 (2026-11-15) | 2.0.0 2024-06-16 | `>=1.24.0,<3` | 2.5.x は `requires_python>=3.12` のため Python 3.11.0 固定下では 2.4.x に落ちる (§4)。3.0 未公開 |
| scipy | `>=1.10.0` | なし | 1.17.1 | 1.18.1 (2026-08-21) | 1.0.0 2017-10-25 | `>=1.10.0,<2` | 1.18 は `>=3.12`。2.0 未公開 |
| ta | `>=0.10.2` | なし | 0.11.0 | 0.11.0 (2023-11-02) | 0.x のみ | `>=0.10.2,<1` | 指標ライブラリ (app.py / modules/indicators.py で top-level import)。3 年更新なし、1.0 が出たら API 変更の可能性大 |
| requests | `>=2.31.0` | なし | 2.34.2 | 2.34.2 (2026-05-14) | 2.0.0 2013-09-24 | `>=2.31.0,<3` | OANDA / 外部 API 全経路。3.0 未公開 |
| pytest | `>=7.4.0` | なし | 9.2.0 | 9.2.0 (2026-10-27) | 9.0.0 2025-11-08 (8.0 2024-01) | `>=7.4.0,<10` | ツール (Render は install するが app は import しない)。露出は install 失敗のみ。上限は CI の決定論のため |
| flake8 | `>=6.1.0` | なし | 7.5.0 | 7.5.0 (2026-10-28) | 7.0.0 2024-01-05 | `>=6.1.0,<8` | 同上 (lint 規則の変化で CI が赤になる露出) |
| sentry-sdk[flask] | `>=2.0.0,<3` | **あり (11-24)** | 2.76.0 | 3.0.0 (2026-11-23) | 3.0.0 2026-11-23 | 不変 | 11-24 修理済み |
| jpholiday | `>=1.0.3` | なし | 1.0.3 | 1.0.3 (2025-12-26) | 1.0.0 2025-03-20 | `>=1.0.3,<2` | 祝日判定 (modules)。2.0 未公開 |
| apscheduler | `>=3.10.0` | なし | 3.11.3 | 3.11.3 (2026-06-28) | 3.0.0 2014-07-28 | `>=3.10.0,<4` | 4.x は全面書き直し (`BackgroundScheduler` 廃止)。app.py の guard は `ImportError` のみ (§6) |
| python-dotenv | `>=1.0.0` | なし | 1.2.4 | 1.2.4 (2026-10-01) | 1.0.0 2023-02-24 | `>=1.0.0,<2` | ローカル用。2.0 未公開 |

**結論: 上限なし 14/15 行、全て `<解決版メジャー+1>` を付ける。付けない行 = 0。** 下限は触らない。採用 spec は全行で Render 解決版を含む (解決結果不変 = 挙動不変 = R3)。

## 4. 副所見 (記録のみ、本 PR で触らない)
- **Python 3.11.0 固定 (Render env `PYTHON_VERSION`) がすでに暗黙の上限になっている行がある**: numpy 2.5 / scipy 1.18 は `requires_python>=3.12` のため 2.4.6 / 1.17.1 に留まる。これは pip の解決器が面倒を見ているだけで宣言ではない。Python を上げる日に numpy / scipy が同時にジャンプする (別 PR、観測対象)。
- **ローカル開発環境 (Python 3.9.6、pandas 2.3.3 / numpy 2.0.2 / gunicorn 23.0.0) と本番 (3.11.0、pandas 3.1.1 / numpy 2.4.6 / gunicorn 27.0.1) は版が違う**。pandas 2 → 3 の挙動差 (copy-on-write 既定、文字列 dtype) は CI (3.11、fresh resolve = 本番と同じ版) が担保しており、ローカル pytest は担保しない。既知の差として記録 (ローカル環境の更新は user 領域)。
- **上限 pin はパッチ/マイナーは通す**: `<28` は 27.x のセキュリティ修正を止めない。止めるのはメジャーだけ。

## 5. 固定費
- 上限更新 PR は「本番で動かす版を意図して選ぶ」行為 = 1 PR / メジャー。実測の頻度 (PyPI 2026 年): gunicorn 4 / pyarrow 4 / その他 0〜1 → **年 ≈ 8〜10 本**、各 R3 (CI green + 必要なら API 差分確認)。
- 比較対象: 上限なしの事故 1 回 = 市場開場中の engine 空白 ≈80 秒 + **修理するまで全 deploy が失敗** (11-24 実測、docs PR でも発生)。年 8〜10 本の pin 更新は意図した固定費として受容。
- 検知: 上限に当たった日は pip が旧メジャーを解決し続けるだけで**何も壊れない** (= 静かに旧版に留まる)。「最新を追えていない」ことの読み手は本表の再実行 (PyPI JSON vs `requirements.txt`) で、sprint 終了レビューの固定項目に載せる (`sprint-1122-triage-close` 12-21 で初回)。

## 6. 付属物の初期化が fail-closed な箇所 (列挙、registry message の要求)
`app.py` の module-level で、例外を `ImportError` だけで受けている accessory:

| 箇所 | 何を守るか | 現状 | 判定 |
|---|---|---|---|
| `app.py:81-85` `cfd_trader.web.app.register(app)` | shadow dashboard (/cfd) | `except ImportError` のみ。register 内の他例外は import を落とす | 候補。ただし観測された欠陥なし → 本 PR では触らない |
| `app.py:88-104` APScheduler `BackgroundScheduler(...)` + `add_job` + `start()` | cfd catchup cron | `except ImportError` のみ。4.x は `BackgroundScheduler` 消滅 = ImportError で guard が効く。3.x 内の `TypeError` (kwarg 変更) は落とす | 上限 `<4` で露出を閉じる。例外幅の拡大は保留 |
| `app.py:33-37` `load_dotenv()` | ローカル .env | `except ImportError` のみ | 本番は `RENDER` env で no-op 相当、露出なし |
| `app.py:57-59` `from ta.* import …` | 指標 (本体) | guard なし | **付属物ではない** (本体の前提条件)。上限 `<1` のみ |
| `app.py:62-68` sklearn | ML (任意) | `except ImportError` → `_ML_AVAILABLE=False` | requirements に無い (本番は常に False)。露出なし |
| `app.py:13598-13640` disk_guard / candidate_logger / block_event_logger / migrate_seed | 付属 init | `except Exception` + print | すでに fail-open |
| `modules/sentry_boot.py` | Sentry | fail-open (11-24) | 済 |

cfd / apscheduler の 2 箇所を `except Exception` に広げる案は、**cfd shadow 側の実欠陥 (本来 import で気付くべきもの) を隠す側**でもあるため、観測された事故なし = R3 の要件 (構造バグ) を満たさず起票しない。次に同型の事故が出た時点で同 PR に載せる。

## 7. 機械 pin (`tests/test_requirements_upper_bounds.py`、3 本)
1. 全行に `<N` 上限がある (= `>=` だけの行を 1 本も残さない)。
2. 上限 N = 表の Render 解決版 (test 内 `RENDER_RESOLVED_2026_11_24` に転記) のメジャー + 1、下限 ≤ 解決版、表と requirements.txt の集合が一致。**上限を上げる PR は新しい build log の値で表も更新する** (表が古いまま上限だけ上げると落ちる)。
3. この interpreter に入っている版が pin の範囲内 (CI = 3.11 fresh resolve = 本番と同じ版で評価される)。

既存 `tests/test_sentry_boot_fail_open.py::test_requirements_pins_sentry_sdk_below_3` は不変 (sentry 行は spec を変えていない)。

## 8. 判断
- **rule:R3** — 挙動不変 (解決版は全行不変)、live パラメータ / シグナル / tier / 凍結値 / KV 非接触。`requirements.txt` は `render.yaml` ignoredPaths 外なので deploy が走る → **open live 0 の窓で merge**、Phase 5 は `list_deploys.status == live` と build log の `Successfully installed` 行が §3 の解決版と一致することで読む (pid 変化は証拠にしない)。
- registry `runtime-dep-upper-bound-audit` (12-08) → resolve (本 PR)。後継 entry は起票しない: 上限に当たっても何も壊れない構造にしたので「期日」ではなく sprint 終了レビューの固定項目 (§5) で読む。

## 出所・関連
- [[lesson-unbounded-dep-pin-deploy-fail-2026-11-24]] / [[2026-11-24-session]] Phase 5-6 / [[2026-11-25-session]]
- Render `list_logs` build `bld-dc2mis6q1p3s73dkjmi0` / `bld-dc2m9qc9v7es73b9o5q0`、PyPI JSON 15 件 (scratchpad に保存、git 外)
- 同型の既往: [[lesson-validity-check-pins-proxy-2026-09-02]] (性質でなく代理を pin するな — 本表は「本番が解決した版」という性質を test に転記して pin する)
