# Update Monitor — scripts/openclaw_multi_channel_update.sh

A daemon that polls npm for new OpenClaw releases and orchestrates a safe,
multi-node backup-and-upgrade sequence with real-time notifications sent
simultaneously to Telegram, Slack, and Discord.

---

## How It Works

1. **Version poll** — runs `npm view openclaw version` on the control node
   every `CHECK_INTERVAL` seconds (default: 24 h).
2. **Main-node first** — backs up then upgrades the gateway node before touching
   any workers, preventing a split-brain scenario.
3. **Parallel worker updates** — all worker nodes are backed up and upgraded
   concurrently; per-node failures are collected and reported without blocking
   the other workers.
4. **Heartbeat** — when no update is needed the monitor still notifies all
   channels so you can detect a silent crash.

---

## Prerequisites

| Tool | Purpose |
|---|---|
| `bash` ≥ 4.0 | Associative arrays for parallel job tracking |
| `curl` | Sending webhook notifications |
| `python3` | Safe JSON serialisation of notification messages |
| `npm` | Version check against the npm registry |
| `ssh` (key auth) | Connecting to remote nodes |
| `openclaw` CLI | Running `doctor` and `gateway` commands on each node |

---

## Configuration

All configuration is driven by environment variables — no secrets are
hardcoded in the script.

### Credentials file (recommended)

Create `/etc/openclaw/notify.env` on the **control node** and restrict its
permissions so that only root can read it:

```bash
sudo install -m 0600 /dev/null /etc/openclaw/notify.env
```

Populate it with your credentials (see `.env.example` for a full template):

```bash
NOTIFY_TELEGRAM=true
TELEGRAM_BOT_TOKEN=1234567890:ABCDEfghijklmnopqrstuvwxyz
TELEGRAM_CHAT_ID=-100123456789

NOTIFY_SLACK=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

NOTIFY_DISCORD=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/XXX/YYY
```

Set `NOTIFY_TELEGRAM=false` (or the equivalent for Slack/Discord) to disable
channels you are not using.

### All available variables

| Variable | Default | Description |
|---|---|---|
| `MAIN_NODE` | `gateway-main` | Hostname of the primary gateway node |
| `WORKER_NODES_CSV` | `node1,node2,node3` | Comma-separated list of worker hostnames |
| `OPENCLAW_DIR` | `/opt/openclaw` | Path to the OpenClaw data directory on each node |
| `BACKUP_BASE` | `$HOME/openclaw_backups` | Directory where backups are stored on each node |
| `CHECK_INTERVAL` | `86400` | Seconds between version polls (default: 24 h) |
| `SSH_USER` | `deploy` | SSH user used to connect to remote nodes |
| `LOG_FILE` | `/var/log/openclaw_update.log` | Path to the persistent log file on the control node |
| `NOTIFY_TELEGRAM` | `true` | Set to `false` to disable Telegram |
| `NOTIFY_SLACK` | `true` | Set to `false` to disable Slack |
| `NOTIFY_DISCORD` | `true` | Set to `false` to disable Discord |
| `TELEGRAM_BOT_TOKEN` | *(required if Telegram on)* | Bot API token |
| `TELEGRAM_CHAT_ID` | *(required if Telegram on)* | Target chat/channel ID |
| `SLACK_WEBHOOK_URL` | *(required if Slack on)* | Incoming Webhook URL |
| `DISCORD_WEBHOOK_URL` | *(required if Discord on)* | Webhook URL |
| `OPENCLAW_ENV_FILE` | `/etc/openclaw/notify.env` | Path to the credentials file |

---

## SSH Key Setup

The script connects to every node as `SSH_USER` (default: `deploy`) using
key-based authentication. No passwords are supported (`BatchMode=yes`).

1. Create a dedicated deploy user on each remote node:
   ```bash
   sudo useradd -m -s /bin/bash deploy
   ```
2. Add your control-node's public key:
   ```bash
   sudo -u deploy mkdir -p /home/deploy/.ssh
   echo "<your-public-key>" | sudo tee /home/deploy/.ssh/authorized_keys
   sudo chmod 700 /home/deploy/.ssh && sudo chmod 600 /home/deploy/.ssh/authorized_keys
   ```
3. Grant the deploy user permission to run the required `openclaw` and `npm`
   commands via `sudo` (or ensure the commands are on its `PATH`).

---

## Running as a systemd Service (Recommended)

Using systemd ensures the monitor auto-restarts on failure and survives reboots.

```bash
# 1. Install the script
sudo install -m 0755 scripts/openclaw_multi_channel_update.sh \
    /opt/openclaw/scripts/openclaw_multi_channel_update.sh

# 2. Install the unit
sudo cp scripts/openclaw-monitor.service /etc/systemd/system/

# 3. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-monitor

# 4. Check status / follow logs
sudo systemctl status openclaw-monitor
sudo journalctl -u openclaw-monitor -f
tail -f /var/log/openclaw_update.log
```

---

## Running Manually (screen / tmux)

```bash
sudo ./scripts/openclaw_multi_channel_update.sh
```

Run inside `screen` or `tmux` on the control node if you prefer not to use
systemd.

---

## Notification Reference

| Emoji | Meaning |
|---|---|
| 🚀 | Monitor started |
| 💓 | Heartbeat — monitor is alive, no update this cycle |
| 🟢 | New version detected |
| 🔄 | Update sequence starting |
| 🔹 | Progress step |
| ✅ | Step/node succeeded |
| ⚠️ | Step/node failed |
| 🎯 | Full update sequence completed successfully |
