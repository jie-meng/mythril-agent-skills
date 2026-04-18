# Fullstack Impl — Design Document

Design document for the `fullstack-impl` skill. Covers requirements, solution
architecture, agent coordination, and workflow details.

**Last updated**: 2026-04-18

---

## Problem Statement

After a fullstack workspace is initialized by `fullstack-init`, developers
need to implement features, refactors, and fixes across multiple repos.
Without a structured approach:

1. Context is lost — requirements from Jira/Confluence/Figma aren't gathered
   before coding starts.
2. Branch management is inconsistent — each repo may end up on different
   branches or miss the latest main.
3. No work tracking — progress isn't documented, making resume after session
   breaks impossible.
4. No review cycle — changes go unchecked, cross-repo inconsistencies slip in.
5. No agent coordination — planner, implementer, reviewer, and debugger roles
   aren't separated, leading to shallow work.

## Workflow

```mermaid
flowchart TD
    A[User invokes fullstack-impl] --> B{fullstack.json exists?}
    B -- No --> FAIL[Inform user: run fullstack-init first]
    B -- Yes --> C[Read fullstack.json, AGENTS.md]

    C --> D{Links in user prompt?}
    D -- Jira --> D1[Read via jira skill]
    D -- Confluence --> D2[Read via confluence skill]
    D -- GitHub --> D3[Read via gh-operations skill]
    D -- Figma --> D4[Read via figma skill]
    D -- None --> E[Use prompt text as requirements]
    D1 & D2 & D3 & D4 --> E

    E --> F[Determine work type: feat / refactor / fix]

    F --> G[Identify affected repos]
    G --> H{Present to user for confirmation}
    H -- User corrects --> G
    H -- User confirms --> I[Derive branch name]

    I --> J{Existing work directory?}
    J -- Yes --> K[Resume: read plan.md + progress.md]
    J -- No --> L[Create work directory in docs repo]

    L --> L1[Write plan.md]
    L --> L2[Write progress.md]
    L --> L3[Write review.md header]

    K --> M[Branch management per repo]
    L1 & L2 & L3 --> M

    M --> M1{Branch already exists?}
    M1 -- Yes, repo on it --> M2[Skip checkout - resume scenario]
    M1 -- Yes, different branch --> M3[git checkout branch]
    M1 -- No --> M4[git checkout default + pull + checkout -b]

    M2 & M3 & M4 --> N[Implementation loop — serial, in dependency order]

    N --> N1[Read repo AGENTS.md + README.md]
    N1 --> N1a[Activate environment: venv / nvm / bundler]
    N1a --> N2{Repo has .agents/agents/?}
    N2 -- Yes --> N3[Use repo-level agents]
    N2 -- No --> N4[Use workspace agents]
    N3 & N4 --> N5[Implement changes]
    N5 --> N6[Lint + type-check]
    N6 --> N7[Run repo tests]
    N7 --> N7a{Tests pass?}
    N7a -- No --> N7b[Fix failures, re-run]
    N7b --> N7
    N7a -- Yes --> N8[Commit + update progress.md]
    N8 --> N9{More repos?}
    N9 -- Yes --> N1
    N9 -- No --> O[Review]

    O --> O1[Reviewer reads plan + progress + git diff]
    O1 --> O2[Append findings to review.md]
    O2 --> O3{Verdict}
    O3 -- PASS --> P[Finalize]
    O3 -- NEEDS_FIXES --> O4[Dev fixes P0/P1 items]
    O4 --> O5[Update progress.md]
    O5 --> O6{Cycle < 3?}
    O6 -- Yes --> O1
    O6 -- No --> P

    P --> P1[Update progress.md: status = Complete]
    P --> P2[Update plan.md: status = Done]
    P --> P3[Report summary to user]
```

## Requirements

### R1 — Context gathering before implementation

Must read all linked resources (Jira, Confluence, GitHub, Figma) before
planning or coding.

### R2 — Work type classification

Support three work types: `feat`, `refactor`, `fix`. Each has its own
directory in the docs repo and branch prefix.

### R3 — Mandatory user confirmation

Always present the list of affected repos and branch name for confirmation,
even when confident.

### R4 — Branch management

- Detect default branch (main/master/dev)
- Pull latest before branching
- Resume detection: skip checkout if already on the correct branch
- Naming: `<type>/<JIRA-KEY>/<Title>` or `<type>/<Title>`
- Docs repo does NOT use feature branches

