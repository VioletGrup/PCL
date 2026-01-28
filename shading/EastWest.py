#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from Project import Project
from TrackerABC import TrackerABC

from ..ProjectConstraints import ProjectConstraints, ShadingConstraints


@dataclass
class EastWest:
    constraints: ShadingConstraints

    def __init__(self, constraints: ProjectConstraints) -> None:
        if not constraints.with_shading:
            raise ValueError("EastWest shading analysis requires with_shading=True.")
        assert isinstance(constraints, ShadingConstraints)
        self.constraints = constraints

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

    def ew_shadow_length(self) -> float:  # millimeters
        max_shadow_length = 1000 / (math.tan(math.radians(self.sun_angle)))
        return math.cos(math.radians(90 - self.azimuth)) * (max_shadow_length / 1000)

    def max_idk(self, east_tracker: TrackerABC, west_tracker: TrackerABC) -> float:
        max_shadow_length = 1000 / (math.tan(math.radians(self.sun_angle)))
        ew_shadow_length = 
        day_max_tracking_angle = abs(
            math.atan(
                math.tan(self.zenith * (math.pi / 180))
                * math.sin((self.azimuth * (math.pi / 180)) - self.tracker_axis_angle_max)
            )
            * (math.pi / 180)
        )
        # module_height_diff = 0.0  #############################
        max_module_height_diff = (
            math.sin(day_max_tracking_angle * (math.pi / 180)) * self.module_length
        )
        tracker_module_gap = (
            self.pitch
            - math.cos(self.tracker_axis_angle_max * (math.pi * 180)) * self.module_length
        )
        max_height_diff = (tracker_module_gap / ew_shadow_length) - max_module_height_diff
        max_slope_percentage = (max_height_diff * 100) / self.pitch

        return max_slope_percentage
