# Cross-Repo Consistency Review (multi-repo only)

Read this after the final wave's gate passes on a multi-repo work item.

Skip this step for single-repo work. For multi-repo, this is **the one
global barrier** of the whole implementation: after the final wave's
gate, delegate to the **code-reviewer** subagent in cross-repo mode to
verify changes are consistent across all affected repos. Per-repo
staged reviews (4d) never substitute for it — each saw only its own
diff; integration defects live between diffs.

## 5a. Brief the code-reviewer (cross-repo mode)

Give it paths and commands, not pasted content — it reads and diffs for
itself, so the diffs never pass through your context:

- the work-dir path, with `plan.md` and `analysis.md` (the frozen
  contracts) to read from disk;
- per affected repo: its path, default branch, and feature branch, so it
  can run `git diff <default-branch>...<feature-branch>`;
- for a repo without version control, its `### Changed files` list in
  `review.md` instead (see `references/no-vcs-repos.md`);
- for successor work (`-vN`): the predecessor's shipped contracts
  (backward-compatibility check).

The code-reviewer's cross-repo checklist lives in its agent file (API
contracts, shared types, env vars, migrations, error contracts, version
alignment, and backward compatibility for successor work).

## 5b. Write cross-repo findings

Append the code-reviewer's output to `review.md` using the template in
`references/review-formats.<lang>.md`. Even if
no issues are found, write a `PASS` confirmation documenting what was
checked.

## 5c. Fix cross-repo issues

If P0/P1 cross-repo issues are found:
1. Fix upstream repo first, then downstream (topological order — the
   wave plan from Step 4 is the order).
2. For each repo needing fixes, go through its scoped developer →
   code-reviewer loop again (Steps 4b through 4e). Fixes to MUTUALLY
   INDEPENDENT repos may fan out in parallel, exactly like a normal
   wave.
3. Re-run the cross-repo review after all fix repos pass.
4. Max 2 fix rounds — if issues persist, record as residual.
