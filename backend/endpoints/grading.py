# backend/api/endpoints/grading.py
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add parent directory to path to import your modules
sys.path.append(str(Path(__file__).parent.parent.parent))

import flatTrackerGrading  # Import the module, not specific functions
from BasePile import BasePile
from BaseTracker import BaseTracker
from Project import Project
from ProjectConstraints import ProjectConstraints

router = APIRouter()

class PileInput(BaseModel):
    pile_id: float
    pile_in_tracker: int
    northing: float
    easting: float
    initial_elevation: float
    flooding_allowance: float = 0.0

class ConstraintsInput(BaseModel):
    min_reveal_height: float  # m
    max_reveal_height: float  # m
    pile_install_tolerance: float  # m
    max_incline: float  # %
    target_height_percantage: float = 0.5
    max_angle_rotation: float = 0.0
    # Terrain-following only
    max_segment_deflection_deg: Optional[float] = None
    max_cumulative_deflection_deg: Optional[float] = None

class GradingRequest(BaseModel):
    tracker_id: int
    tracker_type: str  # "flat" or "xtr"
    piles: List[PileInput]
    constraints: ConstraintsInput

class PileResult(BaseModel):
    pile_id: float
    pile_in_tracker: int
    northing: float
    easting: float
    initial_elevation: float
    final_elevation: float
    pile_revealed: float
    total_height: float
    cut_fill: float  # positive = cut, negative = fill
    flooding_allowance: float = 0.0

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

@router.post("/grade-tracker", response_model=GradingResponse)
async def grade_single_tracker(request: GradingRequest):
    """
    Grade a single tracker using either flat or terrain-following algorithm.
    """
    try:
        # Values are now expected in meters and ratios directly from frontend
        constraints = ProjectConstraints(
            min_reveal_height=request.constraints.min_reveal_height,
            max_reveal_height=request.constraints.max_reveal_height,
            pile_install_tolerance=request.constraints.pile_install_tolerance,
            max_incline=request.constraints.max_incline / 100.0, # Convert % to ratio
            target_height_percantage=request.constraints.target_height_percantage,
            max_angle_rotation=request.constraints.max_angle_rotation,
            max_segment_deflection_deg=request.constraints.max_segment_deflection_deg,
            max_cumulative_deflection_deg=request.constraints.max_cumulative_deflection_deg,
        )

        # Create project
        project_type = "terrain_following" if request.tracker_type == "xtr" else "standard"
        project = Project(
            name=f"Tracker_{request.tracker_id}",
            project_type=project_type,
            constraints=constraints
        )

        # Create tracker
        tracker = BaseTracker(tracker_id=request.tracker_id)

        # Add piles
        for pile_data in request.piles:
            pile = BasePile(
                northing=pile_data.northing,
                easting=pile_data.easting,
                initial_elevation=pile_data.initial_elevation,
                pile_id=pile_data.pile_id,
                pile_in_tracker=pile_data.pile_in_tracker,
                flooding_allowance=pile_data.flooding_allowance
            )
            tracker.add_pile(pile)

        # Sort piles by position
        tracker.sort_by_pole_position()

        # Add tracker to project
        project.add_tracker(tracker)

        # Run grading algorithm
        if request.tracker_type == "flat":
            # Run flat tracker grading using the main function
            flatTrackerGrading.main(project)
        else:  # xtr / terrain-following
            # For terrain-following, we need to implement the algorithm
            raise HTTPException(
                status_code=501,
                detail="Terrain-following grading not yet implemented in API."
            )

        # Calculate results
        pile_results = []
        total_cut = 0.0
        total_fill = 0.0
        violations = []

        for pile in tracker.piles:
            cut_fill = pile.final_elevation - pile.initial_elevation
            if cut_fill > 0:
                total_cut += cut_fill
            else:
                total_fill += abs(cut_fill)

            # Check for violations against ACTUAL project limits
            min_reveal_m = request.constraints.min_reveal_height
            max_reveal_m = request.constraints.max_reveal_height
            
            # Use the main branch tolerance logic (tolerance / 2)
            tolerance = request.constraints.pile_install_tolerance
            
            if pile.pile_revealed < (min_reveal_m + pile.flooding_allowance
                                      + tolerance / 2 - 0.0001):
                violations.append({
                    "pile_id": pile.pile_id,
                    "type": "min_reveal",
                    "value": pile.pile_revealed,
                    "limit": min_reveal_m + pile.flooding_allowance + tolerance / 2
                })
            elif pile.pile_revealed > (max_reveal_m - tolerance / 2 + 0.0001):
                violations.append({
                    "pile_id": pile.pile_id,
                    "type": "max_reveal",
                    "value": pile.pile_revealed,
                    "limit": max_reveal_m - tolerance / 2
                })

            pile_results.append(PileResult(
                pile_id=pile.pile_id,
                pile_in_tracker=pile.pile_in_tracker,
                northing=pile.northing,
                easting=pile.easting,
                initial_elevation=pile.initial_elevation,
                final_elevation=pile.final_elevation,
                pile_revealed=pile.pile_revealed,
                total_height=pile.total_height,
                cut_fill=cut_fill,
                flooding_allowance=pile.flooding_allowance
            ))

        return GradingResponse(
            tracker_id=request.tracker_id,
            tracker_type=request.tracker_type,
            piles=pile_results,
            total_cut=total_cut,
            total_fill=total_fill,
            violations=violations,
            success=True,
            message=f"Successfully graded tracker {request.tracker_id}",
            constraints=request.constraints
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, 
                            detail=f"Grading failed: {str(e)}\n{traceback.format_exc()}")

