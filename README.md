# IEOR Visit-Day Matching Tool

Matches prospective grad students with faculty during the two-day visit, maximizing
preference-weighted meetings while keeping the schedule fair across students.

## Key decisions baked in
- 20-min meeting + 5-min buffer = 25-min slot (set in `src/config.py`, change there).
- Two days, identical grid. 16 slots/day, 32 total with a noon lunch excluded.
- Faculty sit in fixed offices on one floor; students travel (buffer covers walking).
- Students rank a top-N of faculty; the solver only places ranked pairs.

## Layout
- `src/config.py` all tunable numbers
- `src/grid.py` builds the discrete slot grid (solver sees slot_id; clock times are for rendering)
- `src/synthetic.py` synthetic data generator (skewed popularity, clustered interests, availability gaps)
- `src/model.py` CP-SAT optimizer (preference value + fairness term)
- `src/run.py` end-to-end: generate -> solve -> render schedules

## Run
```
pip install -r requirements.txt
python src/run.py        # CLI: generate, solve, print metrics
streamlit run app.py     # staff app: load data, match, view, download
```

## Staff app (app.py)
Built for non-technical IEOR staff. Generate demo data or upload the three intake
CSVs, set meeting/buffer length in the sidebar, click Match, then review per-student
and per-faculty schedules and download them. The slot length set here flows through
the grid, model, and rendered times.

## Next steps for the team
1. Intake forms: Google Form -> CSV for faculty availability and student rankings, matching the schemas in `data/`.
2. .ics export per student and per faculty (the `ics` lib is already in requirements).
3. Manual override in the app: let staff drag/swap a meeting after solving.
4. Validation: build a deliberately over-subscribed instance and report how the max-min floor allocates the shortfall.
