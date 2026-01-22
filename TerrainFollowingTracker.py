#!/usr/bin/env python3

from dataclasses import dataclass, field
import math
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

    def validate_tracker_deflections(
        self,
        max_segment_deflection_deg: float,
        max_cumulative_deflection_deg: float,
    ) -> tuple[list[tuple[int, float]], float]:
        """
        Validate per-segment and cumulative tracker deflections.

        Returns
        -------
        violations : list[tuple[int, float]]
            (segment_id, abs_deflection_deg) for segments exceeding the limit.
        cumulative_abs_deflection_deg : float
            Sum of absolute deflection angles across all segments.
        """
        violations: list[tuple[int, float]] = []
        cumulative = 0.0

        for seg in self.segments:
            abs_deg = abs(seg.degree_of_deflection())
            cumulative += abs_deg

            if math.isinf(abs_deg) or abs_deg > max_segment_deflection_deg:
                violations.append((seg.segment_id, abs_deg))

        return violations, cumulative

    def ensure_tracker_deflections_ok(
        self,
        max_segment_deflection_deg: float,
        max_cumulative_deflection_deg: float,
    ) -> bool:
        """
        Return True if all tracker deflection constraints are satisfied.
        """
        violations, cumulative = self.validate_tracker_deflections(
            max_segment_deflection_deg,
            max_cumulative_deflection_deg,
        )

        return not violations and cumulative <= max_cumulative_deflection_deg
