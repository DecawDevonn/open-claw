# open-claw
ai agent workforce system

Open Claw is a lightweight workforce orchestration API (agents + tasks). This repository contains a minimal Flask-based API and development helpers for running locally and in Docker.

Quick start

- Clone the repo:

  git clone https://github.com/DecawDevonn/open-claw.git
  cd open-claw

- Create environment:

  cp .env.example .env
  # Edit .env and set SECRET_KEY and any DB/Redis URLs you need.

- Install (local):

  python -m venv .venv
  source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
  pip install -r requirements.txt

- Run:

  python app.py

  The API will listen on 0.0.0.0:8080 by default. See .env.example for configurable values.

Run with Docker

- Build and run single container:

  docker build -t open-claw .
  docker run --env-file .env -p 8080:8080 open-claw

- Run with docker-compose (development with Postgres and Redis):

  docker-compose up --build

Development

- Run locally with Python (see Quick start).
- Run tests:

  pytest

Configuration

- Copy .env.example to .env and update the SECRET_KEY, DATABASE_URL, and REDIS_URL as needed.

Notes

- Official getting started and onboarding docs: https://docs.openclaw.ai/start/getting-started
- docker-compose in this repository has been updated to map the web service to port 8080 to match the Flask app default.
- setup.py was updated to include realistic install_requires but does not add a console entry point (this repo runs as a module/script).

Contributing

See CONTRIBUTING.md for contribution guidelines.
