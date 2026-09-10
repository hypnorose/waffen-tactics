from pathlib import Path


def test_deploy_run_tests_matches_the_canonical_release_gate():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "deploy.ps1").read_text(encoding="utf-8")

    required_fragments = [
        "python -W error -m pytest -q 'waffen-tactics\\tests'",
        "python -W error -m pytest -q 'waffen-tactics-web\\backend'",
        "Invoke-Step \"Frontend typecheck\"",
        "npm run typecheck",
        "Invoke-Step \"Frontend lint\"",
        "npm run lint",
        "Invoke-Step \"Frontend tests\"",
        "npx vitest run",
        "Invoke-Step \"Frontend production build\"",
        "npm run build",
    ]

    for fragment in required_fragments:
        assert fragment in script, f"Missing canonical deploy gate command: {fragment}"

    assert "python -m pytest -q 'waffen-tactics\\tests'" not in script
    assert "python -m pytest -q 'waffen-tactics-web\\backend\\tests'" not in script
    assert "if ($RunTests)" in script
    assert script.index("if ($RunTests)") < script.index("$trackedChanges")
