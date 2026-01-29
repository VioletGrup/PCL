#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from Project import Project
from TrackerABC import TrackerABC

from PCL.ProjectConstraints import ProjectConstraints, ShadingConstraints


@dataclass
class EastWest:
    constraints: ShadingConstraints

    @property
    def azimuth(self) -> float:
        return self.constraints.azimuth_deg

    @property
    def zenith(self) -> float:
        return self.constraints.zenith_degzenith

    @property
    def tracker_axis_angle_max(self) -> float:
        return self.constraints.tracker_axis_angle_max

    @property
    def sun_angle(self) -> float:
        return self.constraints.sun_angle_deg

    @property
    def pitch(self) -> float:
        return self.constraints.pitch

    @property
    def module_length(self) -> float:
        return self.constraints.module_length

    @property
    def tracker_axis_angle(self) -> float:
        return self.constraints.tracker_axis_angle

    def ew_shadow_length(self) -> float:  # millimeters
        max_shadow_length = 1000 / (math.tan(math.radians(self.sun_angle)))
        return math.cos(math.radians(90 - self.azimuth)) * (max_shadow_length / 1000)

    def max_tracking_angle(self) -> float:  # degrees
        return abs(
            math.atan(
                math.tan(self.zenith * (math.pi / 180))
                * math.sin((self.azimuth * (math.pi / 180)) - self.tracker_axis_angle)
            )
            * (math.pi / 180)
        )

    def max_module_height_diff(self) -> float:  # metres
        return math.sin(self.max_tracking_angle() * (math.pi / 180)) * self.module_length

    def ew_tracker_module_gap(self) -> float:  # metres
        return (
            self.pitch
            - math.cos(self.tracker_axis_angle_max * (math.pi * 180)) * self.module_length
        )

    def max_ew_pile_height_difference(self) -> float:  # metres
        return (
            self.ew_tracker_module_gap() / self.ew_shadow_length()
        ) - self.max_module_height_diff()

    def max_slope_percentage(self) -> float:  # %
        return (self.max_ew_pile_height_difference() * 100) / self.pitch

    def full_ew(self) -> dict[str, float]:
        shadow_length = self.ew_shadow_length()
        max_tracking_angle = self.max_tracking_angle()
        max_module_height_diff = self.max_module_height_diff()
        tracker_module_gap = self.tracker_module_gap()
        max_pile_height_diff = self.max_pile_height_diff()
        max_slope = self.ew_slope()

        return {
            "shadow_length_m": shadow_length,
            "max_tracking_angle_deg": max_tracking_angle,
            "max_module_height_diff_m": max_module_height_diff,
            "tracker_module_gap_m": tracker_module_gap,
            "max_pile_height_diff_m": max_pile_height_diff,
            "max_slope_percent": max_slope,
        }
