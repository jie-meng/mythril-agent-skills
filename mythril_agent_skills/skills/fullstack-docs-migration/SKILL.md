---
name: fullstack-docs-migration
description: >
  Migrates a fullstack docs repo from the legacy layout (top-level
  feat/fix/refactor/spike dirs, Status fields, no archive) to the
  changes/{feat,refactor,fix,archive}/ layout: reorganizes work dirs, merges
  spikes into their implementation, archives completed work, and writes a
  migration report. Use when the user points at a docs repo created by an
  older version of the fullstack skills. Triggers: "fullstack docs migration",
  "migrate the docs repo", "迁移文档", "迁移工作目录".
license: Apache-2.0
---

# Fullstack Docs Migration

Reorganize an existing docs repo from the legacy fullstack structure to
the new `changes/` structure. This is a **one-time** migration tool —
run once per docs repo, then use the normal lifecycle skills.

## What the new structure looks like

```text
<docs-dir>/
├── changes/
│   ├── feat/<work-name>/            # active
│   ├── refactor/<work-name>/
│   ├── fix/<work-name>/
│   └── archive/YYYY-MM-DD-<type>-<work-name>/   # completed
├── …                                   # non-convention dirs (untouched)
└── MIGRATION-REPORT.md                 # written by this skill
```

## What the legacy structure looks like

```text
<docs-dir>/
├── feat/<name>/   ├── refactor/<name>/   ├── fix/<name>/   ├── spike/<name>/
└── …              # non-convention dirs
```

Legacy work directories have `analysis.md` / `plan.md` / `progress.md` /
`review.md` (impl work) or `analysis.md` / `findings.md` / `verdict.md`
(spike work), and `plan.md` carries a `**Status**:` field.

## Input

The user provides the docs repo path. If they don't, ask for it. The
migration runs inside that directory. No code repos are touched.

## Language Selection

The migration report and user-facing messages match the language of
the user's prompt.

1. If the user **explicitly requests a language** → use that language.
2. If the user's prompt contains **any Chinese characters** → use Chinese.
3. Otherwise → use English (default).

This does NOT affect directory names the migration creates (always
lowercase-hyphenated English) and does NOT rewrite the body of migrated
documents — their existing language stays as it is.

## Step 1 — Scan the Repo

Run the bundled scanner to inventory the legacy structure. `SKILL_PATH` is this skill's installed directory (the folder holding this SKILL.md); run scripts from the user's working directory, not from inside it.

```bash
python3 SKILL_PATH/scripts/migrate_scan.py <docs-dir>
```

The scanner outputs machine-readable JSON:

```json
{
  "work_items": [
    {
      "old_path": "feat/add-dark-mode",
      "type": "feat",
      "name": "add-dark-mode",
      "four_files": {"analysis": true, "plan": true, "progress": true, "review": true},
      "plan_status": "In Progress | Done | ...",
      "progress_status": "...",
      "last_active": "2026-05-03",
      "last_active_source": "git | progress | mtime",
      "matching_spike": "spike/add-dark-mode"
    }
  ],
  "spikes": [
    {"old_path": "spike/oauth-pkce", "name": "oauth-pkce", "verdict": "FEASIBLE", "impl_counterpart": null}
  ],
  "non_convention_dirs": ["docs", "changelog", "errors", "user-survey", "scripts", "graphify-out"]
}
```

