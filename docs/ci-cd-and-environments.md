# CI/CD and Environments

This document describes the GitHub Actions workflows, deployment environments, and known configuration issues for the Success Brand Hub (Jesse) project. GitHub is the source of truth for all automation.

## Continuous integration

`test.yml` runs on every pull request and on pushes to `main`. It installs Python and Node dependencies, runs the Jesse and Content pytest suites, builds the Astro site, and performs a secret / private-data scan. This is the primary quality gate.

## Deployment workflows

Staging is deployed by `deploy-staging.yml`, which triggers automatically after a successful `test.yml` run on `main` (via `workflow_run`) and can also be dispatched manually. It authenticates to Google Cloud using Workload Identity Federation (no service-account JSON key) and performs a read-only Google Sheets metadata check.

Production is deployed by `deploy-production.yml`. It is manual-dispatch only, requires an explicit `staging_verified` confirmation and a `rollback_sha`, and runs inside the protected `production` environment. `rollback.yml` restores a known-good commit and also runs in the `production` environment.

External providers (ElevenLabs, Twilio, n8n, Gmail, Google Calendar) remain disabled in the v1 adapter and require human approval before activation.

## Environments

The `staging` environment holds sandbox credentials and configuration variables (Workload Identity provider, service account, sandbox sheet ID, etc.).

The `production` environment holds Make.com configuration and requires reviewer approval before a deployment proceeds.

Secret values are never stored in the repository. Configuration variables (non-sensitive) are managed as GitHub Environment Variables.

## Dependency management

`.github/dependabot.yml` schedules weekly update checks for the `npm`, `pip`, and `github-actions` ecosystems, with grouped pull requests to reduce noise.

## Configuration validation

Configuration is validated by the existing `external-config-validate.yml` workflow (runs on pull requests and pushes) together with the Pydantic schemas in `agents/jessie/api/schemas.py`. No additional validation tooling is required at this time.

## Known configuration issue (documentation only)

The `deploy-staging.yml` workflow currently references several secrets under `JESSE_`-prefixed names (for example `JESSE_ELEVENLABS_API_KEY`, `JESSE_TWILIO_ACCOUNT_SID`, `JESSE_N8N_API_KEY`, `JESSE_GOOGLE_CREDENTIALS_JSON`) that do not match the secrets actually configured in the `staging` environment, which use `SANDBOX`-style names (for example `ELEVENLABS_SANDBOX_API_KEY`, `TWILIO_SANDBOX_ACCOUNT_SID`, `N8N_SANDBOX_*`). In addition, `JESSE_GOOGLE_STAGING_CALENDAR_ID` exists as a variable, not a secret.

Because unmatched `secrets.*` references resolve to empty strings, any staging step that depends on those values is effectively unconfigured. This is a latent issue and is documented here for follow-up. Reconciling these names touches the deploy workflow and should be handled in a separate, reviewed change rather than as part of this cleanup.
