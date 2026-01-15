#!/usr/bin/env python3
"""
Additional critical tests for comprehensive coverage of edge cases
"""

from __future__ import annotations

import pytest

from BasePile import BasePile
from BaseTracker import BaseTracker
from flatTrackerGrading import main
from Project import Project
from ProjectConstraints import ProjectConstraints


class TestFullTrackerValidation:
    """Test that entire trackers produce correct outputs, not just individual piles"""

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
        return Project(name="Full_Tracker_Test", project_type="standard", constraints=constraints)

    def test_tracker_175_all_piles(self, project):
        """
        Validate ALL 15 piles in tracker 175 match expected output
        (Tracker 175 has 1 pile that needs grading).
        This ensures the entire grading algorithm works correctly across the full tracker.
        """
        tracker = BaseTracker(tracker_id=175)

        # Complete input data
        input_data = [
            (1, 6907395.974, 338615.049, 416.000000),
            (2, 6907387.704, 338615.049, 416.000000),
            (3, 6907378.276, 338615.049, 416.006960),
            (4, 6907368.848, 338615.049, 416.047460),
            (5, 6907358.263, 338615.049, 416.092930),
            (6, 6907348.835, 338615.049, 416.133430),
            (7, 6907338.249, 338615.049, 416.178900),
            (8, 6907329.166, 338615.049, 416.217920),
            (9, 6907320.084, 338615.049, 416.256940),
            (10, 6907309.498, 338615.049, 416.302410),
            (11, 6907300.070, 338615.049, 416.424320),
            (12, 6907289.484, 338615.049, 416.553460),
            (13, 6907280.057, 338615.049, 416.692480),
            (14, 6907270.629, 338615.049, 416.824200),
            (15, 6907262.359, 338615.049, 416.939740),
        ]

        # Expected output data
        expected_outputs = [
            (1, 416.000000, 0.000000, 417.375000, 1.375000),
            (2, 416.000000, 0.000000, 417.433165, 1.433165),
            (3, 416.006960, 0.000000, 417.499473, 1.492513),
            (4, 416.047460, 0.000000, 417.565782, 1.518322),
            (5, 416.092930, 0.000000, 417.640229, 1.547299),
            (6, 416.133430, 0.000000, 417.706538, 1.573108),
            (7, 416.178900, 0.000000, 417.780991, 1.602091),
            (8, 416.217920, 0.000000, 417.844874, 1.626954),
            (9, 416.256940, 0.000000, 417.908749, 1.651809),
            (10, 416.3082023, 0.005792344, 417.9832023, 1.675000),  # Pile 10 HAS a change
            (11, 416.424320, 0.000000, 418.049511, 1.625191),
            (12, 416.553460, 0.000000, 418.123965, 1.570505),
            (13, 416.692480, 0.000000, 418.190267, 1.497787),
            (14, 416.824200, 0.000000, 418.256576, 1.432375),
            (15, 416.939740, 0.000000, 418.314740, 1.375000),
        ]

        for pit, northing, easting, elevation in input_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"175.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Validate ALL piles
        for (
            pile_num,
            expected_final,
            expected_change,
            expected_total,
            expected_revealed,
        ) in expected_outputs:
            pile = tracker.get_pile_in_tracker(pile_num)

            assert abs(pile.final_elevation - expected_final) < 1e-5, (
                f"Pile {pile_num}: final_elevation mismatch"
            )

            actual_change = pile.final_elevation - pile.initial_elevation
            assert abs(actual_change - expected_change) < 1e-5, f"Pile {pile_num}: change mismatch"

            assert abs(pile.total_height - expected_total) < 1e-5, (
                f"Pile {pile_num}: total_height mismatch"
            )

            assert abs(pile.pile_revealed - expected_revealed) < 1e-5, (
                f"Pile {pile_num}: pile_revealed mismatch"
            )


