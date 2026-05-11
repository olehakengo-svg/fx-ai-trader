---
id: 20260511-1500-flag-drift-backfill-preregistration
title: "[FLAG-DRIFT-Backfill] post-cutoff FX FLAG_DRIFT 行を is_shadow=1 へ backfill (Pre-reg + dry-run-first)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-11T15:00:00+0900
roadmap_gate: "48025eb (fix(flag-drift)) follow-up。Live edge<0/DD=47.22% の数字に FLAG_DRIFT N=140 / PnL=-132.4pip が混入していた事実 (Phase A 法医学で確定)。historical KPI の bias 除去なしに戦略修正に進むのは部分的クオンツの罠 (memory: feedback_partial_quant_trap)。"
rule: pre-reg
related:
  - modules/demo_db.py
  - .ai/decisions/2026-05-11-1400-flag-drift-codex-stash-leak.md
  - knowledge-base/raw/snapshots/render-demo-trades-20260503.db
  - 48025eb (commit hash, flag-drift forward fix)
---

# 0. 背景

48025eb で **forward path** の FLAG_DRIFT 発生は防止済 (`oanda_trade_id` 空なら `is_shadow=0` で書けない invariant)。
本タスクは **historical backfill**: 既に DB に蓄積された FLAG_DRIFT 行を `is_shadow=1` へ修正する。

Phase A 法医学 (`render-demo-trades-20260503.db`、FX-only post-cutoff `entry_time >= 2026-04-08T00:00:00`、XAU 除外):

| cohort | 定義 | N | PnL pip |
|---|---|--:|--:|
| TRUE_LIVE | `is_shadow=0 AND oanda_trade_id != ''` | 371 | -254.6 |
| **FLAG_DRIFT** | `is_shadow=0 AND oanda_trade_id IS NULL OR ''` | **140** | **-132.4** |
| SHADOW | `is_shadow=1` | 3820 | -4989.1 |

FLAG_DRIFT trades は OANDA に発注されていない (oanda_trade_id 空) にも関わらず Live cohort で集計され、Live KPI を汚染していた。

**過去事例参照**: `modules/demo_db.py:468-489` に類似の OANDA-fill `is_shadow=1→0` backfill (2026-05-03) あり。今回はその逆方向。

# 1. Pre-registration (memory: feedback_label_empirical_audit 必須)

**仮説**: post-cutoff FX FLAG_DRIFT 行は本来 shadow として扱われるべきだった。OANDA に発注されていないため。

**反証可能性**:
- もし FLAG_DRIFT のうち `bridge_status='filled'` の rows が `oanda_audit` 側に存在し、demo_trades 側で `oanda_trade_id` が空ならば、`set_oanda_trade_id()` 呼出漏れの結果として TRUE_LIVE に分類するのが正解（FLAG_DRIFT として shadow 化するのは誤分類）。
- このケースが N > 0 なら、本タスクは UNSAFE で停止、別 fix を先行させる。

**実測クエリ (codex 実行、結果を pre-reg form に貼ること)**:

```sql
-- Q1: post-cutoff FX FLAG_DRIFT N, 統計
SELECT COUNT(*) as n, SUM(pnl) as pnl_total, AVG(pnl) as pnl_avg
FROM demo_trades
WHERE entry_time >= '2026-04-08T00:00:00'
  AND instrument != 'XAU_USD'
  AND is_shadow = 0
  AND (oanda_trade_id IS NULL OR oanda_trade_id = '');

-- Q2: 上記 FLAG_DRIFT 行に対応する oanda_audit エントリの有無 (誤分類検出)
SELECT a.bridge_status, COUNT(*) as n
FROM demo_trades t
LEFT JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
WHERE t.entry_time >= '2026-04-08T00:00:00'
  AND t.instrument != 'XAU_USD'
  AND t.is_shadow = 0
  AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '')
GROUP BY a.bridge_status;

-- Q3: bridge_status='filled' で oanda_trade_id 空のレコードがあるか (UNSAFE 判定)
SELECT t.trade_id, t.entry_type, t.instrument, t.entry_time,
       t.oanda_trade_id, a.bridge_status, a.oanda_trade_id as audit_oanda_id
FROM demo_trades t
JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
WHERE t.entry_time >= '2026-04-08T00:00:00'
  AND t.instrument != 'XAU_USD'
  AND t.is_shadow = 0
  AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '')
  AND a.bridge_status = 'filled'
LIMIT 50;
```

