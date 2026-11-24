---
name: fullstack-explore
description: |
  Read-only knowledge exploration across a multi-repo fullstack workspace
  — answer architecture questions, locate implementations, explain
  cross-repo relationships, and recommend next steps. No branches, no
  commits, no file modifications. Information is gathered in order of
  token efficiency: workspace documents (human summaries) → graphify
  knowledge graphs (structured queries) → direct file reading (raw code).
  Trigger: "fullstack explore", "fullstack query", "全栈探索",
  "全栈查询", "工作区查询", "workspace query"; ALSO when the user asks
  discovery questions inside a fullstack workspace — "what does this
  workspace do", "这个工作区是做什么的", "which repo handles X",
  "哪个仓库负责X", "explain the architecture", "讲解架构",
  "where is the code for Y", "Y的代码在哪里", "how does X work
  across repos", "which repos are involved in Z", "Z涉及哪些仓库",
  "告诉我这个项目的结构", "这个项目的技术栈是什么".
license: Apache-2.0
---

# Fullstack Explore

Answer questions about a multi-repo workspace initialized by
`fullstack-init` — architecture, where code lives, how repos connect — and
recommend the next step. **Read-only**: no branches, commits, pushes, PRs,
or file edits in any repo.

## Source-of-Truth Rule

**Documents and graphify tell you WHERE to look; source code tells you
WHAT is true.** Work-item documents can be stale and graphs out of date.
Never present a finding as fact until you have read the source file behind
it; when they disagree, the source wins and the answer says so.

| Step | Source | Purpose |
|------|--------|---------|
| 1. Navigate | Docs repo (work items, issues) | Which repos, files, and concepts matter |
| 2. Navigate | graphify knowledge graphs | Where modules, functions, and relationships live |
| 3. Verify & answer | Source files | The only authoritative source |

**Reading discipline** — load a reference only at the step that names it:

| File | Read when |
|------|-----------|
| `references/graphify-queries.md` | `graphify_check.py` reports `EXISTS` for the docs repo or a code repo |
| `references/answer-format.md` | Writing the answer (Step 6) |

`SKILL_PATH` is this skill's installed directory.

## Workspace Validation Gate (MANDATORY SCRIPT CALL)

```bash
python3 SKILL_PATH/scripts/check_workspace.py
```

`WORKSPACE_VALID=false` → STOP: tell the user the workspace was not
detected, list the `MISSING=` markers, and ask them to `cd` to the
workspace root and restart the agent, or run `fullstack-init` first.
`WORKSPACE_VALID=true` → note `DOCS_DIR` and continue.

## Language

Answer in the user's language: an explicit request wins; otherwise any
Chinese character in the prompt → Chinese; otherwise English.

## Step 1 — Understand the Query

Classify it — architecture overview, role discovery ("which repo handles
X"), implementation lookup, cross-repo flow, tech stack, or dependency /
impact ("what breaks if I change X"). The class sets the scope: all repos
at surface level, one repo plus its callers, or a full chain. Ask one
clarifying question only when the scope is genuinely unclear.

## Step 2 — Workspace Context

Read the workspace `AGENTS.md`: the repos table (names, roles, stacks —
the authoritative repo list), Workspace Conventions, and the
*Docs-Code Lockstep* section's reverse-lookup command.

## Step 3 — Documents First (MANDATORY)

Before touching a repo, look for prior work on the topic. Documents are
navigation, not the answer.

1. **The query names a file or symbol** → run the reverse lookup from the
   workspace `AGENTS.md` (`plan_lint.py --find <path-or-symbol>`). A
   `CODEMAP:` hit names the work item that owns the code — its documents
   are the most precise starting point.
2. **Docs repo graph** — `python3 SKILL_PATH/scripts/graphify_check.py
   <docs-dir>`. `EXISTS` → query it (`references/graphify-queries.md`).
3. **Otherwise scan by name** under `<docs-dir>/`: active work in
   `changes/{feat,refactor,fix}/<name>/`, completed work in
   `changes/archive/YYYY-MM-DD-<type>-<name>/` (scan it too — history
   lives there), and recorded problems in `issues/<YYYY-MM-DD-name>/`
   (README symptom and analysis sections). Match directory names, Jira
   keys, and topic keywords.

For each match, skim headings and first paragraphs; read deeply only the
relevant sections. High-signal sections: `plan.md` §Summary, repositories
table, Code Map, Success Criteria; `analysis.md` problem / root cause /
affected repos; `review.md` §Status Overview and Evidence table.

Then judge coverage: **full** (documents answer it → verify mode),
**partial** (context, gaps remain → targeted mode), or **none**.

## Step 4 — Pick the Repos

Every repo in the `AGENTS.md` table whose role relates to the query is in
scope; documents may prioritize repos but never justify skipping one.

- **Verify mode** — extract the documents' structural claims (paths,
  modules, decisions) and check them against current code; answer from
  the documents where they hold, and gather fresh context only where the
  code diverged.
