---
id: 20260506-1610-tier-promotion-consistency-audit
title: "[Tier-Audit] Promotion ladder consistency audit (M1〜M7)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-06T16:10:00+0900
roadmap_gate: "司令塔の演繹監査で抽出した昇格パイプラインの 7 矛盾候補を、SQLite + Render API で実測検証する"
rule: R-empirical
prereq_artifacts:
  - tools/auto_force_demoted_recovery.py
  - tools/sentinel_promotion_scanner.py
  - modules/demo_trader.py
related:
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_shadow_first_quant_architecture.md
  - knowledge-base/wiki/lessons/feedback_codex_schema_hallucination.md
  - knowledge-base/wiki/lessons/feedback_check_orphan_local_app.md
  - knowledge-base/wiki/lessons/feedback_live_shadow_separation.md
---

# 0. ミッション

司令塔 (Claude Code) が演繹で抽出した昇格パイプラインの **7 矛盾候補 (M1〜M7)** を、SQLite + Render API で**実測**検証する。コード演繹回答禁止 (`feedback_label_empirical_audit.md`) — 全項目に **WHERE/GROUP BY/HAVING を含む SQL クエリと結果数値**を最終レポートに添付すること。

# 1. 前提チェック (実行前 MUST)

## 1.1. ローカル orphan app.py 検査
```bash
pgrep -f "python.*app\.py" || echo "no orphan"
```
出力に PID が出たら **タスク中断**し、司令塔に報告。
理由: `feedback_check_orphan_local_app.md` — 長期稼働 orphan が phantom trade で DB を汚染する。

## 1.2. データソース
- **一次ソース**: `demo_trades.db` (ローカル SQLite)
- **真値クロスチェック**: `https://fx-ai-trader.onrender.com/api/...` (Render LIVE API)
- BT 必要時: `data/cache/massive/*.parquet` (`feedback_bt_must_use_massive.md`)

## 1.3. LIVE/Shadow 分離
全集計クエリで `WHERE is_shadow = 0` (LIVE) と `WHERE is_shadow = 1` (Shadow) を**必ず分離**。混入で景色反転 (`feedback_live_shadow_separation.md`)。

# 2. Schema (推測禁止 — この CREATE TABLE 文を真実とせよ)

`feedback_codex_schema_hallucination.md` 準拠。以下を spec の真実とする。

## 2.1. demo_trades
```sql
CREATE TABLE demo_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT UNIQUE,
    status          TEXT DEFAULT 'OPEN',         -- 'OPEN' / 'CLOSED'
    direction       TEXT,                         -- 'BUY' / 'SELL'
    entry_price     REAL,
    entry_time      TEXT,
    exit_price      REAL,
    exit_time       TEXT,
    sl              REAL,
    tp              REAL,
    pnl_pips        REAL,
    pnl_r           REAL,
    outcome         TEXT,                         -- 'WIN' / 'LOSS' / 'BE'
    entry_type      TEXT,                         -- strategy name (e.g., 'ema_pullback')
    confidence      INTEGER,
    tf              TEXT DEFAULT '15m',
    reasons         TEXT,
    regime          TEXT,
    layer1_dir      TEXT,
    score           REAL,
    close_reason    TEXT,
    ema_conf        INTEGER,
    sr_basis        REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    mode            TEXT DEFAULT '',              -- 'scalp' / 'swing' / 'tf' etc.
    oanda_trade_id  TEXT DEFAULT '',
    instrument      TEXT DEFAULT 'USD_JPY',       -- 'USD_JPY' / 'EUR_JPY' etc.
    signal_price    REAL DEFAULT 0,
    spread_at_entry REAL DEFAULT 0,
    spread_at_exit  REAL DEFAULT 0,
    slippage_pips   REAL DEFAULT 0,
    cooldown_elapsed REAL DEFAULT 0,
    close_analysis  TEXT DEFAULT '',
    mafe_adverse_pips REAL DEFAULT 0,
    mafe_favorable_pips REAL DEFAULT 0,
    is_shadow       INTEGER DEFAULT 0,            -- 1=shadow, 0=live (** MUST分離 **)
    mtf_regime      TEXT,
    mtf_d1_label    INTEGER,
    mtf_h4_label    INTEGER,
    mtf_vol_state   TEXT,
    gate_group      TEXT,
    mtf_alignment   TEXT,
    mtf_gate_action TEXT,
    alpha_snapshot  TEXT,
    dedup_violation INTEGER
);
```

