"""Visit-day structure: per-day hours plus arbitrary blocked events.

Staff define each of the two visit days independently: a start time, an end time,
and any number of blocked events (lunch, a welcome session, a coffee break). Any
time NOT blocked becomes available for student-faculty meetings.

This generalizes grid.build_grid, which only knew a single shared start/end and
one lunch block. The output grid has the same shape the solver already consumes:
columns slot_id, day, start_time, end_time. So the matcher needs no changes.

A DayPlan is plain data so it serializes straight to/from Streamlit session state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from config import Config


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%H:%M")


@dataclass
class Block:
    label: str
    start: str  # "HH:MM"
    end: str    # "HH:MM"


@dataclass
class DayPlan:
    day: int
    start: str = "09:00"
    end: str = "17:00"
    blocks: list = field(default_factory=list)  # list[Block]


def default_plans() -> list:
    """Two identical days, 9-5 with a noon lunch. The starting point staff edit."""
    return [
        DayPlan(day=d, start="09:00", end="17:00",
                blocks=[Block("Lunch", "12:00", "13:00")])
        for d in (1, 2)
    ]


def _slots_for_day(plan: DayPlan, cfg: Config) -> list:
    """Open meeting slots for one day, skipping any that overlap a blocked event."""
    step = timedelta(minutes=cfg.slot_minutes)
    meeting = timedelta(minutes=cfg.meeting_minutes)
    blocks = [(_t(b.start), _t(b.end)) for b in plan.blocks]

    rows = []
    cur, day_end = _t(plan.start), _t(plan.end)
    while cur + meeting <= day_end:
        m_end = cur + meeting
        blocked = any(cur < be and m_end > bs for bs, be in blocks)
        if not blocked:
            rows.append({
                "slot_id": f"D{plan.day}-S{len(rows) + 1}",
                "day": plan.day,
                "start_time": cur.strftime("%H:%M"),
                "end_time": m_end.strftime("%H:%M"),
            })
        cur += step
    return rows


def build_grid_from_plans(plans: list, cfg: Config) -> pd.DataFrame:
    """Build the solver grid from a list of DayPlan. Same columns as grid.build_grid."""
    rows = []
    for plan in plans:
        rows.extend(_slots_for_day(plan, cfg))
    return pd.DataFrame(rows, columns=["slot_id", "day", "start_time", "end_time"])
