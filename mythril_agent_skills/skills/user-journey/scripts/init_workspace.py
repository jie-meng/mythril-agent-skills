#!/usr/bin/env python3
"""Initialize a user-journey workspace.

Creates the standard workspace layout:

    <workspace>/
    ├── JOURNEY.md
    ├── journey.json
    ├── DESIGN.md            (copied from a preset under SKILL_PATH/templates/design-styles/)
    ├── index.html           (with journey.json + design-tokens inlined)
    ├── README.md
    ├── preview.py
    └── assets/
        ├── styles.css
        ├── render.js
        └── wireframe.js

The workspace is also initialized as an independent git repo so changes are
tracked. Uses only Python 3.10+ standard library — no third-party deps.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
WORKSPACE_TPL = TEMPLATES_DIR / "workspace"
DESIGN_STYLES_DIR = TEMPLATES_DIR / "design-styles"

VALID_LANGUAGES = {"en", "zh"}

# Import the canonical mermaid label-escape helper from the bundled copy
# in the same scripts/ directory. The bundled mermaid_lint.py is kept in
# sync with mythril_agent_skills/shared/mermaid/mermaid_lint.py by
# scripts/sync-shared-assets.py.
sys.path.insert(0, str(SCRIPT_DIR))
from mermaid_lint import escape_label_for_mermaid  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helpers (tested in tests/skills/test_user_journey.py)
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert arbitrary text to a lowercase-hyphenated slug."""
    if not text:
        return "untitled"
    text = text.strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def list_design_styles(styles_dir: Path = DESIGN_STYLES_DIR) -> list[str]:
    """Return the available DESIGN.md preset slugs (without .md extension)."""
    if not styles_dir.exists():
        return []
    return sorted(p.stem for p in styles_dir.glob("*.md"))


def resolve_design_style(name: str, styles_dir: Path = DESIGN_STYLES_DIR) -> Path:
    """Resolve a design-style name to its template path. Raises if missing."""
    if not name:
        raise ValueError("design style name is required")
    candidate = styles_dir / f"{name}.md"
    if not candidate.exists():
        available = ", ".join(list_design_styles(styles_dir)) or "<none>"
        raise FileNotFoundError(
            f"design style '{name}' not found. Available: {available}"
        )
    return candidate


def build_initial_journey(
    *,
    title: str,
    subtitle: str,
    persona_name: str,
    persona_role: str,
    language: str,
) -> dict:
    """Build the initial journey.json structure (1 persona, 3 skeleton stages)."""
    if language not in VALID_LANGUAGES:
        raise ValueError(
            f"language must be one of {sorted(VALID_LANGUAGES)}, got {language!r}"
        )
    persona_slug = slugify(persona_name) or "primary-user"
    if language == "zh":
        labels = ["发现", "尝试", "习惯"]
        summaries = [
            "用户了解到产品并决定试用",
            "用户完成首次核心动作",
            "用户形成稳定使用习惯",
        ]
    else:
        labels = ["Discover", "Try", "Habit"]
        summaries = [
            "User learns about the product and decides to try it",
            "User completes the first core action",
            "User forms a stable usage habit",
        ]

    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "schema_version": "1",
        "title": title,
        "subtitle": subtitle,
        "language": language,
        "personas": [
            {
                "id": persona_slug,
                "name": persona_name,
                "role": persona_role,
                "goals": [],
                "frustrations": [],
                "context": "",
            }
        ],
        "stages": [
            {
                "id": slugify(labels[idx]) or f"stage-{idx + 1}",
                "label": labels[idx],
                "summary": summaries[idx],
                "persona_id": persona_slug,
                "steps": [],
                "notes": "",
            }
            for idx in range(3)
        ],
        "metadata": {
            "created": today,
            "last_updated": today,
            "version": "0.1.0",
        },
    }


