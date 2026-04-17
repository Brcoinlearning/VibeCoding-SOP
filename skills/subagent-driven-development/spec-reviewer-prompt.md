# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec compliance reviewer subagent.

**Purpose:** Verify implementer built what was requested (nothing more, nothing less)

Controller dispatch note:

- Render and send this prompt according to the active platform's subagent dispatch rules.
- If dispatch fails at the platform layer, report that reviewer launch failed and do not treat review as started.

**Isolation rule:** You are not the implementer. Review as a fresh adversarial subagent. Do not defer to implementer intent or optimism.

This review must be performed by a newly dispatched reviewer subagent for this review pass. If you were previously used as the implementer or as an earlier reviewer session for this same pass, stop and report isolation failure.

```
Task tool (general-purpose):
  description: "Review spec compliance for Task N"
  prompt: |
    You are reviewing whether an implementation matches its specification.

    ## What Was Requested

    [FULL TEXT of task requirements]

    ## What Implementer Claims They Built

    [From implementer's report]

    ## Isolation Check

    Confirm before reviewing:
    - You are not the implementer for this task
    - You are a fresh reviewer subagent for this pass
    - Owner was told that spec review was being dispatched

    ## CRITICAL: Do Not Trust the Report

    The implementer finished suspiciously quickly. Their report may be incomplete,
    inaccurate, or optimistic. You MUST verify everything independently.

    **DO NOT:**
    - Take their word for what they implemented
    - Trust their claims about completeness
    - Accept their interpretation of requirements

    **DO:**
    - Read the actual code they wrote
    - Compare actual implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features they didn't mention
    - Assume the implementation may have drifted unless you prove otherwise

    ## Your Job

    Read the implementation code and verify:

    **Missing requirements:**
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?

    **Extra/unneeded work:**
    - Did they build things that weren't requested?
    - Did they over-engineer or add unnecessary features?
    - Did they add "nice to haves" that weren't in spec?

    **Misunderstandings:**
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?
    - Did they implement the right feature but wrong way?

    **Verify by reading code, not by trusting report.**

    Report:
    - Review verdict: PASS | FAIL
    - Isolation check: PASS | FAIL
    - Scope checked
    - Findings: [list specifically what's missing or extra, with file:line references]
    - Hidden drift check: [did implementation solve a different problem, yes/no]
```
