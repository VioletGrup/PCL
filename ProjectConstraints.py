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


@dataclass
class ShadingConstraints(ProjectConstraints):
    """
    Extra constraints required when shading analysis is enabled.
    """

    # Solar position / shared shading inputs
    azimuth_deg: float = 0.0
    sun_angle_deg: float = 0.0  # solar altitude
    zenith_deg: Optional[float] = None

    # Geometry / tracker constraints used by shading analyses
    pitch: float = 0.0
    min_gap_btwn_end_modules: float = 0.0
    module_length: float = 0.0
    tracker_axis_angle: float = 0.0

    @property
    def tracker_axis_angle_max(self) -> float:
        """Alias for ProjectConstraints.max_angle_rotation (degrees)."""
        return self.max_angle_rotation

    def validate(self, project_type: ProjectType) -> None:
        super().validate(project_type)

        if not (0.0 <= self.azimuth_deg <= 360.0):
            raise ValueError("azimuth_deg must be in [0, 360].")
        if not (0.0 <= self.sun_angle_deg <= 90.0):
            raise ValueError("sun_angle_deg must be in [0, 90].")

        if self.pitch <= 0.0:
            raise ValueError("pitch must be > 0.")
        if self.min_gap_btwn_end_modules < 0.0:
            raise ValueError("min_gap_btwn_end_modules must be >= 0.")
        if self.module_length <= 0.0:
            raise ValueError("module_length must be > 0.")