def build_mermaid(journey: dict) -> str:
    """Render the stages as a mermaid flowchart body (indented for codeblock).

    Uses the shared escape_label_for_mermaid helper so any embedded
    newlines, parens, brackets, or double quotes in stage labels become
    renderer-safe (literal `\\n` and real newlines → `<br/>`).
    """
    stages = journey.get("stages", [])
    if not stages:
        return "    %% No stages yet"
    nodes = [
        f'    {s["id"]}[{escape_label_for_mermaid(s["label"])}]'
        for s in stages
    ]
    edges = [
        f"    {stages[i]['id']} --> {stages[i + 1]['id']}"
        for i in range(len(stages) - 1)
    ]
    return "\n".join(nodes + edges)


def render_template(
    template: str,
    *,
    title: str,
    subtitle: str,
    language: str,
    persona_name: str,
    persona_slug: str,
    persona_role: str,
    first_stage_label: str,
    mermaid_body: str,
    date: str,
    journey_json: str,
    design_tokens_json: str,
) -> str:
    """Substitute the {{TOKEN}} placeholders in a template string."""
    mapping = {
        "{{TITLE}}": title,
        "{{SUBTITLE}}": subtitle,
        "{{LANG}}": language,
        "{{PERSONA_NAME}}": persona_name,
        "{{PERSONA_SLUG}}": persona_slug,
        "{{PERSONA_ROLE}}": persona_role,
        "{{FIRST_STAGE_LABEL}}": first_stage_label,
        "{{MERMAID_BODY}}": mermaid_body,
        "{{DATE}}": date,
        "{{JOURNEY_JSON}}": journey_json,
        "{{DESIGN_TOKENS_JSON}}": design_tokens_json,
    }
    out = template
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def parse_design_frontmatter(md_text: str) -> dict:
    """Extract DESIGN.md YAML frontmatter into a python dict.

    Hand-rolled mini-parser — no PyYAML dependency. Supports the subset used
    by our design-style presets: top-level scalars + nested maps two levels
    deep with string/numeric scalar leaves.
    """
    if not md_text.startswith("---"):
        return {}
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}
    yaml_text = parts[1].strip("\n")
    return _parse_simple_yaml(yaml_text)


