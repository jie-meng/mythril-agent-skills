## `plan.md`

### Status is the directory location — no Status field

The lifecycle state of a work item is expressed by its directory
location, NOT a text field. Active work lives in
`<docs-dir>/changes/<type>/<work-name>/`; archived work lives in
`<docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>/`. Do NOT
write a `**Status**:` field in `plan.md`.

### English

```markdown
# <Work Name>

**Source**: <Jira link / user prompt / Confluence page / predecessor work item>

**Type**: feat | refactor | fix

**Branch**: <branch-name>

**Created**: <date>

## Summary

**In one sentence**: <what the problem is and what we'll do — no ids, no file refs>

**In plain words**: <what will be different once this ships — one line a non-engineer can read, no ids; include the biggest remaining risk when there is one>

**Status**: <planning | ready to implement | in progress | done> — <lean | full> tier — <one-line latest verdict, e.g. plan review round 2 PASS>

**Decisions needed from you**: <none; or one line each: question → options → our recommendation>

**Not solved here**: <explicit exclusions, pending verifications, residual risks — one line each>

**Where to read**: problem detail → analysis.md; how → this file's body; evidence → review.md

## Requirements

<Summary of requirements from gathered context>

## Success Criteria

<Testable, specific acceptance criteria — "Works correctly" is not a
criterion; "returns 200 with valid JSON matching schema X for inputs A,
B, C" is. Each criterion is checked against evidence in review.md.
Every criterion carries an `SC<n>` id — no hyphen, numbered per work
item, never reused. The Evidence table and the coverage matrix cite the
id, and `plan_lint.py` matches Evidence rows to criteria by it.>

- [ ] **SC1** — <observable behavior + expected outcome>
- [ ] **SC2** — <...>
- [ ] **SC3** — <...>

## Affected Repositories (in dependency order)

| # | Repository | Branch | Changes Needed | Depends On | Priority |
|---|-----------|--------|---------------|-----------|----------|
| 1 | shared-lib | feat/Dark-Mode-Toggle | Add theme types | — | P0 |
| 2 | api | feat/BE-450/Dark-Mode-Toggle | Add preference endpoint | shared-lib | P0 |
| 3 | android | feat/MOBILE-301/Dark-Mode-Toggle | Add toggle screen | shared-lib, api | P1 |

Repos MUST be listed in dependency order: upstream first (shared libs,
data models), then services (api, backend), then consumers (web, ios,
android). fullstack-apply derives its parallel implementation waves
from this table — repos sharing no dependency edge are developed and
committed concurrently. Every interface a downstream repo consumes
MUST be frozen in analysis.md (exact field names, types, error codes):
parallel developers write against the frozen contract, not against
upstream code that may not exist yet.

## Code Map

<The reverse index — which files this work item owns. Written here at
planning time with the paths the plan expects to touch; `fullstack-apply`
replaces planned paths with the paths it actually changed, on every
round. Later readers query this table to find the work item behind a
file, so a path that changed code but is missing here is a change nobody
can trace back to a spec.>

| Repository | Path | Symbols | What changed |
|-----------|------|---------|--------------|
| api | `src/preferences/dark_mode.py` | `ThemePreference`, `GET /pref` | New preference endpoint |
| android | `app/src/ui/SettingsScreen.kt` | `DarkModeToggle` | Toggle row on the settings screen |

Rules:

- **Path is relative to the repo root** (`src/preferences/dark_mode.py`),
  never an absolute machine path and never a bare file name. Prefixing
  the repo column and the repo-relative path is what makes the pair
  greppable from a workspace-relative path. A file that really sits at the
  repo root is written `./README.md` — the `./` says "root", where a bare
  `README.md` leaves the lookup guessing between same-named files in other
  repos.
- **Symbols is optional** — fill it when the file name does not say what
  changed. It is the lookup key for a reader who was told "the
  `computeWave` function is wrong" and has no file path.
- **Rewrite the table in place.** Unlike `progress.md`, this is a current
  state, not a log: a path that was touched then reverted does not stay
  listed. History belongs in `progress.md`. Earlier rounds' files stay in
  the table — it is the item's whole ownership, not this round's diff.
- **One row per file**, no ranges (`src/ui/*`) and no path lists in one
  cell (`src/a.py`, `src/b.py`) — a wildcard or a merged cell cannot be
  matched by a path lookup, so each silently drops traceability for every
  file it pretends to cover. A directory (`src/ui/`) or a placeholder
  (`—`, `待定`) names no file either.

## Implementation Plan

<Every task carries a `T<n>` id, numbered across phases and never
reused; review rounds and the coverage matrix cite it.>

### Phase 1: <name>
- [ ] **T1** (repo-x) — <task>
- [ ] **T2** (repo-y) — <task>

### Phase 2: <name>
- [ ] **T3** (repo-x) — <task>

## Dependencies

<Cross-repo dependencies, order constraints>

## Risks / Open Questions

**Active risks**

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | <risk, stated as its conclusion> | Medium | High | <mitigation> |

**Closed**

(none — a risk that has closed moves here with one line: why it closed and
where it was resolved. Rows are never deleted; the partition keeps the
live exposure readable at a glance.)
```



### Successor addition

When this work item inherits from an archived predecessor, add a
`Predecessor` line to the header right after `Created`:

- English: `**Predecessor**: feat/dark-mode/ (archived 2026-04-15)`
- Chinese: `**前置工作**：feat/dark-mode/（2026-04-15 归档）`

---
