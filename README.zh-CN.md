# mythril-agent-skills

<p align="center">
  <img src="docs/assets/banner.webp" width="500" alt="mythril-agent-skills">
</p>

面向多智能体 AI 编程助手的统一技能管理系统。本工具包（以 Python 包形式分发）提供一套精选的可复用技能集合，以及用于在 Github Copilot、Claude Code、Cursor、Codex、Gemini CLI、OpenClaw、Hermes 等工具之间安装、配置和维护技能的集中式 CLI 命令。

[English](./README.md) | 中文

## 什么是 Skill？

Skill（技能）是一个提示词/指令包，用于教 AI 助手如何处理特定类型的任务。可以把它理解为一个专用工具：它有名称、触发描述和详细的操作指令。

根据作用范围和管理方式，技能主要分为两类：

| 特性 | 用户级技能（全局） | 项目级技能（本地） |
| :--- | :--- | :--- |
| **作用范围** | 在你所有项目中均可使用 | 仅限特定项目仓库 |
| **可移植性** | 在同一台机器的不同项目间复用 | 随该项目仓库一起移动 |
| **适用场景** | 通用工具（如 Jira 集成、代码审查、Git 操作、Figma） | 项目专属规则（如自定义 UI 规范、特定构建/部署步骤） |
| **管理方式** | 安装在用户主目录（`~/.claude/skills`、`~/.cursor/skills` 等） | 存放在项目目录内（如 `.claude/skills/`、`.github/skills/`） |
| **版本控制** | 通过本工具包集中管理 | 提交到项目 Git 仓库，供团队共享 |

### 本工具包的定位

**`mythril-agent-skills` 专门用于管理用户级技能。** 它作为集中式 CLI 工具包，负责在你机器上的多个 AI 编程助手之间安装、配置并保持通用技能同步。

对于**项目级技能**，无需使用本安装器。我们推荐使用内置的 **[Skill Creator](./mythril_agent_skills/skills/skill-creator/)** 技能，在项目工作区中直接调用它来生成项目专属技能，然后提交到版本控制系统，让整个团队受益。

## 可用技能

[English](./README.md) | 中文

<details>
<summary><b>Meta</b>（工具类）</summary>
<br>

**[Skill Creator](./mythril_agent_skills/skills/skill-creator/)**

为任意 AI 平台创建/优化技能和提示词，含起草、测试用例生成、评估、基准测试、描述优化。

- **示例：** 帮我创建一个 Cursor skill
- **依赖：** —

</details>

<details>
<summary><b>代码审查</b></summary>
<br>

**[Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/)**

针对 Git 暂存区变更的上下文感知代码审查，读取相关文件验证。

- **示例：** 审查暂存的代码
- **依赖：** `git` CLI

**[Code Review (Local Branch Diff)](./mythril_agent_skills/skills/branch-diff-review/)**

纯本地 git 操作对比分支差异，无需平台 API，支持任意 git 仓库（GitHub、GitLab、Gitee、Bitbucket 等）。

- **示例：** Review 一下 feat/123 合到 main
- **依赖：** `git` CLI

**[Code Review (GitHub PR)](./mythril_agent_skills/skills/github-code-review-pr/)**

通过 `gh` CLI 对 Pull Request 进行上下文感知代码审查，支持 github.com 和 GitHub Enterprise（任意域名），使用 partial clone + sparse checkout 获取深层仓库上下文。

- **示例：** 审查这个 PR https://github.com/xxx/yyy/pull/100
- **依赖：** `git` CLI, `gh` CLI

</details>

<details>
<summary><b>Git & GitHub</b></summary>
<br>

**[Git Repo Reader](./mythril_agent_skills/skills/git-repo-reader/)**

克隆、缓存并阅读任意托管平台的 git 仓库（GitHub、GitLab、Gitee、Bitbucket 等），支持跨会话复用缓存。

- **示例：** 看看这个仓库 https://github.com/xxx/yyy
- **依赖：** `git` CLI

**[GH Operations](./mythril_agent_skills/skills/gh-operations/)**