- `four_files` — which of the four work-tracking documents exist.
- `plan_status` — raw `**Status**:` text from `plan.md` (may be empty).
- `progress_status` — completion marker from `progress.md` (may be empty).
  Status lines decide; whole words only, negations ("not done", "almost
  complete"), headings, and unchecked checklist items never count.
- `last_active` — last activity date: the last git commit touching the
  directory, else the latest date written in `progress.md`, else the
  newest file mtime. `last_active_source` says which; treat `mtime` as
  weak evidence (a copy or checkout resets it).
- `matching_spike` — a legacy spike directory whose normalized name
  (case-insensitive, `-`/`_` equivalent) equals the work item's, if any.
- `verdict` (spikes) — `FEASIBLE` / `NOT_FEASIBLE` /
  `NEEDS_MORE_RESEARCH`, or empty if missing.

If the scanner exits non-zero (1 = not a git repository, 2 = bad
argument or not a directory), stop and report its `ERROR:` line.

Before moving anything, check `git -C <docs-dir> status --short` is
empty; if not, ask the user to commit or stash first, so the migration
commit contains only the migration.

## Step 2 — Classify Each Work Item

For every work item, decide: **active** or **done**.

| Signal | Active | Done |
|--------|--------|------|
| `progress_status` | no completion marker, or "In Progress" | "Complete", "Done", "已完成", "已合并", etc. |
| `last_active` | recent (within ~30 days) | old (beyond ~30 days) |
| `plan_status` | Planning / In Progress | Done / Closed |

**Conflict rule**: if signals disagree, prefer `progress_status` +
`last_active` over `plan_status` (the Status field is the least reliable
— it was filled in only 7% of real work items). Record the conflict in
the migration report.

**Uncertainty rule**: if you genuinely cannot tell whether an item is
done, treat it as **active** (do not archive something the user may
still be working on) and flag it in the report for the user to confirm.

## Step 3 — Plan the Moves

Create a migration plan — every move as `old_path → new_path` with an
action and reason. Present the summary to the user for confirmation
before executing:

| Action | Rule |
|--------|------|
| **Move active** | `feat/<name>/ → changes/feat/<name>/` (same for refactor/fix) |
| **Archive done** | `feat/<name>/ → changes/archive/YYYY-MM-DD-feat-<name>/` |
| **Merge spike** | spike has an impl counterpart (`matching_spike`) → archive the spike like an orphan (row below) AND add a `## Predecessor Spike` section to the counterpart's `analysis.md` that links to the archived spike. The spike's files are never deleted — the link must resolve |
| **Archive orphan spike** | spike has NO impl counterpart → `spike/<name>/ → changes/archive/YYYY-MM-DD-spike-<name>/` (this preserves the record — including NOT_FEASIBLE verdicts, which are valuable "no" records) |
| **Leave untouched** | `docs/`, `changelog/`, `errors/`, `user-survey/`, and other non-convention dirs — never move or modify them |

**Date for archived items**: use the work item's **last active day**
(from Step 1), not today — this preserves the historical timestamp.
For spikes with no usable date, use today.

**Archive name**: `YYYY-MM-DD-<type>-<name>` where `<type>` is `feat` /
`fix` / `refactor` / `spike` taken from the source parent directory.

## Step 4 — Execute the Moves

Execute the confirmed plan:

```bash
# Create the changes/ container
mkdir -p <docs-dir>/changes/{feat,refactor,fix,archive}

# Move each work item per the plan
mv <docs-dir>/feat/<name> <docs-dir>/changes/feat/<name>       # active
mv <docs-dir>/feat/<name> <docs-dir>/changes/archive/YYYY-MM-DD-feat-<name>   # done
```

For **spike merges** (after the counterpart has moved to its final
location):

1. Archive the spike: `git mv <docs-dir>/spike/<name>
   <docs-dir>/changes/archive/YYYY-MM-DD-spike-<name>` (plain `mv` if it
   is untracked).
2. Read the spike's `analysis.md`, `findings.md`, `verdict.md`.
3. Append a `## Predecessor Spike` section to the counterpart's
   `analysis.md`: a relative link to the ARCHIVED spike directory and a
   short summary of the verdict. The depth depends on where the
   counterpart landed:
   - active `changes/<type>/<name>/analysis.md` →
     `../../archive/YYYY-MM-DD-spike-<name>/`
   - archived `changes/archive/<dir>/analysis.md` →
     `../YYYY-MM-DD-spike-<name>/`
4. Verify the link target exists before committing.

Migration moves directories; it rewrites no document body, so a `plan.md`
that already carries a `## 代码地图` / `## Code Map` keeps it untouched.
Legacy items have no such table, and the linter errors on that as soon as
someone touches their code — so list in the report which migrated items
lack a Code Map. Do not invent rows for them from dates or guesses: the
table is the item's ownership claim, and a wrong row sends a later
`--find` to the wrong spec. Backfill each one from that item's
`### Changed files` / `### 改动文件` records when it is next worked on.

## Step 5 — Write the Migration Report

Write `<docs-dir>/MIGRATION-REPORT.md`:

```markdown
# Docs Migration Report

**Date**: <date>
**Source**: <legacy structure>
**Target**: changes/ structure

## Work items
| Old path | New path | Action | Reason |
|----------|----------|--------|--------|
| feat/add-dark-mode | changes/archive/2026-05-03-feat-add-dark-mode | archive | progress=Complete, last_active 2026-05-03 |

## Spikes
| Old path | Action | Detail |
|----------|--------|--------|
| spike/oauth-pkce | archived as changes/archive/2026-04-02-spike-oauth-pkce, linked from changes/feat/oauth-pkce | FEASIBLE |
| spike/harmonyos-support | archived | orphan spike, FEASIBLE |

## Non-convention directories (untouched)
docs/  changelog/  errors/  user-survey/  …

## Warnings
- feat/import-export: status conflict (plan.md=In Progress, progress.md=Complete) — treated as done
- spike/nimble-write-error-propagation: verdict missing — archived with warning
```

## Step 6 — Commit and Report

1. Commit the docs repo with all moves and the report:

   ```bash
   cd <docs-dir>
   git add -A
   git commit -m "docs: migrate to changes/ structure"
   ```

2. Report the migration summary to the user: counts of active vs
   archived items, spikes merged vs archived, and every warning that
   needs a human decision.
3. Tell the user to re-run `fullstack-init` from the workspace root: it
   creates `issues/` and refreshes the workspace and docs `AGENTS.md`,
   which may still describe the legacy layout.

## Requirements

- Python 3.10+
- A docs repo path provided by the user
- `git` available (the docs repo is a git repo)

## Guardrails

- **Only the docs repo is modified.** No code repo is touched.
- **Non-convention directories are never moved or modified** — only
  listed in the report.
- **Uncertain items are treated as active**, never archived on a guess.
- **Status conflicts are reported, not silently resolved.**
- Spike merges preserve the record: the spike directory is archived, never
  deleted, and the counterpart links to it.
- The migration is committed as one atomic docs-repo commit; the report
  documents every decision so it is auditable.
