import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import flatTrackerGrading
from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints


def test_grading():
    print("Starting debug grading...")
    constraints = ProjectConstraints(
        min_reveal_height=1.2,
        max_reveal_height=3.2,
        pile_install_tolerance=0.2,
        max_incline=0.15,
        target_height_percantage=0.5,
        max_angle_rotation=0.0,
    )
    project = Project(name="Debug", project_type="standard", constraints=constraints)
    tracker = BaseTracker(tracker_id=1)

    # Add some dummy piles
    for i in range(1, 11):
        pile = BasePile(
            northing=i * 5.0,
            easting=0.0,
            initial_elevation=100.0 + (i % 3) * 0.1,
            pile_id=1.0 + i / 100.0,
            pile_in_tracker=i,
            flooding_allowance=0.0,
        )
        tracker.add_pile(pile)

    tracker.sort_by_pole_position()
    project.add_tracker(tracker)

    print("Running flatTrackerGrading.main...")
    flatTrackerGrading.main(project)
    print("Grading complete!")


if __name__ == "__main__":
    test_grading()
