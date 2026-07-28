# Estimation Patterns & Buffer Strategies

Real-world estimation is not a one-shot calculation. This document covers patterns for
handling common estimation challenges: phasing, uncertainty, team calibration, story
splitting, cross-checking, and buffer allocation.

---

## 1. Buffer Strategy

### Why Buffer?

Estimates are inherently optimistic. Teams consistently underestimate by 20–40% because:
- Requirements are never 100% complete at estimation time
- Unknown unknowns only surface during implementation
- Integration points reveal hidden complexity
- Environment issues, tooling problems, and dependency delays are invisible at planning time
- Context switching, meetings, and communication overhead are not accounted for in
  per-story estimates

Buffer is NOT padding or sandbagging. It's a structured acknowledgment of irreducible
uncertainty.

### Buffer Types

| Buffer Type | What It Covers | Typical Range | When to Use |
|---|---|---|---|
| **Implicit (per-story)** | Minor unknowns within a single story | Already baked into the point value via uncertainty dimension | Always — this is why points combine effort + complexity + uncertainty |
| **Integration buffer** | Cross-story coordination, API contract mismatches, end-to-end testing | 10–20% of functional total | Multi-service projects, external integrations |
| **Team ramp-up buffer** | New team members, unfamiliar tech stack, learning curve | 10–30% of total | New team, new tech, new domain |
| **Scope creep buffer** | Small, inevitable requirement additions during development | 10–15% of total | Client-facing projects, evolving product requirements |
| **Risk contingency** | Specific known risks that may materialize | Per-risk: probability × impact | Documented in RAID log |
| **Communication overhead** | Cross-team meetings, alignment, reporting | 5–15% of total | 3+ teams, distributed/remote, client reporting |
| **Final polish buffer** | Bug fixes, UX refinements, performance tuning in hardening sprint | 15–25% of last sprint | Always — the last 10% of polish takes 30% of time |

### How to Calculate and Present Buffer

**Do NOT** present buffer as a single opaque lump sum. That invites questions and erodes
trust. Instead, present it as a **transparent line item** with clear justification:

```
Grand Total (functional + CFR):            85 points
Integration buffer (15%):                 +13 points   [cross-team API + E2E testing]
Team ramp-up buffer (20%):                +17 points   [2 new devs joining, new MQ tech]
Risk contingency:                          +8 points   [see RAID item #3: API vendor stability]
Communication overhead (10%):             +9 points   [3 teams, weekly client sync]
─────────────────────────────────────────────────────
Recommended Planning Estimate:            132 points
```

This makes buffer defensible. Each line item can be discussed, adjusted, or removed
as conditions change. It also helps the team track whether buffer was consumed by the
specific risk it was allocated for — learning for future estimates.

### When Buffer Becomes Dangerous

- **Double-counting**: Don't add implicit buffer to stories AND explicit buffer on top.
  If you've already bumped each story for uncertainty, the buffer percentage should be lower.
- **Buffer as commitment padding**: Buffer is for estimation, not for adding safety margin
  to a committed date. If leadership cuts the buffer, the estimate is now best-case optimistic.
- **Using buffer to avoid hard conversations**: If a specific risk has a 50% chance of
  adding 20 points, flag it explicitly. Don't hide it in a general buffer percentage.

---

## 2. Phased Delivery Strategy

Most projects are not delivered as one monolithic release. The estimation should reflect
how the work can be phased for incremental value delivery.

### Phase Decomposition

| Phase | Typical Content | Characteristics |
|---|---|---|
| **MVP / Phase 1** | Core user journey, minimal feature set, happy path only | Highest certainty, tightest estimates |
| **Phase 2** | Secondary features, edge cases, reporting, admin tools | Medium certainty, depends on Phase 1 feedback |
| **Phase 3+** | Nice-to-haves, optimization, advanced features | Lowest certainty, may change based on user feedback |

### Per-Phase Confidence

Phases further out carry exponentially more uncertainty. Apply a **discount factor**
when presenting estimates:

```
Phase 1 (next 3 months):    85 points    Confidence: High (±15%)
Phase 2 (3–6 months):      120 points    Confidence: Medium (±30%)
Phase 3 (6–12 months):     200 points    Confidence: Low (±50%)
```

Never commit to Phase 3 estimates with the same confidence as Phase 1. Label them
explicitly as **"indicative / subject to change based on Phase 1 learnings."**

### Feature Flagging for Incremental Delivery

When possible, estimate stories so they can be delivered behind feature flags. This
decouples deployment from release and reduces integration risk. Flag-based delivery
typically adds 1–2 points per story for flag management, but saves much more in
reduced merge conflicts and rollback safety.

