#!/usr/bin/env python3
"""
Unit tests for flat tracker grading logic.
Tests core grading algorithms and helper functions.
"""

from __future__ import annotations

import pytest

from BasePile import BasePile
from BaseTracker import BaseTracker
from flatTrackerGrading import (
    _interpolate_coords,
    _window_by_pile_in_tracker,
    _y_intercept,
    check_within_window,
    grading,
    grading_window,
    sliding_line,
    target_height_line,
)
from Project import Project
from ProjectConstraints import ProjectConstraints


class TestHelperFunctions:
    """Test mathematical helper functions."""

    def test_y_intercept_positive_slope(self):
        """Test y-intercept calculation with positive slope."""
        slope = 0.5
        x = 10.0
        y = 20.0
        result = _y_intercept(slope, x, y)
        expected = 15.0
        assert abs(result - expected) < 1e-6

    def test_y_intercept_negative_slope(self):
        """Test y-intercept calculation with negative slope."""
        slope = -0.15
        x = 100.0
        y = 50.0
        result = _y_intercept(slope, x, y)
        expected = 65.0
        assert abs(result - expected) < 1e-6

    def test_y_intercept_zero_slope(self):
        """Test y-intercept with zero slope (horizontal line)."""
        slope = 0.0
        x = 50.0
        y = 100.0
        result = _y_intercept(slope, x, y)
        assert abs(result - 100.0) < 1e-6

    def test_interpolate_coords_basic(self):
        """Test coordinate interpolation."""
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        slope = 0.01
        y_intercept = 5.0
        result = _interpolate_coords(pile, slope, y_intercept)
        expected = 0.01 * 100.0 + 5.0
        assert abs(result - expected) < 1e-6

    def test_window_by_pile_in_tracker(self):
        """Test conversion of window list to dictionary."""
        window = [
            {"pile_in_tracker": 1, "grading_window_min": 10.0, "grading_window_max": 15.0},
            {"pile_in_tracker": 2, "grading_window_min": 11.0, "grading_window_max": 16.0},
        ]
        result = _window_by_pile_in_tracker(window)
        assert result[1] == (10.0, 15.0)
        assert result[2] == (11.0, 16.0)


