#!/usr/bin/env python3

from dataclasses import dataclass, field
import math
from typing import List

from .BaseTracker import BaseTracker
from .Segment import Segment
from .TerrainFollowingPile import TerrainFollowingPile


@dataclass
class TerrainFollowingTracker(BaseTracker):
    piles: List[TerrainFollowingPile] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    north_wing_deflection: float = field(init=False, default=0.0)
    south_wing_deflection: float = field(init=False, default=0.0)

    def add_pile(self, pile: TerrainFollowingPile) -> None:
        """Add a pile to the tracker."""
        self.piles.append(pile)

    def create_segments(self) -> None:
        """Create segments between consecutive piles."""
        self.segments = []
        self.piles.sort(key=lambda p: p.pile_in_tracker)
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
    ) -> tuple[list[tuple[int, float]], float, float]:
        """
        Validate per-segment and per-wing cumulative tracker deflections.

        Wing logic
        ----------
        - We split at the centre pile (by pile_in_tracker index).
        - A segment belongs to a wing if BOTH its endpoints are on that side.
          (Segments that cross the centre shouldn't normally exist if piles are consecutive;
           but we handle it defensively.)

        Returns
        -------
        violations : list[tuple[int, float]]
            (segment_id, abs_deflection_deg) for segments exceeding per-segment limit.
        north_cumulative_abs_deflection_deg : float
            Sum of absolute deflections for the north wing.
        south_cumulative_abs_deflection_deg : float
            Sum of absolute deflections for the south wing.
        """
        violations: list[tuple[int, float]] = []

        centre = self.get_centre_pile().pile_in_tracker

        north_cum = 0.0
        south_cum = 0.0

        for seg in self.segments:
            abs_deg = abs(seg.segment_angle())

            # Per-segment violations
            if math.isinf(abs_deg) or abs_deg > max_segment_deflection_deg:
                violations.append((seg.segment_id, abs_deg))

            # Wing assignment (by endpoint positions)
            a = seg.start_pile.pile_in_tracker
            b = seg.end_pile.pile_in_tracker
            lo, hi = (a, b) if a <= b else (b, a)

            if hi <= centre:
                # Entirely on "south" side (lower pile_in_tracker indices up to centre)
                south_cum += abs_deg
            elif lo > centre:
                # Entirely on "north" side (strictly above centre)
                north_cum += abs_deg
            else:
                # Segment crosses centre (rare/shouldn't happen in consecutive pile segments)
                # Option A: split half-half
                half = 0.5 * abs_deg
                south_cum += half
                north_cum += half

        return violations, north_cum, south_cum

    def ensure_tracker_deflections_ok(
        self,
        max_segment_deflection_deg: float,
        max_cumulative_deflection_deg: float,
    ) -> bool:
        """
        Return True if:
          - no segment exceeds max_segment_deflection_deg, AND
          - each wing's cumulative abs deflection <= max_cumulative_deflection_deg
            (e.g. 4 deg north, 4 deg south)
        """
        violations, north_cum, south_cum = self.validate_tracker_deflections(
            max_segment_deflection_deg,
            max_cumulative_deflection_deg,
        )

        return (
            not violations
            and north_cum <= max_cumulative_deflection_deg
            and south_cum <= max_cumulative_deflection_deg
        )

    def get_centre_pile(self) -> TerrainFollowingPile:
        """
        Returns the pile in the centre of the tracker.
        Used to determine north and south wings
        """
        pile_in_tracker = math.floor(self.pole_count / 2)
        return self.get_pile_in_tracker(pile_in_tracker)

    def get_longest_segment(self) -> float:
        """Returns the length of the longest segment in the tracker"""
        if not self.segments:
            return 0.0

        return max(segment.length() for segment in self.segments)