@router.post("/grade-project", response_model=ProjectGradingResponse)
async def grade_project(request: ProjectGradingRequest):
    """
    Grade an entire project (all trackers).
    """
    try:
        # Convert constraints
        constraints = ProjectConstraints(
            min_reveal_height=request.constraints.min_reveal_height,
            max_reveal_height=request.constraints.max_reveal_height,
            pile_install_tolerance=request.constraints.pile_install_tolerance,
            max_incline=request.constraints.max_incline / 100.0, # Convert % to ratio
            target_height_percantage=request.constraints.target_height_percantage,
            max_angle_rotation=request.constraints.max_angle_rotation,
            max_segment_deflection_deg=request.constraints.max_segment_deflection_deg,
            max_cumulative_deflection_deg=request.constraints.max_cumulative_deflection_deg,
        )

        # Create project
        project_type = "terrain_following" if request.tracker_type == "xtr" else "standard"
        project = Project(
            name="Full_Project_Analysis",
            project_type=project_type,
            constraints=constraints
        )

        # Group piles by tracker
        piles_by_tracker = {}
        for p in request.piles:
            tracker_id = int(p.pile_id)
            if tracker_id not in piles_by_tracker:
                piles_by_tracker[tracker_id] = []
            piles_by_tracker[tracker_id].append(p)

        # Create trackers and add to project
        for tid, piles in piles_by_tracker.items():
            tracker = BaseTracker(tracker_id=tid)
            for pile_data in piles:
                pile = BasePile(
                    northing=pile_data.northing,
                    easting=pile_data.easting,
                    initial_elevation=pile_data.initial_elevation,
                    pile_id=pile_data.pile_id,
                    pile_in_tracker=pile_data.pile_in_tracker,
                    flooding_allowance=pile_data.flooding_allowance
                )
                tracker.add_pile(pile)
            
            tracker.sort_by_pole_position()
            project.add_tracker(tracker)

        # Run grading
        if request.tracker_type == "flat":
            flatTrackerGrading.main(project)
        else:
             raise HTTPException(
                status_code=501,
                detail="Terrain-following grading not yet implemented in API."
            )

        # Collect results
        pile_results = []
        total_cut = 0.0
        total_fill = 0.0
        violations = []

        min_reveal_m = request.constraints.min_reveal_height
        max_reveal_m = request.constraints.max_reveal_height
        tolerance = request.constraints.pile_install_tolerance

        for tracker in project.trackers:
            for pile in tracker.piles:
                cut_fill = pile.final_elevation - pile.initial_elevation
                if cut_fill > 0:
                    total_cut += cut_fill
                else:
                    total_fill += abs(cut_fill)

                # Check violations against ACTUAL project limits (main branch tolerance logic)
                if pile.pile_revealed < (min_reveal_m + pile.flooding_allowance
                                          + tolerance / 2 - 0.0001):
                    violations.append({
                        "pile_id": pile.pile_id,
                        "type": "min_reveal",
                        "value": pile.pile_revealed,
                        "limit": min_reveal_m + pile.flooding_allowance + tolerance / 2
                    })
                elif pile.pile_revealed > (max_reveal_m - tolerance / 2 + 0.0001):
                    violations.append({
                        "pile_id": pile.pile_id,
                        "type": "max_reveal",
                        "value": pile.pile_revealed,
                        "limit": max_reveal_m - tolerance / 2
                    })

                pile_results.append(PileResult(
                    pile_id=pile.pile_id,
                    pile_in_tracker=pile.pile_in_tracker,
                    northing=pile.northing,
                    easting=pile.easting,
                    initial_elevation=pile.initial_elevation,
                    final_elevation=pile.final_elevation,
                    pile_revealed=pile.pile_revealed,
                    total_height=pile.total_height,
                    cut_fill=cut_fill,
                    flooding_allowance=pile.flooding_allowance
                ))

        return ProjectGradingResponse(
            total_cut=total_cut,
            total_fill=total_fill,
            piles=pile_results,
            violations=violations,
            success=True,
            message=f"Successfully graded {len(project.trackers)} trackers",
            constraints=request.constraints
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500,
                             detail=f"Grading failed: {str(e)}\n{traceback.format_exc()}")
