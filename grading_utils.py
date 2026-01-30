#!/usr/bin/env python3
"""
Common utility functions shared between flat and terrain tracker grading modules.
"""

from __future__ import annotations

from bisect import bisect_left
from typing import DefaultDict, Dict, List, Optional, Protocol

from Project import Project
from BasePile import BasePile


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


def build_northing_index(
    project: Project,
) -> Dict[float, List[tuple[float, BasePile]]]:
    """
    Maps rounded northing -> sorted list of (easting, pile)
    """
    index = DefaultDict(list)

    for tracker in project.trackers:
        for pile in tracker.piles:
            key = round(pile.northing, 2)
            index[key].append((pile.easting, pile))

    for key in index:
        index[key].sort(key=lambda x: x[0])

    return index


def find_pile_west(
    project: Project,
    target: BasePile,
    northings: Dict[float, List[tuple[float, BasePile]]],
    *,
    max_ew_dist: float = 10.0,  # metres
) -> Optional[BasePile]:
    """
    Find the closest pile west of `target` with:
    - |northing difference| <= northing_tol
    - east-west distance <= max_ew_dist
    """
    idx = northings

    # check neighbouring northing buckets
    base_key = round(target.northing, 2)
    step = 10**-2
    bucket_range = int(0.05 / step) + 1

    for i in range(-bucket_range, bucket_range + 1):
        key = round(base_key + i * step, 2)
        bucket = idx.get(key)
        if not bucket:
            continue

        eastings = [e for e, _ in bucket]
        pos = bisect_left(eastings, target.easting)

        # scan westward only
        for j in range(pos - 1, -1, -1):
            ew_dist = target.easting - eastings[j]
            if ew_dist > max_ew_dist:
                break  # too far west
            pile = bucket[j][1]
            if abs(pile.northing - target.northing) <= 0.05:
                return pile  # closest valid west pile

    return None
