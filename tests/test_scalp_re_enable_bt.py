from pathlib import Path
from types import SimpleNamespace


def _stats(n=30, pf=1.2, wr=60.0, ev=0.5):
    return {
        "n": n,
        "wins": int(n * wr / 100),
        "losses": n - int(n * wr / 100),
        "win_rate": wr,
        "ev_pips": ev,
        "profit_factor": pf,
        "wilson_lo_95": 40.0,
        "wilson_hi_95": 75.0,
        "bev_wr": 34.4,
        "bonferroni_p": 0.5,
        "bonferroni_alpha_div_k": 0.01,
        "kelly_half": 0.01,
        "max_drawdown_pips": 4.0,
        "max_drawdown_pct": 10.0,
        "walk_forward": {
            "split": "50/50 time split",
            "midpoint_utc": "2026-02-01T00:00:00+00:00",
            "is": {"n": n // 2, "win_rate": wr, "profit_factor": pf, "ev_pips": ev},
            "oos": {"n": n - n // 2, "win_rate": wr, "profit_factor": pf, "ev_pips": ev},
        },
    }


def _payload(verdict):
    stats = _stats()
    return {
        "run_at": "2026-05-03T00:00:00+00:00",
        "config": {
            "pair": "USD_JPY",
            "strategy": "mtf_regime_trend_cascade_scalp",
            "interval": "5m",
            "lookback_days": 180,
            "abbreviated": False,
            "dry_run": False,
        },
        "bonferroni": {"alpha": 0.05, "k": 5, "alpha_div_k": 0.01, "justification": "test"},
        "thresholds": {},
        "primary": {
            "standard": {"strategy_stats": stats},
            "vec": {"available": True, "strategy_stats": stats},
            "comparison": {"oracle": "standard_bt", "n_gap_pct": 0.0},
            "selected_engine": "standard_bt",
            "selected": {"strategy_stats": stats, "midpoint_utc": "2026-02-01T00:00:00+00:00"},
            "verdict": verdict,
            "verdict_reasons": ["test reason"],
            "live_comparable_selected": _stats(n=0, pf=None, wr=0.0, ev=0.0),
        },
    }


def test_main_full_primary_writes_alternative_scan_when_not_promote(monkeypatch, tmp_path):
    import tools.scalp_re_enable_bt as mod

    raw_md = tmp_path / "primary.md"
    raw_json = tmp_path / "primary.json"
    prereg = tmp_path / "prereg.md"

    monkeypatch.setattr(mod, "default_output_paths", lambda: (raw_md, raw_json, prereg))
    monkeypatch.setattr(mod, "build_payload", lambda args: _payload("Reject"))
    monkeypatch.setattr(
        mod,
        "run_alternative_scans",
        lambda lookback, engine_timeout=900: [
            {
                "strategy": "bb_squeeze_breakout",
                "pair": "USD_JPY",
                "interval": "5m",
                "verdict": "Shadow",
                "selected": {"strategy_stats": _stats(n=31, pf=1.15, wr=61.0, ev=0.4)},
            }
        ],
    )
    monkeypatch.setattr(
        mod,
        "parse_args",
        lambda argv=None: SimpleNamespace(
            pair="USD_JPY",
            strategy="mtf_regime_trend_cascade_scalp",
            interval="5m",
            lookback=180,
            engine_timeout=900,
            output=None,
            abbreviated=False,
            dry_run=False,
        ),
    )

    assert mod.main([]) == 0

    text = Path(prereg).read_text()
    assert "Alternative candidate scan" in text
    assert "bb_squeeze_breakout" in text
    assert "Shadow" in text


def test_parse_args_uses_realistic_engine_timeout_default():
    import tools.scalp_re_enable_bt as mod

    args = mod.parse_args([])

    assert args.engine_timeout == 900


def test_parse_args_allows_engine_timeout_override():
    import tools.scalp_re_enable_bt as mod

    args = mod.parse_args(["--engine-timeout", "0"])

    assert args.engine_timeout == 0
