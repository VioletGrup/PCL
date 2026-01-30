
import pytest
import pandas as pd
import sys
import os
# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from ProjectConstraints import ProjectConstraints
from testing_get_data_tf import load_project_from_excel

def test_pile_id_zero_padding():
    """Test that pile IDs are zero-padded (e.g., 1.01) to avoid Excel collisions."""
    
    # Mock data
    data = {
        "Frame": [1, 1],
        "Description": [1, 10],  # Pile 1 and Pile 10
        "Easting": [100.0, 110.0],
        "Northing": [200.0, 210.0],
        "Elevation": [10.0, 10.0],
        "Dummy": [0, 0]
    }
    df = pd.DataFrame(data)
    
    # Mock read_excel to return our DataFrame
    with patch("pandas.read_excel", return_value=df):
        constraints = ProjectConstraints(
            min_reveal_height=1.0,
            max_reveal_height=2.0,
            pile_install_tolerance=0.0,
            max_incline=0.1,
            max_angle_rotation=0.0,
            edge_overhang=0.0,
            max_segment_deflection_deg=1.0,
            max_cumulative_deflection_deg=5.0
        )
        project = load_project_from_excel(
            excel_path="dummy.xlsx",
            sheet_name="Sheet1",
            project_name="Test",
            project_type="terrain_following",
            constraints=constraints
        )
        
        # Check pile IDs in tracker 1
        tracker = project.trackers[0]
        # Sort piles just in case
        tracker.sort_by_pole_position()
        
        pile1 = tracker.piles[0]
        pile10 = tracker.piles[1]
        
        assert pile1.pile_in_tracker == 1
        assert pile10.pile_in_tracker == 10
        
        # KEY ASSERTION: Verify format is 1.01, not 1.1
        assert pile1.pile_id == "1.01", f"Expected '1.01', got '{pile1.pile_id}'"
        assert pile10.pile_id == "1.10", f"Expected '1.10', got '{pile10.pile_id}'"
        
        # Verify they are distinc strings
        assert pile1.pile_id != pile10.pile_id

if __name__ == "__main__":
    test_pile_id_zero_padding()
    print("Test passed!")
