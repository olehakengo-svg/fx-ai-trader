---
title: SHADOW_EMIT 60s dedup gate 不在による汚染データ蓄積イベント
date: 2026-04-30
type: decision
severity: HIGH
related: [[../lessons/lesson-shadow-emit-dedup-2026-04-30]], [[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]], [[../lessons/lesson-select-best-bottleneck-2026-04-28]], [[phase10-g2-investigation-2026-04-29]], [[../strategies/vsg_jpy_reversal]], [[../strategies/rsk_gbpjpy_reversion]], [[../strategies/mqe_gbpusd_fix]]
---

# SHADOW_EMIT 60s dedup gate 不在による汚染データ蓄積イベント (2026-04-30)

## サマリー

2026-04-29 〜 2026-04-30 の間、Phase 10 G2 で SHADOW_ALWAYS_STRATEGIES に投入された 3 戦略 (`vsg_jpy_reversal`, `rsk_gbpjpy_reversion`, `mqe_gbpusd_fix`) が、`shadow_emit_signals` 経路の 60s dedup gate 不在により tick 毎に shadow trade として量産された。本番 demo_trades DB の N=204 sample 中 98 件の SHADOW_ALWAYS shadow のうち **68 件 (69.4%)** が同一 (entry_type, instrument, direction) の 60s window 内 2 件目以降の重複だった。

`mqe_gbpusd_fix` 単独で 2026-04-29 15:00 UTC の 1 時間に **78 件** emit (≈ 46 秒に 1 件)、同 minute bar 内で n=4 の emit が 11 分連続。

## タイムライン

| 時刻 (UTC) | イベント | commit |
|---|---|---|
| 2026-04-29 ~03:00 | Phase 10 G2 で 3 戦略を SHADOW_ALWAYS に投入 | `febe1cd` |
| 2026-04-29 06:58〜21:43 | 汚染期間 (98 件サンプル中、最初〜最後の SHADOW_ALWAYS shadow emit) | — |
| 2026-04-30 02:42 | 60s dedup gate 移植 commit | `6a45bb2` |
| 2026-04-30 02:55 | lesson 文書作成 | `4e54363` |
| 2026-04-30 03:42 | 共通 helper `_maybe_reserve_signal_emit` 抽出 (構造的予防) | `fbef071` |
| 2026-04-30 03:52 | `dedup_violation` 列 + 起動時 backfill 実装 | `13eb929` |
| 2026-04-30 04:25 | 診断エンドポイント `/api/admin/dedup_status` + verbose log 追加 | `4c2bebd` |

## 影響範囲

### 直接的な影響 (構造的)

- **demo_trades テーブル**: 2026-04-29 ~ 2026-04-30 02:42 UTC の SHADOW_ALWAYS shadow 行が tick-frequency で重複生成されていた (推定 60-150 倍の N 膨張)。
- **learning_engine の Wilson/Kelly 計算**: 独立試行を前提とする統計が、強相関な observation で計算されていた。実 effective_N より見かけの N が大きいため:
  - Wilson CI 下限が **過小幅化** (overconfident)
  - Bonferroni 補正の n_test_eff が過小推定
  - Kelly fraction が **over-stated** → 本番昇格判定で誤った GO サインが出るリスク
- **Sentinel 評価 (`get_shadow_trades_for_evaluation`)**: 同上。Live N≥30 → OANDA 昇格 gate がもし auto で動作していたら、**統計的根拠ゼロで本番昇格していた可能性**。本イベントの最大級の潜在リスク。

### 確認された / 未確認の昇格副次影響

- **未確認 (要監査)**: 当該 3 戦略の `is_shadow=0` (live) 行が auto promotion により発生したか、`oanda_trades` テーブルに forwarding されたか。
- **既知**: lesson-shadow-always-emit-cleanup-2026-04-28 と同じ pattern。前回 (sr_anti / sr_liquid) は `EV<0` 確定で N=300 蓄積後に発覚 → `frozenset()` 化で出血止め。今回は **昇格 1 日後** に発覚 → 60s dedup gate 移植で構造的根治。

