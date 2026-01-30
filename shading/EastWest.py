#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from ProjectConstraints import ShadingConstraints


@dataclass
class EastWest:
    constraints: ShadingConstraints

    @property
    def azimuth(self) -> float:  # degrees
        return self.constraints.azimuth_deg

    @property
    def zenith(self) -> float:  # degrees
        return self.constraints.zenith_deg

    @property  #
    def tracker_axis_angle_max(self) -> float:  # degrees
        return self.constraints.tracker_axis_angle_max

    @property
    def sun_angle(self) -> float:  # degrees
        return self.constraints.sun_angle_deg

    @property
    def pitch(self) -> float:  # metres
        return self.constraints.pitch

    @property
    def module_length(self) -> float:  # metres
        return self.constraints.module_length

    @property
    def tracker_axis_angle(self) -> float:  # degrees
        return self.constraints.tracker_axis_angle

    def ew_shadow_length(self) -> float:  # metres
        max_shadow_length_mm = 1000 / math.tan((self.sun_angle))
        return abs(
            math.cos((90 - self.azimuth) * (math.pi / 180))
            * (max_shadow_length_mm / 1000)
        )

    def max_tracking_angle(self) -> float:  # degrees
        return abs(
            math.degrees(
                math.atan(
                    math.tan(math.radians(self.zenith))
                    * math.sin(math.radians(self.azimuth - self.tracker_axis_angle))
                )
            )
        )

    def max_module_height_diff(self) -> float:  # metres
        return math.sin(math.radians(self.tracker_axis_angle_max)) * self.module_length

    def ew_tracker_module_gap(self) -> float:  # metres
        return (
            self.pitch
            - math.cos(math.radians(self.tracker_axis_angle_max)) * self.module_length
        )

    def max_ew_pile_height_difference(self) -> float:  # metres
        return (
            self.ew_tracker_module_gap() / self.ew_shadow_length()
            - self.max_module_height_diff()
        )

    def max_slope_percentage(self) -> float:  # %
        return (self.max_ew_pile_height_difference() * 100) / self.pitch

    def full_ew(self) -> dict[str, float]:
        return {
            "ew_shadow_length": self.ew_shadow_length(),
            "max_tracking_angle_deg": self.max_tracking_angle(),
            "ew_max_module_height_diff": self.max_module_height_diff(),
            "ew_tracker_module_gap": self.ew_tracker_module_gap(),
            "ew_max_pile_height_diff": self.max_ew_pile_height_difference(),
            "ew_max_slope_percent": self.max_slope_percentage(),
        }
