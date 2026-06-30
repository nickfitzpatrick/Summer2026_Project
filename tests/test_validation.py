import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

from validation import validate_solver_inputs


def test_validation_rejects_unknown_faculty_and_slot():
    faculty = pd.DataFrame([{"faculty_id": "F01", "name": "Prof A"}])
    availability = pd.DataFrame([{"faculty_id": "F01", "slot_id": "BAD-SLOT"}])
    preferences = pd.DataFrame([{"student_id": "S01", "faculty_id": "F99", "rank": 1}])
    grid = pd.DataFrame([{
        "slot_id": "D1-S1",
        "day": 1,
        "start_time": "09:00",
        "end_time": "09:20",
    }])

    report = validate_solver_inputs(faculty, availability, preferences, grid)

    assert not report.ok
    assert any("preferences.csv refers to faculty IDs" in e for e in report.errors)
    assert any("availability.csv refers to slot IDs" in e for e in report.errors)


def test_validation_accepts_minimal_clean_case():
    faculty = pd.DataFrame([{"faculty_id": "F01", "name": "Prof A"}])
    availability = pd.DataFrame([{"faculty_id": "F01", "slot_id": "D1-S1"}])
    preferences = pd.DataFrame([{"student_id": "S01", "faculty_id": "F01", "rank": 1}])
    grid = pd.DataFrame([{
        "slot_id": "D1-S1",
        "day": 1,
        "start_time": "09:00",
        "end_time": "09:20",
    }])

    report = validate_solver_inputs(faculty, availability, preferences, grid, min_preferences=1)

    assert report.ok
    assert report.info
