"""Google intake plumbing, isolated behind one interface.

Everything that talks to Google (Forms, Sheets, Gmail) lives here so the rest of
the app never imports a Google library. The app calls send_intake(...) and gets
back an IntakeResult. Two modes:

  dry_run=True  (default)  validate the student CSV, build the form spec, and
                           return what WOULD happen. No network, no credentials.
                           This is what runs in demos and during development.
  dry_run=False            actually create the form + response sheet and email
                           each student. Requires credentials (see SETUP_GOOGLE.md).

The live path is intentionally thin and all in one place: when credentials are
ready, fill in _build_live() and nothing else in the app has to change.
"""

from dataclasses import dataclass, field
import base64
from email.message import EmailMessage
import json
import os
import re

import pandas as pd

from form_spec import build_spec, Q_EMAIL

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/gmail.send",
]


@dataclass
class IntakeResult:
    ok: bool
    dry_run: bool
    n_recipients: int
    form_url: str = ""
    sheet_url: str = ""
    recipients: list = field(default_factory=list)   # cleaned (name, email) rows
    errors: list = field(default_factory=list)       # per-row problems
    messages: list = field(default_factory=list)     # human-readable status lines


def validate_recipients(df: pd.DataFrame):
    """Return (clean_rows, errors). Expects columns name/first+last and email."""
    errors = []
    cols = {c.lower().strip(): c for c in df.columns}

    email_col = cols.get("email")
    name_col = cols.get("name")
    first_col = cols.get("first name") or cols.get("first")
    last_col = cols.get("last name") or cols.get("last")

    if not email_col:
        return [], ["CSV must have an 'email' column."]
    if not name_col and not (first_col and last_col):
        return [], ["CSV must have a 'name' column, or 'first name' and 'last name'."]

    clean, seen = [], set()
    for i, r in df.iterrows():
        if name_col:
            name = str(r[name_col]).strip()
        else:
            name = f"{r[first_col]} {r[last_col]}".strip()
        email = str(r[email_col]).strip().lower()

        if not EMAIL_RE.match(email):
            errors.append(f"Row {i + 2}: invalid email '{email}'.")
            continue
        if email in seen:
            errors.append(f"Row {i + 2}: duplicate email '{email}'; skipped.")
            continue
        seen.add(email)
        clean.append({"name": name or email, "email": email})
    return clean, errors


def send_intake(recipients_df: pd.DataFrame, roster_path: str = None, dry_run: bool = True,
                credentials_path: str = None, spec: dict = None, subject: str = "",
                body: str = "", sender: str = "") -> IntakeResult:
    """Validate recipients, build the form spec, and (live only) create + email.

    Pass either roster_path (builds the student preference form) or a prebuilt
    spec (e.g. the faculty availability form). Everything downstream - recipient
    validation, dry-run reporting, and the live Google path - is shared.

    In dry-run this performs every step that does not require Google and reports
    exactly what the live run would send.
    """
    clean, errors = validate_recipients(recipients_df)
    if spec is None:
        spec = build_spec(roster_path)

    if not clean:
        return IntakeResult(
            ok=False, dry_run=dry_run, n_recipients=0, errors=errors,
            messages=["No valid recipients found; nothing to send."],
        )

    msgs = [
        f"Form: '{spec['title']}' with {len(spec['questions'])} questions.",
        f"{len(clean)} valid recipient(s) ready.",
    ]
    if errors:
        msgs.append(f"{len(errors)} recipient row(s) had problems (see details).")

    if dry_run:
        msgs.append("DRY RUN: no form created and no email sent.")
        return IntakeResult(
            ok=True, dry_run=True, n_recipients=len(clean),
            recipients=clean, errors=errors, messages=msgs,
        )

    return _build_live(spec, clean, errors, msgs, credentials_path, subject, body, sender)


def live_config_status() -> tuple[bool, list]:
    """Return whether Google live sending looks configured, plus staff messages."""
    missing = []
    if not (_secret_json("GOOGLE_OAUTH_TOKEN_JSON") or os.path.exists(_default_token_path())):
        missing.append("Google OAuth token or service-account JSON is not configured.")
    return (len(missing) == 0), missing