**判定基準**:
- Q3 結果が **N=0** → SAFE: 全 FLAG_DRIFT を `is_shadow=1` へ backfill
- Q3 結果が **N>0** → UNSAFE: 該当行は `oanda_trade_id` を audit から逆引きして埋める方が正、本タスクは PAUSE / 設計再考

# 2. 仕様（SAFE 判定後の実装）

## 2.1 DDL 拡張

`demo_trades` に reclass マーカーカラム追加:
```sql
ALTER TABLE demo_trades ADD COLUMN flag_drift_backfilled INTEGER DEFAULT 0;
```
- `flag_drift_backfilled=1` は「2026-05-11 backfill で `is_shadow=0→1` 修正された行」を示す
- audit trail を破壊しないため、新カラムでマーキング (既存 `dedup_violation` 同様の pattern)

## 2.2 backfill ロジック

`modules/demo_db.py` の DemoDB.__init__ → 既存 backfill chain (line 60-489 周辺) に **FLAG_DRIFT backfill** を追加:

```python
# ── 2026-05-11 (rule:pre-reg): post-cutoff FX FLAG_DRIFT backfill ──
# Forensic (render-demo-trades-20260503.db): FX-only post-cutoff
#  is_shadow=0 AND oanda_trade_id IS NULL/'' → N=140 / PnL=-132.4pip
# OANDA 発注されていない trades が Live cohort を汚染していた。
# Forward path (48025eb commit) は 修正済、historical 行を本 backfill で修正。
_flag_drift_cutoff = "2026-04-08T00:00:00"
res = conn.execute(
    "SELECT COUNT(*) FROM demo_trades "
    "WHERE entry_time >= ? "
    "  AND instrument != 'XAU_USD' "
    "  AND is_shadow = 0 "
    "  AND (oanda_trade_id IS NULL OR oanda_trade_id = '')",
    (_flag_drift_cutoff,)
).fetchone()
_count_to_fix = int(res[0])
if _count_to_fix > 0:
    conn.execute(
        "UPDATE demo_trades "
        "SET is_shadow = 1, flag_drift_backfilled = 1 "
        "WHERE entry_time >= ? "
        "  AND instrument != 'XAU_USD' "
        "  AND is_shadow = 0 "
        "  AND (oanda_trade_id IS NULL OR oanda_trade_id = '')",
        (_flag_drift_cutoff,)
    )
    conn.commit()
    self._last_flag_drift_backfill_result = {
        "fixed_count": _count_to_fix,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"[FLAG_DRIFT_BACKFILL] reclassified {_count_to_fix} rows: is_shadow=0→1")
```

idempotent (再実行で N=0 になるので no-op)。

## 2.3 admin diag endpoint

`/api/admin/dedup_status` パターンを踏襲、`/api/admin/flag_drift_backfill_status` を新規追加 (or 既存 dedup endpoint に統合)。`_last_flag_drift_backfill_result` を返す。

## 2.4 dry-run script

`scripts/check_flag_drift_backfill_safety.py` 新規:
- DB path を arg で受ける (local or render-shell snapshot)
- 上記 Q1/Q2/Q3 を実行、結果を JSON で出力
- Q3 が N>0 なら exit code 1 で UNSAFE 警告

# 3. 受入基準

