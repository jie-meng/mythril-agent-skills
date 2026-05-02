# Mode Selection — Routing Among Reference / Iteration / Follow-up / Fresh

When the user's request touches a workspace with one or more existing
work directories, the skill must route to the right mode. Picking the
wrong mode is expensive: too eager → phantom Predecessor links and
modified prior dirs; too conservative → lost continuity and re-derived
decisions. This document is the routing center.

## The four modes at a glance

| Mode | Lifecycle stage | Reads prior dir | Writes prior dir | Cost of misroute |
|------|----------------|-----------------|------------------|------------------|
| **Fresh** (standard Step 1-9) | No prior work referenced | No | No | Low |
| **Reference** | Independent new work; prior work cited as background | Yes | **No** | Low — easy to delete prose citations |
| **Iteration** | Open work item (`Status: Done`/`In Progress`) — same scope, PR not yet merged | Yes (in same dir) | Yes (same dir, append) | Medium — same dir |
| **Follow-up** | Closed work item (`Status: Closed`) — extending shipped code | Yes | **Yes** (`## Successors` back-link) | High — touches two dirs + uses `-vN` |

## Routing decision tree

```
User request arrives
        │
        ▼
1. Does the user use any of the explicit mode verbs below?
        │
        ├── YES → use that mode (skip implicit detection)
        │
        └── NO → continue to step 2
        │
        ▼
2. Is there an existing work directory whose scope overlaps the request?
        │
        ├── NO matching dir   → Fresh
        │
        ├── Match, Status = Planning / In Progress
        │   AND user wants to continue
        │                      → Resume (standard Step 1-9 from where it stopped)
        │
        ├── Match, Status = Done (PR not merged)
        │   AND user wants tweaks/fixes/feedback
        │                      → Iteration (silent, no announcement)
        │
        ├── Match, Status = Closed (PR merged, shipped)
        │   AND user uses follow-up verb
        │                      → Follow-up
        │
        ├── Match, Status = Closed
        │   AND user uses reading verb
        │                      → Reference
        │
        ├── Match, Status = Closed
        │   AND user uses neither verb
        │                      → ASK with the three-option question below
        │                        (default to Fresh if user just confirms generically)
        │
        └── Match, in-progress AND request is clearly unrelated
                               → Fresh (do not pollute the active dir)
```

## Explicit verbs by mode

The agent recognizes these verbs without further inference. **Always
prefer explicit verbs over implicit scope matching** — they encode
the user's intent unambiguously.

### Reference Mode verbs (read prior, write fresh)

| Language | Phrasing |
|----------|----------|
| English | "look at feat/X", "read feat/X docs", "based on the X docs", "reference feat/X", "use feat/X for context", "check the X analysis", "see what we did in feat/X" |
| Chinese | "参考 feat/X", "看一下 feat/X", "看看 feat/X 文档", "基于 feat/X 的文档", "X 当背景", "X 当参考", "看下 feat/X 的 analysis" |

### Follow-up Mode verbs (build on closed predecessor)

| Language | Phrasing |
|----------|----------|
| English | "follow up on X", "extend X", "build on top of X", "on top of X", "based on X work" (note: "based on X **work**" differs from "based on X **docs**") |
| Chinese | "在 X 基础上", "基于 X 做后续", "X 的后续", "扩展 X", "follow up X" |

### Iteration Mode verbs (silent — no announcement needed)

Any feedback / fix / tweak verb pointing at an open work item:

| Language | Phrasing |
|----------|----------|
| English | "this is wrong", "fix this", "doesn't work", pasted error/log, reviewer comment, "also add X" |
| Chinese | "调一下", "再改一下", "这里不对", "log 报错", "顺便加一下", reviewer 反馈 |

## The clarifying question (when verbs are ambiguous)

Use this when the request scope overlaps a closed work item but the
user did not commit to a verb:

