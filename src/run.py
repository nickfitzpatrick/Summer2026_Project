"""End-to-end pipeline: synthetic data -> solve -> render schedules.

This is the entry point the team builds the Streamlit app around. Run with:
  python src/run.py
"""

import pandas as pd

from config import DEFAULT
from synthetic import generate


def render_schedules(assignments, faculty, grid):
    fac_name = dict(zip(faculty["faculty_id"], faculty["name"]))
    times = grid.set_index("slot_id")[["day", "start_time", "end_time"]].to_dict("index")

    rows = []
    for idx, a in assignments.iterrows():
        t = times[a["slot_id"]]
        rows.append(
            {
                "assignment_index": idx,
                "student_id": a["student_id"],
                "faculty_id": a["faculty_id"],
                "faculty": fac_name[a["faculty_id"]],
                "day": t["day"],
                "start": t["start_time"],
                "end": t["end_time"],
                "slot_id": a["slot_id"],
                "locked": bool(a.get("locked", False)),
            }
        )
    sched = pd.DataFrame(rows).sort_values(["student_id", "day", "start"])
    return sched


def compute_metrics(assignments, preferences):
    """Satisfaction-focused metrics shared by the CLI and the app."""
    n_students = preferences["student_id"].nunique()
    got = assignments.merge(preferences, on=["student_id", "faculty_id"], how="left")
    top3 = (
        got[got["rank"] <= 3]
        .groupby("student_id")
        .size()
        .reindex(preferences["student_id"].unique())
        .fillna(0)
    )
    met_per_student = (
        assignments.groupby("student_id").size().reindex(preferences["student_id"].unique()).fillna(0)
    )
    return {
        "total_meetings": len(assignments),
        "avg_meetings": len(assignments) / n_students if n_students else 0,
        "min_meetings": int(met_per_student.min()),
        "max_meetings": int(met_per_student.max()),
        "top1_met": int(got[got["rank"] == 1]["student_id"].nunique()),
        "n_students": n_students,
        "top3_avg": float(top3.mean()),
        "top3_worst": int(top3.min()),
    }


def main():
    from model import solve

    cfg = DEFAULT
    faculty, availability, preferences, grid = generate(cfg)
    assignments, status, obj = solve(faculty, availability, preferences, grid, cfg)

    sched = render_schedules(assignments, faculty, grid)
    mx = compute_metrics(assignments, preferences)

    print(f"solver status: {status}   objective: {obj:.0f}")
    print(f"total meetings scheduled: {mx['total_meetings']}")
    print(f"avg meetings per student: {mx['avg_meetings']:.1f}")
    print(f"min / max meetings per student: {mx['min_meetings']} / {mx['max_meetings']}")
    print(f"students who got their #1 choice: {mx['top1_met']} / {mx['n_students']}")
    print(f"avg top-3 choices met per student: {mx['top3_avg']:.2f} / 3")
    print(f"worst-off student got {mx['top3_worst']} of their top 3")

    sched.to_csv("outputs/student_schedules.csv", index=False)
    print("\nwrote outputs/student_schedules.csv")
    print("\nsample (one student):")
    sample_sid = sched["student_id"].iloc[0]
    print(sched[sched["student_id"] == sample_sid].to_string(index=False))


if __name__ == "__main__":
    main()
