"""OpenClaw channel adapters — one per inbound message source."""

from .telegram_channel import TelegramChannel
from .slack_channel import SlackChannel
from .web_channel import WebChannel
from .voice_channel import VoiceChannel

__all__ = ["TelegramChannel", "SlackChannel", "WebChannel", "VoiceChannel"]
