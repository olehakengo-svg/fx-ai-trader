"""
Production Data Fetcher
═══════════════════════

Render 本番 API から closed trades を取得するユーティリティ。
ローカル demo_trades.db は開発用のため、分析は本番データで実施する
(CLAUDE.md: 「分析は本番(Render)データを使用」).

Usage:
    from research.edge_discovery.production_fetcher import fetch_closed_trades
    df = fetch_closed_trades(date_from="2026-04-08")  # pandas DataFrame
    df.to_parquet("closed_trades_snapshot.parquet")   # 任意でキャッシュ
"""
from __future__ import annotations
import json
from typing import Optional
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

# NOTE: These endpoints (/api/demo/trades, /api/demo/factors) are currently
# public read-only by design — analysis tooling relies on unauthenticated access.
# If auth is added in future, update the fetcher to pass API_AUTH_TOKEN.
BASE_URL = "https://fx-ai-trader.onrender.com"
FIDELITY_CUTOFF = "2026-04-08"  # BT/Live fidelity 担保日 (CLAUDE.md)


class ProductionFetchError(RuntimeError):
    """Raised when Render API fetch fails or returns non-JSON."""


def _safe_get_json(url: str, timeout_sec: int) -> dict:
    """GET JSON with clear error messages on HTTP/network/decode failure.

    Render cold-start や stale instance が HTML を返すケースを検知し、
    解析ミスを防ぐ. 致命傷は caller に explicit な例外で伝える.
    """
    try:
        with urlopen(url, timeout=timeout_sec) as r:
            status = getattr(r, "status", 200)
            if status >= 400:
                raise ProductionFetchError(
                    f"HTTP {status} from {url}"
                )
            body = r.read()
    except HTTPError as e:
        raise ProductionFetchError(
            f"HTTP {e.code} {e.reason} from {url}"
        ) from e
    except URLError as e:
        raise ProductionFetchError(
            f"Network error fetching {url}: {e.reason}"
        ) from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        snippet = body[:200].decode("utf-8", errors="replace") if body else "(empty)"
        raise ProductionFetchError(
            f"Non-JSON response from {url} (likely Render cold-start HTML). "
            f"First 200 bytes: {snippet!r}"
        ) from e


def fetch_closed_trades(
    date_from: str = FIDELITY_CUTOFF,
    date_to: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 5000,
    include_xau: bool = False,
    include_shadow: bool = True,
    timeout_sec: int = 60,
):
    """Render 本番から closed trades を取得 (pandas DataFrame)."""
    import pandas as pd

    params = {
        "status": "closed",
        "limit": limit,
        "date_from": date_from,
    }
    if date_to:
        params["date_to"] = date_to
    if mode:
        params["mode"] = mode

    url = f"{BASE_URL}/api/demo/trades?" + urlencode(params)
    data = _safe_get_json(url, timeout_sec)

    trades = data.get("trades", [])
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)

    # 型変換
    for col in ["entry_time", "exit_time", "created_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    for col in ["pnl_pips", "pnl_r", "entry_price", "exit_price", "sl", "tp",
                "score", "slippage_pips", "spread_at_entry", "spread_at_exit",
                "mafe_adverse_pips", "mafe_favorable_pips"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # フィルター
    if not include_xau and "instrument" in df.columns:
        df = df[~df["instrument"].fillna("").str.contains("XAU", na=False)]
    if not include_shadow and "is_shadow" in df.columns:
        df = df[df["is_shadow"] != 1]

    # 派生列 (TradeLogAnalyzer と同じインタフェース)
    if "entry_time" in df.columns:
        df = df.dropna(subset=["entry_time"])
        df["hour_of_day"] = df["entry_time"].dt.hour
        df["weekday"] = df["entry_time"].dt.weekday
        df["session"] = df["hour_of_day"].apply(_session_label)
    if "pnl_pips" in df.columns:
        df["is_win"] = (df["pnl_pips"].fillna(0) > 0).astype(int)

    # 連続エントリ時刻でソート (walk-forward 用)
    if "entry_time" in df.columns:
        df = df.sort_values("entry_time").reset_index(drop=True)

    return df


def _session_label(h: int) -> str:
    if 0 <= h < 7:
        return "tokyo"
    elif 7 <= h < 12:
        return "london_morn"
    elif 12 <= h < 17:
        return "london_ny_overlap"
    elif 17 <= h < 22:
        return "ny"
    return "late_ny"


def fetch_factors(
    factors: list[str],
    date_from: str = FIDELITY_CUTOFF,
    min_n: int = 5,
    include_shadow: bool = False,
    timeout_sec: int = 60,
) -> dict:
    """Production-side /api/demo/factors を叩く (多次元セル別 WR/EV/PF/Kelly)."""
    params = {
        "factors": ",".join(factors),
        "date_from": date_from,
        "min_n": min_n,
        "include_shadow": "1" if include_shadow else "0",
    }
    url = f"{BASE_URL}/api/demo/factors?" + urlencode(params)
    return _safe_get_json(url, timeout_sec)


if __name__ == "__main__":
    import sys
    df = fetch_closed_trades()
    print(f"Fetched {len(df)} closed trades from {df['entry_time'].min()} "
          f"to {df['entry_time'].max()}")
    print(f"Columns: {list(df.columns)[:15]}...")
    print(df[["entry_time", "entry_type", "instrument", "mode",
              "pnl_pips", "is_shadow"]].head(10).to_string())
