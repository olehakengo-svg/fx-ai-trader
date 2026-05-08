---
id: 20260508-0030-sr-weight-audit-logging-phase1
title: "[SR-Weight-Phase1] oanda_audit に SR 重み 5 列追加 + INSERT path 改修 + pre-registration doc"
owner: codex
status: queued
priority: P1
created_at: 2026-05-08T00:30:00+0900
roadmap_gate: "Phase 2 (集計/BH FDR レポート) 投入の前段。SR 重みが LIVE 発注時に DB 記録されない設計欠陥を解消、bin 集計の根拠データを蓄積開始する"
rule: pre-reg
related:
  - modules/demo_db.py
  - modules/oanda_bridge.py
  - modules/indicators.py
  - modules/demo_trader.py
  - app.py
  - .ai/decisions/SR_strength_audit_preregistration.md
---

# 0. 背景

司令塔監査 2026-05-07 で確定した設計欠陥:

- `find_sr_levels_weighted()` (`modules/indicators.py:330`) は SR レベルの重み (`strength` / `touches` / `days_span` / `is_strong`) を完全に算出済
- しかし発注ログ用 `_add_audit()` (`modules/oanda_bridge.py:202`) は `entry_type` 文字列のみ保存し、SR 重み一切破棄
- 結果、`dual_sr_bounce` の rolling EV=-2.486 (H13 ゲートで shadow 降格中) が "全 strength bin 混合" の数字に過ぎず、`strength≥0.7` (touches≥50, 強レベル) cell が生きているか死んでいるかを bin 集計で判別不能

W4-EDA メモリ「思想は正、設計が誤」91% の典型。bin 集計クエリを Phase 2 で投げる前に、データ蓄積パイプを Phase 1 で確立する必要がある。

並走 P0 タスク `20260507-1515-r2-critical-demote-and-schedule` (R2 alert 12 CRITICAL cell 即時 demote) は既存 cell の demote、本タスクは将来 cell の feature 蓄積で衝突なし。R2 が demote した `sr_channel_reversal` / `sr_fib_confluence` も同じ SR 重み記録対象として **追加可** (本タスク改修内 §3 で対応戦略リストに含める判断は実装側で確認、見つからなければ本タスク 4 戦略のみで PR、それ以外は Phase 2 拡張で扱う)。

# 1. 仕様

## 1.1 DDL 拡張 (`modules/demo_db.py:1092` 周辺の `oanda_audit` 関連)

実測した現状 DDL:

```sql
CREATE TABLE IF NOT EXISTS oanda_audit (
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
);
```

新規 5 列を追加 (NULL 許容、既存行は NULL のまま、戦略ロジック不変、後方互換):

```sql
ALTER TABLE oanda_audit ADD COLUMN sr_strength    REAL;
ALTER TABLE oanda_audit ADD COLUMN sr_touches     INTEGER;
ALTER TABLE oanda_audit ADD COLUMN sr_days_span   REAL;
ALTER TABLE oanda_audit ADD COLUMN sr_is_strong   INTEGER;
ALTER TABLE oanda_audit ADD COLUMN sr_distance_atr REAL;
```

要件:
- CREATE TABLE 文も同列追加 (新規 DB 作成時にも反映)
- ALTER は **冪等化必須**: `PRAGMA table_info(oanda_audit)` で各列の存在チェック → 無ければ ADD のみ実行
- migration script は app 起動時に自動実行 (現状の `demo_db` init 関数パターンに合わせる)
- 既存の demote/promote ロジック・他テーブル DDL に影響を出さない

## 1.2 `_add_audit()` シグネチャ拡張 (`modules/oanda_bridge.py:202`)

```python
def _add_audit(self, ..., sr_meta: dict | None = None):
    """
    sr_meta = {
        "strength": float (0.0-1.0),
        "touches": int,
        "days_span": float,
        "is_strong": bool,
        "distance_atr": float,
    }
    None なら NULL 列で挿入 (SR 戦略以外: engulfing_bb 等は従来通り)
    """
```