class TestGradingWindow:
    """Test grading window calculations."""

    @pytest.fixture
    def project(self):
        """Create a test project with standard constraints."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    @pytest.fixture
    def tracker(self):
        """Create a test tracker with 3 piles."""
        tracker = BaseTracker(tracker_id=1)
        piles = [
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.01,
                pile_in_tracker=1,
                flooding_allowance=0.0,
            ),
            BasePile(
                northing=110.0,
                easting=50.0,
                initial_elevation=10.5,
                pile_id=1.02,
                pile_in_tracker=2,
                flooding_allowance=0.0,
            ),
            BasePile(
                northing=120.0,
                easting=50.0,
                initial_elevation=11.0,
                pile_id=1.03,
                pile_in_tracker=3,
                flooding_allowance=0.0,
            ),
        ]
        for pile in piles:
            tracker.add_pile(pile)
        return tracker

    def test_grading_window_structure(self, project, tracker):
        """Test that grading window returns correct structure."""
        window = grading_window(project, tracker)
        assert len(window) == 3
        assert all(
            key in window[0]
            for key in [
                "pile_id",
                "pile_in_tracker",
                "grading_window_min",
                "grading_window_max",
                "ground_elevation",
            ]
        )

    def test_grading_window_values(self, project, tracker):
        """Test grading window calculation values."""
        window = grading_window(project, tracker)
        first_pile = window[0]

        # min = current_elevation + min_reveal + flooding + (tolerance/2)
        expected_min = 10.0 + 1.375 + 0.0 + 0.0
        # max = current_elevation + max_reveal - (tolerance/2)
        expected_max = 10.0 + 1.675 - 0.0

        assert abs(first_pile["grading_window_min"] - expected_min) < 1e-6
        assert abs(first_pile["grading_window_max"] - expected_max) < 1e-6


class TestTargetHeightLine:
    """Test target height line calculation."""

    @pytest.fixture
    def project(self):
        """Create a test project."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    def test_target_height_line_horizontal(self, project):
        """Test target height line with horizontal tracker."""
        tracker = BaseTracker(tracker_id=1)
        # Create piles with same elevation
        for i in range(3):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0 + i * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        slope, y_intercept = target_height_line(tracker, project)

        # With same elevation, slope should be 0
        assert abs(slope) < 1e-6

        # All piles should be at target height
        for pile in tracker.piles:
            expected = pile.pile_at_target_height(project)
            assert abs(pile.height - expected) < 1e-6

    def test_target_height_line_sloped(self, project):
        """Test target height line with sloped terrain."""
        tracker = BaseTracker(tracker_id=1)
        piles_data = [
            (100.0, 10.0),
            (110.0, 10.5),
            (120.0, 11.0),
        ]
        for i, (northing, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=50.0,
                initial_elevation=elevation,
                pile_id=1.0 + i * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        slope, y_intercept = target_height_line(tracker, project)

        # Verify slope is calculated correctly
        first = tracker.get_first()
        last = tracker.get_last()
        first_target = first.pile_at_target_height(project)
        last_target = last.pile_at_target_height(project)
        expected_slope = (last_target - first_target) / (last.northing - first.northing)

        # Should be capped at max_incline if needed
        if abs(expected_slope) > project.constraints.max_incline:
            expected_slope = (
                project.constraints.max_incline
                if expected_slope > 0
                else -project.constraints.max_incline
            )

        assert abs(slope - expected_slope) < 1e-6

    def test_target_height_line_exceeds_max_incline(self, project):
        """Test that slope is capped at max_incline."""
        tracker = BaseTracker(tracker_id=1)
        # Create steep slope that exceeds max_incline (0.15)
        piles_data = [
            (100.0, 10.0),
            (110.0, 15.0),  # Very steep: rise=5, run=10, slope=0.5 > 0.15
        ]
        for i, (northing, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=50.0,
                initial_elevation=elevation,
                pile_id=1.0 + i * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        slope, _ = target_height_line(tracker, project)

        # Slope should be capped at max_incline
        assert abs(slope) <= project.constraints.max_incline + 1e-6


class TestCheckWithinWindow:
    """Test window violation detection."""

    @pytest.fixture
    def project(self):
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    def test_all_within_window(self, project):
        """Test when all piles are within window."""
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        # Set height within window
        pile.height = pile.pile_at_target_height(project)

        window = grading_window(project, tracker)
        violations = check_within_window(window, tracker)

        assert len(violations) == 0

    def test_pile_below_window(self, project):
        """Test when pile is below minimum window."""
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        # Set height below minimum
        pile.height = pile.true_min_height(project) - 0.1

        window = grading_window(project, tracker)
        violations = check_within_window(window, tracker)

        assert len(violations) == 1
        assert violations[0]["pile_id"] == 1
        assert violations[0]["below_by"] < -0.09  # Approximately -0.1

    def test_pile_above_window(self, project):
        """Test when pile is above maximum window."""
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        # Set height above maximum
        pile.height = pile.true_max_height(project) + 0.1

        window = grading_window(project, tracker)
        violations = check_within_window(window, tracker)

        assert len(violations) == 1
        assert violations[0]["pile_id"] == 1
        assert violations[0]["above_by"] > 0.09  # Approximately 0.1


class TestSlidingLine:
    """Test sliding line adjustment."""

    @pytest.fixture
    def project(self):
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    def test_sliding_line_adjusts_heights(self, project):
        """Test that sliding line adjusts pile heights."""
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        # Set initial height
        pile.height = pile.true_min_height(project) - 0.1
        initial_height = pile.height

        violating_piles = [
            {
                "pile_id": 1,
                "target_height": pile.height,
                "grading_window_min": pile.true_min_height(project),
                "grading_window_max": pile.true_max_height(project),
                "below_by": -0.1,
                "above_by": 0.0,
            }
        ]

        slope = 0.0
        y_intercept = _y_intercept(slope, pile.northing, pile.height)

        sliding_line(tracker, violating_piles, slope, y_intercept)

        # Height should have changed
        assert abs(pile.height - initial_height) > 1e-6


class TestGrading:
    """Test grading function that adjusts ground elevation."""

    @pytest.fixture
    def project(self):
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    def test_grading_adjusts_elevation_correctly(self, project):
        """
        Test that grading adjusts current elevation by the correct amount.

        The grading function should move ground elevation by (below_by + above_by).
        - If pile is BELOW window (below_by < 0), ground should be LOWERED
        - If pile is ABOVE window (above_by > 0), ground should be RAISED
        """
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        initial_elevation = pile.current_elevation

        # Pile is 0.08 below the minimum window
        violating_piles = [
            {
                "pile_id": 1,
                "below_by": -0.08,  # Pile is 0.08 below minimum
                "above_by": 0.0,
            }
        ]

        grading(tracker, violating_piles)

        # Expected movement = below_by + above_by = -0.08 + 0.0 = -0.08
        # Ground should be lowered by 0.08 to bring pile height up into window
        expected_movement = violating_piles[0]["below_by"] + violating_piles[0]["above_by"]
        actual_movement = pile.current_elevation - initial_elevation

        assert abs(actual_movement - expected_movement) < 1e-6, (
            f"Expected ground to move by {expected_movement}, but moved by {actual_movement}"
        )

    def test_grading_pile_above_window(self, project):
        """Test grading when pile is above the window (ground needs to be raised)."""
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        initial_elevation = pile.current_elevation

        # Pile is 0.05 above the maximum window
        violating_piles = [
            {
                "pile_id": 1,
                "below_by": 0.0,
                "above_by": 0.05,  # Pile is 0.05 above maximum
            }
        ]

        grading(tracker, violating_piles)

        # Expected movement = below_by + above_by = 0.0 + 0.05 = 0.05
        # Ground should be raised by 0.05 to bring pile height down into window
        expected_movement = violating_piles[0]["below_by"] + violating_piles[0]["above_by"]
        actual_movement = pile.current_elevation - initial_elevation

        assert abs(actual_movement - expected_movement) < 1e-6, (
            f"Expected ground to move by {expected_movement}, but moved by {actual_movement}"
        )


class TestAlgorithmCorrectness:
    """
    Test that demonstrates WHY the grading algorithm is correct.
    These tests explain the algorithm logic step-by-step.
    """

    def test_grading_algorithm_logic_simple_case(self):
        """
        Demonstrates the grading algorithm logic with a simple 3-pile tracker.

        SCENARIO:
        - 3 piles with elevations: 10.0, 10.5, 11.0
        - min_reveal=1.375, max_reveal=1.675 (window size = 0.3)
        - target_height_percentage=0.5 (midpoint of window)
        - max_incline=0.15

        EXPECTED BEHAVIOR:
        1. Calculate grading windows for each pile
        2. Set target heights at midpoint (1.375 + 0.15 = 1.525 above ground)
        3. Create line through target heights
        4. If slope > max_incline, clamp it
        5. Check if all piles fit within their windows
        6. If not, slide line vertically OR adjust ground elevations
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=1)

        # Create simple 3-pile tracker
        piles_data = [
            (100.0, 10.0),  # Pile 1: northing=100.0, elevation=10.0
            (110.0, 10.5),  # Pile 2: northing=110.0, elevation=10.5
            (120.0, 11.0),  # Pile 3: northing=120.0, elevation=11.0
        ]

        for i, (northing, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=50.0,
                initial_elevation=elevation,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)

        # STEP 1: Verify grading windows are calculated correctly
        window = grading_window(project, tracker)

        for i, pile in enumerate(tracker.piles):
            expected_min = pile.current_elevation + constraints.min_reveal_height
            expected_max = pile.current_elevation + constraints.max_reveal_height

            assert abs(window[i]["grading_window_min"] - expected_min) < 1e-6, (
                f"Pile {i + 1} window min incorrect"
            )
            assert abs(window[i]["grading_window_max"] - expected_max) < 1e-6, (
                f"Pile {i + 1} window max incorrect"
            )

        # STEP 2: Set target height line
        slope, y_intercept = target_height_line(tracker, project)

        # STEP 3: Verify slope is reasonable
        # Target heights: pile1=11.525, pile2=12.025, pile3=12.525
        # Rise = 12.525 - 11.525 = 1.0
        # Run = 120.0 - 100.0 = 20.0
        # Slope = 1.0 / 20.0 = 0.05 < max_incline (0.15)
        assert abs(slope) <= constraints.max_incline + 1e-6, (
            f"Slope {slope} should be <= max_incline {constraints.max_incline}"
        )

        # STEP 4: Verify each pile's height is on the target line
        for pile in tracker.piles:
            expected_height = slope * pile.northing + y_intercept
            assert abs(pile.height - expected_height) < 1e-6, (
                f"Pile {pile.pile_in_tracker} height not on target line"
            )

        # STEP 5: Check if piles are within windows
        violations = check_within_window(window, tracker)

        # With this gentle slope, all piles should fit
        assert len(violations) == 0, f"Expected no violations, but found {len(violations)}"

    def test_grading_algorithm_steep_terrain_requires_clamping(self):
        """
        Test algorithm behavior when terrain slope exceeds max_incline.

        SCENARIO:
        - Very steep terrain: elevations 10.0, 12.0, 14.0 (rise=4.0 over run=20.0)
        - Natural slope would be 0.2, but max_incline=0.15

        EXPECTED:
        - Algorithm should CLAMP slope to 0.15
        - First pile should be at minimum reveal (1.375)
        - Last pile should be at maximum reveal (1.675)
        - Middle piles interpolated along clamped line
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Steep_Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=1)

        # Steep terrain
        piles_data = [
            (100.0, 10.0),
            (110.0, 12.0),  # Rise of 2.0 over run of 10.0 = slope 0.2
            (120.0, 14.0),
        ]

        for i, (northing, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=50.0,
                initial_elevation=elevation,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)

        # Set target height line
        slope, y_intercept = target_height_line(tracker, project)

        # Verify slope is clamped
        assert abs(abs(slope) - constraints.max_incline) < 1e-6, (
            f"Slope should be clamped to max_incline {constraints.max_incline}, got {slope}"
        )

        # Run full grading
        from flatTrackerGrading import main

        main(project)

        # Verify all piles respect constraints after grading
        for pile in tracker.piles:
            assert pile.pile_revealed >= constraints.min_reveal_height - 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal below minimum"
            )
            assert pile.pile_revealed <= constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal above maximum"
            )

    def test_grading_algorithm_with_violations_requires_ground_adjustment(self):
        """
        Test algorithm when sliding line isn't enough - ground must be adjusted.

        SCENARIO:
        - Terrain with a sudden dip in the middle
        - Target line would violate middle pile's window
        - Sliding line can't fix it (limited by window size / 2)
        - Ground elevation must be adjusted for violating piles

        EXPECTED:
        - Algorithm slides line first
        - If still violations, adjusts ground elevations
        - Final result: all piles within windows
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Dip_Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=1)

        # Terrain with dip in middle
        piles_data = [
            (100.0, 10.0),
            (110.0, 10.1),
            (120.0, 8.0),  # Sudden dip
            (130.0, 10.2),
            (140.0, 10.3),
        ]

        for i, (northing, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=50.0,
                initial_elevation=elevation,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)

        # Record initial elevation of middle pile
        middle_pile = tracker.get_pile_in_tracker(3)
        initial_middle_elevation = middle_pile.initial_elevation

        # Run full grading algorithm
        from flatTrackerGrading import main

        main(project)

        # Middle pile should have had its ground elevation adjusted
        # (because the dip was too severe for just line sliding)
        assert middle_pile.final_elevation != initial_middle_elevation, (
            "Middle pile ground should have been adjusted due to dip"
        )

        # All piles should now be within windows
        for pile in tracker.piles:
            assert pile.pile_revealed >= constraints.min_reveal_height - 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal below minimum after grading"
            )
            assert pile.pile_revealed <= constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal above maximum after grading"
            )
