#!/usr/bin/env python3


import math
from typing import Dict

from .flatTrackerGrading import sliding_line
from .Project import Project
from .ProjectConstraints import ProjectConstraints
from .TerrainFollowingPile import TerrainFollowingPile
from .TerrainFollowingTracker import TerrainFollowingTracker
from .testing_compare_tf import compare_results
from .testing_get_data_tf import load_project_from_excel, to_excel


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


def _window_by_pile_in_tracker(
    window: list[dict[str, float]],
) -> Dict[int, tuple[float, float]]:
    """
    Convert grading window data into a lookup dictionary.

    Parameters
    ----------
    window : list[dict[str, float]]
        List of grading window dictionaries containing pile limits.

    Returns
    -------
    Dict[int, tuple[float, float]]
        Dictionary mapping pile_in_tracker to (min_height, max_height).
    """
    out: Dict[int, tuple[float, float]] = {}
    for row in window:
        pid = int(row["pile_in_tracker"])
        out[pid] = (float(row["grading_window_min"]), float(row["grading_window_max"]))
    return out


def _interpolate_coords(pile: TerrainFollowingPile, slope: float, y_intercept: float) -> float:
    """
    Interpolate the elevation of a pile from a linear grading line.

    Parameters
    ----------
    pile : TerrainFollowingPile
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


def grading_window(project: Project, tracker: TerrainFollowingTracker) -> list[dict[str, float]]:
    """
    Generate the grading window for all piles in a tracker.

    Parameters
    ----------
    project : Project
        Project containing grading constraints.
    tracker : TerrainFollowingTracker
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
                "pile_in_tracker": pile.pile_in_tracker,
                "grading_window_min": pile.true_min_height(project),
                "grading_window_max": pile.true_max_height(project),
                "ground_elevation": pile.current_elevation,
            }
        )
    return window


def target_height_line(tracker: TerrainFollowingTracker, project: Project) -> tuple[float, float]:
    """
    Set pile elevations along a target height line constrained by project limits.
    Different to flat trackers as it determines the slope based on the current ground

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose piles are adjusted.
    project : Project
        Project providing target heights and incline constraints.

    Returns
    -------
    tuple[float, float]
        The slope and y-intercept of the target height line.
    """
    first_pile = tracker.get_first()
    last_pile = tracker.get_last()
    # deterimine the equation of the line assuming the ground is a straight line
    slope = (last_pile.current_elevation - first_pile.current_elevation) / (
        last_pile.northing - first_pile.northing
    )
    max_incline = project.constraints.max_incline
    slope = max(-max_incline, min(max_incline, slope))  # ensure slope is below max slope
    first_pile.height = first_pile.pile_at_target_height(project)
    pile_y_intercept = _y_intercept(slope, first_pile.northing, first_pile.height)

    # set each pile to the target height and elevation based on the linear equation
    target_heights = []
    for pile in tracker.piles:
        pile.height = _interpolate_coords(pile, slope, pile_y_intercept)
        target_heights.append(pile.height)
    return slope, pile_y_intercept, target_heights


def check_within_window(
    window: list[dict[str, float]], tracker: TerrainFollowingTracker
) -> list[dict[str, float]]:
    """
    Identify piles whose elevations lie outside their grading window.

    Parameters
    ----------
    window : list[dict[str, float]]
        Grading window data for the tracker.
    tracker : TerrainFollowingTracker
        Tracker whose piles are checked.

    Returns
    -------
    list[dict[str, float]]
        List of dictionaries describing piles that violate the grading window.
        An empty list indicates no violations.
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
    Determine the new ground elevations for piles that fall outside the allowed grading window

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker that the violating piles belong to
    violating_piles : list[dict[str, float]]
        List of piles currently outside the grading window.
    """
    for pile in violating_piles:
        p = tracker.get_pile_in_tracker(pile["pile_in_tracker"])
        movement = pile["below_by"] + pile["above_by"]
        p.set_current_elevation(p.current_elevation + movement)


def alteration1(
    tracker: TerrainFollowingTracker,
    project: Project,
    violating_piles: list[dict[str, float]],
) -> list[dict[str, float]]:
    """
    Force every pile's height to the CENTRE of its grading window.

    - Ignores ALL constraints (segment + cumulative deflection, etc.)
    - Assumes later steps (slope_correction / verify_and_fix_deflections) will fix angles.
    - Only changes pile.height (does NOT change ground/current_elevation).

    Notes:
    - This applies to *all piles in the tracker*, not just violators, because you asked
      to bring all heights to the window centre.
    - moved_by is recorded for piles present in violating_piles list (kept for debugging).
    """
    # quick lookup so we can still report moved_by for the original violators
    violator_ids = {v["pile_in_tracker"]: v for v in violating_piles}

    for pile in tracker.piles:
        wmin = pile.true_min_height(project)
        wmax = pile.true_max_height(project)
        target = 0.5 * (wmin + wmax)

        h0 = pile.height
        pile.height = target

        # record movement for any pile that was flagged as a violator in the input list
        v = violator_ids.get(pile.pile_in_tracker)
        if v is not None:
            v["grading_window_min"] = wmin
            v["grading_window_max"] = wmax
            v["moved_by"] = pile.height - h0

    return violating_piles


