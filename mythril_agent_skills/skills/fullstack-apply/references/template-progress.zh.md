## `progress.md`

`progress.md` is a **dated log**. Every meaningful change — kickoff,
per-repo completion, review-driven fixes, user feedback, follow-up
edits — is recorded as a `### <date>` section. Each entry **opens with a
bold result line** (`**Result**:` / `**结果**：`) — the decision-maker's
first line — and **closes with a process-notes tail**
(`（Process notes: …）` / `（过程记录：…）`) holding AI-workflow detail.
Git history is the authoritative record of code changes; this file is
the human-readable narrative that ties changes to decisions.


### Chinese

```markdown
# 进度：<工作名称>

**最后更新**：<date>

**分支**：<branch-name>

## 已完成

（暂无）

## 进行中

- [ ] <当前步骤>

## 阻塞

（无）

## 变更记录

### <date> — 启动

**结果**：<一两句人话：发生了什么、现在状态如何——给决策者的第一行>
- 创建工作计划
- 确定涉及仓库：<list>
- 创建分支：<list>
（过程记录：<子代理运行情况、门禁输出、措辞同步等 AI 工作流细节>）

### <date> — <发生了什么>

**结果**：<一两句人话：发生了什么、现在状态如何>
- <做了什么、为什么、结果如何>
（过程记录：<AI 工作流细节>）
```


### Successor back-link — `## Successors` table (optional)

The forward link is what always carries the chain forward: the
successor's `**Source**` / `**Predecessor**` points at the archived
predecessor and is written for every successor.

A reverse `## Successors` (English) / `## 后续工作` (Chinese) table can
**additionally** be appended to the predecessor's `progress.md` — but
only if the successor is already known while the predecessor is still
active, i.e. **before** it is archived. Because a successor is normally
planned only *after* archiving, this back-link is best-effort and often
absent. That is fine: archive is final and archived directories are
never edited; discovery relies on the `-vN` naming convention plus the
forward link instead.

---
