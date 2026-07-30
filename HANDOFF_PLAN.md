# IEOR Visit-Day Matching Handoff Plan

## Current branch

Development for launch readiness is on `v1-launch-ready`. Do not merge into
`master` until IEOR reviewers have tested the workflow with demo and sample data.

## What is ready

- Staff-facing Streamlit workflow for visit-day setup, intake previews,
  scheduling, diagnostics, manual review, and exports.
- Scheduler input validation with blocking errors and reviewable warnings.
- Student-level max meeting requests, defaulting to 4, with normalized
  satisfaction and meeting fulfillment diagnostics.
- Staff-controlled intake workflow with form templates, recipient CSVs, email
  text downloads, send-package logging, and response CSV upload.
- Semi-automated CSV fallback for Google Form responses:
  - student response CSV -> `preferences.csv`
  - faculty response CSV -> `availability.csv`
- Documentation for local run, Streamlit deployment, Google setup, staff usage,
  and secrets handling.
- Validation harness for environments without pytest.
- CSV sample files in `sample_data/` for testing uploads without hidden in-app
  test-data buttons.

## What is intentionally not automated

- Live Gmail/Outlook sending.
- Automatic Google Form creation.
- Automatic Google Sheet sync.
- Re-optimizing around locked manual meetings.

Staff build/send the Google Forms manually and link each form's Responses tab to
a Google Sheet. This avoids OAuth, Google Cloud setup, sender-permission issues,
and token maintenance during handoff.

## Reviewer checklist

1. Run the app locally with `streamlit run app.py`.
2. Use demo data to build a schedule.
3. Download and re-upload the sample CSVs from `sample_data/`.
4. Confirm validation appears before solving.
5. Confirm the simplified review notes flag practical issues before finalizing.
6. Try manual review:
   - lock a meeting
   - unlock it
   - remove an unlocked meeting
   - add a non-conflicting meeting
7. Download all exports.
8. Download student/faculty send packages; confirm no email is sent by the app.
9. Download `send_log.csv`.
10. Test the CSV fallback with exported Google response CSVs or synthetic samples.

## Operational notes

- Streamlit session state is temporary. Staff must download final outputs.
- Runtime files under `data/` and `outputs/` are not a durable archive.
- Credentials belong in Streamlit secrets or environment variables, never in git.
- Real student data should only be used on a private deployment with access
  controls configured by the project owner.

## Validation commands

```bash
python tests/validation_harness.py
```

Optional when available:

```bash
pytest
```
