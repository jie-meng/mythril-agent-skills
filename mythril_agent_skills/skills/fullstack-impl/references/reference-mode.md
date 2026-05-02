# Reference Mode — Reading Prior Work as Context

Sometimes the user wants the agent to **read** an existing work
directory as background context — to understand prior decisions,
data models, naming conventions, or constraints — but the new work
is **fundamentally independent** of the prior work. No Predecessor
link. No back-link in the old directory. No `-vN` suffix. Just a
fresh standard work item that benefits from informed context.

This is Reference Mode. It is the safest of the three "looking at
prior work" modes (Reference, Iteration, Follow-up): it never writes
into a prior work directory, never creates a parent-child link, and
never adds a `-vN` suffix that future readers might misinterpret.

> Reading order: this document defines Reference Mode. For the
> three-way comparison, see [`mode-selection.md`](mode-selection.md).
> If the new work actually extends a closed predecessor, use
> [`followup-mode.md`](followup-mode.md) instead.

## When Reference Mode applies

Reference Mode applies when:

1. The user wants the agent to read one or more existing work
   directories under `<docs-dir>/{feat,refactor,fix}/` for context
   — typically a closed predecessor, occasionally an in-progress
   peer.
2. The new work is independent in scope, naming, ownership, and
   lifecycle. It would have started identically even if the
   referenced work did not exist.
3. The user does NOT want a Predecessor / Successor relationship.

If condition 2 or 3 is uncertain, ASK before proceeding. The wrong
mode is expensive: choosing Follow-up when the user wanted
Reference creates phantom parent-child links across two directories;
choosing Reference when the user wanted Follow-up loses the audit
trail.

## Triggers — explicit reading verbs

Enter Reference Mode when the user uses an explicit reading /
referencing verb tied to a prior work directory or its docs:

| Language | Phrasing |
|----------|----------|
| English | "look at feat/X", "read feat/X docs", "based on the X docs", "reference feat/X", "use feat/X for context", "check the X analysis", "see what we did in feat/X" |
| Chinese | "参考 feat/X", "看一下 feat/X", "看看 feat/X 文档", "基于 feat/X 的文档", "X 当背景", "X 当参考", "看下 feat/X 的 analysis" |

Critical distinguishing test: the verb is **about reading** ("look",
"read", "reference", "参考", "看"), NOT about extending ("follow up",
"extend", "在...基础上", "build on top"). The latter is
[Follow-up Mode](followup-mode.md).

If a sentence mixes both ("look at feat/dark-mode and build on top
of it"), the **building** verb wins — that is Follow-up Mode. ASK
the user if you are uncertain.

## How Reference Mode is different from Follow-up Mode

| Aspect | Reference Mode | Follow-up Mode |
|--------|---------------|----------------|
| Reads prior work's 4 docs | Yes | Yes |
| Writes into prior directory | **No** | **Yes** (appends `## Successors`) |
| New work directory naming | Free naming (e.g. `feat/theme-customization/`) | `<predecessor>-vN/` |
| Branch naming | Standard (no `-vN`) | `<title>-vN` |
| `Predecessor:` field in headers | **No** | **Yes** |
| `## Predecessor Context` section | **No** (may freely cite in prose) | **Yes**, mandatory 4 sub-sections |
| Backward-compat check (cross-repo review) | Not required | Required |
| Suitable when | Independent new feature with shared background | True continuation of shipped work |
| Reversibility cost | Zero (rename is enough) | High (must clean two directories + amend git) |

## Execution flow

Reference Mode runs the **standard** Steps 1-9 with two small
additions:

### Step 1 — Gather Context (extended)

In addition to the standard context gathering:

1. Read the named prior work directory's four documents in full
   (`analysis.md`, `plan.md`, `progress.md`, `review.md`). If the
   prior work has its own `## Successors` table, also briefly scan
   the latest successor.
2. Note the prior work's status (Closed / Done / In Progress) — this
   does NOT change the routing, but it informs how stable the cited
   information is. Closed work has stable decisions; in-progress
   work may still change.

### Step 5 — Create Work Plan (light citation)

The new work directory is created with a fresh, free name following
the standard rules. The four documents follow the standard templates
in [`document-templates.md`](document-templates.md) — no Predecessor
field, no Predecessor Context section.

When the new `analysis.md` cites the referenced work, do so in
**prose links**, not in structured fields. For example:

- Good: `Following the theming pattern established in [feat/dark-mode/](../dark-mode/), this work introduces ...`
- Good: `See [feat/dark-mode/analysis.md](../dark-mode/analysis.md) for the underlying theme model that this work extends with custom palettes.`
- Bad (this would be Follow-up Mode): `**Predecessor**: feat/dark-mode/`
- Bad (this would be Follow-up Mode): writing a `## Predecessor Context` section.

### Step 9 — Finalize (no extra gates)

The four-file consistency gate runs as standard. There is no
Predecessor field to verify and no back-link to write.

## What does NOT happen in Reference Mode

- The prior work directory is **not modified**. No `## Successors`
  row appended.
- No `-vN` suffix on directory or branch names.
- No `Predecessor:` header field.
- No mandatory `## Predecessor Context` section.
- No cross-repo backward-compat check (unless the new work
  legitimately consumes the predecessor's shipped contracts and
  must stay compatible — but in that case the user should consider
  whether this is actually Follow-up Mode).

## Promoting Reference → Follow-up mid-flight

If, during planning, the agent realizes the new work IS actually
extending the prior work (e.g. it starts touching the same
endpoints, modifying the same data model in incompatible ways), it
should pause and ask the user:

```
On reflection, this looks more like a true follow-up to feat/dark-mode/
than an independent piece of work. Switching modes would mean:

  - Renaming the new dir to feat/dark-mode-v2/
  - Adding `Predecessor: feat/dark-mode/` to analysis.md and plan.md
  - Writing a `## Predecessor Context` section
  - Appending a `## Successors` row to feat/dark-mode/progress.md
  - Adding -v2 to the new branch names
  - Adding a backward-compat check in Step 7

Should I switch to Follow-up Mode, or stay in Reference Mode?
```

If the user agrees, switch and apply the conversions. If not, stay
in Reference Mode and continue.

The reverse demotion (Follow-up → Reference) is uncommon and harder
because it requires deleting the back-link from the predecessor.
Avoid it by asking up-front when the route is ambiguous, instead of
guessing Follow-up.

## Anti-patterns to refuse

| Anti-pattern | Why it's wrong | Correct behavior |
|--------------|---------------|------------------|
| Auto-add a Predecessor field "just in case" because you read the prior docs | Predecessor implies a parent-child commitment; "just in case" creates phantom relationships | Cite in prose only; do not add the field unless it is a real Follow-up |
| Append `## Successors` to the prior work's `progress.md` "to be helpful" | Modifies a closed work item without justification | The back-link is reserved for Follow-up Mode; do not write it in Reference Mode |
| Use `-v2` directory naming in Reference Mode | The `-vN` suffix is reserved for Follow-up Mode; misusing it confuses future readers | Use a fresh free name |
| Treat Reference as Follow-up because the scope overlaps | Follow-up requires explicit user intent; overlap alone is not enough | Default to Reference (or fresh) and ASK if you are not sure |
