# Contributing to OpenClaw

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/open-claw.git`
3. **Create a branch**: `git checkout -b feat/your-feature-name`
4. **Set up the development environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install flask pytest pytest-cov flake8
   ```
5. **Make your changes** — see guidelines below
6. **Run tests**: `pytest tests/ -v`
7. **Lint**: `flake8 app.py openclaw/ --max-line-length=120`
8. **Commit** with a clear message: `git commit -m "feat: add XYZ endpoint"`
9. **Push**: `git push origin feat/your-feature-name`
10. **Open a Pull Request** against `main`

## Contribution Guidelines

- **Tests**: Add or update tests for every change. All tests must pass.
- **Style**: Follow PEP 8. Max line length is 120 characters.
- **Docstrings**: Document public functions with a one-line description.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).
- **Breaking changes**: Discuss in an issue before implementing.

## Reporting Issues

Please use [GitHub Issues](https://github.com/DecawDevonn/open-claw/issues) and include:

- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Questions?

Open a [GitHub Discussion](https://github.com/DecawDevonn/open-claw/discussions) or email **contact@openclaw.dev**.
