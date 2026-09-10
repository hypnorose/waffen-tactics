from pathlib import Path


def test_release_validation_gate_separates_automated_and_runtime_evidence():
    repo_root = Path(__file__).resolve().parents[2]
    document = (repo_root / "docs" / "RELEASE_VALIDATION_GATE.md").read_text(
        encoding="utf-8"
    )

    required_fragments = [
        "canonical pre-release checklist",
        "Local automated gate",
        "Replay and contract evidence",
        "Revision alignment before deployment",
        "VPS deployment and post-deployment checks",
        "Manual runtime gate",
        "1280x720",
        "1920x1080",
        "Needs Manual Test",
        "explicit user waiver",
        "status.sh",
        "api.log",
        "vite.log",
        "Emergency VPS change reconciliation",
        "git diff --check",
        "python -W error -m pytest -q waffen-tactics\\tests",
        "python -W error -m pytest -q waffen-tactics-web\\backend",
        ".\\deploy.ps1 -RunTests",
    ]

    for fragment in required_fragments:
        assert fragment in document, f"Missing release-gate guidance: {fragment}"


def test_historical_desync_checklist_cannot_be_mistaken_for_release_approval():
    repo_root = Path(__file__).resolve().parents[2]
    document = (repo_root / "mdfiles" / "DEPLOYMENT_CHECKLIST.md").read_text(
        encoding="utf-8"
    )

    for fragment in (
        "historical checklist",
        "not a release approval",
        "docs/RELEASE_VALIDATION_GATE.md",
        "Do **not** use `git checkout HEAD~1`",
        "Automated Evidence Only",
        "authenticated Game View",
    ):
        assert fragment in document, f"Missing stale-checklist guard: {fragment}"

    assert "You're Ready!" not in document
