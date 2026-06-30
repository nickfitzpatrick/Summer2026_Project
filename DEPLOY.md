# Deploying the staff app to Streamlit Community Cloud

This gives the team a persistent URL (e.g. `https://ieor-visitday.streamlit.app`)
that runs `app.py` with no local setup. Free for public or Berkeley-account repos.

The app runs in demo-data mode with no secrets, so it deploys as-is. The Google
Forms / Gmail intake is optional and stays disabled on the hosted version (it needs
OAuth credentials that should not live in a public deploy). Hosted = demo and
scheduling review; live form-sending stays local for now.

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
API keys, or service-account JSON files.

For Streamlit Community Cloud, open the app dashboard, then go to **Settings ->
Secrets**. Use TOML-style values like:

```toml
APP_PASSWORD = "replace-with-a-shared-internal-password"

[google]
client_id = "replace-me"
client_secret = "replace-me"

[email]
sender = "ieor-visitday@example.edu"
```

The current app does not yet read these values for live sending. They are
documented here so deployment owners have the correct place to put credentials
when a guarded live path is enabled.

Local developers can create `.streamlit/secrets.toml` with the same structure.
That file must not be committed.

## Keeping it updated

Every push to the deployed branch auto-redeploys. No manual step. Teammates just
refresh the URL.

## Notes and gotchas

- `requirements.txt` already pins `ortools`, `streamlit`, `pandas`, `numpy`,
  `openpyxl`, `ics`. `ortools` is large; if the build times out, redeploy once.
- `IEOR_Faculty_Roster.xlsx` is committed, so the app finds the roster on the host.
- Live form/email sending is disabled in the current app. The UI records dry-run
  send logs only. If you later want live form-sending hosted too, move OAuth
  credentials into Streamlit **Secrets** rather than committing them, and gate that
  path behind a private app. Do not put `credentials/oauth_client.json` in git.
- The app reads/writes `data/` and `outputs/` at runtime. On Streamlit Cloud these
  are ephemeral (reset on redeploy), which is correct for a demo. Anything staff
  need to keep, they download via the in-app buttons.
