"""Delivery formatters — transform agent output for different channels."""

from __future__ import annotations

import re
from typing import Any


def format_response(response: Any, source: str = "default") -> str:
    """Format an agent's raw response for delivery on *source*.

    Applies channel-specific formatting rules:

    * ``"telegram"``  — passes Markdown through unchanged (Telegram renders it).
    * ``"slack"``     — converts ``**bold**`` to ``*bold*`` (Slack mrkdwn).
    * ``"web"``       — returns the response as-is (HTML is handled client-side).
    * ``"voice"``     — strips all Markdown so TTS reads clean prose.
    * anything else   — returns the plain-text representation.

    Args:
        response: The agent's reply (any type — will be coerced to ``str``).
        source:   Channel name to format for.

    Returns:
        A formatted string ready for delivery.
    """
    text = str(response) if not isinstance(response, str) else response

    formatters = {
        "telegram": _format_telegram,
        "slack": _format_slack,
        "web": _format_web,
        "voice": _format_voice,
    }

    formatter = formatters.get(source.lower(), _format_plain)
    return formatter(text)


# ── Channel-specific formatters ───────────────────────────────────────────────

def _format_telegram(text: str) -> str:
    """Telegram supports MarkdownV2 — pass through with light sanitisation."""
    return text.strip()


def _format_slack(text: str) -> str:
    """Convert Markdown bold/italic to Slack mrkdwn syntax."""
    # **bold** → *bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # _italic_ remains the same in Slack mrkdwn
    # `code` remains the same
    return text.strip()


def _format_web(text: str) -> str:
    """Web channel — return as-is; the frontend handles rendering."""
    return text.strip()


def _format_voice(text: str) -> str:
    """Strip all Markdown so TTS engines read clean prose."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    # Remove Markdown links: [text](url) → text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Remove heading markers
    text = re.sub(r"#{1,6}\s*", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _format_plain(text: str) -> str:
    """Fallback: strip Markdown, return plain text."""
    return _format_voice(text)
