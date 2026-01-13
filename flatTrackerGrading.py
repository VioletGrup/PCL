#!/usr/bin/env python3

from typing import Dict

from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project


def _y_intercept(slope: float, x: float, y: float) -> float:
    """
    Compute the y-intercept of a line.

    Parameters
    ----------
    slope : float
        Gradient of the line.
    x : float
        X-coordinate of a known point on the line.
    y : float
        Y-coordinate of a known point on the line.

    Returns
    -------
    float
        Y-intercept of the line.
    """
    return y - slope * x


def _window_by_pile_id(window: list[dict[str, float]]) -> Dict[int, tuple[float, float]]:
    """
    Convert grading window data into a lookup dictionary.

    Parameters
    ----------
    window : list[dict[str, float]]
        List of grading window dictionaries containing pile limits.

    Returns
    -------
    Dict[int, tuple[float, float]]
        Dictionary mapping pile_id to (min_height, max_height).
    """
    out: Dict[int, tuple[float, float]] = {}
    for row in window:
        pid = int(row["pile_id"])
        out[pid] = (float(row["grading_window_min"]), float(row["grading_window_max"]))
    return out


def _interpolate_coords(pile: BasePile, slope: float, y_intercept: float) -> float:
    """
    Interpolate the elevation of a pile from a linear grading line.

    Parameters
    ----------
    pile : BasePile
        Pile for which the elevation is calculated.
    slope : float
        Gradient of the grading line.
    y_intercept : float
        Y-intercept of the grading line.

    Returns
    -------
    float
        Interpolated elevation of the pile.
    """
    return slope * pile.northing + y_intercept


def grading_window(project: Project, tracker: BaseTracker) -> list[dict[str, float]]:
    """
    Generate the grading window for all piles in a tracker.

    Parameters
    ----------
    project : Project
        Project containing grading constraints.
    tracker : BaseTracker
        Tracker whose piles are evaluated.

    Returns
    -------
    list[dict[str, float]]
        List of dictionaries describing grading limits and ground elevation
        for each pile.
    """
    window = []
    for pile in tracker.piles:
        window.append(
            {
                "pile_id": pile.pile_id,
                "grading_window_min": pile.true_min_height(project),
                "grading_window_max": pile.true_max_height(project),
                "ground_elevation": pile.current_elevation,
            }
        )
    return window


def target_height_line(tracker: BaseTracker, project: Project) -> tuple[float, float]:
    """
    Set pile elevations along a target height line constrained by project limits.

    Parameters
    ----------
    tracker : BaseTracker
        Tracker whose piles are adjusted.
    project : Project
        Project providing target heights and incline constraints.

    Returns
    -------
    tuple[float, float]
        The slope and y-intercept of the target height line.
    """
    # set the first and last pile in the tracker to the target heights
    first_target_height = tracker.get_first_pile().pile_at_target_height(project)
    last_target_height = tracker.get_last_pile().pile_at_target_height(project)

    # deterimine the equation of the line at target height
    slope = (last_target_height - first_target_height) / (
        tracker.get_last_pile().northing - tracker.get_first_pile().northing
    )

    # if the slope exceeds the maximum incline, set it to the maximum incline
    slope = min(slope, project.constraints.max_incline)

    y_intercept = _y_intercept(
        slope,
        tracker.get_first_pile().northing,
        first_target_height,
    )

    # set each pile to the target height based on the linear equation
    for pile in tracker.piles:
        pile.current_elevation = _interpolate_coords(pile, slope, y_intercept)

    return slope, y_intercept


def check_within_window(
    window: list[dict[str, float]], tracker: BaseTracker
) -> list[dict[str, float]]:
    """
    Identify piles whose elevations lie outside their grading window.

    Parameters
    ----------
    window : list[dict[str, float]]
        Grading window data for the tracker.
    tracker : BaseTracker
        Tracker whose piles are checked.

    Returns
    -------
    list[dict[str, float]]
        List of dictionaries describing piles that violate the grading window.
        An empty list indicates no violations.
    """
    limits = _window_by_pile_id(window)

    violations = []
    for pile in tracker.piles:
        pid = pile.pile_id
        if pid not in limits:
            raise ValueError(f"Pile id {pid} not found in grading window")

        wmin, wmax = limits[pid]
        height = pile.current_elevation

        # if the pile is outside the window, add it to the list and find how far away it is
        if not wmin <= height <= wmax:
            violations.append(
                {
                    "pile_id": pid,
                    "target_elevation": height,
                    "grading_window_min": wmin,
                    "grading_window_max": wmax,
                    "below_by": min(0.0, height - wmin),
                    "above_by": max(0.0, height - wmax),
                }
            )

    return violations


def sliding_line(
    tracker: BaseTracker,
    violating_piles: list[dict[str, float]],
    slope: float,
    y_intercept: float,
) -> None:
    """
    Slide the grading line vertically to reduce grading window violations.

    Parameters
    ----------
    tracker : BaseTracker
        Tracker whose pile elevations are adjusted.
    project : Project
        Project containing grading constraints.
    violating_piles : list[dict[str, float]]
        List of piles currently outside the grading window.
    slope : float
        Gradient of the grading line.
    y_intercept : float
        Current y-intercept of the grading line.
    """
    # calculate average distance piles are outside the window
    avg_distance = (
        sum(pile["below_by"] + pile["above_by"] for pile in violating_piles) / tracker.pole_count
    )

    # add the average distance to the y_intercept to slide the line up or down
    new_y_intercept = y_intercept + avg_distance

    # update the elevations of each pile based on the new line
    for pile in tracker.piles:
        pile.current_elevation = _interpolate_coords(pile, slope, new_y_intercept)


def grading(tracker: BaseTracker, violating_piles: list[dict[str, float]]) -> None:
    """
    Determine the new ground elevations for piles that fall outside the allowed grading window

    Parameters
    ----------
    tracker : BaseTracker
        Tracker that the violating piles belong to
    violating_piles : list[dict[str, float]]
        List of piles currently outside the grading window.
    """
    for pile in violating_piles:
        p = tracker.get_pile_in_tracker(pile["pile_id"])
        movement = pile["below_by"] + pile["above_by"]
        p.set_current_elevation(p.current_elevation + movement)


def main(project: Project) -> None:
    """
    Run grading optimisation for all trackers in a project.

    Parameters
    ----------
    project : Project
        Project containing trackers and grading constraints.
    """
    for tracker in project.trackers:
        # determine the grading window for the tracker
        window = grading_window(project, tracker)

        # set the tracker piles to the target height line
        slope, y_intercept = target_height_line(tracker, project)

        # if at least one of the piles is outside the window, slide the line up
        # or down to determine its optimal position
        piles_outside = check_within_window(window, tracker)
        if piles_outside:
            sliding_line(tracker, piles_outside, slope, y_intercept)

            # if at least one of the piles is outside the window, begin grading
            piles_outside = check_within_window(window, tracker)
            if piles_outside:
                # Function changes the current ground elevation of the piles
                grading(tracker, piles_outside)

        # Set the final ground elevations of all piles, some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
