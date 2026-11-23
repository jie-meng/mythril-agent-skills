## 面向决策者的写作规则（Writing Rules for Decision Readers）

These rules apply to **all four documents, in both languages, and to
every message that asks the user to decide** — interrogation questions,
confirmations, review verdicts, and the Step 5 report. They are
the "reads like it was written for a person" layer on top of the
machine-checked structure. They bound *how* things are written, never
*what* may be recorded: no rule below is permission to drop evidence,
caveats, or audit detail.

1. **Verdict first, evidence after（先结论，后证据）** — the first
   sentence of every section, finding, and risk answers "what is this /
   what is the conclusion"; evidence and detail follow. 每个章节、每条
   发现、每条风险的第一句直接回答"这是什么/结论是什么"，证据与细节放
   后面。Good: "**iOS 冷启动必现崩溃** —— 崩溃点在主题切换后的资源释
   放路径，堆栈见下。" Bad: "经过对多个子系统的分析并交叉比对日志后，
   发现可能存在一个潜在问题……"
2. **Explain every term on first use; give an example where it is
   subtle（术语首用必解释，微妙处必举例）** — an abbreviation or piece
   of jargon gets one line of plain words the first time it appears; a
   mechanism gets one concrete scenario or analogy. 缩写与行话首次出现
   给一行大白话；机制给一个具体场景或比喻。Good: "UAF（use-after-free，
   释放后使用）——对象已释放但代码还在用，如同房间退租后还有人拿旧钥匙
   进来，表现为随机崩溃重启。" Bad: "命中 UAF，需排查。"（首次出现无解释）
3. **Never use a coined term bare（自造缩略语禁裸用）** — a name this
   work item invented（三同步约束、假绿、判定性实验……）is spelled out in
   plain words on first use; the short form may appear afterwards. 项目
   自造的名字首次出现必须拆开说清，之后才可用简称。Good: "三同步约束
   （plan_lint.py、references 模板、SKILL.md 三处必须同步改动）。"
4. **One claim per sentence（一条一个论点）** — more than two levels of
   subordination or parentheses means split the sentence; paths, version
   numbers, and line numbers belong in the evidence layer, not in the
   claim sentence. 超过两层转折或括号就拆句；路径、版本号、行号放证据
   层，不进论点句。Bad: "根因是 A（因为 B，而 B 又依赖 C（见 D:120，
   v2.3.1）），同时 E 的历史包袱导致 F，但 G 在另外的分支上已经……"
   ——一层句子塞四个论点加三层括号。Good: 论点句只说一件事，路径、版
   本、行号挪到证据行："根因是 A（见证据 1）。证据 1：`D:120`，v2.3.1
   起引入；证据 2：……"
5. **Ids are an index, not the content（编号是索引不是内容）** — the
   first occurrence of an id in a document carries a 3–8 character
   gloss; the sentence must still read cleanly with the ids covered. 每
   份文档里编号首次出现带 3–8 字说明；遮住编号句子仍要读得通。Bad:
   "T3 同步 + SC3/SC6 双断言 + 三同步约束。" Good: "T3（同步三处 lint
   副本）落地后，SC3 与 SC6 的断言（副本逐字节一致）随之生效。"
6. **Process noise is not content（过程与技术分离）** — AI workflow
   detail（子代理、门禁、簿记）goes into progress's process-notes tail or
   the review round that produced it, never mixed into technical
   conclusions. AI 工作流细节进 progress 的过程记录或产生它的审查轮次，
   不与技术结论混排。Bad: progress 技术条目里写"子代理运行至 150 轮上限
   被中断"。Good: 该细节放进 `（过程记录：…）`。
7. **Field lines are separate paragraphs（字段行各自成段）** — two
   consecutive lines that each start with a bold label (`**Source**:`,
   `**来源**：`) MUST be separated by a blank line, in every template and
   every generated document. Markdown renders consecutive lines of one
   paragraph as a single merged line: the source looks line-broken in an
   editor, but any preview fuses the whole header into one line.
   相邻两行 `**字段**：…` 之间必须空一行：Markdown 渲染会把同一段落的
   连续行合并成一行，编辑器里看着分行、预览里就粘成一长行。
8. **One language per document; borrow a foreign term only when it is the
   industry name（全文一种语言，外文只在必要时用）** — after the document
   language is decided, keep the whole document in it. An English term
   stays English only when it IS the industry name (`API`, `JWT`,
   `webhook`, `OAuth`) or has no accepted translation; when a widely used
   term exists in the document language, use it and put the original in
   parentheses on first use. Do not switch languages mid-sentence when a
   plain word in the document language says the same thing. 全文使用选定
   的那一种语言：术语本身就是行业名（API、JWT、webhook）或没有通行译名
   时保留外文；有通行译名的用中文表述并在首次出现时括注原文；句中不无
   故夹用外文。Good: "这条调用链的消费方会出现延迟回退（latency
   regression）。" Bad: "这个 flow 的 consumer 侧会有 latency regression。"
