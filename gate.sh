#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOCAL_MODE=0
if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  LOCAL_MODE=1
fi

HAD_NODE_MODULES=0
HAD_VENV=0
HAD_UV_LOCK=0
HAD_PNPM_LOCK=0
HAD_YARN_LOCK=0
HAD_BUN_LOCK=0
[[ -d node_modules ]] && HAD_NODE_MODULES=1
[[ -d .venv ]] && HAD_VENV=1
[[ -f uv.lock ]] && HAD_UV_LOCK=1
[[ -f pnpm-lock.yaml ]] && HAD_PNPM_LOCK=1
[[ -f yarn.lock ]] && HAD_YARN_LOCK=1
[[ -f bun.lockb || -f bun.lock ]] && HAD_BUN_LOCK=1

CLEANED=0
TMP_DIRS=()
RAN_CHECKS=0
RAN_TESTS=0

info() {
  printf 'repo-gate: %s\n' "$*"
}

fail() {
  printf 'repo-gate: FAIL: %s\n' "$*" >&2
  exit 1
}

run() {
  info "$*"
  "$@"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

cleanup_local_artifacts() {
  [[ "$CLEANED" -eq 1 ]] && return
  CLEANED=1

  if [[ "${#TMP_DIRS[@]}" -gt 0 ]]; then
    for dir in "${TMP_DIRS[@]}"; do
      [[ -n "$dir" && -d "$dir" ]] && rm -rf "$dir"
    done
  fi

  if [[ "$LOCAL_MODE" -eq 1 && "${REPO_GATE_KEEP_DEPS:-0}" != "1" ]]; then
    [[ "$HAD_NODE_MODULES" -eq 0 ]] && rm -rf node_modules
    [[ "$HAD_VENV" -eq 0 ]] && rm -rf .venv
    [[ "$HAD_UV_LOCK" -eq 0 ]] && rm -f uv.lock
    [[ "$HAD_PNPM_LOCK" -eq 0 ]] && rm -f pnpm-lock.yaml
    [[ "$HAD_YARN_LOCK" -eq 0 ]] && rm -f yarn.lock
    if [[ "$HAD_BUN_LOCK" -eq 0 ]]; then
      rm -f bun.lockb bun.lock
    fi
  fi
}

trap cleanup_local_artifacts EXIT

meta_tokens() {
  sed 's/#.*//' .repo-meta.yaml | grep -Eo "$1-[a-z0-9-]+" | sort -u || true
}

require_one_of() {
  local value="$1"
  local allowed="$2"
  [[ " $allowed " == *" $value "* ]] || fail "invalid taxonomy value: $value"
}

validate_taxonomy() {
  [[ -f .repo-meta.yaml ]] || fail ".repo-meta.yaml is required"

  local projects functions topics topic_count
  projects="$(meta_tokens proj)"
  functions="$(meta_tokens fn)"
  topics="$(meta_tokens topic)"
  topic_count="$(printf '%s\n' "$topics" | sed '/^$/d' | wc -l | tr -d ' ')"

  [[ "$(printf '%s\n' "$projects" | sed '/^$/d' | wc -l | tr -d ' ')" == "1" ]] ||
    fail ".repo-meta.yaml must contain exactly one proj-* value"
  [[ "$(printf '%s\n' "$functions" | sed '/^$/d' | wc -l | tr -d ' ')" == "1" ]] ||
    fail ".repo-meta.yaml must contain exactly one fn-* value"
  [[ "$topic_count" -ge 1 && "$topic_count" -le 3 ]] ||
    fail ".repo-meta.yaml must contain 1-3 topic-* values"

  local project function topic
  project="$(printf '%s\n' "$projects" | sed -n '1p')"
  function="$(printf '%s\n' "$functions" | sed -n '1p')"

  require_one_of "$project" "proj-gus proj-office-369 proj-abacus proj-borussia proj-splat proj-finance proj-straincellar proj-abledumb proj-familyrecipes proj-sites proj-research-kb proj-substrate"
  require_one_of "$function" "fn-clean-core fn-practice fn-scaffolding fn-dataset fn-reference fn-archive-candidate"

  while IFS= read -r topic; do
    [[ -z "$topic" ]] && continue
    require_one_of "$topic" "topic-ai-agents topic-fleet-infra topic-web-frontend topic-audio-music topic-data-kb topic-finance topic-research-pipeline topic-dev-tooling topic-3d-graphics topic-governance"
  done <<< "$topics"

  info "taxonomy ok: $project / $function / $(printf '%s' "$topics" | tr '\n' ' ')"
}

repo_function() {
  meta_tokens fn | sed -n '1p'
}

has_tests() {
  find . \
    -path './.git' -prune -o \
    -path './node_modules' -prune -o \
    -path './.venv' -prune -o \
    -type f \( -path '*/tests/*' -o -name 'test_*.py' -o -name '*_test.py' -o -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' -o -name '*.spec.tsx' -o -name '*.test.js' -o -name '*.spec.js' \) \
    -print -quit | grep -q .
}

node_package_manager() {
  local declared
  declared="$(node -e "try { process.stdout.write(require('./package.json').packageManager || '') } catch (_) {}")"
  if [[ -f pnpm-lock.yaml || "$declared" == pnpm@* ]]; then
    printf 'pnpm'
  elif [[ -f bun.lockb || -f bun.lock || "$declared" == bun@* ]]; then
    printf 'bun'
  elif [[ -f yarn.lock || "$declared" == yarn@* ]]; then
    printf 'yarn'
  else
    printf 'npm'
  fi
}

has_npm_script() {
  local script="$1"
  node -e "const pkg=require('./package.json'); process.exit(pkg.scripts && pkg.scripts[process.argv[1]] ? 0 : 1)" "$script"
}

node_has_dep() {
  local dep="$1"
  node -e "const pkg=require('./package.json'); const all={...(pkg.dependencies||{}),...(pkg.devDependencies||{})}; process.exit(all[process.argv[1]] ? 0 : 1)" "$dep"
}

pm_run() {
  local pm="$1"
  local script="$2"
  case "$pm" in
    npm) run npm run "$script" ;;
    pnpm) run pnpm run "$script" ;;
    yarn) run yarn "$script" ;;
    bun) run bun run "$script" ;;
    *) fail "unsupported package manager: $pm" ;;
  esac
}

