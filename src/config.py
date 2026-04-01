import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class FortressConfig:
    enabled: bool = True
    sandbox_timeout: int = 30
    max_workers: int = 4
    allowed_commands: List[str] = field(default_factory=lambda: [
        "ls", "cat", "echo", "pwd", "git", "python", "pip", "pytest"
    ])
    data_dir: str = "/tmp/fortress"


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    TESTING = False
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/open-claw')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    FORTRESS = FortressConfig(
        enabled=os.environ.get('FORTRESS_ENABLED', 'true').lower() == 'true',
        sandbox_timeout=int(os.environ.get('FORTRESS_SANDBOX_TIMEOUT', '30')),
        max_workers=int(os.environ.get('FORTRESS_MAX_WORKERS', '4')),
        data_dir=os.environ.get('FORTRESS_DATA_DIR', '/tmp/fortress'),
    )


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
