#!/usr/bin/env python3

from dataclasses import dataclass

@dataclass
class PileCoordinates:
    X: float
    Y: float
    Z: float
    poleTotal: int
    poleInTracker: int