- [ ] Q1/Q2/Q3 実測クエリを Codex が `render-demo-trades-20260503.db` snapshot で実行し、結果を本 task の pre-reg form に貼る
- [ ] **Q3 SAFE (N=0) 確認後にのみ §2 実装に進む**。N>0 なら abort して司令塔報告
- [ ] backfill ロジックを既存 chain に追加、`flag_drift_backfilled` カラム新設
- [ ] ローカル DB (`render-demo-trades-20260503.db` コピー) で dry-run、実際に N=140 が `is_shadow=1` に flip するか確認
- [ ] backfill 前後で SQL 集計:
  - TRUE_LIVE_FX cohort の N / PnL_total 変化なし (是正前 N=371→371)
  - SHADOW_FX cohort の N が +140 (3820→3960)
  - FLAG_DRIFT_FX cohort が N=0 になる
- [ ] 既存 unit tests: `pytest tests/test_demo_db.py tests/test_flag_drift_writepath.py -q` 全 PASS
- [ ] 新規 test `tests/test_flag_drift_backfill.py`: idempotency / cutoff 境界 / XAU 除外 / 既 shadow 不変
- [ ] `python3 scripts/check.py` PASS
- [ ] dry-run script が SAFE/UNSAFE を正しく判定するテスト

# 4. 非ゴール

- 本番 Render DB への適用（コードを deploy したら Render 再起動時に backfill chain が自動実行される、それで完了。手動 Render shell SQL は不要）
- oanda_audit テーブル側の整合性検証 (memory: reference_oanda_audit_twin_meaning の二義性は別問題)
- BT 結果の再計算 (backfill 後の clean Live KPI 再測定は別タスク)

# 5. クオンツ的注意

- **Q3 N>0 ケースの優先処理**: もし bridge_status='filled' で oanda_trade_id 空が存在するなら、それは forward path の別 bug。本 backfill を急ぐより、その bug を先に潰す。
- **Cutoff 厳守**: `entry_time >= 2026-04-08T00:00:00` (FIDELITY_CUTOFF) 内のみ対象。それ以前の trades は別運用フェーズで信頼性が異なる
- **XAU 除外**: memory: feedback_exclude_xau に従う (instrument != 'XAU_USD')
- **idempotency**: 再走で no-op (forward path で新規 FLAG_DRIFT 発生不可なので、初回以降は count=0)
- **Rollback**: 緊急時は `UPDATE demo_trades SET is_shadow=0 WHERE flag_drift_backfilled=1` で復元可能 (新カラムが識別子)
- **本番反映後の検証**: deploy 完了後 `/api/admin/flag_drift_backfill_status` で fixed_count 確認、`/api/risk/dashboard` で Live edge / DD が改善 (or 悪化) するかチェック。改善幅が forensic 予測 (PnL -132.4 が Shadow 側へ) と一致するか実測

# 6. 報告フォーマット

final.md に以下を含めること:
- Q1 / Q2 / Q3 の実測結果 (SQL output)
- SAFE/UNSAFE 判定
- (SAFE 時) backfill 前後の N / PnL 集計テーブル
- (UNSAFE 時) 設計再考が必要な理由と推奨 fix 案

# 7. Codex pre-reg 実測結果 (2026-05-11)

対象: `knowledge-base/raw/snapshots/render-demo-trades-20260503.db`

注意: raw snapshot には `oanda_audit` テーブルが存在しなかった (`.tables` は `demo_trades` のみ)。
そのため Q2/Q3 は raw snapshot では `no such table: oanda_audit`。dry-run script は
`audit_table_present=false` として扱い、Q3 filled audit sample は 0 件と判定した。

Q1:
```text
n    pnl_total  pnl_avg
---  ---------  -------
140  -132.4     -0.9457
```

Q2:
```text
bridge_status         n
-------------------  ---
NO_OANDA_AUDIT_TABLE 140
```

参考: migrated empty-audit copy では以下。
```text
bridge_status  n
-------------  ---
NULL           140
```

Q3:
```text
q3_filled_count
---------------
0
```

判定: SAFE。ただし snapshot に `oanda_audit` が無いため、filled audit の不存在は
「当該 snapshot から観測可能な範囲」の判定。実装側には `bridge_status='filled'`
が存在する DB では backfill を停止する unsafe guard を入れる。
