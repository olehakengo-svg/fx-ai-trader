---
id: 20260518-1352-price-shock-rev-phase-b1
title: "[price_shock_rev Phase B-1] Tier 1 family 5戦略 (H1, LONG, percentile=0.01) を Shadow-only 実装"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T13:52:00+0900
roadmap_gate: "Price-Shock Reversion Grid BT (3,744 cell, commit 63c7cf18) で 227 SHADOW_CANDIDATE → dedup 23 family → 司令塔 pre-reg で Tier 1 (TOP PROMOTE) 5 family を確定。Qiita 由来 AUDJPY H4 完全再現 (WR=60.00% vs 60.06%) + 同方法論で発見した 5 family の本実装 (Shadow-only)。BT→Shadow→Live 段階 ramp の Shadow 投入フェーズ。"
rule: pre-reg-R1
related:
  - tools/price_shock_reversion_bt.py
  - tools/price_shock_dedup_analysis.py
  - data/price_shock_grid_cells.db
  - reports/price_shock_reversion_grid/shadow_promote_shortlist.md
  - reports/price_shock_reversion_grid/dedup_families.md
  - strategies/hourly/__init__.py
  - strategies/hourly/donchian_momentum_breakout.py
  - strategies/hourly/keltner_squeeze_breakout.py
  - strategies/base.py
  - strategies/context.py
  - modules/demo_trader.py
  - tools/sync_kb_index.py
  - tools/tier_integrity_check.py
  - knowledge-base/wiki/tier-master.md
  - knowledge-base/wiki/strategies/
  - data/cache/massive/EUR_GBP_1h.parquet
  - data/cache/massive/EUR_AUD_1h.parquet
  - data/cache/massive/USD_CAD_1h.parquet
  - data/cache/massive/NZD_JPY_1h.parquet
  - data/cache/massive/AUD_JPY_1h.parquet
  - feedback_shadow_first_quant_architecture
  - feedback_live_shadow_separation
  - feedback_partial_quant_trap
  - feedback_codex_mock_test_trap
  - feedback_codex_schema_hallucination
  - feedback_codex_stash_leak
  - feedback_bt_must_use_massive
  - feedback_exclude_xau
  - project_price_shock_reproduction_success_2026_05_15
  - project_price_shock_reversion_queued_2026_05_15
---

# 0. 背景

Price-Shock Reversion Grid BT (`tools/price_shock_reversion_bt.py`) で 3,744 cell の grid を回し、227 SHADOW_CANDIDATE を発見。`tools/price_shock_dedup_analysis.py` で dedup → 23 distinct family。司令塔が **post-hoc tune 禁止 pre-reg** で Tier 1 (TOP PROMOTE) 5 family を確定 (本 task の対象)。

## 0.1 Tier 1 family (literal、変更禁止)

| # | Strategy name | pair | TF | direction | percentile | horizon (bars) | vol_q | N | WR | Wilson_lo | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `price_shock_rev_eur_gbp_h1_long` | EUR_GBP | H1 | LONG | 0.01 | 3 | Q5 | 239 | 72.8% | 0.668 | 14.75 |
| 2 | `price_shock_rev_eur_aud_h1_long` | EUR_AUD | H1 | LONG | 0.01 | 12 | Q5 | 262 | 67.6% | 0.617 | 4.05 |
| 3 | `price_shock_rev_usd_cad_h1_long` | USD_CAD | H1 | LONG | 0.01 | 3 | Q5 | 247 | 66.4% | 0.603 | 5.30 |
| 4 | `price_shock_rev_nzd_jpy_h1_long` | NZD_JPY | H1 | LONG | 0.01 | 12 | Q5 | 303 | 64.0% | 0.585 | 5.02 |
| 5 | `price_shock_rev_aud_jpy_h1_long` | AUD_JPY | H1 | LONG | 0.01 | 12 | ALL | 426 | 63.8% | 0.592 | 2.54 |

詳細レポート: `reports/price_shock_reversion_grid/shadow_promote_shortlist.md`

## 0.2 設計判断 (司令塔)

