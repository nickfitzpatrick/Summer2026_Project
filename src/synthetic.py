"""Synthetic data generator.

This is a real deliverable, not a stub. It deliberately builds HARD instances:
- faculty popularity is skewed (a few faculty draw most interest)
- student interests cluster by research area, so preferences overlap and contend
- faculty availability has gaps, so popular faculty are not free in every slot

Outputs three CSVs that mirror what the real intake forms will collect:
  faculty.csv      one row per faculty with primary research area
  availability.csv long format: (faculty_id, slot_id) the faculty is free
  preferences.csv  long format: (student_id, faculty_id, rank) top-N ranked
"""

import random
import numpy as np
import pandas as pd

from config import Config, DEFAULT
from grid import build_grid

AREAS = [
    "Optimization", "Stochastic", "ML", "Supply Chain", "Finance", "Healthcare",
]


def generate(cfg: Config = DEFAULT):
    random.seed(cfg.random_seed)
    np.random.seed(cfg.random_seed)

    grid = build_grid(cfg)
    slots = grid["slot_id"].tolist()
    areas = AREAS[: cfg.num_research_areas]

    faculty = pd.DataFrame(
        {
            "faculty_id": [f"F{i+1:02d}" for i in range(cfg.num_faculty)],
            "name": [f"Prof {i+1:02d}" for i in range(cfg.num_faculty)],
            "area": [random.choice(areas) for _ in range(cfg.num_faculty)],
        }
    )

    # popularity: Zipf-like skew so a handful of faculty dominate demand
    pop = 1.0 / np.arange(1, cfg.num_faculty + 1)
    pop = pop / pop.sum()
    pop_map = dict(zip(faculty["faculty_id"], pop))

    # availability: each faculty free in a random contiguous-ish subset of slots
    avail_rows = []
    for fid in faculty["faculty_id"]:
        free_frac = random.uniform(0.5, 0.9)
        chosen = random.sample(slots, k=max(1, int(len(slots) * free_frac)))
        for s in chosen:
            avail_rows.append({"faculty_id": fid, "slot_id": s})
    availability = pd.DataFrame(avail_rows)

    # student preferences: clustered by a primary area plus skew toward popular faculty
    pref_rows = []
    for i in range(cfg.num_students):
        sid = f"S{i+1:02d}"
        primary = random.choice(areas)
        weights = []
        for fid, farea in zip(faculty["faculty_id"], faculty["area"]):
            w = pop_map[fid]
            if farea == primary:
                w *= 4.0          # strong pull toward own area
            weights.append(w)
        weights = np.array(weights)
        weights /= weights.sum()
        picks = np.random.choice(
            faculty["faculty_id"], size=cfg.prefs_per_student, replace=False, p=weights
        )
        for rank, fid in enumerate(picks, start=1):
            pref_rows.append({"student_id": sid, "faculty_id": fid, "rank": rank})
    preferences = pd.DataFrame(pref_rows)

    return faculty, availability, preferences, grid


if __name__ == "__main__":
    fac, avail, pref, grid = generate()
    fac.to_csv("data/faculty.csv", index=False)
    avail.to_csv("data/availability.csv", index=False)
    pref.to_csv("data/preferences.csv", index=False)
    grid.to_csv("data/grid.csv", index=False)
    print(f"faculty: {len(fac)}  availability rows: {len(avail)}  preference rows: {len(pref)}  slots: {len(grid)}")
