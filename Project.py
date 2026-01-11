#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from Tracker import Tracker

ProjectType = Literal["standard", "terrain_following"]


@dataclass
class Project:
    """
    A solar project containing many trackers plus grading/design constraints.

    User-defined constraints
    ------------------------
    min_height : float
        Minimum allowable pile height above ground (m).
    max_height : float
        Maximum allowable pile height above ground (m).
    pile_install_tolerance : float
        Installation tolerance (+/-) applied to the height window (m).
    max_incline : float
        Maximum allowable tracker incline as rise/run (e.g., 0.15 for 15%).

    Terrain-following only
    ----------------------
    max_segment_deflection_deg : float | None
        Maximum allowed change per segment (degrees). Required if project_type is
        "terrain_following".
    max_cumulative_deflection_deg : float | None
        Maximum cumulative allowed change (degrees). Required if project_type is
        "terrain_following".

    Derived properties computed from trackers/constraints
    -----------------------------------------------------
    max_piles_per_tracker : int
        Max number of piles found in any tracker in this project.
    max_segment_slope_change : float
        For terrain-following: tan(max_segment_deflection_deg) (rise/run).
        For standard: 0.0
    max_cumulative_slope_change : float
        For terrain-following: tan(max_cumulative_deflection_deg) (rise/run).
        For standard: 0.0
    """

    name: str
    project_type: ProjectType

    # User-defined constraints (always required)
    min_height: float
    max_height: float
    pile_install_tolerance: float
    max_incline: float
    target_height: float  # percentage of grading window
    max_angle_rotation: float
    tolerance: float

    # Terrain-following only (degrees)
    max_segment_deflection_deg: Optional[float] = None
    max_cumulative_deflection_deg: Optional[float] = None

    trackers: List[Tracker] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Basic validation
        if self.min_height <= 0 or self.max_height <= 0:
            raise ValueError("min_height and max_height must be > 0.")
        if self.min_height >= self.max_height:
            raise ValueError("min_height must be < max_height.")
        if self.pile_install_tolerance < 0:
            raise ValueError("pile_install_tolerance must be >= 0.")
        if self.max_incline < 0:
            raise ValueError("max_incline must be >= 0 (rise/run).")

        if self.project_type == "terrain_following":
            if (
                self.max_segment_deflection_deg is None
                or self.max_cumulative_deflection_deg is None
            ):
                raise ValueError(
                    "Terrain-following projects require max_segment_deflection_deg and "
                    "max_cumulative_deflection_deg."
                )
            if self.max_segment_deflection_deg < 0 or self.max_cumulative_deflection_deg < 0:
                raise ValueError("Deflection degrees must be >= 0.")

    def add_tracker(self, tracker: Tracker) -> None:
        """Add a tracker to the project."""
        self.trackers.append(tracker)

    @property
    def total_piles(self) -> int:
        """
        Total number of piles across all trackers in the project.
        """
        return sum(t.pole_count for t in self.trackers)

    @property
    def max_piles_per_tracker(self) -> int:
        """Maximum pile count across all trackers."""
        if not self.trackers:
            return 0
        return max(t.pole_count for t in self.trackers)

    @property
    def max_cumulative_slope_change(self) -> float:
        """
        Maximum cumulative slope change (rise/run).

        Terrain-following: tan((max_cumulative_deflection_deg * pi)/180)
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0

        assert self.max_cumulative_deflection_deg is not None
        return math.tan((self.max_cumulative_deflection_deg * math.pi) / 180)

    @property
    def max_segment_slope_change(self) -> float:
        """
        Maximum per-segment slope change (rise/run).

        Terrain-following: max_cumulative_slope_change / 6
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0
        # degrees -> slope ratio

        assert self.max_cumulative_slope_change is not None
        return self.max_cumulative_slope_change / 6