```
I noticed a closed work item that overlaps your request:
  feat/dark-mode/  (Closed 2026-04-15)
  Summary: <one-line from progress.md>

Three ways to proceed:

  A) Follow-up — create feat/dark-mode-v2/ that explicitly builds on
     the closed work. Inherits decisions, gets a Predecessor field,
     adds a back-link in dark-mode/progress.md. Best when this work
     is a true continuation of the dark-mode effort.

  B) Reference — start a fresh work item with a free name. I'll read
     dark-mode's docs as background context, but no Predecessor link
     and no modification to the old directory. Best when your work
     is related but operationally independent.

  C) Independent — start a fresh work item with no relationship to
     dark-mode at all. I won't read dark-mode's docs unless you ask.
     Best when the overlap is coincidental.

Which fits?
```

If the user picks A, see [`followup-mode.md`](followup-mode.md).
If the user picks B, see [`reference-mode.md`](reference-mode.md).
If the user picks C, run standard Step 1-9 without reading
the named prior dir.

## Why this design — the trade-offs

The routing rules above are deliberately **biased toward asking when
unsure** rather than auto-detecting. The reasoning:

1. **Misroute cost is asymmetric.** Auto-routing to Follow-up when
   the user wanted Reference creates phantom Predecessor links AND
   modifies a closed predecessor's `progress.md` — both cost a
   git-amend or two to clean up. Auto-routing to Reference (or
   Fresh) when the user wanted Follow-up just means missing
   Predecessor metadata — easily fixable by adding the field
   later.

2. **Implicit scope matching is unreliable.** "Add a setting toggle"
   could overlap dark-mode, accessibility, language-picker, or
   none of them. Pattern matching on repo + surface gives false
   positives in feature-rich workspaces.

3. **The question is cheap.** A single clarifying question costs
   one user turn. A wrong route costs cleaning two directories,
   amending git history, and explaining the confusion.

4. **Explicit verbs are reliable.** When the user says "follow up on
   X" or "look at X", the intent is unambiguous. The agent should
   trust verbs and not second-guess them.

## Promoting / demoting modes mid-flight

Modes are not always set in stone at routing time — sometimes the
agent discovers mid-planning that a different mode fits better.
Allowed transitions:

| From | To | When | How |
|------|----|------|-----|
| Reference | Follow-up | New work clearly extends prior work in incompatible ways | Ask user; if yes, rename dir to `-v2`, add Predecessor field, write Predecessor Context, append Successors row. See "Promoting Reference → Follow-up" in [`reference-mode.md`](reference-mode.md). |
| Fresh | Reference | User asks "actually, look at feat/X first" mid-flight | Read the prior dir, optionally cite in `analysis.md` prose; no other changes |
| Fresh | Follow-up | User pivots and asks for a true follow-up | Restart Step 5 with `-vN` naming; the Step 1 context gathering must include the predecessor docs |
| Iteration | Fresh | User pastes an unrelated bug while iterating | Recognize the scope mismatch, ask, start a separate work item |

The reverse demotions (Follow-up → Reference, Follow-up → Fresh) are
uncommon and harder because they require **un-writing** the
back-link in the predecessor's `progress.md`. Avoid them by asking
up-front when the route is ambiguous.

## Quick examples

| User says | Status of matched dir | Route | Why |
|-----------|----------------------|-------|-----|
| "look at feat/dark-mode/ docs, then implement theme customization" | Closed | **Reference** | Explicit reading verb + new feature is independent |
| "在 dark-mode 基础上加跟随系统选项" | Closed | **Follow-up** | Explicit follow-up verb in Chinese |
| "继续 dark mode" | In Progress | **Resume** | Open work, user wants to continue |
| "继续 dark mode" | Done (PR not merged) | **Iteration** | Open work, user wants to continue tweaking |
| "继续 dark mode" | Closed | **Ask** (3-option question) | Closed → "continue" is ambiguous between Follow-up and Reference |
| "this is wrong" (pasted log) | Done | **Iteration** | Open work + bug report signal |
| "implement theme customization" (no mention of dark-mode) | Closed `dark-mode/` exists with overlapping scope | **Ask** (3-option question) | Implicit overlap with no verb — default to asking |
| "add CSV import to import-export feature" | Closed `feat/import-export/` exists | **Ask** | Same as above; clear theme but no follow-up verb |
| "implement a brand new admin dashboard" | No overlap | **Fresh** | Standard new work |
