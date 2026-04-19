#!/usr/bin/env python3
"""Initialize or update a multi-repo fullstack workspace.

Scans a root directory for git repositories, analyzes their README.md and
AGENTS.md files, and generates workspace-level infrastructure: AGENTS.md,
agent templates, and shared docs directory.

Design: every run is a full refresh. AGENTS.md, README.md, and agent
templates are regenerated from scratch. The only persistent state is
fullstack.json (stores docs_dir). The docs directory and user directories
(scripts/, .agents/skills/) are created if missing but never overwritten.

The workspace root is NOT a git repo — no .gitignore, no .git. This is
intentional: all major AI agents (Cursor, Claude Code, Copilot, Codex,
Gemini CLI, etc.) respect .gitignore and hide ignored files from their
search/indexing tools. Since the workspace contains independent repos as
subdirectories, a .gitignore that hides them would make their files
invisible to AI agents. The docs directory is the only workspace-managed
git repo.

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "fullstack.json"
LEGACY_CONFIG_FILENAME = ".fullstack-init.json"

DEFAULT_DOCS_DIR = "central-docs"

INFRA_DIRS = {
    ".agents",
    "scripts",
    "node_modules",
    "__pycache__",
}


# ---------------------------------------------------------------------------
# Config persistence (fullstack.json is the ONLY persistent state)
# ---------------------------------------------------------------------------

def load_config(root: Path) -> dict[str, str]:
    """Load workspace config from fullstack.json (with legacy fallback)."""
    config_path = root / CONFIG_FILENAME
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    legacy_path = root / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        try:
            return json.loads(legacy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(root: Path, config: dict[str, str]) -> None:
    """Save workspace config to fullstack.json (removes legacy file if present)."""
    config_path = root / CONFIG_FILENAME
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    legacy_path = root / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        legacy_path.unlink()


def resolve_docs_dir(root: Path, cli_docs_dir: str | None) -> str:
    """Determine docs dir: CLI arg > saved config > default."""
    if cli_docs_dir:
        return cli_docs_dir
    config = load_config(root)
    saved = config.get("docs_dir")
    if saved:
        return saved
    return DEFAULT_DOCS_DIR


# ---------------------------------------------------------------------------
# Repo discovery and analysis
# ---------------------------------------------------------------------------

def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def discover_repos(root: Path, docs_dir: str) -> list[Path]:
    """Find all immediate subdirectory git repos under root."""
    exclude = INFRA_DIRS | {docs_dir}
    repos = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in exclude:
            continue
        if is_git_repo(entry):
            repos.append(entry)
    return repos


def detect_tech_stack(repo_path: Path) -> str:
    """Detect primary tech stack from common config files."""
    indicators: list[tuple[str, str]] = [
        ("package.json", "JavaScript/TypeScript"),
        ("tsconfig.json", "TypeScript"),
        ("Podfile", "iOS (Swift/ObjC)"),
        ("build.gradle", "Android (Kotlin/Java)"),
        ("build.gradle.kts", "Android (Kotlin)"),
        ("requirements.txt", "Python"),
        ("pyproject.toml", "Python"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("pom.xml", "Java"),
        ("Gemfile", "Ruby"),
        ("composer.json", "PHP"),
        ("pubspec.yaml", "Flutter/Dart"),
        ("*.csproj", "C# / .NET"),
        ("CMakeLists.txt", "C/C++"),
    ]
    found = []
    for filename, tech in indicators:
        if "*" in filename:
            if list(repo_path.glob(filename)):
                found.append(tech)
        elif (repo_path / filename).exists():
            found.append(tech)
    return ", ".join(found[:3]) if found else "—"


def extract_repo_description(repo_path: Path) -> str:
    """Extract a one-line description from README.md or AGENTS.md."""
    for filename in ("README.md", "AGENTS.md"):
        filepath = repo_path / filename
        if not filepath.exists():
            continue
        text = filepath.read_text(encoding="utf-8", errors="replace")
        desc = _extract_first_description(text)
        if desc:
            return desc
    return "—"


def _extract_first_description(text: str) -> str:
    """Extract the first meaningful paragraph after the H1 heading."""
    lines = text.split("\n")
    past_h1 = False
    for line in lines:
        stripped = line.strip()
        if not past_h1:
            if stripped.startswith("# "):
                past_h1 = True
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        if stripped.startswith(("![", "<", "```", "|", "---", "- ", "* ")):
            continue
        desc = stripped.rstrip(".")
        if len(desc) > 120:
            desc = desc[:117] + "..."
        return desc
    return ""


def detect_repo_role(repo_path: Path) -> str:
    """Infer the repo's role/platform from its name and contents."""
    name = repo_path.name.lower()
    role_keywords: list[tuple[list[str], str]] = [
        (["web", "frontend", "fe", "webapp", "dashboard", "portal"], "Web Frontend"),
        (["api", "backend", "server", "service", "gateway"], "Backend / API"),
        (["ios", "apple"], "iOS"),
        (["android"], "Android"),
        (["mobile", "app"], "Mobile"),
        (["infra", "devops", "deploy", "k8s", "terraform", "helm"], "Infrastructure"),
        (["shared", "common", "lib", "sdk", "core", "pkg", "packages"], "Shared Library"),
        (["docs", "doc", "documentation", "wiki"], "Documentation"),
        (["design", "figma", "sketch"], "Design"),
        (["data", "ml", "ai", "model", "pipeline"], "Data / ML"),
        (["test", "e2e", "qa", "integration-test"], "Testing"),
        (["config", "env", "setup"], "Configuration"),
    ]
    for keywords, role in role_keywords:
        for kw in keywords:
            if kw in name:
                return role
    return "—"


