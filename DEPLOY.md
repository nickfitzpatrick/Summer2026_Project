# Deploying the staff app to Streamlit Community Cloud

This gives the team a persistent URL (e.g. `https://ieor-visitday.streamlit.app`)
that runs `app.py` with no local setup. Free for public or Berkeley-account repos.

The app can deploy with demo data, but set `APP_PASSWORD` in Streamlit Secrets
before sharing a public URL. The launch intake workflow is staff-controlled:
the app generates templates, recipient lists, and email text; staff send emails
manually and upload exported response CSVs.

## Prerequisites

- The repo is pushed to GitHub at `nickfitzpatrick/Summer2026_Project` (already set
  as `origin`). Finish `HANDOFF_GIT.md` first so the latest code is on `main`/`master`.
- A Streamlit Community Cloud account: sign in at https://share.streamlit.io with the
  GitHub account that owns the repo.

## Steps

1. Go to https://share.streamlit.io and sign in with GitHub. Authorize Streamlit to
   read the repo when prompted.
2. Click **Create app** -> **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `nickfitzpatrick/Summer2026_Project`
   - Branch: `master` (or `main` if you rename it)
   - Main file path: `app.py`
4. Optional: set a custom subdomain under **Advanced settings** (e.g. `ieor-visitday`).
5. Click **Deploy**. First build installs `requirements.txt` and takes 2-4 minutes.
   When it finishes you get a shareable URL.

## Sharing with the team

- A **public** app: anyone with the link can open it. Fine for synthetic demo data.
- To restrict access, in the app's **Settings -> Sharing** invite teammates by email;
  only invited Google/GitHub accounts can then view it.

## Streamlit secrets

Do not commit passwords, OAuth client secrets, Gmail accounts, Berkeley accounts,
API keys, or service-account JSON files. The app checks `APP_PASSWORD` before it
shows the scheduling interface.

For Streamlit Community Cloud, open the app dashboard, then go to **Settings ->
Secrets**. Use TOML-style values like:

```toml
APP_PASSWORD = "replace-with-a-shared-internal-password"
```

Local developers can create `.streamlit/secrets.toml` with the same structure.
That file must not be committed.

If `APP_PASSWORD` is missing, the app shows a warning and allows local/demo use.
For any shared deployment, treat `APP_PASSWORD` as required.

## Keeping it updated

Every push to the deployed branch auto-redeploys. No manual step. Teammates just
refresh the URL.

## Validation before deploying

Run these checks before pushing a deployment branch:

```bash
python tests/validation_harness.py
```

If `pytest` is available, also run:

```bash
pytest
```

The bundled harness covers the intake pipeline, input validation, and faculty
availability CSV adapter. In a full local environment with `ortools` installed,
the pipeline test also verifies the solver path.

## Notes and gotchas

- `requirements.txt` already pins `ortools`, `streamlit`, `pandas`, `numpy`,
  `openpyxl`, `ics`. `ortools` is large; if the build times out, redeploy once.
- `IEOR_Faculty_Roster.xlsx` is committed, so the app finds the roster on the host.
- The app does not send live email in the launch workflow. Staff use the
  downloaded recipients and email text in Gmail or Outlook.
- Staff should manually link each Google Form's Responses tab to a Google Sheet
  before collecting responses.
- The app reads/writes `data/` and `outputs/` at runtime. On Streamlit Cloud these
  are ephemeral (reset on redeploy), which is correct for a demo. Anything staff
  need to keep, they download via the in-app buttons.
