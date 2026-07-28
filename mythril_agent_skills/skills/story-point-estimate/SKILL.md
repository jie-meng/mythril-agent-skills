---
name: story-point-estimate
description: |
  Estimate software development effort using Fibonacci story points. Triggers when user
  asks to "estimate", "估点", "估算", "story point", "Fibonacci point", "sprint sizing",
  "effort estimation", "需求估算", "规模估算", "t-shirt sizing", or shares/writes requirements
  (PRD, user stories, functional specs, images, PPT, PDF, Word, Excel, screenshots) and wants
  effort estimates. Works with any input format — text, documents, images, presentations, or
  voice transcripts. Decomposes requirements from a Tech Lead perspective, identifying both
  functional and non-functional needs (security, performance, monitoring, infra, SLA, compliance).
  Assigns Fibonacci points with clear rationale — points reflect effort, complexity, and
  uncertainty combined, NOT person-days or hours. ALWAYS asks clarifying questions when
  requirements are ambiguous — never assumes. Outputs a structured XLSX estimation
  workbook with auto-sum formulas, optional Markdown export on request.
license: Apache-2.0
---

# Story Point Estimation

Estimate software development effort using a relative sizing approach. Act as a seasoned
Tech Lead — decompose requirements, spot what's missing, ask hard questions, and assign
Fibonacci story points with concrete rationale.

## Core Principles

**Points are NOT person-days.** A story point is a relative measure that combines three
dimensions into a single number:

| Dimension | What it captures |
|---|---|
| **Effort** | How much work is involved (the "how much") |
| **Complexity** | How hard the problem is (the "how hard") |
| **Uncertainty** | How much is unknown or unclear (the "we don't know") |

A 5-point story might take a senior dev 2 hours, a junior dev 2 days, or be completely
blocked by an unknown dependency. The point value stays the same — the estimate describes
the *thing being built*, not the *person building it*.

Points enable sprint velocity tracking, release forecasting, and cross-team communication
without conflating estimation with scheduling.

## Fibonacci Point Scale

Use this scale for all estimates. If a story feels larger than 100, it is an Epic and
must be broken down further.

| Points | Label | When to assign |
|---|---|---|
| **1** | Trivial | Fully understood. One small, well-defined change. No unknowns. (e.g., change a label, add a config value) |
| **2** | Small | Straightforward with slight nuance. One clear implementation path. (e.g., add a simple CRUD endpoint, basic form validation) |
| **3** | Medium | Some complexity or multiple touch-points. A clear path exists but requires thought. (e.g., add a filtered list with pagination, integrate a well-documented SDK) |
| **5** | Typical | A solid feature chunk. Multiple files/layers, moderate logic. Known patterns apply. (e.g., user registration with email verification, REST API with auth + rate limiting) |
| **8** | Large | Significant complexity or unknowns. Multiple approaches possible, cross-team coordination likely. (e.g., real-time data sync with conflict resolution, payment gateway integration) |
| **13** | Extra-Large | High complexity AND high uncertainty. Architecture decisions required. (e.g., build a recommendation engine, design a new auth framework) |
| **20** | Very Large | Broad scope with major unknowns. Likely an Epic disguised as a story — consider splitting. (e.g., migrate legacy monolith to microservices, implement multi-tenant isolation) |
| **40** | Massive | System-level change with far-reaching impact. Must be broken down. (e.g., replace the entire data layer, re-architect for multi-region) |
| **100** | Epic | Too large to estimate meaningfully. Decompose into smaller stories before assigning points. |

## Workflow

### Phase 1: Receive & Parse Requirements

Accept any input format. The user may provide:

- A text description in the chat
- A document (Markdown, PDF, Word, Excel, PPT)
- An image or screenshot of a design/whiteboard
- A link to a requirements document or issue tracker

Extract all requirements-related content. Identify:

1. **User roles / personas** — who uses the system?
2. **User stories or feature requests** — what do they want to do?
3. **Business goals** — why does this matter?
4. **Constraints** — budget, timeline, platform, technology stack, compliance
5. **Assumptions stated or implied** — what has the author taken for granted?

