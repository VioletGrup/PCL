#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field

from Project import Project


@dataclass
class BasePile:
    """


    Attributes
    ----------

    """

    northing: float
    easting: float
    initial_elevation: float
    pile_id: float
    pile_in_tracker: int
    flooding_allowance: float

    current_elevation: float = field(init=False)
    final_elevation: float = field(init=False)

    def __post_init__(self) -> None:
        """
        Initialise derived attributes and validate inputs.
        """
        # Initialise current final elevation to initial elevation
        self.final_elevation = self.initial_elevation
        self.current_elevation = self.initial_elevation

        # Basic validation
        if self.pile_id < 0:
            raise ValueError("pile_id must be non-negative")
        if self.pile_in_tracker < 1:
            raise ValueError("pile_in_tracker must be >= 1")
        if self.flooding_allowance < 0:
            raise ValueError("flooding_allowance must be non-negative")

    def set_current_elevation(self, elevation: float) -> None:
        """Set the current elevation of the pile during installation simulation."""
        self.current_elevation = elevation

    def set_final_elevation(self, elevation: float) -> None:
        """Set the final elevation of the pile after installation simulation."""
        self.final_elevation = elevation

    def true_min_height(self, project: Project) -> float:
        """Return the true minimum height of the pile including flooding allowance and tolerance."""
        return (
            self.current_elevation
            + self.flooding_allowance
            + project.constraints.pile_install_tolerance / 2
        )

    def true_max_height(self, project: Project) -> float:
        """Return the true maximum height of the pile including tolerance."""
        return self.current_elevation - project.constraints.pile_install_tolerance / 2

    def pile_at_target_height(self, project: Project) -> float:
        """Return the target height of the pile based on the grading window percentage."""
        grading_window = self.true_max_height(project) - self.true_min_height(project)
        return self.true_min_height(project) + (
            grading_window * project.constraints.target_height_percantage / 100
        )
