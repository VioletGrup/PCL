#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional, Type, TypeVar

from .BasePile import BasePile
from .BaseTracker import BaseTracker
from .ProjectConstraints import ProjectConstraints
from .TerrainFollowingTracker import TerrainFollowingTracker
from .TrackerABC import TrackerABC

T = TypeVar("T", bound=BaseTracker)
ProjectType = Literal["standard", "terrain_following"]


@dataclass
class Project:
    """Project containing all trackers and constraints for a given solar farm"""

    name: str
    project_type: ProjectType
    constraints: ProjectConstraints

    trackers: list[TrackerABC] = field(default_factory=list)

    # factory types (set in __post_init__)
    _tracker_cls: Type[TrackerABC] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.constraints.validate(self.project_type)

        if self.project_type == "standard":
            self._tracker_cls = TrackerABC  # type: ignore[assignment]
        else:
            self._tracker_cls = TerrainFollowingTracker  # type: ignore[assignment]

    def new_tracker(self, tracker_id: int) -> TrackerABC:
        """Create a correctly-typed tracker for this project."""
        return self._tracker_cls(tracker_id)  # type: ignore[call-arg]

    def add_tracker(self, tracker: TrackerABC) -> None:
        """
        Add a new tracker to the project

        BaseTracker for standard projects
        TerrainFollowingTracker for terrain following projects
        """
        self.trackers.append(tracker)

    @property
    def total_piles(self) -> int:
        """Return the total number of piles in the solar farm"""
        return sum(t.pole_count for t in self.trackers)

    @property
    def max_piles_per_tracker(self) -> int:
        """Return the maximum number of piles in a tracker"""
        return max((t.pole_count for t in self.trackers), default=0)

    @property
    def max_cumulative_slope_change(self) -> float:
        """
        Maximum cumulative slope change (rise/run).

        Terrain-following: tan((max_cumulative_deflection_deg * pi)/180)
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0

        assert self.constraints.max_cumulative_deflection_deg is not None
        return math.tan(
            (self.constraints.max_cumulative_deflection_deg * math.pi) / 180
        )

    @property
    def max_segment_slope_change(self) -> float:
        """
        Maximum per-segment slope change (rise/run).

        Terrain-following: max_cumulative_slope_change / 6
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0
        # degrees -> slope ratio

        assert self.max_cumulative_slope_change is not None
        return self.max_cumulative_slope_change / 6

    @property
    def max_strict_segment_slope_change(self) -> float:
        """
        Maximum per-segment slope change (rise/run).
        Used when verifying that individual segments do not exceed allowable deflection.

        Terrain-following: tan((max_segment_deflection_deg * pi)/180))
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0
        # degrees -> slope ratio

        assert self.max_cumulative_slope_change is not None
        x = math.tan((self.constraints.max_segment_deflection_deg * math.pi) / 180)
        x *= 10000  # round final value to 4 decimal places
        x = round(x)
        return x / 10000

    @property
    def max_conservative_segment_slope_change(self) -> float:
        """
        Conservative maximum per-segment slope change (rise/run).
        Used when updating pile heights, ensures that the sum of all deflections in a
        tracker will be within the allowable range

        Terrain-following: max_cumulative_slope_change / 6
        Standard: 0.0
        """
        if self.project_type != "terrain_following":
            return 0.0
        # degrees -> slope ratio

        assert self.max_cumulative_slope_change is not None
        x = self.max_cumulative_slope_change / 6
        x *= 1000  # round down final value to 3 decimal places
        return math.floor(x) / 1000

    def get_tracker_by_id(self, tracker_id: int) -> Optional[TrackerABC]:
        """Return tracker with specified tracker_id"""
        for tracker in self.trackers:
            if tracker.tracker_id == tracker_id:
                return tracker
        raise ValueError(f"Tracker with tracker_id {tracker_id} not found in project.")

    def get_pile_by_id(self, pile_id: float) -> Optional[BasePile]:
        """Return pile with specified pile_id"""
        # eg. pile_id = 13.24
        tracker_id = math.floor(pile_id)  # 13

        pile_id_dec = Decimal(str(pile_id))
        pile_in_tracker = int((pile_id_dec % 1) * 100)  # 24

        return self.get_tracker_by_id(tracker_id).get_pile_in_tracker(pile_in_tracker)
        # raises ValueError if not found

    def get_trackers_on_easting(
        self, easting: float, ignore_ids: list[int]
    ) -> list[TrackerABC]:
        """Returns all the trackers with the same easting"""
        same_easting = []
        for tracker in self.trackers:
            if tracker.tracker_id in ignore_ids:
                continue  # early exit
            if tracker.get_first().easting == easting:
                same_easting.append(tracker)
        return same_easting

    def get_tracker_length(self, tracker_id: int) -> float:
        """Returns the length of a given tracker, including the overhangs off the edge piles"""
        tracker = self.get_tracker_by_id(tracker_id)
        return tracker.distance_first_to_last_pile + (
            self.constraints.edge_overhang * 2
        )
