"""CP-SAT matching model.

Decision var x[s, f, t] = 1 if student s meets faculty f in slot t.

Objective prioritizes SATISFACTION over raw meeting count:
  1. convex rank value: a #1 choice is worth far more than several low-ranked
     meetings combined, so the solver chases the faculty students actually want
     rather than padding counts with easy-to-schedule low picks
  2. max-min floor: lift the satisfaction of the worst-off student, so no one
     is starved to feed popular faculty

Constraints:
  - a faculty does at most one meeting per slot
  - a student does at most one meeting per slot
  - a meeting can only use a slot where the faculty is available
  - a given student-faculty pair meets at most once
  - a student only meets faculty they ranked (keeps the model focused)
"""

from collections import defaultdict
import pandas as pd
from ortools.sat.python import cp_model

from config import Config, DEFAULT


def solve(faculty, availability, preferences, grid, cfg: Config = DEFAULT):
    slots = grid["slot_id"].tolist()
    avail = defaultdict(set)
    for _, r in availability.iterrows():
        avail[r["faculty_id"]].add(r["slot_id"])

    # convex rank value: value(rank) = round(rank_base * rank_decay^(rank-1)).
    # with base=100, decay=0.6: rank1=100, rank2=60, rank3=36, ... so a single
    # top choice outweighs a fistful of low-ranked meetings.
    pref_val = {}
    for _, r in preferences.iterrows():
        pref_val[(r["student_id"], r["faculty_id"])] = round(
            cfg.rank_base * (cfg.rank_decay ** (r["rank"] - 1))
        )

    students = preferences["student_id"].unique().tolist()

    m = cp_model.CpModel()
    x = {}
    for (sid, fid), val in pref_val.items():
        for t in slots:
            if t in avail[fid]:
                x[(sid, fid, t)] = m.NewBoolVar(f"x_{sid}_{fid}_{t}")

    # faculty: one meeting per slot
    fac_slot = defaultdict(list)
    stu_slot = defaultdict(list)
    pair_vars = defaultdict(list)
    for (sid, fid, t), var in x.items():
        fac_slot[(fid, t)].append(var)
        stu_slot[(sid, t)].append(var)
        pair_vars[(sid, fid)].append(var)

    for vs in fac_slot.values():
        m.AddAtMostOne(vs)
    for vs in stu_slot.values():
        m.AddAtMostOne(vs)
    for vs in pair_vars.values():
        m.AddAtMostOne(vs)   # a pair meets at most once

    # total preference value captured across all meetings
    pref_term = sum(pref_val[(sid, fid)] * var for (sid, fid, t), var in x.items())

    # per-student satisfaction = sum of rank-values that student actually received
    sat = {}
    for sid in students:
        sat[sid] = sum(
            pref_val[(s2, fid)] * var
            for (s2, fid, t), var in x.items()
            if s2 == sid
        )

    # max-min floor: maximize the satisfaction of the worst-off student
    max_possible = cfg.rank_base * cfg.prefs_per_student
    floor = m.NewIntVar(0, max_possible, "floor")
    for sid in students:
        m.Add(floor <= sat[sid])

    m.Maximize(pref_term + cfg.floor_weight * floor)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.solver_time_limit_s
    status = solver.Solve(m)

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (sid, fid, t), var in x.items():
            if solver.Value(var):
                assignments.append({"student_id": sid, "faculty_id": fid, "slot_id": t})

    return pd.DataFrame(assignments), solver.StatusName(status), solver.ObjectiveValue()