要件:
- INSERT 文に 5 列追加、`(sr_meta or {}).get("strength")` 等で抽出 (None 安全)
- `is_strong` は `int(bool)` で 0/1 化
- 既存呼び出し元 (`sr_meta` 未指定) で例外を出さない (デフォルト None)

## 1.3 発注パスで重み引き渡し (`modules/demo_trader.py` / `app.py`)

SR 戦略 **6 つ** すべてで `find_sr_levels_weighted()` の選択レベル (`_sup` 等の dict) を `sr_meta` として `_add_audit()` 呼出に渡す:

| 戦略 | 状態 | 概略所在 (実装側で確定) |
|---|---|---|
| `dual_sr_bounce` | active | `app.py:2351` 周辺 (`_dt_sr_weighted` 参照箇所) |
| `sr_anti_hunt_bounce` | active | grep で発注パス特定 |
| `dt_sr_channel_reversal` | active | grep で発注パス特定 |
| `strong_sr_breakout` | active | grep で発注パス特定 |
| `sr_channel_reversal` | **R2 demoted** (P0 task で除外済) | grep で発注パス特定、shadow N 継続記録のため記録対象に含める |
| `sr_fib_confluence` | **R2 demoted** (P0 task で除外済) | grep で発注パス特定、同上 |

→ demote 済戦略でも shadow path で `find_sr_levels_weighted()` を呼んでいる箇所はそのまま、`_add_audit(sr_meta=...)` で記録される (entry_type は記録され続ける既存挙動を活用)。

`sr_distance_atr` の計算:

```python
sr_distance_atr = abs(sr_level["price"] - signal_price) / atr_at_signal
```

- `signal_price` ベース (entry_price ではない — SR 近接性は signal 時点の判定が正、spread 影響は別問題で扱わない)
- `atr_at_signal` は対応 timeframe (15m / 1h 等) の signal bar ATR
- 0 除算ガード: `atr_at_signal` が 0 / None なら `sr_distance_atr=None`

SR 系以外の戦略 (engulfing_bb / fib_reversal / ema_trend_scalp 等) は `sr_meta=None` 明示渡しで従来動作維持。

## 1.4 Pre-registration doc コミット (PR 必須項目)

同 PR で `.ai/decisions/SR_strength_audit_preregistration.md` を作成し以下を **改修コミット時点で固定** (2 cohort 分離設計):

```yaml
hypothesis:
  H0: "SR strength と LIVE/Shadow EV は無相関 (cohort 内共通)"
  H1: "strength>=0.7 cell の EV > strength<0.5 cell (片側 Welch、cohort 別)"

# === Primary cohort: 現状 active な 4 戦略、promote/keep 判定対象 ===
primary_cohort:
  strategies:
    - dual_sr_bounce
    - sr_anti_hunt_bounce
    - dt_sr_channel_reversal
    - strong_sr_breakout
  primary_cell:
    strategy: dual_sr_bounce
    bin: strength>=0.7
    bridge_status: 'sent'
    is_live: 1  # OANDA 実発注のみ (demo は補助参照)
    expected_n_30d: 30+
  cells: 12  # 4 × 3 strength bin
  multiple_testing:
    method: BH FDR
    q: 0.10
    m: 12
  decision_criteria:
    promote: "Wilson_lo(WR)>0.45 AND PF>=1.20 AND Kelly>=0.10 AND BH-FDR adj p<0.05"
    shadow_keep: "Wilson_lo(WR)>0.40 AND PF>=1.05"
    demote: "それ以外"

# === Exploratory cohort: R2 demoted 2 戦略、redesign 判断専用 ===
exploratory_cohort:
  strategies:
    - sr_channel_reversal       # R2 で USD_JPY (-1.77 EV, N=97) / EUR_USD (-1.18 EV, N=31) demote
    - sr_fib_confluence         # R2 で 3 cell demote (EUR_JPY -13.06 / GBP_JPY -6.71 / USD_JPY -3.71)
  rationale: |
    R2 で全 cell demote されたが strength 別に分離すると strength>=0.7 cell が
    生き残っている可能性。Shadow N 蓄積を続けて feature 観察、redesign 根拠化。
  cells: 6  # 2 × 3 strength bin
  multiple_testing:
    method: BH FDR
    q: 0.10
    m: 6  # 独立 family、primary cohort と合算しない
  decision_criteria:
    redesign_recommend: "strength>=0.7 cell の Wilson_lo(WR)>0.40 AND PF>=1.0"
    graveyard_confirm: "全 cell で Wilson_lo(WR)<0.30"
  prohibitions:
    - "本 cohort 結果のみによる active promote 禁止 (post-hoc bias、demote 後に都合の良い cell を拾う罠)"
    - "primary cohort と合算した m=18 BH FDR 計算禁止 (family 独立)"
    - "redesign_recommend 該当時は spec 書き直し → 新タスク投入 (本 task では実装しない)"

sanity_floor:
  catastrophic_only: "平均 EV 符号反転"  # v2.1 paradigm fix 準拠、両 cohort 共通

stages:
  stage_0_7d: "primary cell N<5/週なら BLOCKED_DATA = 戦略 dead 扱い、本監査打切り"
  stage_1_30d: "primary cohort 全 cell N>=30 揃うか sanity 確認、足りなければ +30d 延長"
  stage_2_60_90d: "final verdict、両 cohort で BH FDR 補正後判定"

global_prohibitions:
  - "post-hoc cell selection 禁止 (W3-3 S4 / W3-5 で reject 確定済罠)"
  - "primary cell 以外で有意 → 報告は許可、判定根拠としては不可"
  - "stage 完了前の中間 promote 禁止"
  - "exploratory cohort の有意結果を primary cohort に流用禁止"
```

