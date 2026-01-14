#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List

from BaseTracker import BaseTracker
from Segment import Segment
from TerrainFollowingPile import TerrainFollowingPile


@dataclass
class TerrainFollowingTracker(BaseTracker):
    piles: List[TerrainFollowingPile] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)

    def add_pile(self, pile: TerrainFollowingPile) -> None:
        """Add a pile to the tracker."""
        self.piles.append(pile)
