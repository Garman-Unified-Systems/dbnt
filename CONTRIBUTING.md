# Contributing to DBNT

Thanks for your interest in making AI systems learn better.

## Development Setup

```bash
git clone https://github.com/Garman-Unified-Systems/dbnt
cd dbnt
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=dbnt  # with coverage
```

## Code Style

We use ruff for linting and formatting:

```bash
ruff check src tests
ruff format src tests
```

## Adding an Adapter

1. Create `src/dbnt/adapters/your_adapter.py`
2. Extend `BaseAdapter`
3. Register in `pyproject.toml` entry points
4. Add tests in `tests/test_adapters/`

Example adapter skeleton:

```python
from dbnt.adapters.base import BaseAdapter

class YourAdapter(BaseAdapter):
    def install(self) -> None:
        """Install DBNT hooks/integration."""
        pass

    def uninstall(self) -> None:
        """Remove DBNT from system."""
        pass

    def get_rules_path(self) -> Path:
        """Where rules are stored."""
        pass

    def sync_rule(self, rule: Rule) -> None:
        """Convert and save rule in system's format."""
        pass

    def is_installed(self) -> bool:
        """Check if DBNT is active."""
        pass
```

## Adding Signal Patterns

Edit `src/dbnt/signals/detector.py`:

- `POSITIVE_STRONG` - Triggers success rule creation
- `POSITIVE_MODERATE` - Logs for review
- `NEGATIVE_STRONG` - Triggers failure rule creation
- `NEGATIVE_MODERATE` - Logs for review

Patterns are regex. Keep them language-agnostic when possible.

## Philosophy

1. **Success > Failure** - Weight success signals 1.5x
2. **No anger required** - Mild feedback should work
3. **Portable** - Adapters make it work anywhere
4. **Measurable** - Dissonance gives a number to track

## Pull Requests

1. Fork and branch from `main`
2. Add tests for new features
3. Run `ruff check` and `pytest`
4. Keep commits atomic
5. Describe the "why" in your PR

## Releasing (PyPI Trusted Publishing)

Releases publish automatically via GitHub Actions using PyPI's trusted
publishing (OIDC) — there is no stored PyPI API token in this repo.

### One-time setup (Director / maintainer, on pypi.org)

Before the first tagged release, register this repo as a trusted publisher
on the `dbnt` project at https://pypi.org/manage/project/dbnt/settings/publishing/
using exactly these values:

| Field | Value |
|---|---|
| PyPI Project Name | `dbnt` |
| Owner | `Garman-Unified-Systems` |
| Repository name | `dbnt` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

This is a one-time step. No API token or secret needs to be created or
stored — GitHub Actions authenticates to PyPI via short-lived OIDC tokens
scoped to this exact repo/workflow/environment combination.

### Cutting a release

1. Bump `version` in `pyproject.toml` and `src/dbnt/__init__.py`; update
   `CHANGELOG.md`.
2. Run the release candidate gates locally:
   ```bash
   python scripts/validate_release.py
   python -m pytest
   ruff check src tests scripts
   python -m build
   twine check dist/*
   ```
3. Merge the reviewed release PR to `main` and wait for required CI checks.
4. Tag that exact release commit and push an exact stable SemVer tag:
   ```bash
   git tag v0.6.0
   git push origin v0.6.0
   ```
5. The `.github/workflows/publish.yml` workflow validates the tag against the
   package version, builds and checks the sdist/wheel, and
   publishes them to PyPI automatically. Watch the run under the repo's
   Actions tab; the `publish` job requires the `pypi` GitHub Environment
   (see one-time setup above) to be configured before it will succeed.

Production publication cannot be started with `workflow_dispatch`. A failed
release must be diagnosed without moving or reusing the tag; prepare a new
version when the released artifact would change.

## Questions?

Open an issue or reach out.
