"""IEOR Visit-Day Matching - staff app.

Run with:  streamlit run app.py

Designed for non-technical IEOR staff. The workflow runs left to right across the
tabs: read the Overview, lay out the two visit days, collect student preferences
and faculty availability via Google Forms, then build the optimal schedule.
"""

import os
import sys
import hmac

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import streamlit as st

from config import Config
from synthetic import generate
from model import solve
from run import render_schedules, compute_metrics
from visit_days import Block, default_plans, build_grid_from_plans
from validation import validate_solver_inputs
from diagnostics import build_diagnostics
from exports import build_export_tables, to_csv_bytes
from student_metrics import MAX_COL

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "logo.png")
ROSTER_XLSX = os.path.join(HERE, "IEOR_Faculty_Roster.xlsx")
SAMPLE_DIR = os.path.join(HERE, "sample_data")

# Berkeley IEOR palette
NAVY = "#002677"
NAVY_MID = "#1a4672"
GOLD = "#fdb517"
GOLD_SOFT = "#ffe3a3"
BAND = "#edf3f6"
INK = "#12100b"

st.set_page_config(page_title="Visit-Day Matching", layout="wide", page_icon=LOGO)


def _configured_password():
    try:
        return st.secrets.get("APP_PASSWORD", "")
    except Exception:
        return os.environ.get("APP_PASSWORD", "")


