#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from BasePile import BasePile


class TrackerABC(ABC):
    tracker_id: int
    piles: List[BasePile]

    @abstractmethod
    def add_pile(self, pile: BasePile) -> None:
        """Add a pile to the tracker."""

    def sort_by_pole_position(self) -> None:
        """Sort piles by pole position within the tracker."""
        self.piles.sort(key=lambda p: p.pile_in_tracker)

    @property
    def pole_count(self) -> int:
        """Total number of piles in this tracker."""
        return len(self.piles)

    @property
    def tracker_length(self) -> float:
        """Return the total length of the tracker"""  # overhangs?
        raise NotImplementedError("This function is not yet implemented.")

    def get_xyz(self) -> Tuple[list[float], list[float], list[float]]:
        """Return X, Y, Z arrays for plotting or analysis."""
        xs = [p.X for p in self.piles]
        ys = [p.Y for p in self.piles]
        zs = [p.Z for p in self.piles]
        return xs, ys, zs

    def get_first(self) -> BasePile:
        """Return north most pile in tracker"""
        return self.piles[0]

    def get_last(self) -> BasePile:
        """Return south most pile in tracker"""
        return self.piles[-1]

    def get_pile_in_tracker(self, pile_in_tracker: int) -> BasePile:
        """Return pile with specified pole_id"""
        for p in self.piles:
            if p.pile_in_tracker == pile_in_tracker:
                return p

        raise ValueError(
            f"Pile with pole_id {pile_in_tracker} not found in tracker {self.tracker_id}"
        )

    def get_northmost_pile(self) -> BasePile:
        """Return the northmost pile in this tracker"""
        if not self.piles:
            raise ValueError(f"Tracker {getattr(self, 'tracker_id', '?')} has no piles")

        return max(self.piles, key=lambda p: p.northing)

    def get_southmost_pile(self) -> BasePile:
        """Return the southmost pile in this tracker"""
        if not self.piles:
            raise ValueError(f"Tracker {getattr(self, 'tracker_id', '?')} has no piles")

        return min(self.piles, key=lambda p: p.northing)
