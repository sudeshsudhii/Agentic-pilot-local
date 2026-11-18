#!/usr/bin/env bash
# Pre-restart / pre-commit verification gate.
#
# Runs every fast, mock-only check across both halves of the app and refuses
# to pass if any of them fail. Nothing here launches a real browser or
# FreeCAD -- that is deliberate: this gate must be fast enough to run before
# every restart, not just before a release.
#
# Usage: bash scripts/verify.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

section() { printf '\n\033[1;36m=== %s ===\033[0m\n' "$1"; }
ok()      { printf '\033[1;32m[OK]\033[0m %s\n' "$1"; }
bad()     { printf '\033[1;31m[FAIL]\033[0m %s\n' "$1"; FAIL=1; }

section "Backend: pytest (mocked, excludes tests/e2e)"
# pytest must run with the project root as cwd so `backend.*` imports resolve.
if (cd "$ROOT" && PILOT_HEADLESS_BROWSER=true python -m pytest tests --ignore=tests/e2e -q); then
  ok "backend pytest"
else
  bad "backend pytest"
fi

section "Frontend: vitest"
if (cd "$ROOT/frontend" && npx vitest run); then
  ok "frontend vitest"
else
  bad "frontend vitest"
fi

section "Frontend: tsc --noEmit"
if (cd "$ROOT/frontend" && npx tsc --noEmit); then
  ok "frontend typecheck"
else
  bad "frontend typecheck"
fi

section "Frontend: production build"
if (cd "$ROOT/frontend" && npx vite build >/tmp/pilot_vite_build.log 2>&1); then
  ok "frontend build"
else
  bad "frontend build (see /tmp/pilot_vite_build.log)"
fi

echo
if [ "$FAIL" -eq 0 ]; then
  printf '\033[1;32mALL CHECKS PASSED\033[0m\n'
  exit 0
else
  printf '\033[1;31mVERIFY FAILED -- do not restart or commit until this is green.\033[0m\n'
  exit 1
fi
