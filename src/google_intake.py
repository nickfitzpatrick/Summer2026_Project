"""Google intake plumbing, isolated behind one interface.

Everything that talks to Google (Forms, Sheets, Gmail) lives here so the rest of
the app never imports a Google library. The app calls send_intake(...) and gets
back an IntakeResult. Two modes:

  dry_run=True  (default)  validate the student CSV, build the form spec, and
                           return what WOULD happen. No network, no credentials.
                           This is what runs in demos and during development.
  dry_run=False            intentionally unsupported in the launch workflow.
                           Staff send the generated email/package manually.

The launch workflow is deliberately semi-automated: the app prepares form specs,
recipient lists, and email text; staff send the emails themselves and upload
response CSVs after collection.
"""

from dataclasses import dataclass, field
import os
import re

import pandas as pd

from form_spec import build_spec

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    """Validate recipients and build the form-send preview package.

    Pass either roster_path (builds the student preference form) or a prebuilt
    spec (e.g. the faculty availability form). Everything downstream - recipient
    validation, reporting, and the manual-send package - is shared.

    The launch workflow is staff-controlled. The app does not call Gmail or
    Google Forms APIs; staff send the generated email text manually.
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

    msgs.append("STAFF-SEND MODE: no form created and no email sent by the app.")
    return IntakeResult(
        ok=True, dry_run=True, n_recipients=len(clean),
        recipients=clean, errors=errors, messages=msgs,
    )
