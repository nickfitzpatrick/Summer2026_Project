"""End-to-end pipeline: synthetic data -> solve -> render schedules.

This is the entry point the team builds the Streamlit app around. Run with:
  python src/run.py
"""

import pandas as pd

from config import DEFAULT
from synthetic import generate
from model import solve


def render_schedules(assignments, faculty, grid):
    fac_name = dict(zip(faculty["faculty_id"], faculty["name"]))
    times = grid.set_index("slot_id")[["day", "start_time", "end_time"]].to_dict("index")

    rows = []
    for _, a in assignments.iterrows():
        t = times[a["slot_id"]]
        rows.append(
            {
                "student_id": a["student_id"],
                "faculty": fac_name[a["faculty_id"]],
                "day": t["day"],
                "start": t["start_time"],
                "end": t["end_time"],
                "slot_id": a["slot_id"],
            }
        )
    sched = pd.DataFrame(rows).sort_values(["student_id", "day", "start"])
    return sched


def main():
    cfg = DEFAULT
    faculty, availability, preferences, grid = generate(cfg)
    assignments, status, obj = solve(faculty, availability, preferences, grid, cfg)

    sched = render_schedules(assignments, faculty, grid)

    n_students = preferences["student_id"].nunique()
    met_per_student = assignments.groupby("student_id").size()
    print(f"solver status: {status}   objective: {obj:.0f}")
    print(f"total meetings scheduled: {len(assignments)}")
    print(f"avg meetings per student: {len(assignments) / n_students:.1f}")
    print(f"min / max meetings per student: {met_per_student.min()} / {met_per_student.max()}")

    # satisfaction metrics
    got = assignments.merge(preferences, on=["student_id", "faculty_id"], how="left")
    top1 = got[got["rank"] == 1]["student_id"].nunique()
    top3 = got[got["rank"] <= 3].groupby("student_id").size()
    print(f"students who got their #1 choice: {top1} / {n_students}")
    print(f"avg top-3 choices met per student: {top3.mean():.2f} / 3")
    print(f"worst-off student got {top3.min()} of their top 3")

    sched.to_csv("outputs/student_schedules.csv", index=False)
    print("\nwrote outputs/student_schedules.csv")
    print("\nsample (one student):")
    sample_sid = sched["student_id"].iloc[0]
    print(sched[sched["student_id"] == sample_sid].to_string(index=False))


if __name__ == "__main__":
    main()