## 採用した対応 (今回確定)

### A. 構造的修正 (commit `6a45bb2`, `fbef071`)

`shadow_emit_signals` ループに、primary trade と key 空間共有の 60s dedup を移植。さらに `_maybe_reserve_signal_emit` ヘルパーに集約することで、将来の variant / sentinel / その他 bypass 経路を追加した際も自動的に dedup 共有される構造に変更。

### B. 過去汚染の non-destructive flag 化 (commit `13eb929`, `4c2bebd`)

`demo_trades` に `dedup_violation INTEGER DEFAULT 0` 列を追加。`DemoDB.__init__` で post-hoc backfill を実行し、`entry_time < 2026-04-30T02:42:00 UTC` × `is_shadow=1` × `entry_type IN (vsg, rsk, mqe)` に対し runtime と同等の 60s window 判定で 2 件目以降を `dedup_violation=1` に flag。

`get_stats()` および `get_shadow_trades_for_evaluation()` に `AND dedup_violation = 0` フィルタを追加し、汚染データを Wilson/Kelly/Bonferroni の入力から除外。

`/api/admin/dedup_status` (GET) と `/api/admin/dedup_run` (POST, Bearer) を追加し、backfill 結果の検証と再実行を可能にした。

### C. SHADOW_ALWAYS 維持 (user 判断)

候補 P0-B として「`SHADOW_ALWAYS_STRATEGIES = frozenset()` で一時停止」を提案したが、ユーザー判断で却下:

- 修正 (A) deploy 後の新規 emit は既にクリーン
- 過去汚染は flag 化 (B) で分析層から除外
- CLAUDE.md 4原則 #1「マーケット開いてる間は攻める」と整合
- pause は事後 demote (Rule 2) ではなく pre-emptive halt で発動条件を満たさない

## 採用しなかった対応とその理由

| 案 | 却下理由 |
|---|---|
| `DELETE FROM demo_trades WHERE dedup_violation = 1` (物理削除) | データ自体は実フィル価格・実 outcome を持っており、後の post-hoc 分析機会を失う。flag 化なら「もし dedup があったら」のシミュレーションが可能。 |
| `SHADOW_ALWAYS = frozenset()` 一時停止 | 上記 user 判断。修正 + flag 化で十分。 |
| 全 shadow 経路に dedup を強制適用 | shadow_variants / Sentinel 等の他経路は既に異なる dedup ロジックを持ち、一括適用は副作用リスク。`_maybe_reserve_signal_emit` ヘルパーで「呼び出し側が選択する」形が妥当。 |

## クオンツ規律違反としての分類

### Rule 違反

- **R3 違反検知の遅れ**: `lesson-shadow-always-emit-cleanup-2026-04-28` で「per-bar dedup なし」が既知だった構造的脆弱性が、Phase 10 G2 (`febe1cd`) で再投入された際に事前検証されなかった。
- **partial quant trap**: `is_shadow=1` の N が tick 数分インフレしていた事実を、**ユーザー目視まで気づけなかった**。N の数だけ見て N の質を見ていない構造。
- **本番監視の欠落**: `is_shadow=1` per-minute 件数の異常検知アラートが未実装だった。

### Rule 1 妥当性疑い (別問題、本イベント外で要監査)

`febe1cd` commit で 3 戦略を SHADOW_ALWAYS に投入した根拠は **BT 20 signals / Bonferroni 7-13 通過**。CLAUDE.md Rule 1 の閾値「365日BT or Live N≥30 + Bonferroni + Pre-reg LOCK」に対し、BT N=20 は閾値未満。これが Rule 3 (構造バグ修正) を装って Rule 1 (新戦略) を実行した可能性は別途 audit が必要 (本 decision の scope 外)。

## 構造的対策 (P2、次セッション以降)

