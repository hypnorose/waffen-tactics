import subprocess
import sys
import pytest
from pathlib import Path


@pytest.mark.integration
def test_generate_and_verify_replay_passes_for_seed_19(tmp_path):
    """Integration test: run the generator+verifier for a known-good seed.

    This ensures the end-to-end replay+reconstruct verification runs in CI.
    """
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "waffen-tactics-web" / "backend" / "scripts" / "generate_and_verify_replay.py"
    out_file = tmp_path / "sim_dump_19.jsonl"
    cmd = [sys.executable, str(script), "--seed", "19", "--out", str(out_file)]
    res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        pytest.fail(f"Replay script failed (rc={res.returncode})\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}")
    assert "Verification PASSED" in res.stdout
