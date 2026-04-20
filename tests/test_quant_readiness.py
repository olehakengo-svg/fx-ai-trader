"""Tests for tools/quant_readiness.py — offline logic and grace-degradation."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import quant_readiness as qr  # type: ignore


class TestURLValidation(unittest.TestCase):
    def test_rejects_file_scheme(self):
        with self.assertRaises(ValueError):
            qr._validate_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with self.assertRaises(ValueError):
            qr._validate_url("ftp://example.com/x")

    def test_accepts_https(self):
        qr._validate_url("https://fx-ai-trader.onrender.com/api/demo/stats")

    def test_accepts_http(self):
        qr._validate_url("http://localhost:8000/api/demo/stats")

    def test_rejects_no_netloc(self):
        with self.assertRaises(ValueError):
            qr._validate_url("http:///nohost")


class TestBuildAccumulation(unittest.TestCase):
    def test_live_and_shadow_split(self):
        live = {"total": 14}
        shadow = {"total": 863, "live_count": 14, "shadow_count": 849}
        acc = qr.build_accumulation(live, shadow)
        self.assertEqual(acc["live_n"], 14)
        self.assertEqual(acc["shadow_n"], 849)
        self.assertFalse(acc["live_eligible_kelly"])
        self.assertAlmostEqual(acc["live_pct_to_kelly"], 14 / 20)

    def test_kelly_eligible_at_threshold(self):
        live = {"total": 20}
        shadow = {"total": 50}
        acc = qr.build_accumulation(live, shadow)
        self.assertTrue(acc["live_eligible_kelly"])


class TestBuildGate(unittest.TestCase):
    def test_pp_candidates_filter(self):
        live = {"total": 5, "by_type": {}}
        sentinel = {
            "by_type_pair": {
                "foo|USD_JPY": {"entry_type": "foo", "instrument": "USD_JPY",
                                "n": 35, "ev": 1.2, "wr": 55.0},
                "bar|EUR_USD": {"entry_type": "bar", "instrument": "EUR_USD",
                                "n": 100, "ev": -0.5, "wr": 20.0},  # EV<0 -> exclude
                "baz|GBP_USD": {"entry_type": "baz", "instrument": "GBP_USD",
                                "n": 10, "ev": 2.0, "wr": 70.0},  # N<30 -> exclude
            },
        }
        gate = qr.build_gate(live, sentinel)
        self.assertEqual(len(gate["pp_review_candidates"]), 1)
        self.assertEqual(gate["pp_review_candidates"][0]["strategy"], "foo")

    def test_fd_risk_trigger(self):
        live = {
            "total": 100,
            "by_type": {
                "sink": {"trades": 40, "pnl": -25.0},       # ev=-0.625 → include
                "neutral": {"trades": 35, "pnl": -2.0},     # ev≈-0.057 → exclude
                "small": {"trades": 5, "pnl": -10.0},       # n<30 → exclude
            },
        }
        sentinel = {"by_type_pair": {}}
        gate = qr.build_gate(live, sentinel)
        self.assertEqual(len(gate["fd_risk"]), 1)
        self.assertEqual(gate["fd_risk"][0]["strategy"], "sink")


class TestBuildCoverage(unittest.TestCase):
    def test_filters_pre_cutoff_and_xau(self):
        payload = {
            "trades": [
                {"entry_time": "2026-04-10T00:00:00", "instrument": "USD_JPY",
                 "mtf_regime": "range_tight"},                # pre-cutoff
                {"entry_time": "2026-04-17T00:00:00", "instrument": "XAU_USD",
                 "mtf_regime": "range_tight"},                # XAU
                {"entry_time": "2026-04-17T00:00:00", "instrument": "USD_JPY",
                 "mtf_regime": "trend_up_strong"},
                {"entry_time": "2026-04-18T00:00:00", "instrument": "EUR_USD",
                 "mtf_regime": None},
                {"entry_time": "2026-04-19T00:00:00", "instrument": "EUR_USD",
                 "mtf_regime": "range_wide"},
            ],
        }
        cov = qr.build_coverage(payload)
        self.assertEqual(cov["total_post_cutoff"], 3)  # 2 labeled + 1 unlabeled
        self.assertEqual(cov["labeled_n"], 2)
        self.assertAlmostEqual(cov["coverage_pct"], 2 / 3)
        # trend_down_* must be reported as zero/missing
        self.assertIn("trend_down_strong", cov["missing_regimes"])


class TestDeriveAlerts(unittest.TestCase):
    def test_low_live_n_triggers_kelly_alert(self):
        rep = {
            "accumulation": {"live_n": 10, "shadow_n": 200,
                             "live_eligible_kelly": False,
                             "live_pct_to_kelly": 0.5},
            "coverage": {"coverage_pct": 0.9, "missing_regimes": []},
            "gate": {"fd_risk": []},
        }
        alerts = qr.derive_alerts(rep)
        self.assertTrue(any("Kelly threshold" in a for a in alerts))

    def test_trend_down_zero_warns_backfill(self):
        rep = {
            "accumulation": {"live_n": 50, "shadow_n": 500,
                             "live_eligible_kelly": True,
                             "live_pct_to_kelly": 2.5},
            "coverage": {"coverage_pct": 0.9,
                         "missing_regimes": ["trend_down_strong"]},
            "gate": {"fd_risk": []},
        }
        alerts = qr.derive_alerts(rep)
        self.assertTrue(any("backfill" in a for a in alerts))


class TestRenderText(unittest.TestCase):
    def test_renders_without_exception_offline(self):
        rep = {
            "timestamp": "2026-04-20T10:00:00+00:00",
            "api": "https://example.invalid",
            "cutoff": qr.FIDELITY_CUTOFF,
            "errors": ["URLError: offline (https://example.invalid/api/demo/stats)"],
            "alerts": [],
        }
        out = qr.render_text(rep)
        self.assertIn("Fetch Errors", out)
        self.assertIn("URLError", out)


if __name__ == "__main__":
    unittest.main()