1. **本番アラート SQL** — `daily_review` に dup-check を組み込み:
   ```sql
   SELECT entry_type, instrument, COUNT(*) AS n
   FROM demo_trades
   WHERE is_shadow = 1
     AND entry_time >= NOW() - INTERVAL '1 hour'
   GROUP BY entry_type, instrument, date_trunc('minute', entry_time)
   HAVING COUNT(*) > 1;
   ```
   `HAVING COUNT(*) > 1` ヒット時 Discord 通知。

2. **SHADOW_ALWAYS_STRATEGIES 追加時の pre-flight チェックリスト**:
   - [ ] 当該経路で `_recent_signal_emits` または共通 gate helper を経由しているか
   - [ ] 過去 24h の本番 demo_trades で同一 (entry_type, instrument, signal) bar が COUNT(*) > 1 でヒットしないか
   - [ ] N 集計が tick 数ではなく実シグナル発火回数で割られているか

3. **BT/Live ロジック統一の実証** — `_bt_signal()` も `_maybe_reserve_signal_emit` 等価の dedup を持たせ、BT-Live 非対称を排除。

## 検証 (post-deploy 実測)

### 過程で発見した二次バグ

最初の commit `13eb929` で backfill が `total_flagged=0` のまま動作しなかった。診断機構を追加した commit `d08b8d5` で `last_startup_backfill_result` を expose したところ:

```json
{
  "error": "name 'timedelta' is not defined",
  "status": "exception",
  "type": "NameError",
  "traceback": "File demo_db.py line 492 in _backfill_dedup_violation_impl..."
}
```

`from datetime import datetime, timedelta, timezone` の `timedelta` を import 漏れしていた。commit `b6f54d5` で修正、deploy 後に正常動作。

**教訓**: 例外を catch して戻り値 dict で診断可能にする構造のおかげで原因特定可能だった。silent except だと「動かない理由」が永遠に不明だった。

### `/api/admin/dedup_status` post-fix 出力

```json
{
  "by_target": [
    {"entry_type": "mqe_gbpusd_fix",   "is_shadow": 1, "dedup_violation": 0, "n": 26},
    {"entry_type": "mqe_gbpusd_fix",   "is_shadow": 1, "dedup_violation": 1, "n": 60},
    {"entry_type": "vsg_jpy_reversal", "is_shadow": 1, "dedup_violation": 0, "n":  4},
    {"entry_type": "vsg_jpy_reversal", "is_shadow": 1, "dedup_violation": 1, "n":  8}
  ],
  "candidates_remaining": 30,
  "total_flagged": 68,
  "last_startup_backfill_result": {
    "status": "flagged",
    "flagged": 68,
    "rows_examined": 98,
    "unique_keys": 30
  }
}
```

シミュレーション予測 (98 → 68 flagged / 30 keep) と完全一致。

### `/api/demo/stats` Wilson CI 補正効果

| 戦略 | N (pre→post) | WR (pre→post) | Wilson_BF (pre→post) |
|---|---|---|---|
| `vsg_jpy_reversal` | 12 → **4** | 83.3% → 75.0% | 37.4% → **15.5%** |
| `mqe_gbpusd_fix` | 86 → **26** | 46.5% → 46.2% | 30.2% → **20.2%** |

Wilson_BF 下限が ~50% 縮小。「データ多くて高 confidence」だった見かけが「データ少なくて慎重判断必要」に正規化。これが真実の statistical state。

### 診断 endpoint 一覧 (今回追加)

- `GET /api/admin/dedup_status` — 現状の cross-tab + last startup result (no-auth, read-only)
- `POST /api/admin/dedup_run` — backfill 強制再実行 (Bearer 必須、idempotent)

## クロスリファレンス

- 静的解析証拠: [[../lessons/lesson-shadow-emit-dedup-2026-04-30]] §1-2
- 修正実装詳細: commit `6a45bb2` (gate 移植), `fbef071` (helper 抽出), `13eb929` (flag 化), `4c2bebd` (診断)
- 前回の同種問題: [[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]]
- 関連戦略: [[../strategies/vsg_jpy_reversal]], [[../strategies/rsk_gbpjpy_reversion]], [[../strategies/mqe_gbpusd_fix]]
