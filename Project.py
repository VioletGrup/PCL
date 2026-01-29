#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional, Type

from BasePile import BasePile
from BaseTracker import BaseTracker
from ProjectConstraints import ProjectConstraints, ShadingConstraints
from TerrainFollowingTracker import TerrainFollowingTracker
from TrackerABC import TrackerABC

ProjectType = Literal["standard", "terrain_following"]


@dataclass
class Project:
    """Project containing all trackers and constraints for a given solar farm"""

    name: str
    project_type: ProjectType
    constraints: ProjectConstraints
    with_shading: bool = False

    trackers: list[TrackerABC] = field(default_factory=list)

    _tracker_cls: Type[TrackerABC] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # choose tracker class
        if self.project_type == "standard":
            self._tracker_cls = TrackerABC  # type: ignore[assignment]
        else:
            self._tracker_cls = TerrainFollowingTracker  # type: ignore[assignment]

        # validate (including shading type checks)
        self.validate()

    def validate(self) -> None:
        # enforce correct constraints type
        if self.with_shading:
            if not isinstance(self.constraints, ShadingConstraints):
                raise ValueError(
                    "Project.with_shading=True requires constraints to be ShadingConstraints."
                )
        else:
            if isinstance(self.constraints, ShadingConstraints):
                raise ValueError(
                    "Project.with_shading=False requires constraints to be ProjectConstraints."
                )

        # validate numeric constraints
        self.constraints.validate(self.project_type)

    def new_tracker(self, tracker_id: int) -> TrackerABC:
        """Create a correctly-typed tracker for this project."""
        return self._tracker_cls(tracker_id)  # type: ignore[call-arg]

    def add_tracker(self, tracker: TrackerABC) -> None:
        self.trackers.append(tracker)

    @property
    def total_piles(self) -> int:
        return sum(t.pole_count for t in self.trackers)

    @property
    def max_piles_per_tracker(self) -> int:
        return max((t.pole_count for t in self.trackers), default=0)

    @property
    def max_cumulative_slope_change(self) -> float:
        if self.project_type != "terrain_following":
            return 0.0
        assert self.constraints.max_cumulative_deflection_deg is not None
        return math.tan(math.radians(self.constraints.max_cumulative_deflection_deg))

    @property
    def max_segment_slope_change(self) -> float:
        if self.project_type != "terrain_following":
            return 0.0
        return self.max_cumulative_slope_change / 6

    @property
    def max_strict_segment_slope_change(self) -> float:
        if self.project_type != "terrain_following":
            return 0.0
        assert self.constraints.max_segment_deflection_deg is not None
        x = math.tan(math.radians(self.constraints.max_segment_deflection_deg))
        return round(x, 4)

    @property
    def max_conservative_segment_slope_change(self) -> float:
        if self.project_type != "terrain_following":
            return 0.0
        x = self.max_cumulative_slope_change / 6
        return math.floor(x * 1000) / 1000

    def get_tracker_by_id(self, tracker_id: int) -> TrackerABC:
        for tracker in self.trackers:
            if tracker.tracker_id == tracker_id:
                return tracker
        raise ValueError(f"Tracker with tracker_id {tracker_id} not found in project.")

    def get_pile_by_id(self, pile_id: float) -> BasePile:
        tracker_id = math.floor(pile_id)
        pile_id_dec = Decimal(str(pile_id))
        pile_in_tracker = int((pile_id_dec % 1) * 100)
        return self.get_tracker_by_id(tracker_id).get_pile_in_tracker(pile_in_tracker)

    def get_trackers_on_easting(self, easting: float, ignore_ids: list[int]) -> list[TrackerABC]:
        same_easting: list[TrackerABC] = []
        for tracker in self.trackers:
            if tracker.tracker_id in ignore_ids:
                continue
            if tracker.get_first().easting == easting:
                same_easting.append(tracker)
        return same_easting

    def get_tracker_length(self, tracker_id: int) -> float:
        tracker = self.get_tracker_by_id(tracker_id)
        return tracker.distance_first_to_last_pile + (self.constraints.edge_overhang * 2)
