# Changelog

All notable changes to OpenClaw are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Sapphire Cognitive Memory** (`openclaw/services/sapphire.py`): persistent ChromaDB-backed
  vector store implementing the Sapphire Protocol — save, search, inject, reflect, delete, list
- **`AIService.chat()`** — Cognitive Wrapper that retrieves relevant memories, injects them into
  the system prompt, calls the LLM, and saves the response back to memory; configurable via
  `save_response` and `memory_format` parameters
- **`save_to_memory` agent tool** registered in `ToolRegistry` with full OpenAI function-calling
  JSON Schema; agents can call it by name during any task execution
- **New API routes**: `POST /api/ai/chat`, `POST /api/memory/save`,
  `POST /api/memory/search`, `GET /api/memory/list`, `POST /api/memory/reflect`,
  `DELETE /api/memory/<id>`
- **`agents/devonn/memory.md`**: Sapphire memory structure documentation — schema, retrieval
  protocol, self-reflection loop, API reference, and configuration table
- **Sapphire env vars** added to `.env.example`: `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION`,
  `SAPPHIRE_MEMORY_TOP_K`, `SAPPHIRE_REFLECTION_INTERVAL`
- **`memory` optional dependency group** in `pyproject.toml` and `setup.py` (`chromadb>=1.0.0`)
- **32 new tests** in `tests/test_sapphire.py` covering the memory service, tool, Cognitive
  Wrapper, and all new endpoints (126 tests total)
- **`docs/QUICKSTART.md`**: replaced Node.js placeholder with full Python/Flask quickstart
- **`docs/API.md`**: complete API reference for all ~50 endpoints replacing the generic placeholder
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
