#!/usr/bin/env python3
"""Jenkins REST API client for CI/CD workflows.

Required environment variables:
  JENKINS_URL        — e.g. https://ci.example.com:8443 (context path allowed)
  JENKINS_USER       — Jenkins username
  JENKINS_API_TOKEN  — Jenkins API token (user -> Security -> API Token)

Uses only Python 3.10+ standard library (zero dependencies).
"""

import os, sys, json, time, argparse, base64, ssl
import urllib.request
import urllib.error
from urllib.parse import urlencode, quote


TOKEN_URL = "https://www.jenkins.io/doc/book/managing/security/#api-tokens"

TOKEN_HELP = f"""\
ERROR: Jenkins environment not fully configured.

Required environment variables:
  JENKINS_URL        — e.g. https://ci.example.com:8443 (context path allowed)
  JENKINS_USER       — Jenkins username
  JENKINS_API_TOKEN  — Jenkins API token

Add to your shell config (~/.zshrc, ~/.bashrc, etc.):
  export JENKINS_URL="https://ci.example.com:8443"
  export JENKINS_USER="your-username"
  export JENKINS_API_TOKEN="your-api-token"

Create an API token in the Jenkins UI:
  1. Open your Jenkins, click your username (top right) -> Security
  2. Under "API Token" click "Add new Token" -> Generate
  3. Copy the token — it is shown only once

Official docs: {TOKEN_URL}
"""

POLL_INTERVAL = 3  # seconds between queue/build status polls

# Exit codes by final build result (build --wait). Other errors use 1/2.
RESULT_EXIT_CODES = {
    "SUCCESS": 0,
    "FAILURE": 1,
    "UNSTABLE": 2,
    "ABORTED": 3,
    "NOT_BUILT": 4,
}

# Jenkins job color -> human readable status ("_anime" suffix means running)
COLOR_STATUS = {
    "blue": "SUCCESS",
    "red": "FAILURE",
    "yellow": "UNSTABLE",
    "aborted": "ABORTED",
    "notbuilt": "NOT BUILT",
    "disabled": "DISABLED",
}


class ApiError(Exception):
    """HTTP error from the Jenkins REST API."""

    def __init__(self, code: int, body: str):
        super().__init__(f"HTTP {code}: {body[:200]}")
        self.code = code
        self.body = body


def _create_ssl_context() -> ssl.SSLContext | None:
    """Build an SSL context respecting enterprise network configuration.

    Checks these environment variables (in precedence order):
      SSL_NO_VERIFY=1          — disable certificate verification entirely
      SSL_CERT_FILE=<path>     — custom CA bundle path
      CURL_CA_BUNDLE=<path>    — same as SSL_CERT_FILE (curl convention)
      REQUESTS_CA_BUNDLE=<path> — same as SSL_CERT_FILE (requests convention)

    Returns None to use the default OS trust store.
    """
    if os.environ.get("SSL_NO_VERIFY", "").strip() == "1":
        return ssl._create_unverified_context()
    cert_file = (
        os.environ.get("SSL_CERT_FILE", "")
        or os.environ.get("CURL_CA_BUNDLE", "")
        or os.environ.get("REQUESTS_CA_BUNDLE", "")
    ).strip()
    if cert_file:
        return ssl.create_default_context(cafile=cert_file)
    return None