def _parse_simple_yaml(text: str) -> dict:
    """Very small YAML subset parser: top-level keys + 2 levels of nested maps."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent + 2, child))
        else:
            parent[key] = _coerce_scalar(value)
    return root


def _coerce_scalar(value: str):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


# ---------------------------------------------------------------------------
# Filesystem ops
# ---------------------------------------------------------------------------

def copy_workspace_template(dst: Path, *, force: bool) -> None:
    """Copy the template tree (HTML, CSS, JS, README, preview.py) into dst."""
    dst.mkdir(parents=True, exist_ok=True)
    if not force and any(dst.iterdir()):
        raise FileExistsError(
            f"workspace {dst} is not empty. Pass --force to overwrite."
        )
    assets_src = WORKSPACE_TPL / "assets"
    (dst / "assets").mkdir(exist_ok=True)
    for path in assets_src.iterdir():
        if path.is_file():
            shutil.copy2(path, dst / "assets" / path.name)
    shutil.copy2(WORKSPACE_TPL / "preview.py", dst / "preview.py")
    (dst / "preview.py").chmod(0o755)


def write_outputs(
    workspace: Path,
    *,
    journey: dict,
    design_md_text: str,
    design_tokens: dict,
    journey_md_text: str,
    index_html_text: str,
    readme_text: str,
) -> None:
    (workspace / "DESIGN.md").write_text(design_md_text, encoding="utf-8")
    (workspace / "journey.json").write_text(
        json.dumps(journey, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (workspace / "JOURNEY.md").write_text(journey_md_text, encoding="utf-8")
    (workspace / "index.html").write_text(index_html_text, encoding="utf-8")
    (workspace / "README.md").write_text(readme_text, encoding="utf-8")


def git_init(workspace: Path) -> bool:
    """Initialize the workspace as an independent git repo. Returns True on success."""
    if (workspace / ".git").exists():
        return True
    try:
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main"],
            cwd=workspace,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (workspace / ".gitignore").write_text(
            "__pycache__/\n.DS_Store\n.idea/\n.vscode/\n",
            encoding="utf-8",
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    workspace = Path(args.path).expanduser().resolve()
    language = args.language or "en"
    if language not in VALID_LANGUAGES:
        print(f"error: --language must be one of {sorted(VALID_LANGUAGES)}", file=sys.stderr)
        return 2
    try:
        design_path = resolve_design_style(args.design_style)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    title = args.title or workspace.name
    subtitle = args.subtitle or ""
    persona_name = args.persona or ("Primary user" if language == "en" else "主要用户")
    persona_role = args.persona_role or (
        "Primary user of the product" if language == "en" else "产品主要使用者"
    )

    journey = build_initial_journey(
        title=title,
        subtitle=subtitle,
        persona_name=persona_name,
        persona_role=persona_role,
        language=language,
    )

    design_md_text = design_path.read_text(encoding="utf-8")
    design_tokens = parse_design_frontmatter(design_md_text)

    mermaid_body = build_mermaid(journey)
    first_stage_label = journey["stages"][0]["label"] if journey["stages"] else ""

    journey_json_inline = json.dumps(journey, indent=2, ensure_ascii=False)
    design_tokens_inline = json.dumps(design_tokens, indent=2, ensure_ascii=False)

    journey_md_tpl = (WORKSPACE_TPL / "JOURNEY.md").read_text(encoding="utf-8")
    index_html_tpl = (WORKSPACE_TPL / "index.html").read_text(encoding="utf-8")
    readme_tpl = (WORKSPACE_TPL / "README.md").read_text(encoding="utf-8")

    today = datetime.now().strftime("%Y-%m-%d")
    common_kwargs = dict(
        title=title,
        subtitle=subtitle,
        language=language,
        persona_name=persona_name,
        persona_slug=journey["personas"][0]["id"],
        persona_role=persona_role,
        first_stage_label=first_stage_label,
        mermaid_body=mermaid_body,
        date=today,
        journey_json=journey_json_inline,
        design_tokens_json=design_tokens_inline,
    )
    journey_md_text = render_template(journey_md_tpl, **common_kwargs)
    index_html_text = render_template(index_html_tpl, **common_kwargs)
    readme_text = render_template(readme_tpl, **common_kwargs)

    if args.dry_run:
        print(f"[dry-run] would create workspace at {workspace}")
        print(f"[dry-run] design style: {design_path.name}")
        print(f"[dry-run] language: {language}")
        print(f"[dry-run] stages: {len(journey['stages'])}")
        return 0

    try:
        copy_workspace_template(workspace, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_outputs(
        workspace,
        journey=journey,
        design_md_text=design_md_text,
        design_tokens=design_tokens,
        journey_md_text=journey_md_text,
        index_html_text=index_html_text,
        readme_text=readme_text,
    )

    git_ok = git_init(workspace)
    print(f"OK: workspace created at {workspace}")
    print(f"  design style:  {design_path.stem}")
    print(f"  language:      {language}")
    print(f"  stages:        {len(journey['stages'])} (skeleton)")
    print(f"  git tracked:   {'yes' if git_ok else 'no (git not available)'}")
    print()
    print(f"  open:  double-click {workspace / 'index.html'}")
    print(f"  or:    cd {workspace} && python3 preview.py")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a user-journey workspace.",
    )
    parser.add_argument(
        "--path",
        help="destination directory for the workspace (required unless --list-styles is set)",
    )
    parser.add_argument(
        "--title",
        help="title of the journey (defaults to the workspace directory name)",
    )
    parser.add_argument(
        "--subtitle",
        default="",
        help="one-line scope statement ('from X to Y')",
    )
    parser.add_argument(
        "--persona",
        help="primary persona name",
    )
    parser.add_argument(
        "--persona-role",
        help="primary persona role description",
    )
    parser.add_argument(
        "--language",
        choices=sorted(VALID_LANGUAGES),
        default="en",
        help="language for default labels and template prose",
    )
    parser.add_argument(
        "--design-style",
        default="corporate-clean",
        help="design-style preset slug (see SKILL_PATH/templates/design-styles/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files if the workspace is not empty",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would happen without writing any files",
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="list available design-style presets and exit",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.list_styles:
        for name in list_design_styles():
            print(name)
        sys.exit(0)
    if not args.path:
        print("error: --path is required (or pass --list-styles to list presets)", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(args))


if __name__ == "__main__":
    main()
