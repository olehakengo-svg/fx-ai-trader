---
title: SR Anti-Hunt-Bounce / Liquidity-Grab — signal-to-trade pipeline gap (G3 N=0 root cause)
date: 2026-04-28
type: bug-finding + architectural-proposal
related: [[live-thaw-gate-2026-04-27]], [[../strategies/sr-anti-hunt-bounce]]
---

# SR strategies が Shadow trade を生成しない根本原因 (2026-04-28)

## Trigger

- live_thaw_check.py で **G3 SR Anti-Hunt EUR_USD Sentinel N=0** (BLOCKED)
- commit 4bc55bd (10:35 JST) で `sr_anti_hunt_bounce` + `sr_liquidity_grab` を `enabled=True` で integrate
- 24h 経過しても production trades に該当 entry_type が **0 件**
- 私の前回 audit で「commit と engine state が乖離」と誤指摘 → 実際は engine 登録済

## クオンツ規律

- ラベル実測主義: コード演繹ではなく hunt_event log と demo_trades.db を実走査
- 部分的クオンツの罠回避: signal 数 / trade 数 / score 分布の三段検証

## 実測

### Step 1 — 戦略は実際に signal を発射している
```
$ wc -l knowledge-base/raw/hunt_events/2026-04-28.jsonl
81 events (24h)
  sr_anti_hunt_bounce: 46
  sr_liquidity_grab:   35
  EURUSD=X: 73, EURJPY=X: 7, USD_JPY: 1
```

`hunt_event_logger.log_hunt_event()` は Candidate を return する**直前**に呼ばれる
([sr_anti_hunt_bounce.py L127-137](../../strategies/daytrade/sr_anti_hunt_bounce.py)) ため、
**81 events = 81 actual signal emissions**.

### Step 2 — Trade DB には 0 件
```
$ sqlite3 demo_trades.db "SELECT entry_type, COUNT(*) FROM demo_trades
  WHERE entry_type IN ('sr_anti_hunt_bounce','sr_liquidity_grab')
  AND entry_time >= datetime('now','-1 day')"
  → 0 件

直近1時間の全 entry_type:
  ema200_trend_reversal: 2
  dt_bb_rsi_mr:          1
  squeeze_release_momentum: 1
```

### Step 3 — Score competition で構造的敗北
DT 戦略の score 分布 (`grep "score = " strategies/daytrade/*.py`):

| Score | 戦略 |
|---:|---|
| 6.0 | inducement_ob |
| 5.5 | session_time_bias, london_fix_reversal, alpha_atr_regime_break, tokyo_range_breakout |
| 5.0 | post_news_vol, alpha_wick_imbalance, trendline_sweep, alpha_intraday_seasonality |
| 4.5 | jpy_basket_trend, mqe_gbpusd_fix, vol_spike_mr, london_close_reversal, orb_trap |
| 4.0 | doji_breakout, asia_range_fade_v1 |
| 3.5 | **sr_liquidity_grab**, london_close_reversal_v2, ema200_reversal, london_ny_swing |
| **3.0** | **sr_anti_hunt_bounce ← lowest** |

`DaytradeEngine.select_best()` (strategies/daytrade/__init__.py L172) は単純に
`max(candidates, key=lambda c: c.score)` で **1 strategy/bar** を選択。
SR Anti-Hunt は score=3.0 で全 DT 戦略の最下位 → **毎 bar で構造的敗北**。

### Step 4 — `enabled=True` コメントの誤解
[sr_anti_hunt_bounce.py L33](../../strategies/daytrade/sr_anti_hunt_bounce.py):
```python
enabled = True   # Shadow 全走で data 蓄積 (PAIR_PROMOTED 不在で OANDA は default Sentinel)
```
作者は「`enabled=True` で全走 (= 全 candidate が trade になる)」と想定していたが、
実際は `enabled=True` は「evaluate() が呼ばれる」だけで、
**`select_best` の max-score 選別**を通過しなければ trade にならない。

→ **commit 4bc55bd の "Shadow 全走で data 蓄積" は設計バグ**

## Root Cause

**Signal evaluation と trade creation の間に max-score selector があり、
SR 系 (低スコア strategy) は毎 bar で他戦略に敗北。
`hunt_event_logger` には記録されるが、shadow trade として DB 永続化されない**

