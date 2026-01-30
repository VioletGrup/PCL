#!/usr/bin/env python3

import warnings
from typing import Dict

from grading_utils import (
    y_intercept as _y_intercept,
    window_by_pile_in_tracker as _window_by_pile_in_tracker,
    interpolate_coords as _interpolate_coords,
    total_grading_cost as _total_grading_cost,
)
from Project import Project
from ProjectConstraints import ProjectConstraints
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from testing_get_data_tf import load_project_from_excel, to_excel
from shading.shadingAnalysis import main as shading_requirements


def grading_window(project: Project, tracker: TerrainFollowingTracker) -> list[dict[str, float]]:
    """
    Compute the allowable pile height window (min/max) for each pile in a tracker.

    The window is derived from each pile’s:
      - true_min_height(project)
      - true_max_height(project)

    Parameters
    ----------
    project : Project
        Provides reveal/tolerance constraints used inside pile window methods.
    tracker : TerrainFollowingTracker
        Tracker whose piles will be evaluated.

    Returns
    -------
    list[dict[str, float]]
        Per-pile window information. Each dict contains:
        - "pile_id"
        - "pile_in_tracker"
        - "grading_window_min"
        - "grading_window_max"
        - "ground_elevation" (current_elevation snapshot)
    """
    window = []
    for pile in tracker.piles:
        wmin = pile.true_min_height(project)
        wmax = pile.true_max_height(project)

        # Warn if inverted window (min > max) from excessive flooding/tolerance
        if wmin > wmax:
            warnings.warn(
                f"Pile {pile.pile_id}: inverted grading window (min={wmin:.3f} > max={wmax:.3f}). "
                "This may be caused by excessive flooding_allowance or pile_install_tolerance.",
                UserWarning,
            )

        window.append(
            {
                "pile_id": pile.pile_id,
                "pile_in_tracker": pile.pile_in_tracker,
                "grading_window_min": wmin,
                "grading_window_max": wmax,
                "ground_elevation": pile.current_elevation,
            }
        )
    return window


def target_height_line(tracker: TerrainFollowingTracker, project: Project) -> None:
    """
    Initialise pile heights along a target-height straight line (terrain-following).

    - Slope is estimated from the line connecting first/last pile CURRENT elevations
      (current_elevation), then clamped to +/- project.constraints.max_incline.
    - The first pile is set to its target height (pile_at_target_height(project)).
    - All pile heights are then set by linear interpolation with respect to northing.

    This sets `pile.height` for all piles in the tracker. It does NOT grade the ground
    and does NOT guarantee window compliance.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose pile heights will be initialised.
    project : Project
        Provides max incline and target height policy.
    """
    # Handle single-pile tracker: no slope calculation needed
    if len(tracker.piles) == 1:
        pile = tracker.piles[0]
        pile.height = pile.pile_at_target_height(project)
        return

    first_pile = tracker.get_first()
    last_pile = tracker.get_last()

    # Guard against ZeroDivisionError from vertical alignment
    northing_diff = last_pile.northing - first_pile.northing
    if abs(northing_diff) < 1e-9:
        raise ValueError(
            "Cannot calculate slope: piles have identical northing coordinates "
            "(vertical alignment). Check tracker pile positions."
        )

    # determine the equation of the line assuming the ground is a straight line
    slope = (last_pile.current_elevation - first_pile.current_elevation) / northing_diff
    max_incline = project.constraints.max_incline
    slope = max(-max_incline, min(max_incline, slope))  # ensure slope is below max slope
    first_pile.height = first_pile.pile_at_target_height(project)
    pile_y_intercept = _y_intercept(slope, first_pile.northing, first_pile.height)

    # set each pile to the target height and elevation based on the linear equation
    for pile in tracker.piles:
        pile.height = _interpolate_coords(pile, slope, pile_y_intercept)