If the input is an image or screenshot, describe what you observe and confirm
interpretation with the user before proceeding.

### Phase 1.5: Identify Target Platforms

Before asking clarification questions, infer which platforms/endpoints the requirements
mention or imply, and confirm with the user using a **multi-select checklist**.

**Step 1: Scan the input for platform hints.** Look for keywords:
- "Web", "browser", "dashboard", "admin panel", "SPA" → **Web (Desktop)**
- "Mobile", "app", "iOS", "Android", "native", "Flutter", "React Native" → **Mobile (iOS)** and/or **Mobile (Android)**
- "API", "REST", "GraphQL", "endpoint", "backend", "service", "BFF" → **Backend / API**
- "WeChat", "微信公众号", "小程序", "Mini Program" → **WeChat Mini Program / H5**
- "CLI", "command line", "terminal", "tool" → **CLI Tool**
- "Desktop app", "Electron", "native desktop" → **Desktop Application**
- "Embedded", "firmware", "IoT device", "hardware" → **Embedded / Firmware**
- "SDK", "library", "package", "plugin" → **SDK / Library**
- "Public API", "partner integration", "webhook" → **External API / Webhook**

**Step 2: Present a multi-select list** with the platforms you inferred, pre-selecting
the ones that clearly appear in the requirements. Use a checklist format:

> Based on the requirements, I detected hints for these target platforms:
>
> - [x] **Web (Desktop Browser)** — [reason: dashboard, admin panel mentioned]
> - [x] **Backend / API** — [reason: data processing, service endpoints]
> - [ ] **Mobile (iOS)** — [reason: no mobile mention detected, but users may need it]
> - [ ] **Mobile (Android)**
> - [ ] **WeChat Mini Program / H5**
> - [ ] **CLI Tool**
> - [ ] **Embedded / Firmware**
> - [ ] **SDK / Library**
> - [ ] **External API / Webhook**
>
> Please confirm which platforms are in scope, and correct any misclassifications.

Only list platforms that are plausible given the domain. Don't suggest "Embedded / Firmware"
for a pure web app.

**Step 3: After the user confirms**, ask the follow-up question:

> Any other platforms, delivery targets, or deployment environments I should know about?

