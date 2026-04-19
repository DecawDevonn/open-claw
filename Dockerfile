# ============================================================
# Devonn.AI Backend — Production Dockerfile
# Base: python:3.13-slim (Debian Bookworm)
# Security: non-root user (uid 1000), no new privileges
# ============================================================
FROM python:3.13-slim

# Install only what's needed, then clean up in the same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies as root (before dropping privileges)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY storage/ storage/

# DocumentDB TLS CA bundle (required for MongoDB/DocumentDB TLS connections)
COPY global-bundle.pem /global-bundle.pem

# Create non-root user and set ownership
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser && \
    chown -R appuser:appgroup /app /global-bundle.pem

# Switch to non-root user
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8080/api/health || exit 1

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:application"]