def analyze_repo(repo_path: Path) -> dict[str, str]:
    """Analyze a single repo and return its metadata."""
    return {
        "name": repo_path.name,
        "description": extract_repo_description(repo_path),
        "tech_stack": detect_tech_stack(repo_path),
        "role": detect_repo_role(repo_path),
    }


# ---------------------------------------------------------------------------
# Content generation (all pure functions — no side effects)
# ---------------------------------------------------------------------------

def build_repos_table(repos: list[dict[str, str]]) -> str:
    """Build a Markdown table from repo metadata."""
    lines = [
        "| # | Repository | Role | Tech Stack | Description |",
        "|---|-----------|------|-----------|-------------|",
    ]
    for i, repo in enumerate(repos, 1):
        lines.append(
            f"| {i} | [{repo['name']}](./{repo['name']}/) "
            f"| {repo['role']} "
            f"| {repo['tech_stack']} "
            f"| {repo['description']} |"
        )
    return "\n".join(lines)


def generate_agents_md(
    project_name: str,
    repos_table: str,
    docs_dir: str,
) -> str:
    """Generate the workspace-level AGENTS.md (always from scratch)."""
    return f"""\
# {project_name}

## Project Overview

This is a multi-repo fullstack workspace. Every subdirectory — including
`{docs_dir}/` — is an independent git repository with its own version control.

## Repositories

{repos_table}

## Workspace Conventions

- **Cross-repo changes**: When making changes that span multiple repos,
  commit and test each repo independently.
- **Shared documentation**: Cross-cutting docs live in `{docs_dir}/`
  (its own git repo — NOT managed by the workspace git).
- **Scripts**: Workspace-level automation lives in `scripts/`.
- **Agent delegation**: Workspace-level agents live in `.agents/agents/`.
  When working inside a specific repo that has its own `.agents/agents/`,
  prefer using the repo-level agents for that repo's code.

## Work Tracking

When starting any cross-repo work, create a work directory under
`{docs_dir}/` in the appropriate category:

| Category | Directory | Branch prefix | Use for |
|----------|-----------|--------------|---------|
| Feature | `{docs_dir}/feat/<name>/` | `feat/` | New features, capabilities |
| Refactor | `{docs_dir}/refactor/<name>/` | `refactor/` | Code restructuring, tech debt |
| Fix | `{docs_dir}/fix/<name>/` | `fix/` | Bug fixes, issue resolution |

Each work directory contains:

```
<category>/<work-name>/
├── analysis.md        # Technical analysis (architecture, root cause, design options)
├── plan.md            # Implementation plan (repos involved, tasks, approach)
├── progress.md        # Current status, completed steps, blockers
└── review.md          # Review findings and fix history (append-only)
```

Work directories are **never deleted** — they serve as project history.
The `{docs_dir}/` repo does NOT use feature branches — all work tracking
docs are committed directly to its main branch.

## Branch Naming Convention

When implementing work items, create branches in each affected repo:

| Category | Without Jira | With Jira |
|----------|-------------|-----------|
| Feature | `feat/Import-Export` | `feat/XYZ-706/Import-Export` |
| Refactor | `refactor/Refine-Models` | `refactor/XYZ-707/Refine-Models` |
| Fix | `fix/iPad-Ble-Not-Working` | `fix/XYZ-708/iPad-Ble-Not-Working` |

Branch names use Title-Case-With-Hyphens for the descriptive part.

## Directory Structure

```
{project_name}/
├── AGENTS.md          # This file (regenerated by fullstack-init)
├── README.md          # Human-readable project overview (regenerated)
├── fullstack.json     # Workspace config — the only persistent state
├── .agents/
│   ├── agents/        # Workspace-level sub-agents (regenerated)
│   │   ├── planner.md
│   │   ├── developer.md
│   │   ├── reviewer.md
│   │   └── debugger.md
│   └── skills/        # Custom skills for this workspace (preserved)
├── scripts/           # Workspace-level automation scripts (preserved)
├── {docs_dir + "/":<23s}# Shared docs (independent git repo, preserved)
│   ├── AGENTS.md
│   ├── feat/
│   ├── refactor/
│   └── fix/
├── web/               # ← Independent git repo (example)
├── api/               # ← Independent git repo (example)
└── ios/               # ← Independent git repo (example)
```
"""


