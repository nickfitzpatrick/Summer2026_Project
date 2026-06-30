# Google setup for form and email integration

The app currently supports preview and dry-run workflows only. It validates
recipient lists, previews form content, previews email subjects and bodies, and
records dry-run send logs. It does not send real email or create live Google
Forms automatically yet.

This document describes what a developer must configure before a future guarded
live path can be enabled. Non-technical staff should not handle credentials.

## What gets wired

The app needs to do three things on the staff member's behalf:

1. Create a Google Form from the generated spec (`src/form_spec.py`).
2. Link a Google Sheet to collect responses.
3. Email each student the form link (Gmail).

That requires the Forms API, the Sheets/Drive API, and the Gmail API, plus
credentials the app can use.

## One-time setup (developer, ~30 min)

1. Go to https://console.cloud.google.com and create a project, e.g. `ieor-visitday`.
2. Under APIs and Services > Library, enable: Google Forms API, Google Drive API,
   Google Sheets API, Gmail API.
3. Under APIs and Services > OAuth consent screen, configure an internal app
   (if using a berkeley.edu Workspace) and add yourself as a test user.
4. Under Credentials, create an OAuth client ID of type Desktop app. Download the
   JSON and save it as `credentials/oauth_client.json` (this folder is gitignored).
5. First run will open a browser to authorize the staff Google account that will
   own the forms and send the email. The resulting token is cached in
   `credentials/token.json`.

Service-account alternative: a Workspace admin can create a service account with
domain-wide delegation instead, which avoids the per-run browser prompt. Use this
if a shared admin account should own everything. Either way, only `_build_live`
in `src/google_intake.py` changes.

## Implementing the live path later

All Google calls live in one function: `_build_live` in `src/google_intake.py`.
It currently raises `NotImplementedError`, and the Streamlit UI does not call it
for real sending. To turn sending on later, implement it with
`google-api-python-client` and `google-auth`, then keep preview, dry-run, final
confirmation, and send-log requirements in place:

```
pip install google-api-python-client google-auth google-auth-oauthlib
```

Steps inside `_build_live`:
- load credentials from `credentials/` (OAuth or service account),
- create the form: build questions from the `spec` dict (it already encodes
  every question type, title, and option list),
- create and link the response sheet,
- for each recipient, send the form URL via the Gmail API,
- set `form_url` and `sheet_url` on the returned `IntakeResult`.

Only enable the live call after dry-run behavior is stable and reviewed. The
button must remain disabled until staff have previewed recipients, subject, and
body, and explicitly confirmed the send.

## After responses come in

Download the linked response sheet as CSV and run the adapter to produce the
files the matcher reads:

```
python src/adapter.py path/to/responses.csv
```

This writes `data/preferences.csv` and `data/student_interests.csv`. Load
`preferences.csv` (with a faculty file and availability file) in the Build
Schedule tab.

## Known UX caveat: ordering 8 faculty

The form asks students to pick their top 8 faculty, then order them with 8
sequential dropdowns. This produces clean, gap-free rankings the solver uses
directly, but it is tedious for students with 25 faculty to scroll. If completion
rates are low, the alternative is a small custom web form with drag-to-rank;
that is a larger build and is not required for the pipeline to work.
