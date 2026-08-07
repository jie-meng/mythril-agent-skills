# Fullstack Skills — Concepts

This guide explains the core ideas behind the fullstack skill family and
how they fit together. For practical usage, see [Overview](overview.md) and
[Workflows](workflows.md).

---

## Philosophy

```text
directory-location-as-state — the path tells you the lifecycle stage
one work directory, one lifecycle — spike results survive into implementation
four documents, one causal chain — analysis → plan → progress → review
archive is a move, not a field — done means moved into archive/
decision records, not specs — documents capture why, not SHALL-contracts
```

Why these matter: text fields drift (we measured: a `Status` field was
filled in 7% of real work items and contradicted `progress.md` 38% of the
time). Directory moves cannot drift. One `mv` is the entire lifecycle
transition.

---

## The work directory

Every work item lives in its own directory under the docs repo's
`changes/` container, grouped by type:

```text
<docs-dir>/changes/feat/<work-name>/
├── analysis.md    # technical thinking — why and how (spike findings too)
├── plan.md        # requirements, repos, tasks, Success Criteria
├── progress.md    # what happened, when (dated log)
└── review.md      # review findings, Evidence table, verdict
```

**The four-file invariant**: all four documents are created by propose and
maintained through apply. `analysis.md` is the foundation — it captures
*why* decisions were made. The chain is causal:

```text
analysis.md ──► plan.md ──► progress.md ──► review.md
   (why)          (what)        (status)       (quality)
```

A change to an upstream document propagates to the downstream ones. A
review finding that changes architecture updates `analysis.md`, which
updates `plan.md`, which updates `progress.md`.

### The spike lives inside analysis.md

The old workflow had a separate `spike/` directory that was **rewritten**
into the implementation directory later — measured as 0 lines shared
between spike and implementation analysis across five real pairs. The new
model keeps spike results in the same file they will be implemented from:

1. `analysis.md` starts with `Objective / Hypothesis / Unknowns / Success Criteria`
2. experiments run, findings are appended
3. `Design Options / Target Architecture` are appended to the **same file**
4. the verdict lands in `plan.md`

One directory, one document, no rewrite.

### Success Criteria — the agreement before code

`plan.md` carries a `## Success Criteria` checklist. This is the contract
between what was planned and what "done" means. It is the single most
effective mechanism in the family — spikes that used it had a filled
Evidence table in 79% of cases.

`review.md` carries the matching **Evidence table**: each criterion is
checked against concrete evidence (test results, PR links, screenshots).

---

## The changes/ container

`changes/` is the only convention-managed directory in the docs repo.
Everything under it is lifecycle-controlled; everything outside it
(`docs/`, `changelog/`, your own knowledge dirs) is untouched by the
skills.

```text
changes/
├── feat/<work-name>/            # active
├── refactor/<work-name>/
├── fix/<work-name>/
└── archive/YYYY-MM-DD-<type>-<work-name>/   # completed
```

### Why a container

Before the container existed, `feat/`, `fix/`, `refactor/` sat at the top
level next to knowledge directories, and convention vs user content was
indistinguishable at a glance. A single `changes/` container makes the
line explicit: **inside `changes/` is lifecycle-controlled, outside is
yours.**

### Why the type stays in the path

`feat/`, `refactor/`, `fix/` remain separate because they carry real
semantic weight: the `analysis.md` template differs between a fix
(Debugger writes root-cause analysis) and a feat (Planner writes design
options). They are not cosmetic categories.

---

## Archive

### What archive means

Archiving a work item is **one directory move**:

```text
changes/feat/<work-name>/  →  changes/archive/YYYY-MM-DD-<type>-<work-name>/
```

That move is the entire state transition. There is no Status field to
update, no eight spelling variants to reconcile. A directory under
`changes/` is active. A directory under `changes/archive/` is done.

### Naming rules

```text
YYYY-MM-DD-<type>-<work-name>/
│           │
│           └── feat | fix | refactor | spike (legacy only)
└────────────── date of archiving (or last-active day for migrations)
```

- The date is the **archive day** when archived by `fullstack-archive`;
  migrations use the **last active day** (progress.md update or last git
  commit) to preserve the historical timestamp.
- The type prefix is **mandatory**: `feat/<name>` and `fix/<name>` may
  share a name, so date + name alone can collide.
- Idempotence: if the source name already starts with `YYYY-MM-DD-`
  (a migration leftover), the date is not stacked — only the type prefix
  is added.
- On collision (target already exists), archiving **fails hard** rather
  than overwriting.

### Why archive matters

An unbounded append-only `feat/` makes "abandoned" and "finished-and-
left-alone" indistinguishable. Archive restores the distinction: stale
directories inside `changes/` are abandoned; anything in `changes/archive/`
is intentionally closed. It also gives the docs repo a natural release
timeline — read `changes/archive/` in date order and you see what shipped.

---

## Work types

| Type | Meaning | analysis.md author | Branch prefix |
|---|---|---|---|
| `feat` | New capability | Planner | `feat/` |
| `refactor` | Restructure without behavior change | Planner | `refactor/` |
| `fix` | Bug resolution | Debugger | `fix/` |

The work type is determined at propose time and recorded in the directory
path, branch names, and `plan.md`. It never changes mid-lifecycle.

---

## Successors (`-vN`)

When a closed work item needs further work, a **new** work directory is
created rather than reopening the closed one:

```text
changes/feat/dark-mode-v2/          # successor
changes/archive/…-dark-mode/        # predecessor (already archived)
```

The successor links back to the predecessor via:

- `**Source**` / predecessor reference in `analysis.md`
- a `## Successors` table appended to the predecessor's `progress.md`
  **before** it was archived

Archived items are never reopened. `-vN` chains can grow; that is
expected — each directory is a complete, self-contained record.

---

## What documents are not

The four documents are **decision records**, not behavior specifications.
They answer *why* a decision was made, *what* was planned, *what happened*,
and *how it was reviewed. They do **not** use SHALL/MUST requirement
grammar, delta specs, or a main spec to merge into. If you need a
behavior contract that lives beyond a work item, write it in your own
`docs/` knowledge directories — the skills won't touch them.

---

## Glossary

| Term | Meaning |
|---|---|
| Work item | One logical change: a feat, fix, or refactor |
| Work directory | `changes/<type>/<work-name>/` — the item's four documents |
| `changes/` | The lifecycle container in the docs repo |
| Archive | Moving a work directory into `changes/archive/` with a date+type prefix |
| Success Criteria | The pre-agreed, testable checklist in `plan.md` |
| Evidence table | The review.md table mapping each criterion to concrete proof |
| Spike (deep mode) | propose's optional validation path; lives in `analysis.md` |
| Successor | A new work directory (`-vN`) that continues an archived predecessor |

---

## Where to go next

- Not sure which skill to use? [Workflows](workflows.md).
- Want the one-screen version? [Overview](overview.md).
- How do subagents do the work? [Agent Orchestration](AGENT-ORCHESTRATION.md).
