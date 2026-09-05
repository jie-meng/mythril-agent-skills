# Review Formats

Templates for sections appended to `review.md` during implementation
and review. Use the language matching the user's prompt.

## Per-repo staged review section

Appended once per repo per review round. The full
`code-review-staged` output is preserved verbatim — do not summarize.

### English

```markdown
## <repo> — Review Round <N> — <date>

### Staged Review Output

<Full output from code-review-staged, preserving all sections>

### Verdict

<PASS | NEEDS_FIXES> — <one-line summary>

### Commits

| Hash | Message |
|------|---------|
| `abc1234` | feat: add dark mode toggle |
```

### Chinese

```markdown
## <repo> — 第 <N> 轮审查 — <date>

### 暂存区审查输出

<code-review-staged 的完整输出，保留所有章节>

### 结论

<PASS | NEEDS_FIXES> — <一句话总结>

### 提交记录

| Hash | Message |
|------|---------|
| `abc1234` | feat: add dark mode toggle |
```

### Commits section rules

The `### Commits` / `### 提交记录` section is appended **immediately after
the Verdict** once the repo's staged changes are committed. This applies
to **every round that produces a commit** — the initial implementation
round AND every subsequent iteration round. Record every commit made in
that round, one row per commit, in chronological order.

- **Hash**: short hash (7 chars from `git log --oneline`); wrap in backticks
- **Message**: the full first line of the commit message
- If the round ends with `NEEDS_FIXES` and no commit was made, omit the
  section entirely; it will be added in the later round where the fix
  is committed
- Each iteration round produces its own review section (new
  `## <repo> — Review Round <N>` heading); append `### Commits` to
  that new section after the commit is made — never back-fill into a
  prior round's section

### Keeping commits in sync after hash changes

Whenever a commit's hash changes — due to `git commit --amend`,
interactive rebase, squash, `git reset` + re-commit, or any other
operation — update the affected row(s) in `### Commits` immediately.
This applies regardless of whether the user requested it explicitly:
if you performed or observed an operation that changes hashes, sync
the table without waiting to be asked.

How to detect that a hash changed:

```bash
git log --oneline -5   # compare against what is recorded in review.md
```

Update rules:

- **Amend (same logical commit, new hash)**: replace the old hash with
  the new one in the existing row; optionally note `(amended)` in the
  Message column if the message also changed
- **Squash / fixup (N commits → 1)**: collapse the affected rows into
  one row with the resulting hash; keep the messages collapsed as
  `squash: <summary>` or list them separated by ` / `
- **Rebase (hashes rewritten, messages unchanged)**: update each hash
  in place; messages stay the same
- **Reset + re-commit (logical commit replaced)**: replace old row(s)
  with the new commit(s)
- **Commit deleted / reverted**: strike through or remove the row and
  add a note `(reverted)` in the Message column

This provides a complete, append-only audit trail: every commit that
touched each repo across the entire lifetime of the work item is
traceable to the exact review round that approved it, and the recorded
hashes always match what is actually in the git log.

### Repos without version control

A repo with no git metadata cannot produce commits, so its per-repo
review section has no `### Commits` table. Replace it with a
`### Changed files` / `### 改动文件` section. For such a repo this list
is the ONLY durable record of what changed — there is no diff and no
commit history to inspect later — so it must be exact and
self-sufficient.

### English

```markdown
### Changed files (no version control)

| File (relative to repo root) | What changed |
|------------------------------|--------------|
| `src/ui/SettingRobot.cs` | Added unbind confirmation state machine (4 outcome paths); OnDestroy now unregisters the disconnect listener; added `UnbindTimeoutSeconds` constant |
| `src/net/ShortRangeManager.cs` | Added `BleWriteCommand` overload with completion callback; pause/resume of the status polling loop in `RequestStop`/`RequestReadBleStatus` |
| `assets/strings/en.json` | Added `UNBIND_SEND_FAILED`, `UNBIND_NOT_COMPLETED` keys |
```

### Chinese

```markdown
### 改动文件（无版本控制）

| 文件（相对仓库根目录） | 改动说明 |
|----------------------|---------|
| `Assets/Scripts/UI/SettingRobot.cs` | 新增解绑确认状态机（4 条结果路径）；OnDestroy 注销 disconnect 监听；新增常量 `UnbindTimeoutSeconds` |
| `Assets/Scripts/Net/ShortRangeManager.cs` | 新增带完成回调的 `BleWriteCommand` 重载；`RequestStop`/`RequestReadBleStatus` 中暂停/恢复状态轮询 |
| `Assets/Localization/StringTable_en-US.asset` | 新增本地化键 `UNBIND_SEND_FAILED`、`UNBIND_NOT_COMPLETED` |
```

