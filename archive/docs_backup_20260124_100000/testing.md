# Testing Strategy

Audience: Developers.

## Backend (Engine)

We use `pytest` for testing the Python engine.

### Running Tests
```bash
pytest
```
Configuration is defined in `pytest.ini`.

Evidence: `pytest.ini`, `tests/` directory.

## Frontend (Web)

(Inferring standard Next.js testing)
Frontend testing is typically handled via Jest or Playwright (check `web/package.json` for details).

## Continuous Integration

Tests are run automatically on PRs via GitHub Actions.

Evidence: `.github/workflows/tests.yml`.
