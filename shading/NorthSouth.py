#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from PCL.ProjectConstraints import ProjectConstraints, ShadingConstraints


@dataclass
class NorthSouth:
    constraints: ShadingConstraints

    def __init__(self, constraints: ProjectConstraints) -> None:
        if not constraints.with_shading:
            raise ValueError("NorthSouth shading analysis requires with_shading=True.")
        assert isinstance(constraints, ShadingConstraints)
        self.constraints = constraints

    @property
    def azimuth(self) -> float:
        return self.constraints.azimuth_deg

    @property
    def pitch(self) -> float:
        return self.constraints.pitch

    @property
    def sun_angle(self) -> float:
        return self.constraints.sun_angle

    @property
    def min_gap_btwn_end_modules(self) -> float:
        return self.constraints.min_gap_btwn_end_modules

    def ns_shadow_length(self) -> float:  # millimeters
        max_shadow_length = 1000 / (math.tan(self.sun_angle))
        return math.sin((90 - self.azimuth) * (math.pi / 180)) * (max_shadow_length / 1000)

    def max_height_diff(self) -> float:  # metres
        ns_shadow_length = self.ns_shadow_length()
        max_module_height_diff = self.min_gap_btwn_end_modules / ns_shadow_length
        return max_module_height_diff

    def ns_slope(self) -> float:  # percentage
        return (self.max_height_diff() * 100) / self.min_gap_btwn_end_modules
