"""End-to-end check of the intake pipeline: roster -> form spec -> sample
responses -> adapter -> solver.

Run either way:
    pytest                      # collects test_pipeline below
    python tests/test_pipeline.py   # prints PASS/FAIL lines, exits nonzero on failure
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

import pandas as pd

from roster import load_roster, CANONICAL_AREAS
from form_spec import build_spec, TOP_N
from adapter import adapt

ROSTER = os.path.join(HERE, "IEOR_Faculty_Roster.xlsx")


def test_pipeline():
    failures = []

    def check(cond, msg):
        print(("PASS" if cond else "FAIL"), "-", msg)
        if not cond:
            failures.append(msg)

    # 1. taxonomy: every faculty has at least one interest tag
    roster = load_roster(ROSTER)
    no_tags = roster[roster["interest_areas"].str.strip() == ""]
    check(len(no_tags) == 0, "every faculty has at least one interest area")
    check(
        all(roster["area"].isin(CANONICAL_AREAS)),
        "every primary area is in the canonical taxonomy",
    )

    # 2. form spec: counts line up with the data
    spec = build_spec(ROSTER)
    check(len(spec["faculty"]) == len(roster), "form spec has every faculty as an option")
    check(len(spec["questions"]) == 4 + TOP_N + 1, "form spec question count is correct")

    # 3. adapter: regenerate sample responses, then adapt
    subprocess.run([sys.executable, os.path.join(HERE, "tests", "make_sample_responses.py")],
                   check=True)
    responses = pd.read_csv(os.path.join(HERE, "data", "responses_sample.csv"))
    prefs, interests, warnings = adapt(responses, ROSTER)

    check(set(prefs.columns) == {"student_id", "faculty_id", "rank"},
          "preferences has the exact solver schema")
    check(prefs["faculty_id"].isin(roster["faculty_id"]).all(),
          "every preference maps to a real faculty_id")
    # ranks must be dense and 1-indexed per student
    dense = all(
        sorted(g["rank"]) == list(range(1, len(g) + 1))
        for _, g in prefs.groupby("student_id")
    )
    check(dense, "each student's ranks are dense and 1-indexed")
    check(len(warnings) == 3, "adapter caught the 3 injected edge cases")

    # 4. solver: adapter output produces a feasible schedule
    try:
        from config import Config
        from grid import build_grid
        from model import solve

        cfg = Config()
        grid = build_grid(cfg)
        faculty = roster[["faculty_id", "name", "area"]].copy()
        slots = grid["slot_id"].tolist()
        avail = pd.DataFrame(
            [(f, s) for f in faculty["faculty_id"] for s in slots],
            columns=["faculty_id", "slot_id"],
        )
        assignments, status, obj = solve(faculty, avail, prefs, grid, cfg)
        check(not assignments.empty, f"solver returns a schedule (status {status})")
        check(
            assignments["student_id"].nunique() == prefs["student_id"].nunique(),
            "every student with preferences gets scheduled",
        )
    except ImportError:
        print("SKIP - solver deps (ortools) not installed; adapter chain still verified")

    assert not failures, f"{len(failures)} failure(s): {failures}"


if __name__ == "__main__":
    try:
        test_pipeline()
    except AssertionError as e:
        print()
        print(e)
        sys.exit(1)
    print()
    print("ALL CHECKS PASSED")