- **Targeted / full mode** — present the repo selection with a one-line
  reason each and the basis (repos table, document), then proceed on
  confirmation or "just go ahead".

## Step 5 — Gather Context, One Repo at a Time

Finish the protocol for one repo before the next:

1. **Repo skills** — `python3 SKILL_PATH/scripts/repo_skills.py <repo>`.
   Repo-private skills in `<repo>/.agents/skills/` are invisible from the
   workspace root; read the `SKILL.md` of each skill matching the query
   and follow it. Skip the rest.
2. **Graph check** — `python3 SKILL_PATH/scripts/graphify_check.py <repo>`
   (a direct filesystem check — never Glob, which honours `.gitignore`).
   - `EXISTS` → the graph path is MANDATORY before any grep or source read:
     follow `references/graphify-queries.md`.
   - `NOT_FOUND` → read the repo's `AGENTS.md` and `README.md`, then grep
     and read from config files, entry points, and topic keywords —
     targeted by document context when you have it.
3. **Verify in source** every key claim before it enters the answer.

After all repos: check the cross-repo seams — endpoints the client calls
vs. the server exposes, shared types, and where the data shape changes.

## Step 6 — Answer

Follow `references/answer-format.md`: direct answer first, then sources
with file paths and line ranges, staleness notes, and what was verified in
source.

## Step 7 — Recommend the Next Step

| Situation | Recommend |
|---|---|
| A bug whose root cause is established with evidence, or a fully specified small tweak; one repo, small, no contract / schema change, no active owner | A **quick fix** via `fullstack-apply` — no work item; the smallest change that removes the symptom, broader hardening listed as optional |
| A change that needs design or spans repos / contracts | `fullstack-propose` with a concrete scope, e.g. `fullstack propose "Add Apple Pay to checkout"` |
| Unknowns need validating first | `fullstack-propose` in deep (spike) mode |
| A problem worth recording but not ready to act on | `fullstack-issue-create` |
| An active work item is done | `fullstack-archive` |
| An active issue is fixed or triaged | `fullstack-issue-archive` |
| Workspace files are outdated, or a repo is missing from the table | Re-run `fullstack-init` (three-way refresh — keeps the user's edits) |
| Repos without graphs would benefit | Run `graphify` on them |
| Nothing further | Say so and stop |

Always one concrete next step, not a menu.

## Capturing Findings (only if asked)

When the user asks to record what you found ("记下来", "沉淀一下",
"record this"), hand it to `fullstack-issue-create` — an issue is the
place for findings that are not yet a plan. Never write a partial work
directory under `changes/`: a work item is four documents created by
`fullstack-propose`.

## Repos Outside the Workspace

A repo not in the `AGENTS.md` table: ask whether to add it (re-run
`fullstack-init` after cloning it into the workspace); otherwise read it
as a one-off with `git-repo-reader`.
