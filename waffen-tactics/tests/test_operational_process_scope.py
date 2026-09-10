from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_operational_scripts_use_project_scoped_process_discovery():
    scope = (REPO_ROOT / 'runtime_process_scope.sh').read_text(encoding='utf-8')
    status = (REPO_ROOT / 'status.sh').read_text(encoding='utf-8')
    stop = (REPO_ROOT / 'stop-all.sh').read_text(encoding='utf-8')

    assert 'readlink "/proc/$pid/cwd"' in scope
    assert 'project_pids_for_cwd' in scope
    assert 'project_caddy_pids' in scope
    assert 'case " $cmdline "' in scope
    assert 'project_pids_for_cwd' in status
    assert 'project_caddy_pids' in status
    assert 'pgrep -f' not in status
    assert 'project_process_report' in stop
    assert 'project_pids_for_cwd' in stop
    assert 'project_caddy_pids' in stop
    assert 'ps aux | grep' not in stop
    assert 'pgrep -a caddy' not in stop
