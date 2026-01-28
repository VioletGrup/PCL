#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from Project import Project
from TrackerABC import TrackerABC

from ..ProjectConstraints import ProjectConstraints, ShadingConstraints


@dataclass
class EastWest:
    azimuth: float  # degrees
    zenith: float  # degrees
    tracker_axis_angle_max: float  # degrees
    sun_angle: float  # degrees
    project: Project
    pitch: float

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

    def max_idk(self, east_tracker: TrackerABC, west_tracker: TrackerABC) -> float:
        max_shadow_length = 1000 / (math.tan(self.sun_angle))
        ew_shadow_length = math.cos((90 - self.azimuth) * (math.pi / 180)) * (
            max_shadow_length / 1000
        )
        day_max_tracking_angle = abs(
            math.atan(
                math.tan(self.zenith * (math.pi / 180))
                * math.sin((self.azimuth * (math.pi / 180)) - self.tracker_axis_angle_max)
            )
            * (math.pi / 180)
        )
        length = self.project.get_tracker_length(east_tracker.tracker_id)
        module_height_diff = 0.0  #############################
        max_module_height_diff = math.sin(day_max_tracking_angle * (math.pi / 180)) * length
        tracker_module_gap = (
            self.pitch - math.cos(self.tracker_axis_angle_max * (math.pi * 180)) * length
        )
        max_height_diff = (tracker_module_gap / ew_shadow_length) - module_height_diff
        max_slope_percentage = (max_height_diff * 100) / self.pitch

        return max_slope_percentage
