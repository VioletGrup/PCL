#!/usr/bin/env python3

from NorthSouth import NorthSouth

from TrackerABC import TrackerABC


def main(ns: NorthSouth) -> list[tuple[int, int, float]]:
    analysed_tracker_ids = []  # keep a list of tracker ids that have already been analysed
    violating_trackers = []
    for tracker in ns.project.trackers:
        if tracker.tracker_id in analysed_tracker_ids:
            continue  # ensure we don't accidently loop over a tracker twice
        # get a list of all the trackers that have the same easting
        trackers_in_col = ns.project.get_trackers_on_easting(tracker.easting, analysed_tracker_ids)
        # sort this list of trackers from northmost to southmost
        trackers_in_col = sorted(
            trackers_in_col,
            key=lambda t: t.get_northmost_pile().northing,
            reverse=True,
        )

        for t in trackers_in_col:
            if t.tracker_id not in analysed_tracker_ids:
                analysed_tracker_ids.append(t.tracker_id)

        # loop through the trackers with the same northing and determine if each pair is underneath
        for i in range(len(trackers_in_col) - 1):
            north = trackers_in_col[i]
            north_id = north.tracker_id
            south = trackers_in_col[i + 1]
            south_id = south.tracker_id
            # determine the height difference between the end piles in the trackers
            height_diff = abs(
                north.get_southmost_pile.total_height - south.get_northmost_pile.total_height
            )

            # compare with the maximum height difference as determined by the north-south shading
            # algorithim
            if height_diff > ns.max_height_diff:
                violating_trackers.append((north_id, south_id.height_diff))

    return violating_trackers
