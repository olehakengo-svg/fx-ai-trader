"""
Edge Discovery Framework — Demo Run
═══════════════════════════════════

既存のFXデータ or 合成データに対して、conditional return analysis を実行して
実際に pocket を発見できるかを検証する。

実行:
    cd fx-ai-trader
    python3 -m research.edge_discovery.demo_run
"""
from __future__ import annotations
import os
import sys


def generate_synthetic_bars_1h(n_days: int = 365, seed: int = 42):
    """1h足合成データを生成。時間帯バイアス付き（22:00-00:00 JSTがslight bullish）.

    これは "known edge" を埋め込んだデータで、フレームワークが
    正しく検出できるかの sanity check として使う。
    """
    import pandas as pd
    import numpy as np
    rng = np.random.default_rng(seed)
    n_bars = n_days * 24
    ts = pd.date_range("2025-01-01 00:00", periods=n_bars, freq="1h")
    price = 150.0
    closes = []
    opens = []
    highs = []
    lows = []
    for i, t in enumerate(ts):
        # 時間帯バイアス: 21-23 UTC はわずかに正リターン (既知エッジ)
        hour = t.hour
        drift = 0.015 if 21 <= hour <= 23 else 0.0  # bps scale (極小)
        # 曜日バイアス: 月曜午前 (0-6h UTC) はわずかに負
        if t.weekday() == 0 and 0 <= hour <= 6:
            drift -= 0.010
        noise = rng.normal(0, 0.05)  # pct
        dp = price * (drift / 100.0 + noise / 100.0)
        open_p = price
        close_p = price + dp
        hi = max(open_p, close_p) * (1 + abs(rng.normal(0, 0.0002)))
        lo = min(open_p, close_p) * (1 - abs(rng.normal(0, 0.0002)))
        opens.append(open_p)
        closes.append(close_p)
        highs.append(hi)
        lows.append(lo)
        price = close_p
    df = pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes,
    }, index=ts)
    # ATR(14) 相当を簡易計算
    tr = pd.concat([
        (df["high"] - df["low"]),
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df


def load_live_bars_if_available():
    """既存 Live DB から bars を読めるなら使う。なければ None."""
    try:
        import sqlite3
        import pandas as pd
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "fx_ai_trader.db"
        )
        if not os.path.exists(db_path):
            return None
        conn = sqlite3.connect(db_path)
        # 代表的に USD_JPY の 1h 足を読む（table名は環境依存、最初に見つかるものを使う）
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'", conn
        )
        if tables.empty:
            return None
        return None  # 実データ読み込みは env 依存なので無効化
    except Exception:
        return None


def main():
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("pandas/numpy が必要です")
        sys.exit(1)

    from research.edge_discovery import (
        ConditionalReturnAnalyzer,
        split_half_robustness,
        walk_forward_validate,
    )

    print("=" * 78)
    print("  Edge Discovery Framework — Demo Run")
    print("=" * 78)

    # ── Step 1: データ準備 (known edge 埋込の合成) ──
    print("\n[Step 1] Generating synthetic 1h bars with KNOWN hidden edge...")
    df = generate_synthetic_bars_1h(n_days=365, seed=42)
    print(f"  Bars: {len(df)}, period: {df.index[0]} → {df.index[-1]}")
    print(f"  埋込エッジ: 21-23 UTC に +0.015%/h drift (約 +1.5 bps/bar)")
    print(f"  負エッジ: 月曜0-6 UTC に -0.010%/h drift")

    # ── Step 2: Analyzer 構築 ──
    print("\n[Step 2] Setting up ConditionalReturnAnalyzer...")

    def build(df_sub):
        an = ConditionalReturnAnalyzer(
            bars=df_sub,
            horizons_bars=[1, 4, 12, 24],
            cost_bp_roundtrip=1.5,   # 往復 1.5 bps = 0.015%
        )
        an.add_condition("hour", lambda d: d.index.hour)
        an.add_condition("weekday", lambda d: d.index.weekday)
        an.add_condition(
            "atr_rank",
            lambda d: d["atr"].rank(pct=True).round(1),
        )
        an.add_condition(
            "mon_morning",
            lambda d: ((d.index.weekday == 0) & (d.index.hour <= 6)).astype(int),
        )
        return an

    analyzer = build(df)

    # ── Step 3: 全データで pocket 探索 ──
    print("\n[Step 3] Running full-sample edge discovery...")
    print(analyzer.summary_report(min_n=30, min_abs_sharpe=0.3, top_k=15))

    # ── Step 4: Split-half robustness ──
    print("\n[Step 4] Split-half robustness check...")
    rob = split_half_robustness(df, build, min_n=15, min_abs_sharpe=0.3)
    print(f"  Halves pockets: A={rob['n_total_a']}, B={rob['n_total_b']}")
    print(f"  Common: {rob['n_common']} | Sign-consistent: {rob['n_sign_consistent']}")
    print(f"  Consistency rate: {rob['consistency_rate']:.1%}")
    if rob["robust_pairs"]:
        print("\n  Top 5 robust pockets (same sign in both halves):")
        for pa, pb in rob["robust_pairs"][:5]:
            print(f"    A: {pa}")
            print(f"    B: {pb}")
            print()

    # ── Step 5: Walk-forward validation ──
    print("\n[Step 5] Walk-forward validation (4 folds)...")
    wf = walk_forward_validate(df, build, n_folds=4, min_n=15, min_abs_sharpe=0.3)
    for f in wf["folds"]:
        hr = f.get("oos_hit_rate")
        hr_str = f"{hr:.1%}" if hr is not None else "N/A"
        print(f"  Fold {f['fold']}: IS_pockets={f['is_pockets']} "
              f"OOS_hit_rate={hr_str} (chance=50%)")
    print(f"  Mean OOS hit rate: {wf['mean_hit_rate']:.1%}")

    # ── Step 6: 総括 ──
    print("\n" + "=" * 78)
    print("  解釈ガイド:")
    print("=" * 78)
    print("  - hour=21-23 の h=1 horizon で正のSharpe pocket が出れば detector は正常")
    print("  - mon_morning=1 の h=1 で負のSharpe pocket が出れば双方向検出OK")
    print("  - Split-half で consistency > 50% なら pocket は偶然でない")
    print("  - Walk-forward で mean_hit_rate > 60% なら実データ適用価値あり")
    print("\n  ⚠ 合成データは known edge を埋込み済み — 実データでの pocket 発見は保証なし")
    print("  次ステップ: Live DB / OANDA 履歴に本framework を適用")


if __name__ == "__main__":
    main()
