# Fullstack Skills Refactor Plan — explore / propose / apply / archive

**Last updated**: 2026-08-07
**Status**: Draft — under review
**Scope**: `mythril_agent_skills/skills/fullstack-*` family + `docs/fullstack/` documentation + new `fullstack-docs-migration`

---

## 1. Background & Motivation

### 1.1 Empirical summary (`robo-documents`, 124 work items, 383 commits, 2026-02 → 08)

| Metric | Data | Meaning |
|---|---|---|
| Four-file invariant | 106/110 impl directories complete (96.4%), 14/14 spikes complete | The convention is well executed — not the problem |
| plan.md `**Status**:` field | Only 8/109 filled (7.3%), 8 spellings, 3 of them contradict progress.md | **The status field is effectively dead** |
| `## Iteration Log` | Only 8/109 present (7.3%), 2 of them empty tables; real iteration median is 1 round, 35% zero updates | **The Iteration Log mechanism failed** |
| spike → impl content reuse | 5 analysis.md pairs share **zero** substantive lines; impl rewrites 1.2–2.4× larger | **Spike docs are rewritten, not inherited** |
| Archival traces | **0** directory moves/renames/deletions in 383 commits; 93% of dirs untouched >30 days, 29% >90 days | **"Abandoned" and "completed" are indistinguishable** |
| Manual substitute | User built `robocontrol-changelog/` (22 hand-timestamped files) | **The archive need is real and already paid by hand** |
| spike Success Criteria → Evidence | 12/14 define SC, 11/14 Evidence tables genuinely filled (including one recorded falsification) | **The only healthy criteria-evidence loop in the system** |
| impl-side acceptance criteria | Only 16% of dirs mention them; review verdicts in 8 spellings (257 PASS / 78 通过 / 62 pass…) | **No pre-declared definition of done on the impl side** |
| Reference fields | 4 spellings (`Source` / 来源 / Spike 参考 / 关联文档), incl. 1 broken relative path | **Cross-stage links have no convention** |

### 1.2 Defects this plan addresses

- **D1 No lifecycle state**: the `Status` field had 7.3% adoption and drifts; `route_check.py`'s six-way routing state machine receives no input in 92.7% of cases and effectively spins.
- **D2 No archive**: active / done / abandoned items share one directory, growing unbounded.
- **D3 Explore output is discarded**: five spike→impl pairs show 0% reuse; plain-text handoff + full rewrite.
- **D4 Links are ad-hoc**: 4 source spellings, a broken relative path, and Status snapshots copy-pasted into successor docs that then rot.
- **D5 Document sizing mismatch**: four files are too heavy for small changes (4 shell stubs) and too light for large ones (analysis.md up to 850 lines + 10 escape-hatch files).
- **D6 Iteration Log failed**: serves a multi-round scenario that almost never happens; the cost is paid anyway.
- **D7 Convention drift**: `investigate/` → `spike/`; four non-convention subsystems (docs/, changelog/, errors/, user-survey/) have grown alongside.
- **D8 No definition of done**: planner is asked to produce acceptance criteria (`planner.md:51-53`) but the templates have no slot for them; reviewer is forced to reverse-engineer "what correct means" (`reviewer.md:45-47`).

### 1.3 Design principles

1. **Align with the OpenSpec lifecycle**: explore → propose → apply → archive, without importing its spec grammar.
2. **Express state via directory location, not text fields**: fields rot; `mv` does not.
3. **Fold spike into propose**: no separate spike directory; one document written start to finish.
4. **Keep what is empirically proven**: the four-file invariant, Success Criteria → Evidence, graphify-first, reviewer review.
5. **Drop what is empirically broken**: the Status field (replaced by directory), Iteration Log (replaced by git log + dated progress.md sections), and the 60 hardcoded trigger verbs.
6. **No SDD**: no SHALL/MUST, no delta specs, no main-spec merge. Documents are **decision records**, not behavior specifications.

---

## 2. Target Architecture Overview

### 2.1 Skill mapping

