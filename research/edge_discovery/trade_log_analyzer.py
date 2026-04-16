"""
Trade Log Analyzer — 既存トレード履歴から勝ち/負けパターンを抽出.

デモ/本番のトレードログ (demo_trades.db 等) を読み込み、
どの条件下で勝率/期待値が高いかを多次元で分析。

これは「新戦略を探す」前に「既存戦略の勝ち条件を特定」するためのツール。
Rookie mistake = 「平均勝率」で判断すること。
Pro move = 「条件付き勝率」で pocket を特定して位置サイジング。

使い方:
    from research.edge_discovery.trade_log_analyzer import TradeLogAnalyzer
    an = TradeLogAnalyzer("demo_trades.db")
    an.load()
    print(an.by_dimension("hour_of_day"))
    print(an.by_dimension("entry_type"))
    print(an.cross_tab("entry_type", "hour_bucket"))
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3
import os


@dataclass
class TradeLogAnalyzer:
    db_path: str
    table: str = "demo_trades"
    df: object = None   # pandas.DataFrame

    def load(self, exclude_xau: bool = True):
        import pandas as pd
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(self.db_path)
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM {self.table}", conn)
        conn.close()

        if df.empty:
            self.df = df
            return

        # 時間列を datetime 化
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
        df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce")
        df = df.dropna(subset=["entry_time"])

        # XAU除外 (user memory: feedback_exclude_xau)
        if exclude_xau and "instrument" in df.columns:
            df = df[~df["instrument"].fillna("").str.contains("XAU", na=False)]

        # 派生列
        df["hour_of_day"] = df["entry_time"].dt.hour
        df["weekday"] = df["entry_time"].dt.weekday
        df["hour_bucket"] = pd.cut(
            df["hour_of_day"],
            bins=[-1, 6, 12, 18, 23],
            labels=["night(0-6)", "morn(7-12)", "aft(13-18)", "eve(19-23)"],
        )
        df["session"] = df["hour_of_day"].apply(self._session_label)
        df["is_win"] = (df["pnl_pips"].fillna(0) > 0).astype(int)
        df["hold_hours"] = (
            (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 3600.0
        )

        self.df = df

    @staticmethod
    def _session_label(h: int) -> str:
        # UTC hours approximate session
        if 0 <= h < 7:
            return "tokyo"
        elif 7 <= h < 12:
            return "london_morn"
        elif 12 <= h < 17:
            return "london_ny_overlap"
        elif 17 <= h < 22:
            return "ny"
        else:
            return "late_ny"

    # ── 集計メソッド ──────────────────────────────────
    def overall(self) -> dict:
        import pandas as pd
        df = self.df
        closed = df[df["status"].isin(["CLOSED", "closed"])] if "status" in df else df
        if closed.empty:
            return {"n": 0}
        wins = closed["is_win"].sum()
        return {
            "n": len(closed),
            "wins": int(wins),
            "wr": wins / len(closed),
            "total_pips": float(closed["pnl_pips"].sum()),
            "avg_pips": float(closed["pnl_pips"].mean()),
            "pf": self._pf(closed["pnl_pips"]),
            "avg_hold_h": float(closed["hold_hours"].mean()),
        }

    @staticmethod
    def _pf(series) -> float:
        gw = float(series[series > 0].sum())
        gl = -float(series[series < 0].sum())
        if gl == 0:
            return float("inf") if gw > 0 else 0.0
        return gw / gl

    def by_dimension(self, dim: str, min_n: int = 3) -> object:
        """dim 列ごとの WR/PF/EV/N を返す (pandas DataFrame)."""
        import pandas as pd
        df = self.df
        closed = df[df["status"].isin(["CLOSED", "closed"])] if "status" in df else df
        if dim not in closed.columns:
            raise KeyError(dim)
        g = closed.groupby(dim)
        rows = []
        for val, grp in g:
            if len(grp) < min_n:
                continue
            rows.append({
                dim: val,
                "n": len(grp),
                "wins": int(grp["is_win"].sum()),
                "wr": grp["is_win"].mean(),
                "total_pips": grp["pnl_pips"].sum(),
                "avg_pips": grp["pnl_pips"].mean(),
                "pf": self._pf(grp["pnl_pips"]),
                "avg_hold_h": grp["hold_hours"].mean(),
            })
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("avg_pips", ascending=False)

    def cross_tab(self, dim1: str, dim2: str, min_n: int = 3) -> object:
        """2次元 heatmap 用. (dim1, dim2) 別の avg_pips / n を DataFrame で返す."""
        import pandas as pd
        df = self.df
        closed = df[df["status"].isin(["CLOSED", "closed"])] if "status" in df else df
        g = closed.groupby([dim1, dim2], observed=True)
        rows = []
        for (v1, v2), grp in g:
            if len(grp) < min_n:
                continue
            rows.append({
                dim1: v1, dim2: v2,
                "n": len(grp),
                "wr": grp["is_win"].mean(),
                "avg_pips": grp["pnl_pips"].mean(),
                "pf": self._pf(grp["pnl_pips"]),
            })
        return pd.DataFrame(rows)

    def report(self, min_n: int = 3) -> str:
        """人が読むフルレポート."""
        ov = self.overall()
        if ov["n"] == 0:
            return "(No closed trades)"
        lines = [
            "═══ Trade Log Analysis ═══",
            f"DB: {self.db_path} | Table: {self.table}",
            f"Closed trades: {ov['n']} | Wins: {ov['wins']} | WR: {ov['wr']:.1%}",
            f"Total PnL: {ov['total_pips']:+.1f}p | Avg: {ov['avg_pips']:+.2f}p | "
            f"PF: {ov['pf']:.2f} | Avg hold: {ov['avg_hold_h']:.1f}h",
            "",
        ]
        for dim in ["entry_type", "hour_bucket", "session", "weekday", "instrument", "tf"]:
            if dim not in self.df.columns:
                continue
            tbl = self.by_dimension(dim, min_n=min_n)
            if tbl.empty:
                continue
            lines.append(f"─── By {dim} (min N={min_n}) ───")
            for _, r in tbl.iterrows():
                lines.append(
                    f"  {str(r[dim]):20s} N={int(r['n']):4d} "
                    f"WR={r['wr']:.0%} AvgP={r['avg_pips']:+6.2f}p "
                    f"TotP={r['total_pips']:+7.1f}p PF={r['pf']:.2f}"
                )
            lines.append("")
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "demo_trades.db"
    an = TradeLogAnalyzer(path)
    an.load()
    print(an.report(min_n=3))
