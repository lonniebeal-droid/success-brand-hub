# Automation Department SOP

Status: Planned. This SOP describes the intended process for the Automation department once activated. No step below is currently automated or live.

## Purpose
Define a repeatable process for identifying, specifying, and proposing workflow automations.

## Trigger
A manual, repetitive, or error-prone process is reported by any department, or identified during a periodic review.

## Required Inputs
- Description of the current manual process
- Frequency and time cost of the process
- Systems or tools currently involved

## Step-by-Step Process
1. Log the candidate process in the automation backlog
2. Interview the requesting department to document the current steps
3. Identify risks, edge cases, and required approvals
4. Draft a workflow specification (trigger, steps, inputs, outputs, failure handling)
5. Submit the specification to Michelle for review
6. Route approved specifications to the engineering team for feasibility assessment
7. Track implementation status in tasks.md

## Quality Checks
- Specification includes failure handling and rollback considerations
- No proposal requires unreviewed changes to core/, src/, or deployment
- Risk level is explicitly stated

## Escalation Rules
- Any specification touching protected engineering areas: escalate to Michelle and Ju before any further action
- Unclear ownership of a process: escalate to Michelle

## Handoff Rules
- Approved specifications are handed off to Michelle, who coordinates with the engineering team maintaining core/ and src/
- The requesting department is notified of specification status at each stage

## Output Format
Workflow specification document with sections for trigger, inputs, steps, outputs, risk, and failure handling.

## Metrics
- Opportunities logged per period (target TBD)
- Specification turnaround time (target TBD)

## Failure Handling
If a specification cannot be completed due to missing information, the Automation agent logs the gap in tasks.md and requests clarification from the originating department before proceeding.
