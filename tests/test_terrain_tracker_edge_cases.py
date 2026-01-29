#!/usr/bin/env python3
"""
Edge case tests for terrain tracker grading logic.
Focuses on unusual tracker configurations, extreme terrain, and boundary conditions.
"""

from __future__ import annotations

import pytest
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from terrainTrackerGrading import (
    target_height_line,
    grading_window,
    grading,
    shift_piles,
    slope_correction,
    slide_all_piles,
    main,
    check_within_window,
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
        max_incline=0.15,
        target_height_percentage=0.5,
        max_angle_rotation=0.0,
        max_segment_deflection_deg=1.0,
        max_cumulative_deflection_deg=5.0,
        edge_overhang=0.0,
    )


@pytest.fixture
def simple_project(base_constraints):
    """Simple project for edge case tests."""
    return Project(
        name="EdgeCaseTest", project_type="terrain_following", constraints=base_constraints
    )


# =============================================================================
# STRUCTURAL EDGE CASES
# =============================================================================


class TestSinglePileTracker:
    """Tests for trackers with only one pile."""

    def test_single_pile_target_height_line(self, simple_project):
        """Single pile tracker should set pile height to target height (no slope needed)."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(
            northing=0.0,
            easting=0.0,
            initial_elevation=10.0,
            pile_in_tracker=1,
            pile_id=1.01,
            flooding_allowance=0.0,
        )
        tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        # Single pile now handled correctly - sets height to target
        target_height_line(tracker, simple_project)
        
        # Pile should be set to its target height (middle of window: 11.0 to 12.0 = 11.5)
        assert p.height == pytest.approx(11.5, abs=0.01)

    def test_single_pile_grading_window(self, simple_project):
        """Single pile should produce valid grading window."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(
            northing=0.0,
            easting=0.0,
            initial_elevation=10.0,
            pile_in_tracker=1,
            pile_id=1.01,
            flooding_allowance=0.0,
        )
        tracker.add_pile(p)

        window = grading_window(simple_project, tracker)
        assert len(window) == 1
        assert window[0]["grading_window_min"] == pytest.approx(11.0)
        assert window[0]["grading_window_max"] == pytest.approx(12.0)