# 2. 検証要件 (mock-only trap 対策)

## 2.1 ローカル `pytest`

1. **DDL 冪等性**: 同 DB に migration を 2 回連続実行で例外なし、列重複エラーなし
2. **後方互換**: `_add_audit(sr_meta=None)` (or 引数省略) で従来通り NULL 挿入できる
3. **正常系**: `_add_audit(sr_meta={"strength":0.82,"touches":95,"days_span":33.6,"is_strong":True,"distance_atr":1.2})` で 5 列が round-trip できる (SELECT 結果が一致)
4. **発注パス spy**: SR 戦略 **6 つ** 各々で `_add_audit` を mock し、`sr_meta is not None` かつ必須 5 キーが含まれていることを assert

## 2.2 本番 SQLite (Render persistent disk) E2E

1. デプロイ後初回起動で ALTER が冪等成功 (起動ログに ALTER エラーなし、既存行は新列 NULL のまま)
2. デプロイ後 24h 以内に以下の SQL で 5+ 件返ること:

```sql
SELECT COUNT(*) FROM oanda_audit
WHERE entry_type IN (
        'dual_sr_bounce','sr_anti_hunt_bounce','dt_sr_channel_reversal','strong_sr_breakout',
        'sr_channel_reversal','sr_fib_confluence'
      )
  AND bridge_status='sent'
  AND sr_strength IS NOT NULL;
```

3. 既存行の `sr_strength` カラムは依然 NULL のまま (= 過去データを偽装上書きしていない)

## 2.3 戦略 entry rate 退行チェック

- デプロイ前 24h と後 24h で `oanda_audit` の `entry_type='dual_sr_bounce' AND bridge_status='sent'` 行数を比較
- ±20% 以内 (発注ロジック不変なので変動なしが期待値、ATR 計算追加によるパフォーマンス劣化が無いか確認)

# 3. 範囲外 (Phase 2 以降、本タスクで触らない)

- 集計 SQL の実装 (cells CTE / Wilson CI / PF / Kelly / Sharpe)
- BH FDR / Bonferroni 計算コード
- レポート生成 (pre-registration doc に沿った verdict 出力)
- Phase 2 dispatch は Stage 1 通過時 (30d 後) に司令塔から別タスクで投入

# 4. 注意事項 (memory 由来規律)