# def alteration1(
#     tracker: TerrainFollowingTracker,
#     project: Project,
#     violating_piles: list[dict[str, float]],
# ) -> list[dict[str, float]]:
#     """
#     Snap any violating pile heights directly into their grading window.

#     IMPORTANT:
#     - This intentionally ignores segment/wing deflection constraints.
#       You must run slope_correction() afterwards to restore deflection compliance.
#     - It only changes pile.height (not ground/current_elevation).
#     """
#     for v in violating_piles:
#         pid = v["pile_in_tracker"]
#         pile = tracker.get_pile_in_tracker(pid)

#         wmin = float(v["grading_window_min"])
#         wmax = float(v["grading_window_max"])

#         h0 = pile.height
#         if h0 < wmin:
#             pile.height = wmin
#             v["moved_by"] = pile.height - h0
#         elif h0 > wmax:
#             pile.height = wmax
#             v["moved_by"] = pile.height - h0
#         else:
#             v["moved_by"] = 0.0

#     return violating_piles


def slope_correction(
    tracker: TerrainFollowingTracker,
    project: Project,
    violating_piles: list[dict[str, float]],
    target_heights: list[float],
) -> None:
    """
    Apply slope-change corrections to ensure segment-to-segment slope deltas are within limits.

    Uses a multi-pass approach:
    1. Propagate alteration-1 adjustments to adjacent piles
    2. Iteratively correct segment deflections
    3. Iteratively correct cumulative deflections
    """
    if not tracker.segments:
        tracker.create_segments()

    # Convert limits to radians
    segment_deflection_limit = math.radians(project.constraints.max_segment_deflection_deg)
    wing_deflection_limit = math.radians(project.constraints.max_cumulative_deflection_deg)

    # Identify wings
    centre_pile = tracker.get_centre_pile()
    centre_idx = centre_pile.pile_in_tracker

    north_wing_segments = [
        seg
        for seg in tracker.segments
        if seg.start_pile.pile_in_tracker < centre_idx
        and seg.end_pile.pile_in_tracker <= centre_idx
    ]

    south_wing_segments = [
        seg
        for seg in tracker.segments
        if seg.start_pile.pile_in_tracker >= centre_idx
        and seg.end_pile.pile_in_tracker > centre_idx
    ]

    epsilon = 1e-12
    max_iterations = 50  # Increased from 10

    # Step 2: Iterative correction with adaptive relaxation
    for iteration in range(max_iterations):
        max_violation = 0.0

        for wing in [north_wing_segments, south_wing_segments]:
            if not wing:
                continue

            # Calculate current cumulative deflection
            cumulative = sum(abs(math.radians(seg.degree_of_deflection())) for seg in wing)

            # Step 2a: Fix individual segment violations first
            for seg in wing:
                theta = math.radians(seg.degree_of_deflection())
                theta_abs = abs(theta)

                if theta_abs <= segment_deflection_limit + epsilon:
                    continue

                max_violation = max(max_violation, theta_abs - segment_deflection_limit)

                # Calculate target height for end pile
                theta_lim = math.copysign(segment_deflection_limit, theta)
                dx = seg.end_pile.northing - seg.start_pile.northing

                if abs(dx) < epsilon:
                    continue

                desired_end_height = seg.start_pile.height + math.tan(theta_lim) * dx

                # Use adaptive relaxation - be more aggressive as we iterate
                relaxation = min(0.8, 0.3 + (iteration / max_iterations) * 0.5)
                delta_h = desired_end_height - seg.end_pile.height
                seg.end_pile.height += relaxation * delta_h

            # Step 2b: Fix cumulative deflection violations
            cumulative = sum(abs(math.radians(seg.degree_of_deflection())) for seg in wing)

            if cumulative > wing_deflection_limit + epsilon:
                max_violation = max(max_violation, cumulative - wing_deflection_limit)

                excess = cumulative - wing_deflection_limit

                # Distribute correction proportionally to each segment's contribution
                total_deflection = sum(
                    abs(math.radians(seg.degree_of_deflection())) for seg in wing
                )

                for seg in wing:
                    theta = math.radians(seg.degree_of_deflection())
                    theta_abs = abs(theta)

                    # Calculate this segment's share of the reduction
                    if total_deflection > epsilon:
                        reduction_fraction = theta_abs / total_deflection
                        theta_reduction = excess * reduction_fraction
                    else:
                        theta_reduction = excess / len(wing)

                    dx = seg.end_pile.northing - seg.start_pile.northing
                    if abs(dx) < epsilon:
                        continue

                    # Target angle after reduction
                    theta_target = math.copysign(max(theta_abs - theta_reduction, 0.0), theta)
                    desired_end_height = seg.start_pile.height + math.tan(theta_target) * dx

                    relaxation = min(0.8, 0.3 + (iteration / max_iterations) * 0.5)
                    delta_h = desired_end_height - seg.end_pile.height
                    seg.end_pile.height += relaxation * delta_h

        # Check for convergence
        # if max_violation < epsilon:
        #     print(f"Converged after {iteration + 1} iterations")
        #     break