class TestTwoPileTracker:
    """Tests for trackers with exactly two piles (minimum for segments)."""

    def test_two_pile_target_height_line(self, simple_project):
        """Two pile tracker should calculate slope correctly."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1.01, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 11.0, 2, 1.02, 0.0)
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        simple_project.add_tracker(tracker)

        target_height_line(tracker, simple_project)

        # Slope should be 0.1 (1m rise over 10m)
        h0 = tracker.piles[0].height
        h1 = tracker.piles[1].height
        actual_slope = (h1 - h0) / 10.0
        assert actual_slope == pytest.approx(0.1, abs=0.01)

    def test_two_pile_creates_one_segment(self, simple_project):
        """Two pile tracker should create exactly one segment."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1.01, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 10.0, 2, 1.02, 0.0)
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        tracker.create_segments()

        assert len(tracker.segments) == 1

    def test_two_pile_slope_correction_no_interior(self, simple_project):
        """Two pile tracker has no interior piles to correct."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1.01, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 10.0, 2, 1.02, 0.0)
        p1.height = 11.0
        p2.height = 11.0
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        tracker.create_segments()

        # Should run without error even with no interior piles
        slope_correction(tracker, simple_project)

        # Heights should be unchanged (no interior piles to adjust)
        assert tracker.piles[0].height == 11.0
        assert tracker.piles[1].height == 11.0


# =============================================================================
# EXTREME TERRAIN EDGE CASES
# =============================================================================


class TestExtremeTerrain:
    """Tests for extreme slope conditions."""

    def test_steep_positive_slope_clamped(self, simple_project):
        """Very steep upward terrain clamped to max_incline."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # 20m rise over 10m = 200% slope
        p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1.01, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 30.0, 2, 1.02, 0.0)
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        simple_project.add_tracker(tracker)

        target_height_line(tracker, simple_project)

        h0 = tracker.piles[0].height
        h1 = tracker.piles[1].height
        actual_slope = (h1 - h0) / 10.0

        # Should be clamped to 0.15
        assert actual_slope == pytest.approx(0.15, abs=0.001)

    def test_steep_negative_slope_clamped(self, simple_project):
        """Very steep downward terrain clamped to -max_incline."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # -20m rise over 10m = -200% slope
        p1 = TerrainFollowingPile(0.0, 0.0, 30.0, 1, 1.01, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 10.0, 2, 1.02, 0.0)
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        simple_project.add_tracker(tracker)

        target_height_line(tracker, simple_project)

        h0 = tracker.piles[0].height
        h1 = tracker.piles[1].height
        actual_slope = (h1 - h0) / 10.0

        # Should be clamped to -0.15
        assert actual_slope == pytest.approx(-0.15, abs=0.001)

    def test_perfectly_flat_terrain_zero_grading(self, simple_project):
        """Flat terrain should require no ground grading."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(5):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, 100 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        # No pile should be graded (flat terrain fits in window)
        for p in tracker.piles:
            assert p.final_elevation == p.initial_elevation

    def test_sawtooth_terrain_graded(self, simple_project):
        """Sawtooth pattern should be smoothed with grading."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        elevations = [10.0, 15.0, 10.0, 15.0, 10.0]
        for i, elev in enumerate(elevations):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, elev, i + 1, 400 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        # Interior piles may be graded to smooth the terrain
        # Just verify it completes and constraints are met
        for p in tracker.piles:
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6


# =============================================================================
# BOUNDARY CONDITION EDGE CASES
# =============================================================================


class TestBoundaryConditions:
    """Tests for piles at exact boundaries."""

    def test_pile_at_exact_min_boundary(self, simple_project):
        """Pile exactly at wmin is not a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 11.0  # Exactly at min
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 0

    def test_pile_at_exact_max_boundary(self, simple_project):
        """Pile exactly at wmax is not a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 12.0  # Exactly at max
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 0

    def test_pile_epsilon_below_min(self, simple_project):
        """Pile just below min is a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 10.999  # Just below min
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 1
        assert violations[0]["below_by"] < 0

    def test_pile_epsilon_above_max(self, simple_project):
        """Pile just above max is a violation."""
        window = [
            {
                "pile_in_tracker": 1,
                "grading_window_min": 11.0,
                "grading_window_max": 12.0,
            }
        ]
        tracker = TerrainFollowingTracker(tracker_id=1)
        p = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1, 0.0)
        p.height = 12.001  # Just above max
        tracker.add_pile(p)

        violations = check_within_window(window, tracker)
        assert len(violations) == 1
        assert violations[0]["above_by"] > 0


# =============================================================================
# SPACING EDGE CASES
# =============================================================================


