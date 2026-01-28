#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict

import pandas as pd

from .Project import Project
from .ProjectConstraints import ProjectConstraints
from .TerrainFollowingPile import TerrainFollowingPile
from .TerrainFollowingTracker import TerrainFollowingTracker


def load_project_from_excel(
    *,
    excel_path: str,
    sheet_name: str,
    project_name: str,
    project_type: str,
    constraints: ProjectConstraints,
) -> Project:
    """
    Initialise a Project from an Excel sheet with columns like:

        Point | Northing | Easting | Elevation | Description | Frame
                 B          C          D           E            F

    Where:
      - Description = pile_in_tracker
      - Frame       = tracker_id
      - pile_id     = "tracker_id.pile_in_tracker" (string)

    Notes:
      - Trackers are created based on the 'Frame' value.
      - Piles within each tracker are sorted by pile_in_tracker.
    """

    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

    # Prefer header names; fall back to fixed positions if needed
    cols = {c.strip(): c for c in df.columns if isinstance(c, str)}

    def _col(name: str, fallback_idx: int):
        return cols.get(name, df.columns[fallback_idx])

    northing_col = _col("Northing", 1)  # B
    easting_col = _col("Easting", 2)  # C
    elevation_col = _col("Elevation", 3)  # D
    pile_in_tracker_col = _col("Description", 4)  # E
    tracker_id_col = _col("Frame", 5)  # F

    # Keep only rows that have the required fields
    df = df.dropna(
        subset=[
            northing_col,
            easting_col,
            elevation_col,
            pile_in_tracker_col,
            tracker_id_col,
        ]
    )

    # Coerce numeric (and drop any non-numeric leftovers)
    df[northing_col] = pd.to_numeric(df[northing_col], errors="coerce")
    df[easting_col] = pd.to_numeric(df[easting_col], errors="coerce")
    df[elevation_col] = pd.to_numeric(df[elevation_col], errors="coerce")
    df[pile_in_tracker_col] = pd.to_numeric(df[pile_in_tracker_col], errors="coerce")
    df[tracker_id_col] = pd.to_numeric(df[tracker_id_col], errors="coerce")

    df = df.dropna(
        subset=[
            northing_col,
            easting_col,
            elevation_col,
            pile_in_tracker_col,
            tracker_id_col,
        ]
    )

    project = Project(
        name=project_name,
        project_type=project_type,
        constraints=constraints,
    )

    trackers_by_id: Dict[int, TerrainFollowingTracker] = {}

    for _, row in df.iterrows():
        tracker_id = int(row[tracker_id_col])
        pit = int(row[pile_in_tracker_col])

        northing = float(row[northing_col])
        easting = float(row[easting_col])
        ground_z = float(row[elevation_col])

        # Create tracker if needed
        if tracker_id not in trackers_by_id:
            trackers_by_id[tracker_id] = TerrainFollowingTracker(tracker_id=tracker_id)

        pile_id = float(f"{tracker_id}.{pit}")

        trackers_by_id[tracker_id].piles.append(
            TerrainFollowingPile(
                northing=northing,
                easting=easting,
                initial_elevation=ground_z,
                pile_id=pile_id,  # string id "tracker.pile"
                pile_in_tracker=pit,  # from Description
                flooding_allowance=0.0,
            )
        )

    # Attach trackers in numeric order and sort their piles
    for tid in sorted(trackers_by_id.keys()):
        t = trackers_by_id[tid]
        t.sort_by_pole_position()  # sorts by pile_in_tracker
        project.trackers.append(t)

    return project


def to_excel(project: Project, output_path: str = "PCL/final_pile_elevations_for_tf.xlsx") -> None:
    rows = []

    for tracker in project.trackers:
        for pile in tracker.piles:
            rows.append(
                {
                    "tracker_id": tracker.tracker_id,
                    "pile_id": pile.pile_id,  # "tracker.pile"
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

    pd.DataFrame(rows).to_excel(output_path, index=False)