# def alteration3(project: Project, tracker: TerrainFollowingTracker) -> float:
#     """
#     Excel-style global shift:
#     - average violation over violating piles only
#     - clamp shift so endpoints stay within their windows
#     Returns applied adjustment.
#     """
#     total = 0.0
#     count = 0

#     for pile in tracker.piles:
#         hi = pile.true_max_height(project)
#         lo = pile.true_min_height(project)
#         if pile.height > hi:
#             total += pile.height - hi
#             count += 1
#         elif pile.height < lo:
#             total += pile.height - lo
#             count += 1

#     if count == 0:
#         return 0.0

#     avg = total / count  # ✅ only violators

#     first = tracker.get_first()
#     last = tracker.get_last()

#     # ✅ true half-window
#     half_window = (first.true_max_height(project) - first.true_min_height(project)) / 2.0
#     optimal = max(-half_window, min(half_window, avg))

#     # ✅ clamp so endpoints stay in window after shifting
#     a0_min = first.height - first.true_max_height(project)
#     a0_max = first.height - first.true_min_height(project)
#     a1_min = last.height - last.true_max_height(project)
#     a1_max = last.height - last.true_min_height(project)

#     allowed_min = max(a0_min, a1_min)
#     allowed_max = min(a0_max, a1_max)

#     if allowed_min > allowed_max:
#         adjustment = 0.0
#     else:
#         adjustment = max(allowed_min, min(allowed_max, optimal))

#     for pile in tracker.piles:
#         pile.height -= adjustment

#     return adjustment


def _total_grading_cost(violations: list[dict[str, float]]) -> float:
    # below_by is negative, above_by is positive in your structure
    return sum(abs(v["below_by"]) + abs(v["above_by"]) for v in violations)


def alteration3_sliding_shift(
    project: Project,
    tracker: TerrainFollowingTracker,
    *,
    span: float | None = None,
    coarse_steps: int = 121,
    fine_steps: int = 121,
    fine_span_fraction: float = 0.1,
) -> float:
    """
    Like sliding_line, but ONLY optimises a uniform vertical shift (intercept-only).
    DOES NOT change slope -> DOES NOT change segment/cumulative angles at all.

    Constraints:
      - first pile remains within its grading window
      - last pile remains within its grading window

    Objective:
      - minimise total grading-window violation cost over all piles after the shift.

    Returns
    -------
    float
        The applied shift (signed). Heights updated by: pile.height -= shift
    """
    if not tracker.piles:
        return 0.0

    # Ensure consistent ordering
    tracker.piles.sort(key=lambda p: p.pile_in_tracker)

    # Cache current heights
    original_heights = [p.height for p in tracker.piles]

    # Compute a window snapshot ONCE (windows depend on current_elevation; shift doesn't change that)
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
        return 0.0

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
    return best_s


