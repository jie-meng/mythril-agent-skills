---
name: branch-diff-review
description: |
  Context-aware code review for branch differences — compare any two local git branches
  without relying on GitHub, GitLab, Bitbucket, or any platform API. Pure local git operations.
  Ideal for non-GitHub repos (Gitee, Bitbucket, self-hosted GitLab, etc.) or offline review.
  Triggers when user mentions branch comparison with any review verb.
  Examples: 'review feat/123 合到 main', 'branch diff review', 'branch review',
  '分支合并审查', '看一下 dev 和 main 的差异', 'review branch merge',
  'compare branches for review', 'review branch changes',
  '帮我 review 一下这两个分支', 'review feat/xxx to master',
  'branch code review', '分支审查', '分支 review', '分支CR'.
  Does NOT require any platform CLI or API — works with any git repository.
license: Apache-2.0
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review differences between two git branches:**

Chinese:
- "review feat/123 合到 main" / "看一下 dev 和 main 的差异"
- "分支合并审查" / "分支审查" / "分支 review" / "分支 CR"
- "帮我 review 一下这两个分支" / "帮我看一下这两个分支的差异"
- "看看 feature 分支改了什么" / "分支代码审查"

English:
- "branch diff review" / "branch review" / "branch code review"
- "review feat/xxx to master" / "review branch merge feat/123 to main"
- "compare branches for review" / "review branch changes"
- "review the diff between these two branches"

**This skill is for comparing any two git branches using pure local git operations.**
- No platform API needed — works with any git remote (GitHub, GitLab, Gitee, Bitbucket, self-hosted, etc.)
- For GitHub PR reviews, use `github-code-review-pr` instead.
- For staged changes, use `code-review-staged` instead.

# Requirements

- **Working directory**: Must be inside a git repository
- **Branches**: Both branches must exist locally (or have remote tracking branches that can be checked out)
- **User responsibility**: User ensures branches are up-to-date before review (no automatic fetch/pull)
- **Review language**: Match the user's input language (Chinese or English)

# Implementation

The skill executes these steps:

## Step 1: Determine Source and Target Branches

### 1a. Parse user input

Extract two branches from the user's request:
- **Source branch** (feature branch, the branch being merged): the branch with new changes
- **Target branch** (base branch, the branch being merged into): typically `main` or `master`

User may specify branches in various formats:
- "review `feat/123` 合到 `main`" → source: `feat/123`, target: `main`
- "review `feat/auth` to `master`" → source: `feat/auth`, target: `master`
- "看一下 `dev` 和 `main` 的差异" → source: `dev`, target: `main`
- "branch review `release/2.0` → `main`" → source: `release/2.0`, target: `main`

### 1b. Auto-detect if not fully specified

If the user doesn't specify both branches:
- **No source specified**: Use the current branch (`git rev-parse --abbrev-ref HEAD`) as source
- **No target specified**: Auto-detect the default branch — try `main`, then `master`, then the remote HEAD
- **Neither specified**: Use current branch as source, auto-detect target, then **ask the user to confirm** before proceeding

Auto-detect default branch:
```bash
git rev-parse --verify main 2>/dev/null && echo main || \
git rev-parse --verify master 2>/dev/null && echo master || \
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
```

### 1c. Record the current branch

