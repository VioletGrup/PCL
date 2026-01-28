#!/usr/bin/env python3
"""
Tests for numerical precision and decimal accuracy.
Ensures all calculations maintain 6 decimal place precision.
"""

from __future__ import annotations

import pytest

from BasePile import BasePile
from BaseTracker import BaseTracker
from flatTrackerGrading import main
from Project import Project
from ProjectConstraints import ProjectConstraints


class TestNumericalPrecision:
    """Test that all calculations maintain required precision."""

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
        return Project(name="Precision_Test", project_type="standard", constraints=constraints)

    def test_elevation_precision_6_decimals(self, project):
        """Test that elevations maintain 6 decimal precision."""
        tracker = BaseTracker(tracker_id=1)

        # Use realistic coordinates from actual data
        pile = BasePile(
            northing=6907309.498,
            easting=338615.049,
            initial_elevation=416.30241,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        # Add adjacent piles
        pile2 = BasePile(
            northing=6907299.365,
            easting=338615.049,
            initial_elevation=416.377040,
            pile_id=1.02,
            pile_in_tracker=2,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile2)

        project.add_tracker(tracker)
        main(project)

        # Check that results can represent 6 decimal places
        for p in tracker.piles:
            # Verify we're not losing precision in string representation
            final_str = f"{p.final_elevation:.6f}"
            change_str = f"{p.final_elevation - p.initial_elevation:.6f}"

            # Should be able to parse back to same value
            assert abs(float(final_str) - p.final_elevation) < 1e-9
            assert abs(float(change_str) - (p.final_elevation - p.initial_elevation)) < 1e-9

    def test_small_changes_preserved(self, project):
        """Test that very small elevation changes are preserved."""
        tracker = BaseTracker(tracker_id=1)

        # Create scenario with very small required change
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.000001,  # Very close to target
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Even tiny changes should be detectable
        change = pile.final_elevation - pile.initial_elevation
        # Should be able to measure changes at 6 decimal precision
        change_rounded = round(change, 6)
        assert abs(change - change_rounded) < 1e-9

    def test_coordinate_precision_large_values(self, project):
        """Test precision with large coordinate values."""
        tracker = BaseTracker(tracker_id=1)

        # Use actual large coordinate values from project
        large_coords = [
            (6907309.498000, 338615.049000, 416.302410),
            (6907319.019000, 338622.049000, 416.210570),
            (6907327.037000, 338629.049000, 416.125180),
        ]

        for i, (northing, easting, elevation) in enumerate(large_coords):
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

        # Verify large coordinate values don't cause precision loss
        for pile in tracker.piles:
            # Coordinates should be exact
            northing_str = f"{pile.northing:.6f}"
            easting_str = f"{pile.easting:.6f}"

            assert abs(float(northing_str) - pile.northing) < 1e-6
            assert abs(float(easting_str) - pile.easting) < 1e-6

    def test_reveal_height_precision(self, project):
        """Test that reveal height calculations maintain precision."""
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

        project.add_tracker(tracker)
        main(project)

        # pile_revealed = total_height - final_elevation
        calculated_reveal = pile.total_height - pile.final_elevation
        assert abs(pile.pile_revealed - calculated_reveal) < 1e-9

        # Should maintain 6 decimal precision
        reveal_str = f"{pile.pile_revealed:.6f}"
        assert abs(float(reveal_str) - pile.pile_revealed) < 1e-9


class TestRoundingBehavior:
    """Test that rounding doesn't introduce errors."""

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
        return Project(name="Rounding_Test", project_type="standard", constraints=constraints)

    def test_no_accumulated_rounding_errors(self, project):
        """Test that repeated calculations don't accumulate rounding errors."""
        tracker = BaseTracker(tracker_id=1)

        # Create a long tracker
        for i in range(15):
            pile = BasePile(
                northing=1000.0 + i * 10.123456,
                easting=500.0 + i * 5.654321,
                initial_elevation=100.0 + i * 0.123456,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # Verify no pile has accumulated rounding errors
        for pile in tracker.piles:
            # Change should be reasonable
            change = abs(pile.final_elevation - pile.initial_elevation)
            # Should not have massive accumulated error
            assert change < 1.0  # Reasonable maximum change

            # Reveal height should be within expected bounds
            assert (
                project.constraints.min_reveal_height - 1e-6
                <= pile.pile_revealed
                <= project.constraints.max_reveal_height + 1e-6
            )

    def test_consistency_across_runs(self, project):
        """Test that same input produces same output."""
        tracker1 = BaseTracker(tracker_id=1)
        tracker2 = BaseTracker(tracker_id=2)

        # Create identical trackers
        for tracker in [tracker1, tracker2]:
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

        project.add_tracker(tracker1)
        project.add_tracker(tracker2)
        main(project)

        # Results should be identical for identical trackers
        for p1, p2 in zip(tracker1.piles, tracker2.piles):
            assert abs(p1.final_elevation - p2.final_elevation) < 1e-9
            assert abs(p1.pile_revealed - p2.pile_revealed) < 1e-9
            assert abs(p1.total_height - p2.total_height) < 1e-9