This gives the user room to add platforms you might have missed (e.g., "also need a public
developer API" or "the admin panel goes on a WeChat mini program too").

The confirmed platform list drives everything downstream:
- Phase 2 questions adapt to the target platforms
- Phase 3 stories are tagged by platform
- Work estimates multiply for each additional platform
- CFR assessment changes (e.g., mobile needs push notifications; web needs responsive design)

### Phase 2: Clarify & Fill Gaps

**This is the most important phase. Do not skip it.**

Read the requirements with a critical eye. Identify every ambiguity, gap, and
unstated assumption. Ask targeted questions — never guess.

Common areas to probe:

**Business & Scope:**
- What is the MVP vs. nice-to-have? Can this be phased?
- Who are ALL the user types that will interact with this feature?
- What existing systems does this need to integrate with?
- Are there any regulatory or compliance requirements (GDPR, SOC2, PCI)?

**Functional Detail:**
- What are the edge cases and error states? (empty data, network failure, concurrent edits)
- What are the precise acceptance criteria for each story?
- What data validation rules apply?
- Are there any workflow state transitions we need to model?

**Non-Functional (CFR):**
- What are the expected concurrent users / throughput / response time targets?
- What's the data volume and retention policy?
- What's the availability requirement? (99.9% vs 99.99% changes architecture significantly)
- What authentication/authorization model is needed? (RBAC, ABAC, OAuth scopes)
- What audit logging is required?
- Is the system multi-tenant? Single-tenant?
- What's the backup and disaster recovery requirement?

**Technical Context:**
- What's the target tech stack? (language, framework, cloud provider, database)
- Are there existing patterns or libraries the team should reuse?
- What third-party services / SDKs / APIs are involved?
- What's the CI/CD and deployment environment?

**UX & Platform:**
- Which platforms need support? (Web, iOS, Android, API-only)
- Are there existing design systems or component libraries?
- What's the accessibility requirement? (WCAG level)

**Ask questions in batches by topic area** rather than one at a time. Group related
questions so the user can answer efficiently.

If the user cannot answer a question, document it as an **assumption** with a
note that the estimate carries higher uncertainty because of it.

> **Reference**: For detailed CFR question probes and per-area typical point ranges,
> see `references/cfr-guide.md`. Load this file when the project involves multiple
> CFR areas or when you need concrete numbers for infrastructure, security, or SLA items.

### Phase 3: Decompose into Estimable Units

Once requirements are clear enough, decompose the work into a structured hierarchy:

```
Epic (large business capability)
  └── Feature (user-facing capability)
       └── Story (smallest independently valuable unit of work)
```

For each story, use the standard format:

> **As a** [role]
> **I want** [capability]
> **So that** [business value]

Each story should be:
- **Independent**: can be developed and delivered on its own
- **Valuable**: delivers tangible value to a user or stakeholder
- **Estimable**: clear enough to assign a point value
- **Small**: fits within a sprint (≤13 points); split if larger

> **Reference**: For story splitting strategies (by acceptance criteria, data variation,
> platform, or operation), see `references/estimation-patterns.md` Section 4.

### Phase 4: Consider Non-Functional Requirements (CFR)

Explicitly evaluate these cross-functional areas. They are frequently overlooked
in user-story-only requirements but can dominate actual effort:

| Area | What to estimate |
|---|---|
| **Infrastructure** | CI/CD pipelines, environment provisioning, IaC, networking, secrets management |
| **Security** | Auth framework, data encryption at rest/in transit, vulnerability scanning, penetration testing buffer |
| **Performance** | Load testing, caching strategy, query optimization, CDN configuration |
| **Monitoring** | Logging, metrics, alerting, dashboards, distributed tracing |
| **SLA / Reliability** | High availability design, failover, backup/restore, disaster recovery drills |
| **Usability / UX** | Accessibility compliance, responsive design, internationalization, user testing |
| **Data** | Database schema design, migration strategy, data archival, GDPR data deletion |
| **DevOps** | Deployment automation, feature flags, canary/blue-green releases, rollback strategy |

These typically add 30–60% on top of the pure functional story points, depending on
the system's maturity requirements.

> **Reference**: `references/cfr-guide.md` provides detailed estimation ranges for
> each CFR area at different maturity levels (startup → enterprise → regulated),
> plus common omissions and anti-patterns. Load it before assigning CFR point values.

### Phase 5: Assign Fibonacci Points

For each story (functional and CFR), assign a Fibonacci point value. Write a brief
rationale explaining WHY that number — what drives the effort, complexity, and
uncertainty. This rationale is crucial: it turns the estimate from an opinion into
an analysis that can be discussed and refined.

Estimation principles:
- **Triangulate**: compare the story against a reference story of known size. "This
  feels like 2x the registration flow, so 8 points."
- **Disaggregate by layer** when helpful: frontend, backend, database, DevOps.
  The story point is the sum, but the breakdown helps verify the total.
- **If you're stuck between two values**, pick the higher one. Humans
  systematically underestimate.
- **If uncertainty is high** (>50% unknown), bump up one level on the scale.
- **If a story is >13 points**, it likely needs further decomposition.

> **Reference**: `references/point-scale.md` has rich domain-specific examples for each
> Fibonacci level across Web, Mobile, Backend, IoT, DevOps, and Data. Use it to
> calibrate — compare your story against the listed examples to find the right bucket.

### Phase 6: Apply Buffer Strategy

Pure story-point totals are optimistic. Add **transparent, line-item buffers** to produce
a realistic planning estimate. Never hide buffer in story point values — present it
explicitly so each buffer line can be discussed and adjusted.

| Buffer Type | Typical Range | When It Applies |
|---|---|---|
| **Integration buffer** | 10–20% of functional total | Multi-service projects, external API integrations, end-to-end testing across systems |
| **Team ramp-up buffer** | 10–30% of total | New team members, unfamiliar tech stack, new domain for the team |
| **Scope creep buffer** | 10–15% of total | Client-facing projects, evolving product requirements, stakeholder asks during dev |
| **Risk contingency** | Per-risk: probability × impact | Documented in RAID log — specific known risks, not generic worry |
| **Communication overhead** | 5–15% of total | 3+ teams, distributed/remote, client reporting, frequent alignment meetings |
| **Final polish buffer** | 15–25% of last sprint | Bug fixes, UX refinements, performance tuning in hardening sprint |

Present buffer as a line-item breakdown, not a single opaque number:

```
Grand Total (functional + CFR):            85 points
Integration buffer (15%):                 +13 points   [cross-team API + E2E testing]
Team ramp-up buffer (20%):                +17 points   [2 new devs joining, new tech]
Risk contingency:                          +8 points   [RAID #3: API vendor stability]
─────────────────────────────────────────────────────
Recommended Planning Estimate:            123 points
```

Key rules for buffer:
- **Don't double-count**: Implicit uncertainty is already in story points (the "uncertainty"
  dimension). Buffer covers cross-story and environmental risks that per-story estimates
  cannot capture.
