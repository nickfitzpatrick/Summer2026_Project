# Deploying the staff app to Streamlit Community Cloud

This gives the team a persistent URL (e.g. `https://ieor-visitday.streamlit.app`)
that runs `app.py` with no local setup. Free for public or Berkeley-account repos.

The app can deploy with demo data, but set `APP_PASSWORD` in Streamlit Secrets
before sharing a public URL. The Google Forms / Gmail intake is optional and
stays disabled on the hosted version until credentials are configured.

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
ENABLE_LIVE_EMAIL_SENDING = "false"
GOOGLE_SENDER_EMAIL = "ieor-visitday@example.edu"
GOOGLE_OAUTH_TOKEN_JSON = """
paste-the-entire-contents-of-credentials-token-json-here
"""
```

Keep `ENABLE_LIVE_EMAIL_SENDING = "false"` until dry-run previews, send logs,
and one internal test recipient have been verified. See `SETUP_GOOGLE.md` for
the OAuth token setup.

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
- Live form/email sending is guarded by `ENABLE_LIVE_EMAIL_SENDING`, Google
  OAuth credentials, recipient preview, and an in-app `SEND LIVE` confirmation.
  Do not put `credentials/oauth_client.json` or `credentials/token.json` in git.
- After the app creates a Google Form, staff still need to open the form's
  Responses tab and link it to a Google Sheet before collecting responses.
- The app reads/writes `data/` and `outputs/` at runtime. On Streamlit Cloud these
  are ephemeral (reset on redeploy), which is correct for a demo. Anything staff
  need to keep, they download via the in-app buttons.