## 2.2. oanda_audit
```sql
CREATE TABLE oanda_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    demo_trade_id   TEXT,
    entry_type      TEXT,                         -- bridge_status='sent'時は戦略名 / 'filled'時はMODE名 (** 二義性注意 **)
    direction       TEXT,
    instrument      TEXT,
    units           INTEGER DEFAULT 0,
    is_live         INTEGER DEFAULT 0,            -- 1=実弾発注、0=shadow/blocked
    bridge_status   TEXT,                         -- 'sent' / 'filled' / 'blocked' / 'failed'
    block_reason    TEXT DEFAULT '',              -- 'force_demoted' / 'pair_demoted' / 'sentinel' etc.
    oanda_trade_id  TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);
```
重要: `feedback_oanda_audit_twin_meaning` — `entry_type` の二義性。`bridge_status='filled'` 行は MODE 名 (scalp/swing/tf) が入る。戦略単位集計は `bridge_status='sent'` で行うこと。

## 2.3. algo_change_log
```sql
CREATE TABLE algo_change_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT DEFAULT (datetime('now')),
    change_type     TEXT NOT NULL,                -- 'auto_recovery_from_force_demoted' etc.
    description     TEXT NOT NULL,
    params_before   TEXT,                         -- JSON
    params_after    TEXT,                         -- JSON
    triggered_by    TEXT DEFAULT 'daily_review'
);
```

## 2.4. cell_edge_audit_history (PP_CANDIDATE 監視用)
```sql
CREATE TABLE cell_edge_audit_history (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at                TEXT DEFAULT (datetime('now')),
    scope                 TEXT NOT NULL,          -- 'v2_7d_shadow' etc.
    audit_mode            TEXT NOT NULL,
    window                TEXT NOT NULL,
    data_scope            TEXT NOT NULL,          -- 'shadow' / 'live' / 'both'
    total_trades          INTEGER,
    qualified_cells       INTEGER,
    n_promotion_strict    INTEGER,
    n_promotion_legacy    INTEGER,
    n_watch               INTEGER,
    top_cells_json        TEXT,
    new_strict_cells_json TEXT
);
```

# 3. 司令塔抽出の 7 矛盾候補 (実測対象)

## M1. Wilson 閾値の二重基準
**仮説**: FORCE_DEMOTED 復帰 (Wilson_BF lo > 0.50) と通常 Mode A 昇格 (Wilson_BF lo > 0.294 = BEV) で同じ Bonferroni Z=3.29 を使いながら閾値が乖離 → 復帰経路が過度に厳しい (false negative 過多) または 0.50 が真値で BEV ベースが緩すぎ。

**実測**:
1. 過去 6 ヶ月で `algo_change_log` に `change_type='auto_recovery_from_force_demoted'` で記録された全戦略を抽出
2. 各復帰戦略の復帰直前 30 日 shadow と、復帰後 30 日 (live or shadow 両方) の Wilson_BF lo / WR / EV を計算
3. `MIN_N=30, WILSON_BF_Z=3.29, threshold=0.50` を `0.294` に下げた仮想シナリオで何件追加で復帰したかを再シミュレーション (in-place、DB 書込なし)
4. 結論: BEV (0.294) を採用していたら追加で復帰した戦略の母集団 30 日 PnL を集計し「false negative の過大推定」を判定

```sql
-- 例: 復帰戦略の特定
SELECT timestamp, description, params_after
FROM algo_change_log
WHERE change_type = 'auto_recovery_from_force_demoted'
ORDER BY timestamp DESC;
```

## M2. sentinel の Bonferroni 補正抜け
**仮説**: `sentinel_promotion_scanner.py:78-80` は Wilson 95% (Z=1.96) で PP_CANDIDATE 判定。家族数 m 補正なし。FWER 暴走で false PP_CANDIDATE を量産している。

**実測**:
1. `cell_edge_audit_history` の直近 90 日分を全件取得
2. `top_cells_json` 内の各 cell について、Wilson 95% (Z=1.96) と Wilson_BF (Z=3.29, m = qualified_cells 数) で再計算
3. 「Wilson 95% pass / Wilson_BF fail」ギャップに該当する cell を全列挙
4. それらの cell の **その後 30/60 日 LIVE PnL** (is_shadow=0) を実測 → false positive 率を量化

## M3. N 閾値の発火順序の重畳
**仮説**: N=15〜19 区間でペア降格 (`_PAIR_DEMOTED` 動的追加 in demo_trader.py:5650-5668) と Mode A 昇格判定 (N=20 直前) が時間的に近接 → 同一戦略で「ペア降格 AND グローバル昇格」が発生する。