class TestUnevenSpacing:
    """Tests for trackers with uneven pile spacing."""

    def test_very_short_segment(self, simple_project):
        """Very short segment (2m) should be handled correctly."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Spacing: 10m, 2m, 10m
        northings = [0.0, 10.0, 12.0, 22.0]
        for i, n in enumerate(northings):
            p = TerrainFollowingPile(n, 0.0, 10.0, i + 1, 200 + i, 0.0)
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        # Should complete without error
        for p in tracker.piles:
            assert p.final_elevation is not None

    def test_very_long_segment(self, simple_project):
        """Very long segment (100m) should be handled correctly."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # One very long segment
        northings = [0.0, 100.0, 110.0]
        for i, n in enumerate(northings):
            p = TerrainFollowingPile(n, 0.0, 10.0, i + 1, 300 + i, 0.0)
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        # Should complete without error
        for p in tracker.piles:
            assert p.final_elevation is not None

    def test_mixed_segment_lengths(self, simple_project):
        """Mixed segment lengths should be handled correctly."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Spacing: 5m, 50m, 3m, 20m
        northings = [0.0, 5.0, 55.0, 58.0, 78.0]
        for i, n in enumerate(northings):
            p = TerrainFollowingPile(n, 0.0, 10.0, i + 1, 500 + i, 0.0)
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        for p in tracker.piles:
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6


# =============================================================================
# CONSTRAINT EDGE CASES
# =============================================================================


class TestConstraintEdgeCases:
    """Tests for unusual constraint values."""

    def test_zero_max_incline(self, base_constraints):
        """Max incline of zero forces horizontal line."""
        base_constraints.max_incline = 0.0
        project = Project(
            name="FlatProject", project_type="terrain_following", constraints=base_constraints
        )

        tracker = TerrainFollowingTracker(tracker_id=1)
        # Ground has slope but max_incline = 0
        for i in range(5):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0 + i, i + 1, 600 + i, 0.0
            )
            tracker.add_pile(p)
        project.add_tracker(tracker)

        target_height_line(tracker, project)

        # All heights should be identical (zero slope)
        heights = [p.height for p in tracker.piles]
        assert all(h == pytest.approx(heights[0]) for h in heights)

    def test_narrow_window(self, base_constraints):
        """Very narrow reveal window should still work."""
        base_constraints.min_reveal_height = 1.0
        base_constraints.max_reveal_height = 1.1  # Only 0.1m window
        project = Project(
            name="NarrowWindow", project_type="terrain_following", constraints=base_constraints
        )

        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, 700 + i, 0.0
            )
            tracker.add_pile(p)
        project.add_tracker(tracker)

        main(project)

        # Should complete (may require more grading)
        for p in tracker.piles:
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 1.1 + 1e-6

    def test_wide_window(self, base_constraints):
        """Very wide reveal window should require minimal grading."""
        base_constraints.min_reveal_height = 0.5
        base_constraints.max_reveal_height = 3.0  # 2.5m window
        project = Project(
            name="WideWindow", project_type="terrain_following", constraints=base_constraints
        )

        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(5):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0 + i * 0.3, i + 1, 800 + i, 0.0
            )
            tracker.add_pile(p)
        project.add_tracker(tracker)

        main(project)

        # Wide window should mean no grading needed
        graded_count = sum(
            1 for p in tracker.piles if p.final_elevation != p.initial_elevation
        )
        assert graded_count == 0


# =============================================================================
# ANCHOR INVARIANT EDGE CASES
# =============================================================================


class TestAnchorInvariant:
    """Tests ensuring first and last piles are never graded."""

    def test_anchor_preserved_flat_terrain(self, simple_project):
        """Anchors preserved on flat terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(5):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0, i + 1, 900 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        first = tracker.get_first()
        last = tracker.get_last()

        assert abs(first.final_elevation - first.initial_elevation) < 1e-6
        assert abs(last.final_elevation - last.initial_elevation) < 1e-6

    def test_anchor_preserved_sloped_terrain(self, simple_project):
        """Anchors preserved on sloped terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(5):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 10.0 + i * 0.5, i + 1, 1000 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        first = tracker.get_first()
        last = tracker.get_last()

        assert abs(first.final_elevation - first.initial_elevation) < 1e-6
        assert abs(last.final_elevation - last.initial_elevation) < 1e-6

    def test_anchor_preserved_jagged_terrain(self, simple_project):
        """Anchors preserved even on jagged terrain."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        elevations = [10.0, 15.0, 8.0, 16.0, 10.0]
        for i, elev in enumerate(elevations):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, elev, i + 1, 1100 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        first = tracker.get_first()
        last = tracker.get_last()

        assert abs(first.final_elevation - first.initial_elevation) < 1e-6
        assert abs(last.final_elevation - last.initial_elevation) < 1e-6

    def test_anchor_preserved_steep_terrain(self, base_constraints):
        """Anchors preserved on steep terrain exceeding max_incline."""
        project = Project(
            name="SteepAnchor", project_type="terrain_following", constraints=base_constraints
        )
        tracker = TerrainFollowingTracker(tracker_id=1)
        # Very steep: 10m rise over 10m = 100% slope
        p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 1200, 0.0)
        p2 = TerrainFollowingPile(10.0, 0.0, 20.0, 2, 1201, 0.0)
        tracker.add_pile(p1)
        tracker.add_pile(p2)
        project.add_tracker(tracker)

        main(project)

        first = tracker.get_first()
        last = tracker.get_last()

        assert abs(first.final_elevation - first.initial_elevation) < 1e-6
        assert abs(last.final_elevation - last.initial_elevation) < 1e-6