### R5 — Agent coordination

Four agents with clear boundaries:

| Agent | Writes code? | Modifies review.md? | Modifies plan.md? |
|-------|-------------|---------------------|-------------------|
| Planner | No | No | Yes (creates) |
| Dev | Yes | No | No (after start) |
| Reviewer | No | Yes (append-only) | No |
| Debugger | Yes | No | May add follow-ups |

### R6 — Work tracking

Every work item creates plan.md, progress.md, review.md. Progress is updated
after every meaningful change. Review is append-only.

### R7 — Resume capability

When a previous session's work exists, detect it and resume from where it
left off.

### R8 — Repo-level agent delegation

If a repo has its own `.agents/agents/`, prefer those for repo-specific
concerns. Workspace agents handle cross-repo coordination.

### R9 — Serial per-repo orchestration

Repos are modified one at a time, in dependency order (upstream → services
→ consumers). Parallel per-repo execution is only allowed when the planner
explicitly confirms zero shared interfaces. Default is always serial.

### R10 — Repo convention compliance

Before touching any repo, read its AGENTS.md and README.md. Follow its
coding conventions, commit message format, and architecture constraints.
These are mandatory, not advisory.

### R11 — Environment management

Detect and activate repo-specific environments before running any commands:
venv/conda for Python, nvm for Node, bundler for Ruby, etc. If a venv
doesn't exist but is documented, create it per README instructions.

### R12 — Mandatory test execution

After implementing changes in a repo, run its full validation pipeline:
lint → type-check → tests → build. Fix all failures caused by your changes
before moving to the next repo. Pre-existing failures are documented but
do not block progress.

### R13 — Dependency-ordered implementation

The plan must establish a dependency order for repos (shared libs first,
consumers last). Implementation follows this exact order. Downstream repos
can rely on upstream changes being committed and validated.

## Agent Coordination Model

### Orchestration strategy: serial per-repo

Repos are modified **one at a time, in dependency order** (upstream first,
consumers last). This is the default, even when repos appear independent.

**Rationale (correctness > speed):**

1. **Cross-repo dependencies are the norm.** Shared types → API contracts →
   consumers. Parallel agents can't see each other's WIP, leading to
   contract mismatches that are expensive to fix.
2. **Context accumulates naturally.** What was built in repo A informs
   what needs to happen in repo B — serial flow preserves this.
3. **Shared state conflicts.** Multiple agents writing to `progress.md`
   concurrently creates race conditions.
4. **Debugging is simpler.** Sequential execution gives a clean audit trail.

**Exception**: If the planner explicitly confirms that repos have ZERO
shared interfaces, ZERO data model overlap, and ZERO dependency edges,
they MAY be implemented in parallel. The planner must document this
independence in `plan.md`.

### Per-repo implementation loop

For each repo (serial, in dependency order):

```
Read AGENTS.md + README.md
  → Activate environment (venv, nvm, etc.)
    → Implement changes
      → Lint / type-check / test (fix if broken)
        → Commit (follow repo's commit convention)
          → Update progress.md
```

### Sequence diagram

```mermaid
sequenceDiagram
    participant User
    participant Skill as fullstack-impl
    participant Planner
    participant Dev
    participant Reviewer
    participant Debugger

    User->>Skill: Implement this feature (+ links)
    Skill->>Skill: Gather context (Jira, Confluence, Figma, GitHub)
    Skill->>User: Confirm repos, branch, dependency order
    User->>Skill: Confirmed

    alt Complex work
        Skill->>Planner: Analyze and create plan.md
        Planner->>Planner: Determine dependency order
        Planner-->>Skill: plan.md with ordered repos
    end

    loop For each repo (in dependency order)
        Skill->>Dev: Read repo AGENTS.md + README.md
        Dev->>Dev: Activate environment (venv/nvm/etc.)
        Dev->>Dev: Implement changes
        Dev->>Dev: Run lint + type-check + tests
        alt Tests fail
            Dev->>Dev: Fix failures, re-run until pass
        end
        Dev->>Dev: Commit (repo's convention)
        Dev->>Dev: Update progress.md
    end

    Skill->>Reviewer: Review all repos
    Reviewer->>Reviewer: git diff in each repo
    Reviewer->>Reviewer: Cross-repo consistency check
    Reviewer-->>Skill: Append findings to review.md

    alt NEEDS_FIXES (max 3 cycles)
        Skill->>Dev: Fix P0/P1 findings
        Dev-->>Skill: Fixes applied
        Skill->>Reviewer: Re-review
        Reviewer-->>Skill: Updated review.md
    end

    alt Fix work type
        Skill->>Debugger: Root-cause analysis
        Debugger->>Debugger: Reproduce, isolate, confirm cause
        Debugger-->>Skill: Analysis + minimal fix
    end

    Skill->>User: Summary of completed work
```

