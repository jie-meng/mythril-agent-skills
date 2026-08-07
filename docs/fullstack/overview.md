# Fullstack Skills — Overview

**The fullstack family gives a multi-repo workspace a structured lifecycle:
explore → propose → apply → archive.** Each stage is a separate skill, and
the handoffs between them are plain, well-defined documents — not chat
history.

When you want the long version, [Concepts](concepts.md) has it. When you
want to know which skill to use, see [Workflows](workflows.md).

Here's the entire idea in one line: **agree on what to build in writing,
then build it across repos, then archive the record.**

---

## The lifecycle

```text
explore ──► propose ──► apply ──► archive
   │            │          │         │
   │        plan the   implement  move the
   │        work +     across     record
   │        spike if   repos      into
   │        needed     + PRs      archive
   │
   └── read-only understanding (optional but a great habit)
```

| Skill | What it does | Writes | Modifies code? |
|---|---|---|---|
| `fullstack-explore` | Answer questions, find implementations, understand cross-repo flows | Nothing (optionally a draft analysis if asked) | No |
| `fullstack-propose` | Turn an idea into a work directory with four documents; run a spike if there are unknowns | `changes/<type>/<name>/` | No (spike mode: temporary, uncommitted) |
| `fullstack-apply` | Implement the planned work repo by repo, review, open PRs | `progress.md`, `review.md` | Yes |
| `fullstack-archive` | Move a completed work directory into `changes/archive/` | archive move + optional changelog | No |
| `fullstack-docs-migration` | Reorganize a legacy docs repo into the new structure | MIGRATION-REPORT.md | No |

---

## The directory you build on

Everything centers on the **docs repo** created by `fullstack-init`:

```text
<docs-dir>/
├── changes/
│   ├── feat/<work-name>/            # active work (exists = in progress)
│   ├── refactor/<work-name>/
│   ├── fix/<work-name>/
│   └── archive/YYYY-MM-DD-<type>-<work-name>/   # completed
└── …                                   # your own knowledge dirs (untouched)
```

A work directory exists in `changes/` means it's active. It exists in
`changes/archive/` means it's done. **The directory location is the status
field** — no text field to keep in sync, one `mv` to archive.

---

## Why this is worth the small overhead

- **Decisions are written down before code exists.** A misunderstanding
  caught in a one-page plan costs nothing; caught after 400 lines costs
  a lot.
- **Spike results survive.** Validation, experiments, and verdicts live in
  the same work directory that gets implemented — no rewrite on handoff.
- **"Done" is a directory move.** Active vs archived is visually obvious;
  no digging through Status fields.
- **Six months later, the archive tells you why the system works the way
  it does** — and the next AI session can read it.

The honest tradeoff: for a truly trivial one-line fix, the four documents
may feel like ceremony. That's fine — the structure is designed so the
ceremony scales with the stakes, and `archive` gives you a place to
sweep small items when they're done.

---

## Where to go next

- New here? [Workflows](workflows.md) shows when to use each skill.
- Want the deep version of everything above? [Concepts](concepts.md).
- Curious how the family delegates to subagents? [Agent Orchestration](AGENT-ORCHESTRATION.md).
- Looking at the refactor that produced this? [REFACTOR-PLAN](REFACTOR-PLAN.md).
