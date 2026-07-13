from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Protocol

SENSITIVE_TERMS = {"anxiety", "depression", "mental health", "self-harm", "stress", "suicide", "trauma", "wellbeing"}


@dataclass(frozen=True)
class ContentRequest:
    topic: str
    audience: str = "people building a better future"
    goal: str = "educate and encourage"
    platform: str = "short-form video"
    quantity: int = 1

    def validate(self) -> None:
        if not self.topic.strip():
            raise ValueError("topic is required")
        if not 1 <= self.quantity <= 30:
            raise ValueError("quantity must be between 1 and 30")


@dataclass(frozen=True)
class ContentDraft:
    title: str
    hook: str
    script: str
    caption: str
    hashtags: list[str]
    image_prompts: list[str]
    flow_prompt: str
    veo_prompts: list[str]
    approval_status: str = "draft"
    requires_human_approval: bool = True
    requires_mental_health_review: bool = False


@dataclass(frozen=True)
class ContentBatch:
    topic: str
    mode: str
    model: str
    drafts: list[ContentDraft]

    def to_dict(self) -> dict:
        return asdict(self)


class DraftGenerator(Protocol):
    mode: str
    model: str

    def generate(self, request: ContentRequest) -> list[dict]: ...


class MockDraftGenerator:
    mode = "mock"
    model = "deterministic-template-v1"

    def generate(self, request: ContentRequest) -> list[dict]:
        topic = request.topic.strip()
        slug = re.sub(r"[^a-z0-9]+", "", topic.casefold()) or "success"
        drafts = []
        for number in range(1, request.quantity + 1):
            drafts.append({
                "title": f"{topic}: one step forward {number}",
                "hook": f"What if one small shift could change how you approach {topic}?",
                "script": f"Start with one honest look at {topic}. Choose one practical action you can take today, make it small enough to finish, and notice what improves. Progress grows when the next step is clear. Save this and choose your step.",
                "caption": f"A practical next step for {topic}. Progress can start small.",
                "hashtags": ["#SuccessBrand", f"#{slug}", "#KeepGoing"],
                "image_prompts": [
                    f"Hopeful editorial photograph representing {topic}, warm natural light, diverse adults, no text, vertical 9:16",
                    f"Close-up of a simple completed action connected to {topic}, optimistic and authentic, no text, vertical 9:16",
                ],
                "flow_prompt": f"Create a 20-second vertical 9:16 sequence about {topic}: tension, one practical action, visible progress, hopeful finish; keep captions in the safe zone",
                "veo_prompts": [
                    f"Vertical 9:16 cinematic shot, person pausing to reflect on {topic}, natural movement, warm light, no logos or text, 5 seconds",
                    f"Vertical 9:16 close-up of one practical action for {topic}, realistic hands, smooth camera motion, no text, 5 seconds",
                    f"Vertical 9:16 hopeful final shot showing forward momentum around {topic}, inclusive casting, no text, 5 seconds",
                ],
            })
        return drafts


class VertexDraftGenerator:
    mode = "vertex"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("CONTENT_VERTEX_MODEL", "gemini-2.5-flash")

    def generate(self, request: ContentRequest) -> list[dict]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("vertex mode requires the google-genai package") from exc
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for vertex mode")
        schema = {
            "type": "ARRAY",
            "items": {"type": "OBJECT", "required": ["title", "hook", "script", "caption", "hashtags", "image_prompts", "flow_prompt", "veo_prompts"], "properties": {
                "title": {"type": "STRING"}, "hook": {"type": "STRING"}, "script": {"type": "STRING"},
                "caption": {"type": "STRING"}, "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
                "image_prompts": {"type": "ARRAY", "items": {"type": "STRING"}}, "flow_prompt": {"type": "STRING"},
                "veo_prompts": {"type": "ARRAY", "items": {"type": "STRING"}},
            }},
        }
        prompt = (
            "Create draft-only SuccessBrand content. Be warm, direct, practical, inclusive, and avoid unsupported claims. "
            "Never claim diagnosis, treatment, guaranteed results, or professional advice. Do not depict named real people. "
            "Return exactly the requested number of distinct drafts. Each script should fit 20-40 seconds and include a hook, "
            "one clear idea, and a non-coercive call to action. Image and video prompts must specify vertical 9:16 and no text.\n\n"
            f"Topic: {request.topic}\nAudience: {request.audience}\nGoal: {request.goal}\nPlatform: {request.platform}\nDraft count: {request.quantity}"
        )
        client = genai.Client(vertexai=True, project=project, location=location)
        response = client.models.generate_content(model=self.model, contents=prompt, config=types.GenerateContentConfig(
            temperature=0.5, response_mime_type="application/json", response_schema=schema,
        ))
        return json.loads(response.text)


class ContentPipeline:
    def __init__(self, generator: DraftGenerator | None = None) -> None:
        mode = os.getenv("CONTENT_GENERATION_MODE", "mock").casefold()
        self.generator = generator or (VertexDraftGenerator() if mode == "vertex" else MockDraftGenerator())

    def run(self, request: ContentRequest) -> ContentBatch:
        request.validate()
        sensitive = any(term in request.topic.casefold() for term in SENSITIVE_TERMS)
        raw_drafts = self.generator.generate(request)
        if len(raw_drafts) != request.quantity:
            raise RuntimeError("generator returned an unexpected number of drafts")
        drafts = [ContentDraft(**draft, requires_mental_health_review=sensitive) for draft in raw_drafts]
        return ContentBatch(request.topic, self.generator.mode, self.generator.model, drafts)
