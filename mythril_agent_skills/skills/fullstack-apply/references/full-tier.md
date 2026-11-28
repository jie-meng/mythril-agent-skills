# Full Tier — the wave loop

Read this when the item runs at full tier (`SKILL.md` Step 1 decides the
tier). It replaces the lean loop of `SKILL.md` Step 4; the implementer
checklist, the round 2+ review brief, the code-reviewer fallback, and
4e (commit and bookkeep) stay in `SKILL.md` and apply unchanged.

Repos in the same wave share no dependency edge; each runs develop →
review → commit **in parallel** with its siblings. A wave is a barrier: the
next starts only when every repo of the current one has committed.
Parallelism changes *when* checks run, never *whether*: every repo gets its
staged review before commit; dependents never see unverified upstream code;
the cross-repo review sees all final diffs once.

| Agent | Owns | Must NOT touch |
|-------|------|----------------|
| **developer** | Production code, tests, env setup | `review.md`, `progress.md`, commits |
| **code-reviewer** | Findings + Evidence rows (per-repo and cross-repo modes) | Any file |
| **debugger** | Root cause + fix spec; temporary instrumentation | `plan.md`, commits |
| **you** | `progress.md`, `review.md`, commits, PRs, the user | Code (delegate it) |

Only you write the work-tracking documents, so parallel agents share no
mutable state. Never put two agents in one repo at the same time — repos
are the unit of isolation.

**Context budget — keep every agent short-lived.** An agent re-sends its
whole context on every step, so a run's cost grows with steps × context,
not with the code it writes. One measured full-tier item: a single
developer ran 309 steps on one repo and its context grew from 19K to 382K
tokens — 73% of the item's tokens; resuming that same agent for a
five-finding fix round cost 14M tokens where a fresh one would have cost
about 2M. Therefore:

- **One developer per phase**, not per repo, when `plan.md` schedules
  phases for a repo or its slice is large (several modules, a port plus
  a service layer). Phases of one repo run one after another — still one
  agent in the repo at a time. Each is a fresh subagent; the next phase's
  brief carries the previous phase's returned summary and file list,
  never its transcript. Stage between phases; commit once per repo after
  review unless `plan.md` says otherwise.
- **Fix rounds go to a fresh developer**, never to the agent that wrote
  the code (no resume / SendMessage of a finished implementation run).
  The fix brief is: the findings verbatim, the repo path and branch, the
  slice paths, the implementer checklist, and "fix exactly these, then
  re-validate and re-stage". The staged diff and the work-dir documents
  are on disk.
- A silent agent is not evidence of a long test run; check its latest
  activity before telling the user why it is quiet.

For each wave, in order:

**4a. Briefs — a slice of the plan per repo, never the four documents
whole.** The repo's row and tasks; the Success Criteria it proves; the
relevant `analysis.md` sections; for consumers, the **frozen contracts**
of every upstream interface (code targets exactly these names); the
`repo_skills.py` output verbatim; branch and "wave N of k"; the implementer
checklist and the Code Comment Policy verbatim (the developer cannot see
this file); the work-dir path; "return results — the orchestrator writes
the documents".

**4b. Delegate** every repo of the wave to its developer **in one turn**
(the first phase's developer, for a repo split into phases).

**4c. Handle each result as it returns** — never block a healthy sibling on
a broken one. Tests failed → a fresh developer for THAT repo on a fix
brief (the failure output plus the brief above). `tests:
unknown` / `tests: none` → record it explicitly in `progress.md` and flag it
in review; untested code never passes silently. Write each completed result
to `progress.md` (template: `template-progress.<lang>.md`), then review.

**4d. Per-repo review** — a fresh code-reviewer per repo (parallel), mode
per-repo, with the same slice the developer got, the developer's summary
and test result, and the work-dir path; it runs `git diff --cached`
itself. Re-reviews use the round 2+ brief in `SKILL.md`. Append its output to `review.md` below the plan review rounds
(never renumber them; format: `review-formats.<lang>.md`).

- `NEEDS_FIXES` → P0/P1 to a fresh developer for that repo on a fix
  brief (see "Context budget") → re-validate → re-stage → re-review. P1-only fixes proven by tests / lint / build skip
  the re-review, as in the lean loop. Max 3 review rounds per repo. A P0/P1
  that survives one fix round, or whose cause is not evident from the
  diff, goes to the **debugger** first.
- `PASS` / `PASS_WITH_RISKS` → copy its Evidence rows into the `review.md`
  Evidence table now, then commit (`SKILL.md` 4e).
- `FAIL` → stop that repo, hold its dependents, take it to the user (a
  re-plan goes through `fullstack-propose`). Siblings continue.

**Wave gate — before releasing wave N+1:** every repo of wave N is
committed (not merely "done"); each frozen contract owned by wave N was
compared with what was built — drift is fixed upstream now, or frozen as an
explicit amendment in `analysis.md`; downstream briefs carry any amendment.

After the final wave → `SKILL.md` Step 5.
