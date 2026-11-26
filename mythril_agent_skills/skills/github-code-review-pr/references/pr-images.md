# Collecting and Analyzing PR Images

Read this when the PR metadata (`body`, `comments`, `reviews` in
`PR_VIEW_JSON_PATH`) contains image links:
- Markdown image syntax: `![alt](https://...)`
- Plain asset URLs (especially `/assets/` links)

Do this automatically (no extra back-and-forth with the user) when:
- the user asks to read screenshot/image content, or
- screenshots are part of PR verification evidence (offline check steps, UI
  proof, tracking proof), or
- image information is required to validate correctness/risk.

## Where to save images

Download into a random run directory in the unified cache — not `/tmp` or other
ad-hoc locations — so `skills-clean-cache` can find leftovers.

**Bash (macOS / Linux):**
```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
  CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
fi
CACHE_DIR="$CACHE_ROOT/github-code-review-pr"
mkdir -p "$CACHE_DIR"
RUN_DIR=$(mktemp -d "$CACHE_DIR/XXXXXXXX")
IMAGE_CACHE="$RUN_DIR/images"
mkdir -p "$IMAGE_CACHE"
```

**PowerShell (Windows):**
```powershell
$CACHE_ROOT = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "mythril-skills-cache"
$CACHE_DIR = Join-Path $CACHE_ROOT "github-code-review-pr"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
$RUN_DIR = Join-Path $CACHE_DIR ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $RUN_DIR | Out-Null
$IMAGE_CACHE = Join-Path $RUN_DIR "images"
New-Item -ItemType Directory -Force -Path $IMAGE_CACHE | Out-Null
```

Files under this cache directory are temporary artifacts created by this skill.
Read, write, and delete them without asking the user for confirmation.

## Downloading

Use authenticated retrieval in this order:
1. `curl -fsSL "<image_url>" -o "<local_path>"`
2. If enterprise auth fails, retry:
   `curl -fsSL --negotiate -u : "<image_url>" -o "<local_path>"`

## Validate every download before reading it

Enterprise auth redirects often return HTTP 200 with an HTML login page instead
of the image, so check the type after each download:

```bash
file --mime-type -b "<local_path>"
```

- Output starts with `image/` → valid image, read it.
- `text/html`, `text/plain`, or anything else → it captured an auth redirect.
  Treat it as a retrieval failure: delete it (`rm -f "<local_path>"`), don't
  try to read it, and log a one-line note (e.g. "Image download returned HTML
  instead of image data — likely auth redirect, skipping").

## Analyzing

Read only validated images with image-capable tools and summarize:
- what the screenshot shows (UI / debug panel / logs),
- key values, events, or URLs visible in the image,
- whether the screenshot evidence supports the PR's claim.

Put this in the review's section 1 as the image evidence summary.

## Failures

If retrieval fails (curl error, non-image content, auth redirect), log the URL
and reason, skip the image, and continue the review. Don't repeatedly attempt
to read invalid files. If all images fail, say in the review that image
evidence could not be verified due to access restrictions, and suggest the user
check the screenshots manually.
