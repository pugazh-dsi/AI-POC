#!/usr/bin/env bash
#
# app.sh - single-instance start/stop controller for AI Playbook
#
#   ./app.sh start     Start backend (uvicorn :8000) + frontend (vite :5173)
#   ./app.sh stop      Stop both
#   ./app.sh restart   Stop then start
#   ./app.sh status    Show what is running
#
# Only ONE execution of the stack can run at a time: a lock file plus PID
# files guarantee a second "start" refuses instead of spawning duplicates.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
LOCK_FILE="$RUN_DIR/app.lock"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

# ── helpers ───────────────────────────────────────────────
info() { printf '  %s\n' "$*"; }
ok()   { printf '\033[32m✔\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*"; }
err()  { printf '\033[31m✘\033[0m %s\n' "$*" >&2; }

# Read a pid file and echo the pid only if that process is still alive.
live_pid() {
    local pid_file="$1" pid
    [ -f "$pid_file" ] || return 1
    pid="$(cat "$pid_file" 2>/dev/null)"
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    echo "$pid"
}

# Terminate a process group politely, then forcefully.
stop_pid_file() {
    local name="$1" pid_file="$2" pid
    if ! pid="$(live_pid "$pid_file")"; then
        rm -f "$pid_file"
        info "$name is not running"
        return 0
    fi
    # Negative pid targets the whole process group (uvicorn/vite spawn children).
    kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
    for _ in $(seq 1 40); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.25
    done
    if kill -0 "$pid" 2>/dev/null; then
        warn "$name did not exit, sending SIGKILL"
        kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
    fi
    rm -f "$pid_file"
    ok "$name stopped (pid $pid)"
}

# ── single-instance lock ──────────────────────────────────
# Held for the whole run of this script so two invocations cannot race.
acquire_lock() {
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        err "Another app.sh run is in progress (lock: $LOCK_FILE). Aborting."
        exit 1
    fi
}

# ── start ─────────────────────────────────────────────────
start_backend() {
    local pid
    if pid="$(live_pid "$BACKEND_PID_FILE")"; then
        warn "Backend already running (pid $pid) - not starting a second one"
        return 0
    fi

    local python_bin="$BACKEND_DIR/.venv/bin/python"
    [ -x "$python_bin" ] || python_bin="$(command -v python3 || command -v python)"
    if [ -z "$python_bin" ]; then
        err "No Python interpreter found"
        return 1
    fi
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        warn "backend/.env missing - OPENAI_API_KEY will not be set"
    fi

    # set -m puts the background job in its own process group (pid == pgid),
    # so "stop" can signal uvicorn and every worker it spawned in one go.
    set -m
    ( cd "$BACKEND_DIR" && trap '' HUP && exec "$python_bin" -m uvicorn app.main:app \
        --host 0.0.0.0 --port "$BACKEND_PORT" ) \
        >>"$BACKEND_LOG" 2>&1 < /dev/null 9>&- &
    echo $! > "$BACKEND_PID_FILE"
    disown 2>/dev/null || true
    set +m

    sleep 2
    if pid="$(live_pid "$BACKEND_PID_FILE")"; then
        ok "Backend started (pid $pid) → http://localhost:$BACKEND_PORT"
    else
        err "Backend failed to start - see $BACKEND_LOG"
        tail -n 15 "$BACKEND_LOG" >&2
        return 1
    fi
}

start_frontend() {
    local pid
    if pid="$(live_pid "$FRONTEND_PID_FILE")"; then
        warn "Frontend already running (pid $pid) - not starting a second one"
        return 0
    fi
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        warn "frontend/node_modules missing - run 'npm install' in frontend/"
    fi

    set -m
    ( cd "$FRONTEND_DIR" && trap '' HUP && exec npm run dev -- --port "$FRONTEND_PORT" ) \
        >>"$FRONTEND_LOG" 2>&1 < /dev/null 9>&- &
    echo $! > "$FRONTEND_PID_FILE"
    disown 2>/dev/null || true
    set +m

    sleep 2
    if pid="$(live_pid "$FRONTEND_PID_FILE")"; then
        ok "Frontend started (pid $pid) → http://localhost:$FRONTEND_PORT"
    else
        err "Frontend failed to start - see $FRONTEND_LOG"
        tail -n 15 "$FRONTEND_LOG" >&2
        return 1
    fi
}

cmd_start() {
    printf '\nStarting AI Playbook...\n'
    start_backend  || return 1
    start_frontend || return 1
    printf '\n'
    ok "Ready - open http://localhost:$FRONTEND_PORT"
    info "Logs: $BACKEND_LOG | $FRONTEND_LOG"
    info "Stop with: ./app.sh stop"
    printf '\n'
}

cmd_stop() {
    printf '\nStopping AI Playbook...\n'
    stop_pid_file "Frontend" "$FRONTEND_PID_FILE"
    stop_pid_file "Backend"  "$BACKEND_PID_FILE"
    printf '\n'
}

cmd_status() {
    local pid
    printf '\nAI Playbook status\n'
    if pid="$(live_pid "$BACKEND_PID_FILE")"; then
        ok "Backend  running (pid $pid) → http://localhost:$BACKEND_PORT"
    else
        info "Backend  stopped"
    fi
    if pid="$(live_pid "$FRONTEND_PID_FILE")"; then
        ok "Frontend running (pid $pid) → http://localhost:$FRONTEND_PORT"
    else
        info "Frontend stopped"
    fi
    printf '\n'
}

usage() {
    cat <<EOF
Usage: ./app.sh {start|stop|restart|status}

  start     Start backend and frontend (refuses if already running)
  stop      Stop backend and frontend
  restart   Stop then start
  status    Show current state

Env overrides: BACKEND_PORT (default 8000), FRONTEND_PORT (default 5173)
EOF
}

acquire_lock

case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_stop; cmd_start ;;
    status)  cmd_status ;;
    ""|-h|--help|help) usage ;;
    *) err "Unknown command: $1"; usage; exit 1 ;;
esac
