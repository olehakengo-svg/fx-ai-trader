---
id: 20260520-prod-light-audit-codex-retry-detail
title: 本番ライト監査 RETRY — 8軸詳細レポートを inline 必須 (前回 summary のみ persist 失敗)
status: done
priority: P1
rule: audit
gate: N/A
created: 2026-05-20
owner: codex-cloud
type: read-only-audit
estimated_minutes: 75
parent_task: 20260520-prod-light-audit-codex-side
---

# 本番ライト監査 RETRY — 詳細レポート再取得

## なぜ retry が必要か

前回 `20260520-prod-light-audit-codex-side` (commit `8071b66f`) は exit=0 で完走したが、**push された差分は 19 行の brief summary のみ**。8 軸ごとの Verdict/Evidence/Why/Action 詳細が `/data/repo/fx-ai-trader/.ai/tasks/done/...` 経路で書かれた可能性があるが、実際の commit には含まれていない。memory `feedback_codex_stash_leak` の典型パターン (final.md は repo persist しなければ無意味)。

## このタスクの絶対遵守ルール

⛔ **外部パス禁止**: `/data/repo/...` を含む絶対パスを引用してはいけない。書き込みは **本ファイル `.ai/tasks/queue/20260520-prod-light-audit-codex-retry-detail.md`** または `.ai/tasks/done/20260520-prod-light-audit-codex-retry-detail.md` の **Result セクション内に inline で完結**させる。

⛔ **brief summary は禁止**: 各軸ごとに最低 80 文字の Evidence (実 SQL 結果 or pytest 行 or grep ヒット行) を **本文に直接ペースト**する。「別ファイルに作成しました」「詳細は[...]に」等の指示は失格扱い。

⛔ **書き込み直前に `cat` 確認**: commit 前に `cat .ai/tasks/done/20260520-prod-light-audit-codex-retry-detail.md | tail -80` を実行し、Result セクションが 8 軸分すべて inline で書かれていることを self-check してから git add。

⛔ **本タスクで修正 commit 禁止** (read-only audit)。

## 前回判明している重要事実 (これを土台に詳細を埋める)

- `oanda_audit` 実スキーマには **`is_shadow` 列がなく `is_live` のみ** (前回 Codex 実測)
- `oanda_audit` / `oanda_trades` はローカル DB で 0 rows
- `demo_trades.is_shadow` 分布: 0→12, 1→6
- `/api/oanda/stats?range=...` で `_filters.effective_date_from` が range ごとに変化 (= range バグ修正済み)
- 新規 test 2件 (`tests/test_oanda_strategy_nearest_sent_resolution.py` / `tests/test_pyr_attribution.py`) は **origin/main に存在しない** (ローカル WIP)
- `pre-commit run --all-files`: HIP-1 holdout manifest guard で fail、PEP604 guard は pass
- `data/cache/massive/*.parquet` 実在、Price-Shock BT runner は MASSIVE-only / no Yahoo fallback

## 必須実測コマンド (各軸の Evidence にこれら出力を **inline で貼る**)

### Step A. DB schema 実取得 (schema ハルシネーション罠回避)
```bash
sqlite3 db/fxai.db ".schema oanda_audit"
sqlite3 db/fxai.db ".schema oanda_trades"
sqlite3 db/fxai.db ".schema demo_trades"
sqlite3 db/fxai.db ".tables" | tr ' ' '\n' | grep -i 'shadow\|live\|audit'
```

### Step B. Shadow/Live 分離 実測
```bash
sqlite3 db/fxai.db "SELECT is_live, COUNT(*) FROM oanda_audit GROUP BY is_live;"
sqlite3 db/fxai.db "SELECT is_shadow, COUNT(*) FROM demo_trades GROUP BY is_shadow;"
sqlite3 db/fxai.db "SELECT entry_type, is_live, COUNT(*) FROM oanda_audit GROUP BY entry_type, is_live ORDER BY 3 DESC LIMIT 20;"
grep -n 'is_shadow' modules/demo_db.py | head -20
grep -n 'is_live' modules/oanda_bridge.py | head -20
grep -rn 'is_shadow\s*=\s*0\|is_shadow\s*=\s*False\|exclude_shadow' modules/ | head -20
```