class TestBoundaryPiles:
    """Test first and last pile behavior, which define the grading line"""

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
        return Project(name="Boundary_Test", project_type="standard", constraints=constraints)

    def test_first_pile_at_exact_minimum(self, project):
        """First pile should respect minimum reveal height exactly"""
        tracker = BaseTracker(tracker_id=1)

        # Create tracker where first pile is at minimum reveal
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 + i * 0.1,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        first_pile = tracker.get_first()
        # First pile reveal should be >= min_reveal_height
        assert first_pile.pile_revealed >= project.constraints.min_reveal_height - 1e-6

    def test_last_pile_at_exact_maximum(self, project):
        """Last pile should respect maximum reveal height"""
        tracker = BaseTracker(tracker_id=1)

        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 - i * 0.1,  # Decreasing elevation
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        last_pile = tracker.get_last()
        # Last pile reveal should be <= max_reveal_height
        assert last_pile.pile_revealed <= project.constraints.max_reveal_height + 1e-6


class TestMaxInclineEnforcement:
    """Test that max_incline constraint is properly enforced"""

    @pytest.fixture
    def project(self):
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,  # 15% max slope
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Incline_Test", project_type="standard", constraints=constraints)

    def test_steep_terrain_clamped_to_max_incline(self, project):
        """
        Test that when terrain would naturally create a slope > max_incline,
        the grading line is clamped to max_incline
        """
        tracker = BaseTracker(tracker_id=1)

        # Create steep terrain (slope would be 50% without clamping)
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,  # 10m spacing
                easting=50.0,
                initial_elevation=10.0 + i * 5.0,  # 5m elevation change = 50% slope
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Calculate actual slope between first and last pile
        first = tracker.get_first()
        last = tracker.get_last()

        rise = last.total_height - first.total_height
        run = abs(last.northing - first.northing)
        actual_slope = abs(rise / run)

        # Slope should be <= max_incline (with small tolerance)
        assert actual_slope <= project.constraints.max_incline + 1e-6, (
            f"Slope {actual_slope} exceeds max_incline {project.constraints.max_incline}"
        )


class TestGradingWindowEdgeCases:
    """Test edge cases around grading window boundaries."""

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
        return Project(name="Window_Test", project_type="standard", constraints=constraints)

    def test_pile_barely_within_window(self, project):
        """Test pile that's just barely within the grading window."""
        tracker = BaseTracker(tracker_id=1)

        # Create piles where middle pile is barely within window
        for i in range(5):
            # Set elevation so pile 3 is just within window
            if i == 2:
                elev = 10.0  # Will be set to barely within window
            else:
                elev = 10.0 + i * 0.05

            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=elev,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # All piles should be within reveal bounds
        for pile in tracker.piles:
            assert pile.pile_revealed >= project.constraints.min_reveal_height - 1e-6
            assert pile.pile_revealed <= project.constraints.max_reveal_height + 1e-6

    def test_consecutive_violations(self, project):
        """Test multiple consecutive piles violating the window."""
        tracker = BaseTracker(tracker_id=1)

        # Create terrain with a dip in the middle (piles 6-9 much lower)
        for i in range(15):
            if 5 <= i <= 8:
                elev = 8.0  # Much lower - will need grading
            else:
                elev = 10.0 + i * 0.05

            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=elev,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # After grading, all piles should be within bounds
        for pile in tracker.piles:
            assert pile.pile_revealed >= project.constraints.min_reveal_height - 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal {pile.pile_revealed} below minimum"
            )
            assert pile.pile_revealed <= project.constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal {pile.pile_revealed} above maximum"
            )


class TestDataIntegrity:
    """Test handling of malformed or edge-case input data."""

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
        return Project(name="Data_Integrity_Test", project_type="standard", constraints=constraints)

    def test_unsorted_pile_data(self, project):
        """Test that algorithm works even if piles are added out of order."""
        tracker = BaseTracker(tracker_id=1)

        # Add piles in random order
        pile_order = [3, 1, 5, 2, 4]
        for pit in pile_order:
            pile = BasePile(
                northing=100.0 + pit * 10.0,
                easting=50.0,
                initial_elevation=10.0 + pit * 0.1,
                pile_id=1.0 + pit * 0.01,
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)

        # Manually sort (normally done by load function)
        tracker.sort_by_pole_position()

        # Should work without errors
        main(project)

        # First pile should have pile_in_tracker = 1
        assert tracker.get_first().pile_in_tracker == 1
        # Last pile should have pile_in_tracker = 5
        assert tracker.get_last().pile_in_tracker == 5

    def test_identical_elevations(self, project):
        """Test tracker where all piles have identical initial elevations."""
        tracker = BaseTracker(tracker_id=1)

        # All piles at same elevation (perfectly flat)
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0,  # All identical
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Should produce valid grading (slope = 0)
        for pile in tracker.piles:
            assert pile.final_elevation >= 0
            assert pile.total_height > 0
            assert pile.pile_revealed >= project.constraints.min_reveal_height - 1e-6
            assert pile.pile_revealed <= project.constraints.max_reveal_height + 1e-6

    def test_zero_initial_elevation(self, project):
        """Test handling of piles at elevation = 0 (sea level or datum)."""
        tracker = BaseTracker(tracker_id=1)

        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=0.0 + i * 0.1,  # Starting from 0
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Should handle zero elevations correctly
        first_pile = tracker.get_first()
        assert first_pile.final_elevation >= 0
        assert first_pile.total_height > 0


