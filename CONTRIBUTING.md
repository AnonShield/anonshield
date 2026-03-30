# Contributing to AnonShield

Thank you for your interest in contributing. This document covers everything you need to get started: setting up the development environment, coding conventions, how to add new features, and the pull-request process.

---

## Table of Contents

1. [Development Setup](#1-development-setup)
2. [Project Structure](#2-project-structure)
3. [Coding Conventions](#3-coding-conventions)
4. [Running Tests](#4-running-tests)
5. [Adding New Features](#5-adding-new-features)
6. [Commit Message Convention](#6-commit-message-convention)
7. [Pull Request Process](#7-pull-request-process)
8. [Reporting Bugs](#8-reporting-bugs)
9. [License](#9-license)

---

## 1. Development Setup

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv), Git.

```bash
# Clone the repository
git clone https://github.com/AnonShield/tool.git
cd tool

# Install all dependencies using uv
uv sync

# Verify the CLI works
uv run anon.py --help
```

For GPU support, ensure CUDA 12.x drivers are installed. The `cupy-cuda12x` and `torch` packages are declared in `pyproject.toml` and installed automatically via `uv sync`.

Alternatively, use Docker (see `Makefile`):

```bash
make build       # CPU image
make build-gpu   # GPU image
make shell       # interactive shell inside container
```

---

## 2. Project Structure

```
anon.py                   # CLI entry point (composition root)
src/anon/                 # Core library
  core/protocols.py       # Protocol interfaces (EntityStorage, CacheStrategy, …)
  engine.py               # AnonymizationOrchestrator
  strategies.py           # Built-in anonymization strategies
  processors.py           # File-format processors
  entity_detector.py      # NER (spaCy + Transformers)
  slm/                    # Small Language Model integration
scripts/                  # Utility/analysis scripts
tests/                    # Test suite (unittest)
benchmark/                # Benchmarking suite
docs/developers/          # Developer documentation
examples/                 # Sample configs and documents
docker/                   # Dockerfile and docker-compose
```

See [docs/developers/ARCHITECTURE.md](docs/developers/ARCHITECTURE.md) for the full module map and data-flow diagram.

---

## 3. Coding Conventions

### Style

- **Naming conventions:** snake_case for functions/variables, PascalCase for classes, UPPER_CASE for module-level constants.
- **Line length:** keep lines under 100 characters.
- **Type annotations** on all public functions and methods (params and return type).
- **Docstrings** on all new public classes and methods; use the Google style (`Args:`, `Returns:`, `Raises:`) when the method has non-trivial parameters or return values.

### Patterns

Respect the established patterns — do not work around them:

| Pattern | Where |
|---|---|
| Strategy | `AnonymizationStrategy` ABC in `strategies.py` |
| Template Method | `FileProcessor` ABC in `processors.py` |
| Repository | `EntityRepository` in `repository.py` |
| Dependency Injection | `AnonymizationOrchestrator.__init__()` parameters |
| Protocol-based inversion | `src/anon/core/protocols.py` |

New extension points must follow these patterns. See [docs/developers/EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md) for worked examples for every extension point.

### Security

- Never hard-code secrets or PII in tests or examples.
- Supply the HMAC key via `ANON_SECRET_KEY` (value) or `ANON_SECRET_KEY_FILE` (path to a file containing the key); key loading is handled by `src/anon/security.py`.
- Avoid `eval`, `exec`, `subprocess` with user-controlled strings, and any form of shell injection.

---

## 4. Running Tests

Tests use Python's standard `unittest` library. Run them with:

```bash
# Run all tests
uv run python -m unittest discover -s tests/

# Run a specific test file
uv run python -m unittest tests.test_security
```

Inside Docker:

```bash
make test
```

**Requirements for new code:**

- Tests for all new public functions and classes.
- Tests for new file processors and strategies should use the sample files in `examples/`.

---

## 5. Adding New Features

The most common extension points are:

| What you want to add | Where to look |
|---|---|
| New anonymization strategy | [Section 2 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#2-anonymization-strategies) |
| New file format processor | [Section 3 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#3-file-processors) |
| New entity type / regex | [Section 4 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#4-entity-types-and-regex-patterns) |
| New transformer model | [Section 5 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#5-transformer-models) |
| Custom cache / hash / storage | [Sections 6–8 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#6-cache-backend) |
| New SLM backend | [Section 11 of EXTENSIBILITY.md](docs/developers/EXTENSIBILITY.md#11-slm-client) |

For larger changes (new strategies, new processors), open an issue first to discuss the approach before writing code.

---

## 6. Commit Message Convention

Use a short type prefix followed by a description:

```
<type>: <short description>
```

**Types:**

| Type | Use for |
|---|---|
| `feat` | New feature or extension point |
| `fix` | Bug fix |
| `perf` | Performance improvement |
| `refactor` | Code restructuring with no behaviour change |
| `test` | Adding or improving tests |
| `docs` | Documentation only |
| `chore` | Build, CI, dependency updates |

**Examples:**

```
feat: add ODS file processor

fix: handle empty text chunks in fallback path

docs: add worked example for custom SLM client
```

Keep the subject line under 72 characters. Use the commit body for motivation and context when needed.

---

## 7. Pull Request Process

1. **Branch** off `main` with a descriptive name: `feat/xml-streaming`, `fix/csv-empty-header`, `docs/slm-guide-update`.
2. **Write tests** that cover the change. All existing tests must continue to pass.
3. **Update documentation** — if you change a public interface or add an extension point, update the relevant file in `docs/developers/`.
4. **Open the PR** against `main`. Fill in the PR description:
   - What problem does this solve?
   - How was it tested?
   - Any breaking changes?

---

## 8. Reporting Bugs

Please include:

- AnonShield version / git commit hash.
- Python version and OS.
- Minimal command that reproduces the issue (redact any real PII from inputs).
- Full traceback or error output.
- Expected vs actual behaviour.

---

## 9. License

By contributing you agree that your contributions will be licensed under the [GNU General Public License v3.0](LICENSE) that covers this project.