---

## 3. Uncertainty & Risk Management

### Uncertainty Classification

| Level | Description | % of Stories | Pointing Impact |
|---|---|---|---|
| **Low** | Technical approach is clear. Similar work done before. Dependencies are stable. | <20% unknown | Estimate as-is |
| **Medium** | Approach is plausible but unproven. Some unknowns in integration or data model. | 20–50% unknown | Consider bumping up one level OR adding a spike story |
| **High** | Major architectural questions unanswered. Novel technology. Unstable dependencies. | >50% unknown | Do NOT estimate — spike first, then re-estimate |

### The Spike Pattern

When uncertainty exceeds 50% for a story, replace it with a **time-boxed spike**:

> Instead of: "Build real-time sync engine — 20 points"
>
> Create two items:
> 1. **Spike: Real-time sync approach research** — 3 points (time-box: 3 days, must produce
>    a decision doc with recommended approach + prototype)
> 2. **Build real-time sync engine** — Re-estimate after spike with actual data

A spike IS estimable (3–5 points typically) because the output and time-box are fixed.
The follow-up work becomes estimable only after the spike delivers clarity.

### Tracking Uncertainty in the Workbook

Each row in the Estimates sheet has an **Uncertainty** column (Low/Medium/High). Use
this to:
- Surface which estimates need revisiting
- Calculate "known good" vs "speculative" totals
- Prioritize spikes and clarification conversations

The Summary sheet breaks down points by uncertainty level so stakeholders see exactly
how much of the total is built on assumptions.

---

## 4. Story Splitting Strategies

Stories above 13 points should almost always be split. Stories of 20+ points MUST be split.
Here are splitting patterns beyond the obvious:

### Splitting by Acceptance Criteria
A large story like "User can search and filter products" can become:
- Basic keyword search (3 points)
- Faceted filtering (5 points)
- Sort by relevance/price/date (2 points)
- Save search preferences (3 points)
- Search result pagination (2 points)

### Splitting by Data Variation
"Import data from CSV" can become:
- Happy path: well-formatted CSV with all required fields (3 points)
- Error handling: malformed CSV, missing fields, encoding issues (3 points)
- Large file handling: streaming parser for >100MB files (5 points)
- Field mapping UI: user maps CSV columns to system fields (5 points)

### Splitting by Platform
"User registration" can become:
- Backend: registration API + email verification (5 points)
- Web: registration form + email verification flow (3 points)
- iOS: native registration screen + deep link for email verify (5 points)
- Android: native registration screen + deep link for email verify (5 points)

### Splitting by Operation
Full CRUD for an entity can be split:
- Read: list + detail view (3 points)
- Create: form + validation + API (3 points)
- Update: form pre-filled + validation + API (3 points)
- Delete: confirmation + API + cascade handling (2 points)

### The Split Test
A split is valid if each resulting story:
1. Delivers independent value to a user
2. Can be developed and tested in isolation
3. Is small enough to complete within one sprint (≤13 points)

If splitting produces stories that are all 1s and 2s, you may have over-split. Merge
back to meaningful chunks.

---

## 5. Team Calibration

### Baseline Stories

Every team should maintain 3–5 **baseline stories** — well-understood pieces of work
that serve as reference points for relative estimation.

Example baselines:
- "Add a simple CRUD resource with list + detail + create + update endpoints" → **5 points**
- "Build a basic form with validation and API submission" → **3 points**
- "Integrate a well-documented third-party SDK with callback handling" → **5 points**
- "Set up CI/CD for a new service with test + build + deploy stages" → **5 points**

When estimating a new story, compare it to these baselines: "This feels about twice the
work of the basic form story, so 5 points."

### Cross-Team Calibration

Different teams settle on different absolute scales (Team A's 5 might be Team B's 8).
This is normal — points are team-relative. What matters is **internal consistency**
within a team.

When working across teams:
- Don't compare absolute point values
- Compare ratios: "This feature is 40% of our total scope, and 50% of theirs — do we agree on relative sizing?"
- Use T-shirt sizing (S/M/L/XL) for cross-team alignment discussions, then convert to
  team-specific points after alignment

### Velocity-Based Calibration

A team's velocity (points completed per sprint) is the ultimate calibration tool.
After 3–4 sprints:
- If the team consistently delivers 20 points/sprint and you estimated 100 points, the
  project takes 5 sprints — regardless of what the absolute point values "should" be.
- If the team delivers 10 points when you expected 20, either: (a) stories were
  under-estimated [fix: recalibrate], (b) the team was disrupted [one-time anomaly], or
  (c) the team is less productive than assumed [fix: adjust expectations].

