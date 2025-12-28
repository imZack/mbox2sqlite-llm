# Release Workflow Guide

## Development & Testing Releases

### 1. Create a Dev Version (Testing)

```bash
# Make your changes
git add .
git commit -m "Add new feature"

# Create dev version: 0.9.0.dev1, 0.9.0.dev2, etc.
uvx bump-my-version bump --new-version "0.9.0.dev1" build
# Or manually edit: version = "0.9.0.dev1" in setup.py and pyproject.toml

# Push to GitHub (no tag yet)
git push origin main
```

### 2. Test Publish to TestPyPI

```bash
# Build the package
uv build

# Publish to TestPyPI (test server)
uv publish --publish-url https://test.pypi.org/legacy/ --token <test-pypi-token>

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ mbox2sqlite-llm==0.9.0.dev1
```

### 3. Verify Everything Works

```bash
# Test your package
mbox2sqlite-llm --help
mbox2sqlite-llm mbox test.db test.mbox

# If issues found, fix and create 0.9.0.dev2, repeat testing
```

### 4. Create Stable Release

```bash
# Bump to stable version
uvx bump-my-version bump patch  # 0.9.0.dev2 → 0.9.1
# Or for first release from dev:
# Manually set: version = "0.9.0"

# Commit and tag
git add .
git commit -m "Release 0.9.0"
git tag 0.9.0
git push origin main --tags

# Create GitHub Release (triggers automatic PyPI publish)
# Go to: https://github.com/imZack/mbox2sqlite-llm/releases/new
# Select tag: 0.9.0
# Click "Publish release"
```

---

## Quick Workflow (For Small Changes)

### Direct Stable Release

```bash
# 1. Make changes
git add .
git commit -m "Fix bug in cleaning"

# 2. Bump version
uvx bump-my-version bump patch  # 0.9.0 → 0.9.1

# 3. Push (bump-my-version auto-creates tag)
git push origin main --tags

# 4. Create GitHub Release
# The workflow automatically publishes to PyPI
```

---

## Version Numbering Guide

### Development Versions (Testing)
```
0.9.0.dev1  ← First dev version
0.9.0.dev2  ← Second dev version
0.9.0.dev3  ← Third dev version
```

### Stable Versions
```
0.9.0  ← Stable release
0.9.1  ← Bug fix
0.10.0 ← New features
1.0.0  ← Major stable release
```

---

## TestPyPI vs PyPI

### TestPyPI (Testing)
- **URL**: https://test.pypi.org
- **Purpose**: Test uploads, verify package metadata
- **Packages**: Deleted after ~1 week
- **Token**: Separate from production PyPI

### PyPI (Production)
- **URL**: https://pypi.org
- **Purpose**: Real releases for users
- **Packages**: Permanent (cannot delete versions)
- **Token**: Your main PYPI_TOKEN

---

## Setup TestPyPI (One-Time)

```bash
# 1. Create account at https://test.pypi.org/account/register/
# 2. Generate API token at https://test.pypi.org/manage/account/token/
# 3. Add to GitHub Secrets as TEST_PYPI_TOKEN
```

---

## Manual Publishing Commands

```bash
# Build
uv build

# Publish to TestPyPI
export UV_PUBLISH_TOKEN="your-test-token"
uv publish --publish-url https://test.pypi.org/legacy/

# Publish to PyPI
export UV_PUBLISH_TOKEN="your-pypi-token"
uv publish
```

---

## Typical Development Cycle

```
┌─────────────────────────────────────────────┐
│ 1. Develop Feature                          │
│    git commit -m "Add feature"              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ 2. Create Dev Version                       │
│    version = "0.9.0.dev1"                   │
│    uv publish to TestPyPI                   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ 3. Test Installation                        │
│    pip install from TestPyPI                │
│    Run tests, check functionality           │
└────────────────┬────────────────────────────┘
                 │
                 ▼
         ┌───────┴───────┐
         │  Issues?      │
         └───┬───────┬───┘
             │       │
            Yes      No
             │       │
             │       ▼
             │  ┌─────────────────────────────┐
             │  │ 4. Bump to Stable Version   │
             │  │    uvx bump-my-version bump │
             │  │    git tag 0.9.0            │
             │  └────────────┬────────────────┘
             │               │
             │               ▼
             │  ┌─────────────────────────────┐
             │  │ 5. Create GitHub Release    │
             │  │    Auto-publishes to PyPI   │
             │  └─────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│ Fix Issues                                  │
│ Create 0.9.0.dev2, republish to TestPyPI    │
└─────────────────────────────────────────────┘
```

---

## My Recommendation

### For First Release (0.9.0)
1. Create `0.9.0.dev1` - test on TestPyPI
2. Fix any issues → `0.9.0.dev2`
3. When satisfied → Release `0.9.0` to PyPI

### For Future Releases
- Small bug fixes: Direct stable release
- New features: Test with dev version first
- Breaking changes: Always test with dev version
