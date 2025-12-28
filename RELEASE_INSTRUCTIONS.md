# Release to PyPI - v0.9.0

## Step 1: Create PyPI Account & API Token

1. **Create PyPI account** (if you don't have one):
   - Go to: https://pypi.org/account/register/
   - Verify your email

2. **Generate API token**:
   - Go to: https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Token name: `GitHub Actions mbox2sqlite-llm`
   - Scope: `Entire account` (initially, then scope to project after first upload)
   - **IMPORTANT**: Copy the token now (starts with `pypi-...`) - you won't see it again!

3. **Add token to GitHub Secrets**:
   - Go to: https://github.com/imZack/mbox2sqlite-llm/settings/secrets/actions
   - Click "New repository secret"
   - Name: `PYPI_TOKEN`
   - Value: Paste your `pypi-...` token
   - Click "Add secret"

## Step 2: Create GitHub Release (This triggers PyPI publish)

### Option A: Via GitHub Web UI (Recommended)

1. Go to: https://github.com/imZack/mbox2sqlite-llm/releases/new

2. Fill in the form:
   - **Choose a tag**: `0.9.0` (create new tag from: main)
   - **Release title**: `v0.9.0 - Initial Release`
   - **Description**:
     ```markdown
     ## mbox2sqlite-llm v0.9.0

     Initial release with Gmail Takeout support and LLM optimization.

     ### Features
     - ✅ Gmail Takeout .mbox file support
     - ✅ LLM optimization with 91% token reduction via `clean` command
     - ✅ Chinese/CJK full-text search with simple tokenizer
     - ✅ Two-database workflow (original + cleaned)
     - ✅ Python 3.10-3.14 support

     ### Installation
     ```bash
     pip install mbox2sqlite-llm
     ```

     ### Quick Start
     ```bash
     # Import Gmail Takeout
     mbox2sqlite-llm mbox emails.db gmail.mbox

     # Create LLM-optimized version
     mbox2sqlite-llm clean emails.db emails-clean.db --level standard
     ```

     ### Credits
     Forked from [simonw/mbox-to-sqlite](https://github.com/simonw/mbox-to-sqlite)
     ```

3. Click "Publish release"

### Option B: Via Command Line

```bash
# Create and push tag
git tag 0.9.0
git push origin 0.9.0

# Then go to GitHub UI to create the release from the tag
```

## Step 3: Monitor the Workflow

After creating the release:

```bash
# Watch the publish workflow
gh run list --limit 5

# View specific run
gh run watch <run-id>
```

The workflow will:
1. Run tests on Python 3.10-3.14 ✅
2. Build the package ✅
3. Publish to PyPI ✅

## Step 4: Verify Publication

After successful publish:

1. **Check PyPI**:
   - https://pypi.org/project/mbox2sqlite-llm/

2. **Test installation**:
   ```bash
   # In a fresh environment
   pip install mbox2sqlite-llm
   mbox2sqlite-llm --version
   ```

## Troubleshooting

### If publish fails with 403:
- Check that PYPI_TOKEN secret is correctly set
- Ensure token hasn't expired
- Verify token has correct permissions

### If package name conflicts:
- PyPI doesn't allow duplicate names
- Choose a different name if `mbox2sqlite-llm` is taken

### If tests fail:
- Fix the issues
- Create a new commit
- Delete the tag: `git tag -d 0.9.0 && git push origin :refs/tags/0.9.0`
- Recreate the release

## After First Release

After your first successful publish:

1. **Scope your token** (recommended):
   - Go to https://pypi.org/manage/account/token/
   - Delete the "Entire account" token
   - Create new token scoped to `mbox2sqlite-llm` only
   - Update GitHub Secret with new token

2. **Future releases**:
   ```bash
   # Bump version
   uvx bump-my-version bump patch  # 0.9.0 → 0.9.1
   # Or: uvx bump-my-version bump minor  # 0.9.0 → 0.10.0

   git push --tags
   # Create release on GitHub
   ```
