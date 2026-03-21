# Development Guide

This guide is for contributors and developers working on the `mythril-agent-skills` repository itself.

For full coding conventions, naming rules, and architectural decisions, see [AGENTS.md](../AGENTS.md).

## Dev Environment Setup

```bash
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills

# Editable install with test dependencies
pip install -e ".[test]"
```

## Running Tests

Unit tests live in `tests/skills/` and cover pure functions across all skill scripts (URL parsing, formatters, validators, gate logic, template rendering, etc.). They require no network, git, or API access.

```bash
# Run all tests
pytest

# Verbose output
pytest -vv

# Run tests for a specific skill
pytest tests/skills/test_figma.py
pytest tests/skills/test_jira.py

# Filter by keyword
pytest -k "parse_url"
pytest -k "format_adf"
```

### Test coverage by skill

| Skill | Test file | What's covered |
|---|---|---|
| github-code-review-pr | `test_github_code_review_pr.py` | URL parsing, key-value output parsing, 4 quality gates, verdict detection, template rendering (EN/ZH), path selection helpers, cache lookup |
| git-repo-reader | `test_git_repo_reader.py` | URL parsing, normalize key, repo map JSON round-trip |
| figma | `test_figma.py` | Color conversion, paint formatting, node simplification, markdown rendering, URL parsing, safe filename |
| skill-creator | `test_skill_creator.py` | SKILL.md validation (12 edge cases), frontmatter parsing, stats calculation, benchmark aggregation, markdown generation |
| jira | `test_jira.py` | ADF→text (11 node types), issue/search markdown formatting, URL parsing |
| confluence | `test_confluence.py` | HTML stripping (11 patterns), page/space/search/comment formatting, URL parsing |

### Adding tests for new skills

1. Create `tests/skills/test_<skill_name>.py`
2. Import functions from the skill's `scripts/` directory (auto-added to `sys.path` by `conftest.py`)
3. Test pure functions only — avoid network, subprocess, or API calls
4. Run `pytest -vv` to verify

## Adding a New Skill

1. Create a new directory under `mythril_agent_skills/skills/`:

```bash
mkdir mythril_agent_skills/skills/my-skill
```

2. Create `SKILL.md` with required frontmatter:

```yaml
---
name: my-skill
description: |
  What this skill does and when to use it.
  Include trigger keywords for better AI assistant activation.
license: Apache-2.0
---

# My Skill

Detailed instructions, examples, and workflows...
```

3. Validate the skill structure:

```bash
python3 mythril_agent_skills/skills/skill-creator/scripts/quick_validate.py mythril_agent_skills/skills/my-skill
```

4. If the skill has Python scripts, add unit tests in `tests/skills/`.

5. Commit following this format:

```bash
git commit -m "[my-skill] Add initial skill with core workflows"
```

For full conventions (naming, description limits, security rules, cache usage, ordering), see [AGENTS.md](../AGENTS.md).

## Publishing

See [docs/PUBLISHING.md](./PUBLISHING.md) for PyPI publishing and testing instructions.

## Contributing

1. **Fork or create a branch** for your changes
2. **Follow** [AGENTS.md](../AGENTS.md) for code style and structure guidelines
3. **Add tests** for any new script functions
4. **Run `pytest`** to ensure all tests pass
5. **Commit** with descriptive messages: `[skill-name] Brief description`
6. **Open a pull request** with a summary of the changes
