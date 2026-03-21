#!/usr/bin/env python3
"""Select the local repo access path (A / B / C / D) for a PR review.

Checks paths in order:
  A — already inside the target repo (cwd matches the PR repo)
  B — repo found in shared git-repo-reader cache
  C — no local access; caller will clone into shared cache via repo_manager.py
  D — fallback if Path C clone fails; caller does blobless sparse-clone
      into the skill's own temp cache

Prints one [PATH-CHECK] line per path and a final [PATH-SELECTED] line,
then prints machine-readable key-value lines for the caller:

    SELECTED_PATH=A|B|C|D
    REPO_PATH=<absolute-path-or-empty>

Exit codes:
    0 — always (path selection always produces a result)

Usage:
    python3 scripts/path_select.py <repo-url> [<current-repo-nameWithOwner>] [<current-origin-url>]

    <repo-url>                   Full repo URL, e.g.
                                 https://git.example.com/owner/repo
    <current-repo-nameWithOwner> Optional: output of
                                 `gh repo view --json nameWithOwner -q .nameWithOwner`
                                 Pass empty string "" if unavailable.
    <current-origin-url>         Optional: output of `git remote get-url origin`
                                 Pass empty string "" if unavailable.

Output (to stdout):
    [PATH-CHECK] A: HIT|MISS - <reason>
    [PATH-CHECK] B: HIT|MISS - <reason>
    [PATH-CHECK] C: SELECTED|SKIPPED - <reason>
    [PATH-CHECK] D: SELECTED|SKIPPED - <reason>
    [PATH-SELECTED] Path A|B|C|D
    SELECTED_PATH=A|B|C|D
    REPO_PATH=<absolute-path>          # only for Path B; empty for A, C, and D

Uses only Python 3.10+ standard library (zero dependencies).
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path


# ── cache helpers (mirrors repo_cache_lookup.py) ──────────────────────────────


def get_cache_root() -> Path:
    """Return the shared repo cache root under per-user cache."""
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        base = home / "Library" / "Caches"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else home / ".cache"
    return base / "mythril-skills-cache" / "git-repo-cache"


def parse_repo_url(url: str) -> tuple[str, str, str]:
    """Parse a git URL into (host, owner, repo)."""
    url = url.strip()
    ssh = re.match(r"^git@([^:]+):(.+?)(?:\.git)?$", url)
    if ssh:
        host = ssh.group(1)
        parts = ssh.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]
    ssh_url = re.match(r"^ssh://(?:.+@)?([^/]+)/(.+?)(?:\.git)?/?$", url)
    if ssh_url:
        host = ssh_url.group(1)
        parts = ssh_url.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]
    https = re.match(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$", url)
    if https:
        host = https.group(1)
        parts = https.group(2).strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        return host, "/".join(parts[:-1]), parts[-1]
    raise ValueError(f"Unrecognized git URL format: {url}")


def normalized_identity(host: str, owner: str, repo: str) -> tuple[str, str, str]:
    """Normalize repo identity for comparison."""
    return host.lower(), owner.lower(), repo.lower()


def detect_current_origin_url() -> str:
    """Return current repo origin URL, or empty when unavailable."""
    cp = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def detect_inside_git_repo() -> bool:
    """Return whether current working directory is inside a git repo."""
    cp = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return cp.returncode == 0 and cp.stdout.strip().lower() == "true"


def resolve_repo_full_name_via_gh(host: str, owner: str, repo: str) -> str:
    """Resolve canonical owner/repo via gh api, or return empty on failure."""
    cmd = ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".full_name"]
    if host != "github.com":
        cmd = [
            "gh",
            "api",
            "--hostname",
            host,
            f"repos/{owner}/{repo}",
            "--jq",
            ".full_name",
        ]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def resolve_repo_id_via_gh(host: str, owner: str, repo: str) -> str:
    """Resolve repository numeric ID via gh api, or return empty on failure."""
    cmd = ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".id"]
    if host != "github.com":
        cmd = [
            "gh",
            "api",
            "--hostname",
            host,
            f"repos/{owner}/{repo}",
            "--jq",
            ".id",
        ]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def cache_lookup(repo_url: str) -> str | None:
    """Return local path if repo is in shared cache, else None."""
    try:
        host, owner, repo = parse_repo_url(repo_url)
    except ValueError:
        return None
    key = f"{host}/{owner}/{repo}"
    map_path = get_cache_root() / "repo_map.json"
    if not map_path.exists():
        return None
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    path_str = data.get(key) if isinstance(data, dict) else None
    if not path_str:
        return None
    local = Path(path_str)
    if not local.exists() or not (local / ".git").is_dir():
        return None
    return str(local)


# ── main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: path_select.py <repo-url> [<current-repo-nameWithOwner>]",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_url = sys.argv[1].strip()
    current_repo = sys.argv[2].strip() if len(sys.argv) >= 3 else ""
    current_origin_url = sys.argv[3].strip() if len(sys.argv) >= 4 else ""

    # Derive owner/repo from URL for Path A comparison
    try:
        host, owner, repo_name = parse_repo_url(repo_url)
        target_name_with_owner = f"{owner}/{repo_name}"
        target_identity = normalized_identity(host, owner, repo_name)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Path A ────────────────────────────────────────────────────────────────
    if not current_origin_url:
        current_origin_url = detect_current_origin_url()

    path_a_hit = False
    path_a_reason = ""

    if current_origin_url:
        try:
            current_host, current_owner, current_repo_name = parse_repo_url(
                current_origin_url
            )
            current_identity = normalized_identity(
                current_host,
                current_owner,
                current_repo_name,
            )
            if current_identity == target_identity:
                path_a_hit = True
                path_a_reason = (
                    "cwd origin remote matches target "
                    f"({current_host}/{current_owner}/{current_repo_name})"
                )
            elif (
                current_host.lower() == host.lower()
                and current_owner.lower() == owner.lower()
            ):
                current_id = resolve_repo_id_via_gh(
                    current_host,
                    current_owner,
                    current_repo_name,
                )
                target_id = resolve_repo_id_via_gh(host, owner, repo_name)
                if current_id and target_id and current_id == target_id:
                    path_a_hit = True
                    path_a_reason = (
                        "cwd origin remote and target resolve to same repo ID via gh api "
                        f"(id={current_id})"
                    )
                    resolved_full_name = ""
                else:
                    resolved_full_name = resolve_repo_full_name_via_gh(
                        current_host,
                        current_owner,
                        current_repo_name,
                    )
                if (not path_a_hit) and (
                    resolved_full_name.lower() == target_name_with_owner.lower()
                ):
                    path_a_hit = True
                    path_a_reason = (
                        "cwd origin remote maps to target repo via gh api "
                        f"({current_host}/{resolved_full_name})"
                    )
                elif not path_a_hit:
                    path_a_reason = (
                        "cwd origin remote is "
                        f"'{current_host}/{current_owner}/{current_repo_name}', "
                        f"not '{host}/{owner}/{repo_name}'"
                    )
            else:
                path_a_reason = (
                    "cwd origin remote is "
                    f"'{current_host}/{current_owner}/{current_repo_name}', "
                    f"not '{host}/{owner}/{repo_name}'"
                )
        except ValueError:
            path_a_reason = (
                f"failed to parse cwd origin remote URL '{current_origin_url}'"
            )

    if not path_a_hit and current_repo:
        if current_repo.lower() == target_name_with_owner.lower():
            path_a_hit = True
            if path_a_reason:
                path_a_reason = (
                    "cwd repo identity matches target via gh "
                    f"({target_name_with_owner}); origin differs "
                    f"({path_a_reason})"
                )
            else:
                path_a_reason = (
                    "cwd owner/repo matches target "
                    f"({target_name_with_owner}); host not verifiable"
                )
        elif not path_a_reason:
            path_a_reason = (
                f"cwd repo is '{current_repo}', not '{target_name_with_owner}'"
            )

    if path_a_hit:
        print(f"[PATH-CHECK] A: HIT - {path_a_reason}")
        print("[PATH-CHECK] B: SKIPPED - Path A matched")
        print("[PATH-CHECK] C: SKIPPED - Path A matched")
        print("[PATH-CHECK] D: SKIPPED - Path A matched")
        print("[PATH-SELECTED] Path A")
        print("SELECTED_PATH=A")
        print("REPO_PATH=")
        return

    if path_a_reason:
        print(f"[PATH-CHECK] A: MISS - {path_a_reason}")
    elif detect_inside_git_repo():
        print(
            "[PATH-CHECK] A: MISS - inside a git repo but origin remote is unavailable"
        )
    else:
        print("[PATH-CHECK] A: MISS - not inside any git repo")

    # ── Path B ────────────────────────────────────────────────────────────────
    cached_path = cache_lookup(repo_url)
    if cached_path:
        print(f"[PATH-CHECK] B: HIT - cached at {cached_path}")
        print("[PATH-CHECK] C: SKIPPED - Path B matched")
        print("[PATH-CHECK] D: SKIPPED - Path B matched")
        print("[PATH-SELECTED] Path B")
        print("SELECTED_PATH=B")
        print(f"REPO_PATH={cached_path}")
        return

    print("[PATH-CHECK] B: MISS - repo not found in shared git-repo-cache")

    # ── Path C ────────────────────────────────────────────────────────────────
    # Clone to shared git-repo-cache via repo_manager.py sync (reusable across
    # sessions and skills). Path D is the fallback if C fails at runtime.
    cache_root = get_cache_root()
    shared_cache_dir = cache_root / "repos" / host / owner / repo_name

    print(
        f"[PATH-CHECK] C: SELECTED - will clone into shared cache at {shared_cache_dir}"
    )
    print("[PATH-CHECK] D: SKIPPED - Path C selected (D is fallback if C fails)")
    print("[PATH-SELECTED] Path C")
    print("SELECTED_PATH=C")
    print("REPO_PATH=")


if __name__ == "__main__":
    main()
