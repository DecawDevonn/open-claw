#!/bin/bash
# openclaw_multi_channel_update.sh
# Multi-channel real-time alert system for OpenClaw updates.
# Supports Telegram, Slack, and Discord simultaneously.
# Monitors for new versions every CHECK_INTERVAL seconds and updates all nodes.
#
# Configuration:
#   All secrets are read from environment variables. The recommended approach
#   is to store them in /etc/openclaw/notify.env (mode 0600, owned by root):
#
#     TELEGRAM_BOT_TOKEN=...
#     TELEGRAM_CHAT_ID=...
#     SLACK_WEBHOOK_URL=...
#     DISCORD_WEBHOOK_URL=...
#
#   Any variable below can also be overridden by exporting it before running
#   the script, or via Environment= in the systemd unit.
#
# Usage:
#   1. Populate /etc/openclaw/notify.env with your credentials.
#   2. chmod +x openclaw_multi_channel_update.sh
#   3a. Run as a systemd service (recommended):
#         sudo cp scripts/openclaw-monitor.service /etc/systemd/system/
#         sudo systemctl daemon-reload
#         sudo systemctl enable --now openclaw-monitor
#   3b. Or run manually inside screen/tmux:
#         sudo ./openclaw_multi_channel_update.sh

set -euo pipefail

# ===== CONFIGURATION =====
# All values can be overridden via environment variables.
MAIN_NODE="${MAIN_NODE:-gateway-main}"
WORKER_NODES_CSV="${WORKER_NODES_CSV:-node1,node2,node3}"
IFS=',' read -ra WORKER_NODES <<< "$WORKER_NODES_CSV"
OPENCLAW_DIR="${OPENCLAW_DIR:-/opt/openclaw}"
BACKUP_BASE="${BACKUP_BASE:-$HOME/openclaw_backups}"
CHECK_INTERVAL="${CHECK_INTERVAL:-86400}"   # seconds between version checks (default: 24h)
SSH_USER="${SSH_USER:-deploy}"
LOG_FILE="${LOG_FILE:-/var/log/openclaw_update.log}"

# ===== NOTIFICATION CHANNEL TOGGLES =====
# Set to "false" to disable a channel (e.g. if you only use Slack).
NOTIFY_TELEGRAM="${NOTIFY_TELEGRAM:-true}"
NOTIFY_SLACK="${NOTIFY_SLACK:-true}"
NOTIFY_DISCORD="${NOTIFY_DISCORD:-true}"