pm_exec() {
  local pm="$1"
  shift
  case "$pm" in
    npm) run npm exec -- "$@" ;;
    pnpm) run pnpm exec "$@" ;;
    yarn) run yarn exec "$@" ;;
    bun) run bunx "$@" ;;
    *) fail "unsupported package manager: $pm" ;;
  esac
}

install_node_deps() {
  local pm="$1"
  case "$pm" in
    npm)
      need_cmd npm
      if [[ -f package-lock.json ]]; then
        run npm ci
      else
        run npm install --package-lock=false --no-audit --no-fund
      fi
      ;;
    pnpm)
      if ! command -v pnpm >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1; then
        run corepack enable
      fi
      need_cmd pnpm
      if [[ -f pnpm-lock.yaml ]]; then
        run pnpm install --frozen-lockfile
      else
        run pnpm install --no-frozen-lockfile
      fi
      ;;
    yarn)
      if ! command -v yarn >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1; then
        run corepack enable
      fi
      need_cmd yarn
      if [[ -f yarn.lock ]]; then
        run yarn install --frozen-lockfile
      else
        run yarn install
      fi
      ;;
    bun)
      need_cmd bun
      run bun install
      ;;
  esac
}

run_node_gate() {
  [[ -f package.json ]] || return 0
  need_cmd node

  local pm
  pm="$(node_package_manager)"
  info "detected package.json; using $pm"
  install_node_deps "$pm"

  if has_npm_script typecheck; then
    pm_run "$pm" typecheck
    RAN_CHECKS=1
  elif [[ -f tsconfig.json ]] || find . -maxdepth 2 -name 'tsconfig.json' -print -quit | grep -q .; then
    pm_exec "$pm" tsc --noEmit
    RAN_CHECKS=1
  else
    info "no Node typecheck detected"
  fi

  if has_npm_script test; then
    pm_run "$pm" test
    RAN_TESTS=1
    RAN_CHECKS=1
  elif [[ -f vitest.config.ts || -f vitest.config.js ]] || node_has_dep vitest; then
    pm_exec "$pm" vitest run
    RAN_TESTS=1
    RAN_CHECKS=1
  elif [[ -f jest.config.ts || -f jest.config.js || -f jest.config.cjs ]] || node_has_dep jest; then
    pm_exec "$pm" jest
    RAN_TESTS=1
    RAN_CHECKS=1
  else
    info "no Node test command detected"
  fi

  if has_npm_script build; then
    pm_run "$pm" build
    RAN_CHECKS=1
  else
    info "no Node build command detected"
  fi
}

