"""Staff-facing validation for scheduler inputs.

The solver expects three compact tables. This module checks those tables before
we ask CP-SAT to solve, and returns messages written for staff instead of Python
tracebacks.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_solver_inputs(faculty, availability, preferences, grid, min_preferences=3):
    report = ValidationReport()

    if faculty is None or availability is None or preferences is None:
        report.errors.append("Load faculty, availability, and preference files before scheduling.")
        return report

    _require_columns(report, faculty, "faculty.csv", ["faculty_id", "name"])
    _require_columns(report, availability, "availability.csv", ["faculty_id", "slot_id"])
    _require_columns(report, preferences, "preferences.csv", ["student_id", "faculty_id", "rank"])
    _require_columns(report, grid, "visit-day slots", ["slot_id", "day", "start_time", "end_time"])
    if report.errors:
        return report

    faculty = _clean_ids(faculty, ["faculty_id"])
    availability = _clean_ids(availability, ["faculty_id", "slot_id"])
    preferences = _clean_ids(preferences, ["student_id", "faculty_id"])
    grid = _clean_ids(grid, ["slot_id"])

    _duplicates(report, faculty, "faculty.csv", "faculty_id", "faculty IDs")
    _duplicates(report, grid, "visit-day slots", "slot_id", "slot IDs")
    _duplicates(report, preferences, "preferences.csv", ["student_id", "faculty_id"], "student/faculty pairs")
    _duplicates(report, availability, "availability.csv", ["faculty_id", "slot_id"], "faculty/slot rows")

    faculty_ids = set(faculty["faculty_id"])
    slot_ids = set(grid["slot_id"])
    pref_faculty = set(preferences["faculty_id"])
    avail_faculty = set(availability["faculty_id"])
    avail_slots = set(availability["slot_id"])

    unknown_pref_faculty = sorted(pref_faculty - faculty_ids)
    unknown_avail_faculty = sorted(avail_faculty - faculty_ids)
    unknown_avail_slots = sorted(avail_slots - slot_ids)

    if unknown_pref_faculty:
        report.errors.append(
            "preferences.csv refers to faculty IDs that are not in faculty.csv: "
            + _preview(unknown_pref_faculty)
        )
    if unknown_avail_faculty:
        report.errors.append(
            "availability.csv refers to faculty IDs that are not in faculty.csv: "
            + _preview(unknown_avail_faculty)
        )
    if unknown_avail_slots:
        report.errors.append(
            "availability.csv refers to slot IDs that are not in the visit-day setup: "
            + _preview(unknown_avail_slots)
        )

    ranks = pd.to_numeric(preferences["rank"], errors="coerce")
    if ranks.isna().any():
        report.errors.append("preferences.csv has rank values that are not numbers.")
    elif (ranks < 1).any():
        report.errors.append("preferences.csv ranks must be positive numbers starting at 1.")
    elif not (ranks == ranks.astype(int)).all():
        report.errors.append("preferences.csv ranks must be whole numbers.")

    students_with_prefs = set(preferences["student_id"])
    empty_student_ids = _blank_values(preferences, "student_id")
    if empty_student_ids:
        report.errors.append("preferences.csv has blank student_id values.")

    empty_faculty_ids = _blank_values(faculty, "faculty_id")
    if empty_faculty_ids:
        report.errors.append("faculty.csv has blank faculty_id values.")

    faculty_with_no_availability = sorted(faculty_ids - avail_faculty)
    if faculty_with_no_availability:
        report.warnings.append(
            "These faculty have no available slots and cannot be scheduled: "
            + _preview(faculty_with_no_availability)
        )

    low_pref = (
        preferences.groupby("student_id")["faculty_id"]
        .nunique()
        .loc[lambda s: s < min_preferences]
        .sort_index()
    )
    if not low_pref.empty:
        report.warnings.append(
            f"{len(low_pref)} student(s) have fewer than {min_preferences} ranked faculty. "
            "They may receive fewer or lower-priority meetings."
        )

    unavailable_pref_faculty = sorted(pref_faculty - avail_faculty)
    if unavailable_pref_faculty:
        report.warnings.append(
            "Some ranked faculty have no availability, so those preferences cannot be assigned: "
            + _preview(unavailable_pref_faculty)
        )

    if not students_with_prefs:
        report.errors.append("preferences.csv has no student preference rows.")
    if availability.empty:
        report.errors.append("availability.csv has no faculty availability rows.")
    if grid.empty:
        report.errors.append("The visit-day setup has no meeting slots.")

    if report.ok:
        report.info.append(
            f"Ready to solve: {len(students_with_prefs)} student(s), "
            f"{len(faculty_ids)} faculty, {len(slot_ids)} meeting slot(s)."
        )
    return report


def _require_columns(report, df, label, required):
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.errors.append(f"{label} is missing required column(s): {', '.join(missing)}.")


def _clean_ids(df, cols):
    out = df.copy()
    for col in cols:
        out[col] = out[col].astype(str).str.strip()
    return out


def _duplicates(report, df, label, cols, name):
    dupes = df[df.duplicated(cols, keep=False)]
    if not dupes.empty:
        report.errors.append(f"{label} has duplicate {name}.")


def _blank_values(df, col):
    return df[col].astype(str).str.strip().eq("").any() or df[col].isna().any()


def _preview(values, limit=8):
    values = [str(v) for v in values]
    shown = ", ".join(values[:limit])
    if len(values) > limit:
        shown += f", and {len(values) - limit} more"
    return shown
