# Production Deployment Guide

This guide covers deploying OpenClaw in a hardened production environment.

---

## Security Hardening Checklist

- [ ] Set a strong `SECRET_KEY` environment variable
- [ ] Run behind a reverse proxy (nginx/Caddy)
- [ ] Enable HTTPS/TLS with a valid certificate
- [ ] Use a non-root OS user to run the process
- [ ] Restrict firewall to only expose ports 80/443
- [ ] Enable log rotation and monitoring
- [ ] Use MongoDB authentication in production

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask secret key — **must be changed** |
| `MONGO_URI` | `mongodb://mongo:27017/openclaw` | MongoDB connection URI |
| `FLASK_ENV` | `production` | Flask environment |
| `PORT` | `8080` | Application port |

Set these in `/etc/openclaw.env` (owner `root`, mode `0600`):

```bash
SECRET_KEY=your-very-long-random-secret-key
MONGO_URI=mongodb://openclaw_user:password@127.0.0.1:27017/openclaw
FLASK_ENV=production
PORT=8080
```

Generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/DecawDevonn/open-claw.git
cd open-claw

# Set environment variables
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Start services
docker compose up -d

# Check status
docker compose ps
docker compose logs -f web
```

---

## systemd Service

Create `/etc/systemd/system/openclaw.service`:

```ini
[Unit]
Description=OpenClaw AI Agent Workforce API
After=network.target mongod.service

[Service]
Type=simple
User=openclaw
Group=openclaw
WorkingDirectory=/opt/openclaw
EnvironmentFile=/etc/openclaw.env
ExecStart=/opt/openclaw/.venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8080 \
    --timeout 120 \
    --access-logfile /var/log/openclaw/access.log \
    --error-logfile /var/log/openclaw/error.log \
    "app:create_app()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw
sudo journalctl -u openclaw -f
```

---

## nginx Reverse Proxy

Install nginx and create `/etc/nginx/sites-available/openclaw`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/openclaw /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### SSL/TLS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## Monitoring

### Health Check

```bash
curl https://api.yourdomain.com/api/health
```

### Log Rotation

Create `/etc/logrotate.d/openclaw`:

```
/var/log/openclaw/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload openclaw
    endscript
}
```

---

## Scaling

For high-traffic deployments, increase gunicorn workers:

```bash
# Rule of thumb: (2 × CPU cores) + 1
gunicorn --workers 9 --bind 0.0.0.0:8080 "app:create_app()"
```

Use a load balancer (nginx upstream or cloud LB) to distribute across multiple instances.