### New Team Warning

A new team has NO velocity data. First-sprint estimates are essentially guesses. Apply
a **30–50% new-team buffer** on the overall project estimate until velocity stabilizes
(typically after 3 sprints).

---

## 6. Multi-Estimator Approach

For high-stakes estimates, use multiple perspectives to reduce individual bias:

### Wideband Delphi
1. Each estimator independently assigns points to each story (no discussion)
2. Compare results — flag stories where variance exceeds one Fibonacci level
3. Discuss only the divergent stories. High and low estimators explain their reasoning.
4. Re-estimate independently
5. Converge on point values; if still divergent, document both values and the range

### Dual-Track Estimation
1. One person estimates from a **backend/infrastructure** perspective
2. Another estimates from a **frontend/UX** perspective
3. Compare and reconcile — each catches what the other misses

### When to Use Multiple Estimators
- Total scope exceeds 100 points
- The project involves unfamiliar technology
- The estimate is for a fixed-price contract or external commitment
- The estimating team has no prior velocity data

---

## 7. Estimate Evolution & Traceability

Estimates are not static. From the real-world examples studied, a single project's
estimates typically go through 5–8 revisions as scope clarifies, constraints change,
and assumptions are tested.

### Versioning Estimates

Each estimation workbook should include:
- **Version number and date** in the Summary sheet
- **What changed** from the previous version (scope added/removed, assumption validated/invalidated)
- **Who participated** in the estimation

### The Narrowing Cone

Estimates become more accurate as the project progresses:

```
Phase               Accuracy Range        When
───────────────────────────────────────────────────
Pre-sale / Concept   ±50–100%             Vague requirements, no team assigned
Requirements done    ±30–50%              Stories written, architecture drafted
Design complete      ±15–30%              Technical approach validated, spikes done
Mid-sprint           ±10–20%              Implementation underway, unknowns resolved
Sprint complete      ±0%                  Work is done
```

Present estimates with the accuracy range that matches the current phase. Don't let
stakeholders treat an early estimate as a precise commitment.

### Re-Estimation Triggers

Re-estimate when:
- **Scope changes** (>10% of total points added or removed)
- **A spike reveals major complexity** (spike estimated at 3, follow-up was 8, spike
  shows it's actually 20)
- **A key assumption is invalidated** (RAID assumption turns out wrong)
- **External dependency timeline shifts** (API provider delays, infrastructure not ready)
- **Team composition changes** (senior dev leaves, 3 juniors join)
- **After 3 sprints of stable velocity** (recalibrate all remaining estimates against
  actual velocity)

---

## 8. Estimating from Ambiguous Inputs

### Requirements Are an Image/Screenshot/Whiteboard Photo
1. Describe everything you see: screens, fields, flows, annotations
2. Identify missing information: "I see a login screen, but no error states, password
   recovery flow, or registration screen — are these in scope?"
3. **Confirm interpretation before assigning points**

### Requirements Are a Paragraph of Prose
Example: "We need a dashboard for our operations team to monitor device health."
1. Decompose the vague statement into candidate stories
2. Present the candidate list to the user: "Here's what I think the dashboard might
   include. Which of these are in scope?"
3. Only estimate after scope agreement

### Requirements Are a Bullet List with No Detail
Each bullet is an Epic at best, not a story. For each bullet:
1. Ask: "What are the acceptance criteria for this? How do we know it's done?"
2. Ask: "What's the simplest version we could ship first?"
3. Estimate the simplest version, and separately note what a fuller version might cost

### The "Can't Estimate" Response
If requirements are genuinely too vague, say so clearly:
> "I can't assign points to this yet because [specific reason]. Here's what I need to
> know: [specific questions]. Would you like me to estimate a discovery spike (3–5 points)
> to produce a clearer specification?"

---

## 9. Communication Anti-Patterns

- **"It'll take about a month"** — Too vague. What's "about"? Calendar month or 4 sprints?
  One person or a team? Use points, then convert to timeline with known velocity.
- **"Similar project took X, so this is X"** — Unless the projects are identical
  (they never are), this hides assumptions. Break it down.
- **"We'll figure it out as we go"** — Discovery is valid, but budget it explicitly as
  a spike. "Figuring it out" without a time-box is scope creep.
- **"Just give me a number"** (stakeholder pressure) — Giving a rushed number creates
  a false commitment. Instead: "I have low confidence on several items. Here's my
  best estimate with the uncertainty range. I recommend we spike X and Y before
  committing."
- **Comparing points across teams** — "Why is your team's 5-point story taking as long
  as our team's 8-point story?" Teams have different baselines. Points measure internal
  consistency, not cross-team equivalence.
