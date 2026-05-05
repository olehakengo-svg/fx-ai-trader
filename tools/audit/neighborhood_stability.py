"""NSG-1 neighborhood stability gate.

Pure classifier for parameter-grid sensitivity checks. The module accepts an
already materialized grid and returns a frozen verdict; it performs no I/O and
keeps no process state.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from statistics import median, stdev
from typing import Any, Mapping, Sequence

import pandas as pd  # type: ignore[import-untyped]


MIN_NEIGHBOR_N = 5
REQUIRED_METRIC_COLUMNS = frozenset({"N", "wilson_lo", "kelly"})


@dataclass(frozen=True)
class NeighborhoodVerdict:
    median_lift: float
    sign_agreement: float
    variance_cv: float
    a_pass: bool
    b_pass: bool
    c_pass: bool
    pass_overall: bool
    n_neighbors: int
    skipped_axes: list[str]
    notes: list[str]


@dataclass(frozen=True)
class _NeighborRef:
    index: Any
    axis: str


def _ordered_levels(series: pd.Series) -> list[Any]:
    unique_values = list(series.drop_duplicates())
    try:
        return sorted(unique_values)
    except TypeError:
        return unique_values


def _matching_mask(
    grid_results: pd.DataFrame,
    cell: Mapping[str, Any],
    axes: Sequence[str],
) -> pd.Series:
    mask = pd.Series(True, index=grid_results.index)
    for axis in axes:
        mask &= grid_results[axis] == cell[axis]
    return mask


def _require_columns(grid_results: pd.DataFrame, axes: Sequence[str]) -> None:
    required = set(axes) | set(REQUIRED_METRIC_COLUMNS)
    missing = sorted(required - set(grid_results.columns))
    if missing:
        raise KeyError(f"grid_results missing required columns: {missing}")


def _neighbor_refs(
    grid_results: pd.DataFrame,
    primary_cell: Mapping[str, Any],
    axes: Sequence[str],
    max_step: int,
) -> tuple[list[_NeighborRef], list[str]]:
    refs: list[_NeighborRef] = []
    skipped_axes: list[str] = []
    seen: set[Any] = set()

    for axis in axes:
        levels = _ordered_levels(grid_results[axis])
        if len(levels) < 3:
            skipped_axes.append(axis)
        try:
            primary_pos = levels.index(primary_cell[axis])
        except ValueError as exc:
            raise KeyError(f"primary_cell value not in grid for axis {axis!r}") from exc

        for offset in range(1, max_step + 1):
            for neighbor_pos in (primary_pos - offset, primary_pos + offset):
                if neighbor_pos < 0 or neighbor_pos >= len(levels):
                    continue
                neighbor_cell = dict(primary_cell)
                neighbor_cell[axis] = levels[neighbor_pos]
                mask = _matching_mask(grid_results, neighbor_cell, axes)
                for idx in grid_results.index[mask]:
                    if idx not in seen:
                        seen.add(idx)
                        refs.append(_NeighborRef(index=idx, axis=axis))

    return refs, skipped_axes


def _stdev_or_zero(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(stdev(values))


def _median_lift(neighbor_wilson: Sequence[float], primary_wilson: float) -> float:
    if not neighbor_wilson:
        return 0.0
    median_neighbor = float(median(neighbor_wilson))
    if primary_wilson > 0:
        return median_neighbor / primary_wilson
    if median_neighbor > 0:
        return inf
    return 1.0


def compute_neighborhood_stability(
    grid_results: pd.DataFrame,
    primary_cell: Mapping[str, Any],
    bev_wr: float,
    *,
    axes: Sequence[str] | None = None,
    max_step: int = 1,
    a_threshold: float = 0.80,
    b_threshold: float = 0.50,
    c_threshold: float = 1.00,
) -> NeighborhoodVerdict:
    """Compute NSG-1 A/B/C neighborhood stability for a primary grid cell.

    Neighbor extraction is one-axis-at-a-time: candidates differ from the
    primary cell on exactly one parameter axis and by at most ``max_step``
    adjacent grid levels.
    """

    if max_step < 1:
        raise ValueError("max_step must be >= 1")

    resolved_axes = tuple(primary_cell.keys()) if axes is None else tuple(axes)
    _require_columns(grid_results, resolved_axes)

    primary_mask = _matching_mask(grid_results, primary_cell, resolved_axes)
    if not bool(primary_mask.any()):
        raise KeyError(f"primary_cell not found in grid: {dict(primary_cell)}")
    primary = grid_results.loc[primary_mask].iloc[0]

    refs, skipped_axes = _neighbor_refs(
        grid_results,
        primary_cell,
        resolved_axes,
        max_step,
    )

    notes: list[str] = []
    eligible_refs: list[_NeighborRef] = []
    small_n_excluded = 0
    for ref in refs:
        n_value = float(grid_results.at[ref.index, "N"])
        if n_value < MIN_NEIGHBOR_N:
            small_n_excluded += 1
            continue
        eligible_refs.append(ref)

    if small_n_excluded:
        notes.append(f"small_n_excluded:{small_n_excluded}")

    if not eligible_refs:
        notes.append("neighbor_pool_empty")
        return NeighborhoodVerdict(
            median_lift=0.0,
            sign_agreement=0.0,
            variance_cv=inf,
            a_pass=False,
            b_pass=False,
            c_pass=False,
            pass_overall=False,
            n_neighbors=0,
            skipped_axes=skipped_axes,
            notes=notes,
        )

    neighbor_rows = grid_results.loc[[ref.index for ref in eligible_refs]]
    primary_wilson = float(primary["wilson_lo"])
    primary_kelly = float(primary["kelly"])

    a_refs = [ref for ref in eligible_refs if ref.axis not in skipped_axes]
    if a_refs:
        a_rows = grid_results.loc[[ref.index for ref in a_refs]]
        lift = _median_lift(
            [float(value) for value in a_rows["wilson_lo"].tolist()],
            primary_wilson,
        )
        a_pass = lift >= a_threshold
    else:
        lift = 1.0
        a_pass = True
        notes.append("a_all_axes_skipped")

    neighbor_wilson = [float(value) for value in neighbor_rows["wilson_lo"].tolist()]
    sign_agreement = sum(value >= bev_wr for value in neighbor_wilson) / len(
        neighbor_wilson
    )
    b_pass = sign_agreement > b_threshold

    neighbor_kelly = [float(value) for value in neighbor_rows["kelly"].tolist()]
    kelly_stdev = _stdev_or_zero(neighbor_kelly)
    denominator = max(abs(primary_kelly), 0.01)
    variance_cv = kelly_stdev / denominator
    c_pass = kelly_stdev <= c_threshold * denominator

    pass_overall = a_pass and b_pass and c_pass
    return NeighborhoodVerdict(
        median_lift=lift,
        sign_agreement=sign_agreement,
        variance_cv=variance_cv,
        a_pass=a_pass,
        b_pass=b_pass,
        c_pass=c_pass,
        pass_overall=pass_overall,
        n_neighbors=len(eligible_refs),
        skipped_axes=skipped_axes,
        notes=notes,
    )


__all__ = ["NeighborhoodVerdict", "compute_neighborhood_stability"]
