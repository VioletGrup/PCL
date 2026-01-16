#!/usr/bin/env python3


from typing import Dict

from Project import Project
from ProjectConstraints import ProjectConstraints
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from testing_get_data_tf import load_project_from_excel


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


def _window_by_pile_in_tracker(window: list[dict[str, float]]) -> Dict[int, tuple[float, float]]:
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
    tracker: TerrainFollowingTracker, project: Project, violating_piles: list[dict[str, float]]
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
        segment_id = pile.get_outgoing_segment_id(tracker)
        if segment_id == -1:
            continue  # skip first and last piles
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
                # set the pile height exactly to the bottom of the grading window
                pile.height = p["grading_window_max"]
                p["moved_by"] = -dist_to_window
        else:
            # current height is sitting below the grading window, pile moved up
            if abs(dist_to_window) > max_vertical_change:
                # if the distance is to far from the window, move by the max allowed change
                pile.height += max_vertical_change
                p["moved_by"] = abs(max_vertical_change)
            else:
                # set the pile height exactly to the top of the grading window
                pile.height = p["grading_window_min"]
                p["moved_by"] = -dist_to_window

    return violating_piles


def alteration2(tracker: TerrainFollowingTracker, violating_piles: list[dict[str, float]]) -> None:
    """
    Moves piles within tracker based on if the pile before was moved previously

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        The tracker containing the piles to be adjusted.
    violating_piles : list[dict[str, float]]
        List of piles that were outside of the grading window and adjusted in the previous
        alteration.
    """
    for p in violating_piles:
        next_id = p["pile_in_tracker"] + 1
        if next_id > tracker.pole_count:
            continue  # handles the case that the last pile was moved and there is no next pile
        next_pile = tracker.get_pile_in_tracker(next_id)

        moved_by = float(p.get("moved_by", 0.0) or 0.0)
        if moved_by > 0:
            # pile was above the window and moved down
            next_pile.height -= moved_by
        else:
            # pile was below the window and moved up
            next_pile.height += abs(moved_by)


def alteration3(tracker: TerrainFollowingTracker, violating_piles: list[dict[str, float]]) -> None:
    """
    Moves all the piles in the tracker based on the average distance of piles currently outside
    the grading window. Only applied to trackers that have atleast one pile in violation.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        The tracker containing the piles to be adjusted.
    violating_piles : list[dict[str, float]]
        List of piles that are still outside of the grading window after previous alterations.
    """
    # determine the average distance that piles are outside the grading window
    total_distance = 0.0
    for p in violating_piles:
        dist_to_window = p["above_by"] + p["below_by"]
        total_distance += dist_to_window
    average_distance = total_distance / tracker.pole_count

    # if the average distance is larger than half the grading window, limit the adjustment
    half_window = (
        violating_piles[0]["grading_window_max"] + violating_piles[0]["grading_window_min"]
    ) / 2
    adjustment = max(-half_window, min(half_window, average_distance))
    # adjust all piles in the tracker by the average distance
    for pile in tracker.piles:
        pile.height += adjustment


