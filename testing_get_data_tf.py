#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict

import pandas as pd

from Project import Project
from ProjectConstraints import ProjectConstraints
from TerrainFollowingPile import TerrainFollowingPile
from TerrainFollowingTracker import TerrainFollowingTracker


def load_project_from_excel(
    *,
    excel_path: str,
    sheet_name: str,
    project_name: str,
    project_type: str,
    constraints: ProjectConstraints,
    piles_per_tracker: int = 10,
) -> Project:
    """
    Initialise a Project from an Excel sheet where tracker numbers are not provided.

    Assumptions:
      - Each tracker has exactly `piles_per_tracker` piles.
      - Columns are fixed by position:
          B (index 1): northing
          C (index 2): easting
          D (index 3): ground elevation (initial_elevation)
          E (index 4): pile in tracker (1..10)

    Trackers are assigned sequential IDs (1, 2, 3, ...) in the order they appear.
    """

    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

    # Column indices (0-based): B=1, C=2, D=3, E=4
    northing_col = df.columns[1]
    easting_col = df.columns[2]
    elevation_col = df.columns[3]
    pile_in_tracker_col = df.columns[4]

    # Keep only rows that have the required fields
    df = df.dropna(subset=[northing_col, easting_col, elevation_col, pile_in_tracker_col])

    # Coerce numeric (and drop any non-numeric leftovers)
    df[northing_col] = pd.to_numeric(df[northing_col], errors="coerce")
    df[easting_col] = pd.to_numeric(df[easting_col], errors="coerce")
    df[elevation_col] = pd.to_numeric(df[elevation_col], errors="coerce")
    df[pile_in_tracker_col] = pd.to_numeric(df[pile_in_tracker_col], errors="coerce")

    df = df.dropna(subset=[northing_col, easting_col, elevation_col, pile_in_tracker_col])

    project = Project(
        name=project_name,
        project_type=project_type,
        constraints=constraints,
    )

    trackers_by_id: Dict[int, TerrainFollowingTracker] = {}

    pile_global_id = 0
    tracker_id = 1

    for _, row in df.iterrows():
        pile_global_id += 1

        northing = float(row[northing_col])
        easting = float(row[easting_col])
        ground_z = float(row[elevation_col])
        pit = int(row[pile_in_tracker_col])

        # Create tracker if needed
        if tracker_id not in trackers_by_id:
            trackers_by_id[tracker_id] = TerrainFollowingTracker(tracker_id=tracker_id)

        trackers_by_id[tracker_id].piles.append(
            TerrainFollowingPile(
                northing=northing,
                easting=easting,
                initial_elevation=ground_z,
                pile_id=pile_global_id,  # global unique id (int)
                pile_in_tracker=pit,  # from column E
                flooding_allowance=0.0,
            )
        )

        # Advance tracker every N piles (your assumption)
        if pile_global_id % piles_per_tracker == 0:
            tracker_id += 1

    # Attach trackers in numeric order and sort their piles
    for tid in sorted(trackers_by_id.keys()):
        t = trackers_by_id[tid]
        t.sort_by_pole_position()  # sorts by pile_in_tracker
        project.trackers.append(t)

    return project


def to_excel(project: Project) -> None:
    rows = []

    for tracker in project.trackers:
        for pile in tracker.piles:
            rows.append(
                {
                    "tracker_id": tracker.tracker_id,
                    "pile_id": pile.pile_id,
                    "pile_in_tracker": pile.pile_in_tracker,
                    "northing": pile.northing,
                    "easting": pile.easting,
                    "initial_elevation": pile.initial_elevation,
                    "final_elevation": pile.final_elevation,
                    "change": pile.final_elevation - pile.initial_elevation,
                    "total_height": pile.total_height,
                    "total_revealed": pile.pile_revealed,
                }
            )

    df = pd.DataFrame(rows)

    output_path = "final_pile_elevations_for_tf.xlsx"
    df.to_excel(output_path, index=False)


# def main() -> None:
#     # -------------------------------
#     # Manual constraints (edit these)
#     # -------------------------------
#     constraints = ProjectConstraints(
#         min_reveal_height=1.375,
#         max_reveal_height=1.675,
#         pile_install_tolerance=0.0,
#         max_incline=0.15,
#         target_height_percantage=0.5,
#         max_angle_rotation=0.0,
#     )

#     # -------------------------------
#     # Load project from Excel
#     # -------------------------------
#     excel_path = "Punchs creek Flat Tracker Imperial-2.xlsm"  # change if needed
#     sheet_name = "Sheet1"  # change to your actual sheet name

#     project = load_project_from_excel(
#         excel_path=excel_path,
#         sheet_name=sheet_name,
#         project_name="Punchs_Creek",
#         project_type="standard",
#         constraints=constraints,
#     )

#     # Quick sanity prints
#     print(f"Loaded project: {project.name}")
#     print(f"Trackers: {len(project.trackers)}")
#     for t in project.trackers[:3]:
#         print(
#             f"  Tracker {t.tracker_id}: piles={t.pole_count}
#                  first_pit={t.piles[0].pile_in_tracker}"
#         )

#     # Now you can call your grading pipeline:
#     # main_grading(project)  # if you have a function named differently, call it here
