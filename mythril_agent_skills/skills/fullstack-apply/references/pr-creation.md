# Creating Pull Requests (github_repos=true only)

Read this only when the announced `Workspace:` line says
`github_repos=true`. With `github_repos=false`, none of this applies — see
the anti-patterns at the end.

## Pre-conditions

- All repos must have changes committed and pushed
- Review verdict is PASS (or residuals documented)
- Each repo's current branch is a feature branch (not the default)

## Per-repo PR creation

PR creation is per-repo with no cross-repo interaction — create the PRs
for all affected repos in parallel (or sequentially when the host
runs one command at a time). For each repo:

1. `cd` into the repo directory
2. Push the branch if not already pushed: `git push -u origin HEAD`
3. Use the `github-pr-create` skill to create the PR:
   - Base = the repo's default branch
   - Title reflects the work item (derived from branch name or
     `plan.md` title)
   - Body filled per the repo's PR template (if any), using the code
     changes diff + `plan.md` context
   - Include the Jira ticket reference if available
4. Record the PR URL

PR body filling rules:

- If the repo has a PR template, follow it strictly — only fill
  sections where you have information from the implementation
- Leave screenshot/image placeholders as-is
- Leave unfamiliar link placeholders as-is
- Fill Jira/ticket links and tech doc links from gathered context
  when fields ask for them
- When in doubt, preserve the template's original text

## After all PRs are created

1. **Update `progress.md`** — add a "Pull Requests" section:

   ```markdown
   ## Pull Requests

   | Repository | PR URL | Status |
   |-----------|--------|--------|
   | shared-lib | https://github.com/owner/shared-lib/pull/42 | Created |
   | api | https://github.com/owner/api/pull/99 | Created |
   ```

   (Use Chinese labels for Chinese language work items: `## Pull
   Requests` header stays English; `仓库 / PR 链接 / 状态` for columns.)

2. **Commit** the docs repo with the updated progress.

## Error handling

If `gh pr create` fails for a repo (auth, not a GitHub remote, branch
not pushed, etc.), record the failure in `progress.md` and move on:

```markdown
| api | — | Failed: `gh` error: ... |
```

Do NOT block the entire finalization on one repo's PR failure — create
PRs for all repos that succeed and report failures separately.

## Anti-patterns (forbidden when github_repos=false)

| Anti-pattern | Why it's wrong |
|--------------|----------------|
| Inspecting `git remote -v` to "decide" whether the host is GitHub | The user already answered this during `fullstack-init`. Re-deriving from hostname is misclassification |
| Running `which gh glab gitee` to look for an alternative platform CLI | Not your job. The user configures their own tooling |
| Constructing compare URLs (`/compare/main...feat/X`) and presenting them as "PR URLs" | These are not PRs — they are diff views |
| Parsing `git push` output for "Create pull request" hints | Not in scope |
| Asking the user "should I open a PR via the web UI?" | PR creation is the user's responsibility for non-GitHub remotes |
