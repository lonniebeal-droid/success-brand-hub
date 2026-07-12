# Agent Handoff Rules

Status: Planned. This document defines intended handoff rules between agents once departments are activated. No handoff described here is currently automated or live.

## Purpose
Define what information moves between agents, in what form, and with what safeguards, for each defined handoff pair.

## Jesse to Sales
- Trigger: A qualified lead or booked appointment is identified by Jesse
- Required Data: Contact intent, appointment context, and relevant conversation summary (not full transcripts unless necessary)
- Required Redaction: Remove any payment details, government ID numbers, or health information not relevant to the appointment
- Receiving Agent: Sales
- Expected Response Time: Within one business day (target, pending activation)
- Escalation: If Sales cannot make contact after defined attempts, escalate to Michelle
- Completion Criteria: Lead is logged in the pipeline with next action assigned

## Jesse to Michelle
- Trigger: Jesse identifies a cross-department issue, platform risk, or item outside its own authority
- Required Data: Summary of the issue and any relevant context
- Required Redaction: Remove unrelated personal data not needed to understand the issue
- Receiving Agent: Michelle
- Expected Response Time: Same business day for urgent items (target, pending activation)
- Escalation: If unresolved, Michelle escalates to Ju
- Completion Criteria: Michelle acknowledges receipt and assigns an owner or resolution

## Sales to Content
- Trigger: Sales identifies a need for new or updated marketing/sales material
- Required Data: Use case, audience, format, and deadline
- Required Redaction: Remove specific customer identifying details unless required for personalization and approved
- Receiving Agent: Content
- Expected Response Time: Per agreed content SOP turnaround (target TBD)
- Escalation: If deadline is at risk, escalate to Michelle
- Completion Criteria: Content agent confirms the request is logged in tasks.md

## Content to Michelle
- Trigger: Completed content is ready for final publishing coordination, or a blocker needs resolution
- Required Data: Final draft, brand review status, and target channel
- Required Redaction: None beyond standard confidentiality of unpublished material
- Receiving Agent: Michelle
- Expected Response Time: Within the content's scheduled publish window (target TBD)
- Escalation: If Michelle is unavailable and the deadline is imminent, escalate to Ju
- Completion Criteria: Michelle confirms publishing coordination or returns the item for revision

## Research to Content
- Trigger: A research brief relevant to a content request is completed
- Required Data: Research brief with citations and confidence level
- Required Redaction: Remove any sensitive source information not needed for the brief's conclusions
- Receiving Agent: Content
- Expected Response Time: Per the requesting content piece's deadline (target TBD)
- Escalation: If findings are inconclusive and the deadline is at risk, escalate to Michelle
- Completion Criteria: Content confirms the brief was received and incorporated or intentionally not used

## Research to Sales
- Trigger: A research brief relevant to a lead or market segment is completed
- Required Data: Research brief with citations and relevance notes
- Required Redaction: Remove any competitor or third-party data that cannot be shared externally
- Receiving Agent: Sales
- Expected Response Time: Per the requesting need's deadline (target TBD)
- Escalation: If findings conflict with existing sales assumptions, escalate to Michelle
- Completion Criteria: Sales confirms the brief was reviewed

## Finance to Ju
- Trigger: A scheduled financial report is completed, or a material anomaly is flagged
- Required Data: Financial summary report reviewed by Michelle
- Required Redaction: Remove any banking, card, or account credential data; only summary figures are shared
- Receiving Agent: Ju
- Expected Response Time: Per the defined reporting cadence (target TBD)
- Escalation: Material anomalies escalate immediately, outside the normal cadence
- Completion Criteria: Ju acknowledges receipt and forwards to CEO/human leadership if required

## Workspace to Michelle
- Trigger: A proposed structural change, cleanup action, or unresolved organization issue
- Required Data: Proposal summary with current state, proposed state, and rationale
- Required Redaction: None beyond standard confidentiality
- Receiving Agent: Michelle
- Expected Response Time: Per the workspace-sop.md cadence (target TBD)
- Escalation: Any proposed deletion requires explicit human approval before action
- Completion Criteria: Michelle approves, rejects, or requests changes to the proposal

## Mental Health to SuccessBrand
- Trigger: A wellbeing-related content or messaging review is needed
- Required Data: Draft content and specific concern flagged
- Required Redaction: Remove any individual's personal wellbeing information; keep feedback general
- Receiving Agent: SuccessBrand
- Expected Response Time: Before the content's scheduled publish date (target TBD)
- Escalation: Unresolved safety concerns escalate directly to a human, not just to SuccessBrand
- Completion Criteria: SuccessBrand confirms the content was revised or approved with the flagged concern addressed

## SuccessBrand to Ju
- Trigger: A brand-level risk, conflict, or reputational concern cannot be resolved with Michelle
- Required Data: Summary of the conflict, options considered, and recommendation
- Required Redaction: None beyond standard confidentiality
- Receiving Agent: Ju
- Expected Response Time: Within one business day for non-urgent items (target TBD)
- Escalation: Reputational or legal risk escalates immediately to Ju and the CEO
- Completion Criteria: Ju provides a decision or forwards to the CEO

## Michelle to Ju
- Trigger: Any escalation Michelle cannot resolve within her authority, or scheduled status reporting
- Required Data: Consolidated department status and escalation summaries
- Required Redaction: Summarized, not raw, department data unless Ju requests detail
- Receiving Agent: Ju
- Expected Response Time: Per the executive-governance-sop.md cadence (target TBD)
- Escalation: High-risk items are flagged for immediate attention rather than waiting for the normal cadence
- Completion Criteria: Ju acknowledges and either resolves or forwards to the CEO

## Ju to CEO
- Trigger: Any escalation Ju cannot resolve, or scheduled strategic reporting
- Required Data: Summary of cross-department status, risks, and recommended decisions
- Required Redaction: Summarized, not raw, data unless the CEO requests detail
- Receiving Agent: CEO
- Expected Response Time: Per the executive-governance-sop.md cadence (target TBD)
- Escalation: Anything involving finances, legal standing, or irreversible action is flagged for human leadership regardless of cadence
- Completion Criteria: CEO provides a decision or forwards to human leadership
