#!/usr/bin/env python3


from dataclasses import dataclass
from typing import Dict

from .Project import Project
from .ProjectConstraints import ProjectConstraints
from .TerrainFollowingPile import TerrainFollowingPile
from .TerrainFollowingTracker import TerrainFollowingTracker
from .testing_get_data_tf import load_project_from_excel, to_excel


@dataclass(frozen=True)
class LineSearchResult:
    best_intercept: float
    best_cost: float
    best_violations: list[dict[str, float]]


@dataclass(frozen=True)
class Line2DSearchResult:
    best_slope: float
    best_intercept: float
    best_cost: float
    best_violations: list[dict[str, float]]


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


def _apply_line_to_tracker(
    tracker: TerrainFollowingTracker, slope: float, y_intercept: float
) -> None:
    """
    Loops through tracker and sets the height to fit the line

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker containing the piles to be adjusted
    slope : float
        Gradient of the line (m)
    y_intercept : float
        Y-intercept of the line (b)
    """
    for pile in tracker.piles:
        pile.height = _interpolate_coords(pile, slope, y_intercept)


def _slope_candidates(
    baseline_slope: float,
    *,
    max_abs_slope: float,
    tolerance: float = 0.05,  # +/- 5% around baseline
    steps: int = 11,
) -> list[float]:
    """
    Generate candidate slopes around a baseline slope, clipped to an absolute limit.

    Used by the 2D optimiser to search a small band of slopes around an initial estimate
    without exceeding the projects maximum incline

    The returned list:
      - is sorted ascending,
      - has unique values,
      - always includes the clipped baseline slope.

    Parameters
    ----------
    baseline_slope : float
        The starting slope estimate around which to search.
    max_abs_slope : float
        Absolute maximum slope magnitude allowed (e.g. project max incline).
        Candidate slopes will be clipped to [-max_abs_slope, +max_abs_slope].
    tolerance : float, default=0.05
        Relative band half-width around the baseline (e.g. 0.05 = ±5%).
        If the baseline is 0.0, the band is taken as tolerance * max_abs_slope.
    steps : int, default=11
        Number of evenly spaced candidate slopes to generate across the band.
        If steps < 2 or the band collapses to a single point, only the baseline is returned.

    Returns
    -------
    list[float]
        Sorted unique list of candidate slopes to evaluate.
    """
    max_abs_slope = abs(max_abs_slope)
    if max_abs_slope == 0:
        return [0.0]

    # Clip baseline into allowable range
    base = max(-max_abs_slope, min(max_abs_slope, baseline_slope))

    # If baseline is 0, use a small absolute band so we still explore
    band = abs(base) * tolerance
    if band == 0:
        band = max_abs_slope * tolerance

    lo = max(-max_abs_slope, base - band)
    hi = min(max_abs_slope, base + band)

    if steps < 2 or lo == hi:
        return [base]

    candidates = [lo + (hi - lo) * i / (steps - 1) for i in range(steps)]

    # Ensure baseline is included exactly
    if base not in candidates:
        candidates.append(base)

    # sort + unique (stable)
    candidates = sorted(set(candidates))
    return candidates


def _endpoints_within_window(
    tracker: TerrainFollowingTracker,
    window: list[dict[str, float]],
) -> bool:
    """
    Check whether the first and last piles of a tracker lie within their grading windows.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker containing an ordered list of piles.
    window : list[dict[str, float]]
        Grading window data for the tracker, containing per-pile
        'pile_in_tracker', 'grading_window_min', and 'grading_window_max'.

    Returns
    -------
    bool
        True if both first and last piles are within their respective windows,
        otherwise False.
    """
    limits = _window_by_pile_in_tracker(window)

    first = tracker.get_first()
    last = tracker.get_last()

    fmin, fmax = limits[first.pile_in_tracker]
    lmin, lmax = limits[last.pile_in_tracker]

    return (fmin <= first.height <= fmax) and (lmin <= last.height <= lmax)


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


def _interpolate_coords(
    pile: TerrainFollowingPile, slope: float, y_intercept: float
) -> float:
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


