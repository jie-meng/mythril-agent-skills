# Requirements Interrogation — question format, modes, records

Read this when Step 3.5 of `SKILL.md` decides the gate runs. It holds the
question format, the plain-words rules, standard vs. grill mode, and how
the answers are recorded.

## One round, at most five questions

Ask `Q1..Qn` with `n <= 5`, all in one message. Each question carries:

| Part | Content |
|------|---------|
| Title | `Q<n> — <the decision, in words the user can read>` |
| Example | one `比如：…` / `for example: …` line grounded in the feature being planned, showing what each answer makes happen |
| Why it matters | one plain sentence: what the user will see, or what later work depends on, when the answer goes one way or the other |
| Recommendation | the answer you would choose, with its reason |
| Cost of being wrong | what has to be redone and roughly how much work; when it is cheap to reverse, say so in so many words |

`按推荐` / `全部按推荐` / `all recommendations` accepts every recommendation
in the round and closes the interrogation.

### Plain words and a concrete example (MANDATORY)

The user reads the questions; the planner reads the records. A question
the user cannot evaluate is worse than no question — they answer `按推荐`
blindly, and the gate learns nothing. In the text the user sees:

1. **No planner jargon.** Contract, schema, migration, rollback, baseline,
   plan-shaping (契约、数据形状、迁移、回滚、基线) name plan anatomy, not
   behavior — replace each with what actually happens. Jargon stays legal
   in the `### Clarifications` table and the derived REQ lines, which the
   planner reads.
2. **One concrete example per question, from this feature.** Not a
   textbook case: `比如：这次把设置项的存法改了，手机上还装着旧版 App，
   旧版读到新格式要不要照样能打开设置页？`
3. **Options speak in outcomes, not mechanisms.** "旧版 App 打不开设置页"
   is an outcome; "数据形状变更缺少兼容层" is a mechanism — write the
   former.
4. **Label the stakes.** A cheap-to-reverse decision says so —
   `这个拿不准可以直接按推荐，改起来很快` — so the user spends attention
   only where a wrong answer really costs days.

These are decision-reader writing rules applied to questions; the full set
lives in `references/template-rules.<lang>.md`
§面向决策者的写作规则. Translated examples:

| Planner phrasing (do not send) | Plain question (send this shape) |
|---|---|
| `Q1 — 跨仓库契约：类型变更同步发布还是渐进迁移？` | `Q1 — 改了共享类型，其他端要一起改吗？比如：shared-lib 的主题类型加一个字段，网页和 App 不跟着改会直接编译报错。推荐：同一批改完，一次提交把三个端都带上，免得哪个端漏掉。` |
| `Q2 — persisted schema backward-compatibility strategy` | `Q2 — Old app versions must keep working? For example: the settings file gets a new format, and a phone still running the old build must still open settings. Recommendation: keep the old format readable — the old build just won't show the new setting. This is cheap to change later.` |
| `Q3 — rollout 是否保留 feature flag 以支持回滚` | `Q3 — 上线后发现问题，怎么退回来？比如：加一个设置页里的开关，出问题关掉几秒就恢复；不加就得重新发版，可能等一两天。推荐：加开关（多半天工作量，换一个能秒回退的保险）。` |

- **Standard mode** — at most two rounds. A second round runs only when an
  answer opens a new plan-shaping decision, and it asks that new frontier
  only.
- **Grill mode** — the user said "grill me", "拷问我", "盘问我", or
  "别急着给方案". No round cap and no five-question cap: ask the current
  frontier, wait for the answers, recompute the frontier from them, repeat
  until no plan-shaping decision is left. Stop on decisions, not on a
  count.

## Facts are the agent's job, decisions are the user's

Check the repository first. If the answer is in the code, the docs, or the
workspace `AGENTS.md`, it is a fact — look it up and state it; a question
spent on a fact wastes the user's attention. When the fact-find is deep
(a call path, an existing contract, a migration history), dispatch the
`explore` subagent instead of asking; if the host has no `explore`
subagent, do the fact-find yourself. Ask only what code cannot answer:
intent, priority, acceptable trade-offs, rollout policy, and conflicts
between requirements.

## Record the answers

The answers are part of the requirements baseline the Step 4.5 review
falsifies against. After the round, `analysis.md` §Original Requirements /
§需求原文 carries a `### Clarifications` / `### 澄清记录` subsection, one row
per question:

| Q | Question | Recommendation | User answer | Plan impact |
|---|----------|----------------|-------------|-------------|
| Q1 | <the decision> | <recommended answer> | <the user's answer, or `(as recommended)`> | <which part of the plan changes> |

An answer that changes what the system must do derives a requirement line
in the same section: `- **REQ<n>** "<the answer>" — Source: clarification
Q<n>`. When the user accepted the recommendation, quote the
recommendation's own wording and mark it `(as recommended)` — never just
"as recommended", which leaves the baseline with an empty requirement.

Every open decision ends in exactly one of two states:

- `A<n>` — assumed, and only when it does not block acceptance. The row
  goes in `plan.md`'s risk table with the reversal condition — what makes
  the assumption false and how to back out — in the `Mitigation` /
  `应对` column.
- `NEEDS_USER_DECISION` — the decision blocks acceptance; do not write a
  plan around it — ask the user now. Until answered, it stays an open
  decision in the Step 5 report.

No silent assumptions. The exact table and row shape are frozen in
`references/template-analysis.<lang>.md`;
Step 4 writes this content to disk before anyone writes the plan.