def check_within_window(
    window: list[dict[str, float]], tracker: TerrainFollowingTracker
) -> list[dict[str, float]]:
    """
    Check whether each pile’s current `pile.height` lies inside its grading window.

    Parameters
    ----------
    window : list[dict[str, float]]
        Output of `grading_window(project, tracker)` for this tracker.
    tracker : TerrainFollowingTracker
        Tracker whose current `pile.height` values will be tested.

    Returns
    -------
    list[dict[str, float]]
        A list of violations (empty if none). Each violation dict contains:
        - "pile_in_tracker"
        - "grading_window_min"
        - "grading_window_max"
        - "below_by" (<= 0): height - wmin (negative means below)
        - "above_by" (>= 0): height - wmax (positive means above)
    """
    limits = _window_by_pile_in_tracker(window)

    violations = []
    for pile in tracker.piles:
        pid = pile.pile_in_tracker
        if pid not in limits:
            raise ValueError(f"Pile id {pid} not found in grading window")

        wmin, wmax = limits[pid]
        height = pile.height

        # if the pile is outside the window, add it to the list and find how far away it is
        if not wmin <= height <= wmax:
            violations.append(
                {
                    "pile_in_tracker": pid,
                    "grading_window_min": wmin,
                    "grading_window_max": wmax,
                    "below_by": min(0.0, height - wmin),
                    "above_by": max(0.0, height - wmax),
                }
            )

    return violations


def grading(tracker: TerrainFollowingTracker, violating_piles: list[dict[str, float]]) -> None:
    """
    Apply final ground grading to eliminate remaining window violations.

    For each violating pile, this adjusts the pile's current ground elevation by the
    required movement amount:

        movement = below_by + above_by

    Since:
      - below_by is negative when the pile is below the window,
      - above_by is positive when the pile is above the window,

    movement moves the ground/elevation baseline so the pile height would fall
    on the nearest bound (min or max), depending on violation direction.

    Note: First and last piles (anchors) are NEVER graded to preserve the anchor invariant.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker containing the piles to grade.
    violating_piles : list[dict[str, float]]
        Output of `check_within_window(...)` for the current heights.
    """
    num_piles = len(tracker.piles)
    for pile in violating_piles:
        pid = pile["pile_in_tracker"]
        # Skip first and last piles (anchor invariant)
        if pid == 1 or pid == num_piles:
            continue
        p = tracker.get_pile_in_tracker(pid)
        movement = pile["below_by"] + pile["above_by"]
        p.set_current_elevation(p.current_elevation + movement)


def shift_piles(
    tracker: TerrainFollowingTracker,
    project: Project,
    violating_piles: list[dict[str, float]],
) -> None:
    """
    First-pass correction: move violating pile heights toward their window bounds
    subject to a conservative per-segment vertical-change limit.

    For each violating pile (except pile 1 which has no incoming segment):
      - compute conservative max vertical change:
            max_vertical_change = segment.length() * project.max_conservative_segment_slope_change
      - compute signed distance to nearest window boundary:
            dist_to_window = above_by + below_by
      - move pile.height toward the window, capped by max_vertical_change
      - store "moved_by" in the violation dict (signed)

    This updates `pile.height` but does not modify ground elevations.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose pile heights will be adjusted.
    project : Project
        Provides conservative segment slope change limit.
    violating_piles : list[dict[str, float]]
        Output of `check_within_window(...)` (will be mutated with "moved_by").
    """
    for p in violating_piles:
        pile = tracker.get_pile_in_tracker(p["pile_in_tracker"])
        segment_id = pile.get_incoming_segment_id()
        if segment_id == -1:
            continue  # skip last piles
        segment = tracker.get_segment_by_id(segment_id)

        # find the maximum vertical change allowed for the segment based on defelction constraints
        max_vertical_change = segment.length() * project.max_conservative_segment_slope_change
        dist_to_window = p["above_by"] + p["below_by"]

        # adjust the height of the pile within the allowed vertical change
        if dist_to_window > 0:
            # current height is sitting above the grading window, pile moved down
            if dist_to_window > max_vertical_change:
                # if the distance is to far from the window, move by the max allowed change
                pile.height -= max_vertical_change
                p["moved_by"] = -abs(max_vertical_change)
            else:
                # set the pile height exactly to the top of the grading window
                pile.height = p["grading_window_max"]
                p["moved_by"] = -dist_to_window
        elif dist_to_window < 0:
            # current height is sitting below the grading window, pile moved up
            if abs(dist_to_window) > max_vertical_change:
                # if the distance is to far from the window, move by the max allowed change
                pile.height += max_vertical_change
                p["moved_by"] = abs(max_vertical_change)
            else:
                # set the pile height exactly to the bottom of the grading window
                pile.height = p["grading_window_min"]
                p["moved_by"] = -dist_to_window
        else:
            continue


