#!/bin/bash

# Shared process discovery for the Waffen Tactics operational scripts.
# Callers must pass the expected project directory explicitly.

process_cwd() {
    local pid="$1"
    local cwd

    cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
    if [ -z "$cwd" ]; then
        # Caddy runs through sudo and its /proc metadata is not readable by
        # the deploy user. Keep this fail-closed: a missing sudo permission
        # yields no owner instead of broad process matching.
        cwd="$(sudo -n readlink "/proc/$pid/cwd" 2>/dev/null || true)"
    fi
    printf '%s\n' "$cwd"
}

process_cmdline() {
    local pid="$1"
    local cmdline

    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    if [ -z "$cmdline" ]; then
        # The privileged reader opens /proc; tr itself remains unprivileged.
        cmdline="$(sudo -n cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ' || true)"
    fi
    printf '%s\n' "$cmdline"
}

project_pids_for_cwd() {
    local pattern="$1"
    local expected_cwd="$2"
    local pid cwd

    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        cwd="$(process_cwd "$pid")"
        if [ "$cwd" = "$expected_cwd" ]; then
            echo "$pid"
        fi
    done < <(pgrep -f "$pattern" 2>/dev/null || true)
}

project_caddy_pids() {
    local expected_cwd="$1"
    local config_name="${2:-Caddyfile}"
    local pid cwd cmdline

    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        cwd="$(process_cwd "$pid")"
        [ "$cwd" = "$expected_cwd" ] || continue
        cmdline="$(process_cmdline "$pid")"
        if caddy_config_matches_project "$cmdline" "$expected_cwd" "$config_name"; then
            echo "$pid"
        fi
    done < <(pgrep -x caddy 2>/dev/null || true)
}

caddy_config_matches_project() {
    local cmdline="$1"
    local expected_cwd="$2"
    local config_name="${3:-Caddyfile}"
    local absolute_config="$expected_cwd/$config_name"

    case " $cmdline " in
        *" --config $config_name "*|*" --config $absolute_config "*|*" --config=$config_name "*|*" --config=$absolute_config "*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

project_process_report() {
    local pid

    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        ps -p "$pid" -o pid=,args=
    done < <(
        {
            project_pids_for_cwd "api.py" "$BACKEND_DIR"
            project_pids_for_cwd "vite" "$WEB_DIR"
            project_caddy_pids "$WEB_DIR" "Caddyfile"
        } | sort -n -u
    )
}
