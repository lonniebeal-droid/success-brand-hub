from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from agents.content.src.pipeline import ContentBatch


@dataclass(frozen=True)
class ArchiveResult:
    mode: str
    object_name: str
    uri: str
    public: bool = False


class ContentArchive(Protocol):
    mode: str

    def save(self, batch: ContentBatch, campaign: str) -> ArchiveResult: ...


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:80] or "campaign"


def _object_name(campaign: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).strftime("%Y/%m/%d/%Y%m%dT%H%M%SZ")
    return f"content/{_slug(campaign)}/{timestamp}-{uuid4().hex[:12]}/batch.json"


def _payload(batch: ContentBatch, campaign: str, object_name: str, retention_days: int) -> str:
    document = {
        "schema_version": "successbrand_content_archive_v1",
        "campaign": campaign.strip(),
        "object_name": object_name,
        "archived_at": datetime.now(UTC).isoformat(),
        "retention_days": retention_days,
        "publishing_enabled": False,
        "content": batch.to_dict(),
    }
    return json.dumps(document, indent=2, sort_keys=True)


class LocalContentArchive:
    mode = "local"

    def __init__(self, root: str | Path | None = None, retention_days: int = 90) -> None:
        self.root = Path(root or os.getenv("CONTENT_ARCHIVE_LOCAL_ROOT", "/tmp/successbrand-content"))
        self.retention_days = retention_days

    def save(self, batch: ContentBatch, campaign: str) -> ArchiveResult:
        object_name = _object_name(campaign)
        target = self.root / object_name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_text(_payload(batch, campaign, object_name, self.retention_days), encoding="utf-8")
        target.chmod(0o600)
        return ArchiveResult(self.mode, object_name, str(target), public=False)


class GCSContentArchive:
    mode = "gcs"

    def __init__(self, bucket_name: str | None = None, retention_days: int = 90) -> None:
        self.bucket_name = bucket_name or os.getenv("CONTENT_ASSET_BUCKET", "")
        self.retention_days = retention_days
        if not self.bucket_name:
            raise RuntimeError("CONTENT_ASSET_BUCKET is required for GCS storage")

    def save(self, batch: ContentBatch, campaign: str) -> ArchiveResult:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("GCS storage requires the google-cloud-storage package") from exc
        client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)
        bucket = client.get_bucket(self.bucket_name)
        if not bucket.iam_configuration.uniform_bucket_level_access_enabled:
            raise RuntimeError("content bucket must use uniform bucket-level access")
        if bucket.iam_configuration.public_access_prevention != "enforced":
            raise RuntimeError("content bucket must enforce public access prevention")
        object_name = _object_name(campaign)
        blob = bucket.blob(object_name)
        blob.metadata = {
            "approval_status": "draft",
            "retention_days": str(self.retention_days),
            "publishing_enabled": "false",
            "schema_version": "successbrand_content_archive_v1",
        }
        blob.upload_from_string(
            _payload(batch, campaign, object_name, self.retention_days),
            content_type="application/json",
            if_generation_match=0,
            checksum="auto",
            timeout=30,
        )
        return ArchiveResult(self.mode, object_name, f"gs://{self.bucket_name}/{object_name}", public=False)


def configured_archive() -> ContentArchive:
    mode = os.getenv("CONTENT_STORAGE_MODE", "local").casefold()
    if mode == "gcs":
        return GCSContentArchive()
    if mode == "local":
        return LocalContentArchive()
    raise RuntimeError("CONTENT_STORAGE_MODE must be local or gcs")
