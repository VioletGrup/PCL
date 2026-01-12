#!/usr/bin/env python3

from typing import Dict

from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project


def _y_intercept(slope: float, x: float, y: float) -> float:
    return y - slope * x


def _window_by_pile_id(window: list[dict[str, float]]) -> Dict[int, tuple[float, float]]:
    """
    Convert grading_window output into a lookup:
    pile_id -> (min, max)
    """
    out: Dict[int, tuple[float, float]] = {}
    for row in window:
        pid = int(row["pile_id"])
        out[pid] = (float(row["grading_window_min"]), float(row["grading_window_max"]))
    return out


def _interpolate_coords(pile: BasePile, slope: float, y_intercept: float) -> float:
    return slope * pile.northing + y_intercept


def grading_window(project: Project, tracker: BaseTracker) -> list[dict[str, float]]:
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
    Returns a list of piles that are not within the grading window. Empty list
    => all piles are within window.
    Assumes tracker.piles have current_elevation set to the target line.
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
        if not (wmin <= height <= wmax):
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
    project: Project,
    violating_piles: list[dict[str, float]],
    slope: float,
    y_intercept: float,
) -> None:
    # calculate average distance piles are outside the window
    avg_distance = (
        sum(pile["below_by"] + pile["above_by"] for pile in violating_piles) / tracker.pole_count
    )

    # add the average distance to the y_intercept to slide the line up or down
    new_y_intercept = y_intercept + avg_distance

    # update the elevations of each pile based on the new line
    for pile in tracker.piles:
        pile.current_elevation = _interpolate_coords(pile, slope, new_y_intercept)


def main(project: Project) -> None:
    for tracker in project.trackers:
        # determine the grading window for the tracker
        window = grading_window(project, tracker)

        # set the tracker piles to the target height line
        slope, y_intercept = target_height_line(tracker, project)

        # if at least one of the piles is outside the window, slide the line up
        # or down to determine its optimal position
        piles_outside = check_within_window(window, tracker)
        if not piles_outside:
            sliding_line(tracker, project, piles_outside, slope, y_intercept)

        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
