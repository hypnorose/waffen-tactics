from pathlib import Path


def test_remote_workflow_documents_emergency_reconciliation_boundaries():
    repo_root = Path(__file__).resolve().parents[2]
    document = (repo_root / 'docs' / 'CODEX_REMOTE_WORKFLOW.md').read_text(encoding='utf-8')

    required_fragments = [
        'Emergency VPS change reconciliation',
        'git diff --binary HEAD',
        'git ls-files --others --exclude-standard',
        'git format-patch',
        '.env',
        'node_modules',
        'SQLite',
        'git diff --check',
        '.\\deploy.ps1 -RunTests',
        './status.sh',
        'api.log',
        'vite.log',
    ]

    for fragment in required_fragments:
        assert fragment in document, f'Missing reconciliation guidance: {fragment}'
