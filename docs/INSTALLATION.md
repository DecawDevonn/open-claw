# Installation Guide

This guide covers all methods to install and run OpenClaw on your system.

## Requirements

- Python 3.10 or higher
- pip (Python package manager)
- Docker (optional, for containerized deployment)
- Git (for source installation)

---

## macOS

### Using pip (recommended)

```bash
# Install Python if needed
brew install python@3.11

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install OpenClaw
pip install open-claw

# Verify installation
python -c "import openclaw; print(openclaw.__version__)"
```

### Using Docker

```bash
# Pull and run the latest image
docker pull ghcr.io/decawdevonn/open-claw:latest
docker run -p 8080:8080 ghcr.io/decawdevonn/open-claw:latest
```

### From Source

```bash
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Linux (Ubuntu/Debian)

```bash
# Update package list and install Python
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install OpenClaw
pip install open-claw

# Start the server
python -m app
```

### Running as a systemd service

```bash
sudo cp scripts/openclaw.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw
sudo systemctl status openclaw
```

---

## Windows

### Using pip

Open PowerShell as Administrator:

```powershell
# Install Python from https://python.org if not already installed

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install OpenClaw
pip install open-claw
```

### Using Docker Desktop

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Open PowerShell and run:

```powershell
docker pull ghcr.io/decawdevonn/open-claw:latest
docker run -p 8080:8080 ghcr.io/decawdevonn/open-claw:latest
```

---

## Verifying the Installation

After installation, verify the server is responding:

```bash
curl http://localhost:8080/api/health
# Expected: {"status": "healthy", ...}
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'flask'`

You may not be inside the virtual environment. Run:

```bash
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\Activate.ps1  # Windows
```

### Port 8080 already in use

```bash
# Find the process using port 8080
lsof -i :8080        # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill it or choose a different port:
PORT=9090 python app.py
```

### Permission denied errors

On Linux, if you see permission errors installing globally:

```bash
# Always prefer virtual environments
python3 -m venv .venv && source .venv/bin/activate
pip install open-claw
```

---

## Next Steps

- Read the [Quickstart Guide](../README.md)
- Learn about [Production Deployment](PRODUCTION_DEPLOYMENT.md)
- Explore the [API Architecture](ARCHITECTURE.md)