def require_login():
    password = _configured_password()
    if not password:
        st.warning(
            "Access password is not configured. Set APP_PASSWORD in Streamlit Secrets "
            "before using real visit-day data."
        )
        return

    if st.session_state.get("authenticated"):
        return

    st.markdown("## IEOR Visit-Day Matching")
    st.caption("Enter the internal access password to continue.")
    entered = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if hmac.compare_digest(entered, password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


require_login()

st.markdown(
    f"""
    <style>
      /* base type: comfortable, not oversized */
      html, body, [class*="css"], .stMarkdown, p, label, .stCaption {{ font-size: 0.95rem; }}
      .block-container {{ padding-top: 2.4rem; max-width: 1240px; padding-left: 2.2rem; padding-right: 2.2rem; }}
      h1, h2, h3, h4 {{ color: {NAVY}; font-weight: 700; letter-spacing: -0.01em; }}
      p {{ line-height: 1.45; }}

      /* hide the (now empty) sidebar entirely */
      section[data-testid="stSidebar"] {{ display: none; }}

      /* tab bar: roomier, clearer active state */
      .stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; border-bottom: 2px solid {BAND}; }}
      .stTabs [data-baseweb="tab"] {{ font-size: 0.95rem; font-weight: 700; padding: 0.45rem 0.75rem; }}
      .stTabs [aria-selected="true"] {{ color: {NAVY}; }}

      .stButton > button[kind="primary"] {{
        background: {GOLD}; color: {INK}; border: none; font-weight: 700;
        border-radius: 10px; padding: 0.55rem 1.4rem; font-size: 0.98rem;
      }}
      .stButton > button[kind="primary"]:hover {{ background: #e7a40e; color: {INK}; }}
      .stButton > button[kind="secondary"] {{ border-radius: 10px; font-weight: 600; }}
      /* keep button labels on one line (e.g. the Remove buttons) */
      .stButton > button {{ white-space: nowrap; }}

      /* numbered step headers */
      .step {{ color: {NAVY}; font-size: 1.18rem; font-weight: 700; margin: 1.05rem 0 0.45rem; }}
      .step span {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 1.75rem; height: 1.75rem; margin-right: 0.55rem; border-radius: 50%;
        background: {NAVY}; color: #fff; font-size: 0.95rem;
      }}

      /* result stat cards */
      .cardrow {{ display: flex; gap: 0.8rem; margin: 0.35rem 0 1rem; }}
      .card {{
        flex: 1; border-radius: 10px; padding: 0.95rem 1.05rem; color: #fff;
        box-shadow: 0 1px 4px rgba(0,0,0,0.10);
      }}
      .card.navy {{ background: {NAVY}; }}
      .card.gold {{ background: {GOLD}; color: {INK}; }}
      .card .label {{ font-size: 0.92rem; opacity: 0.9; font-weight: 600; }}
      .card .value {{ font-size: 2rem; font-weight: 800; line-height: 1.05; margin-top: 0.15rem; }}
      .card.navy .value {{ color: {GOLD}; }}

      .tag {{
        display: inline-block; background: {GOLD_SOFT}; color: {NAVY};
        border-radius: 6px; padding: 0.2rem 0.65rem; font-size: 0.88rem; font-weight: 700;
      }}

      /* branded confirmation notice */
      .notice {{
        background: {BAND}; border-left: 4px solid {GOLD}; color: {NAVY};
        border-radius: 10px; padding: 0.75rem 1rem; font-weight: 600;
        font-size: 0.96rem; margin: 0.7rem 0;
      }}
      .guidebox {{
        background: #fff8e6; border: 1px solid {GOLD}; border-left: 6px solid {GOLD};
        border-radius: 10px; padding: 0.85rem 1rem; margin: 0.75rem 0 1rem;
        color: {INK};
      }}
      .guidebox .gtitle {{
        color: {NAVY}; font-weight: 800; font-size: 1rem; margin-bottom: 0.35rem;
      }}
      .guidebox ul {{ margin: 0.2rem 0 0 1.15rem; padding: 0; }}
      .guidebox li {{ margin: 0.18rem 0; line-height: 1.35; }}

      /* overview cards: numbered, generous, friendly */
      .ovgrid {{
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.8rem; margin-top: 0.6rem;
      }}
      .ov {{
        display: flex; gap: 1rem; align-items: flex-start;
        background: #fff; border: 1px solid {BAND}; border-radius: 10px;
        padding: 0.95rem 1rem; margin: 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }}
      .ov .num {{
        flex: none; display: inline-flex; align-items: center; justify-content: center;
        width: 2.2rem; height: 2.2rem; border-radius: 50%;
        background: {NAVY}; color: {GOLD}; font-weight: 800; font-size: 1.1rem;
      }}
      .ov h4 {{ margin: 0.1rem 0 0.3rem; font-size: 1.08rem; }}
      .ov p {{ color: {INK}; margin: 0; font-size: 0.94rem; line-height: 1.45; }}
      @media (max-width: 800px) {{
        .block-container {{ padding-top: 2.6rem; padding-left: 1rem; padding-right: 1rem; }}
        .ovgrid {{ grid-template-columns: 1fr; }}
        .cardrow {{ flex-direction: column; }}
      }}

      /* soft divider used to break sections without heavy lines */
      .rule {{ border: none; border-top: 1px solid {BAND}; margin: 1rem 0; }}

      /* scrollable day timeline (Build visit days + Faculty availability) */
      .tl {{
        border: 1px solid {BAND}; border-radius: 10px; padding: 0.45rem 0.55rem;
        max-height: 330px; overflow-y: auto; background: #fff;
      }}
      .tl-row {{ display: flex; align-items: stretch; gap: 0.7rem; margin: 0.15rem 0; }}
      .tl-time {{
        flex: none; width: 5.2rem; text-align: right; padding: 0.5rem 0;
        color: {NAVY_MID}; font-size: 0.86rem; font-variant-numeric: tabular-nums;
      }}
      .tl-bar {{
        flex: 1; border-radius: 9px; padding: 0.5rem 0.85rem;
        font-size: 0.92rem; font-weight: 600; display: flex; align-items: center;
      }}
      .tl-open {{ background: {BAND}; color: {NAVY}; }}
      .tl-block {{ background: {GOLD_SOFT}; color: {INK}; }}
      .tl-meet {{ background: {NAVY}; color: #fff; }}
      .tl-free {{ background: #e9f3ec; color: #1c6b3f; }}
      .tl-busy {{ background: #f4f5f7; color: #8a8f98; }}
      .tl-tag {{
        margin-left: auto; font-size: 0.74rem; font-weight: 700; opacity: 0.85;
        text-transform: uppercase; letter-spacing: 0.03em;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


def step(n, text):
    st.markdown(f'<div class="step"><span>{n}</span>{text}</div>', unsafe_allow_html=True)


def notice(text):
    st.markdown(f'<div class="notice">{text}</div>', unsafe_allow_html=True)


def guide(title, items):
    lis = "".join(f"<li>{item}</li>" for item in items)
    st.markdown(
        f'<div class="guidebox"><div class="gtitle">{title}</div><ul>{lis}</ul></div>',
        unsafe_allow_html=True,
    )


def rule():
    st.markdown('<hr class="rule">', unsafe_allow_html=True)


def send_log_download(send_log_module, key):
    st.download_button(
        "Download send log CSV",
        send_log_module.to_csv().encode("utf-8"),
        "send_log.csv",
        "text/csv",
        key=key,
    )


def sample_download(filename, label=None, key=None):
    path = os.path.join(SAMPLE_DIR, filename)
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        st.download_button(
            label or f"Download {filename}",
            f.read(),
            filename,
            "text/csv",
            key=key or f"sample_download_{filename}",
        )


def download_text(label, text, filename, key):
    st.download_button(
        label,
        text.encode("utf-8"),
        filename,
        "text/plain",
        key=key,
    )


def message_body(audience):
    if audience == "student":
        return (
            "Hello,\n\n"
            "Please complete the IEOR Visit Day faculty preference form so we can "
            "build your meeting schedule.\n\n"
            "Form link: [form link will be inserted here]\n\n"
            "Thank you,\nIEOR Staff"
        )
    return (
        "Hello,\n\n"
        "Please complete the IEOR Visit Day availability form so we can schedule "
        "prospective student meetings around your available time windows.\n\n"
        "Form link: [form link will be inserted here]\n\n"
        "Thank you,\nIEOR Staff"
    )


def staff_send_steps(audience):
    person = "students" if audience == "student" else "faculty"
    form_name = "student preference form" if audience == "student" else "faculty availability form"
    return (
        f"1. Build the {form_name} in Google Forms using the template CSV above.\n"
        "2. Replace the placeholder in the email body with the real Google Form link.\n"
        f"3. Send the email to the downloaded {person} recipient list using Gmail or Outlook.\n"
        "4. In Google Forms, link the Responses tab to a Google Sheet.\n"
        "5. After responses arrive, download the Sheet as CSV and upload it back here.\n"
    )


def render_email_package_downloads(audience, recipients, subject, body, key_prefix):
    st.markdown("**Staff-send package**")
    st.caption(
        "The app prepares the files and text. Staff send the email manually, then upload "
        "the response CSV after Google Forms responses arrive."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download recipients CSV",
            recipients.to_csv(index=False).encode("utf-8"),
            f"{audience}_recipients.csv",
            "text/csv",
            key=f"{key_prefix}_recipients_download",
        )
    with c2:
        email_text = f"Subject: {subject}\n\n{body}"
        download_text(
            "Download email text",
            email_text,
            f"{audience}_email_text.txt",
            key=f"{key_prefix}_email_text_download",
        )
    with c3:
        download_text(
            "Download send steps",
            staff_send_steps(audience),
            f"{audience}_staff_send_steps.txt",
            key=f"{key_prefix}_steps_download",
        )


def spec_template_df(spec):
    rows = []
    for q in spec["questions"]:
        rows.append({
            "question": q["title"],
            "type": q["type"],
            "required": q.get("required", False),
            "options": " | ".join(q.get("options", [])),
            "help": q.get("help", ""),
        })
    return pd.DataFrame(rows)


def clean_people_editor(df, add_faculty_ids=False, add_student_requests=False):
    """Clean direct-entry name/email rows from the Streamlit data editor."""
    if df is None or df.empty:
        cols = ["faculty_id", "name", "email"] if add_faculty_ids else ["name", "email"]
        if add_student_requests:
            cols.append(MAX_COL)
        return pd.DataFrame(columns=cols)
    out = df.copy()
    for col in ["name", "email"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str).str.strip()
    out = out[(out["name"] != "") | (out["email"] != "")].copy()
    if add_faculty_ids:
        out["faculty_id"] = [f"F{i + 1:02d}" for i in range(len(out))]
        if "area" not in out.columns:
            out["area"] = ""
        out["area"] = out["area"].fillna("").astype(str).str.strip()
        return out[["faculty_id", "name", "area", "email"]]
    if add_student_requests:
        if MAX_COL not in out.columns:
            out[MAX_COL] = 4
        out[MAX_COL] = out[MAX_COL].apply(_clean_max_meetings)
        return out[["name", "email", MAX_COL]]
    return out[["name", "email"]]


def load_csv_into_editor(uploaded_file, state_key, add_faculty_ids=False, add_student_requests=False):
    if uploaded_file is None:
        return
    df = pd.read_csv(uploaded_file)
    if add_faculty_ids:
        if "name" not in df.columns:
            df["name"] = ""
        if "email" not in df.columns:
            df["email"] = ""
        if "area" not in df.columns:
            df["area"] = ""
        st.session_state[state_key] = df[["name", "area", "email"]]
    else:
        if "name" not in df.columns:
            df["name"] = ""
        if "email" not in df.columns:
            df["email"] = ""
        if add_student_requests:
            if MAX_COL not in df.columns:
                df[MAX_COL] = 4
            st.session_state[state_key] = df[["name", "email", MAX_COL]]
        else:
            st.session_state[state_key] = df[["name", "email"]]


def uploaded_file_signature(uploaded_file):
    if uploaded_file is None:
        return None
    return (
        getattr(uploaded_file, "name", ""),
        getattr(uploaded_file, "size", None),
        getattr(uploaded_file, "file_id", None),
    )


def _clean_max_meetings(value):
    try:
        if pd.isna(value) or str(value).strip() == "":
            return 4
        parsed = int(float(value))
        return parsed if parsed > 0 else 4
    except (TypeError, ValueError):
        return 4


def student_requests_from_preferences(preferences, source_students=None):
    students = pd.DataFrame({"student_id": preferences["student_id"].astype(str).unique()})
    students[MAX_COL] = 4
    if source_students is not None and not source_students.empty and MAX_COL in source_students.columns:
        source = source_students.reset_index(drop=True)
        for i in range(min(len(students), len(source))):
            students.loc[i, MAX_COL] = _clean_max_meetings(source.loc[i, MAX_COL])
    return students


def student_requests_from_responses(preferences, responses, source_students=None):
    students = pd.DataFrame({"student_id": preferences["student_id"].astype(str).unique()})
    students[MAX_COL] = 4
    if source_students is None or source_students.empty or MAX_COL not in source_students.columns:
        return students

    email_col = _find_col(source_students, "email")
    response_email_col = _find_col(responses, "email")
    if not email_col or not response_email_col:
        return student_requests_from_preferences(preferences, source_students)

    source_by_email = {
        str(row[email_col]).strip().lower(): _clean_max_meetings(row[MAX_COL])
        for _, row in source_students.iterrows()
        if str(row.get(email_col, "")).strip()
    }
    for i, row in responses.reset_index(drop=True).iterrows():
        if i >= len(students):
            break
        email = str(row.get(response_email_col, "")).strip().lower()
        if email in source_by_email:
            students.loc[i, MAX_COL] = source_by_email[email]
    return students


def _find_col(df, target):
    cols = {c.lower().strip(): c for c in df.columns}
    return cols.get(target)


def schedule_view(assignments, faculty, grid):
    view = render_schedules(assignments, faculty, grid).reset_index(drop=True)
    view.insert(0, "meeting_id", [f"M{i + 1:03d}" for i in range(len(view))])
    return view


def can_add_assignment(assignments, student_id, faculty_id, slot_id):
    conflicts = []
    if ((assignments["student_id"] == student_id) & (assignments["slot_id"] == slot_id)).any():
        conflicts.append("That student already has a meeting in this slot.")
    if ((assignments["faculty_id"] == faculty_id) & (assignments["slot_id"] == slot_id)).any():
        conflicts.append("That faculty member already has a meeting in this slot.")
    if ((assignments["student_id"] == student_id) & (assignments["faculty_id"] == faculty_id)).any():
        conflicts.append("That student and faculty member already meet in this schedule.")
    return conflicts


def render_manual_review(result):
    st.caption(
        "Use this table for small corrections after reviewing the schedule. "
        "Manual changes are held in the current app session; download exports again after editing."
    )
    assignments = result["assignments"].copy()
    if "locked" not in assignments.columns:
        assignments["locked"] = False

    view = schedule_view(assignments, result["faculty"], result["grid"])
    st.dataframe(view, hide_index=True, use_container_width=True)

    st.markdown("**Lock or remove a meeting**")
    meeting_ids = view["meeting_id"].tolist()
    selected = st.selectbox("Meeting", meeting_ids, key="manual_selected_meeting")
    row_idx = int(view.loc[view["meeting_id"] == selected, "assignment_index"].iloc[0]) if selected in meeting_ids else None
    c1, c2, c3 = st.columns(3)
    if c1.button("Lock selected meeting", disabled=row_idx is None):
        assignments.loc[row_idx, "locked"] = True
        result["assignments"] = assignments
        st.session_state["result"] = result
        st.rerun()
    if c2.button("Unlock selected meeting", disabled=row_idx is None):
        assignments.loc[row_idx, "locked"] = False
        result["assignments"] = assignments
        st.session_state["result"] = result
        st.rerun()
    locked = bool(assignments.loc[row_idx, "locked"]) if row_idx is not None else False
    if c3.button("Remove selected meeting", disabled=(row_idx is None or locked)):
        result["assignments"] = assignments.drop(assignments.index[row_idx]).reset_index(drop=True)
        st.session_state["result"] = result
        st.rerun()
    if locked:
        st.info("Unlock this meeting before removing it.")

    st.markdown("**Manually add a meeting**")
    students = sorted(result["preferences"]["student_id"].astype(str).unique())
    faculty_options = result["faculty"][["faculty_id", "name"]].copy()
    faculty_options["label"] = faculty_options["faculty_id"].astype(str) + " - " + faculty_options["name"].astype(str)
    slots = result["grid"][["slot_id", "day", "start_time", "end_time"]].copy()
    slots["label"] = (
        slots["slot_id"].astype(str) + " | Day " + slots["day"].astype(str)
        + " " + slots["start_time"].astype(str) + "-" + slots["end_time"].astype(str)
    )

    a1, a2, a3 = st.columns(3)
    sid = a1.selectbox("Student", students, key="manual_add_student")
    flabel = a2.selectbox("Faculty", faculty_options["label"], key="manual_add_faculty")
    slabel = a3.selectbox("Slot", slots["label"], key="manual_add_slot")
    fid = faculty_options.loc[faculty_options["label"] == flabel, "faculty_id"].iloc[0]
    slot_id = slots.loc[slots["label"] == slabel, "slot_id"].iloc[0]
    conflicts = can_add_assignment(assignments, sid, fid, slot_id)
    if conflicts:
        for conflict in conflicts:
            st.warning(conflict)
    if st.button("Add meeting", disabled=bool(conflicts)):
        new_row = pd.DataFrame([{
            "student_id": sid,
            "faculty_id": fid,
            "slot_id": slot_id,
            "locked": True,
        }])
        result["assignments"] = pd.concat([assignments, new_row], ignore_index=True)
        st.session_state["result"] = result
        st.rerun()


def _tl_row(time_label, css, text, tag=""):
    tag_html = f'<span class="tl-tag">{tag}</span>' if tag else ""
    return (f'<div class="tl-row"><div class="tl-time">{time_label}</div>'
            f'<div class="tl-bar {css}">{text}{tag_html}</div></div>')


def render_day_timeline(plan):
    """Scrollable timeline of one day: open meeting windows and blocked events,
    in chronological order. Used in Build visit days."""
    items = []
    for blk in plan.blocks:
        items.append((blk.start, blk.end, "block", blk.label))
    # open windows are the gaps between blocks within day hours
    busy = sorted(((b.start, b.end) for b in plan.blocks))
    cur = plan.start
    for bs, be in busy:
        if cur < bs:
            items.append((cur, bs, "open", "Open for meetings"))
        cur = max(cur, be)
    if cur < plan.end:
        items.append((cur, plan.end, "open", "Open for meetings"))
    items.sort()

    rows = "".join(
        _tl_row(f"{s}-{e}", "tl-open" if kind == "open" else "tl-block",
                label, "open" if kind == "open" else "blocked")
        for s, e, kind, label in items
    )
    st.markdown(f'<div class="tl">{rows or "<em>No hours set.</em>"}</div>',
                unsafe_allow_html=True)


def render_availability_timeline(grid, free_windows):
    """Scrollable timeline of one faculty's availability across the grid days.
    free_windows is a set of 'HH:MM-HH:MM' strings the faculty checked, per day."""
    for day in sorted(grid["day"].unique()):
        st.markdown(f"**Day {int(day)}**")
        day_slots = grid[grid["day"] == day]
        rows = ""
        for r in day_slots.itertuples():
            win = f"{r.start_time}-{r.end_time}"
            free = win in free_windows
            rows += _tl_row(
                win, "tl-free" if free else "tl-busy",
                "Available" if free else "Not available",
                "free" if free else "busy",
            )
        st.markdown(f'<div class="tl">{rows or "<em>No slots.</em>"}</div>',
                    unsafe_allow_html=True)


# --- header ---
# Embed the logo as inline HTML so the browser scales the full-resolution source
# itself (st.image rasterizes at the display width and looks blurry on Retina).
if os.path.exists(LOGO):
    import base64
    with open(LOGO, "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    st.markdown(
        f'<img src="data:image/png;base64,{_logo_b64}" '
        'style="width:230px; height:auto; display:block; margin:0 0 0.2rem;" '
        'alt="Berkeley IEOR">',
        unsafe_allow_html=True,
    )
st.markdown(
    f"<h1 style='margin:0.5rem 0 0; font-size:2.1rem;'>Visit-Day Faculty Matching</h1>"
    f"<p style='color:{NAVY_MID}; margin:0.3rem 0 0.6rem; font-size:1.05rem;'>"
    "Schedule prospective student meetings with the faculty they most want to meet.</p>"
    f"<hr style='border:none; border-top:2px solid {BAND}; margin:0.9rem 0 0.4rem;'>",
    unsafe_allow_html=True,
)

# Slot-sizing and solver settings live inside their relevant tabs (no sidebar).
# They persist in session state so make_config() can read them from anywhere.
st.session_state.setdefault("meeting_min", 20)
st.session_state.setdefault("buffer_min", 5)
st.session_state.setdefault("time_limit", 30)


def make_config():
    return Config(
        meeting_minutes=st.session_state["meeting_min"],
        buffer_minutes=st.session_state["buffer_min"],
        solver_time_limit_s=st.session_state["time_limit"],
    )


def get_plans():
    """The visit-day structure, defaulting to two 9-5 days with lunch."""
    if "plans" not in st.session_state:
        st.session_state["plans"] = default_plans()
    return st.session_state["plans"]


def get_grid():
    """Grid built from the staff-defined visit-day structure."""
    return build_grid_from_plans(get_plans(), make_config())


tabs = st.tabs([
    "1 Overview",
    "2 Build visit days",
    "3 Prospective students",
    "4 Faculty availability",
    "5 Build schedules",
])


# =====================================================================
# TAB 1 - OVERVIEW
# =====================================================================
with tabs[0]:
    st.markdown(
        "<p style='font-size:1.15rem;'>Welcome. This tool helps the IEOR staff give "
        "every prospective graduate student a personalized two-day schedule of meetings "
        "with the faculty they most want to meet. You do not need any technical "
        "background to use it. Just work through the four tabs in order, left to right, "
        "and the tool handles the scheduling for you.</p>",
        unsafe_allow_html=True,
    )
    rule()
    st.markdown("<h3>How it works, step by step</h3>", unsafe_allow_html=True)

    cards = [
        ("Build visit days",
         "Start here. Tell the tool how each of the two visit days is laid out: what "
         "time the day starts, what time it ends, and any blocks of time that are not "
         "for meetings, such as a lunch break, a welcome session, or a campus tour. "
         "Everything you do not block off becomes available time that the tool can use "
         "to schedule student-faculty meetings. You will see a live preview of how many "
         "meeting slots each day has as you make changes."),
        ("Prospective students",
         "Next, enter student names and emails directly, or import a CSV if one already "
         "exists. The tool prepares a preference-form template, recipient list, and email "
         "text. Staff send the email manually, then upload the exported response CSV."),
        ("Faculty availability",
         "Now collect faculty availability. Enter faculty names and emails directly, "
         "with optional research areas, then download the availability-form template and "
         "staff-send package. After responses come back, upload the response CSV and the "
         "app converts checked time windows into scheduler-ready availability."),
        ("Build schedules",
         "Finally, generate the schedules. The tool takes everything you have collected, "
         "the students' ranked preferences, each faculty member's availability, and your "
         "visit-day structure, and works out the best possible two-day schedule for every "
         "student. It aims to give each student as many of their top-choice meetings as "
         "possible while making sure no one is left out. You can review the results by "
         "student or by faculty and download them as a spreadsheet."),
    ]
    card_html = '<div class="ovgrid">' + "".join(
        f'<div class="ov"><div class="num">{i}</div>'
        f'<div><h4>{title}</h4><p>{body}</p></div></div>'
        for i, (title, body) in enumerate(cards, start=1)
    ) + "</div>"
    st.markdown(card_html, unsafe_allow_html=True)


# =====================================================================
# TAB 2 - BUILD VISIT DAYS: per-day hours + blocked events
# =====================================================================
def render_visit_days():
    plans = get_plans()

    step(1, "Meeting setup")
    s1, s2, s3 = st.columns(3)
    st.session_state["meeting_min"] = s1.number_input(
        "Meeting length (minutes)", 5, 60, st.session_state["meeting_min"], step=5)
    st.session_state["buffer_min"] = s2.number_input(
        "Buffer between meetings (minutes)", 0, 30, st.session_state["buffer_min"], step=5)
    cfg = make_config()
    s3.metric("Each meeting block", f"{cfg.slot_minutes} min")

    rule()

    step(2, "Visit-day schedule")
    st.caption("Set day hours and block only the events that are not available for meetings.")

    for plan in plans:
        day_grid = build_grid_from_plans([plan], cfg)
        n = len(day_grid)
        with st.expander(
            f"Day {plan.day}: {plan.start}-{plan.end}, {n} meeting slots",
            expanded=(plan.day == 1),
        ):
            edit_col, view_col = st.columns([1.05, 1])

            with edit_col:
                c1, c2 = st.columns(2)
                plan.start = c1.text_input("Start", plan.start, key=f"d{plan.day}_start")
                plan.end = c2.text_input("End", plan.end, key=f"d{plan.day}_end")

                st.markdown("**Blocked events**")
                keep = []
                for j, blk in enumerate(plan.blocks):
                    bc1, bc2, bc3, bc4 = st.columns([3, 2, 2, 1.2])
                    blk.label = bc1.text_input("Event", blk.label, key=f"d{plan.day}_b{j}_l")
                    blk.start = bc2.text_input("Start", blk.start, key=f"d{plan.day}_b{j}_s")
                    blk.end = bc3.text_input("End", blk.end, key=f"d{plan.day}_b{j}_e")
                    bc4.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
                    if not bc4.button("Remove", key=f"d{plan.day}_b{j}_x",
                                      use_container_width=True):
                        keep.append(blk)
                plan.blocks = keep

                if st.button(f"Add blocked event", key=f"d{plan.day}_add"):
                    plan.blocks.append(Block("New event", "10:00", "10:30"))
                    st.rerun()

            with view_col:
                st.caption("Preview")
                render_day_timeline(plan)

    st.session_state["plans"] = plans

    grid = build_grid_from_plans(plans, cfg)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total slots", len(grid))
    c2.metric("Visit days", len(plans))
    c3.metric("Blocked events", sum(len(p.blocks) for p in plans))
    if grid.empty:
        st.error("No open meeting slots yet. Widen the day hours or remove some blocks.")


with tabs[1]:
    render_visit_days()


# =====================================================================
# TAB 3 - CONTACT PROSPECTIVE STUDENTS (preference form)
# =====================================================================
def render_student_intake():
    from google_intake import send_intake
    from form_spec import build_spec
    from adapter import adapt
    import send_log

    DEFAULT_SUBJECT = "IEOR Visit Day: tell us which faculty you want to meet"

    step(1, "Enter prospective students")
    guide("Staff checklist", [
        "Enter one row per student with name, email, and max meetings requested.",
        "Keep max meetings requested at 4 unless the program wants a different limit.",
        "Use the optional CSV import only if you already have a clean name/email file.",
    ])
    st.caption(
        "Type student names and emails directly. Add rows as needed. CSV upload is "
        "still available below if you already have a file. Max meetings requested "
        "defaults to 4 so the model does not assume ranking more faculty means a "
        "student wants unlimited meetings."
    )

    if "student_people_editor" not in st.session_state:
        st.session_state["student_people_editor"] = pd.DataFrame(
            [{"name": "", "email": "", MAX_COL: 4} for _ in range(8)]
        )
    edited_students = st.data_editor(
        st.session_state["student_people_editor"],
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="student_people_editor_widget",
        column_config={
            "name": st.column_config.TextColumn("Student name"),
            "email": st.column_config.TextColumn("Email"),
            MAX_COL: st.column_config.NumberColumn(
                "Max meetings requested",
                min_value=1,
                step=1,
                help="Defaults to 4. This limits how many faculty meetings the scheduler tries to assign.",
            ),
        },
    )
    st.session_state["student_people_editor"] = edited_students

    with st.expander("Optional: import students from CSV", expanded=False):
        sample_download("test_students.csv", "Download sample student CSV", key="sample_students_download")
        stu_file = st.file_uploader("Student list (CSV)", type="csv", key="intake_csv")
        stu_sig = uploaded_file_signature(stu_file)
        if stu_file is not None and st.session_state.get("last_student_csv_import") != stu_sig:
            load_csv_into_editor(stu_file, "student_people_editor", add_student_requests=True)
            st.session_state["last_student_csv_import"] = stu_sig
            st.session_state.pop("student_people_editor_widget", None)
            st.success("CSV loaded into the editable table above.")
            st.rerun()

    recipients = clean_people_editor(st.session_state["student_people_editor"], add_student_requests=True)
    st.session_state["recipients"] = recipients
    st.session_state["recipients_source"] = "direct entry table"

    if recipients.empty:
        st.info("Enter at least one student name and email to continue.")
        return

    notice(f"Loaded {len(recipients)} students ({st.session_state['recipients_source']}).")
    st.dataframe(recipients.head(25), hide_index=True, use_container_width=True)

    result = send_intake(recipients, roster_path=ROSTER_XLSX, dry_run=True)
    if result.errors:
        with st.expander(f"{len(result.errors)} row issue(s)"):
            for e in result.errors:
                st.write("- ", e)

    step(2, "Prepare the preference form")
    guide("Build the Google Form exactly from this template", [
        "Copy question titles exactly; the response parser uses those titles to identify answers.",
        "Only the student's 1st choice is required; leave 2nd-8th choice questions optional.",
        "In the Google Form or email, encourage students to list at least 3 genuine choices because backups improve scheduling flexibility.",
        "Do not rename faculty options after students have started responding.",
    ])
    spec = build_spec(ROSTER_XLSX)
    st.download_button(
        "Download student form template CSV",
        spec_template_df(spec).to_csv(index=False).encode("utf-8"),
        "student_preference_form_template.csv",
        "text/csv",
        key="student_form_template_download",
    )
    with st.expander(f"Preview form questions ({len(spec['questions'])})", expanded=False):
        st.markdown(f"*{spec['description']}*")
        for i, q in enumerate(spec["questions"], start=1):
            req = " (required)" if q.get("required") else ""
            st.markdown(f"**{i}. {q['title']}**  `{q['type']}`{req}")
            if q.get("help"):
                st.caption(q["help"])
            opts = q.get("options", [])
            if opts:
                shown = ", ".join(opts[:10])
                more = f" ... (+{len(opts) - 10} more)" if len(opts) > 10 else ""
                st.caption(f"Options: {shown}{more}")

    step(3, "Import student responses")
    guide("Upload rule", [
        "After responses are collected, open the linked Google Sheet and download as CSV.",
        "Upload the CSV exactly as downloaded; do not delete columns or rename headers.",
        "Warnings are okay to review, but errors must be fixed before scheduling.",
    ])
    st.caption(
        "After collecting Google Form responses, download the response Sheet as CSV "
        "and upload it here. The app converts it to solver-ready preferences.csv."
    )
    resp_file = st.file_uploader("Student response CSV from Google Forms", type="csv", key="student_resp_csv")
    if resp_file is not None:
        responses = pd.read_csv(resp_file)
        prefs, interests, warnings = adapt(responses, ROSTER_XLSX)
        st.session_state["parsed_preferences"] = prefs
        st.session_state["parsed_student_interests"] = interests
        st.session_state["parsed_students"] = student_requests_from_responses(prefs, responses, recipients)
        notice(f"Parsed {len(prefs)} preference rows for {prefs['student_id'].nunique()} students.")
        if warnings:
            with st.expander(f"{len(warnings)} student response warning(s)", expanded=True):
                for w in warnings:
                    st.warning(w)
        st.download_button(
            "Download preferences.csv",
            prefs.to_csv(index=False),
            "preferences.csv",
            "text/csv",
            key="student_preferences_download",
        )
        st.download_button(
            "Download student_interests.csv",
            interests.to_csv(index=False),
            "student_interests.csv",
            "text/csv",
            key="student_interests_download",
        )

    with st.expander("Prepare staff-send email package", expanded=True):
        guide("Manual send rule", [
            "Replace the form-link placeholder in the email text with the real Google Form URL.",
            "Send the email manually through Gmail or Outlook; the app does not send live email.",
            "Record the package after reviewing recipients, subject, and body.",
        ])
        last = send_log.last_send()
        if last:
            notice(
                f"Last package recorded {send_log.pretty_time(last['timestamp'])} "
                f"for {last['n_recipients']} students."
            )
        subject = st.text_input(
            "Email subject line",
            value=st.session_state.get("subject", DEFAULT_SUBJECT),
            key="subject",
        )
        st.markdown("**Recipient preview**")
        st.dataframe(pd.DataFrame(result.recipients), hide_index=True, use_container_width=True)
        body = st.text_area("Email body preview", value=message_body("student"), height=180, key="student_body")
        render_email_package_downloads("student", recipients, subject, body, "student_package")
        confirmed = st.checkbox(
            "I reviewed the recipients, subject, and body. Staff will send this manually.",
            key="student_confirm",
        )

        if st.button("Record student send package", type="primary", disabled=not (result.ok and confirmed)):
            entry = send_log.record_send(
                result.n_recipients,
                subject,
                simulated=True,
                key="student",
                body=body,
                dry_run=True,
                status="staff_send_package_prepared",
            )
            st.success(
                f"Package recorded on {send_log.pretty_time(entry['timestamp'])} "
                f"for {entry['n_recipients']} students. Staff still sends the email manually."
            )
        send_log_download(send_log, key="student_send_log_download")


with tabs[2]:
    render_student_intake()


# =====================================================================
# TAB 4 - CONTACT FACULTY AVAILABILITY (availability form)
# =====================================================================
def render_faculty_intake():
    from google_intake import send_intake
    from faculty_form_spec import build_faculty_spec
    from faculty_adapter import adapt_faculty_availability
    import send_log

    DEFAULT_SUBJECT = "IEOR Visit Day: when are you available to meet students?"

    grid = get_grid()
    if grid.empty:
        st.warning("Set up the visit days first (no meeting slots defined yet).")
        return

    step(1, "Enter faculty")
    guide("Staff checklist", [
        "Enter one row per faculty member with name and email.",
        "Use consistent faculty names; student preferences and faculty availability depend on matching names.",
        "Area is optional and can be left blank if staff do not need it.",
    ])
    st.caption(
        "Type faculty names and emails directly. The app will assign simple faculty IDs "
        "for the availability workflow. Area is optional."
    )

    if "faculty_people_editor" not in st.session_state:
        st.session_state["faculty_people_editor"] = pd.DataFrame(
            [{"name": "", "area": "", "email": ""} for _ in range(6)]
        )
    edited_faculty = st.data_editor(
        st.session_state["faculty_people_editor"],
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="faculty_people_editor_widget",
        column_config={
            "name": st.column_config.TextColumn("Faculty name"),
            "area": st.column_config.TextColumn("Area (optional)"),
            "email": st.column_config.TextColumn("Email"),
        },
    )
    st.session_state["faculty_people_editor"] = edited_faculty

    with st.expander("Optional: import faculty from CSV", expanded=False):
        sample_download("test_faculty.csv", "Download sample faculty CSV", key="sample_faculty_download")
        fac_file = st.file_uploader("Faculty list (CSV)", type="csv", key="fac_csv")
        fac_sig = uploaded_file_signature(fac_file)
        if fac_file is not None and st.session_state.get("last_faculty_csv_import") != fac_sig:
            load_csv_into_editor(fac_file, "faculty_people_editor", add_faculty_ids=True)
            st.session_state["last_faculty_csv_import"] = fac_sig
            st.session_state.pop("faculty_people_editor_widget", None)
            st.success("CSV loaded into the editable table above.")
            st.rerun()

    recipients = clean_people_editor(st.session_state["faculty_people_editor"], add_faculty_ids=True)
    st.session_state["fac_recipients"] = recipients
    st.session_state["fac_source"] = "direct entry table"

    if recipients.empty:
        st.info("Enter at least one faculty name and email to continue.")
        return

    notice(f"Loaded {len(recipients)} faculty ({st.session_state['fac_source']}).")
    st.dataframe(recipients.head(25), hide_index=True, use_container_width=True)

    spec = build_faculty_spec(grid)
    result = send_intake(recipients, spec=spec, dry_run=True)
    if result.errors:
        with st.expander(f"{len(result.errors)} row issue(s)"):
            for e in result.errors:
                st.write("- ", e)

    step(2, "Prepare the availability form")
    guide("Build the Google Form exactly from this template", [
        "Create one checkbox question for each visit day shown in the template.",
        "Keep time-window labels unchanged so the app can map answers back to schedule slots.",
        "Ask faculty to check every window they are available; unchecked means unavailable.",
    ])
    st.caption("The available time windows come from your visit-day structure.")
    st.download_button(
        "Download faculty availability form template CSV",
        spec_template_df(spec).to_csv(index=False).encode("utf-8"),
        "faculty_availability_form_template.csv",
        "text/csv",
        key="faculty_form_template_download",
    )

    with st.expander(f"Preview form questions ({len(spec['questions'])})", expanded=False):
        st.markdown(f"*{spec['description']}*")
        for i, q in enumerate(spec["questions"], start=1):
            req = " (required)" if q.get("required") else ""
            st.markdown(f"**{i}. {q['title']}**  `{q['type']}`{req}")
            if q.get("help"):
                st.caption(q["help"])
            opts = q.get("options", [])
            if opts:
                shown = ", ".join(opts[:10])
                more = f" ... (+{len(opts) - 10} more)" if len(opts) > 10 else ""
                st.caption(f"Options: {shown}{more}")

    step(3, "Import faculty responses")
    guide("Upload rule", [
        "Download the linked Google Sheet responses as CSV after faculty submit availability.",
        "Upload the CSV exactly as downloaded; do not rename time-window columns.",
        "If the app warns about matching, check faculty names/emails against the table above.",
    ])
    st.caption(
        "After collecting Google Form responses, download the response Sheet as CSV "
        "and upload it here. The app converts checked time windows to availability.csv."
    )
    fac_resp_file = st.file_uploader("Faculty response CSV from Google Forms", type="csv", key="faculty_resp_csv")
    if fac_resp_file is not None:
        responses = pd.read_csv(fac_resp_file)
        if "faculty_id" not in recipients.columns:
            st.warning("Faculty matching is most reliable when the uploaded faculty list includes faculty_id.")
        availability, warnings = adapt_faculty_availability(responses, recipients, grid)
        st.session_state["parsed_availability"] = availability
        st.session_state["parsed_faculty"] = recipients
        notice(f"Parsed {len(availability)} faculty availability rows.")
        if warnings:
            with st.expander(f"{len(warnings)} faculty response warning(s)", expanded=True):
                for w in warnings:
                    st.warning(w)
        st.download_button(
            "Download availability.csv",
            availability.to_csv(index=False),
            "availability.csv",
            "text/csv",
            key="faculty_availability_download",
        )

    with st.expander("Prepare staff-send email package", expanded=True):
        guide("Manual send rule", [
            "Replace the form-link placeholder in the email text with the real Google Form URL.",
            "Send the email manually through Gmail or Outlook; the app does not send live email.",
            "Record the package after reviewing recipients, subject, and body.",
        ])
        last = send_log.last_send(key="faculty")
        if last:
            notice(
                f"Last package recorded {send_log.pretty_time(last['timestamp'])} "
                f"for {last['n_recipients']} faculty."
            )
        subject = st.text_input(
            "Email subject line",
            value=st.session_state.get("fac_subject", DEFAULT_SUBJECT),
            key="fac_subject",
        )
        st.markdown("**Recipient preview**")
        st.dataframe(pd.DataFrame(result.recipients), hide_index=True, use_container_width=True)
        body = st.text_area("Email body preview", value=message_body("faculty"), height=180, key="faculty_body")
        render_email_package_downloads("faculty", recipients, subject, body, "faculty_package")
        confirmed = st.checkbox(
            "I reviewed the recipients, subject, and body. Staff will send this manually.",
            key="faculty_confirm",
        )

        if st.button("Record faculty send package", type="primary", disabled=not (result.ok and confirmed)):
            entry = send_log.record_send(
                result.n_recipients,
                subject,
                simulated=True,
                key="faculty",
                body=body,
                dry_run=True,
                status="staff_send_package_prepared",
            )
            st.success(
                f"Package recorded on {send_log.pretty_time(entry['timestamp'])} "
                f"for {entry['n_recipients']} faculty. Staff still sends the email manually."
            )
        send_log_download(send_log, key="faculty_send_log_download")

    with st.expander("Optional: view imported faculty availability", expanded=False):
        if "parsed_availability" not in st.session_state:
            st.info("Upload a faculty response CSV above to preview parsed availability.")
        else:
            parsed = st.session_state["parsed_availability"]
            if "faculty_id" not in recipients.columns or "name" not in recipients.columns:
                st.info("Upload a faculty list with faculty_id and name to preview individual timelines.")
            else:
                names = recipients_names(recipients)
                pick = st.selectbox("View a faculty member's availability", names)
                faculty_row = recipients[recipients["name"].astype(str) == pick]
                if not faculty_row.empty:
                    fid = faculty_row["faculty_id"].iloc[0]
                    free_slots = set(parsed[parsed["faculty_id"] == fid]["slot_id"])
                    slot_windows = {
                        r.slot_id: f"{r.start_time}-{r.end_time}"
                        for r in grid.itertuples()
                    }
                    render_availability_timeline(
                        grid,
                        {slot_windows[s] for s in free_slots if s in slot_windows},
                    )


def recipients_names(recipients):
    cols = {c.lower().strip(): c for c in recipients.columns}
    if "name" in cols:
        return [str(x).strip() for x in recipients[cols["name"]]]
    first = cols.get("first name") or cols.get("first")
    last = cols.get("last name") or cols.get("last")
    if first and last:
        return [f"{r[first]} {r[last]}".strip() for _, r in recipients.iterrows()]
    return [str(x) for x in recipients.iloc[:, 0]]


with tabs[3]:
    render_faculty_intake()


# =====================================================================
# TAB 5 - BUILD SCHEDULES: load -> solve -> review -> download
# =====================================================================
def render_matching():
    step(1, "Load data")
    guide("Choose the correct source", [
        "Use Demo Data only for practice or demonstrations.",
        "Use Collected Data for real visit-day scheduling.",
        "If you parsed responses in tabs 3 and 4 during this session, click Use parsed response data from this session.",
    ])
    source = st.radio(
        "Load data source",
        ["Use Demo Data", "Use Collected Data"],
        horizontal=True,
    )

    faculty = availability = preferences = students = None
    cfg = make_config()
    grid = get_grid()

    if source == "Use Demo Data":
        demo_cfg = make_config()
        demo_cfg.num_students = 25
        faculty, availability, preferences, _ = generate(demo_cfg)
        students = student_requests_from_preferences(preferences)
        # use the staff-defined grid, regenerating availability against it
        availability = _availability_on_grid(faculty, grid)
        cfg = demo_cfg
        notice("Demo data loaded and ready to schedule.")
    else:
        session_ready = (
            "parsed_faculty" in st.session_state
            and "parsed_availability" in st.session_state
            and "parsed_preferences" in st.session_state
        )
        if session_ready:
            if st.button("Use parsed response data from this session"):
                faculty = st.session_state["parsed_faculty"]
                if "area" not in faculty.columns:
                    faculty = faculty.assign(area="")
                availability = st.session_state["parsed_availability"]
                preferences = st.session_state["parsed_preferences"]
                students = st.session_state.get("parsed_students")
                if students is None:
                    students = student_requests_from_preferences(preferences)
                notice("Parsed response data loaded and ready to schedule.")
        st.caption(
            "Upload faculty.csv, availability.csv, and preferences.csv. Optional students.csv "
            "can include student_id and max_meetings_requested."
        )
        with st.expander("Download sample scheduler CSVs", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                sample_download("test_faculty.csv", "faculty.csv sample", key="build_sample_faculty_download")
            with c2:
                sample_download("test_availability.csv", "availability.csv sample", key="build_sample_availability_download")
            with c3:
                sample_download("test_preferences.csv", "preferences.csv sample", key="build_sample_preferences_download")
            with c4:
                sample_download("test_student_requests.csv", "students.csv sample", key="build_sample_students_download")
        fac_f = st.file_uploader("faculty.csv", type="csv")
        avail_f = st.file_uploader("availability.csv", type="csv")
        pref_f = st.file_uploader("preferences.csv", type="csv")
        students_f = st.file_uploader("students.csv (optional)", type="csv")
        if fac_f and avail_f and pref_f:
            faculty = pd.read_csv(fac_f)
            availability = pd.read_csv(avail_f)
            preferences = pd.read_csv(pref_f)
            students = pd.read_csv(students_f) if students_f else student_requests_from_preferences(preferences)
            notice("Collected data loaded and ready to schedule.")

    rule()
    step(2, "Build the schedule")
    guide("Before clicking Match", [
        "Fix all red errors; the button stays disabled until required data is valid.",
        "Review yellow warnings because they may explain missing or uneven meetings.",
        "Use the same visit-day setup that faculty used when submitting availability.",
    ])
    st.caption(
        "The optimizer respects each student's effective max meetings: the smaller of "
        "their requested max, their number of ranked faculty, and the number of available slots."
    )
    with st.expander("Advanced settings"):
        st.session_state["time_limit"] = st.slider(
            "Solver time limit (seconds)", 5, 120, st.session_state["time_limit"],
            help="How long the optimizer may search. Longer can find better schedules.")
    cfg.solver_time_limit_s = st.session_state["time_limit"]

    validation = None
    if faculty is not None:
        validation = validate_solver_inputs(faculty, availability, preferences, grid, students=students, cfg=cfg)
        if validation.info:
            for msg in validation.info:
                st.success(msg)
        if validation.warnings:
            with st.expander(f"{len(validation.warnings)} warning(s) to review before scheduling", expanded=True):
                for msg in validation.warnings:
                    st.warning(msg)
        if validation.errors:
            with st.expander(f"{len(validation.errors)} issue(s) must be fixed before scheduling", expanded=True):
                for msg in validation.errors:
                    st.error(msg)

    can_solve = validation.ok if validation is not None else False
    if faculty is not None and st.button("Match students to faculty", type="primary", disabled=not can_solve):
        with st.spinner("Optimizing schedule..."):
            assignments, status, obj = solve(faculty, availability, preferences, grid, cfg, student_requests=students)

        if assignments.empty:
            st.error(f"No feasible schedule found (solver status: {status}). Check availability data.")
        else:
            assignments["locked"] = False
            st.session_state["result"] = {
                "assignments": assignments,
                "faculty": faculty,
                "preferences": preferences,
                "students": students,
                "grid": grid,
                "availability": availability,
                "status": status,
                "objective": obj,
            }

    if "result" in st.session_state:
        r = st.session_state["result"]
        sched = render_schedules(r["assignments"], r["faculty"], r["grid"])
        mx = compute_metrics(r["assignments"], r["preferences"])
        dx = build_diagnostics(
            r["assignments"], r["faculty"], r["availability"], r["preferences"], r["grid"],
            students=r.get("students"), cfg=cfg
        )
        exports = build_export_tables(sched, dx["student_outcomes"])

        step(3, "Results")
        guide("Finalize carefully", [
            "Start with Needs review and the notes below; these are the main staff-facing diagnostics.",
            "Check individual student and faculty schedules before sending final schedules.",
            "Use manual edits only for small final corrections, then download all export files.",
        ])
        action_count = sum(1 for note in dx.get("notes", []) if note["level"] in {"Action", "Bottleneck"})
        cards = [
            ("navy", "Meetings scheduled", str(mx["total_meetings"])),
            ("gold", "Capacity used", f"{dx['summary']['utilization_rate']:.0%}"),
            ("navy", "Avg meetings/student", f"{dx['summary']['avg_meetings_per_student']:.1f}"),
            ("gold", "Needs review", str(action_count)),
        ]
        html = '<div class="cardrow">' + "".join(
            f'<div class="card {c}"><div class="label">{lab}</div>'
            f'<div class="value">{val}</div></div>'
            for c, lab, val in cards
        ) + "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.caption(f"Solver status: {r['status']}  |  objective: {r['objective']:.0f}")

        st.markdown("**Review before finalizing**")
        for note in dx.get("notes", [])[:5]:
            if note["level"] == "Action":
                st.error(f"{note['title']}: {note['detail']}")
            elif note["level"] == "Bottleneck":
                st.warning(f"{note['title']}: {note['detail']}")
            elif note["level"] == "OK":
                st.success(f"{note['title']}: {note['detail']}")
            else:
                st.info(f"{note['title']}: {note['detail']}")

        view_stu, view_fac, view_diag, view_manual, view_exports = st.tabs([
            "Student schedules", "Faculty schedules", "Review notes", "Manual edits", "Exports"
        ])
        with view_stu:
            pick = st.selectbox("View a student", sorted(sched["student_id"].unique()))
            st.dataframe(
                sched[sched["student_id"] == pick][["day", "start", "end", "faculty"]],
                hide_index=True, use_container_width=True,
            )
        with view_fac:
            fpick = st.selectbox("View a faculty member", sorted(sched["faculty"].unique()))
            st.dataframe(
                sched[sched["faculty"] == fpick][["day", "start", "end", "student_id"]],
                hide_index=True, use_container_width=True,
            )
        with view_diag:
            st.caption("Use these notes to decide whether the schedule is ready or needs a small manual adjustment.")
            for note in dx.get("notes", [])[5:]:
                if note["level"] == "Action":
                    st.error(f"{note['title']}: {note['detail']}")
                elif note["level"] == "Bottleneck":
                    st.warning(f"{note['title']}: {note['detail']}")
                elif note["level"] == "OK":
                    st.success(f"{note['title']}: {note['detail']}")
                else:
                    st.info(f"{note['title']}: {note['detail']}")
            if len(dx.get("notes", [])) <= 5:
                st.success("No additional review notes.")
            with st.expander("Advanced details for troubleshooting", expanded=False):
                st.markdown("**Faculty capacity**")
                st.dataframe(
                    dx["faculty_capacity"][["name", "available_slots", "scheduled_meetings", "unused_capacity"]],
                    hide_index=True,
                    use_container_width=True,
                )
                st.markdown("**Students to check first**")
                st.dataframe(
                    dx["student_outcomes"][[
                        "student_id", "assigned_meetings", "effective_max_meetings",
                        "top3_met", "meeting_fulfillment_rate"
                    ]].head(20),
                    hide_index=True,
                    use_container_width=True,
                )
                st.markdown("**Popular faculty demand**")
                st.dataframe(
                    dx["faculty_demand"][["name", "total_rankings", "top3_rankings", "scheduled_meetings"]].head(20),
                    hide_index=True,
                    use_container_width=True,
                )
        with view_manual:
            with st.expander("Open manual adjustment tools", expanded=False):
                render_manual_review(r)
        with view_exports:
            guide("Save these files outside Streamlit", [
                "Download exports after every final run; Streamlit is not a permanent archive.",
                "Save the master schedule and student/faculty schedules in the team's shared folder.",
                "Use the email-text exports when staff are ready to notify participants of final schedules.",
            ])
            st.caption("Download these files after each final run so the visit-day record is saved outside the app session.")
            st.download_button(
                "Download master schedule CSV",
                to_csv_bytes(exports["master_schedule"]),
                "master_schedule.csv",
                "text/csv",
                key="export_master_schedule_download",
            )
            st.download_button(
                "Download student schedules CSV",
                to_csv_bytes(exports["student_schedules"]),
                "student_schedules.csv",
                "text/csv",
                key="export_student_schedules_download",
            )
            st.download_button(
                "Download faculty schedules CSV",
                to_csv_bytes(exports["faculty_schedules"]),
                "faculty_schedules.csv",
                "text/csv",
                key="export_faculty_schedules_download",
            )
            st.download_button(
                "Download student email text CSV",
                to_csv_bytes(exports["student_email_text"]),
                "student_email_text.csv",
                "text/csv",
                key="export_student_email_text_download",
            )
            st.download_button(
                "Download faculty email text CSV",
                to_csv_bytes(exports["faculty_email_text"]),
                "faculty_email_text.csv",
                "text/csv",
                key="export_faculty_email_text_download",
            )
            st.download_button(
                "Download student diagnostics CSV",
                to_csv_bytes(exports["student_diagnostics"]),
                "student_diagnostics.csv",
                "text/csv",
                key="export_student_diagnostics_download",
            )


def _availability_on_grid(faculty, grid):
    """Regenerate demo faculty availability against the staff-defined grid."""
    import random
    slots = grid["slot_id"].tolist()
    rows = []
    rng = random.Random(42)
    for fid in faculty["faculty_id"]:
        k = max(1, int(len(slots) * rng.uniform(0.5, 0.9)))
        for s in rng.sample(slots, k=k):
            rows.append({"faculty_id": fid, "slot_id": s})
    return pd.DataFrame(rows)


with tabs[4]:
    render_matching()
