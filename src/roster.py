"""Load the real IEOR faculty roster and tag each faculty with one canonical area.

The roster xlsx lists 1-6 free-text research areas per faculty. The matcher and
the synthetic preference generator both want a single clean area per faculty for
interest clustering, so we collapse the free text into a fixed taxonomy.

Tagging rule: the faculty's PRIMARY listed area (Research Area 1) decides; we only
fall back to later areas when the primary has no keyword match. A few outliers
(lecturers with no listed areas, an innovation/economics professor) are pinned by
hand. The full free-text areas are preserved in a research_areas column.

Not every faculty here will actually be available on visit day. This roster is a
soft upper bound: real availability comes from each faculty's intake response.
"""

import os
import pandas as pd

# canonical areas, checked most-specific-first so e.g. an optimization person who
# also lists "power systems" lands in Optimization, not Energy.
TAXONOMY = [
    ("Robotics", ["robot"]),
    ("Energy & Power", ["power system", "electric power", "energy", "smart grid",
                        "renewable", "power optimization"]),
    ("Healthcare", ["medicine", "healthcare", "biopharm", "medical robot"]),
    ("Machine Learning & AI", ["machine learning", "deep learning", "reinforcement",
                               "artificial intelligence", "bandit", "online learning",
                               "quantum", "robot learning"]),
    ("Finance", ["credit risk", "portfolio", "investment", "trading",
                 "market microstructure", "contract theory", "financial regulation",
                 "dynamic pricing"]),
    ("Supply Chain & Logistics", ["supply chain", "logistic", "inventory", "production",
                                  "manufactur", "distribution systems", "transportation",
                                  "scheduling semiconductor", "railroad", "semiconductor"]),
    ("Stochastic & Probability", ["stochastic", "probab", "markov", "queue", "simulation",
                                  "bsde", "martingale", "mean field", "stochastic control",
                                  "stochastic modeling"]),
    ("Optimization", ["optimization", "programming", "integer", "convex", "algorithm",
                      "game theory", "matrix recovery", "combinatorial",
                      "continuous optimization"]),
]

# pinned by hand: lecturers with no listed areas, and one innovation/economics
# professor with no clean methodological bucket.
OVERRIDE = {
    ("Lee", "Fleming"): "Optimization",
    ("Lizeng", "Zhang"): "Machine Learning & AI",
    ("Svitlana", "Vyetrenko"): "Machine Learning & AI",
}

CANONICAL_AREAS = [name for name, _ in TAXONOMY]


def _tag(primary: str, rest: str) -> str:
    for text in (primary, rest):
        for name, kws in TAXONOMY:
            if any(k in text for k in kws):
                return name
    return "Optimization"  # safe default; department is optimization-centric


def _tags(full_text: str) -> list:
    """All taxonomy areas the faculty spans, in TAXONOMY (most-specific-first) order.

    Used for interest-area gap-fill: a student who picks "Energy & Power" should
    reach every faculty who touches it, not only those whose primary area it is.
    """
    matched = [name for name, kws in TAXONOMY if any(k in full_text for k in kws)]
    return matched or ["Optimization"]


def load_roster(path: str) -> pd.DataFrame:
    """Return a roster DataFrame.

    Columns: faculty_id, name, title, area, interest_areas, research_areas.
      area           single primary tag (first/most-specific match) - solver uses this
      interest_areas semicolon-joined list of every area the faculty spans - gap-fill
    """
    df = pd.read_excel(path)
    area_cols = [c for c in df.columns if c.startswith("Research Area")]

    rows = []
    for i, r in df.iterrows():
        primary = str(r[area_cols[0]]).lower() if pd.notna(r[area_cols[0]]) else ""
        rest = " ".join(str(r[c]).lower() for c in area_cols[1:] if pd.notna(r[c]))
        full_text = f"{primary} {rest}".strip()
        key = (r["First Name"], r["Last Name"])

        override = OVERRIDE.get(key)
        if override:
            area = override
            tags = [override]
        else:
            area = _tag(primary, rest)
            tags = _tags(full_text)
            tags = [area] + [t for t in tags if t != area]  # primary leads

        free_text = "; ".join(
            str(r[c]).strip() for c in area_cols if pd.notna(r[c]) and str(r[c]).strip()
        )
        rows.append(
            {
                "faculty_id": f"F{i + 1:02d}",
                "name": f"{r['First Name']} {r['Last Name']}".strip(),
                "title": r["Title"],
                "area": area,
                "interest_areas": "; ".join(tags),
                "research_areas": free_text,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(here, "data")
    roster = load_roster(os.path.join(here, "IEOR_Faculty_Roster.xlsx"))
    roster.to_csv(os.path.join(data_dir, "faculty_roster.csv"), index=False)

    # canonical taxonomy: one row per area, with the faculty who span it.
    tax_rows = []
    for name in CANONICAL_AREAS:
        members = roster[roster["interest_areas"].str.contains(name, regex=False)]
        tax_rows.append(
            {
                "interest_area": name,
                "n_faculty": len(members),
                "faculty": "; ".join(members["name"]),
            }
        )
    pd.DataFrame(tax_rows).to_csv(
        os.path.join(data_dir, "interest_areas.csv"), index=False
    )

    print(roster[["faculty_id", "name", "area", "interest_areas"]].to_string(index=False))
    print("\nprimary area counts:\n", roster["area"].value_counts().to_string())
    print("\ntaxonomy coverage (faculty per area):")
    for row in tax_rows:
        print(f"  {row['interest_area']:28s} {row['n_faculty']}")
