# syntax=docker/dockerfile:1

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

# Security: create non-root user
RUN groupadd -r openclaw && useradd -r -g openclaw -s /sbin/nologin openclaw

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app.py .
COPY openclaw/ ./openclaw/
COPY storage/ ./storage/

# Set ownership
RUN chown -R openclaw:openclaw /app

# Switch to non-root user
USER openclaw

# Environment defaults
ENV FLASK_ENV=production \
    PORT=8080 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

CMD ["python", "app.py"]