def detect_language(text: str) -> str:
    """Detect language from text. Returns 'zh' if Chinese characters found, else 'en'."""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return "zh"
    return "en"


def generate_readme(project_name: str, docs_dir: str, lang: str = "en") -> str:
    """Generate the workspace README.md with usage guide."""
    if lang == "zh":
        return _generate_readme_zh(project_name, docs_dir)
    return _generate_readme_en(project_name, docs_dir)


def _generate_readme_en(project_name: str, docs_dir: str) -> str:
    """Generate English README."""
    return f"""\
# {project_name}

Multi-repo fullstack workspace managed by
[mythril-agent-skills](https://github.com/jie-meng/mythril-agent-skills)
fullstack skills.

## Quick Start

> **Important**: Always launch your AI agent from the workspace root
> directory (where `fullstack.json` lives). The fullstack skills will not
> work if started from a subdirectory or outside the workspace.

### Initialize the workspace

Run `fullstack-init` when setting up for the first time or after adding /
removing repositories:

```
> Initialize this fullstack workspace
```

This discovers all git repos, generates `AGENTS.md`, agent templates, and
sets up the shared documentation directory (`{docs_dir}/`).

Re-running is safe — it refreshes generated files while preserving your
docs, scripts, and custom skills.

### Implement a feature / refactor / fix

Use `fullstack-impl` to start cross-repo work:

```
> Implement the dark mode feature (Jira: PROJ-123)
> Refactor the authentication module across all services
> Fix the login crash on empty password
```

You can include links to Jira tickets, Confluence pages, GitHub issues, or
Figma designs — the skill will gather context from all of them before
planning.

The skill will:

1. Gather context from linked resources
2. Identify affected repos and propose branches
3. Ask for your confirmation
4. Create a work plan in `{docs_dir}/`
5. Implement changes repo by repo (in dependency order)
6. Run tests and linting in each repo
7. Review changes for cross-repo consistency

### Resume previous work

If a session was interrupted, start a new session and tell the agent to
continue:

```
> Continue the dark mode feature
> Resume work on PROJ-123
> Check the docs and keep going
```

The skill reads `{docs_dir}/` for existing plans and progress, detects
which branches are already checked out, and picks up where it left off.

## Workspace Structure

```
{project_name}/
├── fullstack.json     # Workspace config (do not delete)
├── AGENTS.md          # AI agent context (regenerated by fullstack-init)
├── README.md          # This file (regenerated by fullstack-init)
├── .agents/
│   ├── agents/        # Workspace-level AI agents (regenerated)
│   └── skills/        # Custom skills (preserved across runs)
├── {docs_dir + "/":<23s}# Shared docs — independent git repo
│   ├── feat/          #   Feature work tracking
│   ├── refactor/      #   Refactor work tracking
│   └── fix/           #   Fix work tracking
├── scripts/           # Workspace-level scripts (preserved)
└── <repos...>/        # Your git repositories
```

## Work Tracking

Every cross-repo work item gets its own directory under `{docs_dir}/`:

```
{docs_dir}/<type>/<work-name>/
├── plan.md            # What to do, which repos, in what order
├── progress.md        # What's done, what's in progress, blockers
└── review.md          # Review findings and fix history
```

These are never deleted — they serve as project history.

## Documentation

- **Workspace AGENTS.md** — Cross-repo context and conventions for AI agents
- **`{docs_dir}/AGENTS.md`** — Documentation conventions
- **Repo-level AGENTS.md** — Each repo's own coding standards and build instructions
"""