9. **Write like you explain to a colleague, not like a translated manual
   （像给同事讲，不像翻译腔）** — plain verbs and normal word order beat
   formal register and noun piles. 术语解释完了就直接说事，用平实的动词
   和正常语序，避免堆名词的公文体与翻译腔。Good: "把同步任务从轮询改成
   事件推送，因为轮询每 5 秒查一次库，成本太高。" Bad: "本方案拟对现有
   同步机制实施基于事件驱动范式的替代性迁移，以规避高频轮询所衍生的资
   源开销问题。"
10. **Decisions come with an example and the stakes（决策带例子，带代价）
    ** — every question or approval ask that reaches the user carries a
    concrete `比如` / `for example` line grounded in the feature being
    planned, states what a wrong answer costs to redo and whether that is
    cheap, and marks cheap-to-reverse decisions as safe to default. An
    approval ask quotes the plain-words summary, never a wall of ids. A
    question the user cannot evaluate gets a blind `按推荐`, which teaches
    the process nothing. 每个送到用户面前的追问或确认都带一个落在当前
    功能上的具体例子，说清答错要返工什么、好不好改；好改的明说"拿不准
    就按推荐"。请求确认时引用大白话摘要，而不是一串编号。Good: "旧版
    App 打不开设置页怎么办？比如：设置项换了存法，还装着旧版的手机要照
    样能打开设置。推荐：保留旧格式的读法——旧版只是看不到新设置项，改
    起来也快。" Bad: "Q2 — persisted schema backward-compatibility
    strategy？（无解释、无例子、无代价）"

---

## Visualization rules for `analysis.md`

`analysis.md` should favor visual formats over prose wherever possible.
The reader should be able to skim diagrams and tables to grasp the
shape of the change without reading wall-of-text rationale.

| Need to express | Use |
|-----------------|-----|
| System architecture | mermaid `flowchart` or `graph` |
| Request / data flow | mermaid `sequenceDiagram` |
| State transitions | mermaid `stateDiagram-v2` |
| Before / after | markdown tables or side-by-side code blocks |
| Decision matrix | markdown table with trade-off columns |
| Timeline | mermaid `gantt` or numbered list |
| Component relationships | mermaid `classDiagram` or `erDiagram` |

### Mermaid 10.2.3 compatibility

Every diagram MUST parse and render correctly on Mermaid 10.2.3.

**The full rule set lives in [`MERMAID-RULES.md`](MERMAID-RULES.md)** —
shared canonical source kept in sync across all skills. Read that file
end-to-end before authoring any new diagram. The two most common traps:

1. **Unquoted parens / brackets / curlies in edge labels.** Wrap
   the label in double quotes. Same rule for `subgraph` titles.

   - Bad: `A -->|step (x)| B`
   - Good: `A -->|"step (x)"| B`

2. **Literal `\n` inside `flowchart` / `graph` node labels, edge
   labels, or subgraph titles.** On Mermaid 10.2.3 + GitHub + many
   other renderers, `\n` renders as the two characters `\` and `n`
   instead of a line break. Always use `<br/>` for line breaks
   (and wrap in double quotes because the surrounding text usually
   contains `(` or `)`).

   - Bad: `A[xxx-api\n(Domain API)]`
   - Good: `A["xxx-api<br/>(Domain API)"]`

   This rule applies to flowchart-family diagrams only — sequence
   diagrams have separate rendering and are out of scope.

After writing, run the **Mermaid Compatibility Gate**:
`python3 SKILL_PATH/scripts/mermaid_lint.py <file>...` on every
just-written or just-edited file.
The script accepts multiple files in one call. If `STATUS=FAIL`, read
each `ERROR:` line, apply the suggested fix from
[`MERMAID-RULES.md`](MERMAID-RULES.md), save, and re-run until
`STATUS=PASS`. Do NOT proceed to the next step with `STATUS=FAIL`
standing.

The gate runs whenever a mermaid-bearing doc is just written:
1. After writing `analysis.md` for the first time (propose Step 4)
2. After review-driven fixes that updated `analysis.md` (apply)
3. Once on resume, to confirm prior sessions did not leave broken
   diagrams behind

If the script cannot be run, fall back to manual
review against [`MERMAID-RULES.md`](MERMAID-RULES.md). Skipping the
gate entirely is NOT an acceptable shortcut — broken diagrams block
human reviewers.
