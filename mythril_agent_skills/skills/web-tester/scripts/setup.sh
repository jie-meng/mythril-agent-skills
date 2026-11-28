#!/usr/bin/env bash
# web-tester skill — install the Playwright runtime for the bundled toolbox.
#
# Usage:   bash setup.sh
#
# Installs playwright into the skill's own runtime directory in the unified
# per-user cache — NOT into the project under test, whose package.json and
# lockfile are never touched:
#
#   macOS:   ~/Library/Caches/mythril-skills-cache/web-tester/runtime/
#   Linux:   ${XDG_CACHE_HOME:-~/.cache}/mythril-skills-cache/web-tester/runtime/
#   Windows: %LOCALAPPDATA%\mythril-skills-cache\web-tester\runtime\
#
# Chromium is downloaded to Playwright's own shared browser cache. Idempotent —
# safe to re-run (also upgrades a stale install). lib.mjs resolves playwright
# from the runtime directory automatically.
#
# Windows agents without bash: run the equivalent commands instead:
#   $d = "$env:LOCALAPPDATA\mythril-skills-cache\web-tester\runtime"
#   New-Item -ItemType Directory -Force $d; cd $d
#   npm init -y; npm install playwright; npx playwright install chromium
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node not found. Install Node.js >= 18 first: https://nodejs.org/" >&2
  exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "${NODE_MAJOR}" -lt 18 ]; then
  echo "ERROR: node >= 18 required, found $(node -v)." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. It ships with Node.js — check your installation." >&2
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    CACHE_ROOT="$HOME/Library/Caches/mythril-skills-cache"
    ;;
  MINGW* | MSYS* | CYGWIN*)
    CACHE_ROOT="${LOCALAPPDATA:-$HOME/AppData/Local}/mythril-skills-cache"
    ;;
  *)
    CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/mythril-skills-cache"
    ;;
esac
RUNTIME_DIR="${CACHE_ROOT}/web-tester/runtime"

mkdir -p "${RUNTIME_DIR}"
cd "${RUNTIME_DIR}"

if [ ! -f package.json ]; then
  npm init -y >/dev/null
fi

echo "Installing playwright into ${RUNTIME_DIR} ..."
npm install --no-audit --no-fund playwright

echo "Downloading Chromium for Playwright..."
npx playwright install chromium

echo
echo "Setup complete. Runtime: ${RUNTIME_DIR}"
echo "The project under test was not modified; run one-shot test scripts from"
echo "the project root so evidence lands in ./web-tester-evidence/."
