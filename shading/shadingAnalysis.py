#!/usr/bin/env python3

from PCL.Project import Project
from NorthSouth import NorthSouth
from EastWest import EastWest


#!/usr/bin/env python3

from Project import Project
from shading.NorthSouth import NorthSouth


def main(project: Project) -> tuple[dict[str, float], dict[str, float]]:
    ns = NorthSouth(project.constraints)
    ns_analysis = ns.full_ns

    ew = EastWest(project.constraints)
    ew_analysis = ew.full_ew

    return ns_analysis, ew_analysis
