"""Single source of truth for the faculty availability form.

Parallel to form_spec.py (the student form). Each faculty tells us, for each of
the two visit days, which time windows they can take meetings in, plus their
office location. The question titles double as response-sheet column headers so a
future adapter can read them back without drift.

Availability is collected as a checkbox grid of meeting windows per day. The
windows offered come from the visit-day structure staff set up, so the form can
never offer a slot that does not exist in the schedule.
"""

Q_FIRST = "First Name"
Q_LAST = "Last Name"
Q_EMAIL = "Email"
Q_OFFICE = "Office location"


def _day_avail_title(day: int) -> str:
    return f"Day {day}: select every time window you are available"


def _windows_for_day(grid, day: int) -> list:
    """Human-readable meeting windows for a day, e.g. '09:00-09:20'."""
    rows = grid[grid["day"] == day]
    return [f"{r.start_time}-{r.end_time}" for r in rows.itertuples()]


def build_faculty_spec(grid) -> dict:
    """Return a faculty availability form spec from the visit-day grid.

    Same builder-agnostic shape as the student spec: each question has a type,
    title, and options. grid is the DataFrame from visit_days.build_grid_from_plans.
    """
    days = sorted(grid["day"].unique())

    questions = [
        {"type": "text", "title": Q_FIRST, "required": True},
        {"type": "text", "title": Q_LAST, "required": True},
        {"type": "email", "title": Q_EMAIL, "required": True},
        {"type": "text", "title": Q_OFFICE, "required": False,
         "help": "Where students should come to meet you."},
    ]

    for day in days:
        windows = _windows_for_day(grid, day)
        questions.append({
            "type": "checkbox",
            "title": _day_avail_title(int(day)),
            "options": windows,
            "required": False,
            "help": "Leave a day blank if you cannot meet that day.",
        })

    return {
        "title": "IEOR Visit Day - Faculty Availability",
        "description": (
            "Tell us when you can meet prospective students during visit day. "
            "Check every time window you are free; unchecked windows are treated "
            "as unavailable."
        ),
        "days": [int(d) for d in days],
        "questions": questions,
    }
