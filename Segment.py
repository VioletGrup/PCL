#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from TerrainFollowingPile import TerrainFollowingPile


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

    def degree_of_deflection(self) -> float:
        """Angle of the segment relative to horizontal, in degrees."""
        s = self.slope()
        if math.isinf(s):
            return float("inf")
        return math.degrees(math.atan(s))
