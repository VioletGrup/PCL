import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add parent directory to path to import your modules
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from backend.api.main import app

client = TestClient(app)


def test_grade_project():
    # Sample data
    request_data = {
        "tracker_type": "flat",
        "piles": [
            {
                "pile_id": 1.01,
                "pile_in_tracker": 1,
                "northing": 0.0,
                "easting": 0.0,
                "initial_elevation": 100.0,
                "flooding_allowance": 0.0,
            },
            {
                "pile_id": 1.02,
                "pile_in_tracker": 2,
                "northing": 10.0,
                "easting": 0.0,
                "initial_elevation": 100.5,
                "flooding_allowance": 0.0,
            },
            {
                "pile_id": 2.01,
                "pile_in_tracker": 1,
                "northing": 0.0,
                "easting": 20.0,
                "initial_elevation": 101.0,
                "flooding_allowance": 0.0,
            },
        ],
        "constraints": {
            "min_reveal_height": 1.2,
            "max_reveal_height": 3.2,
            "pile_install_tolerance": 0.2,
            "max_incline": 15,
            "target_height_percantage": 0.5,
            "max_angle_rotation": 0.0,
        },
    }

    response = client.post("/api/grade-project", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["piles"]) == 3
    assert data["total_cut"] >= 0
    assert data["total_fill"] >= 0

    # Check if results are grouped/processed correctly
    # Pile 1.01 and 1.02 should be in one tracker, 2.01 in another
    # But the response is a flat list of piles.

    piles = {p["pile_id"]: p for p in data["piles"]}
    assert 1.01 in piles
    assert 1.02 in piles
    assert 2.01 in piles

    # Check if final elevation is calculated (should not be equal to initial if graded)
    # For flat tracker, it tries to fit a line.
    assert piles[1.01]["final_elevation"] != 0