def slope_correction(
    tracker: TerrainFollowingTracker,
    project: Project,
) -> None:
    """
    Enforce strict local slope-change constraints by iteratively correcting pile heights.

    For each interior pile, compute the difference between incoming and outgoing segment
    slopes. If the slope delta exceeds +/- project.max_strict_segment_slope_change, apply
    a vertical correction proportional to segment length:

        correction = length * (excess slope_delta)

    This is applied directly to `pile.height`.

    Notes
    -----
    - This modifies heights only (not ground elevations).
    - Re-runs a small fixed number of passes (currently 5).

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose pile heights will be adjusted.
    project : Project
        Provides strict segment slope change limit.
    """
    if not tracker.segments:
        tracker.create_segments()

    for _ in range(5):  # iterate slope correction five times
        # calculate slope delta: the difference between the incoming and outgoing segment slopes
        # for all piles
        for pile in tracker.piles:
            if pile.pile_in_tracker == 1 or pile.pile_in_tracker == len(tracker.piles):
                slope_delta = 0.0  # first and last piles haves no slope delta
                continue  # next calculation not needed for first and last piles
            else:
                incoming_segment = tracker.get_segment_by_id(pile.get_incoming_segment_id())
                outgoing_segment = tracker.get_segment_by_id(pile.get_outgoing_segment_id(tracker))
                slope_delta = incoming_segment.slope() - outgoing_segment.slope()
            length = abs(incoming_segment.length())
            if slope_delta > project.max_strict_segment_slope_change:
                # upwards slope is steeper than allowed, lower the pile
                correction = length * (slope_delta - project.max_strict_segment_slope_change)
            elif slope_delta < -project.max_strict_segment_slope_change:
                # downwards slope is steeper than allowed, raise the pile
                correction = length * (slope_delta + project.max_strict_segment_slope_change)
            else:
                correction = 0.0
            pile.height -= correction