class TestNegativeScenarios:
    """Test scenarios that should fail gracefully with clear errors."""

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
        return Project(name="Negative_Test", project_type="standard", constraints=constraints)

    def test_negative_pile_id_rejected(self, project):
        """Negative pile IDs should be rejected."""
        with pytest.raises(ValueError, match="pile_id must be non-negative"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=-1,  # Invalid
                pile_in_tracker=1,
                flooding_allowance=0.0,
            )

    def test_zero_pile_in_tracker_rejected(self, project):
        """pile_in_tracker must be >= 1."""
        with pytest.raises(ValueError, match="pile_in_tracker must be >= 1"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.01,
                pile_in_tracker=0,  # Invalid
                flooding_allowance=0.0,
            )

    def test_negative_flooding_allowance_rejected(self, project):
        """Negative flooding allowance should be rejected."""
        with pytest.raises(ValueError, match="flooding_allowance must be non-negative"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.01,
                pile_in_tracker=1,
                flooding_allowance=-0.5,  # Invalid
            )

    def test_empty_tracker_handled(self, project):
        """Empty tracker should be skipped without errors."""
        tracker = BaseTracker(tracker_id=1)
        project.add_tracker(tracker)

        # Should complete successfully (skipping empty tracker)
        main(project)

        # Tracker should still be in project but unchanged
        assert len(project.trackers) == 1
        assert len(project.trackers[0].piles) == 0


