"""Small validation harness for environments without pytest.

Run:
    python tests/validation_harness.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tests"))


def run(path):
    print(f"running {path}")
    subprocess.run([sys.executable, path], check=True)


if __name__ == "__main__":
    run(os.path.join(HERE, "tests", "test_pipeline.py"))
    from test_faculty_adapter import (
        test_faculty_adapter_maps_windows_to_slots,
        test_faculty_adapter_requires_faculty_id,
    )
    from test_validation import (
        test_validation_accepts_minimal_clean_case,
        test_validation_rejects_student_request_above_available_slots,
        test_validation_rejects_unknown_faculty_and_slot,
    )
    from test_student_metrics import (
        test_eight_ranks_with_max_four_uses_only_top_four_possible_values,
        test_missing_or_invalid_max_meetings_defaults_to_four,
        test_student_with_two_ranks_getting_both_is_fully_satisfied,
    )

    test_validation_rejects_unknown_faculty_and_slot()
    test_validation_accepts_minimal_clean_case()
    test_validation_rejects_student_request_above_available_slots()
    test_faculty_adapter_maps_windows_to_slots()
    test_faculty_adapter_requires_faculty_id()
    test_student_with_two_ranks_getting_both_is_fully_satisfied()
    test_eight_ranks_with_max_four_uses_only_top_four_possible_values()
    test_missing_or_invalid_max_meetings_defaults_to_four()
    print("validation harness completed")
