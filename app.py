"""IEOR Visit-Day Matching - staff app.

Run with:  streamlit run app.py

Designed for non-technical IEOR staff. Two ways to load data:
  1. Generate demo data to try the tool immediately.
  2. Upload the three CSVs collected from intake forms.
Then set the meeting length, click Match, review schedules, and download.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import streamlit as st

from config import Config
from synthetic import generate
from model import solve
from grid import build_grid
from run import render_schedules, compute_metrics

st.set_page_config(page_title="Visit-Day Matching", layout="wide")
st.title("Visit-Day Faculty Matching")
st.caption(
    "Match prospective students with the faculty they most want to meet across the two visit days."
)

# --- sidebar: settings ---
st.sidebar.header("Settings")
meeting_min = st.sidebar.number_input("Meeting length (minutes)", 5, 60, 20, step=5)
buffer_min = st.sidebar.number_input("Buffer between meetings (minutes)", 0, 30, 5, step=5)
day_start = st.sidebar.text_input("Day start", "09:00")
day_end = st.sidebar.text_input("Day end", "17:00")
time_limit = st.sidebar.slider("Solver time limit (seconds)", 5, 120, 30)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Each meeting occupies a {meeting_min + buffer_min}-minute slot. "
    "Faculty stay in their offices; students travel between them."
)


def make_config():
    return Config(
        meeting_minutes=meeting_min,
        buffer_minutes=buffer_min,
        day_start=day_start,
        day_end=day_end,
        solver_time_limit_s=time_limit,
    )


# --- data source ---
st.subheader("1. Load data")
source = st.radio(
    "Where should the data come from?",
    ["Generate demo data", "Upload CSV files"],
    horizontal=True,
)

faculty = availability = preferences = None
cfg = make_config()
grid = build_grid(cfg)

if source == "Generate demo data":
    c1, c2 = st.columns(2)
    n_fac = c1.number_input("Number of faculty", 3, 60, 15)
    n_stu = c2.number_input("Number of students", 3, 120, 25)
    demo_cfg = make_config()
    demo_cfg.num_faculty = int(n_fac)
    demo_cfg.num_students = int(n_stu)
    faculty, availability, preferences, grid = generate(demo_cfg)
    cfg = demo_cfg
    st.success(f"Generated {len(faculty)} faculty and {n_stu} students on a {len(grid)}-slot grid.")
else:
    st.caption(
        "Upload three files. faculty.csv (faculty_id, name, area), "
        "availability.csv (faculty_id, slot_id), preferences.csv (student_id, faculty_id, rank)."
    )
    fac_f = st.file_uploader("faculty.csv", type="csv")
    avail_f = st.file_uploader("availability.csv", type="csv")
    pref_f = st.file_uploader("preferences.csv", type="csv")
    if fac_f and avail_f and pref_f:
        faculty = pd.read_csv(fac_f)
        availability = pd.read_csv(avail_f)
        preferences = pd.read_csv(pref_f)
        st.success("Files loaded.")

# --- solve ---
st.subheader("2. Build the schedule")
if faculty is not None and st.button("Match students to faculty", type="primary"):
    with st.spinner("Optimizing schedule..."):
        assignments, status, obj = solve(faculty, availability, preferences, grid, cfg)

    if assignments.empty:
        st.error(f"No feasible schedule found (solver status: {status}). Check availability data.")
    else:
        st.session_state["result"] = {
            "assignments": assignments,
            "faculty": faculty,
            "preferences": preferences,
            "grid": grid,
            "status": status,
        }

# --- results ---
if "result" in st.session_state:
    r = st.session_state["result"]
    sched = render_schedules(r["assignments"], r["faculty"], r["grid"])
    mx = compute_metrics(r["assignments"], r["preferences"])

    st.subheader("3. Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total meetings", mx["total_meetings"])
    m2.metric("Got their #1 choice", f"{mx['top1_met']}/{mx['n_students']}")
    m3.metric("Avg top-3 met", f"{mx['top3_avg']:.2f}/3")
    m4.metric("Worst-off top-3", f"{mx['top3_worst']}/3")

    tab_stu, tab_fac = st.tabs(["By student", "By faculty"])

    with tab_stu:
        pick = st.selectbox("View a student", sorted(sched["student_id"].unique()))
        st.dataframe(
            sched[sched["student_id"] == pick][["day", "start", "end", "faculty"]],
            hide_index=True,
            use_container_width=True,
        )
        st.download_button(
            "Download all student schedules (CSV)",
            sched.to_csv(index=False),
            "student_schedules.csv",
            "text/csv",
        )

    with tab_fac:
        fpick = st.selectbox("View a faculty member", sorted(sched["faculty"].unique()))
        fac_view = sched[sched["faculty"] == fpick][["day", "start", "end", "student_id"]]
        st.dataframe(fac_view, hide_index=True, use_container_width=True)
        st.download_button(
            "Download full schedule (CSV)",
            sched.to_csv(index=False),
            "full_schedule.csv",
            "text/csv",
        )