### Step C. /api/oanda/stats range の挙動
```bash
grep -n 'range_arg\|effective_date_from\|rolling_days' app.py | head -30
python3 -c "from app import app; c=app.test_client(); 
for r in ('today','7d','30d','all'):
    resp=c.get('/api/oanda/stats?range='+r); 
    print(r, resp.status_code, str(resp.get_json())[:200])"
```

### Step D. Price-Shock Phase B-1 frozenset 強制 shadow
```bash
grep -n 'PRICE_SHOCK_REV_TIER1_TYPES\|_is_price_shock_rev_auto_demoted\|frozenset' modules/demo_trader.py | head -20
sqlite3 db/fxai.db "SELECT entry_type, is_shadow, COUNT(*) FROM demo_trades WHERE entry_type LIKE 'price_shock%' GROUP BY entry_type, is_shadow;"
ls -la data/price_shock_rev_auto_demotions.json 2>&1
```

### Step E. OANDA_UNITS 整合 (Claude 側 🟠 High 発見の Codex 側検証)
```bash
grep -n 'OANDA_UNITS' modules/demo_trader.py modules/oanda_bridge.py
grep -n 'self._units\|_base_units\|_adjusted_units' modules/oanda_bridge.py modules/demo_trader.py | head -30
# restart resend で units 引数が省略される経路の grep
grep -n 'open_trade\|send_trade' modules/demo_trader.py modules/oanda_bridge.py | head -20
```

### Step F. Gate 整合
```bash
grep -rn 'H1.*[Gg]ate\|h1_gate\|win_rate.*0\.40\|0\.40\b' modules/ scripts/ tools/ 2>/dev/null | head -20
grep -n 'shadow_queue\|consecutive_pass\|5.*pass' scripts/weekly_promotion_gate.py 2>&1 | head -20
grep -rn 'rsk_gbpjpy\|per_bar_dedup\|bar_close.*dedup' modules/ 2>/dev/null | head -10
```

### Step G. テスト健全性
```bash
ls .github/workflows/ 2>&1
.venv/bin/pre-commit run --all-files 2>&1 | tail -30
python3 -m pytest tests/ -x -q 2>&1 | tail -30
```

### Step H. アーキ整合
```bash
ls -la data/cache/massive/ | head -10
grep -rn 'yfinance\|yahoo\|Yahoo' modules/ scripts/ 2>/dev/null | head -10
grep -rn 'mock_only\|Mock()' tests/ 2>/dev/null | wc -l
```

## 出力形式 — Result セクション内 inline (W4-EDA 形式)

`.ai/tasks/done/20260520-prod-light-audit-codex-retry-detail.md` (本ファイルが done/ に移動した時) の末尾に以下構造で **本文 inline** で追加:

```markdown
## Result (Detailed 8-Axis Audit)

### Axis 1: 直近 commit リスク
- **Verdict**: 🟢/🟡/🟠/🔴/⚫
- **Evidence**:
  ```
  (実コマンド出力を貼る、最低 3 行)
  ```
- **Why it matters**: 1-2 文
- **Recommended action**: 1-2 文

### Axis 2: 未コミット変更の整合性
(同形式)

...(Axis 8 まで)

### Cross-check vs Claude 側監査
- (一致した項目 / 乖離した項目 / Codex 単独発見 を簡潔に表で)

### Claude 側でこそ確認してほしい項目 (5-10 個)
- 1. ...
- 2. ...
```

## ACCEPT 条件

- Result セクションが本ファイル内 inline で完結 (外部パス参照ゼロ)
- 8 軸すべてに Verdict + Evidence (実コマンド出力) + Why + Action
- Step A-H の実コマンドのうち最低 12 個の出力が貼られている
- Cross-check 表が含まれている
- 修正 commit が 0
- final.md と queue file 以外のファイル変更 = 0

## REJECT 条件

- 「別ファイルに作成しました」「詳細は外部に」等の参照
- Evidence が抽象的記述のみで実コマンド出力が無い
- 8 軸のうち欠落あり
- mock-only テスト結果での PASS 報告
- 修正コミット発生

## Result (Detailed 8-Axis Audit)

