# Live 解凍 Gate — 2026-04-27 (rule:R1)

## 起票背景

memory 175 (2026-04-26 23:17 JST) によれば、システムは:

- **Aggregate Kelly = -17.97%**
- **DD = 32.32%**
- **Live N = 36 のみ**

の危機的状態にある。Kelly が負である以上、規律上は **Live=0%, lot=0** が正解だが、システムは Shadow 観測を継続している(これは正しい — 撤退ではなく観測継続)。

問題は「**いつ Live を解凍するか**」の判断が文書化されていないこと。本文書は **感情駆動を排除し、データ条件で再開を決定する**ため、4 条件 (AND) を pre-register する。

## 解凍条件 — 全 4 項目を満たすまで Live=0% 維持

### G1. Aggregate Kelly が seed-exclusion 適用後で正に転換

```
exec: python3 tools/risk_check.py --kelly --exclude-seed
require: kelly > 0
```

**根拠**: 2026-04-27 commit 9e53794 で seed/backfill replay の 16 件 instant-exit を集計から除外する `exclude_seed=True` を default 化した。これにより fib_reversal の inflate された WR/PF が補正される。Kelly が補正後でも負のままなら **構造的 negative edge** であり、母集団修正で消える種類のものではない。lot 投入は禁止。

### G2. ELITE_LIVE 候補が cell-level Wilson > BEV を達成

```
exec: python3 tools/cell_edge_audit.py \
    --strategies bb_rsi_reversion,fib_reversal \
    --metric wilson_lower \
    --threshold bev
require: 該当 (strategy × pair × dow × hour) cell が ≥ 1 件
```

**根拠**: net_edge_audit の `--all` 結果 (2026-04-27) で `bb_rsi_reversion` (N=32 strat 47% Wilson 31% bench 27%) と `fib_reversal` (N=31 strat 48% Wilson 32% bench 19%) が aggregate net_edge 正のシグナル。ただし aggregate fallacy (CLAUDE.md 「過去の同種ミス」#1) の轍を踏まないため、**cell ごとの Wilson 下限が BEV を超えていることを必須**とする。

### G3. SR Anti-Hunt EUR_USD Sentinel が N≥30 で WR>60% かつ Wilson 下限>55%

```
exec: python3 tools/net_edge_audit.py --strategy sr_anti_hunt_bounce \
    --filter instrument=EUR_USD --db demo_trades.db
require: n_strat >= 30 AND strat_wr > 0.60 AND strat_wilson_lower > 0.55
```

**根拠**: SR Anti-Hunt 戦略は 365d audit で EUR_USD 67.9% (N=81) を示すが、これは hunt パターンを後付けで選んだ生存バイアスの可能性あり。**前向き Sentinel 30 trades の Wilson 下限が 55% を維持できれば**、生存バイアス疑惑は実質的に否定される (BT WR 67.9% から Live WR 55%+ への崩壊許容幅 ~13pt は妥当)。GBP_USD は Wilson 下限がぎりぎり 50% を割るため Sentinel 化は別途判断。

### G4. 直近 14 日の DD < 10%

```
exec: python3 tools/risk_check.py --dd --window 14d
require: max_dd_14d < 0.10
```

**根拠**: 現在 DD=32.32% という critical 状態は単一 Kelly 値で再開するには危険すぎる。**新規 Kelly 計算が DD≧30% 環境下で行われた場合、Kelly の分母 (initial equity) が既に target equity を 32% 下回っているため、recovery 必要 lot は名目 Kelly より大きくなる**。先に DD を回復させてから lot 計算するのが規律。

## 解凍プロセス

全 4 条件 (G1 ∧ G2 ∧ G3 ∧ G4) が満たされた時点で:

1. **段階的 lot 復帰**: 初期 lot = Kelly Half × 0.5 (= Kelly Quarter 相当). G1-G3 の signal が 7 日連続安定したら Kelly Half 通常へ昇格.
2. **Watch list**: net_edge_audit を毎朝実行 (`tools/daily_live_monitor.py` に統合済). 任意の Live 戦略が **net_edge_wr_pt < -10pt かつ N≥10** に達したら **即時 lot=0** に戻す (Rule 2 reactive demote).
3. **ELITE_LIVE candidate gate**: 解凍時に `_ELITE_LIVE` セットへの新規追加は禁止. 既存メンバーのみで再開し、新規候補は別途 Phase 4 BT (pre-reg LOCK) を通過後.

## 検証コマンド (再現性)

```bash
# 解凍可否を一発で判定:
python3 tools/live_thaw_check.py --db demo_trades.db
# 期待出力: PASS (4/4)  または  BLOCKED (G2 missing, G4 missing)
```

**TODO**: `tools/live_thaw_check.py` は未実装. P1 で本文書のロジックを実装する.

## 撤回条件

本 gate が満たされた後でも以下のいずれかで **即時 Live=0 に戻す**:

| 条件 | 判定 | rule |
|------|------|------|
| 連続 SL_HIT 4 回以上 (24h) | demo_trader.py 既存 circuit_breaker | R3 (構造) |
| 同戦略 Live N≥10 で WR<35% | daily_live_monitor の rollback alert | R2 (reactive) |
| 全戦略合計 DD>15% (7d) | risk_analytics watchdog | R3 |
| net_edge_audit alert (-15pt 以上) を **2 戦略**で同時検出 | daily_live_monitor (P0-2) | R2 |

## 関連文書

- 本日のクオンツ提案ロードマップ: `~/.claude/plans/intraday-seasonality-shadow-delightful-zebra.md`
- net_edge 集計仕様: `tools/net_edge_audit.py`
- seed-exclusion 仕様: `modules/demo_db.py` (`SEED_HOLD_SEC_THRESHOLD = 5`)
- dedup guard: `modules/demo_trader.py` `_recent_signal_emits`
- SR Anti-Hunt Phase 4 BT pre-reg LOCK: 未起票 (P1-1 で起票予定)

## 改訂履歴

| 日付 | 変更 |
|------|------|
| 2026-04-27 | 初版起票. 4 条件 + 撤回条件 + 段階的 lot 復帰プロセス定義. |
