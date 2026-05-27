# Sync Rules

`JOURNEY.md` and `journey.json` MUST agree at all times. The renderer reads JSON; humans read MD; stakeholders see both. Drift produces a journey that says one thing in the doc and another in the demo.

## The mandatory loop

After ANY edit to either file:

```bash
python3 SKILL_PATH/scripts/validate_sync.py <workspace>
```

Exit codes:
- `0` — in sync, OK to continue
- `1` — drift detected, must fix before declaring done
- `2` — workspace structure invalid (missing files)

## What gets compared

| Check | JSON source | MD source | If mismatched |
|---|---|---|---|
| Title | `title` | First H1 line | Auto-fix from JSON |
| Stage count | `stages[].length` | `## Stages` section header count + mermaid node count | Error: list both, ask which is authoritative |
| Stage IDs | `stages[].id` | mermaid node IDs in flowchart | Error: list missing/extra IDs |
| Step count per stage | `stages[*].steps.length` | `### <stage>` subsection bullets in MD | Warning if differ |
| Persona IDs | `personas[].id` | `## Personas` subsection slugs | Error: list missing/extra |
| Language | `language` | filename suffix or YAML hint | Auto-detect from MD |

## Bidirectional edit pattern

When the user requests an edit in plain language ("add a stage between Sign up and First task called Tutorial"):

1. **Write JSON first** — insert the new stage into `journey.json` at the right index.
2. **Regenerate the affected MD sections** from JSON:
   - Update mermaid flowchart line `A --> B` to `A --> NEW --> B`
   - Insert a new `### Tutorial` subsection under `## Stages`
3. **Run `validate_sync.py`** — must pass.
4. **Tell the user** in plain language what changed. Do NOT mention JSON / mermaid / sync internals.

If the user is editing `JOURNEY.md` directly (rare, but possible — they may add a thought or rename a stage):

1. Read both files.
2. Detect what changed in MD that isn't in JSON.
3. Update JSON to match.
4. Re-render the affected MD sections from JSON to normalize formatting.
5. `validate_sync.py`.

## Common drift scenarios

### Renamed stage in MD but not in JSON

The mermaid flowchart and `### <stage>` header use the new name; JSON still has the old `label`. Fix:
- Update `journey.json` `stages[i].label` to the new name (keep the `id` stable — never change IDs as they break wireframe references and presenter slide order).

### Added a step in JSON but forgot to update the MD subsection

`### <stage>` in MD lists 3 bullet points; JSON has 4 steps. Fix:
- Regenerate the entire `### <stage>` subsection from JSON.

### Reordered stages in MD

Mermaid edges `A --> C --> B` but JSON still has `[A, B, C]`. Fix:
- Reorder `journey.json` `stages` array to match MD intent.
- Re-render mermaid from JSON to ensure canonical formatting.

### Deleted a persona referenced by a stage

JSON `personas[]` no longer contains `power-user`, but `stages[2].persona_id` is `power-user`. Fix:
- Either restore the persona or change `stages[2].persona_id` to a valid one.
- Never silently drop the reference.

## Stable ID rule

**`stage.id` and `step.id` are immutable once created.** They are used as:
- Mermaid node IDs
- Presenter mode slide anchors (URL hash routes)
- Wireframe reference keys (if any)
- Git diff stability across renames

To rename a stage in display, change `label` only. Changing `id` is a delete+create operation that destroys cross-references and confuses git history. If the user really wants to delete and recreate, do it explicitly with a confirmation.

## What `validate_sync.py` does NOT check

- Prose quality in JOURNEY.md (the AI is responsible for this)
- DESIGN.md token validity (use `npx @google/design.md lint DESIGN.md` for that)
- Whether the journey is "good" — only whether the two files agree

A sync-clean journey can still be a bad journey. Sync is a precondition, not the goal.
