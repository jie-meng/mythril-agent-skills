# Issue-sourced proposals

Read this when the work item plans work for an active issue under
`<docs-dir>/issues/` (an issue recorded by `fullstack-issue-create`).

## Reading the issue (Step 1)

Read the issue's README (symptom, evidence, analysis) — it is a
requirements source like a Jira ticket.

## Writing the documents (Step 4)

- **Requirements**: the issue's symptom and analysis (its `## 现象` /
  `## 分析` sections, or `## Symptom` / `## Analysis` in English issues)
  are quoted verbatim into `analysis.md` §Original Requirements /
  §需求原文, one `REQ<n>` id per ask — the same mechanism as
  user-provided requirements (Step 1, item 1 of `SKILL.md`).
- **Source**: `plan.md`'s **Source** / **来源** points at the issue's
  archive path (`issues/archive/<name>/…`) — the post-move path, never
  the pre-move active path; the active path stops resolving the moment
  the close below lands.

## Closing the issue (Step 5)

After the four documents are committed to the docs repo, invoke
`fullstack-issue-archive` with mode `proposed` and the new work-item
directory as the pointer. That skill moves the issue into
`issues/archive/`, appends the `## 闭环` / `## Closure` record
(`验证: n/a` / `Verification: n/a` — a `proposed` close tracks the
problem, it does not claim it is fixed), and commits the docs repo. Do
not move the directory or write the record yourself as well — a second
move would nest or collide. The other modes (`resolved`, `wontfix`,
`merged`) belong to the issue's own close flow, not to this one.

Only when `fullstack-issue-archive` is not installed, do its steps by
hand in its order — move first, then write, then commit both sides of
the move:

```bash
mkdir -p <docs-dir>/issues/archive
mv <docs-dir>/issues/<name> <docs-dir>/issues/archive/<name>
# append ## 闭环 / ## Closure: mode proposed, date, work-item path, verification n/a
cd <docs-dir> && git add issues/ && git commit -m "docs: close issue <name> (proposed)"
```