# =============================================================================
# EXTREME VALUE EDGE CASES
# =============================================================================


class TestExtremeValues:
    """Tests for extreme coordinate and elevation values."""

    def test_very_high_elevation(self, simple_project):
        """Very high elevations should be handled."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, 1000.0, i + 1, 1300 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        for p in tracker.piles:
            assert p.final_elevation is not None
            assert p.total_height > 1000.0

    def test_negative_elevation(self, simple_project):
        """Negative elevations (below sea level) should be handled."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                float(i * 10), 0.0, -50.0, i + 1, 1400 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        for p in tracker.piles:
            assert p.final_elevation is not None
            reveal = p.total_height - p.final_elevation
            assert reveal >= 1.0 - 1e-6
            assert reveal <= 2.0 + 1e-6

    def test_large_northing_values(self, simple_project):
        """Large northing coordinates should be handled."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        for i in range(3):
            p = TerrainFollowingPile(
                1000000.0 + float(i * 10), 0.0, 10.0, i + 1, 1500 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        main(simple_project)

        for p in tracker.piles:
            assert p.final_elevation is not None

    def test_zero_northing_spacing(self, simple_project):
        """Piles at same northing now raises ValueError with clear message."""
        tracker = TerrainFollowingTracker(tracker_id=1)
        # All piles at same northing (collocated)
        for i in range(3):
            p = TerrainFollowingPile(
                0.0, float(i * 10), 10.0, i + 1, 1600 + i, 0.0
            )
            tracker.add_pile(p)
        simple_project.add_tracker(tracker)

        # Zero northing spacing now raises ValueError with descriptive message
        with pytest.raises(ValueError, match="identical northing"):
            target_height_line(tracker, simple_project)


# =============================================================================
# MULTI-TRACKER EDGE CASES
# =============================================================================


class TestMultiTrackerProject:
    """Tests for projects with multiple trackers."""

    def test_empty_project(self, simple_project):
        """Empty project (no trackers) should not crash."""
        main(simple_project)
        assert len(simple_project.trackers) == 0

    def test_many_trackers(self, simple_project):
        """Project with many trackers should be handled."""
        for tid in range(10):
            tracker = TerrainFollowingTracker(tracker_id=tid + 1)
            for i in range(3):
                p = TerrainFollowingPile(
                    float(i * 10),
                    float(tid * 100),
                    10.0,
                    i + 1,
                    float(tid * 100 + i + 1),
                    0.0,
                )
                tracker.add_pile(p)
            simple_project.add_tracker(tracker)

        main(simple_project)

        assert len(simple_project.trackers) == 10
        for tracker in simple_project.trackers:
            for p in tracker.piles:
                assert p.final_elevation is not None

    def test_trackers_with_different_pile_counts(self, simple_project):
        """Trackers with varying pile counts should be handled."""
        pile_counts = [2, 3, 5, 10, 3]
        for tid, count in enumerate(pile_counts):
            tracker = TerrainFollowingTracker(tracker_id=tid + 1)
            for i in range(count):
                p = TerrainFollowingPile(
                    float(i * 10),
                    float(tid * 100),
                    10.0,
                    i + 1,
                    float(tid * 100 + i + 1),
                    0.0,
                )
                tracker.add_pile(p)
            simple_project.add_tracker(tracker)

        main(simple_project)

        for tracker in simple_project.trackers:
            for p in tracker.piles:
                assert p.final_elevation is not None
