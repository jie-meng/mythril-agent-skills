#!/usr/bin/env bash
# web-tester skill — prepare the project under test for the bundled Playwright toolbox.
#
# Usage:   bash setup.sh [project-dir]     (default: current directory)
#
# Installs playwright as a devDependency of the project under test and
# downloads Chromium for it. Idempotent — safe to re-run.
#
# Windows agents: this is a bash script. Run the equivalent commands instead:
#   npm install --save-dev playwright
#   npx playwright install chromium
set -euo pipefail

TARGET_DIR="${1:-.}"

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

cd "${TARGET_DIR}"

if [ ! -f package.json ]; then
  echo "No package.json here — creating one (npm init -y)."
  npm init -y >/dev/null
fi

echo "Installing playwright (devDependency of $(pwd))..."
npm install --save-dev playwright

echo "Downloading Chromium for Playwright..."
npx playwright install chromium

echo
echo "Setup complete."
echo "Next: run your one-shot test scripts with node FROM THIS directory"
echo "(lib.mjs resolves playwright from the current working directory)."
