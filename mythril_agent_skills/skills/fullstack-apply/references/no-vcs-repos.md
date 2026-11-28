# Repos without version control

Read this when a repo in scope fails `git rev-parse --git-dir`.

If a repo has no git metadata (`git rev-parse --git-dir` fails), it
cannot support branches, staging, commits, or diffs. Handle it as
follows for the WHOLE run — do not improvise per step:

- Skip branch creation (this step), staging (`git add .`), commit
  (4e), and branch push and PR creation (Step 7). The repo
  still gets its developer → review loop and its wave position.
- The developer cannot stage, so it MUST return the exact list of
  every file it created or modified, each with a path relative to the
  repo root — that list replaces the staged diff in every later step.
- Review (4d) runs over that file list — the code-reviewer reads the named
  files instead of a diff. If code-reviewer delegation is impossible, the
  orchestrator may self-review, and the review section must say so
  explicitly ("orchestrator self-review").
- In `review.md`, its per-repo section records a `### Changed files`
  / `### 改动文件` list INSTEAD of `### Commits` — one row per file,
  repo-relative path, concrete per-file change description (template
  and rules in `references/review-formats.<lang>.md`).
  Without git there is no diff and no commit history to inspect
  later, so this list is the only durable change record the team has
  when they commit the repo by hand.
- State in `progress.md` and the final report that the team must
  commit these changes themselves.