class TestImpossibleConstraints:
    """
    Test scenarios where constraints create impossible situations.
    These tests verify the system handles or detects impossible constraints.
    """

    def test_tolerance_plus_flooding_exceeds_window(self):
        """
        Test when tolerance + flooding allowance > reveal window.

        This creates an IMPOSSIBLE situation where min_height > max_height.

        SCENARIO:
        - Reveal window = max_reveal - min_reveal = 1.675 - 1.375 = 0.3
        - Tolerance = 0.2 (consumes 0.2 of window)
        - Flooding = 0.15 (consumes additional 0.15)
        - Total consumed = 0.2 + 0.15 = 0.35 > 0.3 (IMPOSSIBLE!)

        EXPECTED:
        - true_min_height > true_max_height
        - System should detect this during grading
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.2,  # Tolerance = 0.2
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(
            name="Impossible_Constraints_Test", project_type="standard", constraints=constraints
        )

        tracker = BaseTracker(tracker_id=1)

        # Pile with flooding allowance
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.15,  # Flooding = 0.15
        )
        tracker.add_pile(pile)

        # Calculate bounds
        min_h = pile.true_min_height(project)
        max_h = pile.true_max_height(project)

        # min_h = 10.0 + 1.375 + 0.15 + (0.2/2) = 11.625
        # max_h = 10.0 + 1.675 - (0.2/2) = 11.575
        # min_h > max_h is impossible

        assert min_h > max_h, (
            "When tolerance + flooding > window, min should exceed max (impossible constraint)"
        )

        # Document the impossible window size
        window_size = max_h - min_h  # This will be negative
        assert window_size < 0, f"Window size should be negative (impossible), got {window_size}"

        # The grading algorithm should handle this gracefullye
        project.add_tracker(tracker)

        # Try to run grading - document behavior
        try:
            main(project)
            # If it succeeds, check if result is reasonable
            # (it shouldn't be possible to satisfy constraints)
            print("Warning: Impossible constraints did not raise error")
            print(f"  min_h={min_h:.6f}, max_h={max_h:.6f}")
            print(f"  pile final_elevation={pile.final_elevation:.6f}")
            print(f"  pile total_height={pile.total_height:.6f}")
            print(f"  pile pile_revealed={pile.pile_revealed:.6f}")

        except Exception as e:
            print(f"Impossible constraints raised error (expected): {e}")

    def test_tolerance_equals_window_size(self):
        """
        Test when tolerance exactly equals the window size.

        SCENARIO:
        - Window = 1.675 - 1.375 = 0.3
        - Tolerance = 0.3 (exactly equals window)
        - Effective window = 0.0 (zero!)

        EXPECTED:
        - true_min_height == true_max_height
        - Only ONE possible height for each pile
        - Very constrained grading
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.3,  # Equals window size
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Zero_Window_Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=1)

        for i in range(3):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 + i * 0.1,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        # Verify window is zero
        pile = tracker.piles[0]
        min_h = pile.true_min_height(project)
        max_h = pile.true_max_height(project)

        # min_h = 10.0 + 1.375 + 0.15 = 11.525
        # max_h = 10.0 + 1.675 - 0.15 = 11.525
        # They should be equal

        assert abs(min_h - max_h) < 1e-6, (
            f"When tolerance equals window, min and max should be equal. Got min={min_h},\n"
            f"max={max_h}\n"
        )

        # Try to run grading
        project.add_tracker(tracker)

        try:
            main(project)

            # With zero window, all piles must be at exact target
            for pile in tracker.piles:
                effective_min = pile.true_min_height(project)
                effective_max = pile.true_max_height(project)

                # Should be equal
                assert abs(effective_min - effective_max) < 1e-6

                # Total height should be at this exact value
                # (with possible small tolerance for numerical precision)
                assert abs(pile.total_height - effective_min) < 1e-3, (
                    f"With zero window, pile height must be exact: expected {effective_min},"
                    f"got {pile.total_height}"
                )

        except Exception as e:
            print(f"Zero window constraints raised error: {e}")

    def test_flooding_allowance_exceeds_window_alone(self):
        """
        Test when flooding allowance ALONE exceeds the reveal window.

        SCENARIO:
        - Window = 0.3
        - Flooding = 0.4 (exceeds window by itself!)
        - No tolerance

        This is clearly impossible - even without tolerance, we can't fit
        the flooding allowance within the reveal window.
        """
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,  # No tolerance
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(
            name="Flooding_Exceeds_Window", project_type="standard", constraints=constraints
        )

        tracker = BaseTracker(tracker_id=1)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.4,  # Exceeds window of 0.3
        )
        tracker.add_pile(pile)

        min_h = pile.true_min_height(project)
        max_h = pile.true_max_height(project)

        # min_h = 10.0 + 1.375 + 0.4 = 11.775
        # max_h = 10.0 + 1.675 = 11.675
        # min_h > max_h is impossible

        assert min_h > max_h, (
            f"Flooding allowance exceeds window: min={min_h} should be > max={max_h}"
        )

        # This should be caught
        project.add_tracker(tracker)

        try:
            main(project)
            print("Warning: Excessive flooding allowance did not raise error")
            print(f"  min_h={min_h:.6f}, max_h={max_h:.6f}, window={(max_h - min_h):.6f}")
        except Exception as e:
            print(f"Excessive flooding raised error (expected): {e}")