def _generate_readme_zh(project_name: str, docs_dir: str) -> str:
    """Generate Chinese README."""
    return f"""\
# {project_name}

由 [mythril-agent-skills](https://github.com/jie-meng/mythril-agent-skills)
fullstack 技能管理的多仓库全栈工作区。

## 快速上手

> **重要**：请始终在工作区根目录（`fullstack.json` 所在目录）启动你的 AI
> 编程助手。如果在子目录或工作区外启动，fullstack 技能将无法正常工作。

### 初始化工作区

首次使用或增删了子仓库后，运行 `fullstack-init`：

```
> 初始化这个全栈工作区
```

脚本会自动发现所有 git 子仓库、生成 `AGENTS.md`、AI agent 模板，以及共享
文档目录（`{docs_dir}/`）。

重复运行是安全的——会刷新生成的文件，但保留你的文档、脚本和自定义技能。

### 开发新功能 / 重构 / 修复 Bug

使用 `fullstack-impl` 开始跨仓库开发：

```
> 实现暗色模式功能（Jira: PROJ-123）
> 重构所有服务的鉴权模块
> 修复空密码登录崩溃问题
```

你可以在消息中附带 Jira 卡片、Confluence 页面、GitHub Issue 或 Figma 设计
链接——技能会在规划之前自动采集所有相关上下文。

技能会按以下步骤执行：

1. 从链接资源中采集上下文
2. 识别受影响的仓库并提议分支名
3. 等你确认
4. 在 `{docs_dir}/` 中创建工作计划
5. 按依赖顺序逐仓库实现变更
6. 在每个仓库中运行测试和代码检查
7. 跨仓库一致性审查

### 继续上一次的工作

如果上次会话中断了，新建会话后告诉 AI 继续：

```
> 继续暗色模式功能的开发
> 继续 PROJ-123
> 看看文档，接着之前的进度继续
```

技能会读取 `{docs_dir}/` 中已有的计划和进度，检测各仓库当前分支，
从中断处继续。

## 工作区结构

```
{project_name}/
├── fullstack.json     # 工作区配置（请勿删除）
├── AGENTS.md          # AI agent 上下文（fullstack-init 自动生成）
├── README.md          # 本文件（fullstack-init 自动生成）
├── .agents/
│   ├── agents/        # 工作区级 AI agent（自动生成）
│   └── skills/        # 自定义技能（跨运行保留）
├── {docs_dir + "/":<23s}# 共享文档 — 独立 git 仓库
│   ├── feat/          #   功能开发跟踪
│   ├── refactor/      #   重构跟踪
│   └── fix/           #   Bug 修复跟踪
├── scripts/           # 工作区级脚本（跨运行保留）
└── <repos...>/        # 你的各个 git 子仓库
```

## 工作跟踪

每个跨仓库工作项在 `{docs_dir}/` 下都有自己的目录：

```
{docs_dir}/<type>/<work-name>/
├── plan.md            # 做什么、涉及哪些仓库、按什么顺序
├── progress.md        # 已完成、进行中、阻塞项
└── review.md          # 审查发现和修复记录
```

这些目录不会被删除——它们是项目的实施历史记录。

## 文档说明

- **工作区 AGENTS.md** — 跨仓库上下文和 AI agent 约定
- **`{docs_dir}/AGENTS.md`** — 文档编写约定
- **各仓库 AGENTS.md** — 每个仓库自己的编码规范和构建说明
"""


