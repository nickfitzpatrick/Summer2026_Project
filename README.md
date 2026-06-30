# IEOR Visit-Day Matching Tool

Streamlit app for helping Berkeley IEOR staff schedule prospective graduate
student meetings with faculty during Visit Day.

The app is meant to be a practical internal operations tool: staff configure the
visit-day structure, collect or upload student preferences and faculty
availability, run an OR-Tools CP-SAT scheduler, review diagnostics, and download
the final schedules.

## Current workflow

1. Build visit days: set meeting length, buffer time, day hours, and blocked
   events such as lunch or tours.
2. Enter prospective student names/emails directly, or import an optional CSV,
   then preview the student preference form.
3. Download form templates or upload exported student response CSVs.
4. Enter faculty names/emails directly, preview the faculty availability form,
   and upload exported faculty response CSVs.
5. Build schedules from demo data, parsed session data, or uploaded CSVs.
6. Review validation messages before solving.
7. Review schedule diagnostics after solving.
8. Download master, student, faculty, and email-ready exports.

Live Google Forms, Google Sheets, and Gmail automation are intentionally still
behind a stubbed integration path. Until credentials are provisioned and tested,
the app should use preview, dry-run, template, and CSV fallback workflows.

The student and faculty send sections are dry-run only in this version. Staff can
preview recipients, subject, and body, then record a dry-run send log. No email is
sent by the app.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

CLI smoke test:

```bash
python src/run.py
```

Pipeline test:

```bash
pytest
```

## Input schemas

For the scheduler, the collected-data path expects three CSV files.
For small groups, the intake tabs use editable tables so staff can type names
and emails directly. Sample files are still available in `sample_data/` and
through optional in-app download buttons.

`faculty.csv`

```csv
faculty_id,name,area
F01,Faculty Name,Optimization
```

Required columns: `faculty_id`, `name`. `area` is useful for display and future
filtering, but the Stage 1 scheduler validation only requires the first two.

`availability.csv`

```csv
faculty_id,slot_id
F01,D1-S1
F01,D1-S2
```

Required columns: `faculty_id`, `slot_id`. Slot IDs must come from the visit-day
setup shown in the app.

`preferences.csv`

```csv
student_id,faculty_id,rank
S01,F01,1
S01,F03,2
```

Required columns: `student_id`, `faculty_id`, `rank`. Ranks must be positive
whole numbers.

## Validation

Before solving, the app checks:

- missing required columns
- duplicate faculty IDs
- duplicate student/faculty preference pairs
- duplicate faculty/slot availability rows
- unknown faculty IDs in preferences or availability
- unknown slot IDs in availability
- invalid rank values
- empty preference or availability files
- faculty with zero availability
- students with too few preferences

Errors block scheduling. Warnings allow scheduling but should be reviewed.

## Diagnostics and exports

After a successful solve, the app shows:

- solver status and objective
- total meetings
- capacity utilization
- average meetings per student
- lowest meetings assigned to any student
- faculty capacity used vs available
- faculty popularity and unmet demand
- student outcomes and low-satisfaction cases
- unassigned preferences

Downloadable files:

- `master_schedule.csv`
- `student_schedules.csv`
- `faculty_schedules.csv`
- `student_email_text.csv`
- `faculty_email_text.csv`
- `send_log.csv`

Staff should download these files after each final run because Streamlit session
state is not a permanent system of record.

## Project layout

- `app.py`: Streamlit staff app
- `sample_data/`: small CSV files for trying the upload workflow
- `src/config.py`: tunable scheduling settings
- `src/visit_days.py`: visit-day and slot-grid construction
- `src/model.py`: OR-Tools CP-SAT optimizer
- `src/validation.py`: staff-facing input validation
- `src/diagnostics.py`: schedule diagnostics tables
- `src/exports.py`: downloadable schedule export tables
- `src/google_intake.py`: isolated Google/Gmail integration boundary
- `src/form_spec.py`: student preference form template
- `src/faculty_form_spec.py`: faculty availability form template
- `src/adapter.py`: student response CSV adapter
- `tests/`: pipeline checks and sample response generation

## Safety notes

- Do not hardcode credentials, API keys, passwords, Gmail accounts, OAuth
  secrets, or personal data.
- Use Streamlit secrets or environment variables for credentials.
- Set `APP_PASSWORD` in Streamlit Secrets before sharing a deployed app link.
- Real sending must remain disabled until preview, dry-run, confirmation, and
  logging flows are stable.
- No send action should run automatically on page load.
- Preserve CSV upload/download fallback workflows even after Google integration.
