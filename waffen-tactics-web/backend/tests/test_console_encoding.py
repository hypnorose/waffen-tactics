"""Regression coverage for importing the API on legacy Windows consoles."""

import os
import subprocess
import sys
from pathlib import Path


def test_api_import_is_safe_with_cp1250_stdout() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1250"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(backend_dir), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    result = subprocess.run(
        [sys.executable, "-c", "import api"],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("cp1250", errors="replace")