def generate_docs_agents_md(docs_dir: str) -> str:
    """Generate an AGENTS.md for the shared docs directory."""
    title = docs_dir.replace("-", " ").replace("_", " ").title()
    return f"""\
# {title}

This directory is an **independent git repository** that holds shared
documentation spanning all repositories in this workspace. It has its own
version control, separate from the workspace-level git repo.

## Conventions

- Use Markdown for all documents.
- Organize by topic or domain, not by repo.
- Link to repo-specific docs using relative paths: `../repo-name/docs/...`
- Keep documents concise; deep-dive details belong in the relevant repo.
- This repo does NOT use feature branches — commit work tracking docs
  directly to the main branch.

## Work Tracking

The `feat/`, `refactor/`, and `fix/` directories contain per-work-item
documentation created by the `fullstack-impl` skill:

| Directory | Branch prefix | Use for |
|-----------|--------------|---------|
| `feat/` | `feat/` | New features and capabilities |
| `refactor/` | `refactor/` | Code restructuring, tech debt |
| `fix/` | `fix/` | Bug fixes, issue resolution |

Each work item gets its own subdirectory:

```
<category>/<work-name>/
├── plan.md       # Implementation plan
├── progress.md   # Current status and completed steps
└── review.md     # Review findings (append-only)
```

These directories are **never deleted** — they form the project's
implementation history. Do not modify docs created by other work items.

## Structure

```
{docs_dir}/
├── AGENTS.md          # This file
├── feat/              # Feature work tracking
├── refactor/          # Refactor work tracking
├── fix/               # Fix work tracking
├── architecture.md    # System-wide architecture overview (example)
├── api-contracts/     # Shared API schemas, contracts (example)
└── onboarding/        # New-member onboarding guides (example)
```
"""


# ---------------------------------------------------------------------------
# Agent templates
# ---------------------------------------------------------------------------

AGENT_TEMPLATES: dict[str, str] = {}

