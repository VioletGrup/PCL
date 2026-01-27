#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from .TerrainFollowingPile import TerrainFollowingPile


@dataclass
class Segment:
    """Segment between two piles."""

    segment_id: int
    start_pile: TerrainFollowingPile
    end_pile: TerrainFollowingPile

    def length(self) -> float:
        """Returns the length of the segment ie. distance between piles"""
        return math.hypot(
            self.start_pile.easting - self.end_pile.easting,
            self.start_pile.northing - self.end_pile.northing,
        )

    def slope(self) -> float:
        """Return the slope (rise/run) of the segment."""
        run = self.length()
        if run == 0:
            return float("inf")
        rise = self.end_pile.height - self.start_pile.height
        return rise / run

    def height_difference(self) -> float:
        """Return the height difference between the start and end piles, -ve if the start pile is
        higher than the last pile."""
        return self.start_pile.height - self.end_pile.height

    def segment_angle(self) -> float:
        """Absolute tube angle relative to horizontal (deg)."""
        run = self.length()
        if run == 0:
            return float("inf")
        rise = self.end_pile.height - self.start_pile.height
        return math.degrees(math.atan2(rise, run))  # atan2 is a bit safer
