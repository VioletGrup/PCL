#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from ProjectConstraints import ProjectConstraints, ShadingConstraints


@dataclass
class NorthSouth:
    constraints: ShadingConstraints

    @property
    def azimuth(self) -> float:
        return self.constraints.azimuth_deg

    @property
    def pitch(self) -> float:
        return self.constraints.pitch

    @property
    def sun_angle(self) -> float:
        return self.constraints.sun_angle_deg

    @property
    def min_gap_btwn_end_modules(self) -> float:
        return self.constraints.min_gap_btwn_end_modules

    def ns_shadow_length(self) -> float:  # millimeters
        max_shadow_length = 1000 / (math.tan((self.sun_angle)))
        return abs(math.sin((90 - self.azimuth) * (math.pi / 180)) * (max_shadow_length / 1000))

    def max_height_diff(self) -> float:  # metres
        ns_shadow_length = self.ns_shadow_length()
        if ns_shadow_length == 0:
            ns_shadow_length = 1e-12  # stop division by zero
        max_module_height_diff = self.min_gap_btwn_end_modules / ns_shadow_length
        return abs(max_module_height_diff)

    def ns_slope(self) -> float:  # percentage
        return abs((self.max_height_diff() * 100) / self.min_gap_btwn_end_modules)

    def full_ns(self) -> dict[str, float]:
        shadow_length = self.ns_shadow_length()
        max_height_diff = self.max_height_diff()
        max_slope = self.ns_slope()

        return {
            "ns_max_shadow_length": shadow_length,
            "ns_max_height_diff": max_height_diff,
            "ns_max_slope": max_slope,
        }