AGENT_TEMPLATES["planner"] = """\
# Planner — {project_name}

You are **Planner**, the requirements analyst and solution architect for this
workspace.

Your mission is to turn ambiguous requests into clear, actionable, and
verifiable implementation plans before any code is written. Code written
without a plan tends to solve the wrong problem, miss edge cases, or create
architectural debt. You de-risk execution before it starts.

## How you think

Balance two perspectives:

- **Execution** — Can a developer pick this up and implement it in small,
  safe steps? Are the tasks concrete enough to act on without guessing?
- **Architecture** — Are the decisions coherent across repo boundaries?
  Will this approach still make sense in 6 months?

Scale your depth to the problem. A config change doesn't need an architecture
review. A new cross-repo data flow does.

## How you work

1. **Frame the problem** — Clarify goals, constraints, assumptions, and
   non-goals. If information is missing, say what you need.
2. **Identify affected repos** — From the workspace AGENTS.md repo table,
   determine which repos need changes and why.
3. **Propose a direction** — Recommend an approach with trade-offs.
   Consider alternatives and explain your reasoning.
4. **Break into phases** — Concrete tasks per repo with clear dependencies.
   Each phase should be independently verifiable.
5. **Define success** — Testable acceptance criteria, not subjective ones.
6. **Surface risks** — Call out unknowns and cross-repo dependencies.

## What you MUST NOT do

- Do not write implementation code. Your output is `plan.md`, not the solution.
- Do not modify source files. You are a read-only analyst.
- Do not over-plan simple tasks. A brief recommendation is better than a
  10-section document for something straightforward.

## Output

Write the plan to `plan.md` in the work directory. Follow the template
defined in the workspace AGENTS.md.
"""

AGENT_TEMPLATES["developer"] = """\
# Developer — {project_name}

You are **Developer**, the implementation agent for this workspace. You are
the only agent that writes production code, tests, and configuration.

## How you work

1. **Read the plan** — Start from `plan.md`. Understand scope, affected
   repos, dependencies, and acceptance criteria before touching code.
2. **Follow repo conventions** — Before modifying any repo, read its
   `AGENTS.md` and `README.md`. Follow its coding style, test strategy,
   and build instructions exactly.
3. **Implement in dependency order** — Start with shared libraries, then
   backend, then frontend. Cross-repo consistency matters.
4. **Test as you go** — Run each repo's tests after making changes.
   Do not move to the next repo if the current one's tests are broken.
5. **Update progress** — After each meaningful change, update `progress.md`.

## Repo-level agent delegation

If the repo you're modifying has its own `.agents/agents/` with a
specialized dev agent, defer to that agent for the repo's internal
implementation details. You handle cross-repo coordination.

## What you MUST NOT do

- Do not modify `review.md` — that belongs to the reviewer.
- Do not skip tests or linting defined in repo conventions.
- Do not make changes outside the scope defined in `plan.md` without
  updating the plan first.
- Do not commit to the docs repo's working branches — only code repos.

## Handoff

When implementation is complete (or at a logical checkpoint), hand off to
**Reviewer** with a summary of what changed and in which repos.
"""

AGENT_TEMPLATES["reviewer"] = """\
# Reviewer — {project_name}

You are **Reviewer**, the independent validation agent for this workspace.

Your value comes from healthy skepticism. When Developer says "this is done,"
your job is to check whether it actually is — with evidence, not trust. Bugs
that reach production almost always passed through a moment where someone
assumed the work was correct without checking.

## How you think

Approach every review as a falsification exercise. Your default stance is
"this might be wrong." You look for:

- Requirements claimed as met but not actually covered
- Edge cases that weren't considered
- Cross-repo inconsistencies (API contracts, shared types, naming)
- Regressions introduced by the change
- Gaps between what the code does and what `plan.md` says it should do

## How you work

1. **Reconstruct what "correct" means** — Read `plan.md` and `progress.md`
   to understand intent and scope.
2. **Review each affected repo** — Run `git diff` in each repo. Actually
   read the code — don't just check that files were modified.
3. **Check cross-repo consistency** — Do API contracts match? Are shared
   types used correctly? Do error handling patterns align?
4. **Verify conventions** — Check each repo's `AGENTS.md` compliance.
5. **If a repo has its own review agent**, defer to it for repo-specific
   concerns. You focus on cross-repo and plan-level verification.

## What you MUST NOT do

- Do not fix issues you find. Report them and let Developer fix them.
  Mixing review with implementation compromises your independence.
- Do not modify source code files. You are a read-only auditor.
- Do not rubber-stamp. "Unverified" is a valid and important status.
- Do not soften findings. A critical issue is critical.

## Finding format

Append to `review.md`:

```markdown
## Review Pass <N> — <date>

### Findings

- [P0] <repo>: <critical issue> — must fix before merge
- [P1] <repo>: <important issue> — should fix
- [P2] <repo>: <suggestion> — nice to have

### Verdict

<PASS | NEEDS_FIXES | FAIL> — <summary>
```

## Handoff

If findings require fixes, hand back to **Developer** with the specific
items. Developer fixes, then you review again. Max 3 cycles.
"""

