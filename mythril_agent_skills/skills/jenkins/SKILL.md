---
name: jenkins
description: >
  Operates a Jenkins instance through a bundled REST API script: list and
  inspect jobs, trigger (parameterized) builds and wait on them, check status and
  pipeline stages, read or follow console logs, and stop builds. Use when the
  user wants to run, check, or cancel a Jenkins build or pastes a Jenkins URL —
  e.g. "trigger the build", "jenkins console", "跑一下构建", "部署 dev",
  "看构建日志", "重跑 CI". Not for Git/PR work (gh-operations).
license: Apache-2.0
---

# When to Use This Skill

- The user asks to trigger, re-run, or check a Jenkins build/job ("重新编译", "跑一次构建", "看构建", "重新部署 dev", "trigger build")
- The user pastes a Jenkins URL (e.g. `https://ci.example.com/job/foo/123/`) and wants details or actions on it
- The user asks where a pipeline is stuck ("卡在哪个 stage 了", "为什么红了")
- The user wants build logs ("看构建日志", "jenkins console", "tail 一下 build")
- The user wants to abort a running build ("停掉这次构建", "cancel build")

**NOT a trigger**: local git operations, PR reviews (`github-code-review-pr`), GitHub issues/PRs (`gh-operations`). Jenkins job *policies* (which jobs to run, in what order, with what approval gates) are project-level concerns — this skill provides generic instance operations only.

# Prerequisites

Requires `JENKINS_URL`, `JENKINS_USER`, and `JENKINS_API_TOKEN`. See `README.md` in this skill directory for setup.

- `JENKINS_URL` (**required**) — e.g. `https://ci.example.com:8443`; a context path (`https://host/jenkins`) is allowed
- `JENKINS_USER` (**required**) — Jenkins username
- `JENKINS_API_TOKEN` (**required**) — API token from Jenkins (user → Security → API Token)

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the values of `JENKINS_URL`, `JENKINS_USER`, `JENKINS_API_TOKEN`, or any other environment variable. Do NOT run commands like `echo $JENKINS_API_TOKEN` or `printenv JENKINS_API_TOKEN` — even for debugging.
2. **NEVER pass token/credential values as inline CLI arguments or env-var overrides** (e.g. `JENKINS_API_TOKEN=xxx python3 ...`). The script reads credentials from the environment automatically — just run the script directly.
3. **When debugging auth errors**, rely solely on the script's error output (401, 403, 404 messages). Do NOT attempt to verify tokens by reading or printing them.
4. **Do NOT read environment variable values** using shell commands or programmatic access. The script handles all credential access internally.
5. **NEVER extract credentials from OS credential stores or config files.** Strictly forbidden commands include:
   - `security find-internet-password`, `security find-generic-password` (macOS Keychain)
   - `git credential fill`, `cat ~/.git-credentials`, `cat ~/.netrc`
   - Any command that outputs a password, token, or secret value from any credential store
6. **NEVER use extracted credential values in commands.** Do NOT manually construct authenticated requests (e.g. `curl -u user:<token>`). The bundled script handles all authentication internally.
7. **Use only the documented CLI subcommands.** Do NOT `import` the bundled script or call its internal functions (`get_token()`, `*_request()`, etc.) via `python3 -c` or ad-hoc code — that bypasses the CLI's argument handling, and a misordered argument can put the credential into a URL or error message. If a needed subcommand is missing, tell the user instead of scripting around it. Script output redacts credentials as `[REDACTED]`; if a credential value ever appears in any output anyway, do NOT repeat it — tell the user to rotate it.

## Runtime requirements

- Python 3.10+ for `scripts/jenkins_api.py` (standard library only, zero dependencies)

# Workflow

1. Determine what the user wants (view status, trigger, read logs, abort)
2. Run the appropriate script command
3. Read the markdown output and present it to the user

**Safety gates — Jenkins actions change real CI state.**

- `status`, `stages`, `console`, `jobs`, `job`, `whoami` are read-only — run freely.
- `build` triggers a real build; `stop` aborts a running one. Confirm intent before running them when the user has not explicitly asked for the action.
- Before triggering a **deployment** job (job names often contain `deploy`, `prod`, `release`), confirm explicitly — especially when the target environment is production. Project-level skills define the exact approval gates for their own pipelines; when one exists, follow it.

## Using the Output

The script outputs structured markdown. Build results use Jenkins result codes: `SUCCESS`, `FAILURE`, `UNSTABLE`, `ABORTED`, `NOT_BUILT`. Exit codes mirror them: 0 = SUCCESS, 1 = FAILURE, 2 = UNSTABLE, 3 = ABORTED/queued-cancel, 4 = NOT_BUILT; other errors use 1 (API/network) and 2 (bad arguments).

# Running the Script

All commands use `scripts/jenkins_api.py`. `SKILL_PATH` below is this skill's installed directory.

