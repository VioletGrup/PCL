#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List

from PileCoordinates import PileCoordinates


@dataclass
class Tracker:
    """
    Container for managing and analysing a collection of pile coordinates.

    Groups all of the `PileCoordinates` objects under a single
    tracker ID and provides utilities for adding piles, sorting them by
    pole position, and extracting coordinate arrays for downstream
    analysis or plotting.

    Attributes
    ----------
    tracker_id : int
        Unique identifier for the tracker.
    piles : list[PileCoordinates]
        List of piles associated with this tracker, ordered arbitrarily
        until explicitly sorted.
    """

    tracker_id: int
    piles: List[PileCoordinates] = field(default_factory=list)
    # north_adjacent: bool  # optional
    # south_adjacent: bool  # optional
    # east_adjanct: bool  # optional
    # north_adjacent: bool  # optional

    # add tracker string

    def add_pile(self, pile: PileCoordinates) -> None:
        """Add a pile to the tracker."""
        self.piles.append(pile)

    def sort_by_pole_position(self) -> None:
        """Sort piles by pole position within the tracker."""
        self.piles.sort(key=lambda p: p.poleInTracker)

    @property
    def pole_count(self) -> int:
        """Total number of piles in this tracker."""
        return len(self.piles)

    @property
    def tracker_length(self) -> float:
        """Return the total length of the tracker"""  # overhangs?
        raise NotImplementedError("This function is not yet implemented.")

    def get_xyz(self):
        """Return X, Y, Z arrays for plotting or analysis."""
        xs = [p.X for p in self.piles]
        ys = [p.Y for p in self.piles]
        zs = [p.Z for p in self.piles]
        return xs, ys, zs

    def get_first(self):
        """Return north most pile in tracker"""
        return min(self.piles, key=lambda p: p.pole_in_tracker)

    def get_last(self):
        """Return south most pile in tracker"""
        return max(self.piles, key=lambda p: p.pole_in_tracker)
