#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict

import pandas as pd

from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints


def load_project_from_excel(
    *,
    excel_path: str,
    sheet_name: str,
    project_name: str,
    project_type: str,
    constraints: ProjectConstraints,
) -> Project:
    """
    Initialise a Project from an Excel sheet containing tracker + pile rows.

    Expected Excel columns (1-indexed as you described):
      - Col 1: tracker number
      - Col 3: pile in tracker
      - Col 4: easting
      - Col 5: northing
      - Col 9: ground elevation (initial_elevation)

    Pile ID is constructed as "tracker_number.pile_in_tracker" (string).
    Flooding allowance is set to 0 for all piles.
    """
    # Read raw sheet (no header assumptions)
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

    # Drop rows where tracker number is not numeric (e.g. headers like "Table")
    df = df[pd.to_numeric(df.iloc[:, 0], errors="coerce").notna()]

    # If your sheet has headers, we still use positional indexing by column number.
    # Convert to 0-based indexes:
    # col1->0, col3->2, col4->3, col5->4, col9->8
    tracker_col = df.columns[0]
    pile_in_tracker_col = df.columns[2]
    easting_col = df.columns[3]
    northing_col = df.columns[4]
    elevation_col = df.columns[8]

    # Drop rows missing essential fields (common with blank separators)
    df = df.dropna(
        subset=[tracker_col, pile_in_tracker_col, easting_col, northing_col, elevation_col]
    )

    project = Project(
        name=project_name,
        project_type=project_type,  # e.g. "standard"
        constraints=constraints,
    )

    trackers_by_id: Dict[int, BaseTracker] = {}

    for _, row in df.iterrows():
        tracker_num = int(row[tracker_col])
        pit = int(row[pile_in_tracker_col])

        easting = float(row[easting_col])
        northing = float(row[northing_col])
        ground_z = float(row[elevation_col])

        # Create tracker if needed
        if tracker_num not in trackers_by_id:
            trackers_by_id[tracker_num] = BaseTracker(tracker_id=tracker_num)

        pile_id = float(f"{tracker_num}.{pit}")

        trackers_by_id[tracker_num].piles.append(
            BasePile(
                northing=northing,
                easting=easting,
                initial_elevation=ground_z,
                pile_id=pile_id,  # NOTE: string id
                pile_in_tracker=pit,
                flooding_allowance=0.0,
            )
        )

    # Attach trackers in numeric order and sort their piles
    for tid in sorted(trackers_by_id.keys()):
        t = trackers_by_id[tid]
        t.sort_by_pole_position()
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

    output_path = "final_pile_elevations.xlsx"
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
