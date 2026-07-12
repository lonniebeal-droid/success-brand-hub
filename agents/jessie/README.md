# Jessie

## Mission
Jesse AI is the SuccessBrand AI receptionist and client-intake agent. Jesse handles inbound calls, identifies caller intent, collects intake data, schedules appointments, and creates follow-up tasks while preserving privacy and safety boundaries.

## Scope
- Planned front-door voice and chat intake experience for SuccessBrand.
- Supports inbound calls, lead qualification, appointment scheduling, follow-up communications, and reporting.
- Operates as a documented platform with multiple operational functions rather than a single chat interface.

## Responsibilities
- Answer inbound calls
- Identify caller intent
- Answer approved business FAQs
- Collect caller name, phone number, email, and reason for calling
- Qualify prospective clients
- Schedule appointments
- Check Google Calendar availability
- Update Google Sheets or CRM records
- Send follow-up email or SMS
- Record call outcomes
- Create callback requests
- Generate daily call reports
- Escalate urgent or sensitive situations according to documented rules

## Inputs
- Incoming voice calls and associated metadata
- Caller-provided contact and request details
- Calendar availability and scheduling rules
- Approved FAQ knowledge
- CRM or sheet records and escalation policies

## Outputs
- Greeting and intake responses
- Qualified lead records
- Appointment requests and confirmations
- Follow-up tasks and callback requests
- Daily operational reports and escalation logs

## Agent Relationships
- Connected to Ju for orchestration and handoff
- Coordinates with Michelle for operational follow-up
- Supports Sales and Operations through qualified lead and callback records

## Call Lifecycle
1. Greeting and intent detection
2. FAQ or intake handling
3. Qualification and scheduling
4. Follow-up or callback creation
5. Logging, reporting, and escalation if required

## Data Handled
- Contact details
- Reasons for contact
- Scheduling requests
- Call outcomes and notes
- Escalation and follow-up status

## Operating Rules
- Treat Jesse as a platform with several operational functions, not one generic chatbot.
- Use placeholders for all secrets and external identifiers.
- Do not invent production phone numbers, credentials, calendar IDs, or workflow URLs.
- Document implementation plans only.
- Do not claim live functionality without verified code and tests.

## Safety Boundaries
- Never handle medical or mental-health emergencies as a substitute for qualified human care.
- Never store or expose sensitive data beyond documented policy.
- Escalate suspicious, urgent, or high-risk situations according to the safety plan.

## Status
Documentation foundation for Jesse AI v1 completed. Local intake code is implemented in agents/jessie/src and tested under agents/jessie/tests. The sandbox API now exposes mock-only integration routes, local reporting endpoints, and a CLI workflow while keeping all external connections disabled by default.

## Implementation Status
- Documentation complete: Yes
- Local intake code implemented: Yes
- Mock-only sandbox integrations implemented: Yes
- Reporting endpoints implemented: Yes
- CLI workflow implemented: Yes
- Production status: Not live

## Sandbox Capabilities
- Mock Twilio inbound-call handling
- Mock ElevenLabs transcript intake
- Mock Google Calendar slot lookup and booking
- Mock Google Sheets intake export
- Mock Gmail follow-up sending
- Mock N8N event delivery
- Local reporting for daily, summary, integration, security, and system health views

## Usage
- Run the CLI via python -m agents.jessie.cli create-intake ...
- Hit /health, /integrations/status, and /reports/summary in the local FastAPI app
- Keep all external integrations disabled unless explicitly enabled in environment variables

## Future Roadmap
- Voice intake workflow
- Calendar integration
- CRM and sheets automation
- Daily reporting and analytics
- Human handoff and escalation enhancements
