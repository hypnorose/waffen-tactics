#!/usr/bin/env bash
set -euo pipefail
# Run only integration tests (marked with @pytest.mark.integration)
pytest -q -m integration
