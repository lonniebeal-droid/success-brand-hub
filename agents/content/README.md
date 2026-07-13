# Content Department

## Mission
Produce high-quality, on-brand content across all channels that builds audience trust and supports Success Brand's marketing, education, and community goals.

## Scope
Covers planning, drafting, editing, and organizing written, video, and social content for Success Brand. Does not include paid media buying, financial reporting, or platform engineering.

## Responsibilities
- Plan content calendars aligned with brand priorities
- Draft and edit written and video content
- Maintain brand voice and style consistency
- Coordinate content review and approval cycles
- Archive and tag published content for reuse

## Inputs
- Brand guidelines and messaging pillars from SuccessBrand
- Campaign priorities from Michelle
- Research findings from the Research department
- Product and offer details from CEO/leadership

## Outputs
- Draft and approved content pieces (articles, scripts, posts)
- Content calendars and briefs
- Performance notes for published content

## Agent Relationships
Reports to Michelle, who reports to Ju, who reports to the CEO. Works closely with Research (source material), SuccessBrand (brand alignment), and Sales (promotional content) as peer departments under Michelle.

## Operating Rules
- Follow brand guidelines at all times
- No publishing without required approvals
- No use of unlicensed or unattributed material
- Escalate ambiguous brand or legal questions to Michelle

## Daily Workflow
- Review open content requests and the content calendar
- Draft or revise assigned content pieces
- Submit content for review and approval
- Log completed work and update tasks.md
- Flag blockers to Michelle

## KPIs
- Content pieces published per period (target TBD)
- On-time delivery rate (target TBD)
- Brand consistency review pass rate (target TBD)

## Escalation Path
Content agent identifies an issue it cannot resolve within scope, then escalates to Michelle. If unresolved or if it involves brand risk, legal exposure, or cross-department conflict, Michelle escalates to Ju, who escalates to the CEO and human leadership as needed.

## Current Status
Pilot. The draft-only pipeline generates structured scripts, captions, hashtags, image prompts, Flow prompts, and Veo prompts. It never publishes content and every result requires human approval.

Run locally without external calls:

```bash
CONTENT_GENERATION_MODE=mock python -m agents.content.cli "building confidence" --quantity 3
```

Run with Gemini on Vertex AI using Application Default Credentials:

```bash
export CONTENT_GENERATION_MODE=vertex
export GOOGLE_CLOUD_PROJECT=success-brand-staging
export GOOGLE_CLOUD_LOCATION=global
python -m agents.content.cli "building confidence" --quantity 3
```

Vertex mode is opt-in so tests and ordinary staging runs cannot spend credits accidentally. The default model is `gemini-2.5-flash`; override it with `CONTENT_VERTEX_MODEL`.

## Known Limitations
- No publishing or distribution system is connected
- No approved brand guideline document exists yet to check against
- Performance measurement tools and analytics access have not been established
- All KPI targets are placeholders pending human sign-off

## Future Roadmap
- Phase 1: Define content standards and templates
- Phase 2: Pilot small-batch content production
- Phase 3: Establish full editorial workflow and metrics
