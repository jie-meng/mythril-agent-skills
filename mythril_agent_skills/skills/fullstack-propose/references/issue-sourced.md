# Issue-sourced proposals

Read this when the work item plans work for an active issue under
`<docs-dir>/issues/` (an issue recorded by `fullstack-issue-create`).

## Reading the issue (Step 1)

Read the issue's README (symptom, evidence, analysis) — it is a
requirements source like a Jira ticket.

## Writing and closing (Step 5)


   - **Requirements**: the issue's symptom and analysis (its `## 现象` /
     `## 分析` sections, or `## Symptom` / `## Analysis` in English
     issues) are quoted verbatim into `analysis.md` §Original
     Requirements / §需求原文, one `REQ<n>` id per ask — the same
     mechanism as user-provided requirements (Step 1a).
   - **Source**: `plan.md`'s **Source** / **来源** points at the issue's
     archive path (`issues/archive/<name>/…`) — the post-move path, never
     the pre-move active path; the active path stops resolving the moment
     the close below lands.
   - **Close (after the four documents are committed to the docs
     repo)**: invoke `fullstack-issue-archive` (mode `proposed`) — the
     other three modes (`resolved`, `wontfix`, `merged`) belong to the
     issue's own close flow, not the propose flow. The mandatory order
     still applies — move first, then write:

     ```bash
     mv <docs-dir>/issues/<name> <docs-dir>/issues/archive/<name>
     ```

     Then append `## 闭环` (`## Closure` in English issues) to the
     issue's README — the mode, the date, the pointer to the work item
     directory this skill just created, and `验证: n/a` / `Verification:
     n/a` (a `proposed` close tracks the problem, it does not claim it is
     fixed). Then commit the docs repo
     in the same round — `git add issues/` (the parent directory) stages
     both sides of the move above (the new archive path and the old
     active path's deletion):

     ```bash
     cd <docs-dir>
     git add issues/
     git commit -m "docs: close issue <name> (proposed)"
     ```