**実測**:
1. `demo_trades` で各 (entry_type, instrument, mode, is_shadow=0) セルの累積 N を時系列計算
2. N=15 到達時点と N=20 到達時点を比較し、その間の EV / WR の符号転換を抽出
3. 実際に `_PAIR_DEMOTED` に動的追加された記録を `algo_change_log` から探索
4. 同一戦略で同周期に「ペア降格イベント」と「グローバル昇格判定」が同時発火した事例を SQL で抽出

```sql
-- 例: N=15-25 区間の境界判定
WITH live_cells AS (
  SELECT entry_type, instrument, mode,
         COUNT(*) AS n,
         AVG(pnl_pips) AS ev,
         AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END) AS wr
  FROM demo_trades
  WHERE is_shadow = 0 AND status = 'CLOSED'
    AND entry_time >= datetime('now', '-180 days')
  GROUP BY entry_type, instrument, mode
  HAVING n BETWEEN 15 AND 25
)
SELECT * FROM live_cells
WHERE ev < -0.5
ORDER BY entry_type, instrument;
```

## M4. EV grey zone `[-0.5, +friction)` の沈黙
**仮説**: 降格条件 (EV<-0.5) と昇格条件 (EV>=friction>0) の間に grey zone があり、slow bleeder が永久に shadow に残留する。

**実測**:
1. 全 (entry_type, instrument, mode, is_shadow) セルで N>=20 のもの抽出
2. friction_pip を `modules/demo_trader.py` または config から戦略別に取得 (推測禁止 — 実装読み取り必須)
3. EV が `[-0.5, friction)` に入るセルをリスト化、該当戦略の累積 PnL と滞留期間を集計
4. 上位 10 件の sluggish bleeder を提示

## M5. pos_ratio 0.67 × 30d window の頻度バイアス
**仮説**: 低頻度戦略 (multi-day / weekly setup) は 30 日で N=30 に届かず PP_CANDIDATE 不可 → CAD-1 multi-day/weekly lane と非整合。

**実測**:
1. 過去 365 日の各 entry_type の **30 日 rolling 最大 N** を計算
2. 30 日で N>=30 を一度も達成できなかった戦略をリスト化
3. それらの戦略の 365 日累積 PnL (shadow + live 別) を提示 → 「pos_ratio gate に統計的に到達不可だが累積で edge を持つ可能性のある戦略」を抽出

## M6. FORCE_DEMOTED 22 戦略の自動復帰 false positive 試算
**仮説**: W4-EDA で 94% が DESIGN_BROKEN と確定済み。Bonferroni p<0.05 を**運良く**通過する確率を試算 (FWER モデル)。

**実測**:
1. `_FORCE_DEMOTED` リスト 22 戦略を `modules/demo_trader.py:6074-6130` から抽出 (hardcode 読み取り、推測禁止)
2. 各戦略の現在 shadow N / WR / Wilson_BF lo を `demo_trades` から実測
3. p<0.05 通過まで残る期待 N と、3-month / 6-month / 12-month で復帰する期待件数 (binomial null 仮定下) を試算
4. 復帰したら _PAIR_PROMOTED 経由で**実弾再開する戦略**を `_PAIR_PROMOTED` リスト ([demo_trader.py:6195-6253](file:demo_trader.py)) と突合

## M7. 復帰経路の Tier 着地監査 ★最重大★
**仮説**: `auto_force_demoted_recovery.py` は `force_demoted` 集合から削除するだけで、削除後の Tier は base tier に戻る。22 戦略中に `_PAIR_PROMOTED` 残留があれば、復帰直後に**実弾発注**する。これは shadow-first 違反の最重大インシデント。

**実測**:
1. `algo_change_log` から `auto_recovery_from_force_demoted` を全件抽出
2. 各復帰戦略について、復帰直後 7 日 / 30 日の `oanda_audit` で `bridge_status='filled' AND is_live=1` の発注を SQL で集計
3. 実弾発注が発生した戦略を**全件列挙** (1 件でもあれば最優先 alert)
4. 該当戦略の `_PAIR_PROMOTED` 登録ペアを demo_trader.py から確認、shadow-first 違反の経路を再現