def get_env() -> tuple[str, str, str]:
    """Return (base_url, user, token) from the environment. Exits if any is missing."""
    missing = [
        name
        for name, val in (
            ("JENKINS_URL", os.environ.get("JENKINS_URL", "").strip()),
            ("JENKINS_USER", os.environ.get("JENKINS_USER", "").strip()),
            ("JENKINS_API_TOKEN", os.environ.get("JENKINS_API_TOKEN", "").strip()),
        )
        if not val
    ]
    if missing:
        print(f"ERROR: Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        print("", file=sys.stderr)
        print(TOKEN_HELP, file=sys.stderr)
        sys.exit(1)
    return (
        os.environ["JENKINS_URL"].strip().rstrip("/"),
        os.environ["JENKINS_USER"].strip(),
        os.environ["JENKINS_API_TOKEN"].strip(),
    )


def job_path(job: str) -> str:
    """Convert a job name to a Jenkins URL path.

    "deploy"      -> /job/deploy
    "team/deploy" -> /job/team/job/deploy   (folder nesting)
    Segments are percent-encoded; empty or "." / ".." segments are rejected.
    """
    segments = [s.strip() for s in job.strip().split("/") if s.strip()]
    if not segments:
        print("ERROR: Empty job name.", file=sys.stderr)
        sys.exit(2)
    for seg in segments:
        if seg in (".", ".."):
            print(f"ERROR: Invalid job path segment: {seg!r}", file=sys.stderr)
            sys.exit(2)
    return "".join("/job/" + quote(seg, safe="") for seg in segments)


def build_url_path(job: str, build: str | int | None) -> str:
    """Append a build number (or 'lastBuild') to a job path."""
    return f"{job_path(job)}/{build if build is not None else 'lastBuild'}"


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

def _request(
    method: str,
    url: str,
    data: bytes | None = None,
    form: dict | None = None,
    extra_headers: dict | None = None,
    timeout: int = 30,
) -> tuple[int, dict, bytes]:
    """Authenticated request. Returns (status, headers, body_bytes).

    Raises ApiError on HTTP >= 400; exits on network-level failures.
    """
    base_url, user, token = get_env()
    if form:
        data = urlencode(form).encode()
    req = urllib.request.Request(url, data=data, method=method)
    cred = base64.b64encode(f"{user}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {cred}")
    req.add_header("Accept", "application/json")
    if form:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    elif data:
        req.add_header("Content-Type", "application/json")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)

    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        raise ApiError(e.code, e.read().decode(errors="replace")) from None
    except ssl.SSLError as e:
        print(f"ERROR: TLS verification failed: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("If your Jenkins uses a private CA, set one of:", file=sys.stderr)
        print('  export SSL_CERT_FILE="/path/to/ca-bundle.pem"', file=sys.stderr)
        print("  (also accepted: CURL_CA_BUNDLE, REQUESTS_CA_BUNDLE)", file=sys.stderr)
        print("Last resort only: export SSL_NO_VERIFY=1", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _crumb_and_cookie(base_url: str) -> tuple[str, str, dict]:
    """Fetch a CSRF crumb for POST fallback (API tokens bypass this on Jenkins 2.96+;
    kept for instances where the token exemption is disabled or a password is used)."""
    status, headers, body = _request("GET", f"{base_url}/crumbIssuer/api/json")
    data = json.loads(body)
    cookie_header = headers.get("Set-Cookie", "")
    return data["crumbRequestField"], data["crumb"], ({"Cookie": cookie_header} if cookie_header else {})


def _post_action(base_url: str, path: str, form: dict | None = None) -> tuple[int, dict]:
    """POST an action endpoint, retrying once with a CSRF crumb on 403.

    Returns (status, response_headers).
    """
    url = f"{base_url}{path}"
    try:
        status, headers, _ = _request("POST", url, form=form)
        return status, headers
    except ApiError as e:
        if e.code != 403:
            print(f"ERROR: Jenkins API {e.code} POST {path}: {e.body}", file=sys.stderr)
            sys.exit(1)
    field, crumb, cookie = _crumb_and_cookie(base_url)
    try:
        status, headers, _ = _request("POST", url, form=form, extra_headers={field: crumb, **cookie})
        return status, headers
    except ApiError as e:
        print(f"ERROR: Jenkins API {e.code} POST {path}: {e.body}", file=sys.stderr)
        sys.exit(1)


def api_get_json(path: str, params: dict | None = None) -> dict:
    """GET a JSON endpoint. Path may be absolute ("/queue/item/5") or job-relative."""
    base_url, _, _ = get_env()
    url = f"{base_url}{path}"
    if params:
        url += "?" + urlencode(params)
    try:
        status, _, body = _request("GET", url)
        return json.loads(body)
    except ApiError as e:
        print(f"ERROR: Jenkins API {e.code} GET {path}: {e.body}", file=sys.stderr)
        sys.exit(1)


def api_get_json_or_none(path: str, params: dict | None = None) -> dict | None:
    """GET a JSON endpoint, returning None on 404 (e.g. queue item already executed)."""
    base_url, _, _ = get_env()
    url = f"{base_url}{path}"
    if params:
        url += "?" + urlencode(params)
    try:
        status, _, body = _request("GET", url)
        return json.loads(body)
    except ApiError as e:
        if e.code == 404:
            return None
        print(f"ERROR: Jenkins API {e.code} GET {path}: {e.body}", file=sys.stderr)
        sys.exit(1)


def progressive_text(job_build_path: str, start: int) -> tuple[str, bool, int]:
    """Read console log text from an offset.

    Returns (text, more_data, new_offset). Uses the progressiveText endpoint's
    X-Text-Size / X-More-Data headers for incremental log reading.
    """
    base_url, _, _ = get_env()
    url = f"{base_url}{job_build_path}/logText/progressiveText"
    if start:
        url += f"?start={start}"
    status, headers, body = _request("GET", url)
    offset = int(headers.get("X-Text-Size", "0") or "0")
    more = headers.get("X-More-Data", "false").lower() == "true"
    return body.decode(errors="replace"), more, offset


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_duration(ms: int | None) -> str:
    """Humanize a millisecond duration, e.g. '3m 24s'."""
    if ms is None:
        return "-"
    seconds = int(ms // 1000)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, min = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {min:02d}m"
    days, hr = divmod(hours, 24)
    return f"{days}d {hr}h"


def format_timestamp(epoch_ms: int | None) -> str:
    """Format a Jenkins epoch-millisecond timestamp as 'YYYY-MM-DD HH:MM:SS'."""
    if not epoch_ms:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch_ms / 1000))


def color_to_status(color: str | None) -> str:
    """Map a Jenkins job color to a readable status ('_anime' suffix = running)."""
    if not color:
        return "NEVER BUILT"
    running = color.endswith("_anime")
    base = color[:-6] if running else color
    status = COLOR_STATUS.get(base, base.upper())
    return f"{status} (running)" if running else status


def format_jobs_markdown(data: dict, folder: str | None) -> str:
    """Format the jobs list as a markdown table."""
    jobs = data.get("jobs", [])
    label = f" in {folder}" if folder else ""
    noun = "job" if len(jobs) == 1 else "jobs"
    lines = [f"## Jenkins Jobs{label} ({len(jobs)} {noun})"]
    lines.append("")
    if not jobs:
        lines.append("No jobs found.")
        return "\n".join(lines)
    lines.append("| Job | Status | Last Build |")
    lines.append("|-----|--------|------------|")
    for j in jobs:
        name = j.get("name", "")
        status = color_to_status(j.get("color"))
        last = j.get("lastBuild") or {}
        last_str = f"#{last.get('number')}" if last else "-"
        if last and last.get("result"):
            last_str = f"#{last['number']} {last['result']}"
        elif last:
            last_str = f"#{last['number']} (running)"
        lines.append(f"| {name} | {status} | {last_str} |")
    return "\n".join(lines)


def format_job_markdown(info: dict) -> str:
    """Format a single job's details as markdown."""
    lines = [f"## {info.get('displayName') or info.get('name', '?')}"]
    lines.append("")
    if info.get("description"):
        lines.append(f"{info['description']}")
        lines.append("")
    lines.append(f"- **Status**: {color_to_status(info.get('color'))}")
    lines.append(f"- **In Queue**: {'yes' if info.get('inQueue') else 'no'}")
    if info.get("url"):
        lines.append(f"- **URL**: {info['url']}")

    for health in info.get("healthReport", [])[:1]:
        score = health.get("score")
        desc = health.get("description", "")
        if score is not None:
            lines.append(f"- **Health**: {score}/100 — {desc}")

    last = info.get("lastBuild") or {}
    if last:
        state = "running" if not last.get("result") else last["result"]
        lines.append(f"- **Last Build**: #{last.get('number')} — {state}")
    if info.get("lastSuccessfulBuild"):
        lines.append(f"- **Last Successful**: #{info['lastSuccessfulBuild'].get('number')}")
    if info.get("lastFailedBuild"):
        lines.append(f"- **Last Failed**: #{info['lastFailedBuild'].get('number')}")

    params = []
    for prop in info.get("property", []):
        if prop.get("parameterDefinitions"):
            params = prop["parameterDefinitions"]
    if params:
        lines.append("")
        lines.append("### Parameters")
        lines.append("")
        lines.append("| Name | Type | Default | Description |")
        lines.append("|------|------|---------|-------------|")
        for p in params:
            default = (p.get("defaultParameterValue") or {}).get("value", "")
            default = "-" if default == "" else str(default)
            desc = (p.get("description") or "-").strip() or "-"
            lines.append(f"| {p.get('name', '')} | {p.get('type', '')} | {default} | {desc} |")

    return "\n".join(lines)


def format_build_markdown(build: dict, job: str | None = None) -> str:
    """Format a build's status as markdown."""
    number = build.get("number", "?")
    name = job or build.get("fullDisplayName", "")
    building = build.get("building", False)
    result = build.get("result") or "IN PROGRESS"
    title = f"Build #{number} — {result}"
    lines = [f"## {name} {title}".replace("  ", " ")]
    lines.append("")
    lines.append(f"- **Status**: {'BUILDING' if building else result}")
    lines.append(f"- **Started**: {format_timestamp(build.get('timestamp'))}")
    duration = build.get("duration")
    if duration:
        lines.append(f"- **Duration**: {format_duration(duration)}")
    if build.get("url"):
        lines.append(f"- **URL**: {build['url']}")

    for action in build.get("actions", []):
        if action.get("parameters"):
            lines.append("- **Parameters**:")
            for p in action["parameters"]:
                value = p.get("value", "")
                lines.append(f"  - {p.get('name')} = {value}")
    return "\n".join(lines)


def format_stages_markdown(data: dict, job: str, build: str | int) -> str:
    """Format pipeline stage progress (wfapi) as a markdown table."""
    stages = data.get("stages", [])
    lines = [f"## Pipeline Stages — {job} #{build}"]
    lines.append("")
    if not stages:
        lines.append("No stages returned. This may not be a Pipeline (workflow) job.")
        return "\n".join(lines)
    lines.append("| # | Stage | Status | Duration |")
    lines.append("|---|-------|--------|----------|")
    for i, s in enumerate(stages, 1):
        status = s.get("status", "")
        if status == "IN_PROGRESS":
            status = "IN PROGRESS"
        lines.append(
            f"| {i} | {s.get('name', '')} | {status} | {format_duration(s.get('durationMillis'))} |"
        )
    return "\n".join(lines)


def parse_params(pairs: list[str] | None) -> dict:
    """Parse repeated '--param name=value' arguments into a dict."""
    params: dict = {}
    for pair in pairs or []:
        if "=" not in pair:
            print(f"ERROR: --param expects name=value, got: {pair}", file=sys.stderr)
            sys.exit(2)
        name, value = pair.split("=", 1)
        params[name] = value
    return params


def parameter_names(info: dict) -> list[str]:
    """Extract parameter names from a job's api/json property list.

    Matches on the presence of the parameterDefinitions field rather than the
    property class name, which varies across Jenkins versions.
    """
    names = []
    for prop in info.get("property", []):
        if prop.get("parameterDefinitions"):
            names = [p.get("name", "") for p in prop["parameterDefinitions"]]
    return names


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_whoami(args: argparse.Namespace) -> None:
    """Verify connectivity and authentication."""
    base_url, _, _ = get_env()
    data = api_get_json("/whoAmI/api/json")
    name = data.get("name", "?")
    authed = data.get("authenticated", False)
    print(f"Authenticated: {'yes' if authed else 'NO'}")
    print(f"User: {name}")
    print(f"URL: {base_url}")
    if not authed:
        sys.exit(1)


def cmd_jobs(args: argparse.Namespace) -> None:
    """List jobs (optionally inside a folder)."""
    path = job_path(args.folder) if args.folder else ""
    data = api_get_json(f"{path}/api/json", params={
        "tree": "jobs[name,color,url,lastBuild[number,result]]{0,200}",
    })
    jobs = data.get("jobs", [])
    print(format_jobs_markdown(data, args.folder))
    if len(jobs) >= 200:
        print("", "(list truncated at 200 — use a folder argument to narrow)", file=sys.stderr)


def cmd_job(args: argparse.Namespace) -> None:
    """Show a job's details: status, health, last builds, parameters."""
    data = api_get_json(f"{job_path(args.job)}/api/json", params={
        "tree": (
            "displayName,description,color,url,inQueue,"
            "lastBuild[number,result,timestamp],"
            "lastSuccessfulBuild[number],lastFailedBuild[number],"
            "healthReport[score,description],"
            "property[parameterDefinitions[name,type,description,"
            "defaultParameterValue[value],choices]]"
        ),
    })
    print(format_job_markdown(data))


def cmd_build(args: argparse.Namespace) -> None:
    """Trigger a build, optionally waiting for it to finish."""
    base_url, _, _ = get_env()
    params = parse_params(args.param)
    info = api_get_json(f"{job_path(args.job)}/api/json", params={
        "tree": "property[parameterDefinitions[name]]",
    })
    defined = parameter_names(info)

    unknown = sorted(set(params) - set(defined)) if defined else sorted(set(params))
    if defined and unknown:
        print(f"ERROR: Unknown parameter(s) for {args.job}: {', '.join(unknown)}", file=sys.stderr)
        print(f"Defined parameters: {', '.join(defined)}", file=sys.stderr)
        sys.exit(2)
    if params and not defined:
        print(f"ERROR: Job {args.job} is not parameterized but --param was given.", file=sys.stderr)
        sys.exit(2)

    endpoint = "/buildWithParameters" if defined else "/build"
    status, headers = _post_action(base_url, f"{job_path(args.job)}{endpoint}", form=params if defined else None)
    if status not in (200, 201):
        print(f"ERROR: Unexpected status {status} triggering {args.job}.", file=sys.stderr)
        sys.exit(1)

    queue_url = headers.get("Location", "")
    print(f"Triggered {args.job}{f' with {len(params)} parameter(s)' if params else ''}")
    if not args.wait:
        if queue_url:
            print(f"Queue: {queue_url}api/json")
        print(f"Poll with: status {args.job}")
        return

    # --wait: poll queue until the build starts, then poll until it finishes
    deadline = time.time() + args.wait
    build_number = None
    queue_path = ""
    if queue_url:
        m = queue_url.rstrip("/").rsplit("/item/", 1)
        if len(m) == 2:
            queue_path = f"/queue/item/{m[1]}"
    while time.time() < deadline:
        if queue_path:
            q = api_get_json_or_none(f"{queue_path}/api/json")
            if q is None:
                # Item left the queue (started or cancelled) — check below.
                break
            if q.get("cancelled"):
                print(f"Build was cancelled while queued (why: {q.get('why', '-')}).")
                sys.exit(3)
            exe = q.get("executable")
            if exe:
                build_number = exe.get("number")
                break
            print(f"  queued ({q.get('why', 'waiting')}...)", file=sys.stderr)
        else:
            break
        time.sleep(POLL_INTERVAL)

    if build_number is None:
        last = api_get_json(f"{job_path(args.job)}/api/json", params={
            "tree": "lastBuild[number],inQueue",
        })
        if last.get("inQueue"):
            print("ERROR: Still queued after --wait deadline.", file=sys.stderr)
            sys.exit(1)
        build_number = (last.get("lastBuild") or {}).get("number")
        if build_number is None:
            print("ERROR: Could not determine the build number.", file=sys.stderr)
            sys.exit(1)

    print(f"Build started: #{build_number}")
    build = {}
    while time.time() < deadline:
        build = api_get_json(f"{job_path(args.job)}/{build_number}/api/json")
        if not build.get("building"):
            break
        print(f"  running ({format_duration(build.get('duration'))} elapsed)...", file=sys.stderr)
        time.sleep(POLL_INTERVAL)
    else:
        print(f"ERROR: --wait deadline exceeded while build #{build_number} was running.", file=sys.stderr)
        print(f"Check: status {args.job} --build {build_number}", file=sys.stderr)
        sys.exit(1)

    if not build:
        print(f"ERROR: Build #{build_number} did not report a final state.", file=sys.stderr)
        sys.exit(1)
    print(format_build_markdown(build, job=args.job))
    sys.exit(RESULT_EXIT_CODES.get(build.get("result"), 1))


def cmd_status(args: argparse.Namespace) -> None:
    """Show a build's status (latest by default)."""
    info = api_get_json(f"{job_path(args.job)}/api/json", params={"tree": "inQueue"})
    if info.get("inQueue"):
        print("(a build is currently queued)", file=sys.stderr)
    build = api_get_json(f"{build_url_path(args.job, args.build)}/api/json")
    print(format_build_markdown(build, job=args.job))


def cmd_stages(args: argparse.Namespace) -> None:
    """Show pipeline stage progress for a build (Pipeline jobs only)."""
    data = api_get_json(f"{build_url_path(args.job, args.build)}/wfapi/describe")
    print(format_stages_markdown(data, args.job, args.build or "lastBuild"))


def cmd_console(args: argparse.Namespace) -> None:
    """Read a build's console log; optionally tail it or follow until completion."""
    path = build_url_path(args.job, args.build)
    if not args.follow:
        try:
            text, more, _ = progressive_text(path, 0)
        except ApiError as e:
            print(f"ERROR: Jenkins API {e.code} GET console: {e.body}", file=sys.stderr)
            sys.exit(1)
        lines = text.splitlines()
        if args.tail and len(lines) > args.tail:
            lines = lines[-args.tail:]
        print("\n".join(lines))
        if more:
            print("", "(log continues — increase tail or use --follow)", file=sys.stderr)
        return

    deadline = time.time() + args.timeout if args.timeout else None
    offset = 0
    grace_polls = 20  # a 404 at start usually means the build is still in queue
    while True:
        try:
            text, more, offset = progressive_text(path, offset)
        except ApiError as e:
            if e.code != 404:
                print(f"ERROR: Jenkins API {e.code} GET console: {e.body}", file=sys.stderr)
                sys.exit(1)
            grace_polls -= 1
            if grace_polls <= 0:
                print("ERROR: Build log not found (wrong build number, or build never started).", file=sys.stderr)
                sys.exit(1)
            time.sleep(POLL_INTERVAL)
            continue
        if text:
            print(text, end="" if text.endswith("\n") else "\n")
        if not more:
            b = api_get_json_or_none(f"{path}/api/json", params={"tree": "building,result"})
            if b is None:
                print("ERROR: Build disappeared while following the log.", file=sys.stderr)
                sys.exit(1)
            if not b.get("building"):
                result = b.get("result") or "UNKNOWN"
                print("", f"[build finished: {result}]", file=sys.stderr)
                sys.exit(RESULT_EXIT_CODES.get(result, 1))
        if deadline and time.time() > deadline:
            print("", "ERROR: --follow timeout exceeded.", file=sys.stderr)
            sys.exit(1)
        time.sleep(POLL_INTERVAL)


def cmd_stop(args: argparse.Namespace) -> None:
    """Abort a build (latest by default)."""
    base_url, _, _ = get_env()
    n = args.build if args.build is not None else "lastBuild"
    _post_action(base_url, f"{job_path(args.job)}/{n}/stop")
    print(f"Stop requested for {args.job} #{n}")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jenkins REST API client for CI/CD workflows.",
        epilog="Requires JENKINS_URL, JENKINS_USER, JENKINS_API_TOKEN environment variables.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("whoami", help="Verify connectivity and authentication")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("jobs", help="List jobs (optionally inside a folder)")
    p.add_argument("folder", nargs="?", help="Optional folder path (e.g. 'team/services')")
    p.set_defaults(func=cmd_jobs)

    p = sub.add_parser("job", help="Show job details (status, health, parameters)")
    p.add_argument("job", help="Job name, slash-separated for folders (e.g. 'team/deploy')")
    p.set_defaults(func=cmd_job)

    p = sub.add_parser("build", help="Trigger a build (auto-detects parameterized jobs)")
    p.add_argument("job", help="Job name")
    p.add_argument("--param", action="append", metavar="NAME=VALUE",
                   help="Build parameter (repeatable)")
    p.add_argument("--wait", nargs="?", const=600, type=int, metavar="SECONDS",
                   help="Wait for completion (default timeout: 600s)")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("status", help="Show a build's status (latest by default)")
    p.add_argument("job", help="Job name")
    p.add_argument("--build", type=int, help="Build number (default: latest)")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stages", help="Show pipeline stage progress (Pipeline jobs)")
    p.add_argument("job", help="Job name")
    p.add_argument("--build", type=int, help="Build number (default: latest)")
    p.set_defaults(func=cmd_stages)

    p = sub.add_parser("console", help="Read a build's console log")
    p.add_argument("job", help="Job name")
    p.add_argument("--build", type=int, help="Build number (default: latest)")
    p.add_argument("--tail", type=int, default=200, metavar="N",
                   help="Show last N lines (default: 200; 0 = full log)")
    p.add_argument("--follow", action="store_true", help="Follow until the build finishes")
    p.add_argument("--timeout", type=int, default=0, metavar="SECONDS",
                   help="Max seconds for --follow (0 = no limit)")
    p.set_defaults(func=cmd_console)

    p = sub.add_parser("stop", help="Abort a build (latest by default)")
    p.add_argument("job", help="Job name")
    p.add_argument("--build", type=int, help="Build number (default: latest)")
    p.set_defaults(func=cmd_stop)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
