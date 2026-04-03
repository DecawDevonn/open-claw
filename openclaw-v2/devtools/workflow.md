# OpenClaw v2 — Power Setup: Dev Workflow

This document describes the proposed developer workflow and the scripts included in `openclaw-v2/devtools`.

Workflow summary:

1. Reset context: `oc-plan`
2. Recon (read-only): Ask analysis prompts such as "Analyze vision/detector.py" or "Scan hardware layer"
3. Token audit: `oc-check`
4. Mega prompt: craft a single comprehensive request to the model
5. Clean reset: `/clear`

Files in this folder:
- `setup_claude.sh` — bootstrap claude CLI config and statusline
- `statusline.sh` — statusline helper script
- `aliases.sh` — shell alias helpers
