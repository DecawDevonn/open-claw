"""
config.py - Configuration manager for OpenClaw client.

Loads settings from environment variables (.env file) and
~/.openclaw/config.json, with profile support (dev/staging/prod).
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from pydantic import BaseModel, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

_CONFIG_DIR = Path.home() / '.openclaw'
_CONFIG_FILE = _CONFIG_DIR / 'config.json'

DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    'dev': {
        'base_url': 'http://localhost:8080',
        'timeout': 30,
        'verify_ssl': False,
    },
    'staging': {
        'base_url': 'https://staging.openclaw.example.com',
        'timeout': 60,
        'verify_ssl': True,
    },
    'prod': {
        'base_url': 'https://api.openclaw.example.com',
        'timeout': 60,
        'verify_ssl': True,
    },
}


class OpenClawConfig:
    """Manages OpenClaw client configuration."""

    def __init__(self, profile: Optional[str] = None) -> None:
        self._profile = profile or os.environ.get('OPENCLAW_PROFILE', 'dev')
        self._file_config: Dict[str, Any] = self._load_file_config()
        self._env_config: Dict[str, Any] = self._load_env_config()

    def _load_file_config(self) -> Dict[str, Any]:
        if not _CONFIG_FILE.exists():
            return {}
        try:
            with open(_CONFIG_FILE) as f:
                data = json.load(f)
            return data.get(self._profile, data)
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_env_config(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        if os.environ.get('OPENCLAW_BASE_URL'):
            cfg['base_url'] = os.environ['OPENCLAW_BASE_URL']
        if os.environ.get('OPENCLAW_API_KEY'):
            cfg['api_key'] = os.environ['OPENCLAW_API_KEY']
        if os.environ.get('OPENCLAW_TIMEOUT'):
            try:
                cfg['timeout'] = int(os.environ['OPENCLAW_TIMEOUT'])
            except ValueError:
                pass
        if os.environ.get('OPENCLAW_VERIFY_SSL'):
            cfg['verify_ssl'] = os.environ['OPENCLAW_VERIFY_SSL'].lower() not in ('0', 'false', 'no')
        return cfg

    def _get(self, key: str, default: Any = None) -> Any:
        """Retrieve a config value with env > file > profile defaults."""
        if key in self._env_config:
            return self._env_config[key]
        if key in self._file_config:
            return self._file_config[key]
        profile_defaults = DEFAULT_PROFILES.get(self._profile, DEFAULT_PROFILES['dev'])
        return profile_defaults.get(key, default)

    @property
    def base_url(self) -> str:
        return self._get('base_url', 'http://localhost:8080').rstrip('/')

    @property
    def api_key(self) -> Optional[str]:
        return self._get('api_key')

    @property
    def timeout(self) -> int:
        return int(self._get('timeout', 30))

    @property
    def verify_ssl(self) -> bool:
        return bool(self._get('verify_ssl', False))

    @property
    def profile(self) -> str:
        return self._profile

    def save(self, key: str, value: Any) -> None:
        """Persist a value to ~/.openclaw/config.json under the current profile."""
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        existing: Dict[str, Any] = {}
        if _CONFIG_FILE.exists():
            try:
                with open(_CONFIG_FILE) as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        if self._profile not in existing:
            existing[self._profile] = {}
        existing[self._profile][key] = value
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(existing, f, indent=2)

    def as_dict(self) -> Dict[str, Any]:
        return {
            'profile': self._profile,
            'base_url': self.base_url,
            'api_key': '***' if self.api_key else None,
            'timeout': self.timeout,
            'verify_ssl': self.verify_ssl,
        }


def get_config(profile: Optional[str] = None) -> OpenClawConfig:
    """Return a configuration object for the given profile."""
    return OpenClawConfig(profile=profile)
