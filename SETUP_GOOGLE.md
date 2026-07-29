# Google setup for form and email integration

The app supports two intake modes:

- Dry run: validate recipients, preview the form/email, and record a send log.
- Live send: create a Google Form from the generated spec and email the form URL
  to every reviewed recipient through Gmail.

Live sending is locked unless `ENABLE_LIVE_EMAIL_SENDING=true` is set in
Streamlit Secrets or the local environment. Staff must still review the
recipient list and type `SEND LIVE` in the app before any real email is sent.

## What is automated

1. Create the student preference or faculty availability Google Form.
2. Add questions from `src/form_spec.py` or `src/faculty_form_spec.py`.
3. Send the Google Form responder link by Gmail.
4. Record the real send in `send_log.csv`.

## What remains manual

After the form is created, open the form, go to **Responses**, and connect the
responses to a Google Sheet using the green Sheets button. This mirrors the
normal Google Forms UI flow and keeps response ownership clear.

After responses arrive:

1. Open the linked response Sheet.
2. Export/download as CSV.
3. Upload the CSV in the matching intake tab.
4. Let the app convert it to solver-ready CSVs.

## One-time Google Cloud setup

1. Go to https://console.cloud.google.com and create a project, for example
   `ieor-visitday`.
2. Enable these APIs:
   - Google Forms API
   - Gmail API
3. Configure the OAuth consent screen. For a Berkeley Workspace project, prefer
   an internal app if available. Otherwise, add the staff sender account as a
   test user while testing.
4. Create an OAuth client ID of type **Desktop app**.
5. Download the client JSON.

The OAuth account you authorize should be the account that owns the Google Forms
and sends the emails.

## Generate a local OAuth token

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local gitignored credentials folder:

```bash
mkdir credentials
```

Save the OAuth client file as:

```text
credentials/oauth_client.json
```

Run the app locally and attempt a live send, or run a small Python call to
`send_intake(..., dry_run=False)`. The first authorization opens a browser and
writes:

```text
credentials/token.json
```

Do not commit either credentials file.

## Streamlit Cloud secrets

Open the Streamlit app dashboard, then **Settings -> Secrets**. Add:

```toml
APP_PASSWORD = "replace-with-a-shared-internal-password"
ENABLE_LIVE_EMAIL_SENDING = "true"
GOOGLE_SENDER_EMAIL = "sender@example.edu"
GOOGLE_OAUTH_TOKEN_JSON = """
paste-the-entire-contents-of-credentials-token-json-here
"""
```

Recommended rollout:

1. Deploy first with `ENABLE_LIVE_EMAIL_SENDING = "false"`.
2. Confirm dry-run previews and send logs work.
3. Add `GOOGLE_OAUTH_TOKEN_JSON`.
4. Change `ENABLE_LIVE_EMAIL_SENDING` to `"true"`.
5. Send to one internal test recipient first.
6. Confirm the form opens and the email is delivered.
7. Link the form Responses tab to a Google Sheet.

## Local environment alternative

Instead of Streamlit Secrets, local developers can set environment variables:

```powershell
$env:APP_PASSWORD = "local-password"
$env:ENABLE_LIVE_EMAIL_SENDING = "true"
$env:GOOGLE_SENDER_EMAIL = "sender@example.edu"
$env:GOOGLE_OAUTH_TOKEN_JSON = Get-Content credentials/token.json -Raw
streamlit run app.py
```

If `GOOGLE_OAUTH_TOKEN_JSON` is not set locally, the app will look for
`credentials/token.json`.

## Safety rules

- Never commit OAuth client JSON, token JSON, passwords, or sender credentials.
- Keep CSV upload/download fallback workflows available.
- Never bypass the in-app recipient preview and `SEND LIVE` confirmation.
- Test student and faculty live sends with a small internal list before sending
  to real participants.
- If a live send fails, download `send_log.csv`, check Streamlit Cloud logs, and
  verify the OAuth account still has Forms/Gmail API access.
