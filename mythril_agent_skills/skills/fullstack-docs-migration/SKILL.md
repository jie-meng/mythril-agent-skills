---
name: fullstack-docs-migration
description: |
  Migrate a fullstack docs repo from the legacy structure (top-level
  feat/fix/refactor/spike directories, Status fields, no archive) to the
  new explore/propose/apply/archive structure (changes/ container with
  feat/fix/refactor subdirectories and changes/archive/). Reorganizes
  work directories, merges legacy spikes into their implementation
  counterparts, moves completed work into the archive, and writes a
  migration report. Trigger: "fullstack docs migration", "迁移文档",
  "migrate the docs repo", "reorganize docs", "迁移工作目录". Use when
  the user points at an existing docs repository initialized by an older
  version of the fullstack skills and wants it reorganized. The user
  only needs to provide the docs repo path.
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

## Step 1 — Scan the Repo

Run the bundled scanner to inventory the legacy structure:

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
- `last_active` — last modification date (from `progress.md` content or
  git log).
- `matching_spike` — a legacy spike directory with the same or similar
  name, if any.
- `verdict` (spikes) — `FEASIBLE` / `NOT_FEASIBLE` /
  `NEEDS_MORE_RESEARCH`, or empty if missing.

If the scanner reports an error (not a docs repo, unreadable), stop and
report.

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
| **Merge spike** | spike has an impl counterpart (same/similar name) → fold spike docs into the counterpart's `analysis.md` as a `## Predecessor Spike` reference section, then delete the spike directory |
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

For **spike merges**:

1. Read the spike's `analysis.md`, `findings.md`, `verdict.md`.
2. Append a `## Predecessor Spike` section to the counterpart's
   `analysis.md` referencing the spike directory (use a relative link
   with correct `../../` depth) and summarizing the verdict.
3. Delete the spike directory with `git rm -r`.

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
| spike/oauth-pkce | merged into changes/feat/oauth-pkce | FEASIBLE |
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
- Spike merges preserve the record (reference section + verdict), they
  do not discard it.
- The migration is committed as one atomic docs-repo commit; the report
  documents every decision so it is auditable.
