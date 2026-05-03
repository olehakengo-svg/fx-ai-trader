from tools import scalp_alt_pre_reg_bt as bt


def _metrics(**overrides):
    base = {
        "strategy": "bb_squeeze_breakout",
        "pair": "USD_JPY",
        "n": 80,
        "pf": 1.45,
        "wilson_lo": bt.BEV_WR_BY_PAIR["USD_JPY"] + 0.08,
        "wf_is_pf": 1.35,
        "wf_oos_pf": 1.30,
        "max_dd_pct": 0.18,
        "bonferroni_p": 0.004,
    }
    base.update(overrides)
    return base


def test_candidate_metadata_is_locked():
    assert bt.BONFERRONI_K == 4
    assert bt.ALPHA_BONFERRONI == 0.0125
    assert [c.strategy for c in bt.CANDIDATES] == [
        "bb_squeeze_breakout",
        "engulfing_bb",
        "fib_reversal",
        "sr_channel_reversal",
    ]
    assert bt.CANDIDATE_BY_STRATEGY["fib_reversal"].pair == "EUR_USD"
    assert bt.CANDIDATE_BY_STRATEGY["sr_channel_reversal"].interval == "5m"


def test_bonferroni_uses_fixed_k4():
    raw = bt.binomial_one_sided_p(wins=26, n=40, null_wr=0.344)
    adjusted = bt.bonferroni_one_sided_p(wins=26, n=40, null_wr=0.344)
    assert adjusted == min(1.0, raw * 4)
    assert adjusted < 1.0


def test_threshold_logic_promote_shadow_reject_insufficient():
    assert bt.apply_verdict(_metrics())["verdict"] == "PROMOTE"

    shadow = bt.apply_verdict(_metrics(
        pf=1.18,
        wilson_lo=bt.BEV_WR_BY_PAIR["USD_JPY"] + 0.02,
        wf_is_pf=1.05,
        wf_oos_pf=1.04,
        bonferroni_p=0.50,
    ))
    assert shadow["verdict"] == "SHADOW"

    reject = bt.apply_verdict(_metrics(pf=1.09))
    assert reject["verdict"] == "REJECT"

    insufficient = bt.apply_verdict(_metrics(n=29))
    assert insufficient["verdict"] == "INSUFFICIENT"
    assert insufficient["gap_to_30"] == 1


def test_overfit_suspected_downgrades_by_one_tier():
    promote_to_shadow = bt.apply_verdict(_metrics(wf_is_pf=1.50, wf_oos_pf=1.20))
    assert promote_to_shadow["base_verdict"] == "PROMOTE"
    assert promote_to_shadow["verdict"] == "SHADOW"
    assert promote_to_shadow["overfit_suspected"] is True
    assert promote_to_shadow["downgraded_for_overfit"] is True

    shadow_to_reject = bt.apply_verdict(_metrics(
        pf=1.15,
        wilson_lo=bt.BEV_WR_BY_PAIR["USD_JPY"] + 0.01,
        wf_is_pf=1.20,
        wf_oos_pf=1.00,
        bonferroni_p=0.80,
    ))
    assert shadow_to_reject["base_verdict"] == "SHADOW"
    assert shadow_to_reject["verdict"] == "REJECT"
    assert shadow_to_reject["overfit_suspected"] is True


def test_bt_gate_blocked_is_separate_from_insufficient():
    verdict = bt.apply_verdict(_metrics(n=0, bt_gate_blocked=True))
    assert verdict["verdict"] == "BT_GATE_BLOCKED"
    assert verdict["base_verdict"] == "BT_GATE_BLOCKED"


def test_aggregate_enforces_at_most_one_promote():
    records = []
    for strategy in ("bb_squeeze_breakout", "engulfing_bb"):
        records.append({
            "candidate": {"strategy": strategy},
            "metrics": {
                "bonferroni_p": 0.005 if strategy == "bb_squeeze_breakout" else 0.006,
                "pf": 1.4,
                "ev_pip_per_trade": 0.5,
                "n": 80,
            },
            "verdict": {"verdict": "PROMOTE", "base_verdict": "PROMOTE", "reasons": []},
        })

    bt.enforce_single_promote(records)

    assert [r["verdict"]["verdict"] for r in records].count("PROMOTE") == 1
    assert records[0]["verdict"]["verdict"] == "PROMOTE"
    assert records[1]["verdict"]["verdict"] == "SHADOW"