Save the current branch name so we can verify we haven't moved at the end:
```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

**CRITICAL**: The user's current branch MUST remain unchanged throughout the entire review process. Do NOT checkout any branch. All operations use `git diff`, `git log`, and `git show` with explicit branch references — no checkout needed.

## Step 2: Validate Branches Exist Locally

Check if both branches exist locally:
```bash
git rev-parse --verify <source> 2>/dev/null
git rev-parse --verify <target> 2>/dev/null
```

If a branch does NOT exist locally but has a remote tracking branch:
```bash
git branch --track <branch> origin/<branch>
```

If a branch doesn't exist locally AND has no remote tracking branch → report error and stop.

**IMPORTANT**: Do NOT run `git fetch`, `git pull`, or `git checkout`. Work with whatever is already local. The user is responsible for ensuring branches are current.

## Step 3: Get Branch Diff and Commit History

Run these commands concurrently:

### 3a. Three-dot diff (semantic: "what did source add since diverging from target")
```bash
git diff <target>...<source>
```
This is equivalent to a PR diff — it shows only the changes introduced on the source branch since it diverged from the target.

### 3b. Commit history on the source branch since divergence
```bash
git log <target>..<source> --oneline --no-merges
```

### 3c. Changed file list with stats
```bash
git diff <target>...<source> --stat
```

If no diff is found, report that the branches are identical and stop.

## Step 4: Gather Repository Context

Since we're inside the repository, context gathering is cheap and fast — just local file reads and git commands. No branch switching needed.

### 4a. Project structure overview

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the project's module organization, naming conventions, and architecture without reading any file content.

### 4b. Coding conventions and config files

Read key project files (if they exist) to understand coding standards. Prioritize by relevance to the changed files' languages.

**AI agent instruction files** (highest priority — these define project conventions explicitly):

| File | Tool |
|---|---|
| `AGENTS.md` | Cross-tool standard (Codex, Cursor, Copilot, Amp, Windsurf, Devin) |
| `CLAUDE.md` | Claude Code |
| `GEMINI.md` | Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursorrules` / `.cursor/rules/` | Cursor |
| `.windsurfrules` / `.windsurf/rules/` | Windsurf |

**Project and build config files**:

| File | Purpose |
|---|---|
| `README.md` | Project overview |
| `CONTRIBUTING.md` | Development guidelines, contribution rules |
| `pyproject.toml` / `setup.cfg` | Python project config, linting rules |
| `package.json` | Node.js project config, lint config |
| `.editorconfig` | Editor formatting rules |
| `.eslintrc.*` / `biome.json` | JS/TS linting rules |
| `Makefile` / `Justfile` | Build conventions |
| `Cargo.toml` | Rust project config |
| `go.mod` | Go module config |
| `.clang-format` / `.clang-tidy` | C/C++ formatting rules |

**Constraints:**
- Read at most 3-5 config files — prioritize the ones most relevant to the changed files' languages
- Skim only; skip files larger than ~50KB

### 4c. Full content of modified files

Read the **full content** of modified files from the **source branch** to understand complete context around changes. Use `git show` to read files without switching branches:

```bash
git show <source>:<filepath>
```

- **Prioritize**: Read the top 5-8 most important modified files (by relevance, not just size)
- **Skip binary files** and **very large files** (>100KB) — only use the diff for those
- **For files with few changes** (< 5 lines added/deleted): The diff alone may suffice; skip full read
- **Focus on**: Files with substantive logic changes, new files, and files with the most additions

### 4d. Related files not in the diff (targeted)

If the diff references imports, base classes, interfaces, or function calls from files NOT in the diff:

```bash
git show <source>:<related-filepath>
```

- Read **at most 2-3** related files for understanding correctness
- Only read files that are strictly necessary to validate the correctness of the changes

## Step 5: Detect Language

Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review

## Step 6: Perform Code Review

Structure the review into these sections:

### If Chinese review requested:

#### 1. 分支差异概览
- 此次合并的目的和动机（基于分支名、commit 历史推断）
- Source 分支: `<source>`, Target 分支: `<target>`
- 变更规模：X 个文件，+Y / -Z 行，N 个 commits
- 涉及的主要模块和功能领域

#### 2. 仓库上下文分析
- 项目技术栈（语言、框架、工具链）
- 项目的编码规范和风格（基于 config 文件和已有代码推断）
- 此变更是否符合项目整体风格和架构模式

#### 3. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 特别关注：变更是否与项目现有代码风格一致（命名惯例、代码组织方式、错误处理模式等）
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（文件名、代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

