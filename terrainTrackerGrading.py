#!/usr/bin/env python3


from typing import Dict

from .Project import Project
from .ProjectConstraints import ProjectConstraints
from .TerrainFollowingPile import TerrainFollowingPile
from .TerrainFollowingTracker import TerrainFollowingTracker
from .testing_compare_tf import compare_results
from .testing_get_data_tf import load_project_from_excel, to_excel


def _total_grading_cost(violating_piles: list[dict[str, float]]) -> float:
    """
    Return the total amount of grading required in a tracker

    Parameters
    ----------
    violating_piles : list[dict[str, float]]
        List of piles currently outside the grading window.

    Returns
    -------
    float
        Sum of heights that the piles are above or below the grading window
    """
    return sum(abs(v["below_by"]) + v["above_by"] for v in violating_piles)


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
        Dictionary mapping pile_id to (min_height, max_height).
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


def sliding_line(
    tracker: TerrainFollowingTracker,
    violating_piles: list[dict[str, float]],
    slope: float,
    y_intercept: float,
) -> None:
    """
    Slide the grading line vertically to reduce grading window violations.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
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
    # calculate maximum distance piles are outside the window
    max_distance_pile = max(violating_piles, key=lambda x: abs(x["below_by"] + x["above_by"]))
    max_distance = max_distance_pile["below_by"] + max_distance_pile["above_by"]
    movement_limit = (
        violating_piles[0]["grading_window_max"] - violating_piles[0]["grading_window_min"]
    ) / 2

    # determine how much to slide the line by (capped by movement limit)
    if max_distance > movement_limit:
        movement = movement_limit
    elif max_distance < -movement_limit:
        movement = -movement_limit
    else:
        movement = max_distance

    # update the y-intercept based on the required movement
    new_y_intercept = y_intercept - movement

    # update the elevations of each pile based on the new line
    for pile in tracker.piles:
        pile.height = _interpolate_coords(pile, slope, new_y_intercept)


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
    Adjust pile heights to fit within or as close to the grading window while respecting
    segment deflection constraints.
    Parameters
    ----------
    tracker : TerrainFollowingTracker
        The tracker containing the piles to be adjusted.
    project : Project
        The project containing grading constraints.
    violating_piles : list[dict[str, float]]
        List of piles currently outside the grading window.
    Returns
    -------
    list[dict[str, float]]
        List of piles that were moved in this alteration including how far they have moved
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
        # print(tracker.tracker_id, p["pile_in_tracker"], dist_to_window)

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
        pile_heights = []
        for pile in tracker.piles:
            pile_heights.append(pile.height)
        # print(pile.pile_id, pile.height, p["moved_by"], dist_to_window, max_vertical_change)
    return violating_piles, pile_heights


def slope_correction(
    tracker: TerrainFollowingTracker,
    project: Project,
) -> None:
    """
    Check to ensure that all segments are within the maximum segment deflection requirements.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        The tracker containing the piles to be adjusted.
    project : Project
        The project containing grading constraints.
    violating_piles : list[dict[str, float]]
        List of piles that were outside of the grading window and adjusted in the previous
        alteration.
    target_heights: list[float]
        List of all the pile heights when they were set to the target height
    """
    if not tracker.segments:
        tracker.create_segments()

    for _ in range(5):  # iterate slope correction thrice
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
                # print(
                #     1, pile.pile_id, pile.height, correction, length,
                #     slope_delta
                # )
            elif slope_delta < -project.max_strict_segment_slope_change:
                # downwards slope is steeper than allowed, raise the pile
                correction = length * (slope_delta + project.max_strict_segment_slope_change)
                # print(
                #     2, pile.pile_id, pile.height, correction, length,
                #     slope_delta
                # )
            else:
                correction = 0.0
            pile.height -= correction


def alteration3(
    project: Project,
    tracker: TerrainFollowingTracker,
    *,
    span: float | None = None,
    coarse_steps: int = 121,
    fine_steps: int = 121,
    fine_span_fraction: float = 0.1,
) -> None:
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
        piles_outside1 = check_within_window(window, tracker)

        if piles_outside1:
            tracker.create_segments()
            updated_piles_outside1, heights_after1 = alteration1(tracker, project, piles_outside1)
            alteration3(project, tracker)
            slope_correction(tracker, project)
            # for pile in tracker.piles:  ##############
            #     print(tracker.tracker_id, pile.pile_in_tracker, pile.pile_id, pile.height)
            alteration3(project, tracker)

        # complete final grading for any piles still outside of the window
        piles_outside2 = check_within_window(window, tracker)
        if piles_outside2:
            grading(tracker, piles_outside2)

        # Set the final ground elevations, reveal heights and total heights of all piles,
        # some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
            pile.set_total_height(pile.height)
            pile.set_total_revealed()

        #   PRINT FOR TESTING
        # for pile in tracker.piles:
        #     print(
        #         f"{pile.pile_id} IZ: {pile.initial_elevation} FZ: {pile.final_elevation} change: {pile.final_elevation - pile.initial_elevation} height: {pile.total_height}"
        #     )


if __name__ == "__main__":
    print("Initialising project...")
    constraints = ProjectConstraints(
        min_reveal_height=3.22,
        max_reveal_height=5,
        pile_install_tolerance=0.05,
        max_incline=0.15,
        target_height_percantage=0.5,
        max_angle_rotation=0.0,
        max_cumulative_deflection_deg=4.0,
        max_segment_deflection_deg=0.75,
        edge_overhang=0.0,
    )

    # Load project from Excel

    print("Loading data from Excel...")
    excel_path = "PCL/MARYVALE XTR PILING 12D DTM POINTCLOUD.xlsx"  # change if needed
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
        for pid in range(2, tracker.pole_count):
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
    # print("Comparing results to expected outcome...")
    # compare_results()
