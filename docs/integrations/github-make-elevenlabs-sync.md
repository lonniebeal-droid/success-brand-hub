# GitHub control for Make and ElevenLabs

GitHub is the reviewed source of truth for approved Jesse configuration changes. The workflows in this repository can read current Make or ElevenLabs configuration, validate a proposed patch, preview it without writing, and apply it only after an intentional manual run.

This does **not** make every GitHub edit immediately live. That separation is deliberate:

1. Export the provider's current configuration as a short-lived, redacted artifact.
2. Review it and copy only the intended safe patch into `config/external/`.
3. Open and approve a pull request.
4. Run a dry-run deployment from GitHub Actions.
5. Apply to `staging` and verify with fake data.
6. Apply to `production` only through the protected production environment and an explicit `DEPLOY` confirmation.

## Supported provider operations

- ElevenLabs: read an agent with `GET /v1/convai/agents/{agent_id}` and update approved fields with `PATCH /v1/convai/agents/{agent_id}`.
- Make: read scenario details and a draft blueprint, then update approved fields with `PATCH /api/v2/scenarios/{scenarioId}`.

Official references:

- [ElevenLabs Get agent](https://elevenlabs.io/docs/eleven-agents/api-reference/agents/get)
- [ElevenLabs Update agent](https://elevenlabs.io/docs/api-reference/agents/update)
- [Make scenario API](https://developers.make.com/api-documentation/api-reference/scenarios)
- [Make scenario blueprint API](https://developers.make.com/api-documentation/api-reference/scenarios-greater-than-blueprints)

## Repository files

```text
config/external/elevenlabs/
config/external/make/
scripts/external_config_sync.py
.github/workflows/external-config-validate.yml
.github/workflows/external-config-export.yml
.github/workflows/external-config-deploy.yml
```

Tracked manifests contain only a provider, target, environment-variable name for the resource ID, and an approved partial update payload. Empty manifests are safe placeholders. An empty manifest cannot be applied.

## GitHub environment configuration

Create the following in the existing `staging` environment. Repeat with production-specific values in the protected `production` environment only after staging verification.

### ElevenLabs

Secret:

```text
ELEVENLABS_API_KEY
```

Variables:

```text
ELEVENLABS_AGENT_ID
ELEVENLABS_BRANCH_ID        # optional
```

Use a restricted staging key and cloned staging agent in the staging environment. The production key and live Jesse agent ID belong only in the production environment.

The workflows also recognize the existing staging names `ELEVENLABS_SANDBOX_API_KEY` and `ELEVENLABS_SANDBOX_AGENT_ID`, so the current cloned-agent readiness setup does not have to be duplicated.

### Make

Secret:

```text
MAKE_API_TOKEN
```

Variables:

```text
MAKE_API_BASE_URL=https://us1.make.com/api/v2
MAKE_APPOINTMENT_SCENARIO_ID
MAKE_CANCELLATION_SCENARIO_ID
MAKE_RESCHEDULE_SCENARIO_ID
```

Use the Make zone for the account (`us1`, `us2`, `eu1`, or the applicable official Make zone). The token needs `scenarios:read` for export and `scenarios:write` for deployment. Prefer separate read-only and write tokens if the account supports that operating model.

## Export current configuration

In GitHub, open **Actions → Export Make or ElevenLabs config → Run workflow**. Select the provider, target, and approved resource ID variable. The workflow performs read-only requests and uploads a redacted artifact for seven days.

The export never commits changes. It strips credential-like fields and outbound URLs. A `__REDACTED__` placeholder must never be deployed. If a Make blueprint relies on a webhook URL or another secret value, keep that value managed inside Make and limit the GitHub patch to fields that do not require the secret.

## Review and dry run

Copy only the safe fields that should change into the matching manifest. Pull requests automatically validate:

- provider and target
- allowed PATCH fields
- JSON shape
- secret-like fields
- webhook or other outbound URLs
- unresolved redaction placeholders
- config-sync unit tests

After the pull request is merged, open **Actions → Deploy Make or ElevenLabs config**. Select the exact manifest and matching target, and leave **dry run** enabled. The dry run reports the provider, target, resource availability, and payload field names without making a provider request.

## Apply and verify

For staging, rerun the deployment with dry run disabled. The job uses the `staging` GitHub environment. Verify the Make scenario or cloned ElevenLabs agent and run one fake-data phone test.

For production:

- the manifest must declare `target: production`
- the job uses the protected `production` GitHub environment
- a required reviewer must approve the environment
- `production_confirmation` must equal `DEPLOY`

Keep the repository's production environment protection enabled. A repository file cannot bypass that approval.

## Security rules

- Never commit Make or ElevenLabs API tokens.
- Never commit webhook URLs, authorization headers, private keys, or credentials.
- Never paste provider secrets into prompts, issues, pull requests, or logs.
- Exported artifacts expire after seven days and must be reviewed before use.
- The deploy workflow is manual and dry-run by default.
- Production changes require both environment approval and the confirmation word.
- Record each approved live change in the support-owned canonical Google Doc and in `docs/operations/jesse-live-systems-change-log.md`.

## Rollback

Keep the previous approved manifest commit. To roll back, check out the previous payload into a new reviewed pull request, run a staging dry run, verify it, and deploy it through the same protected workflow. If caller behavior or calendar mutation is wrong, disable the affected Make scenario or revert the ElevenLabs agent immediately through the provider console while the GitHub rollback is reviewed.
