---
id: 20260608-2110-r2-audit-dedup-contamination-fix
priority: P0
gate: R3
rule: R3
status: done
created: 2026-06-08
owner: claude
---

> **2026-06-08 実行記録（Claude 直接実装）**
> - **Task 1 完了** ✅: `tools/shadow_promote_r2_alert.py` `filter_shadow_trades` と
>   `tools/r2_cell_demotion_audit.py` `filter_closed_shadow_rows` に `dedup_violation=1` 除外を追加。
>   レポートの "Filters:" 行に `dedup_violation != 1` 明記。
>   unit test `test_dedup_violation_rows_are_excluded` 追加（N=42→12 で CRITICAL 回避を検証）。
>   `pytest tests/test_shadow_promote_r2_alert.py tests/test_r2_cell_demotion_audit.py` = **12 passed**、
>   `scripts/check.py` 全6チェック通過。
>   **実データ A/B（同一 fetch）: shadow 1943→1627 = 316件(16%)除去。CRITICAL 14→11**
>   (sr_break_retest GBP_USD N63→39, sr_fib GBP_USD 67→40, xs_momentum 66/51/56→39/35/34;
>   sr_break_retest GBP_JPY/USD_JPY と sr_anti_hunt USD_JPY は N<30 に落ち CRITICAL から除外)。
> - **Task 3 診断済**（修正は未実施）: dedup_violation=1 は **28戦略・316件にわたり systemic**
>   (sr_fib 54 / xs_momentum 46 / wick_imbalance 45 / sr_break_retest 43 / sr_anti_hunt 27 …)。
>   単一戦略でなく共有 emit 層の per-bar dedup gate leak（vsg/rsk root cause と一致）。
> - **Task 3 root fix 完了** ✅: dedup_violation backfill window を TF-aware 化
>   (`modules/demo_db.py` `_tf_window_sec` 追加 + `_backfill_dedup_violation_impl` が tf を SELECT し
>   per-row window 使用)。**根本原因**: emit gate は TF-aware (15m→900s, 4h→14400s) で同一バー再emit を
>   shadow に振り替えるが (CLAUDE.md 原則3: shadow を時間ブロックしない設計)、backfill の固定 60s window が
>   60〜900s 差の同一バー dupe を flag しそびれ、dedup_violation=0 のまま R2 audit を汚染していた。
>   **実データ検証**: TF-aware で +282件 flag (315→597)、真の clean N=1943→**1346 (31%減)**。
>   bar_time は shadow の 24% しか無い (alpha_snapshot 空 = meta-loss バグ) ため bar_time 単独 dedup 不可、
>   TF-aware window が正解。unit test `test_tf_window_sec_mapping` /
>   `test_backfill_flags_same_15m_bar_reemit_beyond_60s` 追加。
> - **Task 2 root cause 完了**（コード修正不要と判定）: sr_anti_hunt_bounce EUR_JPY は **コードバグでなく
>   戦略パラメータ問題**。TP距離≈108pip / SL≈54pip が M15 バウンスには遠すぎ、max_hold 内で TP/SL に
>   到達せず全件 MAX_HOLD_TIME(勝)/TIME_DECAY_EXIT(負) で決済 → 「SRアンチハント」でなく EUR_JPY
>   上昇ドリフトを BUY+時間決済で拾っているだけ (W4-EDA「思想は正、設計が誤」型)。verdict: 昇格不可、
>   TP/hold パラメータ再設計 or EUR_JPY ではエッジ無し。demo_trader の exit ロジックは正常。
>
> **🔴 最重要結論**: TF-aware dedup 後、**全 promote 候補が N<30**
> (wick_imbalance EUR_USD audit48→clean **24**, dt_bb_rsi EUR_USD 35→17, donchian NZD_USD 15→10)。
> **現状 clean N で昇格資格のあるセルはゼロ** — 汚染が昇格レディネスを系統的に偽装していた。
> 全候補は shadow 継続で clean N≥30 を待つのが正順。
>
> status: **全 Task 完了（Claude 直接実装・検証）。Render deploy 後に backfill が 597 件を reflag → audit が clean N で再計算。**

# R2 Shadow Audit — dedup_violation 汚染除去 + sr_anti_hunt exit バグ調査

**Rule 分類**: R3（データ整合バグ / 統計の算数破綻。365日BTスキップ、derivation はこのタスクに記載済み）

## Background — Claude 検証で確定した違和感（一次データ実測）

Render 本番 API (`/api/demo/trades?limit=2000`, is_shadow=1, 30d, XAU除外, N=1943) を
Claude が直接引いて全クオンツバトリーを回した結果、**R2 shadow audit の統計が
`dedup_violation=1` の重複トレードで汚染されている**ことが確定した。

### 実測根拠

