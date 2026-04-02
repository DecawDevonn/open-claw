#!/bin/bash
# openclaw_multi_channel_update.sh
# Multi-channel real-time alert system for OpenClaw updates.
# Supports Telegram, Slack, and Discord simultaneously.
# Monitors for new versions every CHECK_INTERVAL seconds and updates all nodes.
#
# Usage:
#   1. Fill in the configuration section below.
#   2. chmod +x openclaw_multi_channel_update.sh
#   3. sudo ./openclaw_multi_channel_update.sh
#      (run inside screen/tmux on a control node for persistence)

set -euo pipefail

# ===== CONFIGURATION =====
MAIN_NODE="gateway-main"
WORKER_NODES=("node1" "node2" "node3")
OPENCLAW_DIR="/root/.openclaw"
BACKUP_BASE="$HOME/openclaw_backups"
CHECK_INTERVAL=86400   # seconds between version checks (default: 24h)
SSH_USER="root"

# ===== TELEGRAM SETTINGS =====
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

# ===== SLACK SETTINGS =====
SLACK_WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"

# ===== DISCORD SETTINGS =====
DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"

# ===== NOTIFICATION FUNCTIONS =====
send_telegram() {
    local MESSAGE="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="$MESSAGE" > /dev/null
}

send_slack() {
    local MESSAGE="$1"
    curl -s -X POST "$SLACK_WEBHOOK_URL" -H 'Content-type: application/json' \
        -d "{\"text\":\"$MESSAGE\"}" > /dev/null
}

send_discord() {
    local MESSAGE="$1"
    curl -s -X POST "$DISCORD_WEBHOOK_URL" -H 'Content-type: application/json' \
        -d "{\"content\":\"$MESSAGE\"}" > /dev/null
}

notify_all() {
    local MESSAGE="$1"
    send_telegram "$MESSAGE"
    send_slack "$MESSAGE"
    send_discord "$MESSAGE"
}

# ===== BACKUP & UPDATE FUNCTIONS =====
backup_node() {
    local NODE="$1"
    local BACKUP_DIR="$BACKUP_BASE/${NODE}_$(date +%F_%H%M%S)"
    notify_all "🔹 [$NODE] Backing up memory and Skills..."
    ssh "${SSH_USER}@${NODE}" \
        "mkdir -p $BACKUP_DIR && \
         cp -r $OPENCLAW_DIR/memory $BACKUP_DIR/ && \
         cp -r $OPENCLAW_DIR/Skills $BACKUP_DIR/ && \
         tar -czvf $BACKUP_DIR/openclaw_full_backup.tar.gz $OPENCLAW_DIR > /dev/null"
    notify_all "✅ [$NODE] Backup complete: $BACKUP_DIR"
}

update_node() {
    local NODE="$1"
    {
        notify_all "🔹 [$NODE] Updating OpenClaw CLI..."
        ssh "${SSH_USER}@${NODE}" \
            "if command -v npm >/dev/null 2>&1; then \
                 npm install -g openclaw@latest; \
             else \
                 openclaw update --version 2026.4.1; \
             fi"
        notify_all "🔹 [$NODE] Running doctor to migrate config..."
        ssh "${SSH_USER}@${NODE}" "openclaw doctor --fix"
        notify_all "🔹 [$NODE] Restarting Gateway daemon..."
        ssh "${SSH_USER}@${NODE}" \
            "openclaw gateway stop || true && openclaw gateway start --daemon"
        notify_all "✅ [$NODE] Node update and restart complete!"
    } || {
        notify_all "⚠️ [$NODE] Node update FAILED! Check logs."
    }
}

# ===== VERSION CHECK =====
check_new_version() {
    LATEST=$(npm view openclaw version 2>/dev/null || echo "2026.4.1")
    CURRENT=$(openclaw --version 2>/dev/null || echo "none")
    if [ "$LATEST" != "$CURRENT" ]; then
        notify_all "🟢 New OpenClaw version detected: $LATEST (current: $CURRENT)"
        return 0
    else
        return 1
    fi
}

# ===== MAIN LOOP =====
notify_all "🚀 OpenClaw multi-node update monitor started (interval: ${CHECK_INTERVAL}s)"

while true; do
    if check_new_version; then
        notify_all "🔄 Starting multi-node OpenClaw update sequence..."

        # 1. Main node first
        backup_node "$MAIN_NODE"
        update_node "$MAIN_NODE"

        # 2. Worker nodes
        for NODE in "${WORKER_NODES[@]}"; do
            backup_node "$NODE"
            update_node "$NODE"
        done

        notify_all "🎯 Multi-node OpenClaw update sequence COMPLETED!"
    fi

    sleep "$CHECK_INTERVAL"
done
