"""JWT authentication service + Flask ``require_auth`` decorator.

Provides:
  - ``AuthService.issue_token(user_id, extra_claims)`` → signed JWT string
  - ``AuthService.verify_token(token)`` → decoded claims dict
  - ``AuthService.revoke_token(token)`` → marks JTI as revoked in storage
  - ``require_auth`` decorator — validates Bearer token on protected routes
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

import jwt
from flask import current_app, g, jsonify, request

logger = logging.getLogger(__name__)


class AuthService:
    """Issues, verifies, and revokes JWT access tokens."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        expiry_hours: int = 24,
        storage=None,
    ) -> None:
        if not secret or secret == "change-me-jwt":
            logger.warning(
                "JWT_SECRET is using the default placeholder value. "
                "Set a strong random value via JWT_SECRET in production."
            )
        self._secret = secret
        self._algorithm = algorithm
        self._expiry_hours = expiry_hours
        self._storage = storage  # optional StorageBackend for token revocation

    # ── Issue ─────────────────────────────────────────────────────────────────

    def issue_token(self, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
        """Return a signed JWT for *user_id*."""
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(hours=self._expiry_hours),
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate *token*. Raises ``jwt.PyJWTError`` on failure."""
        claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        if self._storage and self._storage.is_token_revoked(claims.get("jti", "")):
            raise jwt.InvalidTokenError("Token has been revoked.")
        return claims

    # ── Revoke ────────────────────────────────────────────────────────────────

    def revoke_token(self, token: str) -> None:
        """Mark the token's JTI as revoked (requires a storage backend)."""
        if not self._storage:
            raise RuntimeError("A storage backend is required for token revocation.")
        claims = jwt.decode(
            token, self._secret, algorithms=[self._algorithm],
            options={"verify_exp": False},
        )
        self._storage.revoke_token(claims["jti"])


# ── Flask decorator ───────────────────────────────────────────────────────────

def require_auth(f: Callable) -> Callable:
    """Route decorator that enforces JWT Bearer authentication.

    On success the decoded claims are available as ``g.user``.
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header[len("Bearer "):]
        auth_service: Optional[AuthService] = current_app.extensions.get("auth_service")
        if auth_service is None:
            logger.error("AuthService not registered on Flask app.")
            return jsonify({"error": "Authentication not configured"}), 500
        try:
            g.user = auth_service.verify_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.PyJWTError as exc:
            return jsonify({"error": str(exc)}), 401
        return f(*args, **kwargs)
    return decorated
