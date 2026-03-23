#!/usr/bin/env python3
"""Prepare and clean a guarded PR review session.

This script standardizes high-risk operational steps for github-code-review-pr:

1. Fetch PR metadata and diff exactly once (non-interactive pager disabled)
2. Run path selection (A/B/C/D) via path_select.py
3. Prepare local repo context with branch checkout + fallback (pull/<PR>/head)
4. Persist all session state in a manifest JSON
5. Perform deterministic cleanup with required [PATH-CLEANUP] markers

Path overview:
  A — already inside the target repo
  B — repo found in shared git-repo-cache
  C — clone into shared cache via repo_manager.py (reusable, lightweight)
  D — blobless sparse-clone into skill temp cache (large repos or C failure)
  DIFF_ONLY — user explicitly chose no clone (diff + metadata review only)

Large-repo decision flow:
  When path_select.py chooses C but the repo exceeds the size threshold
  (default 100 MB), ``prepare`` saves a pending-decision marker and exits
  with code 10 (PENDING_DECISION_EXIT_CODE).  The AI agent reads
  REPO_SIZE_MB and PENDING_RUN_DIR from stdout, presents options to the
  user, and re-runs with ``--force-path`` and ``--run-dir`` to resume.

Usage:
    # Fresh session
    python3 scripts/review_runner.py prepare <PR_URL_OR_NUMBER>

    # Resume after pending decision (exit code 10)
    python3 scripts/review_runner.py prepare <PR_URL_OR_NUMBER> \
        --force-path C|D|diff-only --run-dir <PENDING_RUN_DIR>

    python3 scripts/review_runner.py cleanup <manifest-path>
    python3 scripts/review_runner.py purge   <manifest-path>

Output (prepare — normal):
    [PATH-CHECK] ... lines (from path_select)
    [PATH-SELECTED] ... line (from path_select)
    RUN_MANIFEST=<path>
    PR_VIEW_JSON_PATH=<path>
    PR_DIFF_PATH=<path>
    SELECTED_PATH=A|B|C|D|DIFF_ONLY
    REPO_PATH=<path-or-empty>
    REPO_WORKDIR=<path-or-empty>
    PR_STATE=<OPEN|CLOSED|MERGED>
    CONTEXT_MODE=<full_repo|diff_only>
    CONTEXT_LIMITATION=<message-or-empty>

Output (prepare — pending decision, exit code 10):
    NEEDS_USER_DECISION=true
    REPO_SIZE_MB=<float>
    THRESHOLD_MB=<int>
    PENDING_RUN_DIR=<path>
    PR_VIEW_JSON_PATH=<path>
    PR_DIFF_PATH=<path>

Output (cleanup):
    [PATH-CLEANUP] ... line(s)

Uses Python 3.10+ standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


PR_VIEW_FIELDS = (
    "number,title,body,state,author,baseRefName,headRefName,labels,reviewDecision,"
    "additions,deletions,changedFiles,commits,files,comments,reviews,url"
)

REPO_SIZE_THRESHOLD_KB = 100 * 1024

# Exit code when repo exceeds size threshold and user must choose a path.
# The AI agent should read REPO_SIZE_MB and PENDING_RUN_DIR from stdout,
# present options to the user, then re-run with --force-path and --run-dir.
PENDING_DECISION_EXIT_CODE = 10

COMMAND_LOG: list[str] = []


@dataclass
class SessionManifest:
    """Serializable review session state for deterministic cleanup."""

    run_dir: str
    pr_ref: str
    pr_url: str
    repo_url: str
    host: str
    owner: str
    repo: str
    pr_number: int
    base_ref_name: str
    head_ref_name: str
    pr_state: str
    selected_path: str
    repo_path: str
    repo_workdir: str
    original_branch: str
    checkout_ref: str
    context_mode: str
    context_limitation: str
    pr_view_json_path: str
    pr_diff_path: str
    command_log_path: str
    path_select_log_path: str
    cleanup_log_path: str
    review_text_path: str
    review_dir: str
    created_at_utc: str


def get_skill_cache_dir() -> Path:
    """Return github-code-review-pr cache directory for this OS user."""
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    else:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg_cache_home) if xdg_cache_home else home / ".cache"
    cache_dir = base / "mythril-skills-cache" / "github-code-review-pr"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_shared_repo_cache_root(skill_cache_dir: Path | None = None) -> Path:
    """Return shared repo cache root used by repo_manager.py."""
    base = (skill_cache_dir or get_skill_cache_dir()).parent
    return base / "git-repo-cache" / "repos"


def resolve_managed_path(path_value: str, allowed_root: Path) -> Path | None:
    """Resolve path if it is within allowed_root; otherwise return None."""
    if not path_value:
        return None

    candidate = Path(path_value).expanduser().resolve(strict=False)
    root = allowed_root.expanduser().resolve(strict=False)
    if not candidate.is_relative_to(root):
        return None
    return candidate


def is_safe_removal_target(path: Path, allowed_root: Path) -> bool:
    """Return whether path is a non-root descendant of allowed_root."""
    root = allowed_root.expanduser().resolve(strict=False)
    candidate = path.expanduser().resolve(strict=False)
    return candidate != root and candidate.is_relative_to(root)


def run_cmd(
    cmd: list[str],
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with non-interactive pager settings."""
    env = dict(os.environ)
    env.setdefault("GH_PAGER", "cat")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("PAGER", "cat")
    if extra_env:
        env.update(extra_env)
    COMMAND_LOG.append(
        json.dumps(
            {
                "cmd": cmd,
                "cwd": str(cwd) if cwd else "",
                "ts_utc": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=True,
        )
    )
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env,
    )


