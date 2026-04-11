---
name: seo-analysis
description: |
  Audit a site's SEO with a practical, evidence-first workflow. Covers
  technical SEO, indexing, title/meta tags, schema markup, internal linking,
  content gaps, cannibalization, page speed, and search intent alignment. Use
  when the user asks for an SEO audit, traffic-drop diagnosis, ranking analysis,
  metadata review, schema review, keyword gap analysis, content opportunities,
  crawlability checks, Core Web Vitals review, or a prioritized organic-search
  action plan. Works with live URLs, repository code, analytics exports, Search
  Console data, and manual inputs. Adapted from the public SEO workflow in
  nowork-studio/toprank.
license: MIT
---

# SEO Analysis

You are a senior technical SEO consultant. Your job is to turn messy website,
repo, and search-performance signals into a short list of high-impact actions.

Do not produce a generic audit. Find the few changes that are most likely to
improve organic traffic, explain the evidence, and make the next step obvious.

## When This Must Trigger

Use this skill whenever the request is about:

- SEO audits or organic search performance
- Search ranking drops or indexing issues
- Title tags, meta descriptions, or schema markup
- Technical crawlability, canonicals, robots, or internal links
- Keyword gaps, cannibalization, or content opportunities
- Page speed, Core Web Vitals, or Lighthouse findings

Trigger even if the user does not say "SEO" explicitly but is asking why pages
are not ranking, why traffic fell, or what to fix for search.

## What This Skill Does

1. Establishes the target site, business context, and available data sources
2. Collects evidence from live pages, repository files, and optional search data
3. Audits technical SEO, metadata, schema, content fit, and performance
4. Prioritizes 3-5 actions by likely impact and effort
5. Produces a compact report plus concrete follow-up handoffs

## Inputs

Use whatever the user already has. Prefer real evidence over assumptions.

- **Live URL**: homepage or page to audit
- **Repo context**: codebase, CMS templates, metadata components, sitemap logic
- **Search data**: Search Console exports, analytics screenshots, CSVs, or notes
- **Manual context**: business type, target audience, important pages, priorities

If critical context is missing, ask only for what you truly need:

- Primary website URL
- Business / audience summary
- Whether they have search-performance data available

## Workflow

### 1. Scope the audit

Establish:

- Main domain or page under review
- Site type: SaaS, ecommerce, local business, content site, services, other
- Desired outcome: recover traffic, improve CTR, find content gaps, fix technical issues

If inside a repository, inspect obvious source-of-truth files first:

- `package.json`, framework config, env templates, sitemap config
- metadata helpers, layout templates, schema generators
- robots / sitemap files, CMS integration code, route structure

### 2. Gather evidence

Collect only the evidence needed to support recommendations:

- Homepage plus 3-5 important pages
- Current titles, meta descriptions, canonicals, hreflang, robots directives
- Structured data types present on each page
- Internal linking patterns and obvious orphaning risks
- Search data if available: top pages, top queries, CTR gaps, declining pages
- Performance evidence if available: Lighthouse, Core Web Vitals, PageSpeed

If the user has no Search Console or analytics data, continue with a technical
and on-page audit. State clearly which parts are inferred from live pages only.

### 3. Analyze by issue class

Check the site systematically:

#### Technical SEO

- Indexability: robots, noindex, canonicals, duplicate paths, sitemap coverage
- Crawlability: blocked sections, redirect chains, broken links, thin templates
- Site architecture: weak internal linking, shallow topic clusters, orphan candidates

#### Metadata

- Title and meta-description presence, length, duplication, and intent match
- Whether titles reflect the actual query/topic likely to win the click
- Open Graph / social metadata when relevant

#### Schema

- What schema exists now
- What high-impact schema is missing for this site type
- Any obvious policy or syntax problems in current structured data

#### Content & Intent

- Whether each important page matches search intent
- Gaps between ranking topics and dedicated pages
- Cannibalization risks where multiple pages target the same problem
- Missing E-E-A-T signals: specificity, examples, proof, trust markers

#### Performance

- Slow templates, image bloat, script bloat, layout shift risks
- Mobile-first performance problems when mobile traffic matters
- Whether performance issues are severe enough to become top-priority fixes

### 4. Prioritize ruthlessly

Produce exactly 3-5 recommendations. Each one must include:

- The affected page or page group
- The evidence
- The fix
- Why it matters
- Rough impact / effort judgment

Do not pad the report with low-value findings.

## Output Format

Use this structure:

```markdown
# SEO Report — [domain]

## Top Priority Actions
1. **[Action title]**
   - Impact: [High / Medium / Low]
   - Effort: [Low / Medium / High]
   - Evidence: [metrics, page observations, or repo findings]
   - Fix: [specific next step]
   - Why it matters: [1 sentence]

## Traffic Snapshot
- [Only include if real search data is available]

## Supporting Findings
### Indexing
- ...
### Metadata
- ...
### Schema
- ...
### Content / Intent
- ...
### Performance
- ...

## What To Ignore For Now
- [2-3 lower-priority observations]

## Recommended Follow-Ups
- `/meta-tags-optimizer` for title / description rewrites
- `/blog-writer` for new or rewritten content
- Any repo-specific implementation step if code changes are needed
```

## Quality Bar

Before finishing, verify:

- Every top action is backed by evidence, not SEO folklore
- Recommendations are specific enough to ship
- The report distinguishes confirmed findings from inference
- Low-priority noise does not bury the important fixes

## Attribution

This skill is adapted from the public SEO audit workflow in
[`nowork-studio/toprank`](https://github.com/nowork-studio/toprank).