def find_optimal_line_intercept(
    *,
    tracker: TerrainFollowingTracker,
    window_fn,  # callable that returns a window for *current* tracker state
    slope: float,
    initial_intercept: float,
    span: float,
    coarse_steps: int = 121,
    fine_steps: int = 121,
    fine_span_fraction: float = 0.1,
) -> LineSearchResult:
    """
    Optimise a grading line intercept ensuring the first and last tracker stay within the grading
    window.

    Candidate intercepts are evaluated by:
      1) Apply candidate line (slope, intercept) to pile heights.
      2) Compute a fresh grading window via `window_fn()`.
      3) Reject candidate if the first or last pile lies outside its window.
      4) Otherwise compute violations and total grading cost.

    If no feasible candidate is found in the search range, the function returns
    a result with `best_cost = inf` and an empty violations list.

    The tracker pile heights are restored to their original values before returning.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose piles are evaluated.
    window_fn : Callable[[], list[dict[str, float]]]
        Function that returns the current grading window for the tracker.
        Must read from `tracker` and `project` state as needed.
    slope : float
        Fixed slope of the grading line.
    initial_intercept : float
        Starting y-intercept about which the search is centred.
    span : float
        Half-width of the intercept search interval.
    coarse_steps : int, default=121
        Number of samples in the coarse grid.
    fine_steps : int, default=121
        Number of samples in the fine grid.
    fine_span_fraction : float, default=0.1
        Fine-search span is (span * fine_span_fraction) around the best coarse intercept.

    Returns
    -------
    LineSearchResult
        best_intercept : float
            Best feasible intercept found (or initial_intercept if none feasible).
        best_cost : float
            Best feasible cost found, or float("inf") if none feasible.
        best_violations : list[dict[str, float]]
            Violations list for the best feasible intercept (empty if infeasible).
    """
    if not tracker.piles:
        return LineSearchResult(initial_intercept, 0.0, [])

    original_heights = [p.height for p in tracker.piles]

    def eval_intercept(b: float) -> tuple[float, list[dict[str, float]], bool]:
        _apply_line_to_tracker(tracker, slope, b)
        w = window_fn()  # fresh
        feasible = _endpoints_within_window(tracker, w)
        if not feasible:
            return float("inf"), [], False
        violations = check_within_window(w, tracker)
        return _total_grading_cost(violations), violations, True

    best_b = initial_intercept
    best_cost = float("inf")
    best_violations: list[dict[str, float]] = []

    # coarse
    for k in range(coarse_steps):
        b = initial_intercept - span + (2.0 * span) * (k / (coarse_steps - 1))
        cost, violations, ok = eval_intercept(b)
        if ok and cost < best_cost:
            best_cost, best_b, best_violations = cost, b, violations

    # fine around best coarse
    if best_cost < float("inf"):
        fine_span = span * fine_span_fraction
        for k in range(fine_steps):
            b = best_b - fine_span + (2.0 * fine_span) * (k / (fine_steps - 1))
            cost, violations, ok = eval_intercept(b)
            if ok and cost < best_cost:
                best_cost, best_b, best_violations = cost, b, violations

    # restore heights
    for pile, h in zip(tracker.piles, original_heights):
        pile.height = h

    # If nothing feasible was found, fall back to initial intercept
    if best_cost == float("inf"):
        return LineSearchResult(initial_intercept, float("inf"), [])

    return LineSearchResult(best_b, best_cost, best_violations)


