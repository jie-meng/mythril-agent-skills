# Review Formats

Templates for sections appended to `review.md` during implementation
and review. Use the language matching the user's prompt.

## Canonical order of `review.md`

One work item has ONE falsification record. Every section carries an
artifact prefix, so a reader (and `plan_lint.py`) can tell a plan-stage
verdict from a code-stage one — both use round numbers:

```text
# 审查：<工作名称>          # header: what this file holds
## 状态速览                  # updated in place — the only exception to append-only
## 证据核验                  # Success Criteria → proof (propose seeds it, apply fills it)
## 方案审查 — 第 N 轮        # written by fullstack-propose (Step 4.5)
## 设计复核（可选，作者自审，非门禁）   # optional author self-check — never authoritative
## 代码审查 — <repo> — 第 N 轮   # written by fullstack-apply (Step 4d)
## 跨仓库一致性审查           # written by fullstack-apply (Step 5)
## 最终结论                  # the item's closing verdict
```

Rules:

- Sections are **appended in this order** — never insert a new round above
  an older one.
- Round numbers are per-prefix and monotonic: `方案审查` rounds run
  1..N on their own, `代码审查` rounds restart at 1 per repo.
- Existing rounds are historical record: never renumber or rewrite one.
  Correct an error with a dated errata note inside the same section.
- A `设计复核` section is the author's own pre-check. It is a working
  artifact, not a gate: its verdict never substitutes for a
  `方案审查` round.

### Status overview — `## 状态速览` / `## Status Overview`

Sits between the header and the Evidence table. It is the one section of
`review.md` that is **updated in place** — the single exception to the
append-only rule above. The orchestrator rewrites it whenever a verdict
lands: after each plan-review round, after each code-review round, when
a risk opens or closes, and at finalization. It always states the
current position, never the history — history lives in the rounds
below. Four lines, in the work item's language:

- **最新结论 / Latest verdict** — <方案审查 PASS_WITH_RISKS（第 N 轮）| 已完成——最终结论见文末>
- **审查轮次 / Review rounds** — <方案审查 N 轮；代码审查 M 轮（repo 名）>
- **活风险 / Active risks** — <N 项，每项一行：编号（人话描述，怎么跟进）>
- **待决策 / Open decisions** — <无 | 列表>

Everything below this section stays append-only, as before.

## Per-repo staged review section (code review)

Appended once per repo per review round. The full
`code-review-staged` output is preserved verbatim — do not summarize.

### English

```markdown
## Code Review — <repo> — Round <N> — <date>

### Staged Review Output

<Full output from code-review-staged, preserving all sections>

### Verdict

<PASS | NEEDS_FIXES> — <one-line summary>

### Commits

| Hash | Message |
|------|---------|
| `abc1234` | feat: add dark mode toggle |

### Document Sync

**Document Sync**: `analysis.md` — <what this round invalidated, or why
nothing changed>; `plan.md` — <…>; `progress.md` — <…>; `review.md` — <…>
```

### Chinese

```markdown
## 代码审查 — <repo> — 第 <N> 轮 — <date>

### 暂存区审查输出

<code-review-staged 的完整输出，保留所有章节>

### 结论

<PASS | NEEDS_FIXES> — <一句话总结>

### 提交记录

| Hash | Message |
|------|---------|
| `abc1234` | feat: add dark mode toggle |

### 文档同步

**文档同步**：`analysis.md` —— <本轮推翻了什么，或为何无需改动>；
`plan.md` —— <…>；`progress.md` —— <…>；`review.md` —— <…>
```

> Items created before this convention used `## <repo> — Review Round <N>`.
> Leave them as they are; only new rounds use the prefixed form.

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

### Document Sync section rules

The `### Document Sync` / `### 文档同步` line states what happened to each
of the four documents in the round that writes it. It is appended right
after `### Commits` (or after `### 结论` / `### Verdict` when the round
made no commit).

- **Name all four documents** — `analysis.md`, `plan.md`, `progress.md`,
  `review.md` — each followed by one clause. A name with no clause is
  not an answer; the line exists to force the judgement, not to be
  filled in.
- **"Small change" is not a reason to skip `analysis.md`.** It is a
  legitimate answer only when it says why（例如"仅修正变量名，结构与流程
  未变"）。
- **`analysis.md` is the document that goes stale most often and least
  visibly.** It holds the as-is architecture, the target architecture,
  the user flow, and the cross-repo impact — plus the diagrams that draw
  them. Any round that moves a responsibility between modules or layers,
  changes the order of calls, adds or removes a component, or alters a
  frozen contract makes one of those sections **false**. Rewrite the
  affected section and its diagram.
- **Rewrite, do not append a correction.** Adding "补充：实际上……" under a
  heading whose body still says the opposite leaves two contradictory
  claims in one document, and the next reader cannot tell which is
  current. The only exception is a section explicitly marked as a
  historical record.
- **A diagram that no longer matches the code is worse than no diagram**
  — it is read as authoritative. Update it in the same pass, and re-run
  the Mermaid gate after editing it.
- **Do not back-fill old rounds.** `plan_lint.py` check 10 requires the
  line on the **newest** code-review round — the one being written now —
  and on every later round once the item uses the line. Rounds that
  predate it stay as they are: writing an attestation for a round you did
  not run would be inventing history.

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

## Closing verdict — `## 最终结论` / `## Final Verdict`

The item's closing verdict is a **fixed four-item list** — a reader
finishes the work item knowing what shipped, what did not, what is
still open, and what is on them. Write it in the work item's language;
do not add or drop rows. Everything a reader might need beyond these
four (evidence, rounds, per-repo detail) stays in the sections above.

### Chinese

```markdown
## 最终结论

| 项 | 内容 |
|----|------|
| 交付了什么 | <一段人话 + 提交哈希> |
| 明确没交付什么 | <排除项——及原因/去向> |
| 残留风险与待办 | <逐条：谁在什么条件下跟进> |
| 需要人做的事 | <无 | 清单> |
```

### English

```markdown
## Final Verdict

| Item | Content |
|------|---------|
| What was delivered | <plain-language paragraph + commit hashes> |
| Explicitly not delivered | <exclusions — and why / where they went> |
| Residual risks & follow-ups | <one line each: who follows up under what condition> |
| What the human must do | <none | list> |
```

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
