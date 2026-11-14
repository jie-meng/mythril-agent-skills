# jenkins skill

Operate any Jenkins instance from the terminal — trigger builds, poll status,
inspect pipeline stages, tail console logs, and abort builds — through the
Jenkins REST API. The bundled Python script uses only the standard library
(zero dependencies) and works with self-hosted and Jenkins-in-Docker setups
alike.

## Setup

### 1. Create an API token

1. Open your Jenkins instance and click your username (top right)
2. **Security** → **API Token** → **Add new Token** → **Generate**
3. Copy the token — it is shown only once

Official docs: <https://www.jenkins.io/doc/book/managing/security/#api-tokens>

### 2. Set environment variables

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export JENKINS_URL="https://ci.example.com:8443"   # context path allowed
export JENKINS_USER="your-username"
export JENKINS_API_TOKEN="your-api-token"
```

Verify: `python3 scripts/jenkins_api.py whoami`

### Self-signed / private-CA certificates

If your Jenkins uses a certificate from a private CA, point the script at the
CA bundle:

```bash
export SSL_CERT_FILE="/path/to/ca-bundle.pem"   # or CURL_CA_BUNDLE / REQUESTS_CA_BUNDLE
```

As a last resort only: `export SSL_NO_VERIFY=1`.

## Commands

| Command | Description | Writes to CI |
|---|---|---|
| `whoami` | Verify connectivity and authentication | no |
| `jobs [FOLDER]` | List jobs with status and last build | no |
| `job NAME` | Job details: health, last builds, parameter definitions | no |
| `build NAME [--param k=v ...] [--wait [SECONDS]]` | Trigger a build; `--wait` polls queue + build to completion | yes |
| `status NAME [--build N]` | Build status (latest by default) | no |
| `stages NAME [--build N]` | Pipeline stage progress (Pipeline jobs) | no |
| `console NAME [--build N] [--tail N] [--follow]` | Console log, tailable and followable | no |
| `stop NAME [--build N]` | Abort a build | yes |

Exit codes for `build --wait` and `console --follow` follow the final result:
0 = SUCCESS, 1 = FAILURE, 2 = UNSTABLE, 3 = ABORTED, 4 = NOT_BUILT.

## Examples

```bash
# Trigger and wait for a build
python3 scripts/jenkins_api.py build robo-server-build --wait

# Trigger a parameterized deploy job
python3 scripts/jenkins_api.py build deploy-dev \
  --param TARGET_SERVERS=172.22.193.101 --wait 1200

# Find out where a build is stuck
python3 scripts/jenkins_api.py stages deploy-dev --build 42
python3 scripts/jenkins_api.py console deploy-dev --build 42 --tail 100
```

## Security notes

- The token stays in the environment; the script never prints it and accepts
  no credentials on the command line.
- AI agents must follow the "Security — MANDATORY rules for AI agents"
  section in `SKILL.md` (no echoing tokens, no credential-store extraction).
- `build` and `stop` change real CI state — the SKILL.md safety-gate section
  asks agents to confirm intent before using them, especially for production
  deployment jobs.
