# Content Cloud Storage

Status: pilot adapter implemented; live bucket provisioning remains manual and staging-only.

## Security contract

- The bucket must enforce uniform bucket-level access.
- Public access prevention must be enforced.
- The application service account receives object creation access only where practical.
- Every upload uses `if_generation_match=0` to prevent replacement of an existing object.
- Archive objects are JSON drafts and cannot publish content.
- Default retention metadata is 90 days; the bucket lifecycle policy is the enforcement layer.

## Object layout

`content/{campaign}/{YYYY}/{MM}/{DD}/{timestamp}-{random-id}/batch.json`

Each archive contains its schema version, campaign, timestamp, retention period, publishing-disabled marker, and complete content batch.

## Required staging configuration

- `CONTENT_STORAGE_MODE=gcs`
- `CONTENT_ASSET_BUCKET=<private staging bucket>`
- `GOOGLE_CLOUD_PROJECT=success-brand-staging`

Do not reuse a production or public website bucket.
