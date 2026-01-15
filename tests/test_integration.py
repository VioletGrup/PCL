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


class TestRealWorldCases:
    """Integration tests using actual data from the project with complete tracker context."""

    @pytest.fixture
    def project(self):
        """Create project matching actual constraints."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        return Project(name="Test_Project", project_type="standard", constraints=constraints)

    def test_tracker_175_pile_10(self, project):
        """
        Test case from tracker 175, pile 10.

        Input: tracker=175, pile=10, X=338615.049, Y=6907309.498, Z=416.30241
        Expected Output: final_elevation=416.3082023, change=0.005792344,
                        total_height=417.9832023, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=175)

        # Complete tracker data
        piles_data = [
            (1, 6907395.974, 338615.049, 416.000000),
            (2, 6907387.704, 338615.049, 416.000000),
            (3, 6907378.276, 338615.049, 416.006960),
            (4, 6907368.848, 338615.049, 416.047460),
            (5, 6907358.263, 338615.049, 416.092930),
            (6, 6907348.835, 338615.049, 416.133430),
            (7, 6907338.249, 338615.049, 416.178900),
            (8, 6907329.166, 338615.049, 416.217920),
            (9, 6907320.084, 338615.049, 416.256940),
            (10, 6907309.498, 338615.049, 416.302410),  # Target pile
            (11, 6907300.070, 338615.049, 416.424320),
            (12, 6907289.484, 338615.049, 416.553460),
            (13, 6907280.057, 338615.049, 416.692480),
            (14, 6907270.629, 338615.049, 416.824200),
            (15, 6907262.359, 338615.049, 416.939740),
        ]

        for pit, northing, easting, elevation in piles_data:
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

        target_pile = tracker.get_pile_in_tracker(10)

        # Expected values from the output data
        expected_final_elevation = 416.3082023
        expected_change = 0.005792344
        expected_total_height = 417.9832023
        expected_total_revealed = 1.675

        # Verify results (within 6 decimal places)
        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )

    def test_tracker_185_pile_9(self, project):
        """
        Test case from tracker 185, pile 9.

        Input: tracker=185, pile=9, X=338622.049, Y=6907319.019, Z=416.210570
        Expected Output: final_elevation=416.2190043, change=0.008434335,
                        total_height=417.8940043, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=185)

        # Complete tracker data
        piles_data = [
            (1, 6907394.909, 338622.049, 416.000000),
            (2, 6907386.639, 338622.049, 416.000000),
            (3, 6907377.212, 338622.049, 416.000000),
            (4, 6907367.784, 338622.049, 416.001090),
            (5, 6907357.198, 338622.049, 416.046560),
            (6, 6907347.770, 338622.049, 416.087060),
            (7, 6907337.185, 338622.049, 416.132530),
            (8, 6907328.102, 338622.049, 416.171550),
            (9, 6907319.019, 338622.049, 416.210570),  # Target pile
            (10, 6907308.433, 338622.049, 416.284390),
            (11, 6907299.005, 338622.049, 416.391630),
            (12, 6907288.420, 338622.049, 416.545620),
            (13, 6907278.992, 338622.049, 416.677340),
            (14, 6907269.564, 338622.049, 416.811840),
            (15, 6907261.294, 338622.049, 416.913780),
        ]

        for pit, northing, easting, elevation in piles_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"185.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        target_pile = tracker.get_pile_in_tracker(9)

        expected_final_elevation = 416.2190043
        expected_change = 0.008434335
        expected_total_height = 417.8940043
        expected_total_revealed = 1.675

        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},\n"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )

    def test_tracker_185_pile_10(self, project):
        """
        Test case from tracker 185, pile 10.

        Input: tracker=185, pile=10, X=338622.049, Y=6907308.433, Z=416.284390
        Expected Output: final_elevation=416.291401, change=0.00701096,
                        total_height=417.966401, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=185)

        # Complete tracker data
        piles_data = [
            (1, 6907394.909, 338622.049, 416.000000),
            (2, 6907386.639, 338622.049, 416.000000),
            (3, 6907377.212, 338622.049, 416.000000),
            (4, 6907367.784, 338622.049, 416.001090),
            (5, 6907357.198, 338622.049, 416.046560),
            (6, 6907347.770, 338622.049, 416.087060),
            (7, 6907337.185, 338622.049, 416.132530),
            (8, 6907328.102, 338622.049, 416.171550),
            (9, 6907319.019, 338622.049, 416.210570),
            (10, 6907308.433, 338622.049, 416.284390),  # Target pile
            (11, 6907299.005, 338622.049, 416.391630),
            (12, 6907288.420, 338622.049, 416.545620),
            (13, 6907278.992, 338622.049, 416.677340),
            (14, 6907269.564, 338622.049, 416.811840),
            (15, 6907261.294, 338622.049, 416.913780),
        ]

        for pit, northing, easting, elevation in piles_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"185.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        target_pile = tracker.get_pile_in_tracker(10)

        expected_final_elevation = 416.291401
        expected_change = 0.00701096
        expected_total_height = 417.966401
        expected_total_revealed = 1.675

        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},\n"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )

    def test_tracker_195_pile_8(self, project):
        """
        Test case from tracker 195, pile 8.

        Input: tracker=195, pile=8, X=338629.049, Y=6907327.037, Z=416.125180
        Expected Output: final_elevation=416.1360133, change=0.010833263,
                        total_height=417.8110133, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=195)

        # Complete tracker data
        piles_data = [
            (1, 6907393.845, 338629.049, 416.000000),
            (2, 6907385.575, 338629.049, 416.000000),
            (3, 6907376.147, 338629.049, 416.000000),
            (4, 6907366.719, 338629.049, 416.000000),
            (5, 6907356.134, 338629.049, 416.000190),
            (6, 6907346.706, 338629.049, 416.040690),
            (7, 6907336.120, 338629.049, 416.086160),
            (8, 6907327.037, 338629.049, 416.125180),  # Target pile
            (9, 6907317.954, 338629.049, 416.164200),
            (10, 6907307.369, 338629.049, 416.253120),
            (11, 6907297.941, 338629.049, 416.380770),
            (12, 6907287.355, 338629.049, 416.530470),
            (13, 6907277.927, 338629.049, 416.659880),
            (14, 6907268.499, 338629.049, 416.771890),
            (15, 6907260.230, 338629.049, 416.872020),
        ]

        for pit, northing, easting, elevation in piles_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"195.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        target_pile = tracker.get_pile_in_tracker(8)

        expected_final_elevation = 416.1360133
        expected_change = 0.010833263
        expected_total_height = 417.8110133
        expected_total_revealed = 1.675

        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},\n"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )

    def test_tracker_195_pile_9(self, project):
        """
        Test case from tracker 195, pile 9.

        Input: tracker=195, pile=9, X=338629.049, Y=6907317.954, Z=416.164200
        Expected Output: final_elevation=416.1952922, change=0.031092219,
                        total_height=417.8702922, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=195)

        # Complete tracker data
        piles_data = [
            (1, 6907393.845, 338629.049, 416.000000),
            (2, 6907385.575, 338629.049, 416.000000),
            (3, 6907376.147, 338629.049, 416.000000),
            (4, 6907366.719, 338629.049, 416.000000),
            (5, 6907356.134, 338629.049, 416.000190),
            (6, 6907346.706, 338629.049, 416.040690),
            (7, 6907336.120, 338629.049, 416.086160),
            (8, 6907327.037, 338629.049, 416.125180),
            (9, 6907317.954, 338629.049, 416.164200),  # Target pile
            (10, 6907307.369, 338629.049, 416.253120),
            (11, 6907297.941, 338629.049, 416.380770),
            (12, 6907287.355, 338629.049, 416.530470),
            (13, 6907277.927, 338629.049, 416.659880),
            (14, 6907268.499, 338629.049, 416.771890),
            (15, 6907260.230, 338629.049, 416.872020),
        ]

        for pit, northing, easting, elevation in piles_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"195.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        target_pile = tracker.get_pile_in_tracker(9)

        expected_final_elevation = 416.1952922
        expected_change = 0.031092219
        expected_total_height = 417.8702922
        expected_total_revealed = 1.675

        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},\n"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )

    def test_tracker_295_pile_7(self, project):
        """
        Test case from tracker 295, pile 7.

        Input: tracker=295, pile=7, X=338685.049, Y=6907327.604, Z=416.000000
        Expected Output: final_elevation=416.0046703, change=0.004670283,
                        total_height=417.6796703, total_revealed=1.675
        """
        tracker = BaseTracker(tracker_id=295)

        # Complete tracker data
        piles_data = [
            (1, 6907385.329, 338685.049, 416.000000),
            (2, 6907377.059, 338685.049, 416.000000),
            (3, 6907367.631, 338685.049, 416.000000),
            (4, 6907358.204, 338685.049, 416.000000),
            (5, 6907347.618, 338685.049, 416.000000),
            (6, 6907338.190, 338685.049, 416.000000),
            (7, 6907327.604, 338685.049, 416.000000),  # Target pile
            (8, 6907318.521, 338685.049, 416.000000),
            (9, 6907309.438, 338685.049, 416.063850),
            (10, 6907298.852, 338685.049, 416.188480),
            (11, 6907289.424, 338685.049, 416.299470),
            (12, 6907278.839, 338685.049, 416.424100),
            (13, 6907269.411, 338685.049, 416.535090),
            (14, 6907259.983, 338685.049, 416.646080),
            (15, 6907251.713, 338685.049, 416.705220),
        ]

        for pit, northing, easting, elevation in piles_data:
            pile = BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=elevation,
                pile_id=float(f"295.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        project.add_tracker(tracker)
        main(project)

        target_pile = tracker.get_pile_in_tracker(7)

        expected_final_elevation = 416.0046703
        expected_change = 0.004670283
        expected_total_height = 417.6796703
        expected_total_revealed = 1.675

        assert abs(target_pile.final_elevation - expected_final_elevation) < 1e-6, (
            f"Final elevation mismatch: got {target_pile.final_elevation},\n"
            f"expected {expected_final_elevation}"
        )

        actual_change = target_pile.final_elevation - target_pile.initial_elevation
        assert abs(actual_change - expected_change) < 1e-6, (
            f"Change mismatch: got {actual_change},\nexpected {expected_change}"
        )

        assert abs(target_pile.total_height - expected_total_height) < 1e-6, (
            f"Total height mismatch: got {target_pile.total_height},\n"
            f"expected {expected_total_height}"
        )

        assert abs(target_pile.pile_revealed - expected_total_revealed) < 1e-6, (
            f"Pile revealed mismatch: got {target_pile.pile_revealed},\n"
            f"expected {expected_total_revealed}"
        )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

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
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
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