def slide_all_piles(
    project: Project,
    tracker: TerrainFollowingTracker,
    *,
    span: float | None = None,
    coarse_steps: int = 121,
    fine_steps: int = 121,
    fine_span_fraction: float = 0.1,
) -> None:
    """
    Optimise a uniform vertical shift applied to all pile heights (intercept-only).

    This is an intercept-only optimisation:
      - All piles are shifted by the same amount (pile.height = original_height - shift)
      - DOES NOT change slope relationships between piles
      - Therefore DOES NOT change segment/cumulative deflection angles

    Feasibility constraint:
      - The first pile and last pile must remain inside their grading windows
        after the shift. This determines an allowed shift interval.

    Objective:
      - Minimise `_total_grading_cost(...)` over all piles after the shift.

    Parameters
    ----------
    project : Project
        Provides grading window computation via pile.true_min/max_height.
    tracker : TerrainFollowingTracker
        Tracker whose pile heights will be uniformly shifted.
    span : float | None, optional
        Optional half-span search size around the initial guess.
        If None, uses the full feasible interval.
    coarse_steps : int, optional
        Number of samples in the coarse grid search.
    fine_steps : int, optional
        Number of samples in the refined grid search around the best coarse shift.
    fine_span_fraction : float, optional
        Fraction of the coarse search width used for the fine search window.

    Returns
    -------
    None
        Updates `pile.height` in-place using the best found shift.
    """
    if not tracker.piles:
        return

    # Ensure consistent ordering
    tracker.piles.sort(key=lambda p: p.pile_in_tracker)

    # Cache current heights
    original_heights = [p.height for p in tracker.piles]

    # Compute a window snapshot ONCE (windows depend on current_elevation; shift doesn't
    # change that)
    window0 = grading_window(project, tracker)

    first = tracker.get_first()
    last = tracker.get_last()

    # Feasible shift interval from endpoints:
    # lo <= h - shift <= hi  =>  h - hi <= shift <= h - lo
    f_lo = first.true_min_height(project)
    f_hi = first.true_max_height(project)
    l_lo = last.true_min_height(project)
    l_hi = last.true_max_height(project)

    f_min_shift = first.height - f_hi
    f_max_shift = first.height - f_lo
    l_min_shift = last.height - l_hi
    l_max_shift = last.height - l_lo

    allowed_min = max(f_min_shift, l_min_shift)
    allowed_max = min(f_max_shift, l_max_shift)

    # If endpoints are already inconsistent, do nothing (or pick 0)
    if allowed_min > allowed_max:
        return

    # Choose a default search span if not provided
    # Span should cover the feasible interval; this mirrors how sliding_line uses intercept_span.
    if span is None:
        # half-width around the midpoint that covers the full allowed interval
        mid = 0.5 * (allowed_min + allowed_max)
        span = 0.5 * (allowed_max - allowed_min)
        span = max(span, 1e-9)
        initial = mid
    else:
        # centre the search around "no shift" but clamp to allowed interval
        initial = max(allowed_min, min(allowed_max, 0.0))
        span = max(span, 1e-9)

    def apply_shift(s: float) -> None:
        for pile, h0 in zip(tracker.piles, original_heights):
            pile.height = h0 - s

    def eval_shift(s: float) -> tuple[float, list[dict[str, float]], bool]:
        # Enforce feasibility by endpoints (fast reject)
        if s < allowed_min or s > allowed_max:
            return float("inf"), [], False

        apply_shift(s)

        # Endpoints guaranteed in-window due to allowed interval,
        # but keep this consistent with sliding_line logic:
        viols = check_within_window(window0, tracker)
        cost = _total_grading_cost(viols)
        return cost, viols, True

    best_s = initial
    best_cost = float("inf")

    # --- coarse search over [initial-span, initial+span] intersected with allowed ---
    lo = max(allowed_min, initial - span)
    hi = min(allowed_max, initial + span)

    if coarse_steps < 2:
        coarse_steps = 2

    for k in range(coarse_steps):
        s = lo + (hi - lo) * (k / (coarse_steps - 1))
        cost, _, ok = eval_shift(s)
        if ok and cost < best_cost:
            best_cost = cost
            best_s = s

    # --- fine search around best coarse ---
    fine_span = (hi - lo) * fine_span_fraction
    fine_span = max(fine_span, 1e-9)

    lo2 = max(allowed_min, best_s - fine_span)
    hi2 = min(allowed_max, best_s + fine_span)

    if fine_steps < 2:
        fine_steps = 2

    for k in range(fine_steps):
        s = lo2 + (hi2 - lo2) * (k / (fine_steps - 1))
        cost, _, ok = eval_shift(s)
        if ok and cost < best_cost:
            best_cost = cost
            best_s = s

    # Apply the best shift permanently
    apply_shift(best_s)


def main(project: Project) -> None:
    """
    Run grading optimisation for all trackers in a project.

    Parameters
    ----------
    project : Project
        Project containing trackers and grading constraints.
    """
    # ensure piles in trackers are sorted north to south
    project.renumber_piles_by_northing()

    for tracker in project.trackers:
        # determine the grading window for the tracker
        window = grading_window(project, tracker)

        # set the tracker piles to the target height line
        target_height_line(tracker, project)
        piles_outside1 = check_within_window(window, tracker)

        if piles_outside1:
            tracker.create_segments()
            shift_piles(tracker, project, piles_outside1)
            slide_all_piles(project, tracker)
            slope_correction(tracker, project)
            slide_all_piles(project, tracker)

        # complete final grading for any piles still outside of the window
        piles_outside2 = check_within_window(window, tracker)
        if piles_outside2:
            grading(tracker, piles_outside2)

        tracker.create_segments()
        # Set the final ground elevations, reveal heights and total heights of all piles,
        # some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
            pile.set_total_height(pile.height)
            pile.set_total_revealed()
            pile.set_final_degree_break(tracker)
        tracker.set_final_deflection_metrics()


