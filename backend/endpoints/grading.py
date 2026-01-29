# backend/api/endpoints/grading.py
import sys
from pathlib import Path
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Add repo root to path so we can import modules from /PCL
sys.path.append(str(Path(__file__).parent.parent.parent))

import flatTrackerGrading

# Base (flat) classes
from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints

# XTR / terrain-following classes
try:
    from TerrainFollowingTracker import TerrainFollowingTracker
except Exception:
    TerrainFollowingTracker = None

try:
    from TerrainFollowingPile import TerrainFollowingPile
except Exception:
    TerrainFollowingPile = None

# Terrain-following grading module
try:
    import terrainTrackerGrading
except Exception:
    terrainTrackerGrading = None

router = APIRouter()


class PileInput(BaseModel):
    pile_id: Union[str, float]
    pile_in_tracker: int
    northing: float
    easting: float
    initial_elevation: float
    flooding_allowance: float = 0.0


class ConstraintsInput(BaseModel):
    """
    Frontend sends:
      - tracker_edge_overhang
    Older backend expects:
      - edge_overhang
    ✅ Accept both via alias.
    """

    min_reveal_height: float  # m
    max_reveal_height: float  # m
    pile_install_tolerance: float  # m
    max_incline: float  # % (frontend provides %)

    target_height_percentage: float = 0.5
    max_angle_rotation: float = 0.0

    # ✅ Accept tracker_edge_overhang from frontend
    edge_overhang: float = Field(0.0, alias="tracker_edge_overhang")

    # XTR-only
    max_segment_deflection_deg: Optional[float] = None
    max_cumulative_deflection_deg: Optional[float] = None

    class Config:
        populate_by_name = True


class GradingRequest(BaseModel):
    tracker_id: int
    tracker_type: str  # "flat" or "xtr"
    piles: List[PileInput]
    constraints: ConstraintsInput


class PileResult(BaseModel):
    pile_id: str
    pile_in_tracker: int
    northing: float
    easting: float
    initial_elevation: float
    final_elevation: float
    pile_revealed: float
    total_height: float
    cut_fill: float
    flooding_allowance: float = 0.0
    final_degree_break: float = 0.0


class GradingResponse(BaseModel):
    tracker_id: int
    tracker_type: str
    piles: List[PileResult]
    total_cut: float
    total_fill: float
    violations: List[dict]
    success: bool
    message: str
    constraints: ConstraintsInput
    
    # XTR-only metrics from backend
    north_wing_deflection: Optional[float] = None
    south_wing_deflection: Optional[float] = None
    max_tracker_degree_break: Optional[float] = None


class ProjectGradingRequest(BaseModel):
    tracker_type: str  # "flat" or "xtr"
    piles: List[PileInput]
    constraints: ConstraintsInput


class ProjectGradingResponse(BaseModel):
    total_cut: float
    total_fill: float
    piles: List[PileResult]
    violations: List[dict]
    success: bool
    message: str
    constraints: ConstraintsInput
    # Map tracker_id (int) -> { north_wing_deflection, south_wing_deflection, max_tracker_degree_break }
    tracker_metrics: Optional[dict] = None


def _pick_classes(tracker_type: str):
    """
    Choose the correct Tracker/Pile classes for flat vs XTR.
    """
    if tracker_type == "flat":
        return BaseTracker, BasePile

    if tracker_type == "xtr":
        if TerrainFollowingTracker is None:
            raise HTTPException(
                status_code=500,
                detail="TerrainFollowingTracker could not be imported. Check filename/import path.",
            )
        if TerrainFollowingPile is None:
            raise HTTPException(
                status_code=500,
                detail="TerrainFollowingPile could not be imported. Check filename/import path.",
            )
        return TerrainFollowingTracker, TerrainFollowingPile

    raise HTTPException(status_code=400, detail=f"Unknown tracker_type '{tracker_type}'")


