# Troubleshooting Guide

Solutions to common issues encountered when running OpenClaw.

---

## Server Won't Start

### SyntaxError or ImportError

```
SyntaxError: invalid syntax
```

Ensure you are using Python 3.10+:

```bash
python3 --version
# Should be Python 3.10.x or higher
```

Reinstall dependencies:

```bash
pip install --upgrade -r requirements.txt
```

### Address already in use

```
OSError: [Errno 98] Address already in use
```

Find and stop the conflicting process:

```bash
# Find what is using port 8080
lsof -i :8080
# Kill by PID
kill <PID>
```

Or change the port:

```bash
PORT=9090 python app.py
```

---

## Connection Problems

### `curl: (7) Failed to connect`

1. Confirm the server is running: `ps aux | grep app.py`
2. Check the correct port: default is `8080`
3. Ensure the firewall allows the port:
   ```bash
   sudo ufw allow 8080/tcp
   ```

### Docker container unreachable

Verify the port binding:

```bash
docker ps
# Should show: 0.0.0.0:8080->8080/tcp
```

If missing, re-run with explicit port mapping:

```bash
docker run -p 8080:8080 ghcr.io/decawdevonn/open-claw:latest
```

---

## API Errors

### 404 Not Found

Check that you are using the correct base path `/api/`:

```bash
# Wrong
curl http://localhost:8080/agents

# Correct
curl http://localhost:8080/api/agents
```

### 400 Bad Request

Ensure you are sending `Content-Type: application/json`:

```bash
curl -X POST http://localhost:8080/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "MyAgent"}'
```

### 500 Internal Server Error

Check the application logs for the full traceback:

```bash
# Docker
docker compose logs web

# systemd
journalctl -u openclaw -n 100
```

---

## MongoDB Issues

### `ServerSelectionTimeoutError`

The app cannot connect to MongoDB. Verify MongoDB is running:

```bash
# Docker Compose
docker compose ps mongo

# Local service
systemctl status mongod
```

Check the `MONGO_URI` environment variable is correct:

```bash
echo $MONGO_URI
# Should be: mongodb://host:27017/openclaw
```

### Authentication failure

If MongoDB is configured with authentication:

```bash
export MONGO_URI="mongodb://username:password@localhost:27017/openclaw?authSource=admin"
```

---

## Performance Issues

### Slow API responses

1. Check the number of gunicorn workers (should be `2 × CPU + 1`)
2. Review MongoDB indexes — add indexes on frequently queried fields:
   ```javascript
   db.agents.createIndex({ "id": 1 }, { unique: true })
   db.tasks.createIndex({ "agent_id": 1 })
   db.tasks.createIndex({ "status": 1 })
   ```
3. Enable connection pooling in the MongoDB URI:
   ```
   mongodb://host:27017/openclaw?maxPoolSize=50
   ```

---

## Log Analysis

### View live logs

```bash
# Docker Compose
docker compose logs -f web

# systemd
journalctl -u openclaw -f

# File-based logs
tail -f /var/log/openclaw/error.log
```

### Find errors in logs

```bash
grep -i "error\|exception\|traceback" /var/log/openclaw/error.log
```

---

## Getting Help

If the issue persists after following these steps:

1. Search [existing issues](https://github.com/DecawDevonn/open-claw/issues)
2. Open a new issue with:
   - Python version (`python3 --version`)
   - OpenClaw version
   - Full error message and traceback
   - Steps to reproduce
