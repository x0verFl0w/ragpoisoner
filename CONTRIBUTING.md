# Contributing to ragpoisoner

Thank you for your interest in contributing to ragpoisoner.

## Code of conduct

Contributions must be oriented toward defensive security research, RAG system hardening,
and authorized red teaming. Do not contribute attack techniques intended for unauthorized use.

## How to contribute

### Reporting bugs

Open an issue with:
- Python version and OS
- Steps to reproduce
- Expected vs. actual behavior
- Full error traceback

### Suggesting features

Open an issue tagged `enhancement`. Describe:
- The RAG attack vector or defensive capability you want to add
- Why it's useful for authorized security testing

### Submitting code

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write code and tests
5. Run tests: `pytest tests/ -v`
6. Lint: `ruff check . && black --check .`
7. Open a pull request with a clear description

### Adding a new payload type

1. Add your template to `ragpoisoner/attacks/payload_templates.py`
2. Include `description`, `template`, `severity`, `required_params`, and `defaults`
3. Add a test in `tests/test_injector.py`

### Adding a new injection test

1. Add your test dict to `INJECTION_TEST_BATTERY` in `ragpoisoner/modules/instruction_tester.py`
2. Include `name`, `description`, `injection`, `success_marker`, and `severity`
3. Add a test case in `tests/test_instruction_tester.py`

### Adding a new stealth technique

1. Add a static method to `StealthEncoder` in `ragpoisoner/attacks/stealth.py`
2. Add detection logic to `detect_stealth_in_document`
3. Wire the new technique into the `inject` CLI command
4. Add tests in `tests/test_injector.py`

## Testing

```bash
# Run full test suite
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=ragpoisoner --cov-report=html
```

Tests that require Ollama are automatically skipped when Ollama is not available.
All unit tests use mocked RAG environments and do not require external services.

## Code style

- Format: `black` (line length 100)
- Lint: `ruff`
- Type hints on all public functions
- No comments unless the why is genuinely non-obvious

## Versioning

This project uses [Semantic Versioning](https://semver.org/).