- **`oanda_audit.entry_type` 二義性** ([reference_oanda_audit_twin_meaning]): `bridge_status='sent'` で戦略名 / `'filled'` で MODE 名。本タスクの sr_meta は **戦略名行 ('sent') のみ書き込み** で OK。'filled' 行に書く必要はない (MODE 単位で SR 重みは未定義)
- **LIVE/Shadow 分離必須** ([feedback_live_shadow_separation]): `is_live` 列と `bridge_status` 列両方で集計時に分離可能なことを Phase 1 で保証 (既存 schema で達成済、本改修で混入させないこと)
- **ローカル app.py orphan 検知** ([feedback_check_orphan_local_app]): 開発 / テスト時 `pgrep -f app.py` で本番接続中プロセス確認、誤って本番 SQLite に書き込まない
- **Codex schema hallucination 対策** ([feedback_codex_schema_hallucination]): 上記 §1.1 の DDL は 2026-05-07 司令塔実測の CREATE TABLE 文ベース、推測ではない。実装時に `modules/demo_db.py` の現状 DDL を再確認し、相違があれば本タスクを停止して司令塔に報告
- **Codex mock-only テストの罠** ([feedback_codex_mock_test_trap]): §2.1 の pytest 全 pass だけでは完了不可、§2.2 の本番 E2E まで確認すること

# 5. 期待アウトプット (完了報告で必須)

- 改修後の `CREATE TABLE oanda_audit` 全文 (列順含む)
- `_add_audit` 改修前後 diff
- 発注パス改修箇所の diff (**6 戦略分**、ファイル名:行番号)
- pytest 結果 (4 種テスト全 pass のログ)
- pre-registration doc (`.ai/decisions/SR_strength_audit_preregistration.md`) の差分
- §2.2 / §2.3 の E2E 検証 SQL とその実行結果
- ファイル変更一覧 (git diff --stat)


## Result (2026-05-08T07:58:08Z)

exit=0 · 176s

```
確認しました。実装本体は既に `364027e feat(audit): record SR-level quality...` に入っており、現 HEAD はその後の task claim commit です。作業ツリーは clean です。

**CREATE TABLE**
```sql
CREATE TABLE IF NOT EXISTS oanda_audit (
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
    sr_strength     REAL,
    sr_touches      INTEGER,
    sr_days_span    REAL,
    sr_is_strong    INTEGER,
    sr_distance_atr REAL,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

**実装要点**
- `modules/demo_db.py:341`: `oanda_audit` CREATE TABLE に 5 列追加。
- `modules/demo_db.py:497`: `PRAGMA table_info(oanda_audit)` ベースの冪等 ALTER。
- `modules/demo_db.py:1120`: INSERT に `sr_strength/sr_touches/sr_days_span/sr_is_strong/sr_distance_atr` 追加。
- `modules/oanda_bridge.py:202`: `_add_audit(..., sr_meta=None)` 追加。`is_strong` は `int(bool(...))` 化。
- `modules/demo_trader.py:662`, `modules/demo_trader.py:4446`, `modules/demo_trader.py:4981`, `5000`, `5064`, `5085`, `5117`: audit 呼び出しへ `sr_meta` 伝播。
- `app.py:3484`: `dual_sr_bounce` の `_dt_nearest_scenario` から `sr_meta` 生成。
- `app.py:3478`, `app.py:8833`, `app.py:9005`, `app.py:9242`: daytrade/scalp/shadow emit の `sr_meta` 伝播。
- `strategies/base.py:23`, `30`: `Candidate.sr_meta` と `sr_meta_from_level/from_price` 追加。
- `strategies/daytrade/sr_anti_hunt_bounce.py:156`, `258`
- `strategies/daytrade/dt_sr_channel.py:106`, `235`
- `strategies/daytrade/sr_fib_confluence.py:96`, `244`
- `strategies/scalp/sr_channel_reversal.py:134`, `287`

**注意点**
`strong_sr_breakout` は `app.py:5121` の `run_backtest()` 内だけで見つかり、production order/audit path は grep 上ありませんでした。既存テストは `_add_oanda_audit` wrapper に `strong_sr_breakout` を渡せることは確認していますが、実 live 発注パ
…(truncated)