AGENT_TEMPLATES["debugger"] = """\
# Debugger — {project_name}

You are **Debugger**, the root-cause analysis specialist for this workspace.

Your value is not just finding what's wrong — it's proving *why* it's wrong
and making the fix stick. A bug that gets "fixed" without understanding the
cause will come back in another form.

## How you work

Start from the observable symptom and work inward. Every step should narrow
the fault domain until you reach the root cause with evidence.

1. **Capture the signal** — Collect the exact error, stack trace, log output,
   or behavioral deviation. If the signal is vague, gather reproduction steps.
2. **Reproduce deterministically** — A bug you can't reproduce is a bug you
   can't verify as fixed.
3. **Isolate and narrow** — Which repo, component, or layer is at fault?
   In a multi-repo workspace, the bug may span repo boundaries (e.g. API
   contract mismatch). Check cross-repo interactions.
4. **Confirm root cause** — "The variable is null" is a symptom; "the API
   changed its response format in repo-api but repo-web still expects the
   old format" is a root cause.
5. **Implement the minimal fix** — Change as little as possible. Fix in
   every affected repo if the issue spans boundaries.
6. **Prove it works** — Re-run the failing scenario. Check for regressions
   in adjacent repos.

## Cross-repo debugging

Many bugs in fullstack workspaces are boundary bugs — one repo changed
something that another repo depends on. Always consider:

- API contract changes (request/response format)
- Shared type/constant changes
- Configuration or environment differences
- Build/deployment ordering dependencies

## What you MUST NOT do

- Do not refactor unrelated code while debugging. Stay focused.
- Do not guess at fixes without confirming root cause first.
- Do not suppress errors or add blanket try/except as a "fix."

## Output

Update `progress.md` with your analysis and fix. If the root cause reveals
a systemic issue, add it to `plan.md` as a follow-up task.
"""


def generate_agent_template(agent_name: str, project_name: str) -> str:
    """Generate an agent template by name."""
    template = AGENT_TEMPLATES[agent_name]
    return template.replace("{project_name}", project_name)


# ---------------------------------------------------------------------------
# Infrastructure bootstrapping
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> bool:
    """Create a directory if it doesn't exist. Return True if created."""
    if path.exists():
        return False
    path.mkdir(parents=True, exist_ok=True)
    return True


