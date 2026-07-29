import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

from config import Config
from student_metrics import student_satisfaction_table, student_request_table


def _grid(n=8):
    return pd.DataFrame([
        {"slot_id": f"T{i}", "day": 1, "start_time": "09:00", "end_time": "09:20"}
        for i in range(1, n + 1)
    ])


def test_student_with_two_ranks_getting_both_is_fully_satisfied():
    cfg = Config()
    prefs = pd.DataFrame([
        {"student_id": "S1", "faculty_id": "F1", "rank": 1},
        {"student_id": "S1", "faculty_id": "F2", "rank": 2},
    ])
    assignments = pd.DataFrame([
        {"student_id": "S1", "faculty_id": "F1", "slot_id": "T1"},
        {"student_id": "S1", "faculty_id": "F2", "slot_id": "T2"},
    ])
    students = pd.DataFrame([{"student_id": "S1", "max_meetings_requested": 4}])

    out = student_satisfaction_table(assignments, prefs, _grid(), students, cfg).iloc[0]

    assert out["effective_max_meetings"] == 2
    assert out["raw_satisfaction"] == out["max_possible_satisfaction"]
    assert out["normalized_satisfaction"] == 1.0
    assert out["meeting_fulfillment_rate"] == 1.0


def test_eight_ranks_with_max_four_uses_only_top_four_possible_values():
    cfg = Config()
    prefs = pd.DataFrame([
        {"student_id": "S1", "faculty_id": f"F{i}", "rank": i}
        for i in range(1, 9)
    ])
    students = pd.DataFrame([{"student_id": "S1", "max_meetings_requested": 4}])

    out = student_satisfaction_table(pd.DataFrame(columns=["student_id", "faculty_id", "slot_id"]),
                                     prefs, _grid(), students, cfg).iloc[0]

    assert out["effective_max_meetings"] == 4
    assert out["max_possible_satisfaction"] == 100 + 60 + 36 + 21.6


def test_missing_or_invalid_max_meetings_defaults_to_four():
    cfg = Config()
    prefs = pd.DataFrame([
        {"student_id": "S1", "faculty_id": f"F{i}", "rank": i}
        for i in range(1, 6)
    ])
    missing = student_request_table(prefs, _grid(), None, cfg).iloc[0]
    invalid = student_request_table(
        prefs,
        _grid(),
        pd.DataFrame([{"student_id": "S1", "max_meetings_requested": "bad"}]),
        cfg,
    ).iloc[0]

    assert missing["max_meetings_requested"] == 4
    assert invalid["max_meetings_requested"] == 4
    assert invalid["effective_max_meetings"] == 4
