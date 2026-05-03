from pathlib import Path


def _stats(
    *,
    n=30,
    pf=1.3,
    wr=60.0,
    ev=0.5,
    wilson_lo=40.0,
    bev_wr=34.4,
    bonf=0.01,
    dd_pct=10.0,
    is_pf=1.2,
    oos_pf=1.2,
):
    wins = int(round(n * wr / 100.0))
    return {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate": wr,
        "ev_pips": ev,
        "profit_factor": pf,
        "wilson_lo_95": wilson_lo,
        "wilson_hi_95": 75.0,
        "bev_wr": bev_wr,
        "bonferroni_p": bonf,
        "bonferroni_alpha_div_k": 0.0125,
        "kelly_half": 0.05,
        "max_drawdown_pips": 8.0,
        "max_drawdown_pct": dd_pct,
        "walk_forward": {
            "split": "50/50 chronological split",
            "midpoint_utc": "2026-02-01T00:00:00+00:00",
            "is": {"n": n // 2, "win_rate": wr, "profit_factor": is_pf, "ev_pips": ev},
            "oos": {"n": n - n // 2, "win_rate": wr, "profit_factor": oos_pf, "ev_pips": ev},
        },
    }


def test_candidate_metadata_matches_locked_pool():
    import tools.scalp_alt_pre_reg_bt as mod

    fib = mod.metadata_for_candidate("fib_reversal")

    assert fib["pair"] == "EUR_USD"
    assert fib["interval"] == "1m"
    assert fib["roadmap_ev_pips"] == 0.426
    assert fib["bev_wr"] == 0.397


def test_dry_run_contains_k4_and_bev_pairs():
    import tools.scalp_alt_pre_reg_bt as mod

    text = mod.dry_run_text()

    assert '"k": 4' in text
    assert '"USD_JPY": 34.4' in text
    assert '"EUR_USD": 39.7' in text
    assert '"Reject"' in text
    assert '"Insufficient"' in text


def test_bonferroni_p_is_adjusted_by_locked_k4(monkeypatch):
    import tools.scalp_alt_pre_reg_bt as mod

    monkeypatch.setattr(
        mod,
        "load_quant_helpers",
        lambda: (
            lambda *_: {"full_kelly": 0.0, "half_kelly": 0.0, "edge": 0.0},
            lambda wins, n, p: 0.01,
            lambda wins, n: 0.5,
            lambda wr, n: 0.7,
        ),
    )

    stats = mod.stats_from_trades(
        [{"outcome": "WIN", "pnl_pips": 1.0, "entry_time": "2026-01-01T00:00:00+00:00"}],
        0.344,
    )

    assert stats["bonferroni_p"] == 0.04


def test_determine_verdict_promote_when_all_locked_conditions_pass():
    import tools.scalp_alt_pre_reg_bt as mod

    verdict, reasons, flags, overfit = mod.determine_verdict(
        _stats(pf=1.35, wilson_lo=40.0, bonf=0.01, is_pf=1.25, oos_pf=1.25),
        False,
    )

    assert verdict == "Promote"
    assert reasons == []
    assert flags == []
    assert overfit["flagged"] is False


def test_stats_from_bt_trade_log_uses_outcome_and_tp_sl_multiples():
    import tools.scalp_alt_pre_reg_bt as mod

    trades = [
        {"outcome": "WIN", "tp_m": 2.0, "exit_friction_m": 0.1, "entry_time": "2026-01-01T00:00:00+00:00"},
        {"outcome": "LOSS", "sl_m": 1.0, "actual_sl_m": 1.2, "exit_friction_m": 0.1, "entry_time": "2026-01-01T00:05:00+00:00"},
        {"outcome": "WIN", "tp_m": 1.5, "exit_friction_m": 0.1, "entry_time": "2026-01-01T00:10:00+00:00"},
    ]

    stats = mod.stats_from_trades(trades, 0.344)

    assert stats["n"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["ev_pips"] == 0.667
    assert stats["profit_factor"] == 2.538


def test_summary_trade_log_type_filter_matches_run_scalp_backtest_shape():
    import tools.scalp_alt_pre_reg_bt as mod

    summary = {
        "trade_log": [
            {"type": "bb_squeeze_breakout", "outcome": "WIN", "tp_m": 1.0, "entry_time": "2026-01-01T00:00:00+00:00"},
            {"type": "bb_squeeze_breakout", "outcome": "LOSS", "sl_m": 1.0, "entry_time": "2026-01-01T00:05:00+00:00"},
            {"type": "fib_reversal", "outcome": "WIN", "tp_m": 2.0, "entry_time": "2026-01-01T00:10:00+00:00"},
        ],
        "entry_breakdown": {
            "bb_squeeze_breakout": {"wins": 1, "total": 2, "pnl": 0.0, "win_rate": 50.0, "ev": 0.0},
        },
    }

    trades = mod.extract_strategy_trades(summary, [], "bb_squeeze_breakout")

    assert len(trades) == 2
    assert all(t["type"] == "bb_squeeze_breakout" for t in trades)


def test_determine_verdict_shadow_when_bonferroni_blocks_promote():
    import tools.scalp_alt_pre_reg_bt as mod

    verdict, reasons, flags, _ = mod.determine_verdict(
        _stats(pf=1.2, wilson_lo=35.0, bonf=0.20, is_pf=1.05, oos_pf=1.05),
        False,
    )

    assert verdict == "Shadow"
    assert reasons == []
    assert flags == []


def test_determine_verdict_bt_gate_blocked_beats_insufficient():
    import tools.scalp_alt_pre_reg_bt as mod

    verdict, reasons, flags, _ = mod.determine_verdict(_stats(n=0, pf=None), True)

    assert verdict == "BT_GATE_BLOCKED"
    assert "N=0" in reasons[0]
    assert flags == []


def test_overfit_suspected_downgrades_shadow_to_reject():
    import tools.scalp_alt_pre_reg_bt as mod

    verdict, reasons, flags, overfit = mod.determine_verdict(
        _stats(pf=1.2, wilson_lo=35.0, bonf=0.50, is_pf=1.20, oos_pf=0.90),
        False,
    )

    assert verdict == "Reject"
    assert "OVERFIT_SUSPECTED" in flags
    assert overfit["flagged"] is True
    assert any("15%" in reason for reason in reasons)


def test_build_aggregate_payload_recommends_a3_when_shadow_exists():
    import tools.scalp_alt_pre_reg_bt as mod

    candidate_payload = {
        "candidate": mod.metadata_for_candidate("bb_squeeze_breakout"),
        "stats": _stats(pf=1.2, wilson_lo=35.0, bonf=0.20, is_pf=1.05, oos_pf=1.05),
        "verdict": "Shadow",
        "reasons": [],
        "flags": [],
        "overfit": {"flagged": False, "oos_to_is_ratio": 1.0, "threshold": 0.85},
        "gate_blocked_likely_gates": [],
    }

    payload = mod.build_aggregate_payload([candidate_payload])

    assert payload["summary"]["next_task"].startswith("A3-simple")


def test_build_aggregate_payload_caps_promote_to_one_candidate():
    import tools.scalp_alt_pre_reg_bt as mod

    first = {
        "candidate": mod.metadata_for_candidate("bb_squeeze_breakout"),
        "stats": _stats(pf=1.35, ev=0.6, wilson_lo=40.0, bonf=0.01, is_pf=1.25, oos_pf=1.25),
        "verdict": "Promote",
        "reasons": [],
        "flags": [],
        "overfit": {"flagged": False, "oos_to_is_ratio": 1.0, "threshold": 0.85},
        "gate_blocked_likely_gates": [],
    }
    second = {
        "candidate": mod.metadata_for_candidate("engulfing_bb"),
        "stats": _stats(pf=1.35, ev=0.5, wilson_lo=40.0, bonf=0.01, is_pf=1.25, oos_pf=1.25),
        "verdict": "Promote",
        "reasons": [],
        "flags": [],
        "overfit": {"flagged": False, "oos_to_is_ratio": 1.0, "threshold": 0.85},
        "gate_blocked_likely_gates": [],
    }

    payload = mod.build_aggregate_payload([second, first])

    promote_candidates = [c for c in payload["candidates"] if c["verdict"] == "Promote"]
    capped_candidates = [c for c in payload["candidates"] if "PROMOTE_CAP_DOWNGRADED" in c["flags"]]
    assert [c["strategy"] for c in promote_candidates] == ["bb_squeeze_breakout"]
    assert [c["strategy"] for c in capped_candidates] == ["engulfing_bb"]
    assert payload["summary"]["promote_count"] == 1


def test_run_aggregate_writes_expected_outputs(monkeypatch, tmp_path):
    import tools.scalp_alt_pre_reg_bt as mod

    candidate = {
        "run_at": "2026-05-03T00:00:00+00:00",
        "candidate": mod.metadata_for_candidate("bb_squeeze_breakout"),
        "stats": _stats(pf=1.2, wilson_lo=35.0, bonf=0.20, is_pf=1.05, oos_pf=1.05),
        "verdict": "Shadow",
        "reasons": [],
        "flags": [],
        "overfit": {"flagged": False, "oos_to_is_ratio": 1.0, "threshold": 0.85},
        "gate_blocked_likely_gates": [],
    }

    monkeypatch.setattr(mod, "load_candidate_payloads", lambda: [candidate])
    monkeypatch.setattr(mod, "aggregate_json_path", lambda: tmp_path / "aggregate.json")
    monkeypatch.setattr(mod, "aggregate_md_path", lambda: tmp_path / "aggregate.md")

    prereg = tmp_path / "prereg.md"
    assert mod.run_aggregate(str(prereg)) == 0

    assert (tmp_path / "aggregate.json").exists()
    assert (tmp_path / "aggregate.md").exists()
    assert prereg.exists()
    assert "bb_squeeze_breakout" in Path(prereg).read_text()


def test_validate_candidate_payload_rejects_stale_missing_strategy_trades():
    import pytest
    import tools.scalp_alt_pre_reg_bt as mod

    stale_payload = {
        "candidate": mod.metadata_for_candidate("bb_squeeze_breakout"),
        "stats": _stats(n=23, wr=0.0, pf=None),
        "verdict": "Insufficient",
        "engine": {
            "raw_trade_count_strategy": 23,
            "summary": {
                "entry_breakdown": {
                    "bb_squeeze_breakout": {"wins": 18, "total": 23, "pnl": 10.9}
                }
            },
        },
    }

    with pytest.raises(ValueError, match="stale candidate JSON"):
        mod.validate_candidate_payload(stale_payload, "bb_squeeze_breakout")