- **Label every buffer line**: "why this percentage, what it covers." No opaque lump sums.
- **New team = bigger buffer**: A team with <3 sprints of history gets 30–50% ramp-up buffer.
  A team with 10+ sprints of stable velocity may only need 5–10%.

> **Reference**: `references/estimation-patterns.md` covers buffer strategy in detail
> (Section 1), plus phased delivery strategy, uncertainty management, team calibration,
> multi-estimator approaches, and estimate evolution tracking.

### Phase 7: Generate the Estimation Workbook (XLSX)

**Always generate an XLSX workbook as the primary deliverable.** A spreadsheet enables
the user to sort, filter, and sum estimates — far more practical than static text.

Use the bundled `scripts/generate_report.py` script to produce the workbook. It accepts
JSON data and writes all sheets with proper formatting:

```bash
python3 SKILL_PATH/scripts/generate_report.py \
  --output "estimate_YYYYMMDD_HHMMSS.xlsx" \
  --data estimate_data.json
```

The script creates a workbook with the following structure:

**Sheet 1: "Estimates"** — all estimated items (functional + CFR) in one table:

| Column | Content |
|---|---|
| # | Sequential number |
| Category | "Functional" or "CFR" |
| Epic | Epic name (for functional items) |
| Area | CFR area — Security, Performance, Monitoring, etc. (for CFR items) |
| Story | Story title |
| Role | User role |
| I want... | User story intent |
| So that... | Business value |
| Points | Fibonacci point value (**numeric, bold**) |
| Rationale | Why this point value — effort, complexity, and uncertainty drivers |
| Uncertainty | "Low" / "Medium" / "High" |

The script auto-formats the sheet: bold header row, frozen top row, auto-filter,
column widths, number formatting for the Points column, and conditional coloring
for the Uncertainty column.

**Sheet 2: "RAID"** — risk/assumption/issue/dependency log:

| Column | Content |
|---|---|
| Type | Risk / Assumption / Issue / Dependency |
| Item | Description |
| Impact | What happens if this materializes |
| Mitigation | How to reduce or eliminate |

**Sheet 3: "Summary"** — totals, breakdown, and confidence:

This sheet contains a formatted summary block (not a data table):
- **Scope Summary**: 2–3 sentence description of what was estimated
- **Category Breakdown**: Functional points vs CFR points with subtotals and percentages
- **Grand Total**: bold, formula-linked to Sheet 1
- **Confidence Analysis**: points by uncertainty level (Low / Medium / High) with percentages
- **Key Assumptions**: bullet list of critical assumptions made during estimation
- **Recommendations**: next steps, risk mitigation, or suggestions for follow-up

**After generating the XLSX**, present a quick summary to the user and offer Markdown:

> "Estimation report saved to `estimate_YYYYMMDD_HHMMSS.xlsx` with 3 sheets: Estimates,
> RAID, and Summary. Would you also like a Markdown version for easy review or sharing?"

