"""never-shorten merge ガード (fetch_massive_data) と
E15/E7 refreeze ツールの台帳検証ロジックのテスト。

背景: 短い --days のフル取得が長い歴史キャッシュを上書きで消し、
E15/E7 pre-reg の凍結 coverage 台帳が 11/13 ペアで再現不能化した
(2026-07-29 修理)。既存行は不変・head 保持・tail 延長のみを保証する。
"""
import numpy as np
import pandas as pd
import pytest

from tools.e15_e7_data_refreeze import verify_against_ledger
from tools.fetch_massive_data import merge_never_shorten


def _frame(start, periods, close0=100.0, freq="15min"):
    idx = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    vals = close0 + np.arange(periods, dtype=float)
    return pd.DataFrame(
        {"Open": vals, "High": vals + 0.2, "Low": vals - 0.2,
         "Close": vals, "Volume": 10.0},
        index=idx,
    )


class TestMergeNeverShorten:
    def test_short_fetch_does_not_drop_head(self):
        existing = _frame("2014-01-01", 1000)
        fresh = _frame("2014-01-08", 100, close0=500.0)  # 短い後発フル取得
        merged = merge_never_shorten(existing, fresh)
        assert merged.index[0] == existing.index[0]
        assert len(merged) >= len(existing)

    def test_existing_rows_win_on_overlap(self):
        existing = _frame("2014-01-01", 100, close0=100.0)
        fresh = _frame("2014-01-01", 100, close0=999.0)  # 同一 index、別値
        merged = merge_never_shorten(existing, fresh)
        # 既存行の値が保持される (凍結台帳の再現性を壊さない)
        pd.testing.assert_frame_equal(merged, existing, check_freq=False)

    def test_new_tail_is_appended(self):
        existing = _frame("2014-01-01", 100)
        fresh = _frame(existing.index[-1] + pd.Timedelta(minutes=15), 50)
        merged = merge_never_shorten(existing, fresh)
        assert len(merged) == 150
        assert merged.index[-1] == fresh.index[-1]

    def test_mid_history_hole_fill_from_fresh(self):
        existing = _frame("2014-01-01", 100)
        holey = existing.drop(existing.index[40:60])
        fresh = existing.copy()  # フル再取得は穴の区間を持つ
        merged = merge_never_shorten(holey, fresh)
        assert len(merged) == 100

    def test_naive_index_normalized_to_utc(self):
        existing = _frame("2014-01-01", 10)
        fresh = _frame("2014-01-01", 20)
        fresh.index = fresh.index.tz_localize(None)
        merged = merge_never_shorten(existing, fresh)
        assert str(merged.index.tz) == "UTC"
        assert len(merged) == 20


class TestVerifyAgainstLedger:
    LED = None

    @pytest.fixture(autouse=True)
    def _ledger(self):
        df = _frame("2014-01-06", 200)  # 月曜開始 (market-time 内)
        self.df = df
        self.led = {
            "first": str(df.index[0]),
            "last": str(df.index[-1]),
            "rows": len(df),
            "explore_coverage": self._cov(df),
        }
        self.window = [str(df.index[0].date()), str(df.index[-1].date())]

    def _cov(self, df):
        import event_modality_lib as L
        return round(L.market_time_coverage(
            df, str(df.index[0].date()), str(df.index[-1].date())), 4)

    def test_exact_reproduction_passes(self):
        led = dict(self.led)
        led["explore_coverage"] = round(__import__(
            "event_modality_lib").market_time_coverage(
                self.df, self.window[0], self.window[1]), 4)
        assert verify_against_ledger(self.df, led, self.window) == {}

    def test_shortened_head_fails(self):
        short = self.df.iloc[50:]
        bad = verify_against_ledger(short, self.led, self.window)
        assert "first" in bad and "rows_at_ledger_last" in bad

    def test_missing_rows_fail(self):
        holey = self.df.drop(self.df.index[100:110])
        bad = verify_against_ledger(holey, self.led, self.window)
        assert "rows_at_ledger_last" in bad
