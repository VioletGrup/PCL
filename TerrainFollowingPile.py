#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

from BasePile import BasePile


@dataclass
class TerrainFollowingPile(BasePile):
    """
    Terrain-following pile that stores incoming and outgoing segment angles.

    Angles are measured in degrees in the XY plane using atan2(dy, dx).
    """

    incoming_pile: TerrainFollowingPile
    outgoing_pileincoming_pile: TerrainFollowingPile
