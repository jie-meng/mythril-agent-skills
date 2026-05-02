---
name: code-review-staged
description: |
  Context-aware code review for git STAGED changes (git diff --cached).
  Triggers when user mentions "暂存" (staged) with any review verb: 审查/评审/看/检查.
  Examples: '审查暂存', '评审暂存', '看看暂存', '看一下暂存', '检查暂存', '暂存区审查',
  '看一下暂存代码', '看看暂存的代码', '审查暂存代码', '检查暂存代码'.
  English triggers: 'review staged', 'staged code review', 'check staged', 'look at staged',
  'look at staged code', 'review staged code'.
  Reads related files to validate changes in context. Auto-generates commit message.
  ONLY reviews staged changes, NOT unstaged or all changes.
license: Apache-2.0
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review STAGED git changes:**

Chinese (关键词"暂存" + 动词: 审查/评审/看/检查):
- "审查暂存" / "审查暂存区" / "审查暂存的代码" / "暂存区审查" / "暂存区代码审查"
- "评审暂存" / "评审暂存区"
- "看看暂存" / "看一下暂存" / "看看暂存区" / "看一下暂存区"
- "检查暂存" / "检查暂存区"

English:
- "review staged" / "review staged changes" / "staged code review" / "staged CR"
- "check staged" / "look at staged" / "review cached changes"

**This skill is specifically for STAGED changes (git diff --cached).**
For remote GitHub PRs, use `github-code-review-pr` instead.

# Requirements

- **Working directory**: Must be inside a git repository
- **Review language**: Match the user's input language (Chinese or English)
- **Commit message**: Always in English, single line, max 72 characters

# Implementation

The skill executes these steps:

## Step 1: Get Staged Changes and Branch Info

Run these commands concurrently:

```bash
git diff --cached
git rev-parse --abbrev-ref HEAD
```

If no staged changes found, report and suggest `git add`.

## Step 2: Gather Repository Context

Since we're already inside the repository, context gathering is cheap and fast — just local file reads.

### 2a. Project structure overview

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the project's module organization, naming conventions, and architecture without reading any file content.

### 2b. Coding conventions and config files

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

### 2c. Full content of modified files

Read the **full content** of staged files to understand complete context around changes. Use a **change-volume driven** strategy instead of a fixed file count:

- **> 50 lines changed** (additions + deletions): Must read full file — major changes require complete context
- **5-50 lines changed**: Read full file — surrounding code is important for correctness judgment
- **< 5 lines changed**: The diff alone may suffice; skip full read unless the change is in a critical path (e.g., security, auth, financial logic)
- **New files**: Always read in full (subject to the size limit below)
- **Skip binary files** and **very large files** (>100KB) — only use the diff for those. This size limit applies to ALL files, including new files

### 2d. Related files not in the diff (targeted)

Analyze the diff to determine if files NOT in the staged changes need to be read for a high-quality review:

- **When to read context**:
    - If a function signature changes, check its callers or definition
    - If a class inherits from a base class not in diff, read the base class definition
    - If a variable type is unclear, check its declaration
    - If a config value changes, check where it's consumed if the impact is ambiguous
    - **Header/Source Pairing**: For C/C++, always check the corresponding `.h` or `.cpp` file if one is modified
    - **Tests**: Check if existing tests need updates or if new tests are consistent with existing patterns
- **Constraints**:
    - Read **3-5** related files that are strictly necessary to validate the correctness of the staged changes
    - If a file is huge, read only relevant sections

## Step 3: Detect Language

Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review
- Commit message always in English

## Step 4: Perform Code Review

Structure the review into these sections:

### If Chinese review requested:

#### 1. 变更概览
- 此 diff 主要做了什么（修复 bug、添加功能、重构、配置变更等）
- 变更规模和受影响的主要模块
- 项目的编码规范和风格（基于 config 文件和已有代码推断）
- 此变更是否符合项目整体风格和架构模式

#### 2. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 特别关注：变更是否与项目现有代码风格一致（命名惯例、代码组织方式、错误处理模式等）
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（行号/文件名/代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

