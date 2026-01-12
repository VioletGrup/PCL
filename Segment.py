#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from Project import Project
from TerrainFollowingPile import TerrainFollowingPile


@dataclass
class Segment:
    """Segment between two piles."""

    start_pile: TerrainFollowingPile
    end_pile: TerrainFollowingPile

    def length(self) -> float:
        return math.hypot(
            self.start_pile.easting - self.end_pile.easting,
            self.start_pile.northing - self.end_pile.northing,
        )

    def slope(self) -> float:
        """Return the slope (rise/run) of the segment."""
        run = self.length()
        if run == 0:
            return float("inf")
        rise = self.end_pile.current_elevation - self.start_pile.current_elevation
        return rise / run

    def max_vertical_movement(self, project: Project) -> float:
        """Return the maximum vertical movement based on the projects max segment deflection"""
        angle = math.radians(project.constraints.max_segment_deflection_deg)
        return math.tan(angle) * self.length()
