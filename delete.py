#!/usr/bin/env python3
from __future__ import annotations

import random

from PCL.Project import Project
from PCL.ProjectConstraints import ShadingConstraints
from PCL.shading.NorthSouth import NorthSouth
from PCL.BaseTracker import BaseTracker
from PCL.shading.EastWest import EastWest


def run_shading_demo() -> None:
    """
    Create a dummy project with 5 trackers and run shading analysis.
    """

    # -------------------------------------------------
    # 1. Define shading constraints
    # -------------------------------------------------
    constraints = ShadingConstraints(
        min_reveal_height=1.075,
        max_reveal_height=1.525,
        pile_install_tolerance=0.17,
        max_incline=0.10,
        max_angle_rotation=60.0,
        edge_overhang=0.3,
        azimuth_deg=180.0,  # south-facing sun
        sun_angle_deg=35.0,  # solar altitude
        zenith_deg=55.0,
        pitch=5.8,
        min_gap_btwn_end_modules=1.024,
        module_length=2.382,
        tracker_axis_angle=10.0,
    )

    # -------------------------------------------------
    # 2. Create project
    # -------------------------------------------------
    project = Project(
        name="Shading_Demo",
        project_type="standard",
        constraints=constraints,
        with_shading=True,
    )

    # -------------------------------------------------
    # 3. Create 5 dummy trackers
    # -------------------------------------------------
    for tid in range(1, 6):
        tracker = BaseTracker(tracker_id=tid)

        project.add_tracker(tracker)

    print(f"Project '{project.name}' created")
    print(f"Trackers: {len(project.trackers)}")

    # -------------------------------------------------
    # 4. Run North–South shading
    # -------------------------------------------------
    ns = NorthSouth(project.constraints)

    ns_shadow = ns.ns_shadow_length()
    ns_height_diff = ns.max_height_diff()
    ns_slope = ns.ns_slope()

    # -------------------------------------------------
    # 5. Print results
    # -------------------------------------------------
    print("\n--- North–South Shading Results ---")
    print(f"Azimuth (deg):           {ns.azimuth:.1f}")
    print(f"Sun angle (deg):         {ns.sun_angle:.1f}")
    print(f"Pitch (m):               {ns.pitch:.2f}")
    print(f"NS shadow length (m):    {ns_shadow:.3f}")
    print(f"Max height diff (m):     {ns_height_diff:.3f}")
    print(f"NS slope (%):            {ns_slope:.3f}")

    # -------------------------------------------------
    # 5. Run East–West shading
    # -------------------------------------------------
    ew = EastWest(project.constraints)
    ew_results = ew.full_ew()

    # -------------------------------------------------
    # 6. Print EW results
    # -------------------------------------------------
    print("\n--- East–West Shading Results ---")
    print(f"Azimuth (deg):                 {constraints.azimuth_deg:.1f}")
    print(f"Sun angle (deg):               {constraints.sun_angle_deg:.1f}")
    print(f"Zenith (deg):                  {constraints.zenith_deg:.1f}")
    print(f"Pitch (m):                     {constraints.pitch:.2f}")
    print(f"Module length (m):             {constraints.module_length:.2f}")
    print(f"EW shadow length (m):          {ew_results['shadow_length_m']:.3f}")
    print(f"Max tracking angle (deg):      {ew_results['max_tracking_angle_deg']:.2f}")
    print(f"Module height diff (m):        {ew_results['max_module_height_diff_m']:.3f}")
    print(f"Tracker module gap (m):        {ew_results['tracker_module_gap_m']:.3f}")
    print(f"Max pile height diff (m):      {ew_results['max_pile_height_diff_m']:.3f}")
    print(f"EW slope (%):                  {ew_results['max_slope_percent']:.3f}")


def main():
    run_shading_demo()


if __name__ == "__main__":
    run_shading_demo()