| New skill | Source | Change |
|---|---|---|
| `fullstack-init` | `fullstack-init` | **Kept as-is** (workspace scaffolding, not part of the work-item lifecycle; OpenSpec has no counterpart) |
| `fullstack-explore` | `fullstack-query` | Renamed + optional discovery capture |
| `fullstack-propose` | `fullstack-spike` + `fullstack-impl` Steps 1–5 | **Merges the planning surface of two skills**; spike becomes its deep mode |
| `fullstack-apply` | `fullstack-impl` Steps 6–9 | Planning stripped out; implementation/review/PR only |
| `fullstack-archive` | **New** | Close completed work by moving the directory |
| `fullstack-docs-migration` | **New** | One-time migration of legacy docs |

> **Key clarification**: this is not a 1:1 rename. The ~3000-line monolith `fullstack-impl` is **split into two skills** (propose takes Steps 1–5, apply takes Steps 6–9), separated by a stage gate of "four documents complete + explicit user approval". This directly eliminates D3 (spike doc rewrite) and D1 (idle routing state machine).

### 2.2 New directory structure

```
<docs-dir>/                          # independent git repo
├── changes/                         # work tracking (the only convention dir; naming see §7)
│   ├── feat/<work-name>/            # active work item (exists = in progress)
│   │   ├── analysis.md
│   │   ├── plan.md
│   │   ├── progress.md
│   │   └── review.md
│   ├── refactor/<work-name>/
│   ├── fix/<work-name>/
│   └── archive/                     # completed (exists = done) ← new
│       └── YYYY-MM-DD-<type>-<work-name>/
├── docs/  changelog/  errors/  …    # non-convention dirs: untouched, migration only reports
└── graphify-out/                    # graphify artifacts (generated)
```

**Archive directory naming rule**: `changes/archive/YYYY-MM-DD-<type>-<work-name>/`, where `<type>` ∈ `feat` / `fix` / `refactor` / `spike`, taken from the source parent directory. **The type prefix is mandatory** — the archive holds three types side by side, and `feat/<work-name>` may share a name with `fix/<work-name>`, so date + name alone can collide.

- **No more `spike/` directory**. Spike is an optional depth level of propose; its output lands directly in `feat|fix|refactor/<work-name>/`. `<type>=spike` in the archive appears only as a migration leftover (legacy standalone spike dirs with no impl counterpart).
- `workspace_init.py:1127-1130`'s directory creation list changes from 4 flat dirs (feat/refactor/fix/spike) to 1 container + 3 types + archive: `changes/{feat,refactor,fix,archive}`.

### 2.3 State expressed by directory location, not the Status field

| State | Old (text field, failed) | New (directory location) |
|---|---|---|
| Planning / In progress | `plan.md: **Status**: Planning / In Progress` | Directory exists under `changes/feat|refactor|fix/<work-name>/` |
| Done | `**Status**: Done / Closed` (8 spellings) | Directory exists under `changes/archive/YYYY-MM-DD-<type>-<work-name>/` |

- Archiving is the **only** state transition — one `mv`, atomic, no drift, no spelling variants.
- Planning vs in-progress are no longer distinguished: both are "active", decided by whether apply has started; no text marker needed.
- `fullstack-docs-migration` translates legacy state into directory location.

### 2.4 Document structure revisions (four files kept, content adjusted)

| Document | Kept | Changed |
|---|---|---|
| `analysis.md` | Technical analysis (why) | In deep mode it carries the spike sections (Objective/Hypothesis/Experiments/Findings); after validation, Design Options / Target Architecture are appended to the **same file** |
| `plan.md` | Requirements / Affected Repos / Implementation Plan / Risks | **`**Status**:` field removed**; **`## Success Criteria` (checkbox) added** |
| `progress.md` | Completed Steps / dated sections (the user actually uses `### YYYY-MM-DD`) | **`## Iteration Log` table removed**; Changelog kept |
| `review.md` | Per-round review records | **Evidence table added** (each Success Criterion checked against evidence); review verdict normalized to `PASS` / `NEEDS_FIXES` / `BLOCKED` |

Supporting changes:
- `fullstack-init/agents/planner.md:51-53`'s required acceptance criteria now have a home (plan.md `## Success Criteria`).
- `fullstack-init/agents/reviewer.md:45-47` no longer reverse-engineers the definition of done.
- The reference field is unified to a single `**Source**` spelling.

