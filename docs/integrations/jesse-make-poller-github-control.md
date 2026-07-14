# Jesse Intake Poller GitHub control

This workflow adds reviewed, GitHub-controlled export and deployment for the inactive Make.com scenario `Jesse Intake Poller Test`.

## Required GitHub staging environment values

Secret:

- `MAKE_API_TOKEN`

Variables:

- `MAKE_API_BASE_URL`, for example `https://us1.make.com/api/v2`
- `MAKE_POLLER_SCENARIO_ID`, set to the inactive Jesse Intake Poller Test scenario ID

The dedicated workflow maps `MAKE_POLLER_SCENARIO_ID` to the existing sync utility's approved Make scenario alias only inside the job. It does not change appointment, cancellation, or rescheduling scenario identifiers.

## Workflow

Open **Actions → Jesse Make poller config → Run workflow**.

Operations:

1. `export`: performs read-only scenario and draft-blueprint requests, redacts sensitive values, and uploads a seven-day artifact.
2. `dry-run`: validates the tracked manifest and reports the planned fields without writing to Make.
3. `apply`: requires the exact confirmation `APPLY` and patches only the configured inactive poller scenario.

Tracked manifest:

`config/external/make/jesse-intake-poller.staging.json`

The manifest is intentionally empty until a redacted export is reviewed. An empty manifest cannot be applied.

## Safe operating procedure

1. Run `export`.
2. Download and inspect the redacted artifact.
3. Copy only the intended safe blueprint or scenario fields into the tracked manifest.
4. Open a pull request and review the JSON diff.
5. Merge only after CI passes.
6. Run `dry-run`.
7. Run `apply` only after explicit approval.
8. Keep the Make scenario inactive.
9. Run the empty-batch, positive-batch, and duplicate-prevention tests manually in Make.
10. Record evidence in GitHub Issue #50 and the canonical Google Doc.

## Guardrails

- The workflow cannot activate the scenario.
- It is fixed to the staging environment.
- It accepts only the dedicated poller manifest path.
- It does not expose the Make token or scenario ID in summaries.
- It does not touch production cancellation or rescheduling scenarios.
- Provider write is disabled unless `operation=apply` and confirmation equals `APPLY`.
- Manual Make execution evidence remains required before production activation.

## Rollback

Restore the previous reviewed manifest in a new pull request, run `dry-run`, then run `apply`. If the scenario behaves incorrectly, keep it inactive and restore the prior blueprint through the same reviewed process.
