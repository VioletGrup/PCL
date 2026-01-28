#!/usr/bin/env python3
import pytest
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from terrainTrackerGrading import main, grading_window
from Project import Project
from ProjectConstraints import ProjectConstraints

@pytest.fixture
def base_constraints():
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
def complex_tracker():
    tracker = TerrainFollowingTracker(tracker_id=1)
    # Create a tracker with 10 piles on jagged terrain
    elevs = [10.0, 11.0, 10.5, 12.0, 11.5, 13.0, 12.0, 14.0, 13.0, 15.0]
    for i, z in enumerate(elevs):
        p = TerrainFollowingPile(float(i*10), 0.0, z, i+1, 500+i, 0.0)  # Fixed arg order: pile_in_tracker, pile_id
        tracker.add_pile(p)
    return tracker

def test_all_piles_within_window_after_grading(base_constraints, complex_tracker):
    """Requirement 1: All piles must be within their grading window after main() completes."""
    project = Project(name="WindowTest", project_type="terrain_following", constraints=base_constraints)
    project.add_tracker(complex_tracker)
    
    main(project)
    
    for pile in complex_tracker.piles:
        wmin = pile.true_min_height(project)
        wmax = pile.true_max_height(project)
        # Requirement: wmin <= height <= wmax
        # Note: pile.total_height is the final pile top elevation
        assert wmin <= pile.total_height + 1e-6, f"Pile {pile.pile_in_tracker} below window"
        assert pile.total_height <= wmax + 1e-6, f"Pile {pile.pile_in_tracker} above window"

def test_first_and_last_piles_no_grading(base_constraints, complex_tracker):
    """Requirement 2: First and last piles must not require ground grading (change == 0)."""
    project = Project(name="AnchorTest", project_type="terrain_following", constraints=base_constraints)
    project.add_tracker(complex_tracker)
    
    main(project)
    
    first = complex_tracker.get_first()
    last = complex_tracker.get_last()
    
    # Grading is defined as final_elevation != initial_elevation
    assert abs(first.final_elevation - first.initial_elevation) < 1e-6, "First pile was graded"
    assert abs(last.final_elevation - last.initial_elevation) < 1e-6, "Last pile was graded"

def test_first_and_last_piles_no_grading_steep_terrain(base_constraints):
    """Requirement 2: Even on steep terrain, first/last should remain un-graded (if possible)."""
    # Create ground slope of 0.3 (exceeds max_incline 0.15)
    tracker = TerrainFollowingTracker(tracker_id=1)
    p1 = TerrainFollowingPile(0.0, 0.0, 10.0, 1, 601, 0.0)
    p2 = TerrainFollowingPile(10.0, 0.0, 13.0, 2, 602, 0.0)
    tracker.add_pile(p1)
    tracker.add_pile(p2)
    
    project = Project(name="SteepAnchorTest", project_type="terrain_following", constraints=base_constraints)
    project.add_tracker(tracker)
    
    main(project)
    
    first = tracker.get_first()
    last = tracker.get_last()
    
    # Even though target line can't follow the ground slope perfectly, 
    # the anchors should ideally stay at ground level unless forced.
    assert abs(first.final_elevation - first.initial_elevation) < 1e-6, "First pile was graded on steep ground"
    assert abs(last.final_elevation - last.initial_elevation) < 1e-6, "Last pile was graded on steep ground"