1. **dedup_violation=1 が全 shadow の 16%（317/1943）**。
   `tools/shadow_promote_r2_alert.py` の `filter_shadow_trades`（L204-223）は
   `is_shadow=1 / pnl_pips NOT NULL / XAU除外 / 30d` のみでフィルタし、
   **`dedup_violation` を除外していない**。→ 毎日の R2 alert（promote/demote 判断の根拠）の
   全セル N・WR・Wilson・PF が水増しされている。

2. **昇格閾値 N≥30 が幻の重複で達成されている**。dedup 除外で主要候補の N が半減:

   | セル | audit N (現状) | dedup除外 clean N | distinct_days |
   |---|---:|---:|---:|
   | wick_imbalance_reversion EUR_USD | 48 | **27** | 8 |
   | dt_bb_rsi_mr EUR_USD | 35 | **20** | 8 |
   | dt_bb_rsi_mr GBP_USD | 17 | 9 | 5 |
   | sr_anti_hunt_bounce EUR_JPY | 16 | 9 | 3 |
   | orb_trap GBP_USD | 9 | 5 | 3 |

   wick_imbalance EUR_USD は「N≥30 で昇格候補」に見えていたが clean N=27 で閾値未達。
   CRITICAL 側（N≥30 EV<0）も同様に inflation している可能性が高い。

3. **sr_anti_hunt_bounce EUR_JPY の PF=189.83 は完全な artifact**。生トレード検査で:
   - 全 16 件が `MAX_HOLD_TIME`（勝ち）/ `TIME_DECAY_EXIT`（負け）で決済。**TP/SL が一度も発火していない**
     （TP距離≈108pip, SL距離≈54pip に対し、決済は +14〜+32 と -0.2/-1.6）。
   - 全 BUY、05-25〜05-27 の 3 日に集中（独立観測でなく一方向ドリフトの反復サンプリング）。
   - dedup ペア多数（32.0/32.0, 16.5/16.5 等、10-20秒差の同一シグナル二重計上）。
   - MEMORY `project_sr_anti_hunt_demo_trades_meta_loss`（confluence engine ImportError /
     alpha_snapshot 空）と整合。exit ロジックが壊れて時間切れ決済に落ちている疑い。

## やること

### Task 1（P0, 確実な修正）: R2 audit から dedup_violation を除外
- `tools/shadow_promote_r2_alert.py` `filter_shadow_trades` に
  `dedup_violation=1` を除外する条件を追加（`int(trade.get("dedup_violation", 0) or 0) == 1` を skip）。
- 同じフィルタ基準を使う他の audit/watchdog も揃える:
  `tools/edge_cell_watchdog.py` / `tools/post_promotion_watchdog.py` /
  `tools/r2_cell_demotion_audit.py` / `modules/shadow_demote_registry.py` 経由の集計。
  → grep で `is_shadow` フィルタを持つ集計箇所を洗い出し、dedup 除外を統一適用。
- レポートの "Filters:" 行に `dedup_violation != 1` を明記。
- **検証**: 修正後に audit を再走 → N が約 16% 減、CRITICAL/WARN セル数が変動することを before/after で出力。
  既存テスト（あれば `tests/` の r2 alert 系）を更新し、dedup 除外の unit test を追加。

### Task 2（P1, 調査）: sr_anti_hunt_bounce EUR_JPY の exit バグ
- なぜ TP/SL が発火せず MAX_HOLD_TIME / TIME_DECAY_EXIT のみになるのか調査。
  `modules/demo_trader.py` の close 判定ロジック + sr_anti_hunt の confluence engine 依存
  （pyarrow / alpha_snapshot）を確認。
- 原因を `knowledge-base/wiki/decisions/` に文書化。修正可能なら hot-fix、不可なら当該セルを
  shadow_demote_registry に追加して隔離。

### Task 3（P1, 根治）: per-bar dedup gate の leak
- そもそも 16% の dedup_violation=1 が**記録されている**＝ entry 時の per-bar dedup gate が
  leak している。`tools/per_bar_dedup_audit.py` / `tools/dedup_violation_triage.py` の既存知見を使い、
  どの戦略/経路で二重 entry が発生しているか集計し、gate 修正案を decisions/ に提示。
  （MEMORY: vsg/rsk per-bar dedup runaway と同根の可能性）

## 完了条件
- Task 1 merge 済み（audit が dedup 除外、before/after の N・CRITICAL 数を final.md に記載）。
- Task 2/3 は調査結果を decisions/ に文書化（修正は別タスク可）。
- **重要**: clean N で再計算した promote 候補リスト（特に wick_imbalance EUR_USD が
  clean N≥30 に到達しているか）を final.md に出すこと。Claude 司令塔が昇格判断に使う。

## データ取得方法（Codex 用）
Render Postgres は本プロジェクトでは SQLite-only 運用のため、一次ソースは
`https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`（urllib で取得、上記フィルタ）。
ローカル DB は orphan 汚染の恐れがあるため使わない（MEMORY `feedback_check_orphan_local_app`）。
