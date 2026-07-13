# Jesse Live Systems Change Log

> Engineering mirror of the canonical Google Doc:  
> [SuccessBrand Jesse Change Log and Live Systems Status](https://docs.google.com/document/d/139NT_r0VKWqAbE6pEKCbaAR7oeiUXTi4jbM0kxDbn78/edit)

## Authority and scope

The Google Doc above is the canonical source of truth for Jesse live-system changes across Codex, ChatGPT, Gemini, Claude, Make, ElevenLabs, Google Workspace, and GitHub. It is owned by `support@successbrand.org`.

This repository file is the engineering and configuration audit mirror. Every change to live prompts, procedures, tools, workflows, calendar connections, phone routing, deployments, or integrations must be recorded in both places.

Each entry must include:

- date and time
- system and environment
- person or assistant making the change
- reason and intended outcome
- exact prompt, procedure, tool, workflow, calendar, file, or setting affected
- verification evidence
- rollback or disable step
- controlled test result
- unresolved follow-up

Do not create a competing master document.

## July 13, 2026 — short-call and immediate hang-up repair

### Evidence

Live ElevenLabs conversation `conv_2801kxej5kg4ec5rjz1bjj5sj3ff` lasted 2 minutes 59 seconds. Jesse repeated the caller's contact and appointment details, continued after the caller said goodbye, and required the caller to end the call remotely.

### Root cause

Conflicting prompt and procedure instructions required confirmation and recap even after caller end intent.

### Published repair

- Caller end intent now overrides routine procedures.
- Jesse may say no more than “Thank you. Goodbye.” before invoking **End conversation**.
- Repeated phone, email, old-time, and new-time readbacks are prohibited.
- Cancellation and rescheduling calls must collect only the minimum required information.
- One short outcome sentence is allowed; no final confirmation loop.
- Updated live procedures:
  - Appointment Confirmation and Notification
  - Intake Notification and Call Completion
  - Clinical Intake and Appointment Booking

### Verification

ElevenLabs reported **Main updated**, and the Publish button became disabled.

### Remaining test

Place one controlled fake-data call. After the tool result, say “Bye” and verify that Jesse gives no recap and ends immediately.

## July 13, 2026 — calendar reschedule failure

### Evidence

A controlled caller requested moving a July 14 appointment from 8:30 AM to 1:45 PM. ElevenLabs reported the Make webhook tools as successful, but no direct Google Calendar tool ran.

Direct calendar inspection found no appointment at 1:45 PM. The only relevant event was **SuccessBrand Sandbox Appointment Test**, 11:00–11:30 AM, created by the staging service account on the SuccessBrand Sandbox Calendar.

### Root cause

The `cancel_appointment` and `reschedule_appointment` tools are Make webhooks. HTTP acceptance proved only that Make received the request; it did not prove that Google Calendar was changed. The tool descriptions incorrectly allowed Jesse to announce completion after webhook success.

### Published safeguard

- Webhook acceptance is treated as **request received only**.
- Jesse must use `google_calendar_list_events` before cancellation or rescheduling.
- Cancellation may be claimed only after the original event is verified absent.
- Rescheduling may be claimed only after:
  1. the original event is verified absent,
  2. the new slot is available, and
  3. `google_calendar_create_event` succeeds.
- If exact verification fails, Jesse routes the request to office follow-up.

## July 13, 2026 — Make calendar automation safety shutdown

### Evidence

- **Jesse Cancellation Handler**
  - Make scenario: `5546279`
  - run: `41c733381d7149c2935e01f90aa595a0`
  - executed nine Google Calendar **Delete an Event** operations
  - run showed both **No matching event** and **Event found** paths
- **Jesse Reschedule Handler**
  - Make scenario: `5572627`
  - run: `661e4c0317e4488ca138f54d6d6fa409`
  - executed four Google Calendar **Update an Event** operations
  - showed the same unsafe multi-bundle routing pattern
- Historical failures referenced the invalid calendar endpoint:
  `/calendar/v3/calendars/support%40successbrand.org/events/`
  and returned Google 404 responses.

### Safety action

Both Make scenarios were switched to **Inactive**:

- Jesse Cancellation Handler
- Jesse Reschedule Handler

They must remain inactive until exact-match filtering is repaired and a synthetic sandbox test proves that one request affects exactly one intended event.

### Required remediation before reactivation

- Inspect the Make search filters and bundle routing.
- Target the correct shared calendar and exact intended event.
- Prevent zero-match and multi-match branches from reaching delete/update modules.
- Test with one synthetic event.
- Confirm exactly one calendar mutation.
- Record the test in the canonical Google Doc and this GitHub mirror.
- Reactivate only after explicit review.

## Current safety status

| Component | Status |
|---|---|
| Jesse Main prompt | Published with short-call and calendar-verification guardrails |
| Direct Google Calendar tools | Attached |
| Make cancellation handler | Inactive |
| Make reschedule handler | Inactive |
| Automatic cancel/reschedule | Paused |
| Fresh end-to-end controlled verification | Pending |
| Production calendar success claim from webhook alone | Prohibited |

## Change-control rule

Before any live change:

1. Document the proposal and reason in the support-owned canonical Google Doc.
2. Identify dependencies, privacy risks, and rollback steps.
3. Make the smallest necessary change.
4. Publish only after review.
5. Run a controlled test with fake data.
6. Record evidence and unresolved follow-up in the Google Doc.
7. Mirror engineering/configuration details in this GitHub file or a linked repository document.