使用 GitHub CLI (`gh`) 执行 GitHub issue/PR 工作流：读写 issue、查看/创建 PR、添加 PR 评论（含行内 review 评论）。

- **示例：** 看看这个 issue https://github.com/xxx/yyy/issues/18331
- **依赖：** `gh` CLI

**[GitHub PR Create](./mythril_agent_skills/skills/github-pr-create/)**

通过 `gh` CLI 创建 GitHub Pull Request。自动检测 PR 模板，根据代码变更填充内容，支持 GitHub Enterprise。确保从特性分支向正确的目标分支创建 PR。

- **示例：** 帮我提个PR
- **依赖：** `git` CLI, `gh` CLI

</details>

<details>
<summary><b>API 集成</b></summary>
<br>

**[Jira](./mythril_agent_skills/skills/jira/)**

通过 Jira REST API（内置 Python 脚本）处理 issue、sprint 和 board 工作流。

- **示例：** 看一下这个 Jira ticket https://yourorg.atlassian.net/browse/PROJ-123
- **依赖：** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Confluence](./mythril_agent_skills/skills/confluence/)**

通过 Confluence REST API（内置 Python 脚本）处理 page、space、comment 和 label 工作流。

- **示例：** 看一下这个 Confluence 页面 https://yourorg.atlassian.net/wiki/spaces/XX/pages/123
- **依赖：** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Figma](./mythril_agent_skills/skills/figma/)**

从 Figma 文件提取设计规格用于实现，涵盖布局、颜色、字体、组件规格，遇到 Figma 链接自动触发。

- **示例：** 这个 Figma 设计是什么样子 https://figma.com/file/xxx
- **依赖：** `FIGMA_ACCESS_TOKEN`

**[Glean](./mythril_agent_skills/skills/glean/)**

通过 Glean CLI (`glean`) 搜索公司知识库、与 Glean AI 对话以及执行完整 API 操作。涵盖搜索、对话、AI Agent、文档、合集、快捷方式、置顶等功能。

- **示例：** glean search "请假政策"
- **依赖：** `glean` CLI

</details>

<details>
<summary><b>数据处理</b></summary>
<br>

**[Excel](./mythril_agent_skills/skills/excel/)**

通过内置 Python 脚本（基于 openpyxl）读取、写入、搜索和操作 Excel 工作簿（.xlsx）。支持单元格/区域读写、搜索、工作表/列/行操作、样式设置、合并单元格、冻结窗格、自动筛选、CSV 转换，写操作默认保存为带时间戳的副本以保护原文件。

- **示例：** 读一下 report.xlsx 的前 20 行
- **依赖：** `openpyxl`（通过 pip 自动安装）

**[PDF](./mythril_agent_skills/skills/pdf/)**

通过内置 Python 脚本读取、提取和操作 PDF 文件。支持文本提取、表格提取（markdown/JSON/CSV）、元信息查看、PDF 转图片、合并、拆分、旋转、提取嵌入图片和解密。

- **示例：** 读一下 document.pdf 的内容
- **依赖：** `pypdf`、`pdfplumber`（通过 pip 自动安装）；`pypdfium2`（可选，用于 PDF 转图片）

**[Markdown to PDF](./mythril_agent_skills/skills/md-to-pdf/)**

将 Markdown 文件转换为 PDF，支持目录生成、自定义 CSS 样式、纸张大小选择和元数据设置。基于 markdown-pdf（markdown-it-py + PyMuPDF）。

- **示例：** 把 README.md 转成 PDF
- **依赖：** `markdown-pdf`（通过 `pip install mythril-agent-skills[md-to-pdf]` 安装）

</details>

<details>
<summary><b>媒体处理</b></summary>
<br>

**[ImageMagick](./mythril_agent_skills/skills/imagemagick/)**

通过 ImageMagick CLI 处理图片，支持缩放、格式转换、裁剪、缩略图、特效、水印、批量处理和元数据提取。

- **示例：** 把 photo.jpg 缩放到 800x600
- **依赖：** `magick` CLI

**[FFmpeg](./mythril_agent_skills/skills/ffmpeg/)**

