#!/bin/bash

# Shared process discovery for the Waffen Tactics operational scripts.
# Callers must pass the expected project directory explicitly.

project_pids_for_cwd() {
    local pattern="$1"
    local expected_cwd="$2"
    local pid cwd

    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
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
        cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
        [ "$cwd" = "$expected_cwd" ] || continue
        cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
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
