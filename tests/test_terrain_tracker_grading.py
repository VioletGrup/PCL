#!/usr/bin/env python3
"""
Unit tests for terrain tracker grading logic.
Tests core grading algorithms and helper functions specific to terrain following.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from terrainTrackerGrading import (
    _y_intercept,
    _interpolate_coords,
    _window_by_pile_in_tracker,
    _total_grading_cost,
    target_height_line,
    grading_window,
    grading,
    check_within_window,
    shift_piles,
    slope_correction,
    slide_all_piles,
    sliding_line,
    main,
)
from Project import Project
from ProjectConstraints import ProjectConstraints


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_constraints():
    """Standard constraints for most tests."""
    return ProjectConstraints(
        min_reveal_height=1.0,
        max_reveal_height=2.0,
        pile_install_tolerance=0.0,
        max_incline=0.1,
        target_height_percentage=0.5,
        max_angle_rotation=0.0,
        max_segment_deflection_deg=1.0,
        max_cumulative_deflection_deg=5.0,
        edge_overhang=0.0,
    )


@pytest.fixture
def project(base_constraints):
    """Standard project for terrain following tests."""
    return Project(
        name="Test", project_type="terrain_following", constraints=base_constraints
    )


@pytest.fixture
def three_pile_tracker():
    """Tracker with 3 piles, 10m spacing, flat terrain at elevation 10."""
    t = TerrainFollowingTracker(tracker_id=1)
    for i in range(3):
        p = TerrainFollowingPile(
            northing=float(i * 10),
            easting=0.0,
            initial_elevation=10.0,
            pile_in_tracker=i + 1,
            pile_id=float(i + 1),
            flooding_allowance=0.0,
        )
        t.add_pile(p)
    return t


@pytest.fixture
def five_pile_tracker():
    """Tracker with 5 piles, 10m spacing, flat terrain at elevation 10."""
    t = TerrainFollowingTracker(tracker_id=1)
    for i in range(5):
        p = TerrainFollowingPile(
            northing=float(i * 10),
            easting=0.0,
            initial_elevation=10.0,
            pile_in_tracker=i + 1,
            pile_id=float(i + 1),
            flooding_allowance=0.0,
        )
        t.add_pile(p)
    return t


# =============================================================================
# TEST HELPER FUNCTIONS
# =============================================================================


class TestHelperFunctions:
    """Test mathematical helper functions."""

    def test_y_intercept_positive_slope(self):
        """Test y-intercept calculation with positive slope."""
        # Line: y = 0.5x + c passing through (10, 20)
        # 20 = 0.5 * 10 + c => c = 15
        assert _y_intercept(0.5, 10.0, 20.0) == 15.0

    def test_y_intercept_negative_slope(self):
        """Test y-intercept calculation with negative slope."""
        # Line: y = -0.2x + c passing through (10, 5)
        # 5 = -0.2 * 10 + c => c = 7
        assert _y_intercept(-0.2, 10.0, 5.0) == 7.0

    def test_y_intercept_zero_slope(self):
        """Test y-intercept with horizontal line."""
        # Horizontal line y = 5 passing through any x
        assert _y_intercept(0.0, 100.0, 5.0) == 5.0

    def test_interpolate_coords_positive_slope(self):
        """Test coordinate interpolation with positive slope."""
        pile = MagicMock(spec=TerrainFollowingPile)
        pile.northing = 100.0
        # y = 0.1 * 100 + 5 = 15
        assert _interpolate_coords(pile, 0.1, 5.0) == 15.0

    def test_interpolate_coords_at_origin(self):
        """Test interpolation at northing = 0."""
        pile = MagicMock(spec=TerrainFollowingPile)
        pile.northing = 0.0
        # y = 0.1 * 0 + 5 = 5
        assert _interpolate_coords(pile, 0.1, 5.0) == 5.0

    def test_interpolate_coords_negative_slope(self):
        """Test interpolation with negative slope."""
        pile = MagicMock(spec=TerrainFollowingPile)
        pile.northing = 50.0
        # y = -0.1 * 50 + 10 = 5
        assert _interpolate_coords(pile, -0.1, 10.0) == 5.0

    def test_window_by_pile_in_tracker_single_entry(self):
        """Test dictionary conversion with single entry."""
        window_data = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 10.0,
                "grading_window_max": 20.0,
            }
        ]
        result = _window_by_pile_in_tracker(window_data)
        assert result[1] == (10.0, 20.0)

    def test_window_by_pile_in_tracker_multiple_entries(self):
        """Test dictionary conversion with multiple entries."""
        window_data = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 10.0,
                "grading_window_max": 20.0,
            },
            {
                "pile_in_tracker": 2,
                "grading_window_min": 12.0,
                "grading_window_max": 22.0,
            },
            {
                "pile_in_tracker": 3,
                "grading_window_min": 15.0,
                "grading_window_max": 25.0,
            },
        ]
        result = _window_by_pile_in_tracker(window_data)
        assert result[1] == (10.0, 20.0)
        assert result[2] == (12.0, 22.0)
        assert result[3] == (15.0, 25.0)

    def test_window_by_pile_in_tracker_non_sequential_ids(self):
        """Test conversion with non-sequential pile IDs."""
        window_data = [
            {
                "pile_in_tracker": 5,
                "grading_window_min": 10.0,
                "grading_window_max": 20.0,
            },
            {
                "pile_in_tracker": 10,
                "grading_window_min": 15.0,
                "grading_window_max": 25.0,
            },
        ]
        result = _window_by_pile_in_tracker(window_data)
        assert 5 in result
        assert 10 in result
        assert result[5] == (10.0, 20.0)


class TestTotalGradingCost:
    """Test the grading cost calculation."""

    def test_no_violations_returns_zero(self):
        """Empty violations list should return zero cost."""
        assert _total_grading_cost([]) == 0.0

    def test_single_below_violation(self):
        """Single pile below window calculates correct cost."""
        violations = [{"below_by": -2.0, "above_by": 0.0}]
        assert _total_grading_cost(violations) == 2.0

    def test_single_above_violation(self):
        """Single pile above window calculates correct cost."""
        violations = [{"below_by": 0.0, "above_by": 3.0}]
        assert _total_grading_cost(violations) == 3.0

    def test_multiple_violations(self):
        """Multiple violations sum correctly."""
        violations = [
            {"below_by": -1.5, "above_by": 0.0},
            {"below_by": 0.0, "above_by": 2.0},
            {"below_by": -0.5, "above_by": 0.0},
        ]
        # Cost = 1.5 + 2.0 + 0.5 = 4.0
        assert _total_grading_cost(violations) == 4.0

    def test_mixed_violation_same_pile(self):
        """Both below_by and above_by in same dict (edge case)."""
        # This shouldn't happen in practice, but test handles it
        violations = [{"below_by": -1.0, "above_by": 2.0}]
        assert _total_grading_cost(violations) == 3.0


# =============================================================================
# TEST GRADING WINDOW
# =============================================================================


class TestGradingWindow:
    """Test grading window calculation."""

    def test_window_structure(self, project, three_pile_tracker):
        """Test that window returns correct structure."""
        window = grading_window(project, three_pile_tracker)
        assert len(window) == 3
        for entry in window:
            assert "pile_id" in entry
            assert "pile_in_tracker" in entry
            assert "grading_window_min" in entry
            assert "grading_window_max" in entry
            assert "ground_elevation" in entry

    def test_window_values_flat_terrain(self, project, three_pile_tracker):
        """Test window values for flat terrain."""
        window = grading_window(project, three_pile_tracker)
        # Flat terrain at 10m, min_reveal=1, max_reveal=2
        # Window should be [11, 12] for all piles
        for entry in window:
            assert entry["ground_elevation"] == 10.0
            assert entry["grading_window_min"] == pytest.approx(11.0)
            assert entry["grading_window_max"] == pytest.approx(12.0)

    def test_window_values_sloped_terrain(self, project):
        """Test window values for sloped terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        elevations = [10.0, 11.0, 12.0]
        for i, elev in enumerate(elevations):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=elev,
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        window = grading_window(project, tracker)
        for i, entry in enumerate(window):
            expected_ground = 10.0 + i
            assert entry["ground_elevation"] == expected_ground
            assert entry["grading_window_min"] == pytest.approx(expected_ground + 1.0)
            assert entry["grading_window_max"] == pytest.approx(expected_ground + 2.0)


