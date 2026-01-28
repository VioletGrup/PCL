#!/usr/bin/env python3
"""
Common utility functions shared between flat and terrain tracker grading modules.
"""

from __future__ import annotations

from typing import Dict, Protocol


class PileProtocol(Protocol):
    """Protocol for pile objects that have a northing coordinate."""
    northing: float


def y_intercept(slope: float, x: float, y: float) -> float:
    """
    Compute the y-intercept (b) of a line y = m*x + b given a point (x, y) and slope m.

    Parameters
    ----------
    slope : float
        Line slope m.
    x : float
        X-coordinate of a known point.
    y : float
        Y-coordinate of a known point.

    Returns
    -------
    float
        The y-intercept b.
    """
    return y - slope * x


def window_by_pile_in_tracker(
    window: list[dict[str, float]],
) -> Dict[int, tuple[float, float]]:
    """
    Convert grading window rows into a lookup dictionary keyed by pile_in_tracker.

    Parameters
    ----------
    window : list[dict[str, float]]
        Output of `grading_window(...)`. Each dict must contain:
        - "pile_in_tracker"
        - "grading_window_min"
        - "grading_window_max"

    Returns
    -------
    Dict[int, tuple[float, float]]
        Mapping: pile_in_tracker -> (grading_window_min, grading_window_max)
    """
    out: Dict[int, tuple[float, float]] = {}
    for row in window:
        pid = int(row["pile_in_tracker"])
        out[pid] = (float(row["grading_window_min"]), float(row["grading_window_max"]))
    return out


def interpolate_coords(pile: PileProtocol, slope: float, y_intercept: float) -> float:
    """
    Evaluate a linear height model at a pile's northing coordinate.

    Uses: height = slope * northing + y_intercept

    Parameters
    ----------
    pile : PileProtocol
        Pile providing the x-coordinate (northing).
    slope : float
        Line slope with respect to northing.
    y_intercept : float
        Line intercept.

    Returns
    -------
    float
        Interpolated pile height along the line.
    """
    return slope * pile.northing + y_intercept


def total_grading_cost(violating_piles: list[dict[str, float]]) -> float:
    """
    Compute a scalar "grading cost" for the current set of window violations.

    Parameters
    ----------
    violating_piles : list[dict[str, float]]
        Output of `check_within_window(...)`. Each dict must contain:
        - "below_by" (<= 0): negative magnitude indicates how far below the min window
        - "above_by" (>= 0): positive magnitude indicates how far above the max window

    Returns
    -------
    float
        Sum of absolute violation magnitudes across all violating piles:
        sum(|below_by| + above_by).
    """
    return sum(abs(v["below_by"]) + v["above_by"] for v in violating_piles)
