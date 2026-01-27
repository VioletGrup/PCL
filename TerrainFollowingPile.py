#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .BasePile import BasePile

if TYPE_CHECKING:
    from TerrainFollowingTracker import TerrainFollowingTracker


@dataclass
class TerrainFollowingPile(BasePile):
    """
    Terrain-following pile that stores incoming and outgoing segment angles.

    Angles are measured in degrees in the XY plane using atan2(dy, dx).
    """

    def get_incoming_segment_id(self) -> int:
        if self.pile_in_tracker == 1:
            return -1  # No incoming segment for first pile
        return self.pile_in_tracker - 1

    def get_outgoing_segment_id(self, tracker: TerrainFollowingTracker) -> int:
        if self.pile_in_tracker >= len(tracker.piles):
            return -1  # No outgoing segment for last pile
        return self.pile_in_tracker

    def degree_break(self, tracker: TerrainFollowingTracker) -> float:
        """Angle difference between adjacent torque tubes (deg)."""
        in_id = self.get_incoming_segment_id()
        out_id = self.get_outgoing_segment_id(tracker)
        if in_id == -1 or out_id == -1:
            return 0.0
        incoming = tracker.get_segment_by_id(in_id)
        outgoing = tracker.get_segment_by_id(out_id)
        return abs(outgoing.segment_angle() - incoming.segment_angle())