# =============================================================================
# TEST TARGET HEIGHT LINE
# =============================================================================


class TestTargetHeightLine:
    """Test target height line calculation with terrain constraints."""

    def test_flat_terrain_zero_slope(self, project, three_pile_tracker):
        """Flat terrain should produce zero slope."""
        target_height_line(three_pile_tracker, project)

        # All piles should have same height
        heights = [p.height for p in three_pile_tracker.piles]
        assert all(h == pytest.approx(heights[0]) for h in heights)

    def test_sets_pile_heights_in_place(self, project, three_pile_tracker):
        """Function should modify pile.height in place."""
        initial_heights = [p.height for p in three_pile_tracker.piles]
        target_height_line(three_pile_tracker, project)
        final_heights = [p.height for p in three_pile_tracker.piles]

        # Heights should be modified
        for init, final in zip(initial_heights, final_heights):
            assert final is not None

    def test_follows_ground_slope_within_max_incline(self, project):
        """Target line follows ground slope when within max_incline."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Create slope of 0.05 (within max_incline of 0.1)
        # Rise = 1m over 20m = 0.05 slope
        for i in range(3):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=10.0 + (i * 0.5),
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        target_height_line(tracker, project)

        # Heights should follow the slope
        h0 = tracker.piles[0].height
        h1 = tracker.piles[1].height
        h2 = tracker.piles[2].height

        slope = (h2 - h0) / 20.0
        assert slope == pytest.approx(0.05, abs=0.01)

    def test_clamps_to_max_incline_positive(self, project):
        """Slope clamped to max_incline for steep upward terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # 10m rise over 20m = 0.5 slope, max_incline is 0.1
        for i, elev in enumerate([10.0, 15.0, 20.0]):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=elev,
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        target_height_line(tracker, project)

        h0 = tracker.piles[0].height
        h2 = tracker.piles[2].height
        actual_slope = (h2 - h0) / 20.0

        assert actual_slope == pytest.approx(0.1, abs=0.001)

    def test_clamps_to_max_incline_negative(self, project):
        """Slope clamped to -max_incline for steep downward terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # -10m rise over 20m = -0.5 slope, max_incline is 0.1
        for i, elev in enumerate([20.0, 15.0, 10.0]):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=elev,
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        target_height_line(tracker, project)

        h0 = tracker.piles[0].height
        h2 = tracker.piles[2].height
        actual_slope = (h2 - h0) / 20.0

        assert actual_slope == pytest.approx(-0.1, abs=0.001)


# =============================================================================
# TEST CHECK WITHIN WINDOW
# =============================================================================


class TestCheckWithinWindow:
    """Test window boundary checking."""

    def test_pile_exactly_at_min_no_violation(self):
        """Pile exactly at min boundary is not a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 11.0
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 0

    def test_pile_exactly_at_max_no_violation(self):
        """Pile exactly at max boundary is not a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 12.0
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 0

    def test_pile_within_window_no_violation(self):
        """Pile in middle of window is not a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 11.5
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 0

    def test_pile_below_window_violation(self):
        """Pile below window returns correct violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 10.0  # 1.0 below min
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 1
        assert violations[0]["pile_in_tracker"] == 1
        assert violations[0]["below_by"] == pytest.approx(-1.0)
        assert violations[0]["above_by"] == 0.0

    def test_pile_above_window_violation(self):
        """Pile above window returns correct violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 14.0  # 2.0 above max
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 1
        assert violations[0]["pile_in_tracker"] == 1
        assert violations[0]["above_by"] == pytest.approx(2.0)
        assert violations[0]["below_by"] == 0.0

    def test_missing_pile_in_window_raises(self):
        """Pile not in window raises ValueError."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Create pile with pile_in_tracker=2, but window only has 1
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 2, 1, 0.0)
        p.height = 11.0
        tracker.add_pile(p)

        with pytest.raises(ValueError, match="not found in grading window"):
            check_within_window(window, tracker)


# =============================================================================
# TEST SHIFT PILES
# =============================================================================


class TestShiftPiles:
    """Test pile shifting toward window bounds."""

    @pytest.fixture
    def project_with_segments(self, base_constraints):
        """Project configured for shift_piles testing."""
        base_constraints.max_segment_deflection_deg = 3.433
        base_constraints.max_cumulative_deflection_deg = 20.0
        return Project(
            name="ShiftTest", project_type="terrain_following", constraints=base_constraints
        )

    def test_no_change_for_first_pile(self, project_with_segments):
        """First pile (anchor) should not be shifted."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 15.0  # Above window
            tracker.add_pile(p)
        tracker.create_segments()

        violating_piles = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": 0.0,
                "above_by": 3.0,
            }
        ]

        original_height = tracker.get_pile_in_tracker(1).height
        shift_piles(tracker, project_with_segments, violating_piles)

        # First pile has segment_id = -1, should be skipped
        assert tracker.get_pile_in_tracker(1).height == original_height

    def test_pile_moved_toward_max_when_above(self, project_with_segments):
        """Pile above window moves down toward max."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 12.5  # Slightly above window max of 12
            tracker.add_pile(p)
        tracker.create_segments()

        violating_piles = [
            {
                "pile_in_tracker": 2,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": 0.0,
                "above_by": 0.5,
            }
        ]

        shift_piles(tracker, project_with_segments, violating_piles)

        # Should move to window max (distance was within limit)
        assert tracker.get_pile_in_tracker(2).height == pytest.approx(12.0)

    def test_pile_moved_toward_min_when_below(self, project_with_segments):
        """Pile below window moves up toward min."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 10.5  # Below window min of 11
            tracker.add_pile(p)
        tracker.create_segments()

        violating_piles = [
            {
                "pile_in_tracker": 2,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": -0.5,
                "above_by": 0.0,
            }
        ]

        shift_piles(tracker, project_with_segments, violating_piles)

        # Should move to window min
        assert tracker.get_pile_in_tracker(2).height == pytest.approx(11.0)

    def test_movement_capped_by_conservative_limit(self, project_with_segments):
        """Large violations capped by max_conservative_segment_slope_change."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 15.0  # 3.0 above window max
            tracker.add_pile(p)
        tracker.create_segments()

        violating_piles = [
            {
                "pile_in_tracker": 2,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": 0.0,
                "above_by": 3.0,
            }
        ]

        shift_piles(tracker, project_with_segments, violating_piles)

        # Movement should be capped
        limit = (
            10.0 * project_with_segments.max_conservative_segment_slope_change
        )
        expected_height = 15.0 - limit
        assert tracker.get_pile_in_tracker(2).height == pytest.approx(
            expected_height, abs=0.01
        )


# =============================================================================
# TEST SLOPE CORRECTION
# =============================================================================


class TestSlopeCorrection:
    """Test slope delta correction."""

    def test_flat_line_no_correction(self, project, five_pile_tracker):
        """Flat pile heights should not be corrected."""
        for p in five_pile_tracker.piles:
            p.height = 11.5

        five_pile_tracker.create_segments()
        original_heights = [p.height for p in five_pile_tracker.piles]

        slope_correction(five_pile_tracker, project)

        # Heights should remain unchanged
        for i, p in enumerate(five_pile_tracker.piles):
            assert p.height == pytest.approx(original_heights[i])

    def test_sharp_upward_kink_corrected(self, base_constraints):
        """Sharp upward kink (high slope delta) should be reduced."""
        base_constraints.max_segment_deflection_deg = 1.0
        project = Project(
            name="KinkTest", project_type="terrain_following", constraints=base_constraints
        )

        tracker = TerrainFollowingTracker(tracker_id=1)
        # Create kink: flat, up, flat => steep incoming, zero outgoing
        heights = [10.0, 10.0, 12.0, 12.0]
        for i, h in enumerate(heights):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = h
            tracker.add_pile(p)
        tracker.create_segments()

        slope_correction(tracker, project)

        # The kink pile (pile 3) should be lowered to reduce slope delta
        # Exact value depends on iterations, just verify direction
        assert tracker.get_pile_in_tracker(3).height < 12.0

    def test_first_and_last_piles_unchanged(self, project, five_pile_tracker):
        """First and last piles should not be modified by slope correction."""
        for i, p in enumerate(five_pile_tracker.piles):
            p.height = 11.0 + i * 0.5  # Sloped heights

        five_pile_tracker.create_segments()
        first_height = five_pile_tracker.piles[0].height
        last_height = five_pile_tracker.piles[-1].height

        slope_correction(five_pile_tracker, project)

        assert five_pile_tracker.piles[0].height == first_height
        assert five_pile_tracker.piles[-1].height == last_height


# =============================================================================
# TEST SLIDE ALL PILES
# =============================================================================


class TestSlideAllPiles:
    """Test uniform vertical shift optimization."""

    def test_no_change_when_all_in_window(self, project, three_pile_tracker):
        """Piles already in window should remain in window after optimization."""
        for p in three_pile_tracker.piles:
            p.height = 11.5  # Middle of window [11, 12]

        slide_all_piles(project, three_pile_tracker)

        # Heights should still be within window [11, 12]
        for p in three_pile_tracker.piles:
            assert p.height >= 11.0 - 1e-6
            assert p.height <= 12.0 + 1e-6

    def test_shifts_toward_window_when_above(self, project, three_pile_tracker):
        """All piles above window should be shifted down."""
        for p in three_pile_tracker.piles:
            p.height = 15.0  # Above window [11, 12]

        slide_all_piles(project, three_pile_tracker)

        # All piles should be lower
        for p in three_pile_tracker.piles:
            assert p.height < 15.0

    def test_shifts_toward_window_when_below(self, project, three_pile_tracker):
        """All piles below window should be shifted up."""
        for p in three_pile_tracker.piles:
            p.height = 8.0  # Below window [11, 12]

        slide_all_piles(project, three_pile_tracker)

        # All piles should be higher
        for p in three_pile_tracker.piles:
            assert p.height > 8.0

    def test_uniform_shift_preserves_slope(self, project, three_pile_tracker):
        """Shift should be uniform (same delta for all piles)."""
        # Set initial heights with slope
        for i, p in enumerate(three_pile_tracker.piles):
            p.height = 15.0 + i * 0.5

        # Record initial slope
        h0_init = three_pile_tracker.piles[0].height
        h2_init = three_pile_tracker.piles[2].height
        initial_slope = (h2_init - h0_init) / 20.0

        slide_all_piles(project, three_pile_tracker)

        # Slope should be preserved
        h0_final = three_pile_tracker.piles[0].height
        h2_final = three_pile_tracker.piles[2].height
        final_slope = (h2_final - h0_final) / 20.0

        assert final_slope == pytest.approx(initial_slope, abs=0.001)


# =============================================================================
# TEST SLIDING LINE
# =============================================================================


class TestSlidingLine:
    """Test legacy sliding line helper."""

    def test_shifts_line_down_when_above_window(self):
        """Line should shift down when piles are above window."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 15.0
            tracker.add_pile(p)

        violating_piles = [
            {
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": 0.0,
                "above_by": 3.0,
            }
        ]

        sliding_line(tracker, violating_piles, 0.0, 15.0)

        # Heights should decrease
        for p in tracker.piles:
            assert p.height < 15.0

    def test_shifts_line_up_when_below_window(self):
        """Line should shift up when piles are below window."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 8.0
            tracker.add_pile(p)

        violating_piles = [
            {
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": -3.0,
                "above_by": 0.0,
            }
        ]

        sliding_line(tracker, violating_piles, 0.0, 8.0)

        # Heights should increase
        for p in tracker.piles:
            assert p.height > 8.0


# =============================================================================
# TEST GRADING
# =============================================================================


class TestGrading:
    """Test final ground elevation adjustment."""

    def test_grading_adjusts_elevation_for_below_violation(self):
        """Pile below window gets ground lowered."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 10.5
            tracker.add_pile(p)

        # Pile 2 is below window by 0.5
        violating_piles = [
            {
                "pile_in_tracker": 2,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": -0.5,
                "above_by": 0.0,
            }
        ]

        grading(tracker, violating_piles)

        # Ground elevation should be lowered by 0.5
        assert tracker.get_pile_in_tracker(2).current_elevation == pytest.approx(9.5)

    def test_grading_adjusts_elevation_for_above_violation(self):
        """Pile above window gets ground raised."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            p.height = 13.0
            tracker.add_pile(p)

        # Pile 2 is above window by 1.0
        violating_piles = [
            {
                "pile_in_tracker": 2,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
                "below_by": 0.0,
                "above_by": 1.0,
            }
        ]

        grading(tracker, violating_piles)

        # Ground elevation should be raised by 1.0
        assert tracker.get_pile_in_tracker(2).current_elevation == pytest.approx(11.0)

    def test_grading_skips_first_pile(self):
        """First pile (anchor) should not be graded."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            tracker.add_pile(p)

        violating_piles = [
            {
                "pile_in_tracker": 1,
                "below_by": -2.0,
                "above_by": 0.0,
            }
        ]

        grading(tracker, violating_piles)

        # First pile elevation unchanged
        assert tracker.get_pile_in_tracker(1).current_elevation == 10.0

    def test_grading_skips_last_pile(self):
        """Last pile (anchor) should not be graded."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, float(i + 1), 0.0
            )
            tracker.add_pile(p)

        violating_piles = [
            {
                "pile_in_tracker": 3,
                "below_by": 0.0,
                "above_by": 2.0,
            }
        ]

        grading(tracker, violating_piles)

        # Last pile elevation unchanged
        assert tracker.get_pile_in_tracker(3).current_elevation == 10.0


# =============================================================================
# TEST MAIN INTEGRATION
# =============================================================================


class TestMain:
    """Integration tests for full grading flow."""

    def test_main_runs_without_error(self, project, five_pile_tracker):
        """Main should execute cleanly on simple project."""
        project.add_tracker(five_pile_tracker)
        main(project)

        for p in five_pile_tracker.piles:
            assert p.final_elevation is not None
            assert p.total_height is not None

    def test_main_respects_reveal_constraints(self, project, five_pile_tracker):
        """Final reveal heights must be within constraints."""
        project.add_tracker(five_pile_tracker)
        main(project)

        for p in five_pile_tracker.piles:
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6

    def test_main_preserves_anchor_invariant(self, project, five_pile_tracker):
        """First and last piles should never be graded."""
        project.add_tracker(five_pile_tracker)
        main(project)

        first = five_pile_tracker.get_first()
        last = five_pile_tracker.get_last()

        assert abs(first.final_elevation - first.initial_elevation) < 1e-6
        assert abs(last.final_elevation - last.initial_elevation) < 1e-6

    def test_main_handles_sloped_terrain(self, project):
        """Main handles terrain with slope."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(5):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=10.0 + (i * 0.5),
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        project.add_tracker(tracker)
        main(project)

        # Just verify it runs and produces valid output
        for p in tracker.piles:
            assert p.total_height is not None
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6

    def test_main_handles_jagged_terrain(self, project):
        """Main smooths jagged terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        elevations = [10.0, 12.0, 10.0, 12.0, 10.0]
        for i, elev in enumerate(elevations):
            p = TerrainFollowingPile(
                northing=float(i * 10),
                easting=0.0,
                initial_elevation=elev,
                pile_in_tracker=i + 1,
                pile_id=float(i + 1),
                flooding_allowance=0.0,
            )
            tracker.add_pile(p)

        project.add_tracker(tracker)
        main(project)

        # Verify constraints are met
        for p in tracker.piles:
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6

    def test_main_handles_multiple_trackers(self, project):
        """Main processes multiple trackers in project."""
        for tid in range(1, 4):
            tracker = TerrainFollowingTracker(tracker_id=tid)
            for i in range(3):
                p = TerrainFollowingPile(
                    northing=float(i * 10),
                    easting=float(tid * 100),
                    initial_elevation=10.0,
                    pile_in_tracker=i + 1,
                    pile_id=float(tid * 100 + i + 1),
                    flooding_allowance=0.0,
                )
                tracker.add_pile(p)
            project.add_tracker(tracker)

        main(project)

        assert len(project.trackers) == 3
        for tracker in project.trackers:
            for p in tracker.piles:
                assert p.final_elevation is not None

class TestWarnings:
    """Tests for warning conditions."""

    def test_inverted_window_warning(self, project):
        """Test that inverted window (min > max) triggers UserWarning."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Pile with massive flooding allowance causing min > max
        p = TerrainFollowingPile(
            northing=0.0,
            easting=0.0,
            initial_elevation=10.0,
            pile_in_tracker=1,
            pile_id=1,
            flooding_allowance=5.0,  # Huge flooding allowance
        )
        tracker.add_pile(p)
        project.add_tracker(tracker)

        with pytest.warns(UserWarning, match="inverted grading window"):
            grading_window(project, tracker)
