#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List

from BasePile import BasePile
from TrackerABC import TrackerABC


@dataclass
class BaseTracker(TrackerABC):
    """
    Container for managing and analysing a collection of pile coordinates.

    Groups all of the `BasePile` objects under a single
    tracker ID and provides utilities for adding piles, sorting them by
    pole position, and extracting coordinate arrays for downstream
    analysis or plotting.

    Attributes
    ----------
    tracker_id : int
        Unique identifier for the tracker.
    piles : list[BasePile]
        List of piles associated with this tracker, ordered arbitrarily
        until explicitly sorted.
    """

    tracker_id: int
    piles: List[BasePile] = field(default_factory=list)
    # north_adjacent: bool  # optional
    # south_adjacent: bool  # optional
    # east_adjanct: bool  # optional
    # north_adjacent: bool  # optional

    # add tracker string

    def add_pile(self, pile: BasePile) -> None:
        """Add a pile to the tracker."""
        self.piles.append(pile)

    @property
    def distance_first_to_last_pile(self) -> float:
        """Returns the distance between the first and last pile in the tracker"""
        return abs(self.get_first().northing - self.get_last().northing)