通过 FFmpeg CLI 处理视频和音频，支持转码、格式转换、裁剪、合并、缩放、压缩、提取音频/字幕、GIF 创建，以及音频格式转换（MP3、WAV、PCM、OGG、AAC、FLAC、OPUS）。

- **示例：** 把 video.mov 转成 mp4
- **依赖：** `ffmpeg` CLI

</details>

<details>
<summary><b>内容创作</b></summary>
<br>

**[Blog Writer](./mythril_agent_skills/skills/blog-writer/)**

通过交互式信息收集，撰写、润色和适配博客内容。该技能会先确认写作语言，并以技术主题为主但不限于技术。支持个人博客、内部邮件/通讯类博客和公众号文章。

- **示例：** 帮我写一篇关于这个开源项目的博客
- **依赖：** —

</details>

<details>
<summary><b>全栈工作区</b></summary>
<br>

**[Fullstack Init](./mythril_agent_skills/skills/fullstack-init/)**

初始化或更新多仓库全栈工作区，统一 AI 上下文。创建带有自动生成仓库表的 AGENTS.md、独立 git 仓库的文档目录、四个工作区 Agent（planner/dev/reviewer/debugger）以及工作跟踪目录（feat/refactor/fix）。

- **示例：** 初始化全栈工作区
- **依赖：** `git` CLI

**[Fullstack Impl](./mythril_agent_skills/skills/fullstack-impl/)**

在多仓库全栈工作区中实现功能、重构和修复。从 Jira/Confluence/GitHub/Figma 链接收集上下文，创建分支，委派给工作区 Agent，在文档仓库中跟踪进度。

- **示例：** 帮我在工作区里做这个 Jira 卡
- **依赖：** 工作区需先通过 `fullstack-init` 初始化

</details>

---

## 快速开始

直接使用本仓库提供的技能：

<details>
<summary>方式 A：通过 pip 安装</summary>

如果只想安装并使用现成的技能，从这里开始。
从 PyPI 安装，无需克隆仓库：

```bash
pip install mythril-agent-skills
```

升级到最新版本：

```bash
pip install -U mythril-agent-skills
```

安装后提供四个命令：

| 命令 | 描述 |
|---|---|
| `skills-setup` | 交互式安装器 — 选择 AI 工具和要安装的技能 |
| `skills-cleanup` | 交互式卸载器 — 选择已安装的技能进行移除 |
| `skills-check` | 依赖检查器 — 验证并配置所需的 CLI 工具和 API 密钥 |
| `skills-clean-cache` | 缓存清理器 — 删除技能运行时产生的临时文件 |

**安装技能：**

```bash
skills-setup              # 交互式：选择工具，再选择技能
skills-setup .cursor      # 直接指定目标：跳过工具选择步骤
```

**移除技能：**

```bash
skills-cleanup
```

**检查依赖：**

```bash
skills-check                    # 交互式：选择要检查的技能
skills-check gh-operations jira figma  # 检查指定技能
```

**清理缓存临时文件：**

```bash
skills-clean-cache          # 交互式：列出缓存内容，确认后删除
skills-clean-cache --force  # 直接删除，不询问确认
skills-clean-cache --repos  # 交互式：选择要删除的仓库
```

检查器将会：
- 无参数运行时启动交互式 UI 让你选择技能
- 检测缺失的 CLI 工具（如 `gh`）并提供自动安装选项
- 提示输入缺失的 API 密钥/Token 并保存到 shell 配置文件
- 验证认证状态（如 `gh auth status`）

</details>

<details>
<summary>方式 B：Claude Code 插件市场</summary>

