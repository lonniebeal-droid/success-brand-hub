from __future__ import annotations

import argparse
import json

from agents.content.src.pipeline import ContentPipeline, ContentRequest
from agents.content.src.storage import configured_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate draft-only SuccessBrand content packages")
    parser.add_argument("topic")
    parser.add_argument("--audience", default="people building a better future")
    parser.add_argument("--goal", default="educate and encourage")
    parser.add_argument("--platform", default="short-form video")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--archive", action="store_true", help="archive the generated batch")
    parser.add_argument("--campaign", help="campaign name used for the archive path")
    args = parser.parse_args()
    batch = ContentPipeline().run(ContentRequest(args.topic, args.audience, args.goal, args.platform, args.quantity))
    result = {"batch": batch.to_dict(), "archive": None}
    if args.archive:
        archive = configured_archive().save(batch, args.campaign or args.topic)
        result["archive"] = {
            "mode": archive.mode,
            "object_name": archive.object_name,
            "uri": archive.uri,
            "public": archive.public,
        }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
