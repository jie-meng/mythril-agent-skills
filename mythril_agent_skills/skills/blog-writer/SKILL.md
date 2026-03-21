---
name: blog-writer
description: >
  Write, refine, and adapt blog posts. Tech-first but supports any topic.
  Trigger when user asks to "write a blog", "draft an article", "refine this post",
  "写博客", "写一篇文章", "帮我写篇博客", "润色这篇文章", "写一篇内部邮件博客",
  "帮我改改这篇博客", "write a technical post", "blog post about",
  "newsletter article", or mentions writing for a personal blog, internal email,
  WeChat official account (公众号), or content channel.
  Auto-infers language, audience, and style from context. Asks only what it
  cannot infer. Outputs Markdown by default. Respects AGENTS.md conventions
  when present in the target directory.
license: Apache-2.0
---

# Blog Writer

Write, refine, and adapt blog posts with a tech-first focus (not tech-only). Supports personal blogs, internal email blogs, WeChat official account articles, and newsletters.

## Core Workflow

### Phase 1: Context Resolution (MANDATORY before writing)

Resolve all parameters before writing. The goal is **minimum friction, maximum signal** — infer everything possible from the user's message and environment, then ask only what is genuinely ambiguous.

#### 1a. Auto-Infer from User Message and Environment

Extract as much as possible without asking:

| Parameter | How to infer |
|---|---|
| **Language** | Match the user's message language. Chinese message → Chinese blog. English message → English blog. If ambiguous (e.g., mixed-language message with no clear dominant language), ask. |
| **Topic** | Extract from the user's message. "写一篇关于 Redis 缓存的博客" → topic is Redis caching. |
| **Format / channel** | Default to **personal technical blog** unless the user says "内部邮件", "newsletter", "公众号", or similar. |
| **Audience** | Default to **fellow engineers** unless the user specifies otherwise. |
| **Tone / style** | Infer from topic type (see style mapping below). Can be overridden later. |
| **Source materials** | If the user referenced files, directories, URLs, or `@`-mentions, those are the source materials. Read them in Phase 2. |
| **Output path** | See "File Output Rules" below. |

**Style mapping** (default tone based on topic type):

| Topic type | Default style |
|---|---|
| Sharing a project / tool / open-source library | Pragmatic, pain-point-first |
| Technical principle / architecture deep-dive | Rigorous, evidence-based |
| Framework / tool comparison | Analytical, judgment-driven |
| Incident postmortem / lessons learned | Honest, retrospective |
| Personal reflection / non-technical | Casual, show the journey |
| Concept explainer | Analogy-driven, light teaching tone |

#### 1b. Identify Gaps and Confirm

After extracting what you can, assess what's missing. There are three possible outcomes:

**Case 1 — Everything is clear**: Topic, source materials (or clearly not needed), and output path are all known. Proceed directly to Phase 2. Show a one-line summary of what you're about to write before starting research:

> 收到。中文个人技术博客，关于 mythril-agent-bgm，务实简洁风格，面向工程师。开始研读素材。

**Case 2 — Only topic is missing**: The user said "写篇博客" without specifying what about. Ask for the topic with numbered choices:

> 博客主题是什么？
>
> 1. 分享一个项目 / 工具 / 开源库
> 2. 解析某个技术原理或架构设计
> 3. 对比多个方案 / 框架 / 工具
> 4. 总结踩坑经验 / 故障复盘
> 5. 个人思考 / 非技术话题
> 6. 其他 (请描述)

After the user answers, proceed to Phase 2 (do NOT ask follow-up questions about style/audience/format — use defaults).

**Case 3 — Multiple things are ambiguous**: Present a confirmation block that lists all inferred values and highlights the gaps. The user can confirm, override, or fill in missing values in a single reply.

Example (Chinese):

> 我理解的参数如下，请确认或修改：
>
> - **语言**: 中文
> - **主题**: _（请补充）_
> - **渠道**: 个人技术博客
> - **读者**: 工程师同行
> - **风格**: 务实简洁
> - **素材**: 无（写出来会比较泛，建议提供代码/文档/链接）
> - **存放位置**: `./blogs/`
>
> 回复确认，或修改任意项。

Example (English):

> Here's what I've inferred — confirm or adjust:
>
> - **Language**: English
> - **Topic**: _(please specify)_
> - **Channel**: Personal tech blog
> - **Audience**: Fellow engineers
> - **Style**: Pragmatic and concise
> - **Materials**: None (output may be generic — consider sharing code/docs/links)
> - **Output path**: `./blogs/`
>
> Reply to confirm, or change any item.

**Rules for the confirmation block:**
- Show ALL parameters (inferred + missing) in one place — the user gets a complete picture.
- Mark missing items with _(请补充)_ / _(please specify)_.
- The user can reply with just "ok" / "确认" to accept all defaults, or override specific items like "风格改成轻松有趣" / "style: casual".
- After confirmation, proceed to Phase 2. Do NOT ask further questions.

#### 1c. Handling "Just Write It"

If the user says "just write" / "直接写" without providing a topic or enough context:
- If topic is missing: you MUST ask — a blog without a topic cannot be written.
- If topic is known but no source materials: proceed with a warning that output will be generic. Do NOT block.

### Phase 2: Research & Preparation

