#!/usr/bin/env python3

from dataclasses import dataclass


@dataclass
class PileCoordinates:
    """
    Spatial coordinates and pole metadata for a single pile.

    This class represents the three-dimensional position of a pile and
    its indexing information, including the total number of poles and
    the pile’s position within its parent tracker.

    Attributes
    ----------
    X : float
        X-coordinate of the pile.
    Y : float
        Y-coordinate of the pile.
    Z : float
        Z-coordinate of the pile.
    poleTotal : int
        Total number of poles associated with the tracker.
    poleInTracker : int
        Index or order of this pile within the tracker.
    """

    x: float
    y: float
    z: float
    pole_id: int
    pole_in_tracker: int
