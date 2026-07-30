"""CP-SAT matching model.

Decision var x[s, f, t] = 1 if student s meets faculty f in slot t.

Objective prioritizes SATISFACTION over raw meeting count:
  1. convex rank value: a #1 choice is worth far more than several low-ranked
     meetings combined, so the solver chases the faculty students actually want
     rather than padding counts with easy-to-schedule low picks
  2. normalized max-min floor: lift the satisfaction percentage of the worst-off student, 
     ensuring fairness even when students have different numbers of total preferences.

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
    num_slots = len(slots)
    
    avail = defaultdict(set)
    for _, r in availability.iterrows():
        avail[r["faculty_id"]].add(r["slot_id"])

    # convex rank value: value(rank) = round(rank_base * rank_decay^(rank-1)).
    # Tracks raw values per student-faculty pair and groups them by student to calculate individual V_max.
    pref_val = {}
    student_prefs = defaultdict(list)
    
    for _, r in preferences.iterrows():
        sid, fid, rank = r["student_id"], r["faculty_id"], r["rank"]
        val = round(cfg.rank_base * (cfg.rank_decay ** (rank - 1)))
        pref_val[(sid, fid)] = val
        student_prefs[sid].append(val)

    students = preferences["student_id"].unique().tolist()

    m = cp_model.CpModel()
    x = {}
    for (sid, fid), val in pref_val.items():
        for t in slots:
            if t in avail[fid]:
                x[(sid, fid, t)] = m.NewBoolVar(f"x_{sid}_{fid}_{t}")

    # faculty / student slot constraints
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

    # --- NORMALIZED FAIRNESS FLOOR MODIFICATION ---
    
    # Scale factor for CP-SAT integer precision (10,000 = 100.00% satisfaction)
    SCALE = 10000 
    
    # Integer variable representing the worst-off student's satisfaction % (0 to 10,000)
    floor_pct = m.NewIntVar(0, SCALE, "floor_pct")
    
    valid_v_maxes = []
    for sid in students:
        # Sort their preference values descending to find their absolute best possible outcomes
        sorted_vals = sorted(student_prefs[sid], reverse=True)
        
        # Max meetings a student can physically have is bounded by the total time slots available
        max_possible_meetings = min(len(sorted_vals), num_slots)
        v_max_s = sum(sorted_vals[:max_possible_meetings])
        
        # Apply fairness constraint only to active students with valid preference metrics
        if v_max_s > 0:
            valid_v_maxes.append(v_max_s)
            # Linearized integer equivalent of: floor_pct / SCALE <= sat[sid] / v_max_s
            m.Add(floor_pct * v_max_s <= sat[sid] * SCALE)

    # Calculate the mean V_max across all active students to scale the weight properly
    mean_v_max = sum(valid_v_maxes) / len(valid_v_maxes) if valid_v_maxes else 100
    
    # Convert cfg.floor_weight (e.g. 50) out of the original absolute value scale 
    # and adjust it into the new 10,000x relative percentage scale space.
    scaled_floor_weight = max(1, round((cfg.floor_weight * mean_v_max) / SCALE))
    
    m.Maximize(pref_term + scaled_floor_weight * floor_pct)
    # -----------------------------------------------

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.solver_time_limit_s
    status = solver.Solve(m)

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (sid, fid, t), var in x.items():
            if solver.Value(var):
                assignments.append({"student_id": sid, "faculty_id": fid, "slot_id": t})

    return pd.DataFrame(assignments), solver.StatusName(status), solver.ObjectiveValue()
