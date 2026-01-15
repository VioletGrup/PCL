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

    def create_segments(self) -> None:
        """Create segments between consecutive piles."""
        self.segments = []
        for i in range(len(self.piles) - 1):
            segment = Segment(
                start_pile=self.piles[i], end_pile=self.piles[i + 1], segment_id=i + 1
            )
            self.segments.append(segment)

    def get_segment_by_id(self, segment_id: int) -> Segment:
        """Return segment with specified segment_id"""
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        raise ValueError(f"Segment with ID {segment_id} not found.")