def _build_live(spec, clean, errors, msgs, credentials_path, subject, body, sender) -> IntakeResult:
    """Create a Google Form and send its link through Gmail.

    Response-sheet linking is still a manual Google Forms UI step because the
    public Forms API does not provide the same simple destination picker that the
    Forms web UI exposes. The returned messages tell staff to link responses in
    the form after creation.
    """
    try:
        creds = _load_credentials(credentials_path)
        forms = _google_build("forms", "v1", credentials=creds)
        gmail = _google_build("gmail", "v1", credentials=creds)

        created = forms.forms().create(body={
            "info": {
                "title": spec["title"],
                "documentTitle": spec["title"],
            }
        }).execute()
        form_id = created["formId"]
        _populate_form(forms, form_id, spec)
        form = forms.forms().get(formId=form_id).execute()
        form_url = form.get("responderUri") or f"https://docs.google.com/forms/d/{form_id}/viewform"

        email_body = _body_with_form_link(body, form_url)
        for recipient in clean:
            _send_email(
                gmail,
                to=recipient["email"],
                subject=subject or spec["title"],
                body=email_body,
                sender=sender,
            )

        msgs.extend([
            "LIVE SEND: Google Form created and email messages sent.",
            "Open the form Responses tab and link it to a Google Sheet before collecting responses.",
        ])
        return IntakeResult(
            ok=True,
            dry_run=False,
            n_recipients=len(clean),
            form_url=form_url,
            sheet_url="",
            recipients=clean,
            errors=errors,
            messages=msgs,
        )
    except Exception as exc:
        return IntakeResult(
            ok=False,
            dry_run=False,
            n_recipients=len(clean),
            recipients=clean,
            errors=errors + [f"Live Google send failed: {exc}"],
            messages=msgs,
        )


def _populate_form(forms, form_id, spec):
    requests = [{
        "updateFormInfo": {
            "info": {"description": spec.get("description", "")},
            "updateMask": "description",
        }
    }]
    for index, q in enumerate(spec["questions"]):
        requests.append({
            "createItem": {
                "item": _question_item(q),
                "location": {"index": index},
            }
        })
    forms.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()


def _question_item(q):
    question = {"required": bool(q.get("required"))}
    qtype = q.get("type")
    if qtype in {"text", "email"}:
        question["textQuestion"] = {"paragraph": False}
    elif qtype in {"checkbox", "dropdown"}:
        choice_type = "CHECKBOX" if qtype == "checkbox" else "DROP_DOWN"
        question["choiceQuestion"] = {
            "type": choice_type,
            "options": [{"value": str(option)} for option in q.get("options", [])],
            "shuffle": False,
        }
    else:
        raise ValueError(f"Unsupported Google Form question type: {qtype}")

    item = {
        "title": q["title"],
        "questionItem": {"question": question},
    }
    if q.get("help"):
        item["description"] = q["help"]
    return item


def _send_email(gmail, to, subject, body, sender=""):
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    if sender:
        msg["From"] = sender
    msg.set_content(body)
    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    gmail.users().messages().send(userId="me", body={"raw": encoded}).execute()


def _body_with_form_link(body, form_url):
    body = (body or "").strip()
    if "{form_url}" in body:
        return body.replace("{form_url}", form_url)
    return f"{body}\n\nForm link:\n{form_url}\n"


def _load_credentials(credentials_path=None):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_info = _secret_json("GOOGLE_OAUTH_TOKEN_JSON")
    if token_info:
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    elif os.path.exists(_default_token_path()):
        creds = Credentials.from_authorized_user_file(_default_token_path(), SCOPES)
    else:
        creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if creds and creds.valid:
        return creds

    client_path = credentials_path or os.environ.get("GOOGLE_OAUTH_CLIENT_PATH") or _default_client_path()
    client_info = _secret_json("GOOGLE_OAUTH_CLIENT_JSON")
    if client_info:
        flow = InstalledAppFlow.from_client_config(client_info, SCOPES)
    elif os.path.exists(client_path):
        flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
    else:
        raise RuntimeError(
            "Missing Google OAuth credentials. Configure GOOGLE_OAUTH_TOKEN_JSON in Streamlit Secrets "
            "or create credentials/token.json locally."
        )

    creds = flow.run_local_server(port=0)
    os.makedirs(os.path.dirname(_default_token_path()), exist_ok=True)
    with open(_default_token_path(), "w") as f:
        f.write(creds.to_json())
    return creds


def _secret_json(name):
    raw = os.environ.get(name)
    try:
        import streamlit as st
        raw = st.secrets.get(name, raw)
    except Exception:
        pass
    if not raw:
        return None
    if isinstance(raw, dict):
        return dict(raw)
    return json.loads(raw)


def _google_build(*args, **kwargs):
    from googleapiclient.discovery import build

    return build(*args, **kwargs)


def _default_client_path():
    return os.path.join(_credentials_dir(), "oauth_client.json")


def _default_token_path():
    return os.path.join(_credentials_dir(), "token.json")


def _credentials_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials")