### Axis 1: 直近 commit リスク
- **Verdict**: 🟡
- **Evidence**:
  ```
  8071b66f feat(codex): complete 20260520-prod-light-audit-codex-side
   .../done/20260520-prod-light-audit-codex-side.md   | 145 +++++++++++++++++++++
   .../20260520-prod-light-audit-codex-side.md        | 126 ------------------
   2 files changed, 145 insertions(+), 126 deletions(-)

  8071b66f feat(codex): complete 20260520-prod-light-audit-codex-side
  .ai/tasks/done/20260520-prod-light-audit-codex-side.md
  .ai/tasks/running/20260520-prod-light-audit-codex-side.md

  d0419b11 chore(codex): claim 20260520-prod-light-audit-codex-retry-detail
  54e659a6 test(codex-cloud): queue 20260520-prod-light-audit-codex-retry-detail (re-run for 8-axis inline detail)
  d04aae67 docs(KB): monitor alert 2026-05-20
  ```
- **Why it matters**: 前回 commit は task ファイルの移動と 145 行の記録追加のみで、アプリ本体やテストコードの変更は含まれていない。したがって本番挙動を変える直接リスクは低いが、前回 Result が要約に留まった監査品質リスクは残る。
- **Recommended action**: この retry の詳細 Result を唯一の監査証跡として扱い、前回 summary は補助情報に格下げする。コード修正は本タスクでは行わず、検出事項ごとに別 task で owner review を通す。

### Axis 2: 未コミット変更の整合性
- **Verdict**: 🟡
- **Evidence**:
  ```
  git status --short --untracked-files=all
  <no output>

  ls -la tests/test_oanda_strategy_nearest_sent_resolution.py tests/test_pyr_attribution.py 2>&1
  ls: cannot access 'tests/test_oanda_strategy_nearest_sent_resolution.py': No such file or directory
  ls: cannot access 'tests/test_pyr_attribution.py': No such file or directory

  git ls-files tests/test_oanda_strategy_nearest_sent_resolution.py tests/test_pyr_attribution.py
  <no output>

  git diff --stat origin/main...HEAD
  <no output>
  ```
- **Why it matters**: 作業ツリーは clean で、前回事実にあったローカル WIP test 2 件はこの checkout には存在しない。監査対象の「未コミット変更」は現在再現できず、過去セッションの前提をそのまま採用すると誤判定になる。
- **Recommended action**: Claude 側は該当 test 2 件が別 runner / stash / branch に残っていないか確認する。現在 checkout 基準では、未コミット WIP による本番混入リスクは観測されない。

### Axis 3: 本番 Gate 整合
- **Verdict**: 🟠
- **Evidence**:
  ```
  grep -rn 'H1.*[Gg]ate\|h1_gate\|win_rate.*0\.40\|0\.40\b' modules/ scripts/ tools/ 2>/dev/null | head -20
  modules/bt_vec_harness.py:199:    # Optional: load + forward-fill H1 features (used by macro-gated strategies)
  modules/bt_vec_harness.py:345:    """H1 indicators per bar — macro trend gate."""
  modules/demo_trader.py:6608:        "mtf_regime_trend_cascade_scalp",  # spread_gate最上位 + H1 macro gate + ema_pullback継承
  modules/demo_trader.py:6983:        "macd_rsi_pullback",           # MACD hist_dir + H1 RSI 60/40 trend-pullback (USD_JPY 1H, TV 3.5y N=196 WR=39.29% PF=1.161 +EV, SCALP_SENTINEL shadow-first 2026-05-14, Live N>=30 で gate 再判定)

  grep -n 'shadow_queue\|consecutive_pass\|5.*pass' scripts/weekly_promotion_gate.py 2>&1 | head -20
  12:    1. shadow_queue.jsonl で "pass" タグが5営業日連続で発生
  44:QUEUE_PATH = ROOT / "knowledge-base" / "raw" / "candidates" / "shadow_queue.jsonl"
  89:                    "consecutive_pass": streak
  145:        lines.append(f"- **Consecutive pass days**: {c['consecutive_pass']}")

  grep -rn 'rsk_gbpjpy\|per_bar_dedup\|bar_close.*dedup' modules/ 2>/dev/null | head -10
  modules/demo_db.py:568:    # rsk_gbpjpy_reversion / mqe_gbpusd_fix が 60s dedup gate 不在の状態で
  modules/demo_db.py:576:        "rsk_gbpjpy_reversion",
  modules/demo_trader.py:3099:        # rsk_gbpjpy_reversion / mqe_gbpusd_fix) が tick 毎に shadow を量産し、
  modules/demo_trader.py:3869:            "rsk_gbpjpy_reversion",          # RSK GBP_JPY: realized skewness reversion (Bonferroni 13通過)
  ```