def _run_grading(project: Project, tracker_type: str) -> None:
    """
    Dispatch grading to correct algorithm.
    """
    if tracker_type == "flat":
        flatTrackerGrading.main(project)
        return

    if tracker_type == "xtr":
        if terrainTrackerGrading is None:
            raise HTTPException(
                status_code=501,
                detail="terrainTrackerGrading could not be imported. Check backend env/dependencies.",
            )

        if hasattr(terrainTrackerGrading, "main"):
            terrainTrackerGrading.main(project)
            return

        if hasattr(terrainTrackerGrading, "grade_project"):
            terrainTrackerGrading.grade_project(project)
            return

        raise HTTPException(
            status_code=501,
            detail="terrainTrackerGrading has no main() or grade_project() entrypoint.",
        )

    raise HTTPException(status_code=400, detail=f"Unknown tracker_type '{tracker_type}'")


def _ensure_xtr_ground_init(pile, initial_elevation: float) -> None:
    """
    Terrain-following grading uses pile.current_elevation as the *ground* elevation.
    The Excel loader usually sets this. When coming from the API, we must set it.
    """
    # Preferred: the class exposes a setter
    if hasattr(pile, "set_current_elevation") and callable(getattr(pile, "set_current_elevation")):
        pile.set_current_elevation(initial_elevation)
        return

    # Fallback: set attribute directly if it exists
    if hasattr(pile, "current_elevation"):
        setattr(pile, "current_elevation", initial_elevation)
        return

    # If neither exists, surface a clear backend error
    raise HTTPException(
        status_code=500,
        detail="TerrainFollowingPile missing current_elevation / set_current_elevation; cannot initialise XTR ground.",
    )