#### 4. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 检查是否有遗漏的修改（如：改了接口但没改调用方，改了 schema 但没改迁移）
- 指出这些疑点，并简单说明为何值得关注

#### 5. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议
- 建议是否需要补充测试、文档、类型声明等

#### 6. 总结评价
- 给出整体评价：**Approve** / **Request Changes** / **Comment**
- 简要总结关键发现和建议优先级

### If English review requested:

#### 1. Branch Diff Overview
- Purpose and motivation of the merge (inferred from branch names, commit history)
- Source branch: `<source>`, Target branch: `<target>`
- Change scope: X files changed, +Y / -Z lines, N commits
- Primary modules and functional areas affected

#### 2. Repository Context Analysis
- Project tech stack (languages, frameworks, toolchain)
- Project coding conventions and style (inferred from config files and existing code)
- Whether these changes align with the project's overall style and architectural patterns

#### 3. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments, readability, maintainability, architecture, modularity, code duplication, etc.
- Pay special attention to: whether changes are consistent with existing project code style (naming conventions, code organization, error handling patterns, etc.)
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or violations of best practices
- Clearly specify the exact location and nature of each problem (filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization with explanatory reasoning

#### 4. Major Issues and Risks
- Evaluate hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, security vulnerabilities
- Check for missed changes (e.g., changed an interface but not its callers, changed a schema but not its migration)
- Point out suspicious areas and explain their potential impact

#### 5. Incremental Suggestions
- Suggestions for improving code quality, maintainability, and test coverage
- Whether additional tests, documentation, or type annotations are needed

#### 6. Summary Verdict
- Overall assessment: **Approve** / **Request Changes** / **Comment**
- Brief summary of key findings and suggestion priorities

## Step 7: Verify Current Branch Unchanged

**This step is MANDATORY — always execute it after review.**

Verify the user is still on the same branch they started on:
```bash
[ "$(git rev-parse --abbrev-ref HEAD)" = "$CURRENT_BRANCH" ] && echo "OK: still on $CURRENT_BRANCH" || echo "ERROR: branch changed!"
```

If for any reason the branch changed (it shouldn't with this workflow), restore it:
```bash
git checkout "$CURRENT_BRANCH"
```

## Error Handling

- **Not a git repo**: Report and suggest navigating to a git repository
- **Branch not found**: Report which branch doesn't exist; suggest `git branch -a` to list available branches
- **No diff between branches**: Report that branches are identical — nothing to review
- **Detached HEAD**: If the user is on a detached HEAD, record the commit hash instead of branch name for restoration
- **Large diff (>50 files)**: Warn the user; focus on the most critical files
- **Binary files**: Skip binary files in review, note them as present
- **Language detection failure**: Default to English review

## Examples

### Example 1: Explicit branches (Chinese)
**User input**: "帮我 review 一下 feat/user-auth 合到 main"
**Action**: source=`feat/user-auth`, target=`main` → validate branches → `git diff main...feat/user-auth` → gather context → Chinese review
**Output**: 6-section Chinese review with verdict

### Example 2: Explicit branches (English)
**User input**: "branch review release/2.0 to master"
**Action**: source=`release/2.0`, target=`master` → validate → diff → context → English review
**Output**: 6-section English review with verdict

### Example 3: Only source specified
**User input**: "review feat/payment 这个分支"
**Action**: source=`feat/payment`, target=auto-detect (`main` or `master`) → confirm with user → review
**Output**: Context-aware review

### Example 4: No branches specified
**User input**: "branch diff review"
**Action**: source=current branch, target=auto-detect → **ask user to confirm** → review
**Output**: Review of current branch vs default branch

### Example 5: Branch not local
**User input**: "review feat/remote-feature 合到 main"
**Action**: `feat/remote-feature` not local → check `origin/feat/remote-feature` exists → `git branch --track feat/remote-feature origin/feat/remote-feature` → proceed with review
**Output**: Review after creating local tracking branch
