"""Persistent record of form sends.

Every send (real or simulated) is appended to data/send_log.json so the intake
tab can show staff when a form last went out and to how many students. Survives
app restarts. When live Google sending is wired, the same log captures it; the
`simulated` flag distinguishes preview sends from real ones.
"""

import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(HERE, "data", "send_log.json")


def record_send(n_recipients: int, subject: str, form_url: str = "",
                sheet_url: str = "", simulated: bool = True, key: str = "student",
                body: str = "", dry_run: bool = True, status: str = "recorded") -> dict:
    """Append a send entry and return it. key tags the audience (student/faculty)."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_recipients": n_recipients,
        "subject": subject,
        "body_preview": body,
        "form_url": form_url,
        "sheet_url": sheet_url,
        "simulated": simulated,
        "dry_run": dry_run,
        "status": status,
        "audience": key,
    }
    log = _read()
    log.append(entry)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
    return entry


def last_send(key: str = "student") -> dict:
    """Most recent send for the given audience. Untagged entries count as student."""
    matches = [e for e in _read() if e.get("audience", "student") == key]
    return matches[-1] if matches else None


def all_sends() -> list:
    return _read()


def to_csv() -> str:
    """Return the send log as CSV text without requiring pandas."""
    rows = _read()
    headers = [
        "timestamp", "audience", "n_recipients", "subject", "dry_run",
        "simulated", "status", "form_url", "sheet_url", "body_preview",
    ]
    if not rows:
        return ",".join(headers) + "\n"
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def pretty_time(iso: str) -> str:
    """Human-friendly timestamp, e.g. 'June 25, 2026 at 2:14 PM'."""
    dt = datetime.fromisoformat(iso)
    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{dt.strftime('%B')} {dt.day}, {dt.year} at {hour}:{dt.strftime('%M %p')}"


def _read() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