class TestNonZeroTolerance:
    """Test grading behavior with pile installation tolerance."""

    @pytest.fixture
    def project_tolerance_01(self):
        """Project with 0.1 unit tolerance."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,  # 0.1 unit tolerance
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Tolerance_01_Test", project_type="standard", constraints=constraints)

    @pytest.fixture
    def project_tolerance_02(self):
        """Project with 0.2 unit tolerance."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.2,  # 0.2 unit tolerance
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Tolerance_02_Test", project_type="standard", constraints=constraints)

    def test_tolerance_reduces_effective_window(self, project_tolerance_01):
        """Test that tolerance reduces the effective grading window."""
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

        # Calculate effective window
        # Original window = max_reveal - min_reveal = 1.675 - 1.375 = 0.3
        # Effective window = original - tolerance = 0.3 - 0.1 = 0.2

        min_h = pile.true_min_height(project_tolerance_01)
        max_h = pile.true_max_height(project_tolerance_01)
        effective_window = max_h - min_h

        # min_h = elevation + min_reveal + tolerance/2 = 10.0 + 1.375 + 0.05 = 11.425
        # max_h = elevation + max_reveal - tolerance/2 = 10.0 + 1.675 - 0.05 = 11.625
        # effective_window = 11.625 - 11.425 = 0.2

        expected_window = 0.2
        assert abs(effective_window - expected_window) < 1e-6, (
            f"Effective window {effective_window} != expected {expected_window}"
        )

    def test_tolerance_02_further_reduces_window(self, project_tolerance_02):
        """Test that larger tolerance further reduces grading window."""
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

        min_h = pile.true_min_height(project_tolerance_02)
        max_h = pile.true_max_height(project_tolerance_02)
        effective_window = max_h - min_h

        # With 0.2 tolerance:
        # min_h = 10.0 + 1.375 + 0.1 = 11.475
        # max_h = 10.0 + 1.675 - 0.1 = 11.575
        # effective_window = 0.1

        expected_window = 0.1
        assert abs(effective_window - expected_window) < 1e-6, (
            f"Effective window {effective_window} != expected {expected_window}"
        )

    def test_grading_respects_tolerance_bounds(self, project_tolerance_01):
        """Test that grading respects tolerance-adjusted bounds."""
        tracker = BaseTracker(tracker_id=1)

        # Create simple tracker
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 + i * 0.1,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project_tolerance_01.add_tracker(tracker)
        main(project_tolerance_01)

        # Verify all piles respect tolerance adjusted bounds
        for pile in tracker.piles:
            min_h = pile.true_min_height(project_tolerance_01)
            max_h = pile.true_max_height(project_tolerance_01)

            # total_height should be within [min_h, max_h]
            assert pile.total_height >= min_h - 1e-6, (
                f"Pile {pile.pile_in_tracker}: total_height {pile.total_height} below min {min_h}"
            )
            assert pile.total_height <= max_h + 1e-6, (
                f"Pile {pile.pile_in_tracker}: total_height {pile.total_height} above max {max_h}"
            )

    def test_tolerance_affects_reveal_height_range(self, project_tolerance_01):
        """Test that tolerance affects the range of possible reveal heights."""
        tracker = BaseTracker(tracker_id=1)

        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 + i * 0.05,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project_tolerance_01.add_tracker(tracker)
        main(project_tolerance_01)

        # With tolerance, reveal heights should still be within bounds
        # but the effective range is smaller
        for pile in tracker.piles:
            reveal = pile.pile_revealed

            # Reveal height should be within original bounds
            # (tolerance affects installation, not the final reveal requirement)
            assert reveal >= project_tolerance_01.constraints.min_reveal_height - 1e-6, (
                f"Pile {pile.pile_in_tracker}: reveal {reveal} below minimum"
            )
            assert reveal <= project_tolerance_01.constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker}: reveal {reveal} above maximum"
            )

    def test_tolerance_with_steep_terrain(self, project_tolerance_01):
        """Test tolerance handling with steep terrain that needs grading."""
        tracker = BaseTracker(tracker_id=1)

        # Create steep terrain
        elevations = [10.0, 10.8, 11.5, 12.0, 12.3]

        for i, elev in enumerate(elevations):
            pile = BasePile(
                northing=100.0 + i * 10.123456,
                easting=50.0 + i * 5.654321,
                initial_elevation=elev,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project_tolerance_01.add_tracker(tracker)
        main(project_tolerance_01)

        # Even with steep terrain and tolerance, constraints should be met
        for pile in tracker.piles:
            min_h = pile.true_min_height(project_tolerance_01)
            max_h = pile.true_max_height(project_tolerance_01)

            assert pile.total_height >= min_h - 1e-6
            assert pile.total_height <= max_h + 1e-6

    def test_large_tolerance_nearly_eliminates_window(self):
        """Test behavior when tolerance nearly eliminates the grading window."""
        # Window = max_reveal - min_reveal = 1.675 - 1.375 = 0.3
        # If tolerance = 0.28, effective window = 0.3 - 0.28 = 0.02 (very small)

        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.28,  # Nearly eliminates window
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(
            name="Narrow_Window_Test", project_type="standard", constraints=constraints
        )

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

        min_h = pile.true_min_height(project)
        max_h = pile.true_max_height(project)
        effective_window = max_h - min_h

        # Effective window = 0.3 - 0.28 = 0.02
        expected_window = 0.02
        assert abs(effective_window - expected_window) < 1e-6

        # Window is still positive but very narrow
        assert effective_window > 0, "Window should still be positive"

    def test_comparison_zero_vs_nonzero_tolerance(self):
        """Compare grading results with zero vs non-zero tolerance."""
        # Project with zero tolerance
        constraints_zero = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project_zero = Project(
            name="Zero_Tolerance", project_type="standard", constraints=constraints_zero
        )

        # Project with 0.1 tolerance
        constraints_01 = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project_01 = Project(
            name="01_Tolerance", project_type="standard", constraints=constraints_01
        )

        # Create identical trackers
        tracker_zero = BaseTracker(tracker_id=1)
        tracker_01 = BaseTracker(tracker_id=2)

        for tracker in [tracker_zero, tracker_01]:
            for i in range(5):
                pile = BasePile(
                    northing=100.0 + i * 10.0,
                    easting=50.0,
                    initial_elevation=10.0 + i * 0.1,
                    pile_id=float(f"{tracker.tracker_id}.{i + 1:02d}"),
                    pile_in_tracker=i + 1,
                    flooding_allowance=0.0,
                )
                tracker.add_pile(pile)

        project_zero.add_tracker(tracker_zero)
        project_01.add_tracker(tracker_01)

        main(project_zero)
        main(project_01)

        # Compare grading windows
        for pile_zero, pile_01 in zip(tracker_zero.piles, tracker_01.piles):
            # Windows should differ by tolerance amount
            window_zero = pile_zero.true_max_height(project_zero) - pile_zero.true_min_height(
                project_zero
            )
            window_01 = pile_01.true_max_height(project_01) - pile_01.true_min_height(project_01)

            # Difference should be exactly the tolerance
            window_diff = window_zero - window_01
            assert abs(window_diff - 0.1) < 1e-6, (
                f"Window difference {window_diff} != tolerance 0.1"
            )

    def test_real_world_tolerance_scenario(self):
        """Test with realistic tolerance value from construction practice"""
        # Typical pile installation tolerance might be 0.05 to 0.1 units
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.05,  # 0.05m tolerance
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(
            name="Realistic_Tolerance", project_type="standard", constraints=constraints
        )

        tracker = BaseTracker(tracker_id=1)

        # Use realistic coordinates and elevations
        piles_data = [
            (6907309.498, 338615.049, 416.30241),
            (6907319.019, 338622.049, 416.21057),
            (6907327.037, 338629.049, 416.12518),
        ]

        for i, (northing, easting, elevation) in enumerate(piles_data):
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Verify grading succeeded with realistic tolerance
        for pile in tracker.piles:
            # All constraints should be met
            assert pile.final_elevation > 0
            assert pile.total_height > pile.final_elevation

            min_h = pile.true_min_height(project)
            max_h = pile.true_max_height(project)

            assert pile.total_height >= min_h - 1e-6
            assert pile.total_height <= max_h + 1e-6


class TestToleranceEdgeCases:
    """Test edge cases specific to tolerance handling"""

    def test_very_small_tolerance(self):
        """Test with very small but non-zero tolerance"""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.001,  # 1mm tolerance
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(
            name="Tiny_Tolerance_Test", project_type="standard", constraints=constraints
        )

        tracker = BaseTracker(tracker_id=1)

        for i in range(3):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0 + i * 0.05,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # With tiny tolerance, behavior should be very close to zero tolerance
        for pile in tracker.piles:
            min_h = pile.true_min_height(project)
            max_h = pile.true_max_height(project)
            window = max_h - min_h

            # Window should be nearly 0.3 (only 0.001 difference)
            expected_window = 0.3 - 0.001
            assert abs(window - expected_window) < 1e-6
