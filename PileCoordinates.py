#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PileCoordinates:
    """
    Spatial coordinates and pole metadata for a single pile.

    Represents the three-dimensional position of a pile together with
    its identification and ordering information within a tracker.
    The final elevation is initialised to the initial elevation and
    may be modified later during grading optimisation.

    Attributes
    ----------
    northing : float
        Northing (Y-coordinate) of the pile.
    easting : float
        Easting (X-coordinate) of the pile.
    initial_elevation : float
        Original terrain or starting elevation (Z-coordinate).
    final_elevation : float
        Elevation after grading. Initialised to `initial_elevation`.
    pole_id : int
        Unique identifier for the pile.
    pole_in_tracker : int
        Index of this pile within its tracker (1-based).
    """

    northing: float
    easting: float
    initial_elevation: float
    pole_id: int
    pole_in_tracker: int
    flooding_allowance: float

    final_elevation: float = field(init=False)

    def __post_init__(self) -> None:
        """
        Initialise derived attributes and validate inputs.
        """
        # Initialise final elevation to initial elevation
        self.final_elevation = self.initial_elevation

        # Basic validation
        if self.pole_id < 0:
            raise ValueError("pole_id must be non-negative")
        if self.pole_in_tracker < 1:
            raise ValueError("pole_in_tracker must be >= 1")
