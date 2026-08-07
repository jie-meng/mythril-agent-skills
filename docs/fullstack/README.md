# Fullstack Skills — Documentation

Documentation home for the **fullstack skill family**: `fullstack-init`,
`fullstack-explore`, `fullstack-propose`, `fullstack-apply`,
`fullstack-archive`, and `fullstack-docs-migration`.

The fullstack family gives AI coding assistants a structured workflow for
multi-repo development: initialize a workspace, explore the codebase,
propose a plan, apply it across repos, and archive completed work.

---

## If you read nothing else, read these two pages

1. [Overview](overview.md) — the whole mental model on one screen: what
   `explore → propose → apply → archive` means and why the lifecycle exists.
2. [Workflows](workflows.md) — which skill to reach for in which situation,
   and how they hand off to each other.

---

## Pick your path

**I'm new to the fullstack family.** Start with [Overview](overview.md),
then [Workflows](workflows.md).

**I just set up a workspace and want to start working.** Run
`fullstack-init` (see the repo README), then use [Propose](workflows.md#propose)
to plan your first work item.

**I want to understand an existing codebase.** Use `fullstack-explore` —
read-only exploration across all repos. See [Workflows](workflows.md#explore).

**I have an idea but it's not fully thought through.** Use
`fullstack-propose` — it plans the work, and can run a spike (deep mode)
to validate unknowns first.

**I'm ready to build.** Use `fullstack-apply` — it implements a planned
work item across repos, reviews it, and opens PRs.

**A work item is done.** Use `fullstack-archive` to move it into the
archive. See [Concepts](concepts.md#archive).

**I have an existing docs repo with the old structure.** Use
`fullstack-docs-migration` to reorganize it into the new layout.

**I want to understand the deep design.** [Concepts](concepts.md) explains
the work directory structure, the four documents, Success Criteria, and
the archive lifecycle.

---

## The whole map

| Doc | What it gives you |
|---|---|
| [Overview](overview.md) | One-screen mental model of the lifecycle |
| [Workflows](workflows.md) | When to use which skill, and how they connect |
| [Concepts](concepts.md) | Deep design: directories, documents, lifecycle, naming |
| [REFACTOR-PLAN](REFACTOR-PLAN.md) | The refactor plan that produced this structure (transitional) |
| [AGENT-ORCHESTRATION](AGENT-ORCHESTRATION.md) | How the family delegates to subagents (planner/developer/reviewer/debugger) |

---

## The thirty-second version

```text
1. Init        fullstack-init            → creates workspace + docs repo
2. Explore     fullstack-explore         → understand code, find answers  (optional)
3. Propose     fullstack-propose         → plan a feat/fix/refactor        (optional spike)
4. Apply       fullstack-apply           → implement across repos + PRs
5. Archive     fullstack-archive         → move completed work into archive
6. Migrate     fullstack-docs-migration  → reorganize a legacy docs repo   (one-time)
```
