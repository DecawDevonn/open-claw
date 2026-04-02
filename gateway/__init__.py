"""OpenClaw gateway — routes inbound messages to the right agent."""

from .router import route_message
from .dispatcher import Dispatcher

__all__ = ["route_message", "Dispatcher"]
