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
        test_validation_rejects_unknown_faculty_and_slot,
    )

    test_validation_rejects_unknown_faculty_and_slot()
    test_validation_accepts_minimal_clean_case()
    test_faculty_adapter_maps_windows_to_slots()
    test_faculty_adapter_requires_faculty_id()
    print("validation harness completed")
