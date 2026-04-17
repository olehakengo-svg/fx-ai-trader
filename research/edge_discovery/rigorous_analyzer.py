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
        """R:R 実測から cost-adjusted break-even WR を算出.

        導出:
          net_win  = avg_win  - cost     (コストが勝ちを削る)
          net_loss = avg_loss + cost     (コストが負けを膨らます, 絶対値)
          EV = 0 の WR:
              WR * (avg_win - cost) = (1-WR) * (avg_loss + cost)
          展開して整理:
              WR = (avg_loss + cost) / (avg_win + avg_loss)

        分母に cost が入らない点が重要。従来の
        `(loss+cost)/(win+loss+cost)` は BE-WR を過小推定していた.
        """
        s = pnl_series
        wins = s[s > 0]
        losses = s[s < 0]
        if len(wins) == 0 or len(losses) == 0:
            return self.breakeven_wr
        avg_win = float(wins.mean())
        avg_loss = -float(losses.mean())  # 正値化
        cost = self.cost_pips_roundtrip
        denom = avg_win + avg_loss
        if denom <= 0:
            return self.breakeven_wr
        be = (avg_loss + cost) / denom
        return max(0.10, min(0.90, be))   # sanity clamp

    def analyze_dimensions(self, dims: list[str]) -> "RigorousAnalyzer":
        """1次元ずつ cell を構築し pocket stats を集める.

        Note: multiple testing correction は finalize() まで遅延される
        (analyze_cross と family を共有するため).
        """
        df = self._apply_filters()
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
                if "entry_time" in grp.columns:
                    items = list(zip(grp["entry_time"], grp["pnl_pips"]))
                    p.wf_stable = wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8)
                self.all_pockets.append(p)
        # 即時 finalize (従来の API を保つため)
        self.finalize()
        return self

    def analyze_cross(self, dim1: str, dim2: str, min_n: int = 15) -> "RigorousAnalyzer":
        """2次元 cross の cell 分析 (dim1, dim2 の組合せ).

        Bonferroni/FDR は全 pockets (1D + cross) にまとめて適用するため、
        家族ごとのエラーレート制御が正しく保たれる.
        """
        df = self._apply_filters()
        if dim1 not in df.columns or dim2 not in df.columns:
            return self
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
            self.all_pockets.append(p)
        # Re-finalize across entire family (全 pockets で補正)
        self.finalize()
        return self

    def finalize(self) -> "RigorousAnalyzer":
        """Apply Bonferroni + BH-FDR over the entire all_pockets family.

        Safe to call multiple times — each call re-computes flags based on
        the current full family size. This is essential when
        analyze_dimensions and analyze_cross are both used, to avoid
        per-batch correction that would inflate false-positive rate.
        """
        if not self.all_pockets:
            return self
        apply_corrections(self.all_pockets, alpha=self.alpha, fdr_q=self.fdr_q)
        assign_recommendation(self.all_pockets, min_n_strong=self.min_n_strong)
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