def parse_pr_repo_url(pr_url: str) -> tuple[str, str, str, str]:
    """Parse PR URL and return (repo_url, host, owner, repo)."""
    match = re.match(r"^(https?://[^/]+)/(.+)/pull/(\d+)(?:/.*)?$", pr_url.strip())
    if not match:
        raise ValueError(f"Cannot parse repo URL from PR URL: {pr_url}")
    root = match.group(1)
    repo_path = match.group(2).strip("/")
    path_parts = repo_path.split("/")
    if len(path_parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from PR URL: {pr_url}")
    host = root.split("//", 1)[1]
    owner = "/".join(path_parts[:-1])
    repo = path_parts[-1]
    return f"{root}/{repo_path}", host, owner, repo


def parse_key_value_output(stdout_text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines from command output."""
    result: dict[str, str] = {}
    for line in stdout_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() and key.strip().isupper():
            result[key.strip()] = value.strip()
    return result


def locate_sibling_script(name: str) -> Path:
    """Locate a sibling script in the same directory as this file."""
    script = Path(__file__).resolve().parent / name
    if not script.exists():
        raise FileNotFoundError(f"{name} not found at {script}")
    return script


def current_repo_name_with_owner() -> str:
    """Return current repo nameWithOwner via gh, or empty if unavailable."""
    cp = run_cmd(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    )
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def current_repo_top_level() -> str:
    """Return current repo top-level path, or empty if unavailable."""
    cp = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def current_branch(repo_dir: Path) -> str:
    """Return current branch name in repo_dir, or empty when detached/unknown."""
    cp = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def query_repo_size_kb(host: str, owner: str, repo: str) -> int | None:
    """Query repo disk size (KB) via GitHub API. Returns None on failure."""
    api_args = ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".size"]
    if host != "github.com":
        api_args = [
            "gh",
            "api",
            "--hostname",
            host,
            f"repos/{owner}/{repo}",
            "--jq",
            ".size",
        ]
    cp = run_cmd(api_args)
    if cp.returncode != 0:
        return None
    try:
        return int(cp.stdout.strip())
    except (ValueError, TypeError):
        return None


def resolve_checkout_target(
    repo_dir: Path,
    base_ref_name: str,
    head_ref_name: str,
    pr_number: int,
) -> tuple[str, str]:
    """Resolve a deterministic checkout target after fetching PR refs.

    Returns:
        (target_ref, limitation)
        target_ref is `origin/<headRefName>` or a fetched commit SHA.
        Empty target_ref means checkout should fall back to diff-only mode.
    """
    errors: list[str] = []

    fetch_cp = run_cmd(
        ["git", "fetch", "origin", base_ref_name, head_ref_name],
        cwd=repo_dir,
    )
    if fetch_cp.returncode != 0:
        errors.append(
            fetch_cp.stderr.strip() or fetch_cp.stdout.strip() or "git fetch failed"
        )

    head_ref_check = run_cmd(
        ["git", "rev-parse", "--verify", "--quiet", f"origin/{head_ref_name}"],
        cwd=repo_dir,
    )
    if head_ref_check.returncode == 0:
        return f"origin/{head_ref_name}", ""

    fallback_fetch_cp = run_cmd(
        ["git", "fetch", "origin", f"pull/{pr_number}/head"],
        cwd=repo_dir,
    )
    if fallback_fetch_cp.returncode != 0:
        errors.append(
            fallback_fetch_cp.stderr.strip()
            or fallback_fetch_cp.stdout.strip()
            or "fallback fetch pull/<PR>/head failed"
        )
    else:
        fetch_head_cp = run_cmd(["git", "rev-parse", "FETCH_HEAD"], cwd=repo_dir)
        if fetch_head_cp.returncode == 0:
            return fetch_head_cp.stdout.strip(), ""
        errors.append(
            fetch_head_cp.stderr.strip()
            or fetch_head_cp.stdout.strip()
            or "cannot resolve FETCH_HEAD"
        )

    limitation = " | ".join(e for e in errors if e)
    limitation = limitation[:4000] if limitation else "Path checkout failed"
    return "", f"Path checkout failed: {limitation}"


def ensure_checkout(
    repo_dir: Path,
    base_ref_name: str,
    head_ref_name: str,
    pr_number: int,
) -> tuple[str, str]:
    """Try branch fetch/checkout; fallback to pull/<PR>/head when needed.

    Returns:
        (checkout_ref, limitation)
        checkout_ref is empty when checkout failed and diff-only mode is required.
        limitation contains an explanation when checkout_ref is empty.
    """
    target_ref, limitation = resolve_checkout_target(
        repo_dir,
        base_ref_name,
        head_ref_name,
        pr_number,
    )
    if not target_ref:
        return "", limitation

    checkout_cp = run_cmd(["git", "checkout", "--detach", target_ref], cwd=repo_dir)
    if checkout_cp.returncode == 0:
        return target_ref, ""

    err = (
        checkout_cp.stderr.strip()
        or checkout_cp.stdout.strip()
        or f"git checkout --detach {target_ref} failed"
    )
    return "", f"Path checkout failed: {err[:4000]}"


def _emit_manifest_outputs(manifest: SessionManifest, manifest_path: Path) -> None:
    """Print machine-readable KEY=VALUE lines for the caller."""
    print(f"RUN_MANIFEST={manifest_path}")
    print(f"PR_VIEW_JSON_PATH={manifest.pr_view_json_path}")
    print(f"PR_DIFF_PATH={manifest.pr_diff_path}")
    print(f"COMMAND_LOG_PATH={manifest.command_log_path}")
    print(f"CLEANUP_LOG_PATH={manifest.cleanup_log_path}")
    print(f"REVIEW_TEXT_PATH={manifest.review_text_path}")
    print(f"SELECTED_PATH={manifest.selected_path}")
    print(f"REPO_PATH={manifest.repo_path}")
    print(f"REPO_WORKDIR={manifest.repo_workdir}")
    print(f"PR_STATE={manifest.pr_state}")
    print(f"CONTEXT_MODE={manifest.context_mode}")
    print(f"CONTEXT_LIMITATION={manifest.context_limitation}")


def _execute_path_c(
    host: str,
    owner: str,
    repo: str,
    repo_url: str,
    base_ref_name: str,
    head_ref_name: str,
    pr_number: int,
) -> tuple[str, str, str, str, str]:
    """Execute Path C: clone into shared cache via repo_manager.py.

    Returns:
        (selected_path, repo_path, repo_workdir, checkout_ref, context_limitation)
        selected_path may be "D" if Path C fails and falls back.
    """
    repo_manager_script = locate_sibling_script("repo_manager.py")
    sync_cp = run_cmd(
        ["python3", str(repo_manager_script), "sync", repo_url],
    )
    synced_path = (
        sync_cp.stdout.strip().splitlines()[-1] if sync_cp.stdout.strip() else ""
    )
    if sync_cp.returncode != 0 or not synced_path or not Path(synced_path).is_dir():
        sync_err = (
            sync_cp.stderr.strip()
            or sync_cp.stdout.strip()
            or "repo_manager.py sync failed"
        )
        print(f"[PATH-FALLBACK] Path C failed ({sync_err}), falling back to Path D")
        return "D", "", "", "", ""
    checkout_ref, limitation = ensure_checkout(
        Path(synced_path),
        base_ref_name,
        head_ref_name,
        pr_number,
    )
    return "C", synced_path, synced_path, checkout_ref, limitation


def _execute_path_d(
    repo_url: str,
    cache_dir: Path,
    base_ref_name: str,
    head_ref_name: str,
    pr_number: int,
) -> tuple[str, str, str, str]:
    """Execute Path D: blobless sparse clone into a temp directory.

    Returns:
        (review_dir, repo_workdir, checkout_ref, context_limitation)
    """
    review_dir_path = Path(tempfile.mkdtemp(prefix="repo-", dir=str(cache_dir)))
    review_dir = str(review_dir_path)
    clone_cp = run_cmd(
        [
            "gh",
            "repo",
            "clone",
            repo_url,
            str(review_dir_path),
            "--",
            "--filter=blob:none",
            "--sparse",
        ]
    )
    if clone_cp.returncode != 0:
        limitation = (
            clone_cp.stderr.strip()
            or clone_cp.stdout.strip()
            or "Path D blobless sparse clone failed"
        )
        return review_dir, "", "", limitation
    checkout_ref, limitation = ensure_checkout(
        review_dir_path,
        base_ref_name,
        head_ref_name,
        pr_number,
    )
    return review_dir, str(review_dir_path), checkout_ref, limitation


def prepare_session(
    pr_ref: str,
    *,
    force_path: str | None = None,
    resume_run_dir: str | None = None,
) -> int:
    """Prepare a review session and emit machine-readable outputs.

    When resuming a pending decision (--force-path + --run-dir), the
    previously fetched metadata and diff are reused from run_dir without
    re-running ``gh pr view`` / ``gh pr diff``.
    """
    cache_dir = get_skill_cache_dir()

    # ── Resume path: reuse saved metadata/diff from a pending session ─────
    if resume_run_dir and force_path:
        return _resume_session(
            pr_ref,
            force_path,
            Path(resume_run_dir),
            cache_dir,
        )

    # ── Normal path: fresh session ────────────────────────────────────────
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=str(cache_dir)))

    pr_view_path = run_dir / "pr_view.json"
    pr_diff_path = run_dir / "pr.diff"
    command_log_path = run_dir / "commands.log"
    path_select_log_path = run_dir / "path_select.log"
    cleanup_log_path = run_dir / "cleanup.log"
    review_text_path = run_dir / "review_text.md"
    manifest_path = run_dir / "manifest.json"

    # Step 2: fetch metadata and diff exactly once.
    pr_view_cp = run_cmd(["gh", "pr", "view", pr_ref, "--json", PR_VIEW_FIELDS])
    if pr_view_cp.returncode != 0:
        print(pr_view_cp.stderr.strip() or pr_view_cp.stdout.strip())
        return 2
    pr_view_path.write_text(pr_view_cp.stdout, encoding="utf-8")

    pr_diff_cp = run_cmd(["gh", "pr", "diff", pr_ref])
    if pr_diff_cp.returncode != 0:
        print(pr_diff_cp.stderr.strip() or pr_diff_cp.stdout.strip())
        return 2
    pr_diff_path.write_text(pr_diff_cp.stdout, encoding="utf-8")

    try:
        metadata = json.loads(pr_view_cp.stdout)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse gh pr view JSON: {exc}")
        return 2

    pr_url = str(metadata.get("url", "")).strip()
    if not pr_url:
        print("Missing .url in gh pr view response")
        return 2

    try:
        repo_url, host, owner, repo = parse_pr_repo_url(pr_url)
    except ValueError as exc:
        print(str(exc))
        return 2

    current_repo = current_repo_name_with_owner()
    path_select_script = locate_sibling_script("path_select.py")
    path_select_cp = run_cmd(
        ["python3", str(path_select_script), repo_url, current_repo],
    )
    combined_path_output = (path_select_cp.stdout or "") + (path_select_cp.stderr or "")
    path_select_log_path.write_text(combined_path_output, encoding="utf-8")

    # Emit path selection trace lines directly (required by skill instructions).
    if combined_path_output:
        print(combined_path_output.rstrip())

    if path_select_cp.returncode != 0:
        return 2

    kv = parse_key_value_output(path_select_cp.stdout)
    selected_path = kv.get("SELECTED_PATH", "")
    repo_path = kv.get("REPO_PATH", "")
    if selected_path not in {"A", "B", "C", "D"}:
        print("Invalid SELECTED_PATH from path_select.py")
        return 2

    pr_number = int(metadata.get("number", 0) or 0)
    base_ref_name = str(metadata.get("baseRefName", "")).strip()
    head_ref_name = str(metadata.get("headRefName", "")).strip()
    pr_state = str(metadata.get("state", "")).strip()

    repo_workdir = ""
    original_branch = ""
    checkout_ref = ""
    context_mode = "full_repo"
    context_limitation = ""
    review_dir = ""

    if selected_path == "A":
        top_level = current_repo_top_level()
        if top_level:
            main_repo_dir = Path(top_level)
            repo_path = top_level
            original_branch = current_branch(main_repo_dir)

            target_ref, context_limitation = resolve_checkout_target(
                main_repo_dir,
                base_ref_name,
                head_ref_name,
                pr_number,
            )
            if target_ref:
                worktree_dir = Path(
                    tempfile.mkdtemp(prefix="worktree-", dir=str(cache_dir))
                )
                add_worktree_cp = run_cmd(
                    [
                        "git",
                        "worktree",
                        "add",
                        "--detach",
                        str(worktree_dir),
                        target_ref,
                    ],
                    cwd=main_repo_dir,
                )
                if add_worktree_cp.returncode == 0:
                    repo_workdir = str(worktree_dir)
                    review_dir = str(worktree_dir)
                    checkout_ref = target_ref
                    context_limitation = ""
                else:
                    context_limitation = (
                        add_worktree_cp.stderr.strip()
                        or add_worktree_cp.stdout.strip()
                        or "Path A temp worktree creation failed"
                    )[:4000]
        else:
            context_limitation = "Path A selected but current repo top-level not found"

    elif selected_path == "B":
        if repo_path:
            repo_workdir = repo_path
            checkout_ref, context_limitation = ensure_checkout(
                Path(repo_workdir),
                base_ref_name,
                head_ref_name,
                pr_number,
            )
        else:
            context_limitation = "Path B selected but REPO_PATH missing"

    elif selected_path == "C":
        threshold_mb = REPO_SIZE_THRESHOLD_KB // 1024
        repo_size_kb = query_repo_size_kb(host, owner, repo)
        size_mb: float = 0.0
        if repo_size_kb is not None:
            size_mb = repo_size_kb / 1024
            print(
                f"[PATH-SIZE] Repo disk size: {size_mb:.1f} MB "
                f"(threshold: {threshold_mb} MB)"
            )
        else:
            print("[PATH-SIZE] Repo disk size: unknown (API query failed)")

        if repo_size_kb is not None and repo_size_kb > REPO_SIZE_THRESHOLD_KB:
            # Repo exceeds threshold — pause and ask user to choose.
            size_mb = repo_size_kb / 1024
            print(
                f"[PATH-SIZE] {size_mb:.1f} MB > {threshold_mb} MB "
                "→ repo exceeds size threshold, user decision required"
            )

            # Save a pending-decision marker so the session can be resumed.
            pending = {
                "status": "pending_decision",
                "pr_ref": pr_ref,
                "pr_url": pr_url,
                "repo_url": repo_url,
                "host": host,
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "base_ref_name": base_ref_name,
                "head_ref_name": head_ref_name,
                "pr_state": pr_state,
                "repo_size_kb": repo_size_kb,
                "repo_size_mb": round(size_mb, 1),
                "threshold_mb": threshold_mb,
            }
            pending_path = run_dir / "pending_decision.json"
            pending_path.write_text(
                json.dumps(pending, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            command_log_path.write_text(
                "\n".join(COMMAND_LOG) + "\n",
                encoding="utf-8",
            )

            # Determine recommended default: sparse clone for ≤1 GB,
            # diff-only for monorepo-scale repos.
            recommended = "D" if size_mb <= 1024 else "diff-only"

            # Emit outputs so the agent knows the run_dir, size, and
            # recommended default option.
            print(f"NEEDS_USER_DECISION=true")
            print(f"REPO_SIZE_MB={size_mb:.1f}")
            print(f"THRESHOLD_MB={threshold_mb}")
            print(f"RECOMMENDED_DEFAULT={recommended}")
            print(f"PENDING_RUN_DIR={run_dir}")
            print(f"PR_VIEW_JSON_PATH={pr_view_path}")
            print(f"PR_DIFF_PATH={pr_diff_path}")
            return PENDING_DECISION_EXIT_CODE
        else:
            if repo_size_kb is None:
                print(
                    f"[PATH-SIZE] Defaulting to Path C "
                    f"(shared cache clone, threshold: {threshold_mb} MB)"
                )
            else:
                print(
                    f"[PATH-SIZE] {size_mb:.1f} MB ≤ {threshold_mb} MB "
                    "→ proceeding with Path C (shared cache clone)"
                )
            result = _execute_path_c(
                host,
                owner,
                repo,
                repo_url,
                base_ref_name,
                head_ref_name,
                pr_number,
            )
            selected_path = result[0]
            if selected_path == "C":
                repo_path = result[1]
                repo_workdir = result[2]
                checkout_ref = result[3]
                context_limitation = result[4]
            # If fell back to D, the block below handles it.

    if selected_path == "D":
        review_dir, repo_workdir, checkout_ref, context_limitation = _execute_path_d(
            repo_url,
            cache_dir,
            base_ref_name,
            head_ref_name,
            pr_number,
        )

    if not checkout_ref:
        context_mode = "diff_only"

    existing_log = ""
    if command_log_path.exists():
        existing_log = command_log_path.read_text(encoding="utf-8")
    new_lines = "\n".join(COMMAND_LOG)
    if new_lines:
        if existing_log and not existing_log.endswith("\n"):
            existing_log += "\n"
        existing_log += new_lines + "\n"
    command_log_path.write_text(existing_log, encoding="utf-8")

    manifest = SessionManifest(
        run_dir=str(run_dir),
        pr_ref=pr_ref,
        pr_url=pr_url,
        repo_url=repo_url,
        host=host,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        pr_state=pr_state,
        selected_path=selected_path,
        repo_path=repo_path,
        repo_workdir=repo_workdir,
        original_branch=original_branch,
        checkout_ref=checkout_ref,
        context_mode=context_mode,
        context_limitation=context_limitation,
        pr_view_json_path=str(pr_view_path),
        pr_diff_path=str(pr_diff_path),
        command_log_path=str(command_log_path),
        path_select_log_path=str(path_select_log_path),
        cleanup_log_path=str(cleanup_log_path),
        review_text_path=str(review_text_path),
        review_dir=review_dir,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    _emit_manifest_outputs(manifest, manifest_path)
    return 0


def _resume_session(
    pr_ref: str,
    force_path: str,
    run_dir: Path,
    cache_dir: Path,
) -> int:
    """Resume a pending-decision session with the user's chosen path.

    Reuses previously fetched metadata and diff from ``run_dir`` without
    re-running ``gh pr view`` / ``gh pr diff``.
    """
    pr_view_path = run_dir / "pr_view.json"
    pr_diff_path = run_dir / "pr.diff"
    command_log_path = run_dir / "commands.log"
    path_select_log_path = run_dir / "path_select.log"
    cleanup_log_path = run_dir / "cleanup.log"
    review_text_path = run_dir / "review_text.md"
    manifest_path = run_dir / "manifest.json"
    pending_path = run_dir / "pending_decision.json"

    if not pr_view_path.exists() or not pr_diff_path.exists():
        print(f"Cannot resume: missing pr_view.json or pr.diff in {run_dir}")
        return 2

    if not pending_path.exists():
        print(f"Cannot resume: missing pending_decision.json in {run_dir}")
        return 2

    try:
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Cannot resume: invalid pending_decision.json: {exc}")
        return 2

    repo_url = str(pending["repo_url"])
    host = str(pending["host"])
    owner = str(pending["owner"])
    repo = str(pending["repo"])
    pr_number = int(pending["pr_number"])
    pr_url = str(pending["pr_url"])
    base_ref_name = str(pending["base_ref_name"])
    head_ref_name = str(pending["head_ref_name"])
    pr_state = str(pending["pr_state"])

    repo_path = ""
    repo_workdir = ""
    checkout_ref = ""
    context_mode = "full_repo"
    context_limitation = ""
    review_dir = ""
    selected_path = force_path.upper() if force_path != "diff-only" else "D"

    if force_path == "diff-only":
        # User chose no clone — review with diff and metadata only.
        selected_path = "DIFF_ONLY"
        context_mode = "diff_only"
        context_limitation = "User chose diff-only mode (no repo clone)"
        print("[PATH-RESUME] User selected diff-only — skipping clone")

    elif force_path.upper() == "C":
        # User chose to clone into shared cache despite large size.
        print("[PATH-RESUME] User selected Path C (shared cache clone)")
        result = _execute_path_c(
            host,
            owner,
            repo,
            repo_url,
            base_ref_name,
            head_ref_name,
            pr_number,
        )
        selected_path = result[0]
        if selected_path == "C":
            repo_path = result[1]
            repo_workdir = result[2]
            checkout_ref = result[3]
            context_limitation = result[4]
        else:
            # Fell back to D
            review_dir, repo_workdir, checkout_ref, context_limitation = (
                _execute_path_d(
                    repo_url,
                    cache_dir,
                    base_ref_name,
                    head_ref_name,
                    pr_number,
                )
            )

    elif force_path.upper() == "D":
        # User chose sparse clone to temp dir.
        print("[PATH-RESUME] User selected Path D (sparse clone to temp dir)")
        selected_path = "D"
        review_dir, repo_workdir, checkout_ref, context_limitation = _execute_path_d(
            repo_url,
            cache_dir,
            base_ref_name,
            head_ref_name,
            pr_number,
        )

    else:
        print(f"Invalid --force-path value: {force_path}")
        return 2

    if not checkout_ref:
        context_mode = "diff_only"

    # Remove the pending marker now that the decision is made.
    pending_path.unlink(missing_ok=True)

    existing_log = ""
    if command_log_path.exists():
        existing_log = command_log_path.read_text(encoding="utf-8")
    new_lines = "\n".join(COMMAND_LOG)
    if new_lines:
        if existing_log and not existing_log.endswith("\n"):
            existing_log += "\n"
        existing_log += new_lines + "\n"
    command_log_path.write_text(existing_log, encoding="utf-8")

    manifest = SessionManifest(
        run_dir=str(run_dir),
        pr_ref=pr_ref,
        pr_url=pr_url,
        repo_url=repo_url,
        host=host,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        pr_state=pr_state,
        selected_path=selected_path,
        repo_path=repo_path,
        repo_workdir=repo_workdir,
        original_branch="",
        checkout_ref=checkout_ref,
        context_mode=context_mode,
        context_limitation=context_limitation,
        pr_view_json_path=str(pr_view_path),
        pr_diff_path=str(pr_diff_path),
        command_log_path=str(command_log_path),
        path_select_log_path=str(path_select_log_path),
        cleanup_log_path=str(cleanup_log_path),
        review_text_path=str(review_text_path),
        review_dir=review_dir,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    _emit_manifest_outputs(manifest, manifest_path)
    return 0


def resolve_default_branch(repo_path: Path) -> str:
    """Resolve remote default branch name for a local repo."""
    cp = run_cmd(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
        cwd=repo_path,
    )
    if cp.returncode != 0:
        return "main"
    value = cp.stdout.strip()
    return value.replace("origin/", "", 1) if value.startswith("origin/") else value


def cleanup_session(manifest_path: Path) -> int:
    """Restore repo state and print [PATH-CLEANUP] evidence.

    This does NOT delete the run_dir — the manifest and command log must
    remain readable so the gate script can validate them afterwards.
    Call ``purge`` after the gate passes to remove session artifacts.
    """
    if not manifest_path.exists():
        print(f"[PATH-CLEANUP] skipped - manifest not found: {manifest_path}")
        return 0

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[PATH-CLEANUP] skipped - invalid manifest JSON: {manifest_path}")
        return 0

    selected_path = str(data.get("selected_path", ""))
    repo_path = str(data.get("repo_path", ""))
    repo_workdir = str(data.get("repo_workdir", ""))
    original_branch = str(data.get("original_branch", ""))
    review_dir_raw = str(data.get("review_dir", "")).strip()
    review_dir = Path(review_dir_raw) if review_dir_raw else None
    skill_cache_dir = get_skill_cache_dir()
    shared_repo_root = get_shared_repo_cache_root(skill_cache_dir)
    had_failure = False

    def mark_fail(message: str) -> None:
        nonlocal had_failure
        had_failure = True
        print(f"[PATH-CLEANUP] {message}")

    def mark_ok(message: str) -> None:
        print(f"[PATH-CLEANUP] {message}")

    if selected_path == "A":
        if review_dir and repo_path and (Path(repo_path) / ".git").is_dir():
            if not resolve_managed_path(str(review_dir), skill_cache_dir):
                mark_fail("Path A - FAIL - temp worktree path is outside skill cache")
                return 1
            cp = run_cmd(
                ["git", "worktree", "remove", "--force", str(review_dir)],
                cwd=Path(repo_path),
            )
            if cp.returncode == 0:
                mark_ok(f"Path A - OK - removed temp worktree: {review_dir}")
            else:
                mark_fail(
                    "Path A - FAIL - failed to remove temp worktree: "
                    f"{cp.stderr.strip() or cp.stdout.strip()}"
                )
        elif repo_workdir and original_branch:
            cp = run_cmd(["git", "checkout", original_branch], cwd=Path(repo_workdir))
            if cp.returncode == 0:
                mark_ok(f"Path A - OK - restored branch to {original_branch}")
            else:
                mark_fail(
                    "Path A - FAIL - failed to restore branch: "
                    f"{cp.stderr.strip() or cp.stdout.strip()}"
                )
        else:
            mark_fail("Path A - FAIL - skipped (missing repo_workdir/original_branch)")

    elif selected_path in ("B", "C"):
        managed_repo_path = resolve_managed_path(repo_workdir, shared_repo_root)
        if managed_repo_path and (managed_repo_path / ".git").is_dir():
            repo_dir = managed_repo_path
            default_branch = resolve_default_branch(repo_dir)
            checkout_cp = run_cmd(["git", "checkout", default_branch], cwd=repo_dir)
            reset_cp = run_cmd(
                ["git", "reset", "--hard", f"origin/{default_branch}"], cwd=repo_dir
            )
            clean_cp = run_cmd(["git", "clean", "-fd"], cwd=repo_dir)

            if (
                checkout_cp.returncode == 0
                and reset_cp.returncode == 0
                and clean_cp.returncode == 0
            ):
                mark_ok(
                    f"Path {selected_path} - OK - reset cached repo to "
                    f"{default_branch}, ready for next use"
                )
            else:
                failure_parts = []
                for label, cp in (
                    ("checkout", checkout_cp),
                    ("reset", reset_cp),
                    ("clean", clean_cp),
                ):
                    if cp.returncode != 0:
                        failure_parts.append(
                            f"{label}: {cp.stderr.strip() or cp.stdout.strip()}"
                        )
                mark_fail(f"Path {selected_path} - FAIL - " + " | ".join(failure_parts))
        else:
            mark_fail(
                f"Path {selected_path} - FAIL - unsafe or missing repo_workdir: "
                f"{repo_workdir or '<empty>'}"
            )

    elif selected_path == "D":
        removed: list[str] = []
        for path in [review_dir]:
            if not path:
                continue
            if not is_safe_removal_target(path, skill_cache_dir):
                mark_fail(
                    "Path D - FAIL - unsafe temp directory path outside skill cache: "
                    f"{path}"
                )
                continue
            if path.exists():
                try:
                    shutil.rmtree(path, ignore_errors=False)
                    removed.append(str(path))
                except OSError as exc:
                    mark_fail(
                        f"Path D - FAIL - failed to delete temp dir {path}: {exc}"
                    )
        if removed:
            mark_ok(f"Path D - OK - deleted temp dirs: {' '.join(removed)}")
        else:
            if not had_failure:
                mark_ok("Path D - OK - no temp dirs to delete")

    elif selected_path == "DIFF_ONLY":
        mark_ok("DIFF_ONLY - OK - no repo to clean up")

    else:
        mark_fail("FAIL - unknown SELECTED_PATH")

    return 1 if had_failure else 0


def purge_session(manifest_path: Path) -> int:
    """Delete run_dir session artifacts after the gate has passed."""
    if not manifest_path.exists():
        print(f"[PURGE] skipped - manifest not found: {manifest_path}")
        return 0

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[PURGE] skipped - invalid manifest JSON: {manifest_path}")
        return 0

    skill_cache_dir = get_skill_cache_dir()
    run_dir = Path(str(data.get("run_dir", "")))
    managed_run_dir = resolve_managed_path(str(run_dir), skill_cache_dir)
    if not managed_run_dir or not is_safe_removal_target(
        managed_run_dir, skill_cache_dir
    ):
        print(f"[PURGE] FAIL - unsafe run_dir outside skill cache: {run_dir}")
        return 1

    run_dir = managed_run_dir
    if run_dir.exists() and run_dir.is_dir():
        try:
            shutil.rmtree(run_dir, ignore_errors=False)
            print(f"[PURGE] Session artifacts removed: {run_dir}")
        except OSError as exc:
            print(f"[PURGE] FAIL - unable to remove run_dir {run_dir}: {exc}")
            return 1
    else:
        print("[PURGE] skipped - run_dir not found or already removed")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for prepare/cleanup/purge subcommands."""
    parser = argparse.ArgumentParser(description="Guarded PR review runner")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare_parser = sub.add_parser("prepare", help="Prepare review session")
    prepare_parser.add_argument("pr_ref", help="PR URL or PR number")
    prepare_parser.add_argument(
        "--force-path",
        choices=["C", "D", "diff-only"],
        default=None,
        help="Force a specific path when resuming after a pending decision",
    )
    prepare_parser.add_argument(
        "--run-dir",
        default=None,
        help="Resume a pending session using this run directory",
    )

    cleanup_parser = sub.add_parser("cleanup", help="Cleanup review session")
    cleanup_parser.add_argument("manifest_path", help="Path to session manifest.json")

    purge_parser = sub.add_parser("purge", help="Delete session artifacts after gate")
    purge_parser.add_argument("manifest_path", help="Path to session manifest.json")
    return parser


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "prepare":
        raise SystemExit(
            prepare_session(
                args.pr_ref,
                force_path=args.force_path,
                resume_run_dir=args.run_dir,
            )
        )
    if args.command == "cleanup":
        raise SystemExit(cleanup_session(Path(args.manifest_path)))
    raise SystemExit(purge_session(Path(args.manifest_path)))


if __name__ == "__main__":
    main()
