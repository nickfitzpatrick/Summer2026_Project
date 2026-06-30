"""Schedule diagnostics for staff review."""

import pandas as pd


def build_diagnostics(assignments, faculty, availability, preferences, grid):
    faculty_capacity = _faculty_capacity(faculty, availability, assignments)
    student_outcomes = _student_outcomes(assignments, preferences)
    demand = _faculty_demand(faculty, preferences, assignments)
    summary = _summary(assignments, availability, preferences, student_outcomes)
    unassigned = _unassigned_preferences(assignments, preferences, faculty)

    warnings = []
    low = student_outcomes[student_outcomes["top3_met"] == 0]
    if not low.empty:
        warnings.append(f"{len(low)} student(s) did not receive any top-3 preference meetings.")
    no_meetings = student_outcomes[student_outcomes["meetings"] == 0]
    if not no_meetings.empty:
        warnings.append(f"{len(no_meetings)} student(s) received no meetings.")
    unused = faculty_capacity[
        (faculty_capacity["available_slots"] > 0) & (faculty_capacity["scheduled_meetings"] == 0)
    ]
    if not unused.empty:
        warnings.append(f"{len(unused)} available faculty have no scheduled meetings.")
    notes = _staff_notes(faculty_capacity, student_outcomes, demand, unassigned)

    return {
        "summary": summary,
        "faculty_capacity": faculty_capacity,
        "student_outcomes": student_outcomes,
        "faculty_demand": demand,
        "unassigned_preferences": unassigned,
        "warnings": warnings,
        "notes": notes,
    }


def _staff_notes(faculty_capacity, student_outcomes, demand, unassigned):
    notes = []

    no_rankings = demand[demand["total_rankings"] == 0]
    if not no_rankings.empty:
        names = _names(no_rankings)
        notes.append({
            "level": "Review",
            "title": f"{len(no_rankings)} faculty were not selected by any student",
            "detail": (
                f"{names}. Consider whether these faculty should remain in the form, "
                "or whether students need clearer research-area guidance."
            ),
        })

    available_unused = faculty_capacity[
        (faculty_capacity["available_slots"] > 0) & (faculty_capacity["scheduled_meetings"] == 0)
    ]
    if not available_unused.empty:
        names = _names(available_unused)
        notes.append({
            "level": "Review",
            "title": f"{len(available_unused)} available faculty received no meetings",
            "detail": (
                f"{names}. This can happen when no students ranked them or when higher-priority "
                "matches used the available slots."
            ),
        })

    no_availability = faculty_capacity[faculty_capacity["available_slots"] == 0]
    if not no_availability.empty:
        notes.append({
            "level": "Action",
            "title": f"{len(no_availability)} faculty have no availability",
            "detail": f"{_names(no_availability)}. Ask for availability or remove them before the final run.",
        })

    bottlenecks = demand[
        (demand["top3_rankings"] >= 3) & (demand["unmet_rankings"] > demand["scheduled_meetings"])
    ].head(5)
    if not bottlenecks.empty:
        notes.append({
            "level": "Bottleneck",
            "title": "Popular faculty may be limiting student satisfaction",
            "detail": (
                f"{_names(bottlenecks)}. If possible, add availability for these faculty "
                "or ask students for backup preferences."
            ),
        })

    low_students = student_outcomes[
        (student_outcomes["meetings"] == 0) | (student_outcomes["top3_met"] == 0)
    ].head(8)
    if not low_students.empty:
        notes.append({
            "level": "Action",
            "title": f"{len(low_students)} student(s) need a closer look",
            "detail": (
                "These students received no meetings or no top-3 meetings: "
                + ", ".join(low_students["student_id"].astype(str).tolist())
                + ". Consider manual adjustment or collecting more preferences."
            ),
        })

    high_rank_unassigned = unassigned[unassigned["rank"] <= 2].head(8)
    if not high_rank_unassigned.empty:
        notes.append({
            "level": "Review",
            "title": "Some first- or second-choice preferences were not assigned",
            "detail": (
                "Examples: "
                + "; ".join(
                    f"{r.student_id} -> {r.faculty} (rank {r.rank})"
                    for r in high_rank_unassigned.itertuples()
                )
            ),
        })

    if not notes:
        notes.append({
            "level": "OK",
            "title": "No major scheduling issues detected",
            "detail": "Review the detailed tables, then export the final schedules.",
        })
    return notes