## Branch Naming Examples

| Scenario | Branch name |
|----------|-------------|
| Jira feature | `feat/XYZ-706/Import-Export` |
| Jira fix | `fix/XYZ-708/iPad-Ble-Not-Working` |
| Jira refactor | `refactor/XYZ-707/Refine-Models` |
| No-Jira feature | `feat/Dark-Mode-Toggle` |
| No-Jira fix | `fix/Login-Crash-On-Empty-Password` |

## File Inventory

```
mythril_agent_skills/skills/fullstack-impl/
└── SKILL.md                     # Pure instruction skill (no scripts)

plugins/fullstack-impl/
└── skills/
    └── fullstack-impl -> ../../../mythril_agent_skills/skills/fullstack-impl
```

This skill is pure instructions — no Python scripts. It orchestrates
behavior through the SKILL.md instructions, delegating actual code changes
to the AI agent following the workspace agents' guidelines.

## Relationship to fullstack-init

| Concern | fullstack-init | fullstack-impl |
|---------|---------------|----------------|
| When | Before any work | For each work item |
| Creates | Workspace infrastructure | Work-specific plans + branches |
| Modifies | AGENTS.md, README.md | Source code in repos |
| Docs dir | Creates + git init | Reads + writes work tracking docs |
| Agents | Creates templates | Follows their guidelines |
| Idempotent | Yes (re-run safe) | Per-work-item (one dir per item) |

## Current Status

### Done

- [x] R1 — Context gathering (Jira, Confluence, GitHub, Figma)
- [x] R2 — Work type classification (feat, refactor, fix)
- [x] R3 — Mandatory user confirmation
- [x] R4 — Branch management with resume detection
- [x] R5 — Four-agent coordination model
- [x] R6 — Work tracking (plan.md, progress.md, review.md)
- [x] R7 — Resume capability
- [x] R8 — Repo-level agent delegation
- [x] R9 — Serial per-repo orchestration with parallel exception
- [x] R10 — Repo convention compliance (AGENTS.md/README.md mandatory)
- [x] R11 — Environment management (venv, nvm, bundler, etc.)
- [x] R12 — Mandatory test execution (lint → type-check → test → build)
- [x] R13 — Dependency-ordered implementation
- [x] Plugin wrapper + marketplace.json entry
- [x] Description validation under 1024 limit

### Planned / Ideas

- [ ] Auto-PR creation: after review passes, auto-create PRs in each repo
  using `gh-operations` skill
- [ ] Dependency graph visualization: generate a mermaid diagram of cross-repo
  dependencies for each work item
- [ ] Template customization: let users define their own plan.md template

## Changelog

### 2026-04-18 — v3: Serial orchestration, environment management, test rigor

- Added serial per-repo orchestration as default strategy with rationale
- Parallel per-repo only when planner explicitly confirms zero dependencies
- Added environment management (venv, nvm, bundler, conda, Docker)
- Mandatory validation pipeline: lint → type-check → tests → build
- Test failure handling: fix own failures, document pre-existing ones
- Dependency-ordered implementation: upstream repos first, consumers last
- Plan.md template now includes Depends On column for repos
- Enhanced cross-repo review checklist (API contracts, shared types, env vars)
- Detailed error handling for environment issues and contract mismatches

### 2026-04-18 — v2: Work types, branch management, four agents, Figma

- Generalized from features-only to feat/refactor/fix work types
- Added branch management with naming convention and resume detection
- Four agents: planner, dev, reviewer, debugger (from init scaffolding)
- Added Figma link support alongside Jira/Confluence/GitHub
- Docs repo does not use feature branches
- Created design document with mermaid workflow diagrams

### 2026-04-18 — v1: Initial implementation

- Context gathering from Jira, Confluence, GitHub
- Repo identification with mandatory user confirmation
- Feature plan creation (plan.md, progress.md, review.md)
- Dev/review cycle with max 3 fix iterations
- Resume capability for incomplete features
