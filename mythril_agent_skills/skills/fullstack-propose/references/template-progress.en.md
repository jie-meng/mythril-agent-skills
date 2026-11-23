## `progress.md`

`progress.md` is a **dated log**. Every meaningful change — kickoff,
per-repo completion, review-driven fixes, user feedback, follow-up
edits — is recorded as a `### <date>` section. Each entry **opens with a
bold result line** (`**Result**:` / `**结果**：`) — the decision-maker's
first line — and **closes with a process-notes tail**
(`（Process notes: …）` / `（过程记录：…）`) holding AI-workflow detail.
Git history is the authoritative record of code changes; this file is
the human-readable narrative that ties changes to decisions.

### English

```markdown
# Progress: <Work Name>

**Last updated**: <date>

**Branch**: <branch-name>

## Completed Steps

(none yet)

## In Progress

- [ ] <current step>

## Blocked

(none)

## Change Log

### <date> — Started

**Result**: <one or two plain sentences: what happened and where things stand now — the decision-maker's first line>
- Created work plan
- Identified affected repos: <list>
- Created branches in: <list>
（Process notes: <subagent runs, gate output, wording syncs — AI workflow detail>）

### <date> — <what happened>

**Result**: <one or two plain sentences: what happened and where things stand now>
- <what was done, why, and the result>
（Process notes: <AI workflow detail>）
```



### Successor back-link — `## Successors` table (optional)

The forward link is what always carries the chain forward: the
successor's `**Source**` / `**Predecessor**` points at the archived
predecessor and is written for every successor.

A reverse `## Successors` (English) / `## 后续工作` (Chinese) table can
**additionally** be appended to the predecessor's `progress.md` — but
only if the successor is already known while the predecessor is still
active, i.e. **before** it is archived. Because a successor is normally
planned only *after* archiving, this back-link is best-effort and often
absent. That is fine: archive is final and archived directories are
never edited; discovery relies on the `-vN` naming convention plus the
forward link instead.

---
