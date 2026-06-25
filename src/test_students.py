"""Synthetic prospective-student roster for testing the intake tab.

Returns a name + email list in the shape the intake CSV expects, so staff can try
the Collect Preferences flow without a real student list. This is the intake
roster only; filled-in form responses for testing the matcher live separately in
tests/make_sample_responses.py.
"""

import random

import pandas as pd

FIRST = [
    "Maya", "Liam", "Sofia", "Noah", "Aisha", "Diego", "Wei", "Priya", "Omar",
    "Lena", "Arjun", "Hana", "Mateo", "Yuki", "Fatima", "Caleb", "Ingrid",
    "Tomas", "Nadia", "Ravi", "Elena", "Kofi", "Mira", "Sven", "Leila",
]
LAST = [
    "Patel", "Nguyen", "Garcia", "Kim", "Hassan", "Silva", "Chen", "Rao",
    "Farah", "Novak", "Okafor", "Tanaka", "Lopez", "Andersson", "Khan",
    "Mbeki", "Romano", "Petrov", "Haddad", "Singh", "Costa", "Mensah",
    "Schmidt", "Dubois", "Park",
]


def generate_students(n: int = 25, seed: int = 11, domain: str = "berkeley.edu") -> pd.DataFrame:
    """Return a DataFrame with name and email columns for n unique students."""
    rng = random.Random(seed)
    pairs = set()
    rows = []
    while len(rows) < n:
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name in pairs:
            continue
        pairs.add(name)
        handle = name.lower().replace(" ", ".")
        rows.append({"name": name, "email": f"{handle}@{domain}"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_students()
    print(df.to_string(index=False))
