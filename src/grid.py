"""Build the discrete slot grid the optimizer runs on.

The solver only ever sees slot_id. start/end clock times exist purely so the
final schedule can be rendered in human-readable form. Lunch is simply absent
from the grid, so no meeting can be placed there with no special constraint.
"""

from datetime import datetime, timedelta
import pandas as pd

from config import Config, DEFAULT


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%H:%M")


def build_grid(cfg: Config = DEFAULT) -> pd.DataFrame:
    rows = []
    step = timedelta(minutes=cfg.slot_minutes)
    lunch_s, lunch_e = _t(cfg.lunch_start), _t(cfg.lunch_end)

    for day in range(1, cfg.num_days + 1):
        cur = _t(cfg.day_start)
        end = _t(cfg.day_end)
        while cur + timedelta(minutes=cfg.meeting_minutes) <= end:
            meeting_end = cur + timedelta(minutes=cfg.meeting_minutes)
            in_lunch = cur < lunch_e and meeting_end > lunch_s
            if not in_lunch:
                rows.append(
                    {
                        "slot_id": f"D{day}-S{len([r for r in rows if r['day'] == day]) + 1}",
                        "day": day,
                        "start_time": cur.strftime("%H:%M"),
                        "end_time": meeting_end.strftime("%H:%M"),
                    }
                )
            cur += step

    return pd.DataFrame(rows)


if __name__ == "__main__":
    g = build_grid()
    print(g.to_string(index=False))
    print(f"\nTotal slots: {len(g)}  ({len(g[g.day == 1])} per day)")