if __name__ == "__main__":
    print("Initialising project...")
    constraints = ProjectConstraints(
        min_reveal_height=1.075,
        max_reveal_height=1.525,
        pile_install_tolerance=0.075 * 2,
        max_incline=0.10,
        target_height_percentage=0.5,
        max_angle_rotation=0.0,
        max_cumulative_deflection_deg=4.0,
        max_segment_deflection_deg=0.5,
        edge_overhang=0.0,
    )

    # Load project from Excel

    print("Loading data from Excel...")
    excel_path = "MARYVALE XTR PILING 12D DTM POINTCLOUD.xlsx"  # change if needed
    sheet_name = "in"  # change to your actual sheet name

    project = load_project_from_excel(
        excel_path=excel_path,
        sheet_name=sheet_name,
        project_name="Punchs_Creek",
        project_type="terrain_following",
        constraints=constraints,
    )

    print("Start Grading...")
    main(project)
    to_excel(project)
    print("Results saved to final_pile_elevations_for_tf.xlsx")

    #### TEST DEGREE BREAKS ####
    viol_break = 0
    viol_cum_n = 0
    viol_cum_s = 0

    break_lim = float(project.constraints.max_segment_deflection_deg)
    cum_lim = float(project.constraints.max_cumulative_deflection_deg)

    for tracker in project.trackers:
        tracker.create_segments()

        # Determine direction (northing increasing or decreasing along pile_in_tracker)
        first = tracker.get_first()
        last = tracker.get_last()
        north_to_south = first.northing > last.northing  # True means pile 1 is more north

        centre = tracker.get_centre_pile()
        centre_id = centre.pile_in_tracker

        north_cum = 0.0
        south_cum = 0.0

        # Check breaks at interior piles
        for pid in range(1, tracker.pole_count):
            pile = tracker.get_pile_in_tracker(pid)
            b = pile.degree_break(tracker)

            if b > break_lim + 1e-9:
                print(
                    f"Break violation: Tracker {tracker.tracker_id} pile {pile.pile_id} "
                    f"break={b:.6f}° (limit {break_lim}°)"
                )
                viol_break += 1

            # accumulate by wing using physical north/south direction
            # north wing = side closer to the north end of the tracker
            if north_to_south:
                # pile 1 is north end
                if pid <= centre_id:
                    north_cum += b
                else:
                    south_cum += b
            else:
                # pile 1 is south end, so north end is at larger pid
                if pid >= centre_id:
                    north_cum += b
                else:
                    south_cum += b

        if north_cum > cum_lim + 1e-9:
            print(
                f"North wing cumulative break violation: Tracker {tracker.tracker_id} "
                f"cumulative={north_cum:.6f}° (limit {cum_lim}°)"
            )
            viol_cum_n += 1

        if south_cum > cum_lim + 1e-9:
            print(
                f"South wing cumulative break violation: Tracker {tracker.tracker_id} "
                f"cumulative={south_cum:.6f}° (limit {cum_lim}°)"
            )
            viol_cum_s += 1

    print(
        f"\n{viol_cum_n} north cumulative violations, {viol_cum_s} south cumulative violations, "
        f"{viol_break} break violations"
    )
    ####################################

    ####### GRADING COUNTER #######
    x = 0
    su = 0
    for tracker in project.trackers:
        for pile in tracker.piles:
            if pile.final_elevation != pile.initial_elevation:
                x += 1
                su += abs(pile.final_elevation - pile.initial_elevation)
                # print(pile.pile_id, pile.final_elevation - pile.initial_elevation)
    print(f"{x} piles requring grading, total cost = {su}")
