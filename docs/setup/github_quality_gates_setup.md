# GitHub Quality Gates Setup

This document explains the merge safety checks added for `AIR-001: Add QualityGates` and how to enable them in GitHub so code cannot be merged into `main` until the checks pass.

## What This Change Adds

The repository now includes these automated pull request checks for PRs targeting `main`:

- `AIR ticket check`
  - Verifies the pull request title contains an `AIR-<number>` ticket.
  - Defined in [`../../.github/workflows/air-ticket-check.yml`](../../.github/workflows/air-ticket-check.yml).
- `Python smoke check`
  - Installs dependencies and compiles the Python code under `services/` to catch syntax and import-time issues early.
  - Defined in [`../../.github/workflows/python-quality-gates.yml`](../../.github/workflows/python-quality-gates.yml).
- `Pipeline tests`
  - Runs the pipeline test suite in GitHub Actions using `pytest`.
  - Defined in [`../../.github/workflows/python-quality-gates.yml`](../../.github/workflows/python-quality-gates.yml).

These checks reduce the chance of merging broken Python changes when the only human review is by the author.

## Why These Checks Matter

- Ticket validation keeps PR naming consistent and makes changes traceable to work items.
- The smoke check catches broken syntax before merge.
- The test job catches regressions in the pipeline code path.
- Together, they create a minimum automated gate for `main`.

They do not replace careful review, but they are a strong baseline when a second reviewer is not available.

## GitHub Branch Protection Setup

The workflow files live in the repo, but branch protection must be enabled in GitHub settings.

In GitHub:

1. Open the repository.
2. Go to `Settings` -> `Branches`.
3. Under branch protection rules, add a rule for `main`.
4. Enable `Require a pull request before merging`.
5. Enable `Require status checks to pass before merging`.
6. Select these required checks:
   - `pr-title-must-have-air-ticket`
   - `Python smoke check`
   - `Pipeline tests`
7. Enable `Require branches to be up to date before merging`.
8. Enable `Restrict pushes that create matching branches` or disable direct pushes to `main`, depending on your GitHub plan and available options.
9. If you want the rule to apply to repo admins too, enable `Do not allow bypassing the above settings`.

## Recommended Merge Policy

For this repo, a safe default is:

- Require pull requests for `main`
- Require all three checks above
- Keep `main` protected from direct pushes
- Prefer `Squash and merge` for feature branches with multiple WIP commits

`Rebase and merge` is also fine when the branch history is already clean and each commit is meaningful.

## What Runs In CI

The GitHub Actions workflow runs:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall services
PYTHONPATH=services/pipeline python -m pytest services/pipeline/tests
```

The `PYTHONPATH` setting is important because the pipeline tests import both `run_pipeline.py` and modules from `services/pipeline/src`.

## Local Verification

You can run the same checks locally from the repository root:

```bash
python -m pip install -r requirements.txt
python -m compileall services
PYTHONPATH=services/pipeline python -m pytest services/pipeline/tests
```

## Future Improvements

If you want stronger automated protection later, consider adding:

- `ruff` for linting
- `black --check` or another formatting gate
- Docker image build validation for the pipeline and dashboard services
- Coverage thresholds for key pipeline modules

Those are useful next steps, but the current gates are a solid baseline for safe merges into `main`.