```sql
-- 例: 復帰直後の実弾発注検出
SELECT
  recov.timestamp AS recovery_time,
  recov.description,
  oa.timestamp AS order_time,
  oa.entry_type,
  oa.instrument,
  oa.bridge_status,
  oa.is_live,
  oa.units,
  oa.block_reason
FROM algo_change_log recov
LEFT JOIN oanda_audit oa
  ON oa.timestamp BETWEEN recov.timestamp
                     AND datetime(recov.timestamp, '+30 days')
 AND oa.bridge_status = 'filled'
 AND oa.is_live = 1
WHERE recov.change_type = 'auto_recovery_from_force_demoted'
ORDER BY recov.timestamp DESC, oa.timestamp ASC;
```

# 4. アウトプット要件

## 4.1. ファイル構成
- `audits/tier_promotion_consistency/2026-05-06_summary.md` — 全体サマリ + Verdict 表
- `audits/tier_promotion_consistency/2026-05-06_M1_wilson_dual_threshold.md` — M1 詳細
- `audits/tier_promotion_consistency/2026-05-06_M2_sentinel_bonferroni_gap.md` — M2 詳細
- 同様に M3〜M7 の個別ファイル
- `audits/tier_promotion_consistency/2026-05-06_data.json` — 全クエリ結果の生データ

## 4.2. Verdict ルール (各 M ごと)
- **CONFIRMED** — 仮説どおり矛盾あり、修正必要 (修正案を spec に書く)
- **REJECTED** — 仮説と異なり実害なし (理由を記述)
- **BLOCKED_DATA** — N 不足等で判定不可 (Wave 4 共通 blocker パターン、`project_w3_4_c1_london_blocked_data.md` 参照)

## 4.3. M7 専用エスカレーション
M7 で `is_live=1 AND bridge_status='filled'` 行が **1 件でも** 検出されたら、サマリ冒頭に **🚨 SHADOW-FIRST VIOLATION 🚨** を明示し、該当 SQL 結果と該当戦略名・取引時刻・PnL を列挙。司令塔は最優先で hot-fix 判断する。

## 4.4. レポート構造 (`feedback_w4_eda_audit_report_format.md`)
各 M ファイルは以下の構造:
1. **仮説** (司令塔が立てた)
2. **実測クエリ** (この spec に書いた SQL を実際に流したもの、コピペ可能形式)
3. **結果** (数値と表)
4. **Verdict** + 🔴🟠✅ emoji
5. **思想** (本来あるべき shadow-first / Bonferroni 整合)
6. **設計欠陥** (具体的にどこが壊れているか、file:line)
7. **再設計案** (Codex の提案、最小変更で fix できるか)

# 5. 制約

- 全クエリで `is_shadow` 分離必須
- 推測禁止 — 数値は全て SQL 結果から
- BT 必要なら `data/cache/massive/*.parquet` を使用 (Yahoo は 60 日制限で BT 不可)
- ローカル DB と Render API の不整合があれば Render を真値とする (`feedback_check_orphan_local_app.md`)
- 実装変更は禁止 (read-only audit)。修正案は spec 提案のみ

# 6. 完了条件

- [ ] M1〜M7 の個別レポート 7 本 + summary 1 本 = 計 8 ファイル
- [ ] 全 SQL クエリと結果が JSON に記録
- [ ] Verdict が CONFIRMED/REJECTED/BLOCKED_DATA のいずれかで全項目埋まっている
- [ ] M7 が CONFIRMED の場合、🚨 alert がサマリ冒頭に明示
- [ ] Codex 自身の **mock-only 自己テストで PASS** したと報告するのは禁止 (`feedback_codex_mock_test_trap.md`) — 実 SQLite 接続クエリ実行が必須

# 7. 司令塔チェックポイント

完了後、司令塔 (Claude Code) は以下を確認:
1. M7 alert の有無
2. 各 M の Verdict 整合性 (司令塔の演繹仮説と実測の乖離)
3. 修正案を Wave 5 ロードマップに統合可能か
4. 最重要矛盾を hot-fix Codex タスクに昇格させる優先順位


## Result (2026-05-06T11:07:49Z)

exit=0 · 21s

```
実行前 MUST チェックで orphan 条件に該当したため、監査を中断しました。

検出 PID: `1608`

補足: `pgrep` / `ps` が環境に存在しなかったため `/proc/*/cmdline` で代替検査しました。PID 検出後に cmdline を読もうとしましたが、その時点では `/proc/1608/cmdline` が消えており、プロセスは終了済みの可能性があります。

指定どおり、`demo_trades.db` 監査・Render API 照合・レポート生成には進んでいません。
```