def _names(df, limit=6):
    names = df["name"].astype(str).tolist()
    shown = ", ".join(names[:limit])
    if len(names) > limit:
        shown += f", and {len(names) - limit} more"
    return shown


def _summary(assignments, availability, preferences, student_outcomes):
    total_capacity = len(availability.drop_duplicates(["faculty_id", "slot_id"]))
    total_meetings = len(assignments)
    n_students = preferences["student_id"].nunique()
    return {
        "total_meetings": total_meetings,
        "total_capacity": total_capacity,
        "utilization_rate": total_meetings / total_capacity if total_capacity else 0,
        "students": n_students,
        "avg_meetings_per_student": total_meetings / n_students if n_students else 0,
        "lowest_student_meetings": int(student_outcomes["meetings"].min()) if not student_outcomes.empty else 0,
        "avg_rank_value": float(student_outcomes["avg_rank"].mean()) if not student_outcomes.empty else 0,
    }


def _faculty_capacity(faculty, availability, assignments):
    capacity = availability.drop_duplicates(["faculty_id", "slot_id"]).groupby("faculty_id").size()
    used = assignments.groupby("faculty_id").size()
    out = faculty[["faculty_id", "name"]].copy()
    out["available_slots"] = out["faculty_id"].map(capacity).fillna(0).astype(int)
    out["scheduled_meetings"] = out["faculty_id"].map(used).fillna(0).astype(int)
    out["unused_capacity"] = out["available_slots"] - out["scheduled_meetings"]
    out["utilization"] = out.apply(
        lambda r: r["scheduled_meetings"] / r["available_slots"] if r["available_slots"] else 0,
        axis=1,
    )
    return out.sort_values(["scheduled_meetings", "available_slots"], ascending=False)


def _student_outcomes(assignments, preferences):
    students = pd.Index(preferences["student_id"].unique(), name="student_id")
    got = assignments.merge(preferences, on=["student_id", "faculty_id"], how="left")
    meetings = assignments.groupby("student_id").size().reindex(students).fillna(0).astype(int)
    top1 = got[got["rank"] == 1].groupby("student_id").size().reindex(students).fillna(0).astype(int)
    top3 = got[got["rank"] <= 3].groupby("student_id").size().reindex(students).fillna(0).astype(int)
    avg_rank = got.groupby("student_id")["rank"].mean().reindex(students)
    prefs_count = preferences.groupby("student_id")["faculty_id"].nunique().reindex(students).fillna(0).astype(int)
    return pd.DataFrame({
        "student_id": students,
        "ranked_faculty": prefs_count.values,
        "meetings": meetings.values,
        "top1_met": top1.values,
        "top3_met": top3.values,
        "avg_rank": avg_rank.fillna(0).round(2).values,
    }).sort_values(["meetings", "top3_met", "avg_rank"], ascending=[True, True, True])


def _faculty_demand(faculty, preferences, assignments):
    demand = preferences.groupby("faculty_id").size()
    top3 = preferences[preferences["rank"] <= 3].groupby("faculty_id").size()
    used = assignments.groupby("faculty_id").size()
    out = faculty[["faculty_id", "name"]].copy()
    out["total_rankings"] = out["faculty_id"].map(demand).fillna(0).astype(int)
    out["top3_rankings"] = out["faculty_id"].map(top3).fillna(0).astype(int)
    out["scheduled_meetings"] = out["faculty_id"].map(used).fillna(0).astype(int)
    out["unmet_rankings"] = out["total_rankings"] - out["scheduled_meetings"]
    return out.sort_values(["total_rankings", "top3_rankings"], ascending=False)


def _unassigned_preferences(assignments, preferences, faculty):
    assigned_pairs = set(zip(assignments["student_id"], assignments["faculty_id"]))
    rows = preferences[
        ~preferences.apply(lambda r: (r["student_id"], r["faculty_id"]) in assigned_pairs, axis=1)
    ].copy()
    if rows.empty:
        return pd.DataFrame(columns=["student_id", "faculty_id", "faculty", "rank"])
    names = dict(zip(faculty["faculty_id"], faculty["name"]))
    rows["faculty"] = rows["faculty_id"].map(names).fillna(rows["faculty_id"])
    return rows[["student_id", "faculty_id", "faculty", "rank"]].sort_values(["rank", "student_id"])
