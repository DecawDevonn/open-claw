# Development

Local development

Prerequisites: Python 3.11 (recommended), Docker (optional), docker-compose (optional).

- Create and activate a virtual environment:

  python -m venv .venv
  source .venv/bin/activate

- Install dependencies:

  pip install -r requirements.txt

- Create .env from example and edit as needed:

  cp .env.example .env

- Run locally:

  python app.py

- Run with Docker:

  docker build -t open-claw .
  docker run --env-file .env -p 8080:8080 open-claw

Docker Compose (Postgres + Redis)

If you plan to use docker-compose (included in this repo) ensure requirements include the db and redis client libraries. Start with:

  docker-compose up --build

Testing

- Run unit tests:

  pytest

Adding CI

- Add a CI workflow (GitHub Actions) to run pytest on push/PR with Python 3.11, and add linting (ruff/flake8) and type checks (mypy) as desired.

Contribution checklist

- Add tests for new features
- Follow code style
- Update README and docs
