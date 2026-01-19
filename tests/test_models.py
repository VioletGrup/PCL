#!/usr/bin/env python3
"""
Unit tests for data models: BasePile, BaseTracker, Project, ProjectConstraints.
Tests validation, calculations, and data integrity.
"""

from __future__ import annotations

import pytest

from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints


class TestBasePile:
    """Test BasePile model."""

    def test_pile_creation(self):
        """Test basic pile creation."""
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.01,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        assert pile.northing == 100.0
        assert pile.easting == 50.0
        assert pile.initial_elevation == 10.0
        assert pile.current_elevation == 10.0
        assert pile.final_elevation == 10.0

    def test_pile_validation_negative_id(self):
        """Test that negative pile_id raises error."""
        with pytest.raises(ValueError, match="pile_id must be non-negative"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=-1.0,
                pile_in_tracker=1,
                flooding_allowance=0.0,
            )

    def test_pile_validation_invalid_pile_in_tracker(self):
        """Test that pile_in_tracker < 1 raises error."""
        with pytest.raises(ValueError, match="pile_in_tracker must be >= 1"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0,
                pile_in_tracker=0,
                flooding_allowance=0.0,
            )

    def test_pile_validation_negative_flooding(self):
        """Test that negative flooding_allowance raises error."""
        with pytest.raises(ValueError, match="flooding_allowance must be non-negative"):
            BasePile(
                northing=100.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0,
                pile_in_tracker=1,
                flooding_allowance=-0.5,
            )

    def test_set_current_elevation(self):
        """Test setting current elevation."""
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        pile.set_current_elevation(11.5)
        assert pile.current_elevation == 11.5

    def test_set_final_elevation(self):
        """Test setting final elevation."""
        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )
        pile.set_final_elevation(12.0)
        assert pile.final_elevation == 12.0

    def test_true_min_height(self):
        """Test true minimum height calculation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.2,
        )

        # min = current + min_reveal + flooding + tolerance/2
        expected = 10.0 + 1.375 + 0.2 + 0.1 / 2
        assert abs(pile.true_min_height(project) - expected) < 1e-6

    def test_true_max_height(self):
        """Test true maximum height calculation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )

        # max = current + max_reveal - tolerance/2
        expected = 10.0 + 1.675 - 0.1 / 2
        assert abs(pile.true_max_height(project) - expected) < 1e-6

    def test_pile_at_target_height(self):
        """Test target height calculation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,  # 50%
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )

        min_h = pile.true_min_height(project)
        max_h = pile.true_max_height(project)
        window = max_h - min_h
        expected = min_h + window * 0.5

        assert abs(pile.pile_at_target_height(project) - expected) < 1e-6

    def test_max_height_no_tolerance(self):
        """Test maximum height without tolerance calculation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.0,
        )

        # max_no_tol = current + max_reveal
        expected = 10.0 + 1.675
        assert abs(pile.max_height_no_tolerance(project) - expected) < 1e-6

    def test_min_height_no_tolerance(self):
        """Test minimum height without tolerance calculation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        pile = BasePile(
            northing=100.0,
            easting=50.0,
            initial_elevation=10.0,
            pile_id=1.0,
            pile_in_tracker=1,
            flooding_allowance=0.2,
        )

        # min_no_tol = current + min_reveal + flooding
        expected = 10.0 + 1.375 + 0.2
        assert abs(pile.min_height_no_tolerance(project) - expected) < 1e-6


class TestBaseTracker:
    """Test BaseTracker model."""

    def test_tracker_creation(self):
        """Test basic tracker creation."""
        tracker = BaseTracker(tracker_id=1)
        assert tracker.tracker_id == 1
        assert len(tracker.piles) == 0

    def test_add_pile(self):
        """Test adding piles to tracker."""
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
        assert len(tracker.piles) == 1
        assert tracker.piles[0] == pile

    def test_pole_count(self):
        """Test pole count property."""
        tracker = BaseTracker(tracker_id=1)
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
        assert tracker.pole_count == 5

    def test_sort_by_pole_position(self):
        """Test sorting piles by position."""
        tracker = BaseTracker(tracker_id=1)
        # Add piles out of order
        positions = [3, 1, 5, 2, 4]
        for pos in positions:
            pile = BasePile(
                northing=100.0 + pos * 10.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0 + pos * 0.01,
                pile_in_tracker=pos,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        tracker.sort_by_pole_position()

        # Verify sorted order
        for i, pile in enumerate(tracker.piles):
            assert pile.pile_in_tracker == i + 1

    def test_get_first_last(self):
        """Test get_first and get_last methods."""
        tracker = BaseTracker(tracker_id=1)
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        first = tracker.get_first()
        last = tracker.get_last()

        assert first.pile_in_tracker == 1
        assert last.pile_in_tracker == 5

    def test_get_pile_in_tracker(self):
        """Test retrieving specific pile by position."""
        tracker = BaseTracker(tracker_id=1)
        for i in range(5):
            pile = BasePile(
                northing=100.0 + i * 10.0,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=1.0 + (i + 1) * 0.01,
                pile_in_tracker=i + 1,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        pile_3 = tracker.get_pile_in_tracker(3)
        assert pile_3.pile_in_tracker == 3

    def test_get_pile_in_tracker_invalid(self):
        """Test that invalid pile position raises error."""
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

        with pytest.raises(ValueError, match="not found"):
            tracker.get_pile_in_tracker(10)


class TestProjectConstraints:
    """Test ProjectConstraints validation."""

    def test_valid_standard_constraints(self):
        """Test creating valid standard project constraints."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.1,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        constraints.validate("standard")
        # Should not raise

    def test_invalid_reveal_heights(self):
        """Test that min >= max reveal height raises error."""
        constraints = ProjectConstraints(
            min_reveal_height=2.0,
            max_reveal_height=1.5,  # Invalid: min > max
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        with pytest.raises(ValueError, match="min_reveal_height must be <"):
            constraints.validate("standard")

    def test_negative_tolerance(self):
        """Test that negative tolerance raises error."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=-0.1,  # Invalid
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        with pytest.raises(ValueError, match="pile_install_tolerance must be >= 0"):
            constraints.validate("standard")


class TestProject:
    """Test Project model."""

    def test_project_creation(self):
        """Test basic project creation."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        assert project.name == "Test"
        assert project.project_type == "standard"
        assert len(project.trackers) == 0

    def test_add_tracker(self):
        """Test adding tracker to project."""
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
        project.add_tracker(tracker)

        assert len(project.trackers) == 1
        assert project.trackers[0] == tracker

    def test_total_piles(self):
        """Test total piles property."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        # Add 2 trackers with different pile counts
        for tracker_id in [1, 2]:
            tracker = BaseTracker(tracker_id=tracker_id)
            for i in range(tracker_id * 5):  # 5 piles in tracker 1, 10 in tracker 2
                pile = BasePile(
                    northing=100.0,
                    easting=50.0,
                    initial_elevation=10.0,
                    pile_id=float(f"{tracker_id}.{i + 1:02d}"),
                    pile_in_tracker=i + 1,
                    flooding_allowance=0.0,
                )
                tracker.add_pile(pile)
            project.add_tracker(tracker)

        assert project.total_piles == 15

    def test_get_tracker_by_id(self):
        """Test retrieving tracker by ID."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=42)
        project.add_tracker(tracker)

        found = project.get_tracker_by_id(42)
        assert found.tracker_id == 42

    def test_get_tracker_by_id_not_found(self):
        """Test that retrieving non-existent tracker raises error."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        with pytest.raises(ValueError, match="not found"):
            project.get_tracker_by_id(999)

    def test_get_pile_by_id_with_real_format(self):
        """Test that get_pile_by_id() works with tracker.pile format."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        tracker = BaseTracker(tracker_id=175)

        # Add sequential piles
        for pit in range(1, 16):
            pile = BasePile(
                northing=100.0 + pit,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=float(f"175.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        tracker.sort_by_pole_position()
        project.add_tracker(tracker)

        # Now test retrieval
        pile_1 = project.get_pile_by_id(175.01)
        assert pile_1.pile_in_tracker == 1
        assert abs(pile_1.pile_id - 175.01) < 1e-6

        pile_10 = project.get_pile_by_id(175.10)
        assert pile_10.pile_in_tracker == 10
        assert abs(pile_10.pile_id - 175.10) < 1e-6

        pile_15 = project.get_pile_by_id(175.15)
        assert pile_15.pile_in_tracker == 15
        assert abs(pile_15.pile_id - 175.15) < 1e-6

    def test_get_pile_by_id_extraction_logic(self):
        """Test the mathematical extraction of tracker_id and pile_in_tracker."""
        constraints = ProjectConstraints(
            min_reveal_height=1.375,
            max_reveal_height=1.675,
            pile_install_tolerance=0.0,
            max_incline=0.15,
            target_height_percantage=0.5,
            max_angle_rotation=0.0,
        )
        project = Project(name="Test", project_type="standard", constraints=constraints)

        # Create tracker 175 with ALL piles 1-15
        tracker = BaseTracker(tracker_id=175)
        for pit in range(1, 16):  # Piles 1 through 15
            pile = BasePile(
                northing=100.0 + pit,
                easting=50.0,
                initial_elevation=10.0,
                pile_id=float(f"175.{pit:02d}"),
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
            tracker.add_pile(pile)

        tracker.sort_by_pole_position()
        project.add_tracker(tracker)

        # Verify extraction works
        import math
        from decimal import Decimal

        pile_id = 175.10
        extracted_tracker = math.floor(pile_id)
        pile_id_dec = Decimal(str(pile_id))
        extracted_pile = int((pile_id_dec % 1) * 100)

        assert extracted_tracker == 175, f"Expected tracker 175, got {extracted_tracker}"
        assert extracted_pile == 10, f"Expected pile 10, got {extracted_pile}"

        # And verify get_pile_by_id uses this correctly
        retrieved = project.get_pile_by_id(175.10)
        assert retrieved.pile_in_tracker == 10
        assert abs(retrieved.pile_id - 175.10) < 1e-6
