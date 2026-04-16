# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

**Isolation rule:** You are not the implementer and must review with an independent, adversarial posture.

This review must be performed by a newly dispatched reviewer subagent for this review pass. If you were previously used as the implementer or as an earlier reviewer session for this same pass, stop and report isolation failure.

```
Task tool (superpowers:code-reviewer):
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  BASE_SHA: [commit before task]
  HEAD_SHA: [current commit]
  DESCRIPTION: [task summary]
```

Before issuing the actual review, confirm:
- You are not the implementer for this task
- You are a fresh reviewer subagent for this pass
- Owner was told that code quality review was being dispatched

**In addition to standard code quality concerns, the reviewer should check:**
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files? (Don't flag pre-existing file sizes — focus on what this change contributed.)
- Did the implementer quietly skip risky areas that the task required?
- Is there evidence that tests exist but do not actually verify the intended behavior?

**Code reviewer returns:** Isolation Check (PASS/FAIL), Strengths, Issues (Critical/Important/Minor with file:line references), Assessment, Approval (PASS/FAIL)
