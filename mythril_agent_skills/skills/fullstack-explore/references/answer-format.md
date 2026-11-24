# Answer Format

Read this when writing the answer (Step 6). Answers are source-code-based:
documents and graphify say where to look, the answer says what the source
files contain, with file paths and line ranges.

## When documents cover the query (verify mode)

Say which findings come from documents and which from code verification:

```markdown
## Answer
<direct, concise answer>

## Sources

### Document: `<docs-dir>/changes/archive/2025-03-15-feat-oauth-migration/`
- plan.md: auth flow moved to `api/src/auth/`
- Verified in source: `api/src/auth/` is the current auth module ✓

### Code verification
- `api/src/auth/handlers.ts:12-80` — OAuth2 handlers (matches plan.md)
- `api/src/auth/middleware.ts:5-41` — JWT validation (matches plan.md)

### Discrepancies
- plan.md cites `web/src/hooks/useAuth.ts` → now `web/src/hooks/useSession.ts`
```

## When documents are partial or absent

```markdown
## Answer
<direct, concise answer>

## Findings

### <repo-name> (<role>)
- Used graphify: yes / no — documents: <work item or "none">
- `<path>:<lines>` — <what it does>
```

## Always include

1. **Direct answer first.**
2. **Source attribution** — document / graphify / source file, per finding.
3. **Staleness notes** — where documents or graphify disagree with the
   source; the source wins.
4. **Key files** — paths verified by reading them, not graph-reported
   paths alone.
5. **What was spot-checked** — which key findings were confirmed in source.
