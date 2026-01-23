#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ProjectType = Literal["standard", "terrain_following"]


@dataclass
class ProjectConstraints:
    """"""

    min_reveal_height: float
    max_reveal_height: float
    pile_install_tolerance: float
    max_incline: float  # rise/run
    max_angle_rotation: float  # degrees
    edge_overhang: float  # meters
    target_height_percantage: float = 0.5  # % of grading window

    # Terrain-following only (degrees)
    max_segment_deflection_deg: Optional[float] = None
    max_cumulative_deflection_deg: Optional[float] = None

    def validate(self, project_type: ProjectType) -> None:
        if self.min_reveal_height <= 0 or self.max_reveal_height <= 0:
            raise ValueError("min_reveal_height and max_reveal_height must be > 0.")
        if self.min_reveal_height >= self.max_reveal_height:
            raise ValueError("min_reveal_height must be < max_reveal_height.")
        if self.pile_install_tolerance < 0:
            raise ValueError("pile_install_tolerance must be >= 0.")
        if self.max_incline < 0:
            raise ValueError("max_incline must be >= 0 (rise/run).")

        if project_type == "terrain_following":
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