- **Why it matters**: H1 gate / promotion streak の静的痕跡はあるが、rsk / mqe の dedup 不在を示すコメントも残っている。Gate が存在することと runaway を防げることは別で、R3 系の pending リスクは監査上 High 扱いが妥当。
- **Recommended action**: rsk / mqe の per-bar または bar-close dedup を別 task で実装・回帰テスト化する。promotion gate は 5 営業日 consecutive pass の入力ファイル更新経路まで Claude 側で追跡してほしい。

### Axis 4: Shadow/Live 分離
- **Verdict**: 🟠
- **Evidence**:
  ```
  sqlite3 db/fxai.db ".schema oanda_audit"
  /bin/sh: 1: sqlite3: not found

  Python fallback: db/fxai.db
  exists False
  is_file False
  parent_exists False
  FileNotFoundError [Errno 2] No such file or directory: 'db/fxai.db'

  -- .schema oanda_audit from demo_trades.db
  CREATE TABLE oanda_audit (
                      id              INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp       TEXT NOT NULL,
                      demo_trade_id   TEXT,
                      entry_type      TEXT,
                      direction       TEXT,
                      instrument      TEXT,
                      units           INTEGER DEFAULT 0,
                      is_live         INTEGER DEFAULT 0,
                      bridge_status   TEXT,
                      block_reason    TEXT DEFAULT '',
                      oanda_trade_id  TEXT DEFAULT '',
                      created_at      TEXT DEFAULT (datetime('now'))
                  , sr_strength REAL, sr_touches INTEGER, sr_days_span REAL, sr_is_strong INTEGER, sr_distance_atr REAL)

  -- oanda_audit is_live from demo_trades.db
  <no rows>
  -- demo_trades is_shadow from demo_trades.db
  0|12
  1|6
  -- oanda_audit entry_type/is_live from demo_trades.db
  <no rows>

  grep -n 'is_shadow' modules/demo_db.py | head -20
  515:            # ── 2026-05-03 (rule:R3): OANDA-fill is_shadow drift backfill ──
  517:            # 34 OANDA-executed trades (38.2%) had is_shadow=1 — `WHERE
  518:            # is_shadow=0` aggregates were silently dropping live PnL.
  527:                    "UPDATE demo_trades SET is_shadow=0 "
  650:                       WHERE is_shadow = 1

  grep -n 'is_live' modules/oanda_bridge.py | head -20
  240:                   is_live: bool, bridge_status: str, block_reason: str,
  257:            "is_live": is_live,
  531:                    is_live=False, bridge_status="blocked",
  626:                        is_live=True, bridge_status="filled",
  ```
- **Why it matters**: 実在 DB では `oanda_audit` に `is_shadow` はなく `is_live` のみで、`demo_trades` は `is_shadow` を持つ二重モデルになっている。集計・監視が片方の列名だけを仮定すると Live/Shadow の景色が反転する。
- **Recommended action**: OANDA audit は `is_live`、demo trade は `is_shadow` と明示して adapter 層で変換する。監査 SQL と dashboard query は `.schema` 取得後の列名に固定し、`oanda_audit.is_shadow` 前提の task は破棄する。

### Axis 5: 既知バグ `/api/oanda/stats` range
- **Verdict**: 🟢
- **Evidence**:
  ```
  grep -n 'range_arg\|effective_date_from\|rolling_days' app.py | head -30
  13886:    range_arg = request.args.get("range")
  13888:    rolling_days_arg = request.args.get("rolling_days", type=int)
  13894:    rolling_days = rolling_days_arg
  13895:    if range_arg:
  13896:        if range_arg == "today":
  13897:            rolling_days = 0
  13898:        elif range_arg == "7d":
  13899:            rolling_days = 7
  13900:        elif range_arg == "30d":
  13901:            rolling_days = 30
  13902:        elif range_arg == "all":
  13906:        effective_date_from = _FIDELITY_CUTOFF
  13913:            effective_date_from = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
  13918:            effective_date_from = max(_FIDELITY_CUTOFF, rolling_cutoff)

  .venv/bin/python API probe, printed as: range status effective_date_from rolling_days all_time
  today 200 2026-05-20T00:00:00 0 False
  7d 200 2026-05-13T07:31:02 7 False
  30d 200 2026-04-20T07:31:02 30 False
  all 200 2026-04-08T00:00:00 None True
  ```
- **Why it matters**: `range=today|7d|30d|all` がそれぞれ別の `effective_date_from` / `rolling_days` を返しており、前回の range 無視バグはこの checkout では再現しない。HTTP status も 200 で、handler の基本動作は復旧済みと判断できる。
- **Recommended action**: この挙動を固定する unit/integration test を CI に残す。total 件数だけでなく `_filters.effective_date_from` の差分も assertion に含める。

### Axis 6: 設定・env・Price-Shock/OANDA_UNITS 整合
- **Verdict**: 🟠
- **Evidence**:
  ```
  grep -n 'PRICE_SHOCK_REV_TIER1_TYPES\|_is_price_shock_rev_auto_demoted\|frozenset' modules/demo_trader.py | head -20
  61:PRICE_SHOCK_REV_TIER1_TYPES = frozenset({
  69:PRICE_SHOCK_REV_TIER1_PAIRS = frozenset({
  6934:    def _is_price_shock_rev_auto_demoted(cls, entry_type: str, instrument: str = "") -> bool:
  6935:        if entry_type not in PRICE_SHOCK_REV_TIER1_TYPES:
  6942:        return entry_type in cls._FORCE_DEMOTED or cls._is_price_shock_rev_auto_demoted(
  7190:        if self._is_price_shock_rev_auto_demoted(entry_type, instrument):

  SELECT entry_type, is_shadow, COUNT(*) FROM demo_trades WHERE entry_type LIKE 'price_shock%' GROUP BY entry_type, is_shadow;
  -- price_shock demo_trades from demo_trades.db
  <no rows>

  ls -la data/price_shock_rev_auto_demotions.json 2>&1
  ls: cannot access 'data/price_shock_rev_auto_demotions.json': No such file or directory

  grep -n 'OANDA_UNITS' modules/demo_trader.py modules/oanda_bridge.py
  modules/demo_trader.py:3571:            _exp_units_est = int(_os_exp.environ.get("OANDA_UNITS", "10000"))
  modules/demo_trader.py:5065:        _base_units = int(_os.environ.get("OANDA_UNITS", "10000"))
  modules/demo_trader.py:5280:                                        int(_os.environ.get("OANDA_UNITS", "10000")),
  modules/demo_trader.py:6895:            return PRICE_SHOCK_REV_MIN_UNITS / max(int(_os.environ.get("OANDA_UNITS", "10000")), 1)
  modules/oanda_bridge.py:60:        self._units = int(os.environ.get("OANDA_UNITS", "1000"))  # 1000 = 0.01 lot

  grep -n 'self._units\|_base_units\|_adjusted_units' modules/oanda_bridge.py modules/demo_trader.py | head -30
  modules/oanda_bridge.py:497:        units: override lot size (0 = use default self._units).
  modules/oanda_bridge.py:534:                    units=(units if units > 0 else self._units),
  modules/oanda_bridge.py:552:                    units=(units if units > 0 else self._units),
  modules/demo_trader.py:5065:        _base_units = int(_os.environ.get("OANDA_UNITS", "10000"))
  modules/demo_trader.py:5066:        _adjusted_units = int(_base_units * _lot_ratio)
  modules/demo_trader.py:5335:                        units=_adjusted_units,
  modules/demo_trader.py:5354:                        units=_adjusted_units,
  ```
- **Why it matters**: Price-Shock の frozenset 強制 shadow ロジックはコード上確認できるが、DB に対象行がなく実データでの徹底は未検証。さらに `demo_trader.py` は `OANDA_UNITS` default 10000、`oanda_bridge.py` は default 1000 で、units 省略経路があると lot が 10 倍ずれる可能性がある。
- **Recommended action**: OANDA units default を単一 source of truth に寄せ、restart resend など units 省略経路のテストを追加する。Price-Shock は対象 audit 行を持つ DB snapshot で `is_live=0` または demo 側 `is_shadow=1` を再確認する。

### Axis 7: テスト健全性
- **Verdict**: 🟠
- **Evidence**:
  ```
  ls .github/workflows/ 2>&1
  alpha-scan.yml
  bug-check.yml
  ci.yml
  daily-report.yml
  r2-alert-scheduled.yml
  trade-monitor.yml
  weekly-audit.yml

  .venv/bin/pre-commit run --all-files 2>&1 | tail -30
  HIP-1 holdout manifest guard.............................................Failed
  - hook id: hip1-holdout-manifest
  - exit code: 1
  HOLDOUT manifest edit rejected: rerun with --allow-holdout-edit after Claude manual approval.
  demo_trader PEP 604 Python 3.9 guard.....................................Passed

  python3 -m pytest tests/ -x -q 2>&1 | tail -30
  /usr/bin/python3: No module named pytest

  .venv/bin/python -m pytest tests/ -x -q 2>&1 | tail -30
  FAILED tests/test_highvol_continuation.py::test_integration_uses_real_massive_usdjpy_m5_parquet
  !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
  1 failed, 446 passed, 1 skipped in 26.97s
  ```
- **Why it matters**: pre-commit は既知の HIP-1 guard で fail し、`.venv` pytest は mock-only ではなく実 MASSIVE parquet 要求で fail した。`python3` 直実行では pytest 自体が無いため、system Python の PASS/FAIL は判断材料にならない。
- **Recommended action**: CI とローカル監査の Python entrypoint を `.venv/bin/python` または同等環境に統一する。HIP-1 manifest は Claude manual approval なしに通さず、MASSIVE parquet 欠損はデータ補充かテスト期待パスの修正を別 task 化する。

### Axis 8: アーキ整合
- **Verdict**: 🟠
- **Evidence**:
  ```
  ls -la data/cache/massive/ | head -10
  total 119176
  drwxrwsr-x 2 worker node     4096 May 20 04:12 .
  drwxrwsr-x 3 worker node     4096 May  3 16:00 ..
  -rw-rw-r-- 1 worker node      230 May 11 07:27 AUD_CAD_1h.audit.json
  -rw-rw-r-- 1 worker node   306389 May 11 07:24 AUD_CAD_1h.parquet
  -rw-rw-r-- 1 worker node      231 May 11 07:27 AUD_CAD_5m.audit.json
  -rw-rw-r-- 1 worker node  2751680 May 11 07:24 AUD_CAD_5m.parquet
  -rw-rw-r-- 1 worker node      292 May 15 14:12 AUD_JPY_1h.audit.json
  -rw-rw-r-- 1 worker node  1057628 May 15 14:12 AUD_JPY_1h.parquet

  ls -la data/cache/massive/ | grep 'USD_JPY' | head -20
  -rw-rw-r-- 1 worker node  6349425 May  5 05:46 USD_JPY_15m.parquet
  -rw-rw-r-- 1 worker node      292 May 15 14:12 USD_JPY_1h.audit.json
  -rw-rw-r-- 1 worker node  1076338 May 15 14:12 USD_JPY_1h.parquet
  -rw-rw-r-- 1 worker node      291 May 15 14:12 USD_JPY_4h.audit.json
  -rw-rw-r-- 1 worker node   319263 May 15 14:12 USD_JPY_4h.parquet
  -rw-rw-r-- 1 worker node 22356359 May  3 16:00 USD_JPY_5m.parquet

  grep -rn 'yfinance\|yahoo\|Yahoo' modules/ scripts/ 2>/dev/null | head -10
  modules/yield_data.py:6:データソース: yfinance (free) — Yahoo Finance Futures
  modules/yield_data.py:52:    import yfinance as yf
  modules/bt_vec_harness.py:17:  - load_1m / load_htf: ローカル parquet キャッシュ + OANDA + yfinance fallback
  modules/bt_vec_harness.py:129:    """Load 1m bars: local parquet → yfinance fallback (7d max)."""
  modules/bt_vec_harness.py:145:    """Load HTF bars: local parquet → OANDA → yfinance fallback.

  grep -rn 'mock_only\|Mock()' tests/ 2>/dev/null | wc -l
  0

  grep -rn 'USD_JPY_5m_2014_2026\|real MASSIVE parquet' tests/ modules/ scripts/ 2>/dev/null | head -20
  tests/test_highvol_continuation.py:50:        source_path=Path("data/cache/massive/USD_JPY_5m_2014_2026.parquet"),
  tests/test_highvol_continuation.py:64:    assert parquet.exists(), "real MASSIVE parquet is required; mock-only test is forbidden"
  tests/test_price_shock_reversion_bt.py:61:    assert parquet.exists(), "real MASSIVE parquet is required; mock-only test is forbidden"
  ```
- **Why it matters**: MASSIVE parquet 群は存在し、mock-only 文字列は tests 内で 0 件だったが、`USD_JPY_5m_2014_2026.parquet` だけは欠損して pytest が停止した。また一般 BT harness には yfinance fallback が残っており、MASSIVE-only 原則と混在している。
- **Recommended action**: strategy BT は MASSIVE-only に寄せ、fallback 使用が許される範囲を docs/test 名で明確化する。欠損している `USD_JPY_5m_2014_2026.parquet` は生成・配置・期待パス修正のどれかを選び、mock 代替で PASS にしない。

### Cross-check vs Claude 側監査

| 項目 | Codex 実測 | Claude 側との関係 |
|---|---|---|
| `oanda_audit` schema | `is_shadow` なし、`is_live` あり。`demo_trades.db` fallback で確認 | 一致。schema ハルシネーション回避の要点 |
| Shadow/Live rows | `oanda_audit` は `<no rows>`、`demo_trades.is_shadow` は `0|12`, `1|6` | 一致。ただし今回の指定 `db/fxai.db` は不存在 |
| `/api/oanda/stats` range | today/7d/30d/all で `effective_date_from` が変化 | 一致。range 無視は現 checkout で再現せず |
| Price-Shock forced shadow | frozenset ロジックはあり、DB 対象行と demotion json はなし | 一部未検証。実データ証跡は不足 |
| OANDA_UNITS | demo 側 default 10000、bridge 側 default 1000 | Claude 側 High 発見を Codex 側でも支持 |
| Gate/dedup | rsk/mqe 60s dedup gate 不在コメントが残存 | Claude 側 pending 指摘と整合 |
| Test health | pre-commit HIP-1 guard fail、pytest は MASSIVE 欠損で fail | 一致または更新。前回の test 2 件は現 checkout に存在しない |
| Architecture | MASSIVE cache はあるが yfinance fallback も残存 | Codex 単独補強。fallback の許容範囲確認が必要 |

### Claude 側でこそ確認してほしい項目 (5-10 個)

- 1. 指定された新規 test 2 件が、別 branch / stash / runner artifact に残っていないか。
- 2. `OANDA_UNITS` default 10000 と 1000 の不一致が、本番 Render env で実害化する restart resend 経路の有無。
- 3. Price-Shock Phase B-1 の実本番 audit 行で、`is_live=0` または demo 側 `is_shadow=1` が保証されているか。
- 4. `db/fxai.db` を参照する古い runbook / task が残っている場合、現在の DB 実体名へ更新すべきか。
- 5. rsk / mqe の dedup pending が「コメントだけ残存」なのか「実装未完了」なのかの静的追跡。
- 6. `weekly_promotion_gate.py` の `shadow_queue.jsonl` 入力が誰により更新され、5 営業日連続 pass が改ざん不能か。
- 7. yfinance fallback が許される module と禁止される BT runner の境界を明文化すること。
- 8. HIP-1 holdout manifest guard fail を、承認待ちの正常停止として扱うか、CI blocker として扱うか。
- 9. `USD_JPY_5m_2014_2026.parquet` 欠損がデータ backfill 未完了なのか、test 期待ファイル名の drift なのか。
- 10. `.venv` と system Python の依存差により、監査 runner ごとに pytest 結果が変わらないよう固定すること。
