"""Generate a wide response sheet that mimics Google Form output, including the
messy edge cases the adapter must survive. Writes data/responses_sample.csv."""

import os
import random
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from roster import load_roster, CANONICAL_AREAS
from form_spec import Q_FIRST, Q_LAST, Q_EMAIL, Q_TOPSET, Q_INTERESTS, TOP_N, _rank_title

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
roster = load_roster(os.path.join(HERE, "IEOR_Faculty_Roster.xlsx"))
names = roster["name"].tolist()
random.seed(7)

FIRST = ["Maya", "Liam", "Sofia", "Noah", "Aisha", "Diego", "Wei", "Priya", "Omar", "Lena"]
LAST = ["Patel", "Nguyen", "Garcia", "Kim", "Hassan", "Silva", "Chen", "Rao", "Farah", "Novak"]

rows = []
for i in range(10):
    picks = random.sample(names, TOP_N)
    row = {
        "Timestamp": f"2026/03/0{i % 9 + 1} 10:0{i}:00",  # Google adds this column
        Q_FIRST: FIRST[i],
        Q_LAST: LAST[i],
        Q_EMAIL: f"{FIRST[i].lower()}.{LAST[i].lower()}@example.edu",
        Q_TOPSET: ", ".join(picks),
    }
    for j, name in enumerate(picks, start=1):
        row[_rank_title(j)] = name
    k = random.randint(1, 3)
    row[Q_INTERESTS] = ", ".join(random.sample(CANONICAL_AREAS, k))
    rows.append(row)

# inject edge cases on specific rows
rows[2][_rank_title(2)] = rows[2][_rank_title(1)]      # duplicate pick
rows[4][_rank_title(8)] = ""                            # blank trailing slot
rows[6][_rank_title(3)] = "Professor Nonexistent"      # unmatched name
rows[8][Q_INTERESTS] = rows[8][Q_INTERESTS] + ", Quantum Widgets"  # bad area

df = pd.DataFrame(rows)
out = os.path.join(HERE, "data", "responses_sample.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
df.to_csv(out, index=False)
print(f"wrote {out}  ({len(df)} rows, {len(df.columns)} columns)")
