"""OpenClaw runtime configuration — loaded once at startup from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """All runtime configuration values for the OpenClaw multi-agent system.

    Values are read from environment variables with sensible defaults.
    Never hardcode secrets — always use the environment.
    """

    # ── Flask / server ─────────────────────────────────────────────────
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "change-me-secret"))
    debug: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "False").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    # ── JWT ────────────────────────────────────────────────────────────
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-jwt"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expiry_hours: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "24")))

    # ── Redis / queues ─────────────────────────────────────────────────
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    queue_channel: str = field(default_factory=lambda: os.getenv("QUEUE_CHANNEL", "openclaw:messages"))

    # ── OpenAI ─────────────────────────────────────────────────────────
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_embedding_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )

    # ── MongoDB ────────────────────────────────────────────────────────
    mongo_url: str = field(default_factory=lambda: os.getenv("MONGO_URL", ""))

    # ── Sapphire / ChromaDB ────────────────────────────────────────────
    chroma_persist_dir: str = field(
        default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./chroma_memory")
    )
    chroma_collection: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION", "sapphire")
    )

    # ── Telegram ───────────────────────────────────────────────────────
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # ── Slack ──────────────────────────────────────────────────────────
    slack_webhook_url: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    slack_signing_secret: str = field(default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", ""))

    # ── SendGrid ───────────────────────────────────────────────────────
    sendgrid_api_key: str = field(default_factory=lambda: os.getenv("SENDGRID_API_KEY", ""))
    sendgrid_from_email: str = field(default_factory=lambda: os.getenv("SENDGRID_FROM_EMAIL", ""))

    # ── Twilio ─────────────────────────────────────────────────────────
    twilio_account_sid: str = field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", ""))
    twilio_from_number: str = field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER", ""))

    # ── AssemblyAI ─────────────────────────────────────────────────────
    assemblyai_api_key: str = field(default_factory=lambda: os.getenv("ASSEMBLYAI_API_KEY", ""))

    # ── Heartbeat / cron ───────────────────────────────────────────────
    heartbeat_interval: float = field(
        default_factory=lambda: float(os.getenv("AGENT_HEARTBEAT_INTERVAL", "60"))
    )

    # ── Sentry ─────────────────────────────────────────────────────────
    sentry_dsn: str = field(default_factory=lambda: os.getenv("SENTRY_DSN", ""))

    def warn_insecure_defaults(self) -> None:
        """Log warnings for any placeholder credentials detected at startup."""
        import logging
        log = logging.getLogger("openclaw.config")
        if self.secret_key == "change-me-secret":
            log.warning("SECRET_KEY is using the insecure default — set a strong value in .env")
        if self.jwt_secret == "change-me-jwt":
            log.warning("JWT_SECRET is using the insecure default — set a strong value in .env")


_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Return the singleton :class:`Settings` instance (created lazily)."""
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
