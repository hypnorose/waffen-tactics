from pathlib import Path
import shutil
import subprocess

import pytest


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


def test_start_uses_shared_caddy_discovery_and_refuses_duplicate_restart():
    start = (REPO_ROOT / 'start-all.sh').read_text(encoding='utf-8')
    scope = (REPO_ROOT / 'runtime_process_scope.sh').read_text(encoding='utf-8')

    assert '. "$SCRIPT_DIR/runtime_process_scope.sh"' in start
    assert 'project_caddy_pids "$WEB_DIR" "Caddyfile"' in start
    assert 'pgrep -a caddy' not in start
    assert 'refusing to start a duplicate' in start
    assert 'caddy_config_matches_project' in scope
    assert ' --config $config_name ' in scope
    assert ' --config $absolute_config ' in scope
    assert ' --config=$config_name ' in scope
    assert ' --config=$absolute_config ' in scope


def test_caddy_config_matcher_covers_relative_absolute_and_unrelated_processes():
    bash = shutil.which('bash')
    if not bash:
        pytest.skip('bash is unavailable on this host')

    probe = subprocess.run(
        [bash, '-c', 'exit 0'],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip('bash launcher is unavailable on this host')

    scope = (REPO_ROOT / 'runtime_process_scope.sh').as_posix()
    command = (
        f". '{scope}'; "
        "caddy_config_matches_project 'caddy run --config Caddyfile' '/srv/waffen-tactics' 'Caddyfile'; "
        "caddy_config_matches_project 'caddy run --config /srv/waffen-tactics/Caddyfile' '/srv/waffen-tactics' 'Caddyfile'; "
        "caddy_config_matches_project 'caddy run --config=Caddyfile' '/srv/waffen-tactics' 'Caddyfile'; "
        "caddy_config_matches_project 'caddy run --config=/srv/waffen-tactics/Caddyfile' '/srv/waffen-tactics' 'Caddyfile'; "
        "! caddy_config_matches_project 'caddy run --config /srv/other/Caddyfile' '/srv/waffen-tactics' 'Caddyfile'"
    )
    result = subprocess.run([bash, '-c', command], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