def verify_and_fix_deflections(tracker: TerrainFollowingTracker, project: Project) -> None:
    """Final pass to ensure all deflection constraints are met."""
    if not tracker.segments:
        tracker.create_segments()

    segment_limit = project.constraints.max_segment_deflection_deg
    cumulative_limit = project.constraints.max_cumulative_deflection_deg

    # Check segment violations
    for seg in tracker.segments:
        deflection = abs(seg.degree_of_deflection())
        if deflection > segment_limit:
            # Adjust end pile to exactly meet limit
            theta_lim = math.copysign(
                math.radians(segment_limit), math.radians(seg.degree_of_deflection())
            )
            dx = seg.end_pile.northing - seg.start_pile.northing
            if abs(dx) > 1e-9:
                seg.end_pile.height = seg.start_pile.height + math.tan(theta_lim) * dx


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
        slope, y_intercept, target_heights = target_height_line(tracker, project)
        piles_outside0 = check_within_window(window, tracker)
        if piles_outside0:
            window_half = (
                piles_outside0[0]["grading_window_max"] - piles_outside0[0]["grading_window_min"]
            ) / 2.0

            intercept_span = max(1e-6, 4.0 * window_half)

            slope, y_intercept = sliding_line(
                tracker,
                project,
                slope,
                y_intercept,
                intercept_span=intercept_span,
                slope_tolerance=0.05,
                slope_steps=11,
            )

        piles_outside1 = check_within_window(window, tracker)
        if piles_outside1:
            tracker.create_segments()
            updated_piles_outside1 = alteration1(tracker, project, piles_outside1)
            slope_correction(tracker, project, updated_piles_outside1, target_heights)

            # alteration3(project, tracker)
            alteration3_sliding_shift(project, tracker)

        # perform one last check of angles
        verify_and_fix_deflections(tracker, project)

        # complete final grading for any piles still outside of the window
        piles_outside2 = check_within_window(window, tracker)
        if piles_outside2:
            grading(tracker, piles_outside2)

        # perfrom one last check for segment and cumulative deflections
        tracker.create_segments()
        # Set the final ground elevations, reveal heights and total heights of all piles,
        # some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
            pile.set_total_height(pile.height)
            pile.set_total_revealed()


if __name__ == "__main__":
    print("Initialising project...")
    constraints = ProjectConstraints(
        min_reveal_height=1.075,
        max_reveal_height=1.6,
        pile_install_tolerance=0.15,
        max_incline=0.10,
        target_height_percantage=0.5,
        max_angle_rotation=0.0,
        max_cumulative_deflection_deg=4.0,
        max_segment_deflection_deg=0.5,
        edge_overhang=0.0,
    )

    # Load project from Excel

    print("Loading data from Excel...")
    excel_path = "PCL/XTR.xlsx"  # change if needed
    sheet_name = "Inputs"  # change to your actual sheet name

    project = load_project_from_excel(
        excel_path=excel_path,
        sheet_name=sheet_name,
        project_name="Maryvale",
        project_type="terrain_following",
        constraints=constraints,
    )

    print("Start Grading...")
    main(project)
    to_excel(project)

    #### TEST SEGMENT DEFLECTIONS ####
    t_north = 0
    t_south = 0
    s = 0

    for tracker in project.trackers:
        # Get centre pile to split wings
        centre_pile = tracker.get_centre_pile()
        centre_idx = centre_pile.pile_in_tracker

        north_cumulative = 0.0
        south_cumulative = 0.0

        for segment in tracker.segments:
            deflection = round(abs(segment.degree_of_deflection()), 11)

            # Check segment violation
            if deflection > round(project.constraints.max_segment_deflection_deg, 11):
                print(
                    f"Segment violation: {segment.start_pile.pile_id} -> {segment.end_pile.pile_id}, "
                    f"deflection: {segment.degree_of_deflection():.12f}°"
                )
                s += 1

            # Accumulate by wing
            if segment.end_pile.pile_in_tracker <= centre_idx:
                # North wing (before/at center)
                north_cumulative += deflection
            elif segment.start_pile.pile_in_tracker >= centre_idx:
                # South wing (at/after center)
                south_cumulative += deflection

        # Check cumulative violations by wing
        north_cumulative = round(north_cumulative, 11)
        south_cumulative = round(south_cumulative, 11)
        max_cumulative = round(project.constraints.max_cumulative_deflection_deg, 11)

        if north_cumulative > max_cumulative:
            print(
                f"North wing violation: Tracker {tracker.tracker_id}, "
                f"cumulative: {north_cumulative:.12f}° (limit: {max_cumulative}°)"
            )
            t_north += 1

        if south_cumulative > max_cumulative:
            print(
                f"South wing violation: Tracker {tracker.tracker_id}, "
                f"cumulative: {south_cumulative:.12f}° (limit: {max_cumulative}°)"
            )
            t_south += 1

    print(
        f"\n{t_north} north wing violations, {t_south} south wing violations, "
        f"{s} segment violations"
    )
    ####################################

    ####### GRADING COUNTER #######
    x = 0
    for tracker in project.trackers:
        for pile in tracker.piles:
            if pile.final_elevation != pile.initial_elevation:
                x += 1
    print(f"{x} piles requring grading")

    print("Results saved to final_pile_elevations_for_tf.xlsx")
    # print("Comparing results to expected outcome...")
    # compare_results()