#### 3. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 检查是否有遗漏的修改（如：改了接口但没改调用方，改了 schema 但没改迁移）
- 指出这些疑点，并简单说明为何值得关注

#### 4. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议
- 建议是否需要补充测试、文档、类型声明等

#### 5. 推荐提交信息
- **严格遵循 [`references/commit-format.md`](references/commit-format.md)** 的格式规范 — 这是单一事实来源
- 提交信息使用英文，单行，最多 72 字符，subject 使用动词原形开头
- scope 必须从 branch name 自动推导，**禁止使用 repo 名当 scope**
- 关键规则速查（完整规则见 commit-format.md）：
  - 分支 `<type>/<JIRA>/<Title>` → scope = JIRA key（如 `feat[XYZ-190]: add export endpoint`）
  - 分支 `<type>/<Title>` 且 title ≤ 30 字符 → scope = lowercase-hyphenated title
  - 分支 `<type>/<Title>` 且 title > 30 字符 → 按 commit-format.md 的"Long-title compression"压缩
  - `-iter-N` 后缀**不**进 scope；`-vN` 后缀**保留**在 scope 中
  - 默认分支（master/main/dev）或无 `/` 分支 → 不带 scope，用 `type: subject`
  - scope + 模板字符 + subject 总长超 72 字符时，丢掉 scope 优先保 subject

### If English review requested:

#### 1. Change Overview
- What this diff does (bug fix, feature, refactor, config change, etc.)
- Change scope and primary modules affected
- Project coding conventions and style (inferred from config files and existing code)
- Whether this change aligns with the project's overall style and architectural patterns

#### 2. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments, readability, maintainability, architecture, modularity, code duplication, etc.
- Pay special attention to: whether changes are consistent with existing project code style (naming conventions, code organization, error handling patterns, etc.)
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or violations of best practices
- Clearly specify the exact location and nature of each problem (line number, filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization with explanatory reasoning

#### 3. Major Issues and Risks
- Evaluate hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, security vulnerabilities
- Check for missed changes (e.g., changed an interface but not its callers, changed a schema but not its migration)
- Point out suspicious areas and explain their potential impact

#### 4. Incremental Suggestions
- Suggestions for improving code quality, maintainability, and test coverage
- Whether additional tests, documentation, or type annotations are needed

#### 5. Recommended Commit Message
- **Strictly follow [`references/commit-format.md`](references/commit-format.md)** — it is the single source of truth
- English, single line, max 72 characters, subject in imperative mood
- Scope MUST be auto-derived from the branch name; **NEVER use the repo name as scope**
- Quick rules (full rules in commit-format.md):
  - Branch `<type>/<JIRA>/<Title>` → scope = JIRA key (e.g. `feat[XYZ-190]: add export endpoint`)
  - Branch `<type>/<Title>` with title ≤ 30 chars → scope = lowercase-hyphenated title
  - Branch `<type>/<Title>` with title > 30 chars → apply "Long-title compression" from commit-format.md
  - `-iter-N` suffix is **stripped** from scope; `-vN` suffix is **kept** in scope
  - Bare branches (master/main/dev) or branches without `/` → no scope, use `type: subject`
  - When `scope + template chars + subject` would exceed 72 chars, drop scope to preserve subject

## Error Handling

- **No staged changes**: Report that no staged changes found and suggest using `git add`
- **Not a git repo**: Report and suggest navigating to a git repository
- **Language detection failure**: Default to English review
- **Large diff (>50 files)**: Warn the user; focus on the most critical files

## Examples

### Example 1: Chinese Request
**User input**: "审查暂存区的代码"
**Branch**: `feat/audio-support`
**Action**: Get staged diff → gather repo context locally → review in Chinese
**Output**: Context-aware Chinese review with recommended commit message

### Example 2: English Request
**User input**: "Review my staged changes"
**Branch**: `fix/wifi-connection`
**Action**: Get staged diff → gather repo context locally → review in English
**Output**: Context-aware English review with recommended commit message
