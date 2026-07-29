"""Central config for the visit-day matching tool.

All tunable numbers live here so staff can adjust without touching logic.
Slot length default: 20 min meeting + 5 min buffer = 25 min block.
Both visit days use an identical grid. Faculty sit in fixed offices.
"""

from dataclasses import dataclass, field


@dataclass
class Config:
    meeting_minutes: int = 20
    buffer_minutes: int = 5

    day_start: str = "09:00"
    day_end: str = "17:00"
    lunch_start: str = "12:00"
    lunch_end: str = "13:00"

    num_days: int = 2

    # faculty source: real roster by default, invented list as a fallback
    use_real_roster: bool = True
    roster_path: str = "IEOR_Faculty_Roster.xlsx"

    # synthetic data sizing
    num_faculty: int = 25             # only used when use_real_roster is False
    num_students: int = 25
    prefs_per_student: int = 8        # top-N ranked faculty per student
    default_max_meetings_requested: int = 4
    minimum_ranked_faculty_threshold: int = 3
    num_research_areas: int = 6       # only used when use_real_roster is False

    # objective weights
    # rank value is convex: a top choice is worth far more than several low ranks
    # combined, so the solver prioritizes the faculty students actually want.
    rank_decay: float = 0.6           # value(rank r) ~ base * decay^(r-1)
    rank_base: int = 100
    floor_weight: int = 50            # weight on the max-min satisfaction floor
    solver_time_limit_s: int = 30

    random_seed: int = 42

    @property
    def slot_minutes(self) -> int:
        return self.meeting_minutes + self.buffer_minutes


DEFAULT = Config()
