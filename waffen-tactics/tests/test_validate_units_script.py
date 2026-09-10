import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / 'tools' / 'scripts' / 'validate_units.py'


def _run_validator(cwd):
    environment = os.environ.copy()
    environment['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding='utf-8',
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Validation complete:' in result.stdout
    assert 'traits checked' in result.stdout


def test_dataset_validator_resolves_authoritative_files_from_any_working_directory(tmp_path):
    _run_validator(REPO_ROOT)
    _run_validator(tmp_path)