@router.post("/grade-tracker", response_model=GradingResponse)
async def grade_single_tracker(request: GradingRequest):
    """
    Grade a single tracker (flat or XTR).
    """
    try:
        constraints = ProjectConstraints(
            min_reveal_height=request.constraints.min_reveal_height,
            max_reveal_height=request.constraints.max_reveal_height,
            pile_install_tolerance=request.constraints.pile_install_tolerance,
            max_incline=request.constraints.max_incline / 100.0,
            target_height_percentage=request.constraints.target_height_percentage,
            max_angle_rotation=request.constraints.max_angle_rotation,
            max_segment_deflection_deg=request.constraints.max_segment_deflection_deg,
            max_cumulative_deflection_deg=request.constraints.max_cumulative_deflection_deg,
            edge_overhang=request.constraints.edge_overhang,
        )

        project_type = "terrain_following" if request.tracker_type == "xtr" else "standard"
        project = Project(
            name=f"Tracker_{request.tracker_id}",
            project_type=project_type,
            constraints=constraints,
        )

        TrackerCls, PileCls = _pick_classes(request.tracker_type)

        tracker = TrackerCls(tracker_id=request.tracker_id)

        for pile_data in request.piles:
            # Force standard ID format f"{tracker_id}.{pit:02d}"
            normalized_id = f"{request.tracker_id}.{pile_data.pile_in_tracker:02d}"

            pile = PileCls(
                northing=pile_data.northing,
                easting=pile_data.easting,
                initial_elevation=pile_data.initial_elevation,
                pile_id=normalized_id,
                pile_in_tracker=pile_data.pile_in_tracker,
                flooding_allowance=pile_data.flooding_allowance,
            )

            # ✅ XTR init: ensure current ground elevation is set
            if request.tracker_type == "xtr":
                _ensure_xtr_ground_init(pile, pile_data.initial_elevation)

            tracker.add_pile(pile)

        tracker.sort_by_pole_position()
        project.add_tracker(tracker)

        _run_grading(project, request.tracker_type)

        # ✅ Calculate final deflection metrics if XTR
        north_wing_deflection = None
        south_wing_deflection = None
        max_tracker_degree_break = None

        if request.tracker_type == "xtr" and hasattr(tracker, "set_final_deflection_metrics"):
            tracker.set_final_deflection_metrics()
            north_wing_deflection = getattr(tracker, "north_wing_deflection", 0.0)
            south_wing_deflection = getattr(tracker, "south_wing_deflection", 0.0)
            max_tracker_degree_break = getattr(tracker, "max_tracker_degree_break", 0.0)

        # Results
        pile_results = []
        total_cut = 0.0
        total_fill = 0.0
        violations = []

        min_reveal_m = request.constraints.min_reveal_height
        max_reveal_m = request.constraints.max_reveal_height
        tolerance = request.constraints.pile_install_tolerance

        for pile in tracker.piles:
            cut_fill = pile.final_elevation - pile.initial_elevation
            if cut_fill > 0:
                total_cut += cut_fill
            else:
                total_fill += abs(cut_fill)

            if pile.pile_revealed < (
                min_reveal_m + pile.flooding_allowance + tolerance / 2 - 0.0001
            ):
                violations.append(
                    {
                        "pile_id": pile.pile_id,
                        "type": "min_reveal",
                        "value": pile.pile_revealed,
                        "limit": min_reveal_m + pile.flooding_allowance + tolerance / 2,
                    }
                )
            elif pile.pile_revealed > (max_reveal_m - tolerance / 2 + 0.0001):
                violations.append(
                    {
                        "pile_id": pile.pile_id,
                        "type": "max_reveal",
                        "value": pile.pile_revealed,
                        "limit": max_reveal_m - tolerance / 2,
                    }
                )
            
            # Grab degree break if exists
            p_break = getattr(pile, "final_degree_break", 0.0)

            pile_results.append(
                PileResult(
                    pile_id=str(pile.pile_id),  # Ensure output is str
                    pile_in_tracker=pile.pile_in_tracker,
                    northing=pile.northing,
                    easting=pile.easting,
                    initial_elevation=pile.initial_elevation,
                    final_elevation=pile.final_elevation,
                    pile_revealed=pile.pile_revealed,
                    total_height=pile.total_height,
                    cut_fill=cut_fill,
                    flooding_allowance=pile.flooding_allowance,
                    final_degree_break=p_break,
                )
            )

        return GradingResponse(
            tracker_id=request.tracker_id,
            tracker_type=request.tracker_type,
            piles=pile_results,
            total_cut=total_cut,
            total_fill=total_fill,
            violations=violations,
            success=True,
            message=f"Successfully graded tracker {request.tracker_id}",
            constraints=request.constraints,
            north_wing_deflection=north_wing_deflection,
            south_wing_deflection=south_wing_deflection,
            max_tracker_degree_break=max_tracker_degree_break,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=500,
            detail=f"Grading failed: {str(e)}\n{traceback.format_exc()}",
        )