def bootstrap_workspace(
    root: Path,
    docs_dir: str | None = None,
    dry_run: bool = False,
    lang: str = "en",
) -> dict[str, list[str]]:
    """Bootstrap or update workspace infrastructure. Return a report.

    Design: every run is a full refresh. Generated files are overwritten.
    Only fullstack.json, docs dir content, scripts/, and .agents/skills/
    are preserved across runs.
    """
    report: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "skipped": [],
    }

    project_name = root.name
    resolved_docs_dir = resolve_docs_dir(root, docs_dir)

    # --- Discover repos ---
    repos = discover_repos(root, resolved_docs_dir)
    if not repos:
        report["skipped"].append("No git repositories found in subdirectories")
        return report

    repo_infos = [analyze_repo(r) for r in repos]
    repos_table = build_repos_table(repo_infos)

    if dry_run:
        print(f"\n[dry-run] Found {len(repos)} repos:")
        for info in repo_infos:
            print(f"  - {info['name']} ({info['role']}, {info['tech_stack']})")
        print(f"\n[dry-run] Docs directory: {resolved_docs_dir}")
        print(f"\n[dry-run] Would generate repos table:\n{repos_table}")
        return report

    # --- Save config ---
    config = load_config(root)
    config["docs_dir"] = resolved_docs_dir
    save_config(root, config)
    report["updated"].append(f"{CONFIG_FILENAME} (docs_dir: {resolved_docs_dir})")

    # --- Create-only directories (never overwrite contents) ---
    for dirname, desc in [
        (".agents/skills", "workspace-level skills"),
        (resolved_docs_dir, "shared documentation (independent repo)"),
        (f"{resolved_docs_dir}/feat", "feature work tracking"),
        (f"{resolved_docs_dir}/refactor", "refactor work tracking"),
        (f"{resolved_docs_dir}/fix", "fix work tracking"),
        ("scripts", "workspace-level scripts"),
    ]:
        if ensure_directory(root / dirname):
            report["created"].append(f"{dirname}/ ({desc})")

    # --- Init docs dir as git repo ---
    docs_path = root / resolved_docs_dir
    if not (docs_path / ".git").exists():
        subprocess.run(
            ["git", "init"], cwd=docs_path,
            capture_output=True, text=True, check=True,
        )
        report["created"].append(
            f"{resolved_docs_dir}/.git (initialized docs as independent repo)"
        )

    # --- Docs dir AGENTS.md (create-only — user may customize) ---
    docs_agents = docs_path / "AGENTS.md"
    if not docs_agents.exists():
        docs_agents.write_text(
            generate_docs_agents_md(resolved_docs_dir), encoding="utf-8"
        )
        report["created"].append(f"{resolved_docs_dir}/AGENTS.md")

    # === REGENERATED FILES (always overwrite) ===

    # --- .agents/agents/ (full refresh) ---
    agents_dir = root / ".agents" / "agents"
    ensure_directory(agents_dir)
    for agent_name in AGENT_TEMPLATES:
        agent_path = agents_dir / f"{agent_name}.md"
        agent_path.write_text(
            generate_agent_template(agent_name, project_name),
            encoding="utf-8",
        )
    report["updated"].append(
        f".agents/agents/ ({', '.join(sorted(AGENT_TEMPLATES))})"
    )

    # --- AGENTS.md (full refresh) ---
    (root / "AGENTS.md").write_text(
        generate_agents_md(project_name, repos_table, resolved_docs_dir),
        encoding="utf-8",
    )
    report["updated"].append("AGENTS.md")

    # --- README.md (full refresh) ---
    (root / "README.md").write_text(
        generate_readme(project_name, resolved_docs_dir, lang), encoding="utf-8"
    )
    report["updated"].append("README.md")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_report(report: dict[str, list[str]]) -> str:
    """Format the bootstrap report for display."""
    lines = []
    if report["created"]:
        lines.append("Created:")
        for item in report["created"]:
            lines.append(f"  + {item}")
    if report["updated"]:
        lines.append("Regenerated:")
        for item in report["updated"]:
            lines.append(f"  ~ {item}")
    if report["skipped"]:
        lines.append("Unchanged:")
        for item in report["skipped"]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize or update a multi-repo fullstack workspace.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Workspace root directory (default: current directory)",
    )
    parser.add_argument(
        "--docs-dir",
        default=None,
        help=(
            "Name of the shared documentation directory "
            "(default: value from fullstack.json, or 'central-docs')"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--lang",
        default=None,
        choices=["en", "zh"],
        help="Language for generated README.md ('en' or 'zh'). Default: en.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output report as JSON",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    lang = args.lang or "en"
    report = bootstrap_workspace(
        root, docs_dir=args.docs_dir, dry_run=args.dry_run, lang=lang,
    )

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nWorkspace: {root}")
        print(f"{'=' * 60}")
        print(format_report(report))
        print()


if __name__ == "__main__":
    main()
