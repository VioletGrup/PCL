import math
from typing import Iterable

from Segment import Segment


def validate_tracker_deflections(
    segments: Iterable[Segment],
    max_segment_deflection_deg: float,
    max_cumulative_deflection_deg: float,
) -> tuple[list[tuple[int, float]], float]:
    """

    Returns:

      - violations: list of (segment_id, abs_deflection_deg) for segments exceeding max

      - cumulative_abs_deflection_deg: sum of abs(deflection_deg) across all segments

    """

    violations: list[tuple[int, float]] = []

    cumulative = 0.0

    for seg in segments:
        deg = seg.degree_of_deflection()

        abs_deg = abs(deg)

        # treat inf as a violation

        if math.isinf(abs_deg) or abs_deg > max_segment_deflection_deg:
            violations.append((seg.segment_id, abs_deg))

        cumulative += abs_deg

    return violations, cumulative


def ensure_tracker_deflections_ok(
    segments: Iterable[Segment],
    max_segment_deflection_deg: float = 0.75,
    max_cumulative_deflection_deg: float = 4.0,  # <-- set this to your tracker-wide limit
) -> bool:
    """

    Raises ValueError if:

      - any segment exceeds max_segment_deflection_deg, OR

      - cumulative sum of abs segment deflections exceeds max_cumulative_deflection_deg

    """

    violations, cumulative = validate_tracker_deflections(
        segments,
        max_segment_deflection_deg=max_segment_deflection_deg,
        max_cumulative_deflection_deg=max_cumulative_deflection_deg,
    )

    problems: list[str] = []

    if violations:
        problems.append(f"Per-segment limit: {max_segment_deflection_deg}°")

        problems.append("Segment violations:")

        for seg_id, abs_deg in violations:
            problems.append(f"  - Segment {seg_id}: {abs_deg:.6f}°")

    if cumulative > max_cumulative_deflection_deg:
        problems.append(
            f"Cumulative deflection violation: {cumulative:.6f}° > {max_cumulative_deflection_deg}°"
        )

    if problems:
        return False
    return True
