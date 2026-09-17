#!/usr/bin/env bash
# ccn-gate-lib.sh — shared CCN<=10 gate logic for local git hooks.
#
# Policy (dru-2okra.20):
#   - Pinned analyzer: lizard==1.24.0.
#   - CCN<=10 for all changed imperative code.
#   - Unsupported imperative language in changed files = fail loud.
#   - Only paths in scripts/ccn-allow-manifest.txt may bypass analysis.
#   - No inline forgiveness. No ad hoc per-function exceptions.
#
# This file is sourced by pre-commit, pre-merge-commit, and pre-push.
# Callers must set CCN_FILES (space-separated list of changed .py files)
# before sourcing this library.
#
# Callers may also set CCN_UNSUPPORTED_LANGS (space-separated list of
# unsupported-language file paths) to trigger the fail-loud path.

set -euo pipefail

# ---------------------------------------------------------------------------
# Unsupported imperative language check (GAP-2).
# Imperative languages this gate does NOT yet analyze — must not be silently
# skipped if they appear in a PR.
# ---------------------------------------------------------------------------
_CCN_IMPERATIVE_EXTS="c cc cpp cxx cs go java js ts jsx tsx rb rs swift kt"

ccn_check_unsupported_langs() {
    local files="$1"
    local unsupported=""

    for f in $files; do
        ext="${f##*.}"
        for imperative_ext in $_CCN_IMPERATIVE_EXTS; do
            if [ "$ext" = "$imperative_ext" ]; then
                unsupported="$unsupported $f"
                break
            fi
        done
    done

    if [ -n "$(echo "$unsupported" | tr -d ' ')" ]; then
        echo "ERROR: Changed files include unsupported imperative languages:" >&2
        for f in $unsupported; do
            echo "  $f" >&2
        done
        echo "" >&2
        echo "The CCN gate covers Python only. Adding support for another imperative" >&2
        echo "language requires updating ccn-gate.yml and .githooks/ccn-gate-lib.sh." >&2
        echo "Do not merge changes to unsupported imperative languages without CCN coverage." >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Lizard version tamper-check.
# ---------------------------------------------------------------------------
ccn_check_analyzer() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 is required to run the CCN gate." >&2
        exit 1
    fi

    local installed
    installed=$(python3 -m lizard --version 2>&1 || true)
    if [ "$installed" != "1.24.0" ]; then
        echo "ERROR: lizard==1.24.0 is required for the CCN gate." >&2
        echo "  Expected: 1.24.0" >&2
        echo "  Got:      ${installed:-<not found>}" >&2
        echo "" >&2
        echo "Install it: pip install lizard==1.24.0" >&2
        echo "Or install dev deps: pip install -e '.[dev]'" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Allow-manifest filter.
# ---------------------------------------------------------------------------
ccn_filter_manifest() {
    local files="$1"
    local root="$2"
    local manifest="$root/scripts/ccn-allow-manifest.txt"

    if [ ! -f "$manifest" ]; then
        echo "$files"
        return
    fi

    local filtered=""
    for f in $files; do
        local skip=0
        while IFS= read -r pattern; do
            # Skip comment lines and empty lines.
            case "$pattern" in
                '#'*|'') continue ;;
            esac
            case "$f" in
                $pattern) skip=1; break ;;
            esac
        done < "$manifest"
        if [ "$skip" -eq 0 ]; then
            filtered="$filtered $f"
        fi
    done
    echo "$filtered"
}

# ---------------------------------------------------------------------------
# Run lizard gate on a file list.
# ---------------------------------------------------------------------------
ccn_run_gate() {
    local files="$1"
    local context_label="$2"

    if [ -z "$(echo "$files" | tr -d ' ')" ]; then
        echo "ccn-gate [$context_label]: no Python files to check — skipped."
        return 0
    fi

    echo "ccn-gate [$context_label]: checking CCN<=10 for: $files"

    # shellcheck disable=SC2086
    if ! python3 -m lizard $files -C 10 -w -i 0; then
        echo "" >&2
        echo "FAIL [$context_label]: One or more changed functions exceed CCN=10." >&2
        echo "Refactor the flagged function(s) to reduce branching complexity." >&2
        echo "No inline suppression comments are permitted — split or simplify." >&2
        exit 1
    fi

    echo "PASS [$context_label]: All changed Python functions are within CCN<=10."
}
