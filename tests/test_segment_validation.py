#!/usr/bin/env python3
"""
Test to verify that the entire segment (not just piles) remains within the grading window.
"""

import pytest
import math
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker
from terrainTrackerGrading import main
from Project import Project
from ProjectConstraints import ProjectConstraints

@pytest.fixture
def project():
    constraints = ProjectConstraints(
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
    return Project(name="SegmentTest", project_type="terrain_following", constraints=constraints)

def interpolate_ground(p1, p2, t):
    """Linearly interpolate ground elevation at fraction t."""
    return p1.final_elevation + t * (p2.final_elevation - p1.final_elevation)

def interpolate_segment_height(p1, p2, t):
    """Linearly interpolate segment height at fraction t."""
    return p1.height + t * (p2.height - p1.height)

def test_segments_within_grading_window(project):
    """
    Verify that points along the segments connecting piles remain within the grading window.
    
    The grading window is defined relative to the ground.
    Ground is assumed to be linearly interpolated between piles.
    """
    tracker = TerrainFollowingTracker(tracker_id=1)
    
    # Create undulating terrain
    # Piles at 0, 10, 20, 30
    # Ground at 10, 12, 11, 13
    piles_data = [
        (1, 0.0, 10.0),
        (2, 10.0, 12.0),
        (3, 20.0, 11.0),
        (4, 30.0, 13.0)
    ]
    
    for pid, north, elev in piles_data:
        p = TerrainFollowingPile(north, 0.0, elev, pid, pid, 0.0)  # pile_in_tracker, pile_id both use pid
        tracker.add_pile(p)
        
    project.add_tracker(tracker)
    
    main(project)
    
    tracker.create_segments()
    
    # Check 10 points along each segment
    for segment in tracker.segments:
        p1 = segment.start_pile
        p2 = segment.end_pile
        
        for i in range(11): # 0.0 to 1.0
            t = i / 10.0
            
            ground_z = interpolate_ground(p1, p2, t)
            segment_z = interpolate_segment_height(p1, p2, t)
            
            reveal = segment_z - ground_z
            
            # Allow for very small floating point errors
            assert reveal >= project.constraints.min_reveal_height - 1e-6, \
                f"Segment {int(segment.segment_id)} at t={t} dips below min reveal. Reveal={reveal}"
                
            assert reveal <= project.constraints.max_reveal_height + 1e-6, \
                f"Segment {int(segment.segment_id)} at t={t} goes above max reveal. Reveal={reveal}"
