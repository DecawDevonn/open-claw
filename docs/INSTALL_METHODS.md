# Installation Methods

All supported ways to install OpenClaw.

---

## 1. pip (PyPI)

The simplest method for most users.

```bash
pip install open-claw
```

With optional MongoDB support:

```bash
pip install "open-claw[mongo]"
```

With development tools:

```bash
pip install "open-claw[dev]"
```

---

## 2. Docker

### Run directly

```bash
docker run -p 8080:8080 ghcr.io/decawdevonn/open-claw:latest
```

### Docker Compose (with MongoDB)

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
docker compose up -d
```

---

## 3. From Source

For contributors or those who want the latest unreleased features:

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\Activate.ps1   # Windows
pip install -e ".[dev]"
```

---

## 4. Quick Install Script

A convenience script that handles virtual environment creation and installation:

```bash
curl -fsSL https://raw.githubusercontent.com/DecawDevonn/open-claw/main/scripts/quick_install.sh | bash
```

Or download and inspect first (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/DecawDevonn/open-claw/main/scripts/quick_install.sh -o quick_install.sh
less quick_install.sh
bash quick_install.sh
```

---

## Verifying the Installation

```bash
curl http://localhost:8080/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000",
  "uptime": "running"
}
```

---

## Upgrading

```bash
# pip
pip install --upgrade open-claw

# Docker
docker pull ghcr.io/decawdevonn/open-claw:latest

# From source
git pull origin main
pip install -e ".[dev]"
```

See also: [scripts/upgrade.sh](../scripts/upgrade.sh)
