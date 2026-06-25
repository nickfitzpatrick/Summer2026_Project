# Git cleanup before the team handoff

Run these on your Mac, in the project folder, in order. They clear a stale lock,
remove design scratch from version control, and commit the handoff fixes.

## 1. Clear the stale lock

A crashed git process left `.git/index.lock`. Until it is gone, every commit or
pull fails with "Unable to create index.lock: File exists". Remove it:

```
cd ~/Desktop/CoWork/Summer2026_Project
rm -f .git/index.lock
```

If `git status` runs cleanly after this, the lock is gone.

## 2. Stop tracking DesignAssets

`DesignAssets/` (palette and page screenshots) is working scratch, not part of the
app, and is now gitignored. Remove it from tracking without deleting the local files:

```
git rm -r --cached DesignAssets
git rm -r --cached .pytest_cache 2>/dev/null || true
```

## 3. Review and commit

```
git status                 # confirm: .gitignore, tests/test_pipeline.py modified;
                           #          DesignAssets + .pytest_cache staged for removal
git add .gitignore tests/test_pipeline.py
git commit -m "Handoff cleanup: gitignore DesignAssets, make pipeline test pytest-collectable"
git push
```

## What changed and why

- `.gitignore`: added `DesignAssets/` and `.pytest_cache/` so design scratch and
  test caches stay out of the repo, consistent with how `WebImages/` was handled.
- `tests/test_pipeline.py`: the checks ran as a bare script, so `pytest` collected
  nothing and reported success while running zero assertions. Wrapped in a
  `test_pipeline()` function with a final `assert`, so `pytest` now actually runs
  it. The `python tests/test_pipeline.py` path still works and still prints
  PASS/FAIL lines.

Run `pytest` after committing to confirm: you should see `1 passed`.
