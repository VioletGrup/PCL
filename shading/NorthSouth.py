#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class NorthSouth:
    sun_angle: float  # degrees
    azimuth: float  # degrees

    def max_height_diff(self, min_gap_btwn_modules: float) -> float:
        max_shadow_length = 1000 / (math.tan(self.sun_angle))
        ns_shadow_length = math.sin((90 - self.azimuth) * (math.pi / 180)) * (
            max_shadow_length / 1000
        )
        max_module_height_diff = min_gap_btwn_modules / ns_shadow_length
        return max_module_height_diff
