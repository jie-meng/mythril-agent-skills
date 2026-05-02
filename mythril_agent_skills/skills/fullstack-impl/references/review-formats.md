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
```

### Chinese

```markdown
## <repo> — 第 <N> 轮审查 — <date>

### 暂存区审查输出

<code-review-staged 的完整输出，保留所有章节>

### 结论

<PASS | NEEDS_FIXES> — <一句话总结>
```

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
`analysis.md`'s Design Options. See [`followup-mode.md`](followup-mode.md).

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
