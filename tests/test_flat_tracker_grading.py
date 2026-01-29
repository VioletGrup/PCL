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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
        assert violations[0]["pile_in_tracker"] == 1
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
        assert violations[0]["pile_in_tracker"] == 1
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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

        slope = 0.0
        y_intercept = _y_intercept(slope, pile.northing, pile.height)

        sliding_line(tracker, project, slope, y_intercept, intercept_span=0.1)

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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        return Project(name="Test", project_type="standard", constraints=constraints)

    def test_grading_brings_violating_pile_into_window(self, project):
        """
        After grading, previously violating piles should be within their windows.
        
        This tests the OUTCOME, not the implementation.
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
        
        # Set pile to violate the window
        pile.height = 11.30  # This will be below minimum
        
        # Get initial window and violations
        window_before = grading_window(project, tracker)
        violations_before = check_within_window(window_before, tracker)
        
        # Verify there IS a violation before grading
        assert len(violations_before) > 0, (
            "Test setup error: pile should violate window before grading"
        )
        
        # ACT - Apply grading
        grading(tracker, violations_before)
        
        # ASSERT - Check that violations are fixed
        # Recalculate window with new ground elevation
        window_after = grading_window(project, tracker)
        violations_after = check_within_window(window_after, tracker)
        
        # After grading, there should be NO violations
        assert len(violations_after) == 0, (
            f"After grading, pile should be within window, but still has violations: "
            f"{violations_after}"
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
                "pile_in_tracker": 1,
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
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
            assert pile.pile_revealed <= constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal above maximum after grading"
            )


class TestEdgeCasesAndAbnormalValues:
    """Test behavior with extreme or invalid values."""

    def test_extreme_tolerance(self):
        """Test with very large tolerance - should raise ValueError for inverted window."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.5,  # tol/2 = 0.25, larger than 1.6-1.4=0.2
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        # Now properly rejects inverted window configurations at validation time
        with pytest.raises(ValueError, match="pile_install_tolerance.*too large"):
            constraints.validate("standard")

    def test_zero_window(self):
        """Test where min reveal == max reveal."""
        constraints = ProjectConstraints(
            min_reveal_height=1.5,
            max_reveal_height=1.5,  # Zero window
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        # Note: ProjectConstraints.validate() might catch this, but let's test the logic.
        with pytest.raises(ValueError, match="min_reveal_height must be < max_reveal_height"):
            constraints.validate("standard")

    def test_negative_target_percentage(self):
        """Test with abnormal target percentage."""
        # Note: validate() doesn't check target_height_percentage range, let's see logic.
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=-1.0,  # Abnormal
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project(name="Edge", project_type="standard", constraints=constraints)
        tracker = BaseTracker(tracker_id=1)
        pile = BasePile(100, 50, 10, 1.01, 1, 0)
        tracker.add_pile(pile)

        target = pile.pile_at_target_height(project)
        # min = 11.375, max = 11.675, span = 0.3
        # target = 11.375 + 0.3 * (-1.0) = 11.075
        assert abs(target - 11.075) < 1e-6

    def test_extremely_steep_terrain(self):
        """Test with terrain slope 1.0 (45 deg) with max_incline 0.15."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("Steep", "standard", constraints)
        tracker = BaseTracker(1)
        # Rise 10 over Run 10 = slope 1.0
        tracker.add_pile(BasePile(100, 50, 10, 1.01, 1, 0))
        tracker.add_pile(BasePile(110, 50, 20, 1.02, 2, 0))

        slope, _ = target_height_line(tracker, project)
        assert abs(slope - 0.15) < 1e-6

    def test_empty_tracker(self):
        """Test that main() handles empty trackers without error."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("Empty", "standard", constraints)
        tracker = BaseTracker(1)  # No piles
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        main(project)  # Should not raise

    def test_zero_northing_difference(self):
        """Test that zero run between piles causes ValueError with clear message."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("ZeroRun", "standard", constraints)
        tracker = BaseTracker(1)
        
        # Same northing - vertical alignment (invalid)
        tracker.add_pile(BasePile(100, 50, 10, 1.01, 1, 0))
        tracker.add_pile(BasePile(100, 60, 11, 1.02, 2, 0))  # Same northing!
        project.add_tracker(tracker)

        # Zero northing difference now raises ValueError with descriptive message
        with pytest.raises(ValueError, match="identical northing"):
            target_height_line(tracker, project)

    def test_single_pile_tracker(self):
        """Test that a single-pile tracker is handled correctly."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("SinglePile", "standard", constraints)
        tracker = BaseTracker(1)
        # One pile
        tracker.add_pile(BasePile(100, 50, 10, 1, 1, 0))
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        main(project)

        pile = tracker.piles[0]
        # target_height = 10 + 1.4 + (1.6-1.4)*0.5 = 11.5
        assert abs(pile.height - 11.5) < 1e-6
        assert abs(pile.pile_revealed - 1.5) < 1e-6

    def test_main_requires_sorted_piles(self):
        """Test that main() works correctly when piles are already sorted by northing.
        
        Note: flatTrackerGrading.main() expects piles to be sorted by northing.
        The caller is responsible for sorting piles before calling main().
        """
        from flatTrackerGrading import main
        
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        
        # Create piles in sorted order (by northing)
        pile_low = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_in_tracker=1,
            pile_id=1.01,
            flooding_allowance=0.0,
        )
        pile_mid = BasePile(
            northing=115.0,
            easting=50.0,
            initial_elevation=11.0,
            pile_in_tracker=2,
            pile_id=1.02,
            flooding_allowance=0.0,
        )
        pile_high = BasePile(
            northing=125.0,
            easting=50.0,
            initial_elevation=12.0,
            pile_in_tracker=3,
            pile_id=1.03,
            flooding_allowance=0.0,
        )
        
        tracker = BaseTracker(tracker_id=1)
        tracker.add_pile(pile_low)
        tracker.add_pile(pile_mid)
        tracker.add_pile(pile_high)
        
        project = Project(
            name="SortTest",
            project_type="standard",
            constraints=constraints,
        )
        project.add_tracker(tracker)
        
        # Piles are in sorted order
        assert tracker.piles[0].northing < tracker.piles[1].northing < tracker.piles[2].northing
        
        # Call main()
        main(project)
        
        # Verify grading completed successfully
        for pile in tracker.piles:
            assert pile.final_elevation >= 0
            assert pile.total_height > 0
            assert constraints.min_reveal_height - 1e-6 <= pile.pile_revealed <= constraints.max_reveal_height + 1e-6

    def test_high_flooding_allowance(self):
        """Test that high flooding allowance shifts the window up."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("Flooding", "standard", constraints)
        tracker = BaseTracker(1)
        # Large flooding allowance
        pile = BasePile(100, 50, 10, 1, 1, flooding_allowance=2.0)
        tracker.add_pile(pile)
        project.add_tracker(tracker)

        with pytest.warns(UserWarning, match="inverted grading window"):
            window = grading_window(project, tracker)
        # min = 10 + 1.4 + 2.0 = 13.4
        # max = 10 + 1.6 = 11.6
        # Note: If max_reveal doesn't account for flooding, min > max happens.
        # This is expected behavior for severe flooding.
        assert window[0]["grading_window_min"] == 13.4
        assert window[0]["grading_window_max"] == 11.6

    def test_target_height_percentage_boundaries(self):
        """Test target_height_percentage at 0.0 and 1.0."""
        tracker = BaseTracker(1)
        tracker.add_pile(BasePile(100, 50, 10, 1, 1, 0))

        # 0%
        c0 = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.0,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        p0 = Project("B0", "standard", c0)
        assert abs(tracker.piles[0].pile_at_target_height(p0) - 11.4) < 1e-6

        # 100%
        c1 = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=1.0,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        p1 = Project("B1", "standard", c1)
        assert abs(tracker.piles[0].pile_at_target_height(p1) - 11.6) < 1e-6

    def test_outlier_spike_handling(self):
        """Test optimizer response to a single major spike."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("Outlier", "standard", constraints)
        tracker = BaseTracker(1)
        # 5 piles, middle one is a spike
        tracker.add_pile(BasePile(northing=100, easting=50, initial_elevation=10, pile_in_tracker=1, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=110, easting=50, initial_elevation=10, pile_in_tracker=2, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=120, easting=50, initial_elevation=20, pile_in_tracker=3, pile_id=1, flooding_allowance=0))  # SPIKE!
        tracker.add_pile(BasePile(northing=130, easting=50, initial_elevation=10, pile_in_tracker=4, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=140, easting=50, initial_elevation=10, pile_in_tracker=5, pile_id=1, flooding_allowance=0))
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        main(project)

        # The algorithm should have adjusted the ground of the spike pile
        # and kept the others closer to the original terrain
        spike_pile = tracker.get_pile_in_tracker(3)
        assert spike_pile.final_elevation < 20.0
        assert spike_pile.pile_revealed >= 1.4 - 1e-6

    def test_negative_elevations(self):
        """Test with projects below sea level (negative initial_elevation)."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("BelowSeaLevel", "standard", constraints)
        tracker = BaseTracker(1)
        # All elevations are negative
        tracker.add_pile(BasePile(northing=100, easting=50, initial_elevation=-10, pile_in_tracker=1, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=110, easting=50, initial_elevation=-10.1, pile_in_tracker=2, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=120, easting=50, initial_elevation=-9.9, pile_in_tracker=3, pile_id=1, flooding_allowance=0))
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        main(project)

        for pile in tracker.piles:
            assert pile.final_elevation < 0
            assert 1.4 - 1e-6 <= pile.pile_revealed <= 1.6 + 1e-6

    def test_massive_coordinate_offsets(self):
        """Test with very large UTM coordinates."""
        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("UTM", "standard", constraints)
        tracker = BaseTracker(1)
        # 7 million Northing, 500k Easting
        tracker.add_pile(BasePile(northing=7000000.1, easting=500000.1, initial_elevation=10, pile_in_tracker=1, pile_id=1, flooding_allowance=0))
        tracker.add_pile(BasePile(northing=7000001.2, easting=500000.2, initial_elevation=10.1, pile_in_tracker=2, pile_id=1, flooding_allowance=0))
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        main(project)

        for pile in tracker.piles:
            assert 1.4 - 1e-6 <= pile.pile_revealed <= 1.6 + 1e-6

    def test_large_tracker_performance(self):
        """Performance test with 500 piles."""
        import time

        constraints = ProjectConstraints(
            min_reveal_height=1.4,
            max_reveal_height=1.6,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percentage=0.5,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
        )
        project = Project("Performance", "standard", constraints)
        tracker = BaseTracker(1)
        for i in range(1, 501):
            tracker.add_pile(BasePile(northing=100 + i * 5, easting=50, initial_elevation=10 + (i % 5), pile_in_tracker=i, pile_id=1, flooding_allowance=0))
        project.add_tracker(tracker)

        from flatTrackerGrading import main

        start = time.time()
        main(project)
        end = time.time()

        # Should complete reasonably fast (e.g., under 2 seconds for 500 piles)
        # The 2D search is O(N_slopes * N_intercepts), but we use optimized search.
        duration = end - start
        assert duration < 5.0  # Loose bound for varied systems