import pandas as pd
import pytest

from tools.audit.neighborhood_stability import compute_neighborhood_stability


def _grid(rows):
    return pd.DataFrame(rows)


def test_smooth_surface_passes_all_metrics():
    df = _grid(
        [
            {"x": 0, "y": "b", "N": 20, "wilson_lo": 0.57, "kelly": 0.045},
            {"x": 1, "y": "b", "N": 20, "wilson_lo": 0.60, "kelly": 0.050},
            {"x": 2, "y": "b", "N": 20, "wilson_lo": 0.58, "kelly": 0.055},
            {"x": 1, "y": "a", "N": 20, "wilson_lo": 0.57, "kelly": 0.047},
            {"x": 1, "y": "c", "N": 20, "wilson_lo": 0.59, "kelly": 0.052},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 1, "y": "b"}, 0.50)

    assert verdict.a_pass is True
    assert verdict.b_pass is True
    assert verdict.c_pass is True
    assert verdict.pass_overall is True
    assert verdict.n_neighbors == 4
    assert verdict.median_lift == pytest.approx(0.575 / 0.60)


def test_single_spike_fails_metric_a():
    df = _grid(
        [
            {"x": 0, "N": 20, "wilson_lo": 0.30, "kelly": 0.045},
            {"x": 1, "N": 20, "wilson_lo": 0.60, "kelly": 0.050},
            {"x": 2, "N": 20, "wilson_lo": 0.30, "kelly": 0.055},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 1}, 0.20)

    assert verdict.median_lift == pytest.approx(0.50)
    assert verdict.a_pass is False
    assert verdict.b_pass is True
    assert verdict.c_pass is True
    assert verdict.pass_overall is False


def test_half_flip_fails_metric_b():
    df = _grid(
        [
            {"x": 0, "y": "b", "N": 20, "wilson_lo": 0.55, "kelly": 0.05},
            {"x": 1, "y": "b", "N": 20, "wilson_lo": 0.60, "kelly": 0.05},
            {"x": 2, "y": "b", "N": 20, "wilson_lo": 0.56, "kelly": 0.05},
            {"x": 1, "y": "a", "N": 20, "wilson_lo": 0.40, "kelly": 0.05},
            {"x": 1, "y": "c", "N": 20, "wilson_lo": 0.42, "kelly": 0.05},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 1, "y": "b"}, 0.50)

    assert verdict.sign_agreement == pytest.approx(0.50)
    assert verdict.b_pass is False
    assert verdict.pass_overall is False


def test_kelly_variance_fails_metric_c():
    df = _grid(
        [
            {"x": 0, "y": "b", "N": 20, "wilson_lo": 0.56, "kelly": -0.05},
            {"x": 1, "y": "b", "N": 20, "wilson_lo": 0.60, "kelly": 0.05},
            {"x": 2, "y": "b", "N": 20, "wilson_lo": 0.56, "kelly": 0.11},
            {"x": 1, "y": "a", "N": 20, "wilson_lo": 0.57, "kelly": 0.13},
            {"x": 1, "y": "c", "N": 20, "wilson_lo": 0.57, "kelly": -0.03},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 1, "y": "b"}, 0.50)

    assert verdict.variance_cv > 1.0
    assert verdict.c_pass is False
    assert verdict.pass_overall is False


def test_boundary_cell_uses_available_one_sided_neighbors():
    df = _grid(
        [
            {"x": 0, "N": 20, "wilson_lo": 0.60, "kelly": 0.050},
            {"x": 1, "N": 20, "wilson_lo": 0.58, "kelly": 0.052},
            {"x": 2, "N": 20, "wilson_lo": 0.57, "kelly": 0.053},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 0}, 0.50)

    assert verdict.n_neighbors == 1
    assert verdict.pass_overall is True


def test_small_n_neighbors_are_excluded_and_noted():
    df = _grid(
        [
            {"x": 0, "N": 3, "wilson_lo": 0.10, "kelly": -0.20},
            {"x": 1, "N": 20, "wilson_lo": 0.60, "kelly": 0.050},
            {"x": 2, "N": 20, "wilson_lo": 0.58, "kelly": 0.052},
        ]
    )

    verdict = compute_neighborhood_stability(df, {"x": 1}, 0.50)

    assert verdict.n_neighbors == 1
    assert verdict.pass_overall is True
    assert "small_n_excluded:1" in verdict.notes


def test_primary_cell_must_exist():
    df = _grid(
        [
            {"x": 0, "N": 20, "wilson_lo": 0.60, "kelly": 0.05},
            {"x": 1, "N": 20, "wilson_lo": 0.59, "kelly": 0.05},
            {"x": 2, "N": 20, "wilson_lo": 0.58, "kelly": 0.05},
        ]
    )

    with pytest.raises(KeyError):
        compute_neighborhood_stability(df, {"x": 3}, 0.50)
