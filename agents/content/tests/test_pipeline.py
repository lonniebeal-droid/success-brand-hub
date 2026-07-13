import json
import os
import subprocess
import sys

import pytest

from agents.content.src.pipeline import ContentPipeline, ContentRequest, MockDraftGenerator


def test_mock_pipeline_builds_complete_draft_batch() -> None:
    batch = ContentPipeline(MockDraftGenerator()).run(ContentRequest("building confidence", quantity=2))
    assert batch.mode == "mock"
    assert len(batch.drafts) == 2
    assert all(draft.requires_human_approval and draft.approval_status == "draft" for draft in batch.drafts)
    assert all(draft.image_prompts and draft.veo_prompts for draft in batch.drafts)


def test_sensitive_topic_requires_mental_health_review() -> None:
    assert ContentPipeline(MockDraftGenerator()).run(ContentRequest("handling stress")).drafts[0].requires_mental_health_review


@pytest.mark.parametrize("quantity", [0, 31])
def test_quantity_is_bounded(quantity: int) -> None:
    with pytest.raises(ValueError):
        ContentPipeline(MockDraftGenerator()).run(ContentRequest("momentum", quantity=quantity))


def test_cli_emits_json_without_external_calls() -> None:
    env = dict(os.environ, CONTENT_GENERATION_MODE="mock")
    result = subprocess.run([sys.executable, "-m", "agents.content.cli", "small business growth"], check=True, capture_output=True, text=True, env=env)
    payload = json.loads(result.stdout)
    assert payload["batch"]["mode"] == "mock"
    assert payload["batch"]["drafts"][0]["approval_status"] == "draft"
    assert payload["archive"] is None
