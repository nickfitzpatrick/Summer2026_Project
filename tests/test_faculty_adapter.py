import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

from faculty_adapter import adapt_faculty_availability
from faculty_form_spec import Q_EMAIL, Q_FIRST, Q_LAST, _day_avail_title


def test_faculty_adapter_maps_windows_to_slots():
    faculty = pd.DataFrame([{
        "faculty_id": "F01",
        "name": "Ada Lovelace",
        "email": "ada@example.edu",
    }])
    grid = pd.DataFrame([{
        "slot_id": "D1-S1",
        "day": 1,
        "start_time": "09:00",
        "end_time": "09:20",
    }])
    responses = pd.DataFrame([{
        Q_FIRST: "Ada",
        Q_LAST: "Lovelace",
        Q_EMAIL: "ada@example.edu",
        _day_avail_title(1): "09:00-09:20",
    }])

    availability, warnings = adapt_faculty_availability(responses, faculty, grid)

    assert warnings == []
    assert availability.to_dict("records") == [{"faculty_id": "F01", "slot_id": "D1-S1"}]


def test_faculty_adapter_requires_faculty_id():
    faculty = pd.DataFrame([{"name": "Ada Lovelace", "email": "ada@example.edu"}])
    grid = pd.DataFrame([{
        "slot_id": "D1-S1",
        "day": 1,
        "start_time": "09:00",
        "end_time": "09:20",
    }])
    responses = pd.DataFrame([{Q_EMAIL: "ada@example.edu", _day_avail_title(1): "09:00-09:20"}])

    availability, warnings = adapt_faculty_availability(responses, faculty, grid)

    assert availability.empty
    assert warnings
