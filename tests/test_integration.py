#!/usr/bin/env python3
"""
Integration tests for the complete grading workflow.
Tests the main grading function with a few Punch's creek data.
"""

from __future__ import annotations

import pytest

from BasePile import BasePile
from BaseTracker import BaseTracker
from flatTrackerGrading import main
from Project import Project
from ProjectConstraints import ProjectConstraints


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

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
        return Project(name="Edge_Test", project_type="standard", constraints=constraints)

    def test_single_pile_tracker(self, project):
        """Test tracker with only one pile."""
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

        # Should not crash
        main(project)

        # Pile should have valid final elevation
        assert pile.final_elevation > 0
        assert pile.total_height > pile.final_elevation

    def test_tracker_no_grading_needed(self, project):
        """Test tracker where all piles are already within window."""
        tracker = BaseTracker(tracker_id=1)

        # Create perfectly flat tracker at target height
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0 + i * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        # All piles should have minimal or no change
        for pile in tracker.piles:
            change = abs(pile.final_elevation - pile.initial_elevation)
            # Should be very small or zero
            assert change < 0.1  # Reasonable tolerance

    def test_multiple_trackers(self, project):
        """Test project with multiple trackers."""
        for tracker_id in range(1, 4):
            tracker = BaseTracker(tracker_id=tracker_id)
            for i in range(10):
                pile = BasePile(
                    northing=100.0 + i * 10.0,
                    easting=50.0 * tracker_id,
                    initial_elevation=10.0 + i * 0.05,
                    pile_id=float(f"{tracker_id}.{i + 1:02d}"),
                    pile_in_tracker=i + 1,
                    flooding_allowance=0.0,
                )
                tracker.add_pile(pile)
            project.add_tracker(tracker)

        # Should process all trackers without error
        main(project)

        # Verify all trackers were processed
        assert len(project.trackers) == 3
        for tracker in project.trackers:
            for pile in tracker.piles:
                assert pile.final_elevation > 0
                assert pile.total_height > 0


class TestConstraintEnforcement:
    """Test that constraints are properly enforced."""

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
        return Project(name="Constraint_Test", project_type="standard", constraints=constraints)

    def test_reveal_height_bounds(self, project):
        """Test that all piles respect reveal height bounds."""
        tracker = BaseTracker(tracker_id=1)

        # Create varied terrain
        elevations = [10.0, 10.5, 11.0, 11.5, 12.0, 11.8, 11.2, 10.8, 10.3, 10.1]
        for i, elev in enumerate(elevations):
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

        # Check all piles respect reveal height bounds
        for pile in tracker.piles:
            reveal = pile.pile_revealed
            assert reveal >= project.constraints.min_reveal_height - 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal height {reveal}\n"
                f"below minimum {project.constraints.min_reveal_height}"
            )
            assert reveal <= project.constraints.max_reveal_height + 1e-6, (
                f"Pile {pile.pile_in_tracker} reveal height {reveal}\n"
                f"above maximum {project.constraints.max_reveal_height}"
            )

    def test_total_height_calculated(self, project):
        """Test that total height is correctly calculated."""
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

        # total_height = pile.height (set during grading)
        # pile_revealed = total_height - final_elevation
        expected_revealed = pile.total_height - pile.final_elevation
        assert abs(pile.pile_revealed - expected_revealed) < 1e-6, (
            f"Pile revealed calculation incorrect: got {pile.pile_revealed},\n"
            f"expected {expected_revealed}"
        )
