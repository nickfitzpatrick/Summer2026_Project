"""Student-level request limits and normalized satisfaction metrics."""

import pandas as pd

from config import DEFAULT


MAX_COL = "max_meetings_requested"


def student_request_table(preferences, grid, students=None, cfg=DEFAULT):
    """Return one row per student with requested/effective max meeting counts."""
    student_ids = pd.Index(preferences["student_id"].astype(str).unique(), name="student_id")
    ranked = (
        preferences.assign(student_id=preferences["student_id"].astype(str))
        .groupby("student_id")["faculty_id"]
        .nunique()
        .reindex(student_ids)
        .fillna(0)
        .astype(int)
    )
    requested = _requested_map(student_ids, students, cfg)
    available_slots = len(grid)

    out = pd.DataFrame({
        "student_id": student_ids,
        MAX_COL: [requested[sid] for sid in student_ids],
        "ranked_faculty": ranked.values,
    })
    out["effective_max_meetings"] = out.apply(
        lambda r: int(max(0, min(r[MAX_COL], r["ranked_faculty"], available_slots))),
        axis=1,
    )
    return out


def student_satisfaction_table(assignments, preferences, grid, students=None, cfg=DEFAULT):
    """Return normalized satisfaction and meeting fulfillment per student."""
    req = student_request_table(preferences, grid, students, cfg)
    prefs = preferences.copy()
    prefs["student_id"] = prefs["student_id"].astype(str)
    prefs["rank_value"] = prefs["rank"].apply(lambda rank: rank_value(rank, cfg))

    assigned = assignments.copy()
    if assigned.empty:
        assigned = pd.DataFrame(columns=["student_id", "faculty_id", "slot_id"])
    assigned["student_id"] = assigned["student_id"].astype(str)

    got = assigned.merge(
        prefs[["student_id", "faculty_id", "rank", "rank_value"]],
        on=["student_id", "faculty_id"],
        how="left",
    )
    assigned_meetings = got.groupby("student_id").size()
    raw = got.groupby("student_id")["rank_value"].sum()
    rank1 = got[got["rank"] == 1].groupby("student_id").size()
    rank2 = got[got["rank"] == 2].groupby("student_id").size()

    max_possible = _max_possible_by_student(prefs, req)
    out = req.copy()
    out["assigned_meetings"] = out["student_id"].map(assigned_meetings).fillna(0).astype(int)
    out["raw_satisfaction"] = out["student_id"].map(raw).fillna(0).round(2)
    out["max_possible_satisfaction"] = out["student_id"].map(max_possible).fillna(0).round(2)
    out["normalized_satisfaction"] = out.apply(
        lambda r: _safe_ratio(r["raw_satisfaction"], r["max_possible_satisfaction"]),
        axis=1,
    )
    out["meeting_fulfillment_rate"] = out.apply(
        lambda r: _safe_ratio(r["assigned_meetings"], r["effective_max_meetings"]),
        axis=1,
    )
    out["got_rank_1"] = out["student_id"].map(rank1).fillna(0).astype(int) > 0
    out["got_rank_2"] = out["student_id"].map(rank2).fillna(0).astype(int) > 0
    return out


def rank_value(rank, cfg=DEFAULT):
    return round(cfg.rank_base * (cfg.rank_decay ** (int(rank) - 1)), 2)


def _requested_map(student_ids, students, cfg):
    default = cfg.default_max_meetings_requested
    requested = {sid: default for sid in student_ids}
    if students is None or MAX_COL not in getattr(students, "columns", []):
        return requested
    sid_col = "student_id" if "student_id" in students.columns else None
    if sid_col is None:
        return requested
    for _, row in students.iterrows():
        sid = str(row.get(sid_col, "")).strip()
        if sid in requested:
            requested[sid] = _clean_positive_int(row.get(MAX_COL), default)
    return requested


def _clean_positive_int(value, default):
    try:
        if pd.isna(value) or str(value).strip() == "":
            return default
        parsed = int(float(value))
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _max_possible_by_student(prefs, req):
    limit = dict(zip(req["student_id"], req["effective_max_meetings"]))
    out = {}
    for sid, group in prefs.sort_values("rank").groupby("student_id"):
        k = limit.get(sid, 0)
        out[sid] = float(group.head(k)["rank_value"].sum()) if k else 0.0
    return out


def _safe_ratio(num, den):
    den = float(den)
    return 0.0 if den <= 0 else float(num) / den