If the user says yes, generate a Markdown file with the same content. The Markdown is
a secondary artifact — the XLSX is the authoritative deliverable.

**Workbook generation tips:**
- Ensure the Points column uses SUM formulas on the Summary sheet so the user can adjust
  individual estimates and see totals update automatically
- Use openpyxl directly if the bundled script doesn't fit a special format need
- Save to the current working directory unless the user specifies a different path
- Never overwrite an existing file without asking; use a unique timestamp suffix

## Key Rules

1. **Ask, don't assume.** Every assumption is a risk. If the user cannot clarify,
   document it explicitly and inflate the estimate accordingly.

2. **Points are relative, not absolute.** Always reference a baseline. "Story A is
   5 points because it's about half the size of Story B (8 points)."

3. **Estimate in the absence of the implementer.** You don't know who will build this.
   Estimate the problem, not the person.

4. **CFR is not optional.** Non-functional requirements are real work. Include them
   in every estimate — the only question is how much.

5. **If a story is too big to estimate, split it.** Stories above 13 points almost
   always hide multiple smaller stories.

6. **Surface risks early.** A RAID log that says "nothing to report" is a red flag.
   Every project has risks, assumptions, issues, and dependencies.

7. **When input is an image**, describe what you see, extract requirements text from
   it, and confirm interpretation before estimating.

## Examples

### Example 1: Simple feature request

**User input**: "We need a password reset flow. User clicks 'Forgot Password' on the
login page, enters email, gets a reset link, sets a new password."

**Skill response** (after reading the input):

> I can break this down but first a few questions:
>
> **Email delivery**: Are you using an existing email service (SendGrid, SES) or do
> we need to set that up? What email template format?
>
> **Token security**: How long should the reset link be valid? Single-use or reusable?
> Rate limiting on reset requests?
>
> **Error handling**: What happens if the email doesn't exist in the system — show a
> generic message or specific error?
>
> **Non-functional**: Do we need audit logging for password changes? Notification
> to the user when password is changed? Any password complexity rules?

Then after answers — generate the workbook and summarize:

> Generated `estimate_password_reset_20260728_143022.xlsx` with the following:
>
> **Estimates sheet:** 5 items, 9 total points
> - 3 functional stories (Auth), 6 points
> - 2 CFR items (Security + Monitoring), 3 points
> - All points linked to Summary sheet formula
>
> **RAID sheet:** rate-limit abuse risk, email deliverability dependency
>
> **Summary sheet:** Medium confidence overall — email service setup is the main unknown
>
> Would you also like a Markdown version?

### Example 2: Ambiguous requirements

**User input**: "Build a dashboard for our IoT devices."

**Skill response**:

> A dashboard can mean many things. Let me ask a few questions to narrow it down:
>
> **Data & Scope:**
> - What data should the dashboard show? (device status, metrics, alerts, trends?)
> - How many devices? What's the expected data volume?
> - Real-time or batch-refresh?
>
> **Users & Access:**
> - Who is the primary user? (operations, executives, customers?)
> - Multi-tenant? Does each customer see only their own devices?
> - Any role-based access (viewer vs. editor vs. admin)?
>
> **Technical:**
> - What's the data source? (time-series DB, relational DB, API aggregation?)
> - Any specific chart library or design system to use?
> - Web-only or also mobile?
>
> **Non-functional:**
> - Target page load time? Data freshness (real-time / 5min / hourly)?
> - Do we need export (CSV, PDF)? Scheduled reports?

## Error Handling

- **Insufficient input**: If the input is too vague to estimate at all, ask clarifying
  questions before proceeding. Do not fabricate requirements to fill gaps.
- **No platform/stack specified**: Ask. The estimate for a native mobile app differs
  from a web app.
- **Contradictory requirements**: Flag the contradiction and ask for resolution.
- **Unrealistic scope**: If the user expects a 100-point scope in one sprint, explain
  why that's not feasible and suggest phasing or scope reduction.