## 影響範囲

直近 commit で同じバグを抱える他戦略:
- `sr_anti_hunt_bounce` (score=3.0) ← 最重症
- `sr_liquidity_grab` (score=3.5)
- `london_close_reversal_v2` (score=3.5)
- `ema200_reversal` (conditional 3.5)
- `london_ny_swing` (conditional 3.5)

これら全部が `enabled=True` でも **score 競争で敗北し続けて N が貯まらない**

## 解決策の比較

### Option A — Score bump (TACTICAL, HARKING-ADJACENT)
- SR 戦略の score を 3.0/3.5 → 4.5 に boost
- リスク: 他戦略との比較根拠なし、observation 後の閾値変更 = HARKing
- → **棄却**: 規律違反

### Option B — Separate "shadow_always" track (RECOMMENDED)
- `DaytradeEngine` に `_shadow_always_strategies` set 追加
- `evaluate_all` の戻り値を `(best_candidate, shadow_always_candidates: list)` に変更
- demo_trader が main slot とは別に shadow trades として shadow_always を全部記録
- impact: app.py / demo_trader.py / engine の API 変更
- → **採用候補**: 規律遵守でデータ蓄積路を作る

### Option C — Separate engine instance (CLEANEST, LARGEST)
- `ShadowEngine` を新設、SR 戦略を移動
- demo_trader が main_loop で `_dt_engine.evaluate_all()` + `_shadow_engine.evaluate_all()` を並行
- 完全直交、副作用最小
- impact: 200+ 行のリファクタ
- → **理想形だが時間コスト大**

### Option D — Score-tier system (FLEXIBLE)
- Candidate に `tier: ("primary"|"shadow")` フィールド追加
- `select_best` は `tier="primary"` のみで競争
- `tier="shadow"` は無条件で list に残る
- impact: 中規模、Candidate dataclass 変更 + select_best ロジック変更
- → **B と C の中間、tier の概念で表現が綺麗**

## 推奨: Option B (最小変更で問題解決)

### 実装案
```python
# strategies/daytrade/__init__.py
class DaytradeEngine:
    SHADOW_ALWAYS_STRATEGIES = frozenset({
        "sr_anti_hunt_bounce",
        "sr_liquidity_grab",
        # 将来 enabled=True で score 競争に負ける戦略を追加
    })

    def evaluate_all(self, ctx) -> dict:
        """Return both primary best and shadow-always candidates."""
        primary, shadow_always = [], []
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            candidate = strategy.evaluate(ctx)
            if candidate is None:
                continue
            if strategy.name in self.SHADOW_ALWAYS_STRATEGIES:
                shadow_always.append(candidate)
            else:
                primary.append(candidate)
        return {"primary": primary, "shadow_always": shadow_always}

    def select_best(self, candidates) -> Optional[Candidate]:
        # backward-compatible: accept list or dict
        if isinstance(candidates, dict):
            candidates = candidates["primary"]
        return max(candidates, key=lambda c: c.score) if candidates else None
```

`demo_trader.py` の trade-creation path で:
- main slot: 既存通り `select_best(result["primary"])`
- shadow slot: `for c in result["shadow_always"]: 強制 is_shadow=1 で trade record`

### 期待効果
- SR Anti-Hunt: 46 candidates/day × ~80% rate (some 失格 conditions) = 約 35-40 shadow trades/day/pair
- 5 pair × 7日 = 1000+ shadow trades が 1週間で蓄積
- live_thaw G3 (`SR Anti-Hunt EUR_USD Sentinel N=30`) は約 24-48h で達成
- live_thaw 2/4 → 3/4 へ進捗

## 規律チェック

- [x] HARKing 防止: score を変更せず、architectural な分離で対応
- [x] ラベル実測主義: hunt_event log + demo_trades.db で根拠提示
- [x] 既存戦略への副作用ゼロ: SHADOW_ALWAYS set 外の戦略は挙動不変
- [x] backward compatibility: select_best の signature 後方互換

## Out of Scope

- SR 戦略の閾値チューニング (proximity_atr, adx_max など) — 別 plan
- Option C (ShadowEngine 分離) の完全実装 — 時間コスト見合いで保留
- score-tier system (Option D) — Candidate dataclass 変更が大きすぎる