**配置ディレクトリ**: `strategies/hourly/` (NOT `strategies/scalp/`)
- 理由: 全 5 戦略は H1 timeframe、horizon=3〜12 bars (3〜12 時間) で intraday-swing 帯。
- 先例: `ob_retest_h1` migration (`.ai/tasks/queue/20260518-1338-ob-retest-h1-migration.md`) も H1 戦略を `strategies/hourly/` 配置。
- AUD_JPY も horizon=12 (12 時間) で daytrade/scalp 領域ではなく hourly。

**Live execution は禁止** (feedback_live_shadow_separation):
- 5 戦略すべて Shadow-only で登録。Live promote 判定は別 task で司令塔が `decisions/price-shock-rev-promote-criteria-2026-05-18.md` の基準で行う。

# 1. シグナル仕様 (pre-reg、BT runner と literal 一致)

`tools/price_shock_reversion_bt.py:150-171` の `add_precomputed_columns()` および `compute_signal_entries` ロジックと **bar-by-bar 同一**にすること。以下が pre-reg ロジック:

## 1.1 Pre-computation (H1 bar が確定したら毎 bar 計算)

```python
import numpy as np

# 1. log return (current bar close vs previous bar close)
df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))

# 2. realized vol (20-bar rolling std of log return)
df["vol20"] = df["log_return"].rolling(20, min_periods=20).std()

# 3. 252-bar rolling percentile of *previous* log returns (current bar EXCLUDED)
#    shifted_ret = df["log_return"].shift(1)
#    → look-ahead 排除のため当該 bar 自体を含めない
shifted_ret = df["log_return"].shift(1)
df["lower_p_0p01"] = shifted_ret.rolling(252, min_periods=252).quantile(0.01)

# 4. vol quintile (Q1-Q5) from 252-bar rolling quantile of *previous* vol20
shifted_vol = df["vol20"].shift(1)
df["vol_q20"] = shifted_vol.rolling(252, min_periods=252).quantile(0.20)
df["vol_q40"] = shifted_vol.rolling(252, min_periods=252).quantile(0.40)
df["vol_q60"] = shifted_vol.rolling(252, min_periods=252).quantile(0.60)
df["vol_q80"] = shifted_vol.rolling(252, min_periods=252).quantile(0.80)

# 当該 bar の vol20 がどの quintile に属するか
# Q1: vol20 <= q20, Q2: <= q40, Q3: <= q60, Q4: <= q80, Q5: > q80
```

**重要**:
- `rolling().quantile()` の `min_periods=252` 厳守。NaN bar はシグナル禁止。
- `shifted_ret` / `shifted_vol` の `.shift(1)` は look-ahead 排除のため必須。
- `vol20` の `min_periods=20` も厳守。

## 1.2 Entry condition (毎 bar)

```python
# Tier 1 のうち vol_q == "Q5" のもの (戦略 #1-4):
condition_vol = (vol20 > vol_q80)   # current bar vol20 が Q5 (top quintile)

# Tier 1 のうち vol_q == "ALL" のもの (戦略 #5 AUD_JPY):
condition_vol = True   # vol bucket 無視

# 共通: log_return が 1%-tile 以下のショック (大きな negative return)
condition_shock = (log_return <= lower_p_0p01)

# シグナル発火 (LONG):
signal = condition_shock and condition_vol
```

**エントリー**: 次の bar の open で BUY (look-ahead 排除のため当該 bar の close ではなく **次 bar の open**)。
- BT 実装の同等性: `tools/price_shock_reversion_bt.py:282` の `entry = df["Open"].shift(-1)` と一致。
- Live 実装では当該 bar 確定 → 次 bar 開始 tick で market BUY。

## 1.3 Exit condition

