# Review Output Template (6 sections)

Every review uses exactly these 6 sections, in this order, in the language
detected in Step 5. `review_template_builder.py` generates the same skeleton;
this file describes what goes into each section. Don't substitute an ad-hoc
structure such as "Strengths / Issues / What's Working Well" — the gate and
the user both expect these sections.

In section 4, keep the finding groups required by SKILL.md Step 6:
`Confirmed Findings` / `已确认问题` and `Potential Risks` / `潜在风险`.

## Chinese review

### 1. PR 概览
- PR 的目的和动机（基于标题、描述、分支名）
- 变更规模：X 个文件，+Y / -Z 行
- 涉及的主要模块和功能领域
- 若 PR 含截图/图片证据，补充 **图片证据摘要**：逐张说明图片内容、关键信息、与代码变更的对应关系

### 2. 仓库上下文分析
- 项目技术栈（语言、框架、工具链）
- 项目的编码规范和风格（基于 config 文件和已有代码推断）
- 此 PR 是否符合项目整体风格和架构模式
- 若为 diff-only 模式，需说明本次审查没有完整仓库上下文

### 3. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 特别关注：变更是否与项目现有代码风格一致
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（文件名、代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

### 4. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 检查是否有遗漏的修改（如：改了接口但没改调用方，改了 schema 但没改迁移）
- 指出这些疑点，并简单说明为何值得关注

### 5. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议
- 建议是否需要补充测试、文档、类型声明等
- 如果 PR 描述缺失或不清晰，建议改进 PR 描述

### 6. 总结评价
- 一行 `Verdict: <X>`，X 只能是 Approve、Request Changes、Comment 之一（门禁脚本读取这一行）
- 简要总结关键发现和建议优先级

## English review

### 1. PR Overview
- Purpose and motivation of the PR (based on title, description, branch names)
- Change scope: X files changed, +Y / -Z lines
- Primary modules and functional areas affected
- If screenshots/images are present, include a **Visual Evidence Summary**: what each image shows, key observed values/events, and how it maps to PR claims

### 2. Repository Context Analysis
- Project tech stack (languages, frameworks, toolchain)
- Project coding conventions and style (inferred from config files and existing code)
- Whether this PR aligns with the project's overall style and architectural patterns
- In diff-only mode, state that the review was done without full repo context

### 3. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments, readability, maintainability, architecture, modularity, code duplication, etc.
- Pay special attention to: whether changes are consistent with existing project code style
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or violations of best practices
- Clearly specify the exact location and nature of each problem (filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization with explanatory reasoning

### 4. Major Issues and Risks
- Evaluate hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, security vulnerabilities
- Check for missed changes (e.g., changed an interface but not its callers, changed a schema but not its migration)
- Point out suspicious areas and explain their potential impact

### 5. Incremental Suggestions
- Suggestions for improving code quality, maintainability, and test coverage
- Whether additional tests, documentation, or type annotations are needed
- If PR description is missing or unclear, suggest improvements

### 6. Summary Verdict
- One line `Verdict: <X>`, where X is exactly one of Approve, Request Changes, Comment (the gate reads this line)
- Brief summary of key findings and suggestion priorities
