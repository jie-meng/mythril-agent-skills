# Deep Mode (spike) — validate unknowns first

Read this when Step 4 of `SKILL.md` picks deep mode. Deep mode is always
full tier. Do the baseline (Step 4a of `SKILL.md`) first; the spike steps
below replace Step 4b, and the gates and plan review that follow still apply.

Use this when Step 1 reveals significant unknowns (technical risk,
unproven feasibility, unclear design choice). The output is the SAME
work directory — no separate spike directory, no rewrite later.

**Spike step 1. Write the spike part of `analysis.md`:**

```markdown
# Analysis: <Work Name>
**Created**: <date>   **Type**: <feat|fix|refactor>   **Author**: Planner

## Objective
<What are we trying to find out? What question does this spike answer?>

## Current State
<Existing system behavior / architecture / limitations>
### Architecture (as-is)
```mermaid
flowchart LR
    A[Component A] --> B[Component B]
```

## Hypothesis
<What do we believe will work? What assumptions are we testing?>

## Spike Approach
| Step | What to try | Repo | Expected outcome | Risk |
|------|-------------|------|-----------------|------|
| 1 | ... | api/ | ... | Low |

## Unknowns
- <What we don't know and need to find out>

## Success Criteria
<How do we know the validation succeeded? What evidence do we need?>
- [ ] Criterion 1
- [ ] Criterion 2
```

**Spike step 2. Execute the spike (temporary, uncommitted):**

1. Read each affected repo's `AGENTS.md` and `README.md`; use graphify
   when available (same protocol as Step 1c).
2. Make temporary code changes to validate the hypothesis. Do NOT run
   `git add` or `git commit` on any code repo.
3. Run tests, start dev servers, check logs — whatever validates the
   criteria.
4. Record each experiment, its result, and evidence directly in
   `analysis.md` under a `## Experiments` section (appended as you go).

**Spike step 3. Complete the analysis — same file:**

After validation, append to `analysis.md` (still the same file):

```markdown
## Experiments
### Experiment 1: <title>
**What was tried**: ...   **Result**: ...   **Evidence**: ...

## Verdict
<FEASIBLE | NOT_FEASIBLE | NEEDS_MORE_RESEARCH> — one paragraph
summarizing whether the approach works and what was learned.

## Design Options
| Option | Approach | Pros | Cons | Complexity |
|--------|----------|------|------|-----------|
| A (chosen) | ... | ... | ... | Medium |

## Target Architecture
```mermaid
flowchart LR
    A[Component A] --> B[Component B]
```

## Cross-Repo Impact
| Repo | Impact | Breaking Change? |
|------|--------|------------------|
| api/ | ... | No |

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
```

**Spike step 4. Write `plan.md` from the verdict.** If NOT_FEASIBLE, write the
plan documenting why it's not proceeding (the plan still exists — the
record matters). If FEASIBLE, the plan reflects the chosen Design Option.

**Spike step 5. Clean up temporary spike changes** before finishing:

```bash
cd <repo-1> && git checkout .
cd <repo-2> && git checkout .
```

...unless the user explicitly says to keep the spike changes for
`fullstack-apply`.