---

## 3. Skill Design Specifications

### 3.1 `fullstack-init` (kept, adjusted)

- **Unchanged**: workspace scaffolding, `workspace_init.py`, four agents, graphify check.
- **Changed**:
  - Generated `<docs-dir>/AGENTS.md` conventions section: `spike/` → `changes/` (with archive); `graphify_check.py` shared asset documented.
  - Generated copy mentioning `fullstack-impl`/`fullstack-spike` updated to the new skill names.
  - Category directories created: `feat/refactor/fix/spike` → `changes/{feat,refactor,fix,archive}`.
- The embedded 8-line install-path candidate lists in SKILL.md (L61-68 etc.) follow the skill rename.

### 3.2 `fullstack-explore` (was `fullstack-query`)

- **Position**: read-only thinking partner. Answer architecture questions, locate implementations, understand cross-repo flows, evaluate tech choices.
- **Inherited**: 7-step flow, graphify-first, Source-of-Truth Rule (documents navigate, source decides), zero code side effects.
- **Improved**:
  - New optional capability: **when the user asks**, capture findings as a draft `analysis.md` in a work directory (aligned with OpenSpec explore's "MAY create artifacts if asked" — capturing thinking is not implementing).
  - "Recommend next steps" becomes explicit routing instead of plain-text suggestion: clear change → propose; needs validation → propose deep mode; just understanding → end.
- **Boundary**: `NEVER write code, NEVER create branches, NEVER commit`. No on-disk artifacts unless the user asks.
- **description draft**:
  > Explore a multi-repo fullstack workspace to answer questions, locate implementations, and understand cross-repo flows. Use when the user wants to understand code, investigate a problem, or think through an idea before planning. Never edits code.

### 3.3 `fullstack-propose` (was `fullstack-spike` + `fullstack-impl` Steps 1–5)

This is the core of the refactor. Two modes:

| Mode | Trigger | Flow |
|---|---|---|
| **Standard** | Requirements clear, no major unknowns | Gather context → determine work type → **user confirms repos** → write the four documents (plan.md with Success Criteria) |
| **Deep (spike)** | Unknowns need validation | On top of standard: `analysis.md` starts with `Objective / Hypothesis / Unknowns / Success Criteria` → run experiments (**temporary code, no branches, no commits**) → record findings as you go → validate → append `Design Options / Target Architecture` to the **same file** → conclusion into plan.md |

**Core promise (eliminates D3)**: the deep mode's output IS the final work directory — **no second rewrite exists**. When propose ends, `changes/feat|fix|refactor/<work-name>/` has all four documents and can go straight into apply.

**Planning boundary (borrowed from OpenSpec propose)** — written both at the top of SKILL.md and in Guardrails:

> This skill plans only. Even if the request includes "and implement it", STOP after producing the planning artifacts and wait for a new user request to trigger apply. No project code is modified.

**Removed**: `route_check.py`'s six-way routing state machine (Fresh/Reference/Iteration/Followup/Resume/AskUser) and the 60 hardcoded verbs. Routing degrades to:
- Directory doesn't exist → create it (standard vs deep decided by the number of unknowns);
- Directory exists and isn't archived → ask the user whether to "revise the plan" or "continue implementation" (the latter goes to apply).

**description draft**:
> Propose a new work item across a multi-repo fullstack workspace — gather context, design the approach, validate unknowns if needed, and write the work-tracking documents. Use when the user wants to plan a feature, fix, or refactor before implementing. Planning only; does not edit project code.

### 3.4 `fullstack-apply` (was `fullstack-impl` Steps 6–9)

- **Position**: implement an already-planned work item. **Input is propose's four documents**; no planning here.
- **Inherited**: per-repo implementation (developer agent), staged review (reviewer), cross-repo consistency review, PR creation, four-document sync discipline.
- **Simplified**:
  - The 4 Mode branches are gone (iteration-mode / followup-mode / reference-mode all become manual documentation, no longer routing branches).
  - `iteration_log_check.py` gate and the `## Iteration Log` sync checklist are removed.
  - `review.md` verdicts normalized to `PASS` / `NEEDS_FIXES` / `BLOCKED`; an Evidence table is added (checked against plan.md's Success Criteria).
  - Follow-up edits: user feedback during apply → recorded in the same four documents (dated progress.md section + new review.md round), no separate Mode state machine.
  - **Successor work** (new requirement building on old work): propose creates `<name>-v2/` (or a new name); apply only cares about "the Success Criteria in plan.md".
- **description draft**:
  > Implement a planned work item across a multi-repo fullstack workspace — implement per repo, run staged and cross-repo reviews, and open PRs. Use when the user wants to implement, continue, or finish a proposed feature, fix, or refactor.

### 3.5 `fullstack-archive` (new)

- **Position**: close completed work. Triggered when the user says "done/archive/ship it/结了".
- **Flow**:
  1. Identify the work item (`changes/<type>/<work-name>/`, type ∈ feat/refactor/fix);
  2. Integrity check: four documents exist; review.md has a final verdict (**warn only, non-blocking**);
  3. Optional changelog entry: if `<docs-dir>/` contains a changelog dir (e.g. `robocontrol-changelog/`), append an entry per that dir's existing naming; otherwise skip;
  4. Archive dir name: `YYYY-MM-DD-<type>-<work-name>` (type from source parent);
  5. `mv <docs-dir>/changes/<type>/<work-name>/ → <docs-dir>/changes/archive/YYYY-MM-DD-<type>-<work-name>/`;
  6. Idempotence rule (borrowed from OpenSpec archive): if the source name already starts with `YYYY-MM-DD-` (a migration leftover), **don't stack the date**, only add the type prefix; archiving same-named items of different types on the same day won't collide (type is in the name);
  7. Collision (target already exists) → **fail hard**, report;
  8. Output an archive summary (name / type / date / contents).
- **Archive semantics**: after archiving, any new request on the same scope → **never reopen the old directory**; propose creates a new one (`-v2` is propose's decision, archive doesn't participate).
- **description draft**:
  > Archive a completed work item by moving its directory into the archive with a date and type prefix. Use when the user says a feature, fix, or refactor is done, shipped, merged, or finished.

### 3.6 `fullstack-docs-migration` (new)

- **Position**: one-time migration tool. The user only provides the docs repo path (or lets the agent discover it); everything else is automatic.
- **Flow**:
  1. Scan `<docs-dir>/` structure, recognizing legacy conventions (top-level `feat|fix|refactor|spike`) vs non-convention dirs;
  2. Classify each work item:
     - Primary signal: completion marker in `progress.md` + last-active date;
     - Secondary signal: `plan.md` `**Status**:` field (if present);
     - On conflict, trust progress.md + date; record the conflict in the migration report;
  3. **Directory moves** (all into `changes/`; archive name `YYYY-MM-DD-<type>-<work-name>`, date = the item's last-active day — last progress.md update or last git commit; type from source parent):
     - Active: `feat/<work-name>/ → changes/feat/<work-name>/` (same for the other two types);
     - Done (D2 classification): `feat/<work-name>/ → changes/archive/YYYY-MM-DD-feat-<work-name>/`;
  4. **Spike migration rules** (core decision, all under `changes/`):
     - Has an impl counterpart (same or similar name) → **merge**: fold the spike's analysis/findings into the counterpart's analysis.md as a predecessor reference section, **delete** the spike directory;
     - No counterpart and verdict FEASIBLE → `changes/archive/YYYY-MM-DD-spike-<work-name>/` (all three docs);
     - No counterpart and verdict NOT_FEASIBLE → `changes/archive/YYYY-MM-DD-spike-<work-name>/` and mark it (this is a valuable "no" record);
     - Verdict missing → `changes/archive/YYYY-MM-DD-spike-<work-name>/`, report flagged "verdict missing";
  5. Incomplete items → stay in the active `changes/<type>/` directory; if analysis.md lacks Success Criteria, add an empty template;
  6. Non-convention dirs (`docs/`, `changelog/`, `errors/`, `user-survey/`) → **untouched**, only listed in the report;
  7. Write the migration report: `<docs-dir>/MIGRATION-REPORT.md` (per item: old path → new path / action / reason / warning), commit the docs repo.
- **Boundary**: only the docs repo is modified, never any code repo; uncertain items are **reported, not guessed**.
- **description draft**:
  > Migrate a fullstack docs repo from the legacy structure (spike/ directories, Status fields, no archive) to the new explore/propose/apply/archive structure. Use when the user points at an existing docs directory and wants it reorganized. Provide the docs repo path to start.

---

## 4. Documentation Conventions

### 4.1 Target structure for `docs/fullstack/` (OpenSpec docs layering)

| File | Role | Reference |
|---|---|---|
| `README.md` | Index: three layers ("read these two pages" → "Pick your path" routing → grouped full map + 30-second version) | OpenSpec `docs/README.md` |
| `overview.md` | One-screen mental model: `explore → propose → apply → archive` one-liner + ASCII diagram + honest tradeoff | OpenSpec `docs/overview.md` |
| `concepts.md` | Ontology: `changes/` structure, four documents, Success Criteria → Evidence, archive naming semantics (`YYYY-MM-DD-<type>-<work-name>`). Each section What → Example → Why | OpenSpec `docs/concepts.md` |
| `workflows.md` | Process: which skill for which situation, `X vs Y` decision sections, mermaid flowchart + sequenceDiagram (Human/Assistant/CLI/Files) | OpenSpec `docs/workflows.md` |
| `REFACTOR-PLAN.md` | This document (transitional; may be archived once the refactor is absorbed into the formal docs) | — |

**Disposition of the existing 3 design docs**:

| Old doc | Disposition |
|---|---|
| `FULLSTACK-INIT.md` | Core content merged into the new `concepts.md` (init is setup, not lifecycle), original deleted |
| `FULLSTACK-IMPL.md` | Content split: Steps 1–5 → propose docs, Steps 6–9 → apply docs, original deleted |
| `AGENT-ORCHESTRATION.md` | **Kept** (the subagent orchestration model is still valid), or merged into `concepts.md` as a section (undecided) |

**Writing conventions** (adopted from OpenSpec's proven patterns):
- Lede either way: thesis-style bold assertion (`**The one thing to know: ...**`) for idea docs, neutral positioning + cross-link for reference docs;
- First paragraph cross-links neighbors; `## Next Steps` / `## Where to go next` closer (written as "question → link" branches);
- Concept diagrams in ASCII (diff-friendly), flows in mermaid `flowchart TD`, responsibility boundaries in `sequenceDiagram`;
- Honest tradeoffs ("The strength here is… The tradeoff is…");
- End each doc with `## A quick checklist` where applicable.

### 4.2 Unified SKILL.md skeleton

All fullstack skills share one skeleton (bold-line sections; `##` is reserved for Output template examples):

```markdown
---
name: fullstack-<verb>
description: <formula per 4.3>
license: Apache-2.0
---

<one-line action statement>

**<Boundary>**: …           # optional: permission/scope boundary (propose MUST have Planning boundary)

<prose paragraph on what this skill produces>

---

**Input**: …
**Steps**                     # numbered + bold step names + code blocks
1. **…**
**Output**                    # copyable literal templates (split by state)
**Guardrails**                # closing bullet list
```

Rules:
- Key boundaries are stated **twice** (opening declaration + closing Guardrails restate);
- Output gives copyable literal templates, not "please report the following";
- Skeleton exceptions allowed (explore is a stance skill with a custom structure), but frontmatter and Guardrails are always kept;
- Hardcoded path / install-path candidate lists move out of SKILL.md into each skill's `scripts/` or shared assets.

### 4.3 description formula

`<imperative capability statement>. Use when the user wants to <trigger 1>, <trigger 2>, or <trigger 3>.`

- First sentence starts with an imperative verb (Explore / Propose / Implement / Archive), not self-referential ("This skill…");
- Second sentence fixed as `Use when the user wants to …`, listing 2–3 trigger intents;
- Each description embeds a differentiator vs its neighbor skill (OpenSpec style: `in one step` / `without archiving` / `Never edits code`);
- Ambiguity-prone skills add a negative third sentence;
- ≤1024 characters (checked by `scripts/validate-skill-descriptions.py`).

### 4.4 Work-tracking document template revisions

(Detailed in each skill spec; summarized here):
- `plan.md`: remove `**Status**:`; add `## Success Criteria` (checkbox, testable, non-subjective);
- `analysis.md`: deep mode carries the spike sections; implementation design is appended to the same file after validation;
- `progress.md`: remove `## Iteration Log`; keep dated sections and Changelog;
- `review.md`: add the Evidence table; verdicts normalized to `PASS` / `NEEDS_FIXES` / `BLOCKED`;
- Unify the reference field to `**Source**`, with correct `../../` cascade for relative paths.

---

## 5. Implementation Plan

### Phase 0 — Decision confirmation (this doc's review)

Needs user sign-off (see §7): whether init keeps its name, AGENT-ORCHESTRATION.md disposition, changelog integration, whether progress.md stays.

### Phase 1 — Documentation layer

1. Create `docs/fullstack/README.md` (index) + `overview.md` + `concepts.md` + `workflows.md`;
2. Handle the old 3 docs (rename/split/delete per §4.1);
3. Link `docs/fullstack/` from `README.md` and `docs/DEVELOPMENT.md` (currently orphaned, no index references it);
4. Update `AGENTS.md`: Skill ordering table (add the missing fullstack-query + new names), shared assets table (**add the `graphify_check.py` row**), shared-assets prose.

### Phase 2 — Skill refactor

Order: **build new first, then delete old** so the repo stays runnable at every step.

1. `fullstack-explore`: git mv `fullstack-query` → update frontmatter/description/internal references → add "capture on demand";
2. `fullstack-propose`: create (content from spike + impl Steps 1–5); git rm `fullstack-spike`;
3. `fullstack-apply`: git mv the `fullstack-impl` directory, rewrite SKILL.md (drop the 4 Mode routing/iteration gate), keep the useful scripts and references;
4. `fullstack-archive`: create;
5. `fullstack-docs-migration`: create;
6. `fullstack-init`: update generated copy and directory list (`changes/{feat,refactor,fix,archive}`), keep the name;
7. **Sync the rename blast radius** (checklist in §5.5);
8. Run verification: `sync-shared-assets.py` (materialize + `--check`), `pytest tests/test_shared_assets_sync.py`, `validate-skill-descriptions.py`, `quick_validate.py`, `pytest tests/skills/`.

### Phase 3 — Migration

1. Migrate a real docs repo with `fullstack-docs-migration` (recommended: dry-run on `robo-documents`);
2. Review the migration report, refine the rules;
3. Rebuild `graphify-out/` (`graph.json` has a custom merge driver — **never merge, always rebuild**).

### Phase 4 — Cleanup & release

1. Update `README.md` / `README.zh-CN.md` (skill tables, directory trees, workflow descriptions; also fix the zh-CN README's long-standing omission of fullstack-query);
2. Update `pyproject.toml` `[tool.pyright] extraPaths`;
3. Bump version with `bump-version.py` before `scripts/publish.py` (marketplace/pyproject/__init__ kept in sync);
4. Release notes: **breaking change** — existing installs of `fullstack-impl` etc. stop resolving; users must re-run `/plugin install`;
5. Delete derived artifacts `build/`, `*.egg-info` (do not hand-edit).

### 5.5 Rename blast radius (complete)

| # | Location | Content |
|---|---|---|
| 1 | `.claude-plugin/marketplace.json` | 4 entries' name/source/description/tags rewritten + 2 new entries (archive, docs-migration) |
| 2 | `plugins/` | 4 wrappers `git rm` + symlink recreation (`git mv` does not rewrite symlink content) + 2 new wrappers. Note: recreating symlink targets is **mandatory** |
| 3 | `scripts/sync-shared-assets.py` | `mermaid_consumers` (impl→apply, spike→propose), `graphify_consumers` (init→init, impl→apply, query→explore, spike→propose) tuple rewrite; `AGENTS.md` shared table gains the graphify row |
| 4 | `pyproject.toml:76-77` | `[tool.pyright] extraPaths` two paths renamed |
| 5 | `README.md` (14) / `README.zh-CN.md` (12) | skill names, directory trees, workflow descriptions |
| 6 | `AGENTS.md:283,427,476-477` | skill ordering table + shared assets table |
| 7 | Inside `fullstack-impl/` (34) | SKILL.md self-references, references/ paths, `check_workspace.py`/`route_check.py`/`iteration_log_check.py` docstrings and the 8-line install-path candidate lists (×3) |
| 8 | Inside `fullstack-init/` (20) | `workspace_init.py` generated AGENTS.md/README copy (**written into every initialized workspace**), `.fullstack-init.json` legacy name, argparse help text |
| 9 | Cross-skill (6) | `code-review-staged/references/commit-format.md`, `user-journey` and `shared/mermaid/MERMAID-RULES.md` fullstack references |
| 10 | `tests/skills/` (11) | `test_fullstack_*.py` renamed; `test_shared_assets_sync.py` unchanged (imports by file path, follows automatically) |
| 11 | `graphify-out/` | Must rebuild, never merge (`.gitattributes` merge driver) |
| 12 | `mythril_agent_skills.egg-info/`, `build/` | Derived artifacts, rebuilt not hand-edited |

**Not affected** (confirmed clean): `mythril_agent_skills/cli/` (dynamic discovery), `skills_check.py`'s `CHECKABLE_SKILLS` (no fullstack entries), `tests/test_skills_setup.py`, `.sync-upstream.json`.

---

## 6. Explicitly Out of Scope

| Not doing | Why |
|---|---|
| SDD / spec grammar (SHALL/MUST, `####` four-hashtag, WHEN-THEN) | Explicitly excluded by the user; documents are decision records, not behavior specs |
| OpenSpec CLI / schema-as-data (YAML artifact definitions + dependency DAG) | Violates the skill self-containment rule (`AGENTS.md` hard constraint); requires a 2057-line CLI to support |
| Delta specs / main-spec merge / `openspec validate` | Same, and the 124 work items show no sign of needing a long-lived behavior contract |
| Bulk archive / bulk migration UI | Not a recurring need; the migration skill already covers it |
| Modifying non-convention dirs (docs/, changelog/, errors/) | The user's existing knowledge-base structure; not part of this refactor |

---

## 7. Open Questions (need user sign-off)

1. **Does `fullstack-init` keep its name?** Recommended: yes (not part of the lifecycle; renaming only adds breakage). If renamed, needs a new name and mapping rationale.
2. **`AGENT-ORCHESTRATION.md` disposition?** Recommended: keep as a standalone doc (subagent orchestration is a cross-cutting concern, not a lifecycle stage).
3. **Changelog integration?** `robo-documents`' `robocontrol-changelog/` is the user's manual archive substitute. Should archive append a changelog entry by default, or only when the target dir exists?
4. **Does `progress.md` stay?** Evidence shows it carries the real state (8 spellings) but is also the source of Status chaos. Options: a) keep but log-only; b) slim and merge into plan.md.
5. **Does `fullstack-docs-migration` need a helper script?** Pure SKILL.md instructions (LLM reads files to judge state) vs a lightweight scan script (emits JSON stats, LLM only decides). Leaning toward the latter (aligned with the route_check.py pattern, fewer LLM misses).
6. **Where does a legacy spike's verdict content go when merged into an impl directory?** Recommended: as a `## Predecessor Spike` reference section in analysis.md, not a full inline copy.
7. **`changes/` naming?** `changes/` (OpenSpec-aligned) vs `work/` (closer to "work item" semantics)? Current recommendation: `changes/`.

---

## Appendix: References

- OpenSpec docs & skills: `/Users/jiemeng/workspace/ai/OpenSpec/` (`docs/README.md` three-layer index, `concepts.md` What→Example→Why, `workflows.md` process, SKILL.md unified skeleton, description formula, Planning boundary)
- Empirical data: `robo-documents` (124 work items, see §1.1 table)
- Existing conventions: this repo's `AGENTS.md`, the 3 design docs in `docs/fullstack/`
