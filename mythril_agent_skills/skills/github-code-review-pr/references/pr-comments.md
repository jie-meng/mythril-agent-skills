# Posting Review Comments to the PR

Read this when, after the review is delivered, the user asks to send comments
about specific issues back to the PR.

## Default: inline line-level comments

Use an inline review comment (equivalent to clicking `+` on a line in the
"Files changed" tab) when any of these apply:

- The user refers to a specific line, code block, or snippet from the review.
- The user copies/pastes part of the review that identifies a specific code
  issue.
- The user says things like "comment on that line", "add comment there",
  "给那行加个评论", "在那里加 comment".
- The review already identified a specific file and line for the issue — the
  user is just asking to post it.

If it is ambiguous whether the user wants inline or general, choose inline:
reviewers find line-anchored comments far easier to act on.

```bash
# Get the PR head commit SHA
HEAD_SHA=$(gh pr view <URL_or_NUMBER> --json headRefOid -q .headRefOid)

# For github.com repos:
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments \
  -X POST \
  -f body='Your review comment here' \
  -f commit_id="$HEAD_SHA" \
  -f path='path/to/file.kt' \
  -F line=42 \
  -f side='RIGHT'

# For GitHub Enterprise (custom host):
gh api --hostname <host> repos/OWNER/REPO/pulls/PR_NUMBER/comments \
  -X POST \
  -f body='Your review comment here' \
  -f commit_id="$HEAD_SHA" \
  -f path='path/to/file.kt' \
  -F line=42 \
  -f side='RIGHT'
```

- `path`: file path relative to the repo root (from the PR diff)
- `line`: line number in the diff's new version of the file (RIGHT side)
- `side`: `RIGHT` for new code (most common), `LEFT` for old/deleted code
- `commit_id`: the HEAD SHA of the PR branch

**Finding the line number:** use the saved PR diff (`PR_DIFF_PATH`). The
`line` parameter is the line number on the RIGHT side of the diff (the new
version). Match the code snippet from the review to the diff.

## Exception: general PR-level comment

Use a general comment (bottom of the PR's "Conversation" tab) only when:

- The user explicitly says "给 PR 写一个 comment", "add a comment to the PR",
  "leave a general comment".
- The comment is about the PR as a whole (overall architecture feedback,
  summary of findings) and does not reference a specific code line.
- The user asks to post the full review summary as a comment.

```bash
gh pr comment <URL_or_NUMBER> --body "Your general comment here"
```

## Examples

Inline (default):
- "把第3点关于空指针的问题发个 comment" → find the file and line from review
  point #3, post an inline comment.
- "send a comment about the missing null check" → find the relevant line in
  the diff, post an inline comment.
- "给这段代码加个评论: `val result = api.fetch()` 没有错误处理" → find where
  this code appears in the diff, post an inline comment.

General:
- "给这个 PR 写一个总结 comment" → post a general PR comment.
- "leave a comment summarizing the review" → post a general PR comment.
