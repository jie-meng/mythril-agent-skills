# Lessons Learned (optional, value-gated)

The four work-tracking documents already record **what happened**. This
step exists to convert a genuinely new, transferable insight into the
docs repo's knowledge so a future session does not rediscover it the
hard way. It is optional and value-gated — most work items produce no
lesson, so a deliberate skip is the correct default, never a default of
"fill a template". Write a lesson when any of these is true:

1. **Non-obvious trap / gotcha** that cost real implementation or review
   time — a library quirk, an ordering or dependency constraint the plan
   did not surface, a silent failure mode.
2. **Cross-repo / cross-tool constraint** that will affect similar
   future work — an env var required by two repos, a build step, a
   migration ordering, a service boundary invariant.
3. **A design decision whose rationale is non-obvious** — one that took
   deep analysis or a falsified hypothesis to reach. If the reasoning is
   already self-evident in `analysis.md`, do not duplicate it.
4. **A recurring mistake corrected** — a bug you misdiagnosed at least
   once, so the correction (and how to recognize the symptom early) is
   worth preserving.

Skip (the default) when the lesson is really just the work item itself —
that belongs in `progress.md` / `review.md`, not in a knowledge doc — or
when the topic is already recorded elsewhere in the docs repo: update
that existing doc, don't create a duplicate.

### Where to put it — follow the docs repo's own structure

Do NOT impose a fixed lessons directory or a generic name like
`lessons-learned/`. First explore the docs repo's existing knowledge
layout (the directories beside `changes/`, e.g. `docs/` organized by
domain / architecture / platform). Find where this work's insight
naturally belongs — the doc for the component, the architecture or
platform section, the topic folder it extends. Write the lesson there
following that area's existing convention: append a `## <Title>`
subsection, add to an existing topic file, or create a domain file if
none exists.

Only when no existing place fits, create a directory named for the
lesson's own subject — the topic the insight actually covers, not a
generic bucket. Choose a concise lowercase-hyphenated name (the repo's
naming convention) that a future reader would search for, e.g.
`docs/<subject>/<subject>.md`. Write the lesson there, short: what you
learned, why it matters, and the guard to apply. Reuse the same file or
directory for later lessons on the same subject rather than inventing a
new name.

When in doubt, ask the user where the lesson belongs before creating a
new directory — do not guess a location the team then has to relocate.

### Record the outcome

- **If you wrote a lesson**, append one bullet to the final entry in
  `progress.md`: `- Captured insight to <relative path> — <summary>`
- **If you deliberately skipped**, record nothing. The absence is the
  correct, intentional outcome and needs no justification entry.

Commit the docs repo with the captured insight (a docs commit of its
own, after the Step 6 finalization commit).
