# Google setup for live form sending

The Collect Preferences tab works in preview (dry-run) mode with no setup: it
validates the student list and shows exactly what would be sent. To actually
create the form and email students, a developer does the one-time setup below.
Non-technical staff never touch this; once it is done, staff just upload a CSV
and click the button.

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

## Implementing the live path

All Google calls live in one function: `_build_live` in `src/google_intake.py`.
It currently raises `NotImplementedError`. To turn sending on, implement it with
`google-api-python-client` and `google-auth`:

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

Nothing else in the app changes: the Collect Preferences tab already calls
`send_intake(..., dry_run=False)` and renders whatever URLs come back.

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