**Job argument**: a job name (folders slash-separated, e.g. `team/services/deploy`) **or a pasted Jenkins URL** — `https://ci.example.com/job/team/job/app/42/console` becomes job `team/app`, build `42`. The URL must be on `JENKINS_URL`'s host. Multibranch branches whose name contains `/` are stored by Jenkins as `feature%2Fx` (shown as `feature%252Fx` in the browser): pass `repo/feature%2Fx`, or just paste the URL.

### Verify setup and connectivity

```bash
python3 SKILL_PATH/scripts/jenkins_api.py whoami
```

### List jobs

```bash
python3 SKILL_PATH/scripts/jenkins_api.py jobs
python3 SKILL_PATH/scripts/jenkins_api.py jobs "team/services"        # jobs inside a folder
```

### Inspect a job (status, health, parameters)

```bash
python3 SKILL_PATH/scripts/jenkins_api.py job robo-server-build
python3 SKILL_PATH/scripts/jenkins_api.py job "team/services/deploy"   # slash-separated for folders
```

The output lists the job's parameter definitions — use them to decide `--param` values for `build`.

### Trigger a build

```bash
python3 SKILL_PATH/scripts/jenkins_api.py build robo-server-build --wait
python3 SKILL_PATH/scripts/jenkins_api.py build deploy-dev --wait 1200
python3 SKILL_PATH/scripts/jenkins_api.py build deploy-dev \
  --param TARGET_SERVERS=172.22.193.101 --param SERVER_VERSION=latest
```

- `--wait` polls the queue and the build until a final state (default timeout 600s; `--wait 1200` for 20 min). Without it, the script prints the queue URL and returns immediately.
- Parameterized jobs are detected automatically and routed to `buildWithParameters`; unknown parameter names are rejected with the list of defined ones.

### Check a build's status

```bash
python3 SKILL_PATH/scripts/jenkins_api.py status deploy-dev                 # latest build
python3 SKILL_PATH/scripts/jenkins_api.py status deploy-dev --build 42
```

### Show pipeline stage progress

```bash
python3 SKILL_PATH/scripts/jenkins_api.py stages deploy-dev --build 42
```

Use this first when a build seems stuck — it shows which stage is `IN PROGRESS` and how long each stage took. Only works for Pipeline (workflow) jobs; freestyle jobs print a note instead.

### Read console logs

```bash
python3 SKILL_PATH/scripts/jenkins_api.py console deploy-dev --build 42 --tail 100
python3 SKILL_PATH/scripts/jenkins_api.py console deploy-dev --tail 0        # full log
python3 SKILL_PATH/scripts/jenkins_api.py console deploy-dev --follow        # stream until finished
python3 SKILL_PATH/scripts/jenkins_api.py console deploy-dev --follow --timeout 600
python3 SKILL_PATH/scripts/jenkins_api.py console "https://ci.example.com/job/deploy-dev/42/"
```

`--follow` pins the build number when it starts, so a newer build cannot hijack the stream.

Exit code follows the final build result (0 = SUCCESS, 1 = FAILURE, …).

### Abort a build

```bash
python3 SKILL_PATH/scripts/jenkins_api.py stop deploy-dev --build 42
python3 SKILL_PATH/scripts/jenkins_api.py stop "https://ci.example.com/job/deploy-dev/42/"
```

A build number is **required** (from `--build` or the URL) — `stop` never defaults to the latest build, which could be someone else's. Confirm with the user before aborting.

# Error Handling

- **Missing environment variables**: the script prints which of `JENKINS_URL` / `JENKINS_USER` / `JENKINS_API_TOKEN` is missing and how to set them.
- **401 Unauthorized**: wrong username or token — regenerate the token in Jenkins (user → Security → API Token).
- **403 Forbidden**: the account lacks permission for the operation, or CSRF is enforced in a non-standard way (the script retries POSTs with a crumb automatically before surfacing this).
- **404 Not Found**: job name wrong (folders use slash-separated paths), or the build number does not exist.
- **SSL: CERTIFICATE_VERIFY_FAILED**: self-signed / private-CA Jenkins. Set `SSL_CERT_FILE` (or `CURL_CA_BUNDLE` / `REQUESTS_CA_BUNDLE`) to the CA bundle, or `SSL_NO_VERIFY=1` as a last resort.
- **`--wait` deadline exceeded**: the script reports whether it was stuck in queue or still building; follow up with `status` / `stages` / `console`.

# Notes

- The script uses only the Python standard library — no `pip install` needed.
- Auth is HTTP Basic with `JENKINS_USER:JENKINS_API_TOKEN`. API-token auth bypasses the CSRF crumb on Jenkins 2.96+; a crumb retry is kept for older or stricter instances.
- Folders are slash-separated job names (`team/services/deploy` → `/job/team/job/services/job/deploy`); each name is percent-encoded once, so `feature%2Fx` → `/job/feature%252Fx` as Jenkins expects.
- Console reading uses the `progressiveText` endpoint's `X-Text-Size` / `X-More-Data` headers, so `--follow` is incremental, not full-log refetching.
- For advanced use cases not covered by the script (creating jobs, editing config, remote-trigger tokens), see `SKILL_PATH/references/API_REFERENCE.md`.
