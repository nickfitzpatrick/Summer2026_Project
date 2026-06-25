"""Single source of truth for the student intake form.

Builds the form definition from the real roster and the interest-area taxonomy,
so the form options stay in sync with the faculty data automatically. The same
spec drives form creation (google_intake.py) and response parsing (adapter.py):
the question titles here ARE the response-sheet column headers, so the two sides
can never drift.

Ranking design: students pick a top-N set, then order it via N ordered single-
choice questions ("1st choice" ... "Nth choice"), each listing every faculty.
Ordered dropdowns give a strict, gap-free rank that the adapter reads directly.
"""

import json
import os

from roster import load_roster, CANONICAL_AREAS

TOP_N = 8  # how many faculty a student ranks; matches Config.prefs_per_student

# Fixed question titles. These double as response-sheet column headers, so the
# adapter keys off them. Do not rename without updating the adapter in lockstep.
Q_FIRST = "First Name"
Q_LAST = "Last Name"
Q_EMAIL = "Email"
Q_TOPSET = f"Select your top {TOP_N} faculty to meet"
Q_INTERESTS = "Select your areas of interest"
RANK_LABELS = ["1st", "2nd", "3rd"] + [f"{i}th" for i in range(4, TOP_N + 1)]


def _rank_title(i: int) -> str:
    """Column header for the i-th ordered choice (1-indexed)."""
    return f"{RANK_LABELS[i - 1]} choice faculty"


def build_spec(roster_path: str) -> dict:
    """Return a form spec dict built from the live roster.

    Structure is builder-agnostic: each question has a type, title, and options.
    google_intake.py maps these onto the Google Forms API; the adapter reads the
    same titles back out of the response sheet.
    """
    roster = load_roster(roster_path)
    faculty_names = roster["name"].tolist()

    questions = [
        {"type": "text", "title": Q_FIRST, "required": True},
        {"type": "text", "title": Q_LAST, "required": True},
        {"type": "email", "title": Q_EMAIL, "required": True},
        {
            "type": "checkbox",
            "title": Q_TOPSET,
            "options": faculty_names,
            "required": True,
            "limit": TOP_N,
            "help": f"Pick exactly {TOP_N}. You will order them on the next questions.",
        },
    ]

    for i in range(1, TOP_N + 1):
        questions.append(
            {
                "type": "dropdown",
                "title": _rank_title(i),
                "options": faculty_names,
                "required": True,
                "help": "Must be one of the faculty you selected above.",
            }
        )

    questions.append(
        {
            "type": "checkbox",
            "title": Q_INTERESTS,
            "options": CANONICAL_AREAS,
            "required": True,
            "help": "Used to fill schedule gaps with faculty in areas you care about.",
        }
    )

    return {
        "title": "IEOR Visit Day - Faculty Meeting Preferences",
        "description": (
            "Tell us which faculty you would most like to meet during your visit. "
            f"Select your top {TOP_N}, order them, and pick your research interests."
        ),
        "top_n": TOP_N,
        "faculty": roster[["faculty_id", "name"]].to_dict("records"),
        "interest_areas": CANONICAL_AREAS,
        "questions": questions,
    }


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = build_spec(os.path.join(here, "IEOR_Faculty_Roster.xlsx"))
    out = os.path.join(here, "data", "form_spec.json")
    with open(out, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"wrote {out}")
    print(f"{len(spec['questions'])} questions, {len(spec['faculty'])} faculty, "
          f"{len(spec['interest_areas'])} interest areas")
    for q in spec["questions"]:
        n = len(q.get("options", []))
        print(f"  [{q['type']:8s}] {q['title']}" + (f"  ({n} options)" if n else ""))
