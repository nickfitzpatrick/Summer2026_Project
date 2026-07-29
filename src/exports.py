"""Download tables and email-ready text for schedules."""

import pandas as pd


def build_export_tables(schedule, student_metrics=None):
    schedule = schedule.drop(columns=["assignment_index"], errors="ignore")
    if student_metrics is not None and not student_metrics.empty:
        metric_cols = [
            "student_id", "max_meetings_requested", "effective_max_meetings",
            "assigned_meetings", "raw_satisfaction", "max_possible_satisfaction",
            "normalized_satisfaction", "meeting_fulfillment_rate",
            "got_rank_1", "got_rank_2",
        ]
        available = [c for c in metric_cols if c in student_metrics.columns]
        schedule = schedule.merge(student_metrics[available], on="student_id", how="left")
    master = schedule.sort_values(["day", "start", "faculty", "student_id"]).copy()
    student = schedule.sort_values(["student_id", "day", "start"]).copy()
    faculty = schedule.sort_values(["faculty", "day", "start", "student_id"]).copy()
    return {
        "master_schedule": master,
        "student_schedules": student,
        "faculty_schedules": faculty,
        "student_diagnostics": student_metrics if student_metrics is not None else pd.DataFrame(),
        "student_email_text": _person_text(student, "student_id", "faculty"),
        "faculty_email_text": _person_text(faculty, "faculty", "student_id"),
    }


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def _person_text(schedule, person_col, counterpart_col):
    rows = []
    for person, group in schedule.groupby(person_col, sort=True):
        lines = [f"Schedule for {person}", ""]
        for r in group.sort_values(["day", "start"]).itertuples():
            lines.append(
                f"Day {r.day}, {r.start}-{r.end}: meet with {getattr(r, counterpart_col)}"
            )
        rows.append({"recipient": person, "schedule_text": "\n".join(lines)})
    return pd.DataFrame(rows)
