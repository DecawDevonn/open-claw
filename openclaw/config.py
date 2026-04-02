"""Central configuration for Devonn.AI / OpenClaw.

All settings are read from environment variables (or a .env file loaded by
python-dotenv).  No secrets are hardcoded here; see .env.example for the full
list of supported variables.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional during bare test runs
    pass

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Single source of truth for every runtime configuration value."""

    # ── Flask core ────────────────────────────────────────────────────────────
    flask_env: str = field(default_factory=lambda: os.getenv("FLASK_ENV", "production"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "change-me-secret"))
    debug: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "False").lower() == "true")
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    api_version: str = field(default_factory=lambda: os.getenv("API_VERSION", "v1"))
    agent_heartbeat_interval: int = field(
        default_factory=lambda: int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30"))
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: Optional[str] = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_URL"))
    mongo_url: Optional[str] = field(default_factory=lambda: os.getenv("MONGO_URL"))
    pg_user: Optional[str] = field(default_factory=lambda: os.getenv("PG_USER"))
    pg_pass: Optional[str] = field(default_factory=lambda: os.getenv("PG_PASS"))
    pg_url: Optional[str] = field(default_factory=lambda: os.getenv("PG_URL"))

    # ── JWT / Auth ────────────────────────────────────────────────────────────
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-jwt"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expiry_hours: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    )
    oauth_client_id: Optional[str] = field(default_factory=lambda: os.getenv("OAUTH_CLIENT_ID"))
    oauth_client_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("OAUTH_CLIENT_SECRET")
    )
    encryption_key: Optional[str] = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY"))

    # ── AI / NLP ──────────────────────────────────────────────────────────────
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )
    openai_embedding_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    hf_api_token: Optional[str] = field(default_factory=lambda: os.getenv("HF_API_TOKEN"))
    hf_model: str = field(
        default_factory=lambda: os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    )
    stability_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("STABILITY_API_KEY")
    )
    deepl_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DEEPL_API_KEY"))

    # ── Voice ─────────────────────────────────────────────────────────────────
    elevenlabs_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ELEVENLABS_API_KEY")
    )
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    )
    assemblyai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ASSEMBLYAI_API_KEY")
    )
    youtube_api_key: Optional[str] = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY"))

    # ── Search / Vector DB ────────────────────────────────────────────────────
    pinecone_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("PINECONE_API_KEY")
    )
    pinecone_environment: str = field(
        default_factory=lambda: os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    )
    pinecone_index: str = field(
        default_factory=lambda: os.getenv("PINECONE_INDEX", "openclaw")
    )
    serpapi_key: Optional[str] = field(default_factory=lambda: os.getenv("SERPAPI_KEY"))
    apify_api_key: Optional[str] = field(default_factory=lambda: os.getenv("APIFY_API_KEY"))
    algolia_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ALGOLIA_API_KEY")
    )
    algolia_app_id: Optional[str] = field(default_factory=lambda: os.getenv("ALGOLIA_APP_ID"))

    # ── Data / Integrations ───────────────────────────────────────────────────
    airtable_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("AIRTABLE_API_KEY")
    )
    airtable_base_id: Optional[str] = field(
        default_factory=lambda: os.getenv("AIRTABLE_BASE_ID")
    )
    google_sheets_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_SHEETS_API_KEY")
    )

    # ── Automation / Webhooks ─────────────────────────────────────────────────
    pabbly_api_key: Optional[str] = field(default_factory=lambda: os.getenv("PABBLY_API_KEY"))
    electroneek_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ELECTRONEEK_API_KEY")
    )
    webhook_secret_key: Optional[str] = field(
        default_factory=lambda: os.getenv("WEBHOOK_SECRET_KEY")
    )
    integration_key: Optional[str] = field(
        default_factory=lambda: os.getenv("INTEGRATION_KEY")
    )
    ws_auth_token: Optional[str] = field(default_factory=lambda: os.getenv("WS_AUTH_TOKEN"))

    # ── Monitoring / CRM ──────────────────────────────────────────────────────
    sentry_dsn: Optional[str] = field(default_factory=lambda: os.getenv("SENTRY_DSN"))
    boostspace_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("BOOSTSPACE_API_KEY")
    )
    slack_webhook_url: Optional[str] = field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL")
    )

    # ── Notification channels (update monitor) ────────────────────────────────
    telegram_bot_token: Optional[str] = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN")
    )
    telegram_chat_id: Optional[str] = field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID")
    )
    discord_webhook_url: Optional[str] = field(
        default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL")
    )

    # ── Communications — Twilio ───────────────────────────────────────────────
    twilio_account_sid: Optional[str] = field(
        default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID")
    )
    twilio_auth_token: Optional[str] = field(
        default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN")
    )
    twilio_from_number: Optional[str] = field(
        default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER")
    )
    twilio_whatsapp_from: Optional[str] = field(
        default_factory=lambda: os.getenv("TWILIO_WHATSAPP_FROM")
    )

    # ── Communications — SendGrid ─────────────────────────────────────────────
    sendgrid_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("SENDGRID_API_KEY")
    )
    sendgrid_from_email: Optional[str] = field(
        default_factory=lambda: os.getenv("SENDGRID_FROM_EMAIL")
    )

    def configured_services(self) -> List[str]:
        """Return names of services that have API keys configured."""
        mapping = {
            "openai": self.openai_api_key,
            "huggingface": self.hf_api_token,
            "elevenlabs": self.elevenlabs_api_key,
            "assemblyai": self.assemblyai_api_key,
            "pinecone": self.pinecone_api_key,
            "serpapi": self.serpapi_key,
            "algolia": self.algolia_api_key,
            "stability": self.stability_api_key,
            "deepl": self.deepl_api_key,
            "airtable": self.airtable_api_key,
            "sentry": self.sentry_dsn,
            "twilio": self.twilio_account_sid,
            "sendgrid": self.sendgrid_api_key,
        }
        return [name for name, key in mapping.items() if key]

    def warn_insecure_defaults(self) -> None:
        """Log warnings for placeholder values that must be changed in production."""
        if self.secret_key == "change-me-secret":
            logger.warning(
                "SECRET_KEY is using the default value. "
                "Set a strong random value via the SECRET_KEY environment variable."
            )
        if self.jwt_secret == "change-me-jwt":
            logger.warning(
                "JWT_SECRET is using the default value. "
                "Set a strong random value via the JWT_SECRET environment variable."
            )


# Module-level singleton — import and use `settings` everywhere.
settings = Settings()
