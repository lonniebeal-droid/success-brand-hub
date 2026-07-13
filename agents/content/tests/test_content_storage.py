import json
from pathlib import Path

from agents.content.src.pipeline import ContentPipeline, ContentRequest, MockDraftGenerator
from agents.content.src.storage import LocalContentArchive, _slug


def test_local_archive_is_private_versioned_json(tmp_path: Path) -> None:
    batch = ContentPipeline(MockDraftGenerator()).run(ContentRequest("building confidence"))
    result = LocalContentArchive(tmp_path).save(batch, "Summer Growth 2026")
    target = Path(result.uri)
    payload = json.loads(target.read_text())
    assert result.public is False
    assert result.object_name.startswith("content/summer-growth-2026/")
    assert target.stat().st_mode & 0o777 == 0o600
    assert payload["publishing_enabled"] is False
    assert payload["content"]["drafts"][0]["approval_status"] == "draft"
    assert payload["retention_days"] == 90


def test_campaign_slug_cannot_escape_archive_prefix() -> None:
    assert _slug("../../My Campaign") == "my-campaign"
