#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Dict

from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints
from shading.northSouthShadingAnalysis import main as ns_main
from shading.NorthSouth import NorthSouth
from testing_compare import compare_results
from testing_get_data import load_project_from_excel, to_excel


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


def _apply_line_to_tracker(tracker: BaseTracker, slope: float, y_intercept: float) -> None:
    """
    Loops through tracker and sets the height to fit the line

    Parameters
    ----------
    tracker : BaseTracker
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
    tracker: BaseTracker,
    window: list[dict[str, float]],
) -> bool:
    """
    Check whether the first and last piles of a tracker lie within their grading windows.

    Parameters
    ----------
    tracker : BaseTracker
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
                "pile_in_tracker": pile.pile_in_tracker,
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
    # Single pile tracker
    if len(tracker.piles) == 1:
        pile = tracker.piles[0]
        target_height = pile.pile_at_target_height(project)
        pile.height = target_height
        return 0.0, target_height  # Zero slope, height is y-intercept

    # set the first and last pile in the tracker to the target heights
    first_target_height = tracker.get_first().pile_at_target_height(project)
    last_target_height = tracker.get_last().pile_at_target_height(project)
    # deterimine the equation of the line at target height
    slope = (last_target_height - first_target_height) / (
        tracker.get_last().northing - tracker.get_first().northing
    )

    # if the slope exceeds the maximum incline, set it to the maximum incline
    if abs(slope) > abs(project.constraints.max_incline):
        if slope > 0:
            slope = project.constraints.max_incline
        else:
            slope = -project.constraints.max_incline

    y_intercept = _y_intercept(
        slope,
        tracker.get_first().northing,
        first_target_height,
    )

    # set each pile to the target height based on the linear equation
    _apply_line_to_tracker(tracker, slope, y_intercept)
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


def find_optimal_line_intercept(
    *,
    tracker: BaseTracker,
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
    tracker : BaseTracker
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
    tracker: BaseTracker,
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
    tracker : BaseTracker
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
    tracker: BaseTracker,
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
    tracker : BaseTracker
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


def grading(tracker: BaseTracker, violating_piles: list[dict[str, float]]) -> None:
    """
    Apply grading to bring violating piles inside their grading windows.

    For each violating pile, this function computes the required vertical movement
    to bring the pile height to the nearest window boundary, and applies that movement
    to the pile's current ground elevation.

    Notes
    -----
    The movement applied is:

        movement = below_by + above_by

    where:
      - below_by is <= 0.0 (negative if pile is below window min)
      - above_by is >= 0.0 (positive if pile is above window max)

    Parameters
    ----------
    tracker : BaseTracker
        Tracker containing piles whose ground elevations will be updated.
    violating_piles : list[dict[str, float]]
        Output of `check_within_window`, containing per-pile below_by/above_by values.

    Returns
    -------
    None
        This function mutates pile current elevations in-place.
    """
    for pile in violating_piles:
        p = tracker.get_pile_in_tracker(pile["pile_in_tracker"])
        movement = pile["below_by"] + pile["above_by"]
        p.set_current_elevation(p.current_elevation + movement)


def main(project: Project) -> None:
    """
    Run grading optimisation for all trackers in a project.

    For each tracker:
      1) Build grading windows for all piles.
      2) Initialise the pile heights to the target-height line (respecting max incline).
      3) If any piles violate their windows, optimise the line (slope + intercept)
         to minimise grading cost while keeping the first and last piles within their windows.
      4) Recompute violations and apply grading if required.
      5) Finalise pile outputs (final elevation, total height, revealed height).

    Parameters
    ----------
    project : Project
        Project containing trackers and grading constraints.

    Returns
    -------
    None
        Mutates the piles within `project.trackers` in-place.
    """
    for tracker in project.trackers:
        if not tracker.piles:
            continue  # skip to the next tracker if the current one is empty

        # determine the grading window for the tracker
        window = grading_window(project, tracker)

        # set the tracker piles to the target height line
        slope, y_intercept = target_height_line(tracker, project)

        # if at least one of the piles is outside the window, slide the line up
        # or down to determine its optimal position
        piles_outside = check_within_window(window, tracker)

        if piles_outside:
            window_half = (
                piles_outside[0]["grading_window_max"] - piles_outside[0]["grading_window_min"]
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

            # Re-check after applying the optimal line (fresh window)
            window = grading_window(project, tracker)
            piles_outside = check_within_window(window, tracker)

        if piles_outside:
            grading(tracker, piles_outside)

        # Set the final ground elevations, reveal heights and total heights of all piles,
        # some will remain the same
        for pile in tracker.piles:
            pile.set_final_elevation(pile.current_elevation)
            pile.set_total_height(pile.height)
            pile.set_total_revealed()

        # for pile in tracker.piles:
        #     print(
        #         f"pile_id: {pile.pile_id}/{pile.pile_in_tracker}     initial_elevation:
        # {pile.initial_elevation}     final_elevation: {pile.final_elevation}
        # change: {pile.final_elevation - pile.initial_elevation}"
        #     )


if __name__ == "__main__":
    print("Initialising project...")
    constraints = ProjectConstraints(
        min_reveal_height=1.375,
        max_reveal_height=1.675,
        pile_install_tolerance=0.0,
        max_incline=0.15,
        target_height_percantage=0.5,
        max_angle_rotation=0.0,
        edge_overhang=0.0,
    )

    # Load project from Excel

    print("Loading data from Excel...")
    excel_path = "Test Piling Info.xlsx"  # change if needed
    sheet_name = "Piling information"  # change to your actual sheet name

    project = load_project_from_excel(
        excel_path=excel_path,
        sheet_name=sheet_name,
        project_name="Punchs_Creek",
        project_type="standard",
        constraints=constraints,
    )

    print("Start Grading...")
    main(project)
    to_excel(project)
    print("Results saved to final_pile_elevations_slide_twice.xlsx")
    # print("Comparing results to expected outcome...")
    # compare_results()