def slope_correction(
    tracker: TerrainFollowingTracker,
    project: Project,
    violating_piles: list[dict[str, float]],
    target_heights: list[float],
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

    # for all the piles that were moved in alteration1, move the adjacent pile the same amount
    for p in reversed(violating_piles):
        this_id = p["pile_in_tracker"]
        next_id = p["pile_in_tracker"] + 1
        if next_id > tracker.pole_count:
            continue  # handles the case that the last pile was moved and there is no next pile
        next_pile = tracker.get_pile_in_tracker(next_id)
        moved_by = float(p.get("moved_by", 0.0) or 0.0)
        # print(tracker.get_pile_in_tracker(this_id).height)
        adjustment = abs(tracker.get_pile_in_tracker(this_id).height - target_heights[this_id - 1])
        if moved_by < 0:
            # pile was above the window and moved down
            next_pile.height -= adjustment
        else:
            # pile was below the window and moved up
            next_pile.height += abs(adjustment)
    # apply slope correction to ensuure we are within max segment and cumulative deflection limits
    if not tracker.segments:
        tracker.create_segments()

    for i in range(2):  # iterate slope correction twice
        # calculate 2slope delta: the difference between the incoming and outgoing segment slopes
        # for all piles
        slope_deltas = []
        for pile in tracker.piles:
            if pile.pile_in_tracker == 1:
                slope_delta = 0.0  # first pile has no slope delta
            elif pile.pile_in_tracker == len(tracker.piles):
                slope_delta = 0.0  # last pile has no slope delta
            else:
                incoming_segment = tracker.get_segment_by_id(pile.get_incoming_segment_id())
                outgoing_segment = tracker.get_segment_by_id(pile.get_outgoing_segment_id(tracker))
                slope_delta = incoming_segment.slope() - outgoing_segment.slope()
            slope_deltas.append(
                {"pile_in_tracker": pile.pile_in_tracker, "slope_delta": slope_delta}
            )

        for s in slope_deltas:
            # determine which piles need to be raised or lowered to meet cumulative deflection
            # requirements
            if abs(s["slope_delta"]) > project.max_strict_segment_slope_change:
                print(
                    tracker.get_pile_in_tracker(s["pile_in_tracker"]).pile_id,
                    tracker.get_pile_in_tracker(s["pile_in_tracker"]).height,
                    s["slope_delta"],
                )
                pile = tracker.get_pile_in_tracker(s["pile_in_tracker"])
                segment = tracker.get_segment_by_id(pile.get_outgoing_segment_id(tracker))
                if s["slope_delta"] > 0:
                    # upwards slope is steeper than allowed, lower the pile
                    correction = segment.length() * (
                        s["slope_delta"] - project.max_strict_segment_slope_change
                    )
                    # print(
                    #     1, pile.pile_id, pile.height, correction, segment.length(),
                    #     s["slope_delta"]
                    # )
                elif s["slope_delta"] < 0:
                    # downwards slope is steeper than allowed, raise the pile
                    correction = segment.length() * (
                        s["slope_delta"] + project.max_strict_segment_slope_change
                    )
                    # print(
                    #     2, pile.pile_id, pile.height, correction, segment.length(),
                    #     s["slope_delta"]
                    # )
                else:
                    correction = 0.0
                pile.height -= correction
    # for pile in tracker.piles:  ###############################
    #     print(tracker.tracker_id, pile.pile_in_tracker, pile.height)


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

        """Try sliding first"""

        # set the tracker piles to the target height line
        slope, y_intercept, target_heights = target_height_line(tracker, project)
        piles_outside1 = check_within_window(window, tracker)

        if piles_outside1:
            tracker.create_segments()
            updated_piles_outside1 = alteration1(tracker, project, piles_outside1)

            slope_correction(tracker, project, updated_piles_outside1, target_heights)
            # for pile in tracker.piles:  ##############
            #     print(tracker.tracker_id, pile.pile_in_tracker, pile.height)
            alteration2(tracker, updated_piles_outside1)
            # recheck if any piles are still outside the window
            piles_outside2 = check_within_window(window, tracker)
            if piles_outside2:
                alteration3(tracker, piles_outside2)

        # complete final grading for any piles still outside of the window
        piles_outside3 = check_within_window(window, tracker)
        if piles_outside3:
            grading(tracker, piles_outside3)

        # Set the final ground elevations, reveal heights and total heights of all piles,
        # some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
            pile.set_total_height(pile.height)
            pile.set_total_revealed()

        #   PRINT FOR TESTING
        # for pile in tracker.piles:
        #     print(
        #         f"{pile.pile_id} IZ: {pile.initial_elevation} FZ: {pile.final_elevation}
        #         change: {pile.final_elevation - pile.initial_elevation} height:
        #         {pile.total_height}"
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
    )

    # Load project from Excel

    print("Loading data from Excel...")
    excel_path = "XTR.xlsx"  # change if needed
    sheet_name = "Inputs"  # change to your actual sheet name

    project = load_project_from_excel(
        excel_path=excel_path,
        sheet_name=sheet_name,
        project_name="Punchs_Creek",
        project_type="terrain_following",
        constraints=constraints,
    )

    print("Start Grading...")
    main(project)
    # to_excel(project)
    # print("Results saved to final_pile_elevations_for_tf.xlsx")
    # print("Comparing results to expected outcome...")
    # compare_results()