Rules:

- **One row per file** — never merge several files into one row and
  never compress the list into flowing prose ("A（…）、B（…）、C（…）"
  style is forbidden). Every file the round created or modified gets
  its own row: code, tests, docs, assets, localization tables alike.
- **Path is relative to the repo root** (`Assets/Scripts/X.cs`) — not
  an absolute machine path, not a bare file name. The team uses these
  paths to locate and hand-commit the changes.
- **The description must let a reader who cannot run `git diff`
  understand the change**: what was added / modified / removed, and
  the key functions, states, keys, or constants involved. Vague label
  stacks ("状态机 + 生命周期清理 + 常量") are not enough.
- **Verify the list before recording it** — against the developer's
  report and the filesystem (e.g. modification times). A file listed
  but not actually changed, or changed but missing, misleads the team
  when they commit this repo by hand. If an error is discovered after
  the round is recorded, correct it with a dated errata note in the
  same section — never silently rewrite a recorded round.
- Note in the section (or the repo heading) that the repo has no
  version control, whether the review was an orchestrator
  self-review, and that the team must commit the changes by hand.

---

### Verdict mapping

| code-review-staged output | Verdict | Action |
|---------------------------|---------|--------|
| Major Issues section has critical/high-severity items | `NEEDS_FIXES` | Fix and re-review |
| Code Quality section has significant violations | `NEEDS_FIXES` | Fix and re-review |
| Only minor suggestions or clean review | `PASS` | Proceed to commit |

### Fix-cycle convergence principle

Each round should have **fewer** findings than the previous round. If
round N introduces more new issues than it fixes, the developer is
likely over-editing — stop the cycle, record residual issues, and
commit. Max 3 rounds; remaining P0/P1 after round 3 is logged as
**residual** in both `review.md` and `progress.md`.

---

## Cross-repo consistency review section

Appended once per work item (multi-repo only). Skip entirely for
single-repo work. Even when no issues are found, a `PASS` section
documenting what was checked must be written.

### English

```markdown
## Cross-Repo Consistency Review — <date>

### Checks Performed

- API contracts: <result>
- Shared types: <result>
- Environment variables: <result>
- Database migrations: <result>
- Error contracts: <result>
- Version compatibility: <result>

### Findings

- [P0] <repo-A> ↔ <repo-B>: <contract mismatch> — must fix
- [P2] No cross-repo issues found

### Verdict

<PASS | NEEDS_FIXES> — <summary>
```

### Chinese

```markdown
## 跨仓库一致性审查 — <date>

### 检查项

- API 契约：<结果>
- 共享类型：<结果>
- 环境变量：<结果>
- 数据库迁移：<结果>
- 错误契约：<结果>
- 依赖版本兼容性：<结果>

### 发现

- [P0] <repo-A> ↔ <repo-B>：<契约不匹配> — 必须修复
- [P2] 未发现跨仓库问题

### 结论

<PASS | NEEDS_FIXES> — <总结>
```

### Backward-compatibility addendum (Follow-up Mode only)

When the work item is a follow-up to a closed predecessor, append one
extra bullet under `Checks Performed`:

- English: `- Backward-compat with predecessor: <result>`
- Chinese: `- 与前置工作的向后兼容：<结果>`

The check verifies that any field, endpoint, schema, or shared type the
predecessor introduced remains compatible — or, if breaking, the change
is an explicit goal of this follow-up and is documented in
`analysis.md`'s Design Options. The predecessor is the work item
referenced under `**Predecessor**:` in `plan.md` (a successor work item,
`<name>-vN`).

---

## Standard cross-repo checks (what each result line should answer)

| Check | What it verifies |
|-------|------------------|
| **API contracts** | Request/response shapes match between producer and consumer |
| **Shared types** | Type definitions in shared-lib match usage in all consumers |
| **Environment variables** | New env vars are documented in all affected repos |
| **Database migrations** | Schema changes are compatible across services |
| **Error contracts** | Error codes/messages are consistent across boundaries |
| **Version compatibility** | Dependency version bumps are aligned across repos |

If a check is genuinely N/A for this work, write `N/A — <reason>`
instead of skipping the bullet. The presence of the bullet proves
the agent considered it.