如果你使用 [Claude Code](https://code.claude.com/)，可以通过[插件市场](https://code.claude.com/docs/en/plugin-marketplaces)安装技能，无需 pip。另见：[发现和安装插件](https://code.claude.com/docs/en/discover-plugins)。

添加市场：
```bash
/plugin marketplace add jie-meng/mythril-agent-skills
```

一键安装所有技能：

```bash
/plugin install all-skills@mythril-agent-skills
```

或按需安装单个技能：

```bash
/plugin install figma@mythril-agent-skills
/plugin install jira@mythril-agent-skills
/plugin install github-code-review-pr@mythril-agent-skills
```

你可以使用 `/plugin discover` 交互式地发现并安装插件：

<p align="center">
  <img src="docs/assets/cc-plugin-usage.webp" width="600" alt="添加市场并安装插件">
</p>

<details>
<summary>全部可用插件</summary>

| 插件 | 描述 |
|---|---|
| `all-skills` | 全部技能包（共 18 个） |
| `skill-creator` | 为任意 AI 平台创建/改进技能和提示词 |
| `code-review-staged` | 暂存区代码审查 |
| `branch-diff-review` | 本地分支差异代码审查 |
| `github-code-review-pr` | 通过 GitHub CLI 审查 PR |
| `git-repo-reader` | 克隆、缓存并阅读任意 git 仓库 |
| `gh-operations` | GitHub CLI 操作（issue 和 PR） |
| `jira` | Jira REST API 集成 |
| `confluence` | Confluence REST API 集成 |
| `figma` | 提取 Figma 设计规格 |
| `glean` | Glean CLI 企业知识搜索与 AI 对话 |
| `excel` | 读取、写入、搜索和操作 Excel 工作簿（.xlsx） |
| `pdf` | 读取、提取和操作 PDF 文件 |
| `md-to-pdf` | 将 Markdown 文件转换为 PDF |
| `imagemagick` | 通过 ImageMagick CLI 处理图片 |
| `ffmpeg` | 通过 FFmpeg CLI 处理视频和音频 |
| `blog-writer` | 撰写、润色和适配以技术为主的多语言博客 |
| `fullstack-init` | 初始化多仓库全栈工作区 |
| `fullstack-impl` | 在全栈工作区中实现功能/修复 |

</details>

后续更新：

```bash
/plugin marketplace update mythril-agent-skills
```

卸载单个插件：

```bash
/plugin uninstall figma@mythril-agent-skills
```

移除整个市场（同时卸载所有已安装的插件）：

```bash
/plugin marketplace remove mythril-agent-skills
```

> **提示：** 此方式仅将技能安装到 Claude Code，不包含 CLI 命令（如 `skills-setup`、`skills-cleanup`、`skills-clean-cache`）。如需完整工具包支持（多工具安装、依赖检查、缓存管理），请使用方式 A。

</details>

或自定义技能：

<details>
<summary>方式 C：自定义技能（GitHub Fork 或独立克隆）</summary>

如果想自定义技能并维护自己的仓库，有两种等效方式：

- **GitHub fork**（保持与 github.com 上游的关联）
- **独立克隆**（完全脱离上游，可托管在任意平台）

选择以下一种方式进行初始化，然后按照后面的共用步骤操作。

**方式 A — GitHub Fork（与上游保持关联）：**

```bash
# 在 GitHub 上 Fork，然后克隆你的 Fork：
git clone https://github.com/<your-username>/mythril-agent-skills.git
cd mythril-agent-skills
```

**方式 B — 独立克隆（与上游脱钩，可用于非 GitHub 平台）：**

```bash
# 1. 克隆原始仓库
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills

# 2. 与上游脱钩（删除 .git，创建全新仓库）
python3 scripts/init-fork.py

# 3. 按照屏幕提示将代码推送到新的远程仓库
```

初始化脚本将会：
- 删除 `.git` 历史记录（切断与上游的关联）
- 执行 `git init`（空仓库 — 你自己创建第一个 commit）
- 可选：重命名根目录

> **警告**：此操作不可逆，仅执行一次。请在全新克隆的副本上运行。

**两种方式的共用步骤：**

直接运行脚本，无需安装：

```bash
python3 scripts/skills-setup.py       # 交互式安装器
python3 scripts/skills-cleanup.py     # 交互式卸载器
python3 scripts/skills-check.py       # 依赖检查器
```

**与上游保持同步（可选）：**

- **方式 A（GitHub fork）**：使用 GitHub 内置的 **"Sync fork"** 按钮
- **方式 B（独立克隆）**：使用内置同步脚本（见下方）

```bash
python3 scripts/sync-upstream.py              # 交互式同步
python3 scripts/sync-upstream.py --dry-run     # 仅预览变更
python3 scripts/sync-upstream.py --force        # 直接应用，不询问确认
```

同步脚本只处理上游已存在的技能。**你自定义的、名称唯一的技能永远不会被覆盖** — 无需任何配置。

只有当你需要防止某个**上游技能**被覆盖时，才在 `.sync-upstream.json` 中使用 `exclude_skills`（例如：你在本地修改过 `jira`，或者想保护一个自定义技能名，以防上游未来新增同名技能）：

```json
{
  "exclude_skills": ["jira"]
}
```

完整指南请参阅 **[docs/FORK-SYNC.md](./docs/FORK-SYNC.md)**。

- 如果你**只新增名称唯一的自定义技能**，效果最佳 — 不会产生冲突
- 如果你**修改过上游技能**（如自定义了 `jira`），同步时可能出现需要手动解决的合并冲突

</details>

---

## 安装器工作原理

`skills-setup` 命令会引导你完成两个交互式界面：

1. **选择 AI 工具** — 选择要将技能安装到哪些工具
2. **选择技能** — 选择要安装哪些技能

技能选择界面分为两个部分：**Builtin Skills**（包内置技能）和 **Local Skills**（当前目录发现的技能）。详情见[安装本地技能](#安装本地技能)。

```
Select skills to install:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [x]  Select All / Deselect All
  ------------------------------------
  Builtin Skills (16)
  [x]  blog-writer
  [x]  code-review-staged
  [x]  figma
  ...
  Local Skills (2)  [my-skills/]
  [x]  my-custom-skill
  [x]  jira  (overrides builtin)

  18/18 selected
```

未在你机器上安装的工具将以灰色显示并标注 `[-]`，无法被选中。

安装完成后，对于需要外部依赖（CLI 工具或 API Token）的内置技能，`skills-check` 会自动运行。本地技能不参与此检查——其依赖管理由用户自行负责。

### 安装本地技能

当你在某个包含技能子目录（任意非隐藏的、含有 `SKILL.md` 文件的子目录）的目录下运行 `skills-setup` 时，安装器会自动发现这些**本地技能**。这让你可以轻松安装下载的第三方或自定义技能集合：

```bash
# 克隆第三方技能仓库或你自己的自定义技能集合
git clone https://github.com/someone/my-custom-skills.git
cd my-custom-skills

# 在该目录内运行 skills-setup
skills-setup
```

安装器会扫描当前目录的直接子目录，并将发现的技能以单独的 **Local Skills** 部分展示在内置技能下方。

**冲突处理：** 如果某个本地技能与内置技能同名，它会以醒目颜色高亮显示，并附有 `(overrides builtin)` 说明。同时安装时，内置技能先安装、本地技能后安装——因此本地版本将覆盖内置版本。

**依赖检查：** 安装完成后，`skills-check` 仅对内置技能运行。本地技能的依赖管理（安装所需 CLI 工具、API 密钥等）由用户自行负责。

### 支持的工具及技能路径

所有配置目录均相对于用户主目录（macOS/Linux 为 `~`，Windows 为 `%USERPROFILE%`）。

| # | 工具 | 技能路径 |
|---|---|---|
| 1 | Copilot CLI / VS Code | `~/.copilot/skills/` |
| 2 | Claude Code | `~/.claude/skills/` |
| 3 | Cursor | `~/.cursor/skills/` |
| 4 | Codex | `~/.codex/skills/` |
| 5 | Gemini CLI | `~/.gemini/skills/` |
| 6 | Qwen CLI | `~/.qwen/skills/` |
| 7 | Opencode | `~/.config/opencode/skills/` |
| 8 | Grok CLI | `~/.grok/skills/` |
| 9 | OpenClaw | `~/.openclaw/skills/` |
| 10 | Hermes | `~/.hermes/skills/` |

### 卸载已安装的技能

```bash
skills-cleanup
```

卸载命令同样引导你完成两个界面：

1. **选择 AI 工具** — 选择要扫描哪些工具目录（默认扫描所有已检测到的）
2. **选择要移除的技能** — 树形视图展示每个工具及其已安装的技能（默认不选中）

```
Select skills to remove:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [ ]  Select All / Deselect All
  ------------------------------------
  Copilot CLI  ~/.copilot/skills/  (0/3)
      [ ]  code-review-staged
      [ ]  figma
      [ ]  skill-creator
  Cursor  ~/.cursor/skills/  (0/2)
      [ ]  gh-operations
      [ ]  jira

  0/5 selected for removal
```

### 项目级安装

如需在项目级别安装技能，手动复制即可：

```bash
cp -r mythril_agent_skills/skills/skill-name ./your-project/.github/skills/
# 或
cp -r mythril_agent_skills/skills/skill-name ./your-project/.claude/skills/
```

---

## 项目结构

```
mythril-agent-skills/
├── .claude-plugin/              # Claude Code 插件市场
│   └── marketplace.json         # 插件目录，供 /plugin install 使用
├── mythril_agent_skills/        # Python 包（同时也是全量插件）
│   ├── cli/                     # CLI 入口点
│   │   ├── skills_setup.py      # 交互式安装器
│   │   ├── skills_cleanup.py    # 交互式卸载器
│   │   └── skills_check.py      # 依赖检查器与配置器
│   └── skills/                  # 内置技能定义
│       ├── skill-creator/       # 创建和改进技能
│       ├── figma/               # 从 Figma 提取设计规格
│       ├── gh-operations/       # GitHub CLI issue/PR/commit 工作流
│       ├── ffmpeg/              # 通过 FFmpeg CLI 处理视频和音频
│       ├── imagemagick/         # 通过 ImageMagick CLI 处理图片
│       ├── glean/               # Glean CLI 企业知识搜索与 AI 对话
│       ├── excel/              # 通过 openpyxl 操作 Excel 工作簿
│       ├── pdf/                 # PDF 读取、提取和操作
│       ├── md-to-pdf/           # Markdown 转 PDF
│       ├── jira/                # Jira REST API issue/sprint/board 工作流
│       ├── code-review-staged/  # 结构化代码审查
│       ├── git-repo-reader/     # 克隆并阅读任意 git 仓库
│       ├── blog-writer/         # 以技术为主的多语言博客写作
│       ├── fullstack-init/      # 初始化多仓库工作区
│       └── fullstack-impl/      # 跨仓库全栈实现
├── plugins/                     # 单技能插件包装器（symlink 指向 skills/）
├── scripts/                     # 开发脚本及向后兼容包装器
│   ├── sync-upstream.py         # Fork 上游同步工具
│   └── init-fork.py             # 一次性 Fork 初始化（脱钩 + git 重初始化）
├── tests/                       # 技能脚本单元测试
│   └── skills/                  # 每个技能一个测试文件
├── docs/
│   ├── DEVELOPMENT.md           # 开发环境、测试、贡献指南
│   ├── INSTALLATION.md          # 完整依赖参考
│   ├── PUBLISHING.md            # PyPI 发布与测试指南
│   ├── FORK-SYNC.md             # Fork 同步指南
│   └── fullstack/               # 全栈技能设计文档
├── .sync-upstream.json          # 上游同步配置（供 Fork 使用）
├── pyproject.toml               # 包配置
├── AGENTS.md                    # 面向 Agent 的开发规范
├── LICENSE                      # Apache 2.0 许可证
└── README.md                    # 英文版说明
```

### 技能目录结构

每个技能遵循以下模式：

```
mythril_agent_skills/skills/skill-name/
├── SKILL.md                  # 必需：元数据 + 指令
├── README.md                 # 可选：人类可读概览
├── scripts/                  # 可选：辅助脚本（Python/Bash）
├── references/               # 可选：文档、指南、Schema
├── agents/                   # 可选：评估用提示词
└── assets/                   # 可选：模板、图标、HTML 资源
```

---

## 开发与贡献

开发环境搭建、运行测试、新增技能及贡献指南，请参阅 **[docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)**。

完整的编码规范与架构决策，请参阅 **[AGENTS.md](./AGENTS.md)**。

---
