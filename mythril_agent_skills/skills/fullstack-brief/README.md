# fullstack-brief

Export the complete context of a multi-repo fullstack workspace (or a single
repo) into **one self-contained, AI-optimized Markdown brief**.

## Why

Solution discussions with a web AI (ChatGPT, Claude.ai, Gemini, ...) are
cheap; every message through a local CLI agent costs tokens. The bottleneck
is getting enough context into that first web message. `fullstack-brief`
automates exactly that: it explores the workspace once and produces a
paste-ready brief, so the expensive context transfer happens locally, one
time, and all follow-up discussion happens on the web.

## What it produces

A single `.md` file written **for an AI reader**, not humans:

- Mission & product overview
- Architecture overview + mermaid diagrams
- Repo/module map with roles, stacks, key entry points
- Key data & control flows
- Code map of load-bearing modules (paths as quoted text)
- Conventions, current work state, domain glossary

Self-contained by construction: no local file/image references, no embeds.
Mermaid source and public internet links are allowed. A mandatory
secret-redaction pass runs before anything is written.

## Modes

| Mode | Detection | Output location |
|------|-----------|-----------------|
| Workspace | `fullstack.json` + `AGENTS.md` + `.agents/` | `<docs-dir>/docs/<name>.md` |
| Single repo | `.git` present, no workspace markers | `<repo>/docs/<name>.md` |

The destination path and filename are always confirmed with the user before
writing. Depth (`quick` / `standard` / `deep`) controls size budget;
optional topic focus allocates extra depth to one area.

## Usage

Trigger phrases: "fullstack brief", "export context", "context handoff",
"生成上下文简报", "导出上下文", "喂给网页AI".

```text
fullstack brief                          # standard depth, whole scope
fullstack brief 深入 支付模块             # deep, focused on payments
quick context brief for this repo        # quick, single repo
```

## Requirements

Python 3.10+, stdlib only. Optional `graphify` CLI accelerates exploration
when knowledge graphs exist; the skill works without it.