# ===== LOAD CREDENTIALS FROM FILE =====
# Credentials are loaded from $OPENCLAW_ENV_FILE.
# The file must not be world-readable: chmod 0600 /etc/openclaw/notify.env
OPENCLAW_ENV_FILE="${OPENCLAW_ENV_FILE:-/etc/openclaw/notify.env}"
if [[ -f "$OPENCLAW_ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$OPENCLAW_ENV_FILE"
fi
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

# ===== LOGGING =====
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ===== STARTUP VALIDATION =====
validate_config() {
    local errors=0
    if [[ "$NOTIFY_TELEGRAM" == "true" ]]; then
        [[ -z "$TELEGRAM_BOT_TOKEN" ]] && { log "ERROR: TELEGRAM_BOT_TOKEN is not set."; errors=$((errors + 1)); }
        [[ -z "$TELEGRAM_CHAT_ID" ]]   && { log "ERROR: TELEGRAM_CHAT_ID is not set.";   errors=$((errors + 1)); }
    fi
    if [[ "$NOTIFY_SLACK" == "true" ]]; then
        [[ -z "$SLACK_WEBHOOK_URL" ]] && { log "ERROR: SLACK_WEBHOOK_URL is not set."; errors=$((errors + 1)); }
    fi
    if [[ "$NOTIFY_DISCORD" == "true" ]]; then
        [[ -z "$DISCORD_WEBHOOK_URL" ]] && { log "ERROR: DISCORD_WEBHOOK_URL is not set."; errors=$((errors + 1)); }
    fi
    if [[ "$errors" -gt 0 ]]; then
        log "ERROR: $errors configuration error(s). Populate $OPENCLAW_ENV_FILE or set NOTIFY_*=false to disable unused channels."
        exit 1
    fi
}

# ===== JSON HELPER =====
# Safely encodes a string as a JSON string value, preventing injection.
json_str() {
    python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$1"
}

# ===== SSH HELPER =====
ssh_run() {
    local NODE="$1"
    shift
    ssh \
        -o StrictHostKeyChecking=accept-new \
        -o ConnectTimeout=10 \
        -o BatchMode=yes \
        "${SSH_USER}@${NODE}" "$@"
}

# ===== NOTIFICATION FUNCTIONS =====
send_telegram() {
    local MESSAGE="$1"
    [[ "$NOTIFY_TELEGRAM" != "true" ]] && return 0
    curl -s --max-time 10 -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=${MESSAGE}" > /dev/null
}

send_slack() {
    local MESSAGE="$1"
    [[ "$NOTIFY_SLACK" != "true" ]] && return 0
    local PAYLOAD
    PAYLOAD="{\"text\":$(json_str "$MESSAGE")}"
    curl -s --max-time 10 -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-type: application/json' \
        -d "$PAYLOAD" > /dev/null
}

send_discord() {
    local MESSAGE="$1"
    [[ "$NOTIFY_DISCORD" != "true" ]] && return 0
    local PAYLOAD
    PAYLOAD="{\"content\":$(json_str "$MESSAGE")}"
    curl -s --max-time 10 -X POST "$DISCORD_WEBHOOK_URL" \
        -H 'Content-type: application/json' \
        -d "$PAYLOAD" > /dev/null
}

notify_all() {
    local MESSAGE="$1"
    log "$MESSAGE"
    send_telegram "$MESSAGE"
    send_slack "$MESSAGE"
    send_discord "$MESSAGE"
}

# ===== BACKUP FUNCTION =====
backup_node() {
    local NODE="$1"
    local BACKUP_DIR="$BACKUP_BASE/${NODE}_$(date +%F_%H%M%S)"
    notify_all "🔹 [$NODE] Backing up memory and Skills..."
    {
        ssh_run "$NODE" \
            "mkdir -p '$BACKUP_DIR' && \
             cp -r '$OPENCLAW_DIR/memory' '$BACKUP_DIR/' && \
             cp -r '$OPENCLAW_DIR/Skills' '$BACKUP_DIR/' && \
             tar -czf '$BACKUP_DIR/openclaw_full_backup.tar.gz' '$OPENCLAW_DIR'"
        notify_all "✅ [$NODE] Backup complete: $BACKUP_DIR"
    } || {
        notify_all "⚠️ [$NODE] Backup FAILED! Aborting update for this node."
        return 1
    }
}

# ===== UPDATE FUNCTION =====
update_node() {
    local NODE="$1"
    {
        notify_all "🔹 [$NODE] Updating OpenClaw CLI..."
        ssh_run "$NODE" \
            "if command -v npm >/dev/null 2>&1; then \
                 npm install -g openclaw@latest; \
             else \
                 openclaw update; \
             fi"
        notify_all "🔹 [$NODE] Running doctor to migrate config..."
        ssh_run "$NODE" "openclaw doctor --fix"
        notify_all "🔹 [$NODE] Restarting Gateway daemon..."
        ssh_run "$NODE" "openclaw gateway stop || true && openclaw gateway start --daemon"
        notify_all "✅ [$NODE] Node update and restart complete!"
    } || {
        notify_all "⚠️ [$NODE] Node update FAILED! Check $LOG_FILE on the control node."
        return 1
    }
}

# ===== UPDATE SEQUENCE (backup then update a single node) =====
update_sequence() {
    local NODE="$1"
    backup_node "$NODE" && update_node "$NODE"
}

# ===== VERSION CHECK =====
check_new_version() {
    local LATEST CURRENT
    LATEST=$(npm view openclaw version 2>/dev/null || echo "")
    CURRENT=$(openclaw --version 2>/dev/null || echo "none")
    if [[ -z "$LATEST" ]]; then
        log "⚠️  Could not determine latest OpenClaw version from npm registry. Skipping update check."
        return 1
    fi
    if [[ "$LATEST" != "$CURRENT" ]]; then
        notify_all "🟢 New OpenClaw version detected: $LATEST (current: $CURRENT)"
        return 0
    else
        return 1
    fi
}

# ===== ENTRY POINT =====
mkdir -p "$(dirname "$LOG_FILE")"
validate_config

notify_all "🚀 OpenClaw multi-node update monitor started (interval: ${CHECK_INTERVAL}s)"

CYCLE=0
while true; do
    CYCLE=$((CYCLE + 1))

    if check_new_version; then
        notify_all "🔄 Starting multi-node OpenClaw update sequence..."

        # 1. Main node first (must succeed before workers proceed)
        update_sequence "$MAIN_NODE"

        # 2. Worker nodes in parallel
        declare -A WORKER_PIDS=()
        for NODE in "${WORKER_NODES[@]}"; do
            update_sequence "$NODE" &
            WORKER_PIDS[$NODE]=$!
        done

        # Collect results from all worker jobs
        FAILED_NODES=()
        for NODE in "${!WORKER_PIDS[@]}"; do
            if ! wait "${WORKER_PIDS[$NODE]}"; then
                FAILED_NODES+=("$NODE")
            fi
        done

        if [[ "${#FAILED_NODES[@]}" -gt 0 ]]; then
            notify_all "⚠️ Update sequence completed with failures on: ${FAILED_NODES[*]}"
        else
            notify_all "🎯 Multi-node OpenClaw update sequence COMPLETED!"
        fi
    else
        # Heartbeat: confirm the monitor is alive even when no update is needed
        notify_all "💓 [Heartbeat] OpenClaw monitor is alive (cycle ${CYCLE}, no update needed)"
    fi

    sleep "$CHECK_INTERVAL"
done
