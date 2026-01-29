#!/usr/bin/env python3

from PCL.Project import Project
from NorthSouth import NorthSouth
from EastWest import EastWest


#!/usr/bin/env python3

from Project import Project
from shading.NorthSouth import NorthSouth


def main(project: Project) -> None:
    ns = NorthSouth(project.constraints)
    ns_shadow_length, ns_max_height_diff, ns_max_slope = ns.full_ns

    ew = EastWest(project.constraints)
    (
        ew_shadow_length,
        max_tracking_angle,
        ew_max_module_height_diff,
        ew_tracker_module_gap,
        ew_max_pile_height_diff,
        ew_max_slope,
    ) = ew.full_ew
    return
