# GitHub Actions Workflows

All workflows use **isolated virtual environments** with `uv` for maximum reproducibility and safety.

## Isolation Strategy

Each workflow job:
1. ✅ Uses a fresh GitHub Actions runner (isolated OS environment)
2. ✅ Installs specific Python version via `uv python install`
3. ✅ Creates isolated venv via `uv venv --python X.Y`
4. ✅ Installs dependencies only in that venv
5. ✅ Runs all commands within the venv context

## Workflows

### test.yml
**Trigger**: Every push and pull request
**Purpose**: Run tests across all supported Python versions
**Isolation**: Separate venv for each Python version (3.10-3.14)

```yaml
- Install uv
- Set up Python (uv python install)
- Create venv (uv venv --python X.Y)
- Install deps (uv pip install -e '.[test]')
- Run tests (uv run pytest)
```

### publish.yml
**Trigger**: GitHub Release creation or version tag push
**Purpose**: Publish to PyPI after tests pass
**Isolation**:
  - Test job: Separate venvs for Python 3.10-3.14
  - Deploy job: Isolated build environment with Python 3.10

```yaml
Test:
  - Install uv
  - Set up Python
  - Create venv
  - Install deps
  - Run tests

Deploy:
  - Install uv
  - Set up Python 3.10
  - Build package (uv build)
  - Publish to PyPI (uv publish)
```

### publish-test.yml
**Trigger**: Dev version tags (e.g., 0.9.0.dev1)
**Purpose**: Publish to TestPyPI for testing
**Isolation**: Same as publish.yml but targets TestPyPI

## Why Isolated Environments?

1. **No dependency conflicts**: Each Python version has its own dependency tree
2. **Reproducible builds**: Same environment structure locally and in CI
3. **Clean state**: No leftover packages from previous runs
4. **Version safety**: Test exact version combinations users will use
5. **Debugging**: Easy to reproduce CI environment locally with `uv venv`

## Local Development Match

Developers can replicate CI exactly:

```bash
# Same as CI does
uv venv --python 3.12
uv pip install -e '.[test]'
uv run pytest
```

## Security

- ✅ No global package installation
- ✅ Each venv is temporary and disposed after job
- ✅ No cross-contamination between jobs
- ✅ Explicit dependency versions via pyproject.toml
