# Contributing to AgentGuard

Thanks for your interest in contributing to AgentGuard.

## Getting Started

1. Fork the repo
2. Clone your fork
3. Create a virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
4. Run tests: `pytest tests/ -v`

## Development

- Code is in `src/agentguard/`
- Tests are in `tests/`
- Dashboard backend is in `dashboard/api/`
- Dashboard frontend is in `dashboard/frontend/`

## Adding a Validator

1. Create `src/agentguard/validators/your_validator.py`
2. Inherit from `BaseValidator`, implement `async def validate(self, action) -> ValidationResult`
3. Add tests in `tests/test_validators/test_your_validator.py`
4. Add YAML config support in `src/agentguard/config/loader.py`

## Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Run `pytest tests/ -v` before submitting
- Run `ruff check src/` for linting
