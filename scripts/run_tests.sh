#!/usr/bin/env bash
set -euo pipefail

# Simple test runner script for the repository.
# Usage:
#   ./scripts/run_tests.sh            # run default (unit) tests
#   ./scripts/run_tests.sh --all      # run full pytest
#   ./scripts/run_tests.sh --exclude "10v10,seed5"  # exclude tests matching substrings
#   ./scripts/run_tests.sh --integration  # run tests marked integration (not implemented)

EXCLUDE_PATTERNS=""
MODE="unit"

while [[ $# -gt 0 ]]; do
  case $1 in
    --all)
      MODE="all"
      shift
      ;;
    --exclude)
      EXCLUDE_PATTERNS="$2"
      shift 2
      ;;
    --integration)
      MODE="integration"
      shift
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

# Build pytest -k expression to exclude patterns
PYTEST_K=""
if [[ -n "$EXCLUDE_PATTERNS" ]]; then
  IFS=',' read -ra PATS <<< "$EXCLUDE_PATTERNS"
  EXPR=""
  for p in "${PATS[@]}"; do
    p_trimmed=$(echo "$p" | xargs)
    if [[ -z "$p_trimmed" ]]; then
      continue
    fi
    if [[ -z "$EXPR" ]]; then
      EXPR="not $p_trimmed"
    else
      EXPR="$EXPR and not $p_trimmed"
    fi
  done
  PYTEST_K="$EXPR"
fi

# Choose pytest args based on mode
if [[ "$MODE" == "unit" ]]; then
  # Run a fast subset: prefer test files under waffen-tactics/tests and waffen-tactics-web/backend/tests small ones
  BASE_ARGS=(waffen-tactics/tests)
elif [[ "$MODE" == "integration" ]]; then
  BASE_ARGS=(waffen-tactics-web/backend/tests)
else
  BASE_ARGS=()
fi

# Build final pytest command
CMD=(pytest -q)
if [[ ${#BASE_ARGS[@]} -gt 0 ]]; then
  CMD+=("${BASE_ARGS[@]}")
fi
if [[ -n "$PYTEST_K" ]]; then
  CMD+=(-k "$PYTEST_K")
fi

# Print and run
echo "Running: ${CMD[*]}"
# Activate venv if it exists
if [[ -f "waffen-tactics-web/backend/venv/bin/activate" ]]; then
  source waffen-tactics-web/backend/venv/bin/activate
fi
# shellcheck disable=SC2086
${CMD[*]}