run_python_gate() {
  [[ -f pyproject.toml ]] || return 0

  if ! has_tests; then
    info "pyproject.toml present, but no Python tests were detected"
    return
  fi

  RAN_TESTS=1
  RAN_CHECKS=1

  if command -v uv >/dev/null 2>&1; then
    local venv
    venv="$(mktemp -d "${TMPDIR:-/tmp}/repo-gate-uv.XXXXXX")"
    TMP_DIRS+=("$venv")
    if [[ -f uv.lock ]]; then
      run env UV_PROJECT_ENVIRONMENT="$venv" uv sync --frozen --dev
    else
      run uv venv "$venv"
      if ! run uv pip install --python "$venv/bin/python" -e ".[dev]"; then
        run uv pip install --python "$venv/bin/python" -e . pytest pytest-asyncio
      fi
    fi
    run "$venv/bin/python" -m pytest
  else
    need_cmd python3
    local venv
    venv="$(mktemp -d "${TMPDIR:-/tmp}/repo-gate-py.XXXXXX")"
    TMP_DIRS+=("$venv")
    run python3 -m venv "$venv"
    run "$venv/bin/python" -m pip install --upgrade pip
    if ! run "$venv/bin/python" -m pip install -e ".[dev]"; then
      run "$venv/bin/python" -m pip install -e . pytest pytest-asyncio
    fi
    run "$venv/bin/python" -m pytest
  fi
}

run_swift_gate() {
  if [[ -f Package.swift ]]; then
    need_cmd swift
    run swift test
    RAN_TESTS=1
    RAN_CHECKS=1
    return
  fi

  local xcodeproj
  xcodeproj="$(find . -maxdepth 1 -name '*.xcodeproj' -print -quit)"
  [[ -z "$xcodeproj" ]] && return 0

  need_cmd xcodebuild
  [[ -n "${REPO_GATE_XCODE_SCHEME:-}" ]] ||
    fail "set REPO_GATE_XCODE_SCHEME to run xcodebuild test for $xcodeproj"
  run xcodebuild test -scheme "$REPO_GATE_XCODE_SCHEME"
  RAN_TESTS=1
  RAN_CHECKS=1
}

run_cleanroom_gates() {
  if [[ ! -f CLEANROOM.md && ! -f CLEAN-ROOM-CHECKLIST.md ]]; then
    return 0
  fi

  need_cmd rg
  info "running cleanroom grep gates"

  local roots=()
  for root in packages apps src; do
    [[ -d "$root" ]] && roots+=("$root")
  done
  [[ "${#roots[@]}" -gt 0 ]] || roots=(".")

  if rg -n -i 'Ableton' "${roots[@]}" \
    --glob '!**/__tests__/**' \
    --glob '!**/__mocks__/**' \
    --glob '!**/*.test.*' \
    --glob '!**/*.spec.*' \
    --glob '!**/node_modules/**' \
    --glob '!**/.git/**'; then
    fail "cleanroom trademark grep found forbidden hits"
  fi

  if rg -n -i 'ableton-link|rubberband|elastique|zplane|opendaw|gridsound' "${roots[@]}" package.json \
    --glob '!**/node_modules/**' \
    --glob '!**/.git/**'; then
    fail "cleanroom forbidden dependency grep found forbidden hits"
  fi

  info "cleanroom grep gates ok"
}

check_clean_tree() {
  [[ "$LOCAL_MODE" -eq 1 ]] || return 0
  [[ "${REPO_GATE_SKIP_CLEAN:-0}" == "1" ]] && return
  need_cmd git
  if [[ -n "$(git status --porcelain)" ]]; then
    git status --short >&2
    fail "working tree must be clean in local mode"
  fi
  info "working tree clean"
}

validate_taxonomy
run_node_gate
run_python_gate
run_swift_gate
run_cleanroom_gates

if [[ "$(repo_function)" == "fn-clean-core" ]]; then
  [[ "$RAN_TESTS" -eq 1 ]] || fail "fn-clean-core requires detected tests"
fi

[[ "$RAN_CHECKS" -eq 1 ]] || info "no supported build/test stack detected"

cleanup_local_artifacts
check_clean_tree
info "PASS"
