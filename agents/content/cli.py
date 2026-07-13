from __future__ import annotations

import argparse
import json

from agents.content.src.pipeline import ContentPipeline, ContentRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate draft-only SuccessBrand content packages")
    parser.add_argument("topic")
    parser.add_argument("--audience", default="people building a better future")
    parser.add_argument("--goal", default="educate and encourage")
    parser.add_argument("--platform", default="short-form video")
    parser.add_argument("--quantity", type=int, default=1)
    args = parser.parse_args()
    batch = ContentPipeline().run(ContentRequest(args.topic, args.audience, args.goal, args.platform, args.quantity))
    print(json.dumps(batch.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