`horizon` bars 経過後の close で必ず exit (戦略 #1,3 は horizon=3 bars、戦略 #2,4,5 は horizon=12 bars)。

**Shadow 拡張 (BT には存在しないが Shadow から必須)**:
- Catastrophic stop: entry 時 `vol20 × √20 × entry_price` を ATR 近似として、`-2.0 × ATR近似` の SL を必須付与。
- 理由: BT は max_holding 内で必ず close するが、Live では系統的に保有中の連鎖損失を防ぐ必要。
- 実装: SL hit でも horizon 到達でもどちらが先でも exit。
- Shadow log では `exit_reason ∈ {horizon, sl_2atr}` を記録。

**TP は無し** (BT 仕様と一致、horizon-close のみ)。

# 2. 実装タスク

## Task A: 戦略実装 (5 files)

### A.1 Common base helper

新規ファイル `strategies/hourly/price_shock_reversion_base.py`:

```python
"""
Price-Shock Reversion family — Tier 1 共通基盤クラス。

参照: Qiita「予測を捨て、分布を読め」(tikeda123/f3bead031159ee8ca1bf)
      + Price-Shock Reversion Grid BT (commit 63c7cf18)

エントリー: H1 bar 確定時に log_return が 252-bar rolling 1%-tile 以下 (大きな negative shock)。
方向: LONG (mean reversion を期待した買い)。
Exit: horizon bars 後の close、または -2 × ATR近似 SL のどちらか早い方。
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Literal

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


VolBucket = Literal["Q1", "Q2", "Q3", "Q4", "Q5", "ALL"]


@dataclass(frozen=True)
class PriceShockRevConfig:
    name: str
    pair: str
    percentile: float        # literal 0.01 for all Tier 1
    horizon_bars: int        # 3 or 12
    vol_q: VolBucket         # "Q5" or "ALL"
    rolling_window: int = 252
    vol20_window: int = 20
    sl_atr_mult: float = 2.0   # catastrophic SL (Shadow 必須)


class PriceShockReversionBase(StrategyBase):
    """Tier 1 family 共通ロジック。サブクラスで cfg を上書きするだけ。"""

    cfg: PriceShockRevConfig  # subclass で定義

    @property
    def name(self) -> str:
        return self.cfg.name

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ctx は H1 candle 列を保持する想定。最低 252+20 bars 必要。
        # 詳細: 既存 hourly 戦略 (donchian_momentum_breakout.py) と同一 API。
        bars = ctx.h1_bars   # list[Bar] | pd.DataFrame、既存 ctx に合わせる
        if not self._has_enough_history(bars):
            return None

        log_returns = self._compute_log_returns(bars)
        vol20 = self._compute_vol20(log_returns)

        # 252-bar rolling, 当該 bar 除外
        lower_pct = self._rolling_quantile_excluding_current(log_returns, self.cfg.percentile)
        vol_quintile = self._compute_vol_quintile(vol20, current_idx=-1)

        if log_returns[-1] is None or lower_pct is None:
            return None
        if log_returns[-1] > lower_pct:
            return None

        if self.cfg.vol_q != "ALL":
            if vol_quintile != self.cfg.vol_q:
                return None

        # SL: -2 × ATR近似. ATR近似 = vol20 × current_price × √20 (annualization なし、bar-level)
        # 厳密化のため ATR(14) で代用可だが、本 spec は BT と整合させるため vol20 由来で固定。
        current_price = bars[-1].close
        atr_proxy = vol20[-1] * current_price * math.sqrt(self.cfg.vol20_window)
        sl_distance = self.cfg.sl_atr_mult * atr_proxy

        # エントリー価格は次 bar の open (engine 側で fill する想定)
        # 既存 hourly 戦略と同様、Candidate には direction と reason を返す
        return Candidate(
            strategy=self.cfg.name,
            direction="BUY",
            score=1.0,   # Tier 1 はゲートで決定済み、スコアは固定
            reason=f"price_shock_rev:{self.cfg.pair}_h1_long pctile={self.cfg.percentile} horizon={self.cfg.horizon_bars} vol_q={self.cfg.vol_q}",
            extra={
                "horizon_bars": self.cfg.horizon_bars,
                "sl_distance": sl_distance,
                "exit_kind": "horizon_or_atr_sl",
                "is_shadow": True,   # Shadow-only
            },
        )

    # --- helpers (実装は既存 hourly 戦略のスタイルに合わせる) ---

    def _has_enough_history(self, bars) -> bool:
        return len(bars) >= self.cfg.rolling_window + self.cfg.vol20_window + 1

    def _compute_log_returns(self, bars) -> list[float]:
        ...

    def _compute_vol20(self, log_returns) -> list[Optional[float]]:
        ...

    def _rolling_quantile_excluding_current(self, log_returns, q: float) -> Optional[float]:
        # 当該 bar (index -1) を除いた直近 252 returns で quantile
        ...

    def _compute_vol_quintile(self, vol20, current_idx: int) -> Optional[VolBucket]:
        # 当該 bar (current_idx) の vol20 が、直近 252 bar (current_idx 除外) の quintile のどこか
        ...
```

**実装注意**:
- `ctx: SignalContext` の H1 bar 列の取得方法は既存 `donchian_momentum_breakout.py` および `keltner_squeeze_breakout.py` を読んで合わせる (Codex 自分で確認)。
- helper の中身は BT runner `tools/price_shock_reversion_bt.py:150-171` の pandas 実装と **数値完全一致**になるよう実装すること。テストで差分≦1e-9 を検証する。
- `Candidate` の field 名 / `score` / `reason` の使い方は既存 hourly 戦略に倣う。

### A.2 5 個の戦略ファイル (それぞれ薄い wrapper)

各ファイル `strategies/hourly/price_shock_rev_{pair_lower}_h1_long.py`:

```python
# 例: strategies/hourly/price_shock_rev_eur_gbp_h1_long.py
from strategies.hourly.price_shock_reversion_base import PriceShockReversionBase, PriceShockRevConfig


class PriceShockRevEurGbpH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_eur_gbp_h1_long",
        pair="EUR_GBP",
        percentile=0.01,
        horizon_bars=3,
        vol_q="Q5",
    )
```

同様に 5 ファイル作成。**percentile / horizon_bars / vol_q は literal、§0.1 表の数値以外は禁止**。

### A.3 Engine 登録

`strategies/hourly/__init__.py` の `HourlyEngine.__init__` に 5 戦略を追加:

```python
from strategies.hourly.price_shock_rev_eur_gbp_h1_long import PriceShockRevEurGbpH1Long
from strategies.hourly.price_shock_rev_eur_aud_h1_long import PriceShockRevEurAudH1Long
from strategies.hourly.price_shock_rev_usd_cad_h1_long import PriceShockRevUsdCadH1Long
from strategies.hourly.price_shock_rev_nzd_jpy_h1_long import PriceShockRevNzdJpyH1Long
from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long

self.strategies = [
    KeltnerSqueezeBreakout(),
    DonchianMomentumBreakout(),
    PriceShockRevEurGbpH1Long(),
    PriceShockRevEurAudH1Long(),
    PriceShockRevUsdCadH1Long(),
    PriceShockRevNzdJpyH1Long(),
    PriceShockRevAudJpyH1Long(),
]
```

## Task B: demo_trader 統合

### B.1 QUALIFIED_TYPES に追加

`modules/demo_trader.py:3511` の `QUALIFIED_TYPES` set に追加:

```python
# 2026-05-18 Phase B-1: Price-Shock Reversion Tier 1 (Shadow-only, rule:R1)
"price_shock_rev_eur_gbp_h1_long",   # EUR_GBP H1 1%-shock LONG horizon=3 Q5 (BT N=239 WR=72.8%)
"price_shock_rev_eur_aud_h1_long",   # EUR_AUD H1 1%-shock LONG horizon=12 Q5 (BT N=262 WR=67.6%)
"price_shock_rev_usd_cad_h1_long",   # USD_CAD H1 1%-shock LONG horizon=3 Q5 (BT N=247 WR=66.4%)
"price_shock_rev_nzd_jpy_h1_long",   # NZD_JPY H1 1%-shock LONG horizon=12 Q5 (BT N=303 WR=64.0%)
"price_shock_rev_aud_jpy_h1_long",   # AUD_JPY H1 1%-shock LONG horizon=12 ALL (BT N=426 WR=63.8%)
```

セクションは「═══ 1H Breakout — HourlyEngine (v5.0) ═══」直下に挿入し、コメントブロックで「Phase B-1 Price-Shock Reversion」と区切る。

### B.2 Shadow flag 強制

各 5 戦略は **必ず Shadow** として処理されること。実装方法は既存 SCALP_SENTINEL / shadow_demote_registry の機構を確認した上で、以下のいずれか:

(a) `modules/demo_trader.py` の `self._FORCE_DEMOTED` (or 同等の Shadow 強制 set) に 5 戦略を追加。
(b) `modules/shadow_demote_registry.py` に Phase B-1 として登録 (既存パターン要確認)。

**Live execution の登録は禁止** — `is_shadow=True` がトレード作成時に必ずセットされる経路を保証すること。

### B.3 Cross-pair correlation guard (EUR_GBP + EUR_AUD)

EUR base の同時 trigger を制限するため、`demo_trader.py` に shared lock を追加 (or 既存の mutual_excl 機構を流用):

```python
# 2026-05-18 Phase B-1: EUR base shock 戦略間の同時ポジション 1 個までに制限
_eur_base_shock_excl = {"price_shock_rev_eur_gbp_h1_long", "price_shock_rev_eur_aud_h1_long"}
if entry_type in _eur_base_shock_excl:
    _others = _eur_base_shock_excl - {entry_type}
    for _ot in open_trades:
        if _ot.get("entry_type") in _others and _ot.get("status") == "open":
            _block(f"eur_base_shock_lock({entry_type}_vs_{_ot.get('entry_type')})")
            return
```

挿入位置: 既存 `_mutual_excl = {"bb_rsi_reversion", "macdh_reversal"}` ブロックの直後 (modules/demo_trader.py:3664 近辺)。

### B.4 Pair 未対応時の handling

`demo_trader` の有効 pair list が EUR_GBP / EUR_AUD / USD_CAD / NZD_JPY / AUD_JPY 全て対応していなければ、**エラーで落とさず**、シグナル評価をスキップして以下を出力:
- `print(f"[INFO] price_shock_rev: pair {pair} not in active list, skipping signal")` (logger.info 推奨)
- `final.md` の "Known Gaps" に「対応未完了 pair: ...」を列挙

## Task C: Tests

### C.1 Unit test (look-ahead 排除)

`tests/test_price_shock_rev_strategies.py` 新規:

```python
import pandas as pd
import numpy as np
import pytest
from pathlib import Path

from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig
from strategies.hourly.price_shock_rev_eur_gbp_h1_long import PriceShockRevEurGbpH1Long
# ... (5 戦略 import)


@pytest.fixture(scope="module")
def eur_gbp_h1_df():
    path = Path("data/cache/massive/EUR_GBP_1h.parquet")
    assert path.exists(), "MASSIVE EUR_GBP H1 parquet 必須 (BT must use MASSIVE)"
    df = pd.read_parquet(path)
    # 既存テストの normalize 関数あれば流用
    return df


def test_lower_percentile_excludes_current_bar(eur_gbp_h1_df):
    """current bar の log_return が 252-bar rolling quantile に含まれてはいけない。"""
    df = eur_gbp_h1_df.copy()
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    shifted = df["log_return"].shift(1)
    quantile_correct = shifted.rolling(252, min_periods=252).quantile(0.01)
    # 違反パターン: shift(1) を入れずに計算した場合、当該 bar が含まれる
    quantile_wrong = df["log_return"].rolling(252, min_periods=252).quantile(0.01)
    # 戦略実装が前者と一致することをチェック (helper を直接呼ぶ)
    strat = PriceShockRevEurGbpH1Long()
    # 例: 最後 1000 bar で差分を確認
    ...
    assert (quantile_correct.dropna() != quantile_wrong.dropna()).any(), \
        "shifted vs non-shifted が同じなら test 自体無意味"


def test_strategy_matches_bt_runner_on_eur_gbp(eur_gbp_h1_df):
    """BT runner (price_shock_reversion_bt.py) と戦略実装で同一 bar に同一シグナルが出ること。"""
    from tools.price_shock_reversion_bt import add_precomputed_columns
    bt_df = add_precomputed_columns(eur_gbp_h1_df, "H1")
    # BT signal mask
    bt_mask = (bt_df["log_return"] <= bt_df["lower_p_0p01"]) & (bt_df["vol_quintile_calc"] == "Q5")

    # 戦略実装で全 bar を順次評価し、同じ位置でシグナル発火することを確認
    strat = PriceShockRevEurGbpH1Long()
    strategy_mask = pd.Series(False, index=bt_df.index)
    for i in range(252 + 20 + 1, len(bt_df)):
        ctx_bars = bt_df.iloc[: i + 1]   # 当該 bar まで
        result = strat.evaluate_from_dataframe(ctx_bars)   # helper 追加して bridge
        strategy_mask.iloc[i] = result is not None

    diff = bt_mask.fillna(False) ^ strategy_mask.fillna(False)
    assert diff.sum() == 0, f"BT runner と戦略実装が {diff.sum()} bar で不一致"


# 同様に EUR_AUD / USD_CAD / NZD_JPY / AUD_JPY 5 戦略すべて、E2E で BT 一致確認
```

**重要 (feedback_codex_mock_test_trap)**:
- mock 禁止。`data/cache/massive/{PAIR}_1h.parquet` を実 read する。
- BT runner の signal mask と戦略実装の signal が **全 bar で一致**することが PASS 条件。
- AUD_JPY は vol_q="ALL" なので vol_quintile gate なしで全 shock bar が signal。

### C.2 Catastrophic SL test

```python
def test_catastrophic_sl_distance_is_finite_and_positive(eur_gbp_h1_df):
    """SL distance が NaN / 負 / 0 にならないこと。"""
    strat = PriceShockRevEurGbpH1Long()
    bars = eur_gbp_h1_df.tail(500).copy()
    # signal が立つ bar で Candidate を取り、extra["sl_distance"] を検証
    ...
```

### C.3 既存 test を壊さないこと

```bash
python3 -m pytest tests/ -x -q
```
で全 PASS (pre-existing failures は除外)。新 test は **必ず PASS**。

## Task D: KB 更新

### D.1 各戦略カード

`knowledge-base/wiki/strategies/price_shock_rev_eur_gbp_h1_long.md` 等 5 個。テンプレ:

```markdown
# price_shock_rev_eur_gbp_h1_long

## 概要
H1 EUR_GBP で 252-bar log return 1%-tile 以下の negative shock が発生し、vol20 が top quintile (Q5) の場合に 3 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 239, WR = 72.8%, Wilson_lo (95%) = 0.668, PF = 14.75, EV ≈ X pip
- 期間: data/cache/massive/EUR_GBP_1h.parquet 全期間
- Cell ID: EUR_GBP_H1_LONG_1_3_Q5

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock + 高 vol regime は overshoot しやすく、短期 mean reversion edge を持つ。
EUR_GBP は range-bound major で reversion 効きが強い。

## エントリー
- Bar 確定時に log_return ≤ 252-bar rolling 1%-tile (当該 bar 除外) AND vol_quintile == Q5
- 次 bar open で BUY

## Exit
- 3 bars 経過後の close で必ず close (horizon exit)
- または -2 × ATR近似 SL hit (catastrophic stop)

## Tier 状態
- 2026-05-18 から Phase B-1 Shadow (is_shadow=True 固定)
- Live promote 基準: `wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md`

## 関連
- BT runner: tools/price_shock_reversion_bt.py
- Grid report: reports/price_shock_reversion_grid/shadow_promote_shortlist.md
```

同様に 5 個作成。N / WR / Wilson_lo / PF / horizon / vol_q は §0.1 表の literal。

### D.2 Pre-reg promote criteria 文書

`knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md` 新規:

```markdown
# Price-Shock Reversion Tier 1: Shadow → Live Promote Pre-reg

## 対象
2026-05-18 Phase B-1 で Shadow 投入された 5 戦略:
- price_shock_rev_eur_gbp_h1_long
- price_shock_rev_eur_aud_h1_long
- price_shock_rev_usd_cad_h1_long
- price_shock_rev_nzd_jpy_h1_long
- price_shock_rev_aud_jpy_h1_long

## Live promote 基準 (LOCK、戦略ごとに独立判定)

戦略 X が以下を全て満たす場合のみ Live promote 提案 (司令塔別判断):

1. **Live shadow N ≥ 30 trades** (closed)
2. **Shadow Wilson_lo (95%) ≥ 0.50** を維持
3. **Bonferroni m=5** (本ファミリー 5 戦略同時昇格判定) で **p < 0.01** (= raw p < 0.05/5)
4. **6 週連続 EV > 0** (週次集計)
5. **Cross-correlation**: EUR_GBP と EUR_AUD は portfolio sizing で 同時 active position 1 個まで (demo_trader 側に shared lock 実装済)

## 棄却基準 (即 demote)

- N=15 蓄積時点で Wilson_lo < 0.40 → Shadow 内で deactivate
- 2 週連続 EV < 0 (週次) → 緊急 review
- catastrophic SL hit 比率 > 30% → 戦略構造再検討

## Post-hoc tune 禁止

percentile / horizon / vol_q は Tier 1 確定時の literal (§0.1 表) から変更しない。
変更したい場合は 新 Codex BT task → 新 family として queue (本 task の派生扱い禁止)。
```

### D.3 tier-master 更新

```bash
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check   # ERROR=0 確認
```

5 戦略は Tier 3 (Shadow) として `knowledge-base/wiki/tier-master.md` および `knowledge-base/wiki/tier-master.json` に登録されること。

## Task E: Commit & verify

### E.1 Pre-existing test failures の扱い

`project_fxai_stale_test_backlog_2026_05_07` の通り pre-commit は 10 件 pre-existing failure で blocked。
本 task は **新 test 追加 + 既存戦略 import は壊さない** ことを保証し、必要なら `--no-verify` 使用可。
**ただし**、新 test (test_price_shock_rev_strategies.py) は **必ず PASS** すること。

### E.2 Commit 構成

```bash
git add strategies/hourly/price_shock_reversion_base.py \
        strategies/hourly/price_shock_rev_*.py \
        strategies/hourly/__init__.py \
        modules/demo_trader.py \
        modules/shadow_demote_registry.py \
        tests/test_price_shock_rev_strategies.py \
        knowledge-base/wiki/strategies/price_shock_rev_*.md \
        knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md \
        knowledge-base/wiki/tier-master.md \
        knowledge-base/wiki/tier-master.json \
        knowledge-base/wiki/index.md \
        knowledge-base/wiki/changelog.md \
        CHANGELOG.md

git commit --no-verify -m "$(cat <<'EOF'
feat(price_shock_rev): Tier 1 family 5 戦略を Phase B-1 Shadow 投入 (rule:R1)

Price-Shock Reversion Grid BT (commit 63c7cf18, 3,744 cell) で 227 SHADOW_CANDIDATE
→ dedup 23 family → 司令塔 pre-reg で TOP PROMOTE 5 family を Shadow 投入。

戦略 (全て H1, LONG, percentile=0.01):
- price_shock_rev_eur_gbp_h1_long (horizon=3 Q5, BT N=239 WR=72.8% Wilson=0.668)
- price_shock_rev_eur_aud_h1_long (horizon=12 Q5, BT N=262 WR=67.6% Wilson=0.617)
- price_shock_rev_usd_cad_h1_long (horizon=3 Q5, BT N=247 WR=66.4% Wilson=0.603)
- price_shock_rev_nzd_jpy_h1_long (horizon=12 Q5, BT N=303 WR=64.0% Wilson=0.585)
- price_shock_rev_aud_jpy_h1_long (horizon=12 ALL, BT N=426 WR=63.8% Wilson=0.592)

Shadow-only (is_shadow=True 強制)、Live promote 基準は
knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md。
EUR_GBP + EUR_AUD は portfolio sizing で同時 active position 1 個まで shared lock。

Pre-reg LOCK: percentile / horizon / vol_q は §0.1 表 literal、post-hoc tune 禁止。
EOF
)"

git status   # clean を確認 (stash leak 防止)
```

### E.3 Stash leak 防止 (feedback_codex_stash_leak)

- `git status` で untracked / modified が **0 件** になっていること。
- `git stash list` で本 task に関連する stash が **存在しない** こと。
- `git log --oneline -5` で本コミットが HEAD にあること。

# 3. 司令塔ガード (必達)

- [ ] Cell パラメータ literal: percentile=0.01, horizon ∈ {3, 12}, vol_q ∈ {Q5, ALL} を §0.1 表の通りに pin
- [ ] post-hoc tune 禁止 (パラメータ sweep / 微調整 / フィルター追加すべて禁止)
- [ ] MASSIVE parquet (`data/cache/massive/{PAIR}_1h.parquet`) のみで BT 一致テスト
- [ ] rolling 252-bar percentile (`min_periods=252`, `shift(1)` で当該 bar 除外)
- [ ] vol20 (`min_periods=20`, `shift(1)` で当該 bar 除外)
- [ ] vol_quintile も `shift(1)` で当該 bar 除外
- [ ] エントリーは **次 bar の open** (look-ahead 排除)
- [ ] Shadow-only (`is_shadow=True` 強制、Live execution 経路に流れないこと)
- [ ] mock 禁止 — test_strategy_matches_bt_runner_on_eur_gbp 等は実 parquet
- [ ] stash 漏れ禁止 — `git status` clean
- [ ] XAU 除外 (本 task は FX のみで XAU 関与なし、ガード)
- [ ] BT runner との bar-by-bar 完全一致を 5 通貨ペアで test 化

# 4. final.md (期待出力)

完了時に `.ai/tasks/queue/20260518-1352-price-shock-rev-phase-b1-final.md` に以下を書き出す:

- 実装ファイルリスト (新規 + 修正)
- `git diff --stat HEAD~1` の出力 (1 コミットなら HEAD~1、複数なら base から)
- `git log --oneline -3`
- `python3 -m pytest tests/test_price_shock_rev_strategies.py -v` の全 PASS 出力
- `python3 tools/tier_integrity_check.py --check` の ERROR=0 確認
- demo_trader 未対応 pair があれば Known Gaps に列挙
- Shadow 起動確認手順 (Render API or local app.py での is_shadow=True 確認方法を 1 行)

# 5. 期待実行時間

2-4 時間 (5 戦略実装 + 共通基盤 + test + KB + commit)。


## Result (2026-05-18T05:43:58Z)

exit=0 · 581s

```
Implemented and committed Price-Shock Reversion Phase B-1.

Commit: `35961351 feat(price_shock_rev): Tier 1 family 5 戦略を Phase B-1 Shadow 投入 (rule:R1)`

What changed:
- Added 5 H1 strategies under `strategies/hourly/` plus shared base.
- Registered them in `HourlyEngine`.
- Integrated Shadow-only routing in `demo_trader`, including FORCE_DEMOTED, EUR_GBP/EUR_AUD shared lock, horizon exits, and `sl_2atr` exits.
- Added MASSIVE parquet tests verifying BT runner bar-by-bar signal equivalence across all 5 pairs.
- Added KB strategy cards, promote criteria, changelog entries, and regenerated tier/index files.
- Wrote final report: `.ai/tasks/queue/20260518-1352-price-shock-rev-phase-b1-final.md`.

Verification:
- `PATH=.venv/bin:$PATH python3 -m pytest tests/test_price_shock_rev_strategies.py -v` → `7 passed`
- `PATH=.venv/bin:$PATH python3 tools/tier_integrity_check.py --check` → passed / ERROR=0
- Full suite `tests/ -x -q` stops on existing unrelated `test_bt_data_loader_parquet_fallback` failure.

Stash check: `git stash list` is empty.

Note: `git status` is not fully clean because unrelated untracked prime-gate files were already present and I left them untouched:
- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md`
- `knowledge-base/wiki/lessons/lesson-prime-gate-order-bug-2026-05-18.md`
- `tests/test_prime_gate_order.py`
- `tools/prime_gate_order_dry_run.py`
```
