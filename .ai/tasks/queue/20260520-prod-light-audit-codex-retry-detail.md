---
id: 20260520-prod-light-audit-codex-retry-detail
title: 本番ライト監査 RETRY — 8軸詳細レポートを inline 必須 (前回 summary のみ persist 失敗)
status: queued
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
