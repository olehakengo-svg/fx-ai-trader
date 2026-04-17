"""
Rigorous Trade Analyzer
═══════════════════════

TradeLogAnalyzer の厳密版:
- 本番データ前提 (production_fetcher.fetch_closed_trades)
- Bonferroni + BH FDR 補正
- Walk-forward stability (時系列 fold)
- Break-even WR をコスト加味して算出
- STRONG / MODERATE / WEAK 推奨

既存 tools/bt_scanner.py と同じ判定流儀に準拠。

Usage:
    from research.edge_discovery.production_fetcher import fetch_closed_trades
    from research.edge_discovery.rigorous_analyzer import RigorousAnalyzer

    df = fetch_closed_trades()
    an = RigorousAnalyzer(df, cost_pips_roundtrip=1.5, breakeven_wr=0.50)
    an.analyze_dimensions(["entry_type", "session", "instrument", "tf", "mode"])
    print(an.report(only_strong=False))
"""
from __future__ import annotations
from dataclasses import dataclass, field

from research.edge_discovery.significance import (
    PocketStats,
    build_pocket,
    apply_corrections,
    assign_recommendation,
    wf_stable_for_cell,
)


@dataclass
class RigorousAnalyzer:
    df: object                                  # pandas DataFrame
    cost_pips_roundtrip: float = 1.5            # 往復コスト [pips]
    breakeven_wr: float = 0.50                  # 本来はR:Rから計算だがdefault
    alpha: float = 0.05
    fdr_q: float = 0.10
    min_n_strong: int = 30
    exclude_shadow: bool = True
    all_pockets: list = field(default_factory=list)

    def _apply_filters(self):
        df = self.df
        if self.exclude_shadow and "is_shadow" in df.columns:
            df = df[df["is_shadow"] != 1]
        # XAU 除外 (user memory)
        if "instrument" in df.columns:
            df = df[~df["instrument"].fillna("").str.contains("XAU", na=False)]
        return df

    def _compute_breakeven_wr(self, pnl_series):
        """R:R 実測から loss-taking の break-even WR を動的計算.

        BE-WR = avg_loss / (avg_win + avg_loss)  (コスト込みのnet)
        これを使う方が 50% 固定より当該戦略のR:R特性を反映できる.
        cost は平均 loss 側に加算する方針.
        """
        s = pnl_series
        wins = s[s > 0]
        losses = s[s < 0]
        if len(wins) == 0 or len(losses) == 0:
            return self.breakeven_wr
        avg_win = float(wins.mean())
        avg_loss = -float(losses.mean())  # 正値化
        # コスト込み調整 (片道でentry/exit両方にかかる)
        avg_loss_adj = avg_loss + self.cost_pips_roundtrip
        be = avg_loss_adj / (avg_win + avg_loss_adj)
        return max(0.10, min(0.90, be))   # sanity clamp

    def analyze_dimensions(self, dims: list[str]) -> "RigorousAnalyzer":
        """1次元ずつ cell を構築し pocket stats を集める."""
        df = self._apply_filters()
        pockets = []
        for dim in dims:
            if dim not in df.columns:
                continue
            for val, grp in df.groupby(dim, observed=True):
                if len(grp) < 10:
                    continue
                pnl = grp["pnl_pips"].dropna()
                if len(pnl) == 0:
                    continue
                be_wr = self._compute_breakeven_wr(pnl)
                p = build_pocket(key=(dim, val), pnl_series=pnl, breakeven_wr=be_wr)
                # walk-forward: use entry_time if available
                if "entry_time" in grp.columns:
                    items = list(zip(grp["entry_time"], grp["pnl_pips"]))
                    p.wf_stable = wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8)
                pockets.append(p)

        # Multiple testing corrections across ALL cells at once (正しい n_tests)
        apply_corrections(pockets, alpha=self.alpha, fdr_q=self.fdr_q)
        assign_recommendation(pockets, min_n_strong=self.min_n_strong)
        self.all_pockets = pockets
        return self

    def analyze_cross(self, dim1: str, dim2: str, min_n: int = 15) -> "RigorousAnalyzer":
        """2次元 cross の cell 分析 (dim1, dim2 の組合せ)."""
        df = self._apply_filters()
        if dim1 not in df.columns or dim2 not in df.columns:
            return self
        pockets = []
        for (v1, v2), grp in df.groupby([dim1, dim2], observed=True):
            if len(grp) < min_n:
                continue
            pnl = grp["pnl_pips"].dropna()
            if len(pnl) == 0:
                continue
            be_wr = self._compute_breakeven_wr(pnl)
            p = build_pocket(
                key=(f"{dim1}×{dim2}", f"{v1}/{v2}"),
                pnl_series=pnl, breakeven_wr=be_wr,
            )
            if "entry_time" in grp.columns:
                items = list(zip(grp["entry_time"], grp["pnl_pips"]))
                p.wf_stable = wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8)
            pockets.append(p)
        apply_corrections(pockets, alpha=self.alpha, fdr_q=self.fdr_q)
        assign_recommendation(pockets, min_n_strong=self.min_n_strong)
        # 既存 + 新規を統合
        self.all_pockets.extend(pockets)
        return self

    def report(
        self,
        only_strong: bool = False,
        include_negative: bool = True,
        top_n: int = 50,
    ) -> str:
        """結果レポート.

        only_strong=True → STRONG のみ
        include_negative=True → 構造的敗者 (avg<0 かつ bonf_sig) も表示
        """
        lines = []
        n_total = len(self.all_pockets)
        n_strong = sum(1 for p in self.all_pockets if p.recommendation == "STRONG")
        n_moderate = sum(1 for p in self.all_pockets if p.recommendation == "MODERATE")
        n_bonf_neg = sum(
            1 for p in self.all_pockets
            if p.bonf_significant and p.avg_pips < 0
        )
        lines.append("═══ Rigorous Trade Analysis ═══")
        lines.append(
            f"Total pockets: {n_total} | STRONG: {n_strong} | MODERATE: {n_moderate} | "
            f"Bonf-significant negative (structural losers): {n_bonf_neg}"
        )
        lines.append(
            f"α={self.alpha}, FDR q={self.fdr_q}, "
            f"cost={self.cost_pips_roundtrip}p, min_n_strong={self.min_n_strong}"
        )
        lines.append("")

        # Positive pockets
        positive = [p for p in self.all_pockets if p.avg_pips > 0]
        positive.sort(key=lambda p: (
            -int(p.recommendation == "STRONG"),
            -int(p.recommendation == "MODERATE"),
            p.p_value,
        ))
        lines.append("─── POSITIVE POCKETS (エッジ候補) ───")
        shown = 0
        for p in positive:
            if only_strong and p.recommendation != "STRONG":
                continue
            lines.append(str(p))
            shown += 1
            if shown >= top_n:
                break

        # Negative (structural losers) — only Bonferroni significant
        if include_negative:
            negatives = [p for p in self.all_pockets
                         if p.avg_pips < 0 and p.bonf_significant]
            if negatives:
                negatives.sort(key=lambda p: p.avg_pips)
                lines.append("\n─── STRUCTURAL LOSERS (Bonferroni有意の負セル) ───")
                for p in negatives[:top_n]:
                    lines.append(str(p))

        return "\n".join(lines)