def find_optimal_line_slope_and_intercept_2d(
    *,
    tracker: TerrainFollowingTracker,
    project: Project,
    baseline_slope: float,
    baseline_intercept: float,
    intercept_span: float,
    slope_tolerance: float = 0.05,
    slope_steps: int = 11,
) -> Line2DSearchResult:
    """
    Optimise both slope and intercept of a grading line (2D search) under constraints.

    This function performs a bounded 2D optimisation:
      - Enumerate candidate slopes in a small band around `baseline_slope`,
        clipped to +/- project.constraints.max_incline.
      - For each candidate slope, run a 1D intercept optimisation using
        `find_optimal_line_intercept_feasible`, which:
          * recomputes the grading window per candidate via grading_window(project, tracker)
          * enforces that the first and last piles are within their grading windows

    The objective is to minimise the total grading cost:

        sum(abs(below_by) + above_by) over violating piles

    The tracker pile heights are restored to their original values before returning.
    The caller is responsible for applying the chosen line.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose piles are evaluated.
    project : Project
        Project providing grading constraints and window rules.
    baseline_slope : float
        Initial slope estimate used to centre the slope search.
    baseline_intercept : float
        Initial intercept estimate used to centre the intercept search for each slope.
    intercept_span : float
        Half-width of the intercept search interval for each slope.
    slope_tolerance : float, default=0.05
        Relative band half-width around the baseline slope (e.g. 0.05 = ±5%).
    slope_steps : int, default=11
        Number of candidate slopes to evaluate.

    Returns
    -------
    Line2DSearchResult
        best_slope : float
            Slope giving the minimum feasible cost found.
        best_intercept : float
            Intercept giving the minimum feasible cost found for best_slope.
        best_cost : float
            Minimum feasible grading cost found. May be inf if nothing feasible.
        best_violations : list[dict[str, float]]
            Violations list corresponding to the best feasible candidate.
    """
    if not tracker.piles:
        return Line2DSearchResult(baseline_slope, baseline_intercept, 0.0, [])

    original_heights = [p.height for p in tracker.piles]

    def window_fn():
        return grading_window(project, tracker)

    max_abs_slope = abs(project.constraints.max_incline)

    # Baseline Eval
    # Apply baseline line (temporarily)
    _apply_line_to_tracker(tracker, baseline_slope, baseline_intercept)
    w0 = window_fn()
    baseline_feasible = _endpoints_within_window(tracker, w0)
    v0 = check_within_window(w0, tracker) if baseline_feasible else []
    c0 = _total_grading_cost(v0) if baseline_feasible else float("inf")

    best = Line2DSearchResult(
        best_slope=baseline_slope,
        best_intercept=baseline_intercept,
        best_cost=c0,
        best_violations=v0,
    )

    # restore before searching
    for pile, h in zip(tracker.piles, original_heights):
        pile.height = h

    # Looping through slopes
    for s in _slope_candidates(
        baseline_slope,
        max_abs_slope=max_abs_slope,
        tolerance=slope_tolerance,
        steps=slope_steps,
    ):
        # restore heights for this slope
        for pile, h in zip(tracker.piles, original_heights):
            pile.height = h

        # 1D intercept search
        res1d = find_optimal_line_intercept(
            tracker=tracker,
            window_fn=window_fn,
            slope=s,
            initial_intercept=baseline_intercept,
            span=intercept_span,
            coarse_steps=121,
            fine_steps=121,
            fine_span_fraction=0.1,
        )

        if res1d.best_cost < best.best_cost:
            best = Line2DSearchResult(
                best_slope=s,
                best_intercept=res1d.best_intercept,
                best_cost=res1d.best_cost,
                best_violations=res1d.best_violations,
            )

    # restore heights
    for pile, h in zip(tracker.piles, original_heights):
        pile.height = h

    return best


def sliding_line(
    tracker: TerrainFollowingTracker,
    project: Project,
    slope: float,
    y_intercept: float,
    *,
    intercept_span: float,
    slope_tolerance: float = 0.05,
    slope_steps: int = 11,
) -> tuple[float, float]:
    """
    Optimise the grading line (slope + intercept) and apply it to the tracker.

    Searches for the line that minimises grading cost while enforcing:
      - |slope| <= project.constraints.max_incline
      - first and last piles remain within their grading windows

    After optimisation, this function applies the chosen line by updating
    each pile's `pile.height` to lie on the line.

    Parameters
    ----------
    tracker : TerrainFollowingTracker
        Tracker whose piles will be adjusted to the optimised line.
    project : Project
        Project containing grading constraints and window rules.
    slope : float
        Baseline slope used to initialise the 2D search.
    y_intercept : float
        Baseline intercept used to initialise the 2D search.
    intercept_span : float
        Half-width of the intercept search interval.
    slope_rel_tol : float, default=0.05
        Relative slope search band half-width (±5% by default).
    slope_steps : int, default=11
        Number of candidate slopes to evaluate.

    Returns
    -------
    tuple[float, float]
        (best_slope, best_intercept) chosen by the optimiser and applied to the tracker.
    """
    res = find_optimal_line_slope_and_intercept_2d(
        tracker=tracker,
        project=project,
        baseline_slope=slope,
        baseline_intercept=y_intercept,
        intercept_span=intercept_span,
        slope_tolerance=slope_tolerance,
        slope_steps=slope_steps,
    )

    # Apply chosen line
    _apply_line_to_tracker(tracker, res.best_slope, res.best_intercept)
    return res.best_slope, res.best_intercept


