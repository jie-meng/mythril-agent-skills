# Commit Message & PR Title Format — Single Source of Truth

This file defines the canonical commit message format used by the
`code-review-staged` skill (recommended commit message) and the
`github-pr-create` skill (PR title). It is the single source of truth
— if a downstream caller needs to format a commit message or PR title,
it MUST follow this document.

The format follows [Conventional Commits](https://www.conventionalcommits.org/)
with strict rules for how `scope` is derived from the branch name, so
the same branch always produces the same scope across repos and
across sessions.

## Format

```
<type>[scope]: <subject>
```

- All English. Single line. Max 72 characters total.
- `<type>` from a fixed enum (see "Type" below).
- `[scope]` automatically derived from branch name (see "Scope
  derivation rules" below). May be omitted if the branch has no
  reliable scope source — in that case use `<type>: <subject>`.
- `<subject>` written by the agent based on the actual diff.

## Type

The type comes from the branch's leading segment when present, else
fall back to the diff's nature:

| Branch starts with | Type |
|--------------------|------|
| `feat/` | `feat` |
| `fix/` | `fix` |
| `refactor/` | `refactor` |
| `docs/` | `docs` |
| `test/` | `test` |
| `chore/` | `chore` |
| (anything else, including bare `master` / `main` / `dev`) | Pick the best fit from the enum based on the diff content; `chore` is the safe default for non-functional / version / config changes |

The full enum: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`,
`perf`, `style`, `build`, `ci`. Use `feat`/`fix`/`refactor`/`docs`/
`test`/`chore` for 95% of cases — the others are rarely needed.

## Scope derivation rules

Scope is automatically derived from the branch name. NEVER use the
**repository name** as scope — repo identity belongs in the PR
metadata, not the commit subject. NEVER invent a scope from thin air;
follow the rules below mechanically.

### Rule 1: three-segment branch with Jira → JIRA key (preferred)

When the branch is `<type>/<JIRA-KEY>/<Title>` (three segments
separated by `/`), the scope is the JIRA key with original casing
preserved.

- The Jira key is automatically detected as a segment matching
  `^[A-Z][A-Z0-9]+-\d+$` (one or more uppercase letters / digits, a
  dash, then digits — e.g. `XYZ-190`, `BE-450`, `ABC123-7`).
- iter / version suffixes on the Title segment do NOT change the scope.

| Branch | Scope |
|--------|-------|
| `feat/XYZ-190/Add-Export` | `XYZ-190` |
| `fix/BE-450/Token-Refresh-Bug` | `BE-450` |
| `feat/MOBILE-301/Dark-Mode-Toggle-iter-2` | `MOBILE-301` |
| `feat/XYZ-580/Add-Export-v2` | `XYZ-580` |

### Rule 2: two-segment branch without Jira → derived from Title

When the branch is `<type>/<Title>` (no Jira key), derive the scope
from `<Title>`:

1. Lowercase the title and replace title-case hyphens with normal
   hyphens — `Dark-Mode-Toggle` → `dark-mode-toggle`.
2. **Strip iter suffixes**: drop trailing `-iter-N` (one or more
   digits). Iter is a per-round naming convention that should NOT
   affect the commit's logical scope — all iterations of the same
   work item share the same scope.
3. **Keep version suffixes**: `-v2`, `-v3`, etc. STAY in the scope.
   Versions are real follow-up work items with semantic meaning
   ("dark-mode v2 = the follow-up" is information worth preserving).
4. If the resulting scope is **30 characters or fewer**, use it as-is.
5. If it exceeds 30 characters, run "Long-title compression" below.

| Branch | Scope |
|--------|-------|
| `feat/Dark-Mode-Toggle` | `dark-mode-toggle` |
| `feat/Dark-Mode-Toggle-iter-2` | `dark-mode-toggle` |
| `feat/Dark-Mode-Toggle-v2` | `dark-mode-toggle-v2` |
| `fix/Battery-Charging-Inverted` | `battery-charging-inverted` |
| `refactor/Refine-Models` | `refine-models` |

### Rule 3: long title (>30 chars after lowercasing) → compress

When the lowercased title exceeds 30 characters, compress it to a
short noun-phrase identifier. Goal: scope is an **identifier**, not a
description.

Algorithm:

1. **Drop filler words**: remove these tokens (case-insensitive)
   anywhere in the title:
   - Verbs: `add`, `update`, `remove`, `refactor`, `improve`,
     `implement`, `introduce`, `create`, `delete`, `fix`, `enhance`,
     `enable`, `disable`, `make`, `support`
   - Connectives: `the`, `a`, `an`, `for`, `to`, `with`, `from`, `of`,
     `in`, `on`, `and`, `or`, `into`, `via`
   - Generic suffixes that add no info: `logic`, `flow`, `feature`,
     `support`, `system` (only if there are stronger words to keep)
2. Take the **first 2-3 remaining words** that carry meaning.
3. If the result is still > 30 chars, drop the last word and repeat.
4. If the result is < 8 chars (over-compressed), back off and keep
   the original 3-word version even if it's slightly over 30 chars
   (a slightly-too-long scope is better than a meaningless 5-char one).
5. Always keep `-vN` if the original branch had it.

| Branch | Compression steps | Scope |
|--------|-------------------|-------|
| `feat/Add-User-Profile-Settings-Page` | drop `add`, `page` → `user-profile-settings` | `user-profile-settings` |
| `refactor/Refactor-Authentication-Token-Refresh-Logic` | drop `refactor`, `logic` → `authentication-token-refresh` | `authentication-token-refresh` |
| `feat/Implement-Real-Time-Collaborative-Editing-With-Conflict-Resolution` | drop `implement`, `with` → `real-time-collaborative-editing-conflict-resolution` (51) → drop tail → `real-time-collaborative-editing` (30) | `real-time-collaborative-editing` |
| `feat/Implement-Real-Time-Collaborative-Editing-With-Conflict-Resolution-v2` | same + keep `-v2` | `real-time-collaborative-editing-v2` |
| `fix/Fix-iPad-BLE-Connection-Drops-After-Background` | drop `fix`, `after` → `ipad-ble-connection-drops-background` (37) → drop tail → `ipad-ble-connection-drops` (25) | `ipad-ble-connection-drops` |

### Rule 4: bare branches without `/` → no scope

When the branch is `master`, `main`, `dev`, or any branch without a
`/` separator, do NOT invent a scope. Use the conventional
no-scope form `<type>: <subject>`.

| Branch | Format |
|--------|--------|
| `master` | `chore: bump version to 1.2.0` |
| `main` | `fix: handle empty config gracefully` |
| `my-experiment` | `feat: prototype the new pricing model` |

### Rule 5: total length budget — subject must fit

The full line MUST NOT exceed 72 characters. Math:

```
"feat[" + scope + "]: " + subject  ≤ 72
"feat[XYZ-190]: " (15 chars) + subject (≤ 57) → fits comfortably
"feat[real-time-collaborative-editing-v2]: " (42 chars) + subject (≤ 30) → tight
```

When subject would have to be shorter than ~30 chars to fit, drop the
scope entirely and use `<type>: <subject>` instead. Rationale: scope
is a redundant locator (the branch name carries the same info), but
subject is unique information about THIS commit.

| Situation | Recommended form |
|-----------|------------------|
| `feat[XYZ-190]:` + 50-char subject | Keep scope |
| `feat[real-time-collaborative-editing-v2]:` + 30-char subject | Keep scope, tighten subject |
| `feat[real-time-collaborative-editing-v2]:` + can't shrink subject below 30 | Drop scope: `feat: <full subject>` |

## Subject rules

The subject is the only part the agent fully writes from scratch.
Constraints:

- **Imperative mood, present tense, no period.**
  - Good: `add export endpoint for user reports`
  - Bad: `added export endpoint`, `adds export endpoint`, `Adds export endpoint.`
- **Lowercase first letter** (Conventional Commits convention).
- **No filler**: don't say `Implement code to ...`, just `implement
  ...`. Don't say `This commit adds ...`, just `add ...`.
- **One sentence covering all the changes**, even multi-file commits.
  Don't enumerate every file.
- **No marketing words** (`comprehensive`, `robust`, `seamlessly`,
  `elegant`).
- **English only.**

## PR title format

The PR title uses the **same format** as the commit message. When the
PR has a single commit, the PR title equals that commit's message.
When the PR has multiple commits, the PR title uses the same scope
(derived from the branch name) but the subject summarizes the whole
PR's intent.

Examples:

- Branch `feat/XYZ-190/Add-Export` → PR title `feat[XYZ-190]: add CSV and JSON export endpoints`
- Branch `feat/Dark-Mode-Toggle-v2` → PR title `feat[dark-mode-toggle-v2]: add follow-system option`

## Cross-repo consistency (multi-repo work items)

When the same feature ships across multiple repos as part of a single
work item (e.g. `fullstack-impl`), every affected repo should use the
**same scope** so the commits are easy to correlate by `git log
--grep` or PR search:

```
robo-server   commit:  feat[XYZ-190]: add version field to RoboDevice
robo-pack-lite commit: feat[XYZ-190]: inject app version in fetchCharacterInitData
android       commit:  feat[XYZ-190]: send app version on character init
```

Or without Jira:

```
robo-server   commit:  feat[device-version-tracking]: add version field to RoboDevice
robo-pack-lite commit: feat[device-version-tracking]: inject app version in fetchCharacterInitData
android       commit:  feat[device-version-tracking]: send app version on character init
```

The repo name does NOT belong in the scope — it is already implicit
from the repository the commit lives in, and including it makes
cross-repo correlation harder, not easier.

## Anti-patterns to refuse

| Anti-pattern | Why it's wrong | Correct |
|--------------|---------------|---------|
| `feat[robo-server]: add version field` | Repo name in scope; cross-repo correlation harder | `feat[XYZ-190]: add version field` or `feat[device-version-tracking]: add version field` |
| `feat: Add export endpoint.` | Capitalized + trailing period | `feat: add export endpoint` |
| `feat[XYZ-190]: This commit adds CSV and JSON export endpoints with comprehensive validation` | Filler + marketing + over-72 chars | `feat[XYZ-190]: add CSV and JSON export endpoints` |
| `feat[Add-User-Profile-Settings-Page]: ...` | Title-case + verb + not compressed | `feat[user-profile-settings]: ...` |
| `feat[dark-mode-toggle-iter-3]: ...` | iter suffix in scope | `feat[dark-mode-toggle]: ...` |
| `feat[main]: bump version` | Bare branch shouldn't synthesize a scope | `chore: bump version to 1.2.0` |
