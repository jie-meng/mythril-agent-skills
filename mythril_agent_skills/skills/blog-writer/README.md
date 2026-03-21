# Blog Writer

Write, refine, and adapt blog posts. Tech-first, but not tech-only.

## Supported Formats

| Format | Typical Length | Key Characteristics |
|---|---|---|
| Personal technical blog | 2000–5000 words | Full narrative arc, code examples, honest limitations |
| Internal email / newsletter | 1000–2000 words | Numbered sections, fast pace, one core value proposition |
| WeChat official account | 1500–3000 words | Mobile-friendly, shorter paragraphs |

## How It Works

The skill guides the AI through four phases:

1. **Context resolution** — Auto-infers language, audience, style, and output path from the user's message and environment. Only asks what it cannot infer. Respects `AGENTS.md` conventions in the target directory.
2. **Research & preparation** — Reads source materials (code, READMEs, URLs, reference articles) to build technical substance.
3. **Writing** — Produces a draft following format-specific rules, style guidelines, and anti-pattern avoidance.
4. **Output & review** — Saves as Markdown, explains choices, provides alternative titles, accepts feedback.

## Usage

Tell your AI assistant what you want to write:

```
写一篇关于我这个开源项目的博客
帮我写一篇内部技术邮件博客，关于 @project-name
Refine this blog post for me
帮我润色一下这篇文章
```

The more context you provide upfront (topic, source materials, target directory), the fewer questions the skill will ask. Provide source materials (code, READMEs, example articles) for best results.

## Prerequisites

- None — this is a pure prompt-based skill with no external dependencies.
