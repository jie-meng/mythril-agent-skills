# Deep Mode (spike) — validate unknowns first

Read this when Step 4 of `SKILL.md` picks deep mode. Deep mode is always
full tier. Do the baseline (Step 4a of `SKILL.md`) first; the spike steps
below replace Step 4b, and the gates and plan review that follow still apply.

Use this when Step 1 reveals significant unknowns (technical risk,
unproven feasibility, unclear design choice). The output is the SAME
work directory — no separate spike directory, no rewrite later.

**Spike step 1. Write the spike part of `analysis.md`** below the
baseline Step 4a already wrote (keep its header and §Original
Requirements; do not start a second `# Analysis` header):

```markdown
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

## Validation Criteria
<How do we know the spike succeeded? What evidence do we need? These
judge the spike, not the delivery — `plan.md` §Success Criteria (`SC<n>`)
is written in step 4.>
- [ ] V1 <...>
- [ ] V2 <...>
```

**Spike step 2. Execute the spike (temporary, uncommitted, never over
the user's own changes):**

1. Read each affected repo's `AGENTS.md` and `README.md`; use graphify
   when available (same protocol as Step 1, item 3 of `SKILL.md`).
2. **Check the working tree before touching a repo:**
   `git -C <repo> status --porcelain`.
   - Empty → spike in place.
   - Not empty → the user has uncommitted work there. Never stash,
     reset, or check out over it. Spike in a throwaway worktree under
     the skill cache instead (or ask the user to commit first):

     ```bash
     if [[ "$(uname -s)" == "Darwin" ]]; then
       CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
     else
       CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
     fi
     SPIKE_DIR="$CACHE_ROOT/fullstack-propose/<work-name>/<repo>"
     git -C <repo> worktree add --detach "$SPIKE_DIR" HEAD
     ```

   Note in `## Experiments` which repos ran in place and which in a
   worktree — step 5 cleans them up differently.
3. Make temporary code changes to validate the hypothesis. Do NOT run
   `git add` or `git commit` on any code repo.
4. Run tests, start dev servers, check logs — whatever validates the
   criteria.
5. Record each experiment, its result, and evidence directly in
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
```

Risks and assumptions go in `plan.md` §Risks / Open Questions only — not
in `analysis.md` — so there is one copy to keep true.

**Spike step 4. Write `plan.md` from the verdict.** If NOT_FEASIBLE, write the
plan documenting why it's not proceeding (the plan still exists — the
record matters). If FEASIBLE, the plan reflects the chosen Design Option.

**Spike step 5. Clean up temporary spike changes** before finishing —
tracked edits and the files the spike created:

```bash
# A repo spiked in place — its tree was clean before the spike (step 2),
# so everything uncommitted now is the spike's own. `git clean -fd`
# leaves ignored files (build output, node_modules) alone.
git -C <repo> checkout -- . && git -C <repo> clean -fd

# A repo spiked in a worktree — the user's tree was never touched.
git -C <repo> worktree remove --force "$SPIKE_DIR"
```

Never run the in-place commands on a repo whose tree was not clean
before the spike. Finish by checking `git -C <repo> status --porcelain`
matches its pre-spike state.

Skip the cleanup only when the user explicitly says to keep the spike
changes for `fullstack-apply` — then say which repos (or worktree paths)
hold them.
