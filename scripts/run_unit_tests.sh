#!/usr/bin/env bash
set -euo pipefail
# Run pytest excluding integration tests
pytest -q -m "not integration"
