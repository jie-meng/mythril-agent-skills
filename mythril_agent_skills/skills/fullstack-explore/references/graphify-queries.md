# Graphify Queries — the graph path for a repo or the docs repo

Read this when `graphify_check.py` reports `EXISTS` for a repo (or for the
docs directory). The graph is a navigation index: it tells you where to
read, never what is true. Every key claim still gets a source read.

## Docs repo

`cd <docs-dir>` and ask for the documents, not the answer:

```
graphify query "which work items relate to authentication?"
graphify query "what files were changed in the payment refactor?"
graphify query "are there any issues about API versioning?"
```

It indexes all document text, so it finds matches buried in `progress.md`
or `review.md` that directory-name scanning misses.

## Code repo — protocol

1. Read the repo's `AGENTS.md` (if any) for module, class, and function
   names to put into queries.
2. `cd` into the repo — graphify is cwd-based.
3. **One precise question per query.** Broad keyword lists traverse
   thousands of nodes and get truncated.

   | Instead of | Try | Why |
   |---|---|---|
   | `"how does auth work in the codebase"` | `"what does the auth_manager module handle"` | Narrow to a module |
   | `"authentication, JWT validation, WebSocket auth"` | `"where is JWT token signing implemented"` | One question |
   | `"what are all the WebSocket handlers"` | `"show me the WebSocket authentication flow"` | Ask for a flow, not a list |

4. **`TRUNCATED` in the output** → before continuing, raise the budget
   (`--budget 8000`), narrow to a module, or query a symbol
   (`"show me AuthManager"`).
5. **With document context**, verify the documents' claims directly:

   ```
   graphify query "does <path-from-doc> still exist? what does it do now?"
   graphify query "has <module-from-doc> been renamed or restructured?"
   ```

6. Go depth-first by module — finish one module before the next.
7. Only after the graph is exhausted, fall back to grep / file reads for
   the gaps.

## After the graph — verify in source (MANDATORY)

For every key claim (file path, function name, module structure), read
the source file and confirm it. Read enough to understand the logic, not
just the first line. If the source disagrees with the graph, the source
wins — note the discrepancy in the answer.
