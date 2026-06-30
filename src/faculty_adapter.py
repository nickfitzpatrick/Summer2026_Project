"""Adapt faculty availability form responses into solver-ready availability."""

import pandas as pd

from faculty_form_spec import Q_FIRST, Q_LAST, Q_EMAIL, _day_avail_title


def adapt_faculty_availability(responses, faculty, grid):
    """Return (availability_df, warnings).

    The response sheet is expected to use the question titles from
    faculty_form_spec.py. Faculty are matched by faculty_id, email, or name,
    depending on which columns are available in the uploaded roster.
    """
    warnings = []
    if "faculty_id" not in faculty.columns:
        return pd.DataFrame(columns=["faculty_id", "slot_id"]), [
            "Faculty list must include faculty_id before responses can be converted to availability.csv."
        ]

    faculty = faculty.copy()
    faculty["faculty_id"] = faculty["faculty_id"].astype(str).str.strip()

    by_id = _lookup(faculty, "faculty_id")
    by_email = _lookup(faculty, "email")
    by_name = {str(r["name"]).strip().lower(): r["faculty_id"] for _, r in faculty.iterrows()}

    slot_by_day_window = {}
    for r in grid.itertuples():
        slot_by_day_window[(int(r.day), f"{r.start_time}-{r.end_time}")] = r.slot_id

    rows = []
    for idx, r in responses.iterrows():
        who = _faculty_id_for_row(r, by_id, by_email, by_name)
        label = _row_label(r, idx)
        if not who:
            warnings.append(f"{label}: could not match this response to a faculty_id; skipped.")
            continue

        seen = set()
        for day in sorted(grid["day"].unique()):
            col = _day_avail_title(int(day))
            raw = r.get(col)
            if pd.isna(raw) or not str(raw).strip():
                continue
            for window in _split_multi(str(raw)):
                slot_id = slot_by_day_window.get((int(day), window))
                if slot_id is None:
                    warnings.append(f"{label}: '{window}' is not a valid Day {int(day)} slot; skipped.")
                    continue
                key = (who, slot_id)
                if key not in seen:
                    rows.append({"faculty_id": who, "slot_id": slot_id})
                    seen.add(key)

        if not seen:
            warnings.append(f"{label}: no valid available time windows were selected.")

    availability = pd.DataFrame(rows, columns=["faculty_id", "slot_id"])
    return availability, warnings


def _lookup(df, col):
    if col not in df.columns:
        return {}
    return {
        str(v).strip().lower(): str(fid).strip()
        for v, fid in zip(df[col], df["faculty_id"])
        if pd.notna(v) and str(v).strip()
    }


def _faculty_id_for_row(row, by_id, by_email, by_name):
    direct = str(row.get("faculty_id", "")).strip().lower()
    if direct in by_id:
        return by_id[direct]

    email = str(row.get(Q_EMAIL, row.get("email", ""))).strip().lower()
    if email in by_email:
        return by_email[email]

    name = str(row.get("name", "")).strip().lower()
    if not name:
        name = f"{row.get(Q_FIRST, '')} {row.get(Q_LAST, '')}".strip().lower()
    return by_name.get(name)


def _row_label(row, idx):
    email = row.get(Q_EMAIL, row.get("email", ""))
    name = row.get("name", "") or f"{row.get(Q_FIRST, '')} {row.get(Q_LAST, '')}".strip()
    return str(name or email or f"Row {idx + 2}")


def _split_multi(raw):
    return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
