from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ContentPack:
    id: str
    topic: str
    audience: str
    hook: str
    situation: str
    therapist_line: str
    resolution: str
    call_to_action: str
    format: str = "9:16 vertical, 15-30 seconds"
    status: str = "draft"
    human_review_required: bool = True


class SuccessBrandContentSystem:
    """Creates review-only content briefs; it does not publish or make clinical claims."""

    def create_pack(self, topic: str, audience: str = "adults") -> dict:
        clean_topic = " ".join(topic.split())
        clean_audience = " ".join(audience.split())
        if not clean_topic or len(clean_topic) > 120:
            raise ValueError("topic must contain 1-120 characters")
        pack = ContentPack(
            id=str(uuid.uuid4()),
            topic=clean_topic,
            audience=clean_audience or "adults",
            hook=f"What people often misunderstand about {clean_topic}",
            situation=f"Show a realistic everyday moment involving {clean_topic}; use subtle acting and no diagnostic claim.",
            therapist_line=f"Offer one brief, supportive observation about {clean_topic} using approved educational language.",
            resolution="Show one small, realistic next step and a hopeful emotional shift.",
            call_to_action="You do not have to carry it alone. Learn more at SuccessBrand.org.",
        )
        return asdict(pack)