@router.post("/grade-project", response_model=ProjectGradingResponse)
async def grade_project(request: ProjectGradingRequest):
    """
    Grade an entire project (all trackers).
    """
    try:
        constraints = ProjectConstraints(
            min_reveal_height=request.constraints.min_reveal_height,
            max_reveal_height=request.constraints.max_reveal_height,
            pile_install_tolerance=request.constraints.pile_install_tolerance,
            max_incline=request.constraints.max_incline / 100.0,
            edge_overhang=request.constraints.edge_overhang,
            target_height_percentage=request.constraints.target_height_percentage,
            max_angle_rotation=request.constraints.max_angle_rotation,
            max_segment_deflection_deg=request.constraints.max_segment_deflection_deg,
            max_cumulative_deflection_deg=request.constraints.max_cumulative_deflection_deg,
        )

        project_type = "terrain_following" if request.tracker_type == "xtr" else "standard"
        project = Project(
            name="Full_Project_Analysis",
            project_type=project_type,
            constraints=constraints,
        )

        TrackerCls, PileCls = _pick_classes(request.tracker_type)

        # Group piles by tracker
        piles_by_tracker = {}
        for p in request.piles:
            tracker_id = int(float(p.pile_id))
            piles_by_tracker.setdefault(tracker_id, []).append(p)

        # Create trackers and add piles
        for tid, piles in piles_by_tracker.items():
            tracker = TrackerCls(tracker_id=tid)
            for pile_data in piles:
                # Force standard ID format f"{tracker_id}.{pit:02d}"
                normalized_id = f"{tid}.{pile_data.pile_in_tracker:02d}"

                pile = PileCls(
                    northing=pile_data.northing,
                    easting=pile_data.easting,
                    initial_elevation=pile_data.initial_elevation,
                    pile_id=normalized_id,
                    pile_in_tracker=pile_data.pile_in_tracker,
                    flooding_allowance=pile_data.flooding_allowance,
                )

                # ✅ XTR init: ensure current ground elevation is set
                if request.tracker_type == "xtr":
                    _ensure_xtr_ground_init(pile, pile_data.initial_elevation)

                tracker.add_pile(pile)

            tracker.sort_by_pole_position()
            project.add_tracker(tracker)

        _run_grading(project, request.tracker_type)

        # Collect results
        pile_results = []
        total_cut = 0.0
        total_fill = 0.0
        violations = []
        tracker_metrics = {}

        min_reveal_m = request.constraints.min_reveal_height
        max_reveal_m = request.constraints.max_reveal_height
        tolerance = request.constraints.pile_install_tolerance

        # ✅ Calculate metrics for each tracker if XTR
        if request.tracker_type == "xtr":
            for tracker in project.trackers:
                if hasattr(tracker, "set_final_deflection_metrics"):
                    tracker.set_final_deflection_metrics()
                    tracker_metrics[tracker.tracker_id] = {
                        "north_wing_deflection": getattr(tracker, "north_wing_deflection", 0.0),
                        "south_wing_deflection": getattr(tracker, "south_wing_deflection", 0.0),
                        "max_tracker_degree_break": getattr(tracker, "max_tracker_degree_break", 0.0),
                    }

        for tracker in project.trackers:
            for pile in tracker.piles:
                cut_fill = pile.final_elevation - pile.initial_elevation
                if cut_fill > 0:
                    total_cut += cut_fill
                else:
                    total_fill += abs(cut_fill)

                if pile.pile_revealed < (
                    min_reveal_m + pile.flooding_allowance + tolerance / 2 - 0.0001
                ):
                    violations.append(
                        {
                            "pile_id": pile.pile_id,
                            "type": "min_reveal",
                            "value": pile.pile_revealed,
                            "limit": min_reveal_m + pile.flooding_allowance + tolerance / 2,
                        }
                    )
                elif pile.pile_revealed > (max_reveal_m - tolerance / 2 + 0.0001):
                    violations.append(
                        {
                            "pile_id": pile.pile_id,
                            "type": "max_reveal",
                            "value": pile.pile_revealed,
                            "limit": max_reveal_m - tolerance / 2,
                        }
                    )
                
                # Grab degree break if exists
                p_break = getattr(pile, "final_degree_break", 0.0)

                pile_results.append(
                    PileResult(
                        pile_id=str(pile.pile_id), # Ensure output is str
                        pile_in_tracker=pile.pile_in_tracker,
                        northing=pile.northing,
                        easting=pile.easting,
                        initial_elevation=pile.initial_elevation,
                        final_elevation=pile.final_elevation,
                        pile_revealed=pile.pile_revealed,
                        total_height=pile.total_height,
                        cut_fill=cut_fill,
                        flooding_allowance=pile.flooding_allowance,
                        final_degree_break=p_break,
                    )
                )

        return ProjectGradingResponse(
            total_cut=total_cut,
            total_fill=total_fill,
            piles=pile_results,
            violations=violations,
            success=True,
            message=f"Successfully graded {len(project.trackers)} trackers",
            constraints=request.constraints,
            tracker_metrics=tracker_metrics,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=500,
            detail=f"Grading failed: {str(e)}\n{traceback.format_exc()}",
        )
