# Changelog

All notable changes to OpenClaw are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Multi-stage Dockerfile with non-root runtime user
- `.dockerignore` to minimize image build context
- GitHub Actions workflows: CI, PyPI publish, Docker publish
- `pyproject.toml` with full project metadata
- `MANIFEST.in` for source distribution
- `openclaw/` Python package with version metadata
- Comprehensive documentation: INSTALLATION, PRODUCTION_DEPLOYMENT, TROUBLESHOOTING, ARCHITECTURE, INSTALL_METHODS
- Eight utility shell scripts in `scripts/`
- `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `RELEASE_TEMPLATE.md`

### Fixed
- `app.py`: Replaced escaped-newline single-line file with proper Python using `create_app()` factory pattern
- `docker-compose.yml`: Fixed escaped newlines; updated to use MongoDB instead of PostgreSQL/Redis
- `storage/mongo.py`: Fixed escaped newlines; restored proper Python formatting
- `tests/test_api.py`: Replaced single broken test with 9 comprehensive pytest tests

### Changed
- `Dockerfile`: Upgraded to multi-stage build with security hardening
- `docs/ARCHITECTURE.md`: Rewrote to accurately reflect the Python/Flask/MongoDB stack

---

## [0.1.0] - 2024-01-01

### Added
- Initial Flask REST API with agent and task management
- In-memory storage backend
- MongoDB storage backend (`storage/mongo.py`)
- Health and status endpoints
- Workforce assignment and summary endpoints
- Basic Dockerfile and docker-compose configuration
- `setup.py` and `requirements.txt`
