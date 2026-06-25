"""Turn wide Google Form responses into the long files the solver consumes.

Input: a response sheet (DataFrame or CSV) where each row is one student and the
columns are the form_spec question titles. Output:
  preferences.csv      (student_id, faculty_id, rank)   - the solver's contract
  student_interests.csv (student_id, interest_area)     - gap-fill input

The ordered-dropdown ranking is read in order: "1st choice faculty" -> rank 1, and
so on. Real responses are messy, so the adapter defends against:
  - a student naming the same faculty twice (keep the earliest rank, drop dupes)
  - blank ordered slots (skip; ranks stay dense and 1-indexed)
  - a name that matches no faculty (recorded as a warning, row not dropped)
Student IDs are assigned S01.. in sheet order unless the sheet already has an id.
"""

import os
import pandas as pd

from roster import load_roster, CANONICAL_AREAS
from form_spec import (
    Q_FIRST, Q_LAST, Q_EMAIL, Q_INTERESTS, TOP_N, _rank_title,
)


def _name_to_id(roster: pd.DataFrame) -> dict:
    return {n.strip().lower(): fid for n, fid in zip(roster["name"], roster["faculty_id"])}


def adapt(responses: pd.DataFrame, roster_path: str):
    """Return (preferences_df, interests_df, warnings).

    preferences_df: student_id, faculty_id, rank
    interests_df:   student_id, interest_area
    warnings:       list of human-readable strings for the staff app to surface
    """
    roster = load_roster(roster_path)
    name2id = _name_to_id(roster)
    warnings = []

    pref_rows = []
    interest_rows = []

    for idx, (_, r) in enumerate(responses.iterrows(), start=1):
        sid = str(r["student_id"]).strip() if "student_id" in responses.columns \
            and pd.notna(r.get("student_id")) else f"S{idx:02d}"
        who = f"{r.get(Q_FIRST, '')} {r.get(Q_LAST, '')}".strip() or sid

        seen = set()
        rank = 0
        for i in range(1, TOP_N + 1):
            col = _rank_title(i)
            val = r.get(col)
            if pd.isna(val) or not str(val).strip():
                continue
            fid = name2id.get(str(val).strip().lower())
            if fid is None:
                warnings.append(f"{who}: '{val}' in {col} matches no faculty; skipped.")
                continue
            if fid in seen:
                warnings.append(f"{who}: {val} listed more than once; kept first.")
                continue
            seen.add(fid)
            rank += 1
            pref_rows.append({"student_id": sid, "faculty_id": fid, "rank": rank})

        if rank == 0:
            warnings.append(f"{who}: no valid ranked faculty; student has no preferences.")

        raw = r.get(Q_INTERESTS)
        if pd.notna(raw) and str(raw).strip():
            for area in _split_multi(str(raw)):
                if area in CANONICAL_AREAS:
                    interest_rows.append({"student_id": sid, "interest_area": area})
                else:
                    warnings.append(f"{who}: unknown interest area '{area}'; skipped.")

    preferences = pd.DataFrame(pref_rows, columns=["student_id", "faculty_id", "rank"])
    interests = pd.DataFrame(interest_rows, columns=["student_id", "interest_area"])
    return preferences, interests, warnings


def _split_multi(raw: str) -> list:
    """Google Forms joins checkbox answers with ', '. Areas have no commas, so
    splitting on comma is safe; we also tolerate semicolons just in case."""
    parts = raw.replace(";", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def adapt_file(in_csv: str, roster_path: str, out_dir: str):
    responses = pd.read_csv(in_csv)
    prefs, interests, warnings = adapt(responses, roster_path)
    os.makedirs(out_dir, exist_ok=True)
    prefs.to_csv(os.path.join(out_dir, "preferences.csv"), index=False)
    interests.to_csv(os.path.join(out_dir, "student_interests.csv"), index=False)
    return prefs, interests, warnings


if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    in_csv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "data", "responses_sample.csv")
    prefs, interests, warnings = adapt_file(
        in_csv, os.path.join(here, "IEOR_Faculty_Roster.xlsx"), os.path.join(here, "data")
    )
    print(f"preferences: {len(prefs)} rows, {prefs['student_id'].nunique()} students")
    print(f"interests:   {len(interests)} rows")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print("  -", w)