def grading_window(
    project: Project, tracker: TerrainFollowingTracker
) -> list[dict[str, float]]:
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


import math


def _wrap_angle_deg(a: float) -> float:
    """Wrap angle to (-180, 180]."""
    a = (a + 180.0) % 360.0 - 180.0
    return a


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest signed difference a-b in degrees."""
    return _wrap_angle_deg(a - b)


def _break_deg_for_height(pile, tracker, h: float) -> float:
    h0 = pile.height
    pile.height = h
    tracker.create_segments()  # ALWAYS
    in_id = pile.get_incoming_segment_id()
    out_id = pile.get_outgoing_segment_id(tracker)
    if in_id == -1 or out_id == -1:
        b = 0.0
    else:
        seg_in = tracker.get_segment_by_id(in_id)
        seg_out = tracker.get_segment_by_id(out_id)
        b = abs(_angle_diff_deg(seg_out.segment_angle(), seg_in.segment_angle()))
    pile.height = h0
    tracker.create_segments()  # restore consistency
    return b


def _project_pile_to_break_limit(
    pile, tracker, project, break_lim_deg: float, *, bisect_iters: int = 60
) -> bool:
    h0 = pile.height
    tracker.create_segments()
    if pile.degree_break(tracker) <= break_lim_deg:
        return False

    hmin = pile.true_min_height(project)
    hmax = pile.true_max_height(project)

    def ok(h: float) -> bool:
        return _break_deg_for_height(pile, tracker, h) <= break_lim_deg

    # If even endpoints can’t satisfy, bail (constraint infeasible under window)
    if (
        min(
            _break_deg_for_height(pile, tracker, hmin),
            _break_deg_for_height(pile, tracker, hmax),
        )
        > break_lim_deg
    ):
        return False

    # Find nearest feasible point to h0 by searching both sides within window
    # Left boundary in [hmin, h0] if feasible exists there
    left = None
    if ok(hmin):
        lo, hi = hmin, min(h0, hmax)
        if not ok(hi):  # boundary exists
            for _ in range(bisect_iters):
                mid = 0.5 * (lo + hi)
                if ok(mid):
                    lo = mid
                else:
                    hi = mid
            left = lo
        else:
            left = hi  # h0 already feasible (shouldn’t happen due to earlier check)

    # Right boundary in [h0, hmax] if feasible exists there
    right = None
    if ok(hmax):
        lo, hi = max(h0, hmin), hmax
        if not ok(lo):
            for _ in range(bisect_iters):
                mid = 0.5 * (lo + hi)
                if ok(mid):
                    hi = mid
                else:
                    lo = mid
            right = hi

    candidates = [x for x in (left, right) if x is not None]
    if not candidates:
        return False

    best = min(candidates, key=lambda x: abs(x - h0))
    if abs(best - h0) < 1e-10:
        return False

    pile.height = best
    tracker.create_segments()
    return True


def target_height_line(
    tracker: TerrainFollowingTracker, project: Project
) -> tuple[float, float]:
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
    slope = max(
        -max_incline, min(max_incline, slope)
    )  # ensure slope is below max slope
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


def grading(
    tracker: TerrainFollowingTracker, violating_piles: list[dict[str, float]]
) -> None:
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
        max_vertical_change = (
            segment.length() * project.max_conservative_segment_slope_change
        )
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
    *,
    max_iters: int = 150,
    relaxation: float = 0.8,  # Factor to prevent oscillation
) -> list[float]:
    """
    Robust Iterative Solver for Articulated Torque Tubes.
    Ensures local degree breaks and wing cumulative limits are satisfied
    within physical grading windows.
    """
    break_lim = float(project.constraints.max_segment_deflection_deg)
    cum_lim = float(project.constraints.max_cumulative_deflection_deg)

    def get_wing_data():
        """Returns breaks per pile and cumulative sums per wing."""
        tracker.create_segments()
        centre_id = tracker.get_centre_pile().pile_in_tracker
        breaks = {p.pile_in_tracker: p.degree_break(tracker) for p in tracker.piles}

        # Determine wing membership (logic based on pile_in_tracker index)
        # Wing 1 (South/Low IDs) | Center Pile | Wing 2 (North/High IDs)
        s_wing = [breaks[i] for i in range(2, centre_id)]
        n_wing = [breaks[i] for i in range(centre_id + 1, tracker.pole_count)]
        # Center break is often split or ignored for cumulative;
        # here we count it half toward both to be conservative
        mid_break = breaks[centre_id]

        return breaks, sum(s_wing) + mid_break * 0.5, sum(n_wing) + mid_break * 0.5

    # 2. Iterative Solver
    for _ in range(max_iters):
        tracker.create_segments()

        # A) LOCAL BREAK CORRECTION (Forward and Backward Sweeps)
        # Sweeping propagates the 'error' out of the system
        for pid_range in [
            range(2, tracker.pole_count),
            range(tracker.pole_count - 1, 1, -1),
        ]:
            for pid in pid_range:
                pile = tracker.get_pile_in_tracker(pid)
                b = pile.degree_break(tracker)

                if b > break_lim:
                    # Calculate vertical shift needed to reduce the break
                    # Using the geometric relationship: dh = (L1*L2)/(L1+L2) * delta_theta_rad
                    in_seg = tracker.get_segment_by_id(pile.get_incoming_segment_id())
                    out_seg = tracker.get_segment_by_id(
                        pile.get_outgoing_segment_id(tracker)
                    )

                    l1, l2 = in_seg.length(), out_seg.length()
                    # Determine direction: if out_slope > in_slope, joint is 'valley', move pile UP
                    diff_slope = out_seg.slope() - in_seg.slope()

                    # Target a break slightly below the limit to ensure convergence
                    target_b = break_lim * 0.95
                    angle_to_fix = math.radians(b - target_b)

                    dy = (
                        (diff_slope / abs(diff_slope if diff_slope != 0 else 1))
                        * ((l1 * l2) / (l1 + l2))
                        * angle_to_fix
                        * relaxation
                    )

                    pile.height += dy

                    # CRITICAL: Always clamp to grading window inside the loop
                    p_min = pile.true_min_height(project)
                    p_max = pile.true_max_height(project)
                    pile.height = max(p_min, min(p_max, pile.height))

        # B) WING CUMULATIVE CORRECTION (Proportional Compression)
        breaks, s_cum, n_cum = get_wing_data()

        if s_cum > cum_lim or n_cum > cum_lim:
            centre_id = tracker.get_centre_pile().pile_in_tracker
            # If a wing is over, we gently 'straighten' all piles in that wing
            # toward the average slope line of that wing
            for pid in range(2, tracker.pole_count):
                pile = tracker.get_pile_in_tracker(pid)
                is_north = pid > centre_id

                if (is_north and n_cum > cum_lim) or (not is_north and s_cum > cum_lim):
                    first = tracker.get_first()
                    last = tracker.get_last()
                    x0, h0 = first.northing, first.height
                    x1, h1 = last.northing, last.height
                    dx = x1 - x0
                    if abs(dx) > 1e-12:
                        t = (pile.northing - x0) / dx
                        h_chord = h0 + t * (h1 - h0)
                        pile.height += (h_chord - pile.height) * 0.08  # small

                    # Clamp again
                    pile.height = max(
                        pile.true_min_height(project),
                        min(pile.true_max_height(project), pile.height),
                    )

        # C) CONVERGENCE CHECK
        tracker.create_segments()
        final_breaks, final_s, final_n = get_wing_data()
        max_b = max(final_breaks.values())

        if (
            max_b <= break_lim + 1e-5
            and final_s <= cum_lim + 1e-5
            and final_n <= cum_lim + 1e-5
        ):
            break

    return [p.height for p in tracker.piles]


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
        piles_outside0 = check_within_window(window, tracker)
        if piles_outside0:
            window_half = (
                piles_outside0[0]["grading_window_max"]
                - piles_outside0[0]["grading_window_min"]
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
            updated_piles_outside1, heights_after1 = alteration1(
                tracker, project, piles_outside1
            )
            alteration3(project, tracker)
            heights_after_correction = slope_correction(tracker, project)
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
    excel_path = "PCL/XTR.xlsx"  # change if needed
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
        north_to_south = (
            first.northing > last.northing
        )  # True means pile 1 is more north

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