1. **Read AGENTS.md / project conventions**: If the output directory (or its parent) contains an `AGENTS.md`, `CLAUDE.md`, or similar convention file, read it. Adopt its style rules, formatting conventions, and structural preferences for the blog. Project-level rules override this skill's defaults where they conflict.
2. **Read source materials**: If the user pointed to code, README files, project directories, or URLs — read them thoroughly. Understand the technical substance before writing.
3. **Study reference articles**: If the user provided example articles for style reference, analyze their structure, tone, paragraph rhythm, and formatting conventions.
4. **Identify the narrative arc**: Plan a "why should I care" hook → problem exploration → solution → honest assessment arc before writing.
5. **Select angles**: If source materials are extensive (large README, many files), identify the 2–3 most interesting angles and propose them to the user for selection before writing.

### Phase 3: Writing

#### Structure

- **Open with a hook**: A specific problem, a relatable frustration, a counterintuitive claim, or a concrete scenario. NEVER open with "随着 XX 技术的发展……" or "在当今数字化时代……"
- **Use informative headings**: H2/H3 headings should tell the reader what they'll learn. Avoid generic headings like "背景介绍" or "总结".
- **End with substance**: Summarize the core conclusion (don't just repeat the body). Include actionable next steps, links, or an honest assessment of limitations.

#### Format-Specific Rules

**Personal blog (default):**
- 2000–5000 words (can be shorter if user requests)
- Full narrative arc from pain point to solution
- Include code examples where relevant (must be runnable, not pseudocode)
- For non-technical topics, replace code with concrete examples, data, or scenarios
- Discuss limitations honestly — this builds trust
- After the draft, provide: 3 alternative titles + 1 SEO meta description

**Internal email blog / newsletter:**
- 1000–2000 words, 5-minute read target
- Use a concise title with a clear core message
- Numbered sections (一、二、三) for easy scanning
- Faster pace: shorter paragraphs, less setup, more conclusions
- End with clear action items (links, install commands)
- Focus on ONE core value proposition — don't try to cover everything

**WeChat official account:**
- 1500–3000 words
- Mobile-friendly: shorter paragraphs, more whitespace
- Can use bold for emphasis on key sentences
- Consider adding a TL;DR at the top

#### Style Rules

- Write in the resolved language and stay consistent throughout.
- Keep code, proper nouns, and product names in their original form.
- If Chinese:
  - Add spaces around English technical terms: `使用 Redis 缓存` not `使用Redis缓存`
  - Use Arabic numerals: `3 个节点` not `三个节点`
  - Use "我" not "笔者"
- If English:
  - Prefer short, clear sentences and concrete claims over abstract phrasing
  - Avoid passive-heavy paragraphs unless needed for clarity
- For other languages, ask whether the user wants formal or conversational tone.
- Have opinions. Make judgments. Avoid empty hedging.
- Vary sentence length.
- One idea per paragraph, max 5 lines per paragraph.

#### Anti-Patterns to Avoid

- **README regurgitation**: Don't copy-paste feature lists, installation steps, or API docs. Summarize by use case, link to the README for details.
- **Exhaustive enumeration**: Don't list every feature. Group by scenario, highlight core value for each group.
- **Empty emphasis**: Don't bold text that isn't actually important.
- **Filler phrases**: No "无需赘述", "相信读者已经了解", "如有不足，欢迎指正".
- **Buzzword soup**: No "赋能", "落地", "闭环", "抓手".

### Phase 4: Output & Review

#### File Output Rules

**Format**: Markdown (`.md`) by default. Only use a different format if the user explicitly requests it.

**File naming**: Lowercase English, hyphen-separated, descriptive. Examples:
- `redis-caching-strategies.md`
- `mythril-agent-bgm-background-music-for-ai-coding.md`
- `skill-management-internal-email.md` (suffix for alternate versions of the same topic)

**Output path resolution** (in priority order):

1. **User-specified path**: If the user explicitly said where to put the file (e.g., "放到 `my-blogs/docs/` 下"), use that path.
2. **AGENTS.md / project conventions**: If the target directory or workspace has an `AGENTS.md` that specifies where blog files go (e.g., "文章保存为 Markdown 文件，放在 `blogs/` 目录下"), follow that convention.
3. **Existing blog directory**: If the workspace has a `blogs/` directory with existing `.md` files, use it.
4. **Current directory**: If none of the above apply, save to the current working directory.

Create parent directories if they don't exist (`mkdir -p`).

#### Post-Draft Deliverables

After the draft:
1. **Explain choices briefly**: Why this opening, this tone, this structure — 2–3 sentences, not a paragraph.
2. **Provide alternatives** (for personal blog format): 3 alternative titles + 1 SEO meta description.
3. **Invite iteration**: Ask if the user wants to adjust tone, length, depth, or emphasis.

#### Editing an Existing Article

When the user asks to edit/refine an existing article (not write from scratch):
- Preserve the author's voice — don't rewrite from scratch.
- Point out logical gaps, unclear explanations, or missing context.
- Suggest specific cuts and rewrites with reasoning.
- Check for "README-ification" and suggest rewrites if found.

## Handling Edge Cases

- **User gives a topic but no source material**: Proceed but warn that output may be generic. For deeply technical topics, suggest what materials would help (e.g., "如果能提供代码仓库或 README，技术细节会更准确").
- **User wants multiple formats from the same content**: Write the primary format first, then adapt. Don't write both simultaneously — the structure and pacing differ.
- **User requests bilingual output**: Draft in one primary language first, then create a localized adaptation.
- **User provides a very long README or codebase**: Don't try to cover everything. Identify the 2–3 most interesting angles and propose them to the user for selection.
- **Conflicting style rules**: AGENTS.md in the target directory takes precedence over this skill's defaults. If AGENTS.md says "use 我们" but the user says "use 我", follow the user's explicit instruction.
