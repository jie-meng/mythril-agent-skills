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

    M2 & M3 & M4 --> N[Implementation loop]

    N --> N1[Read repo AGENTS.md + README.md]
    N1 --> N2{Repo has .agents/agents/?}
    N2 -- Yes --> N3[Use repo-level agents]
    N2 -- No --> N4[Use workspace agents]
    N3 & N4 --> N5[Implement changes]
    N5 --> N6[Run repo tests]
    N6 --> N7[Update progress.md]
    N7 --> N8{More repos?}
    N8 -- Yes --> N1
    N8 -- No --> O[Review]

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

## Agent Coordination Model

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
    Skill->>User: Confirm repos and branch name
    User->>Skill: Confirmed

    alt Complex work
        Skill->>Planner: Analyze and create plan.md
        Planner-->>Skill: plan.md written
    end

    Skill->>Dev: Implement per plan.md
    Dev->>Dev: Code repo-1 (follow repo AGENTS.md)
    Dev->>Dev: Update progress.md
    Dev->>Dev: Code repo-2
    Dev->>Dev: Update progress.md
    Dev-->>Skill: Implementation complete

    Skill->>Reviewer: Review all changes
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
| Modifies | AGENTS.md, .gitignore | Source code in repos |
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
- [x] Plugin wrapper + marketplace.json entry
- [x] Description validation under 1024 limit

### Planned / Ideas

- [ ] Parallel implementation: use sub-agents to work on independent repos
  simultaneously
- [ ] Auto-PR creation: after review passes, auto-create PRs in each repo
  using `gh-operations` skill
- [ ] Dependency graph visualization: generate a mermaid diagram of cross-repo
  dependencies for each work item
- [ ] Template customization: let users define their own plan.md template

## Changelog

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
