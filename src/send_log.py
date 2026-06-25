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
                sheet_url: str = "", simulated: bool = True, key: str = "student") -> dict:
    """Append a send entry and return it. key tags the audience (student/faculty)."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_recipients": n_recipients,
        "subject": subject,
        "form_url": form_url,
        "sheet_url": sheet_url,
        "simulated": simulated,
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


def pretty_time(iso: str) -> str:
    """Human-friendly timestamp, e.g. 'June 25, 2026 at 2:14 PM'."""
    dt = datetime.fromisoformat(iso)
    return dt.strftime("%B %-d, %Y at %-I:%M %p")


def _read() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
