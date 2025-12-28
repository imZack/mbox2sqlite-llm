#!/bin/bash
# Release helper script for mbox2sqlite-llm

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}mbox2sqlite-llm Release Helper${NC}\n"

# Check if we have uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    git status -s
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep "^version = " pyproject.toml | cut -d'"' -f2)
echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}\n"

# Ask what kind of release
echo "What kind of release?"
echo "1) Dev version (0.9.0 → 0.9.0.dev1) - for TestPyPI"
echo "2) Patch (0.9.0 → 0.9.1) - bug fixes"
echo "3) Minor (0.9.0 → 0.10.0) - new features"
echo "4) Major (0.9.0 → 1.0.0) - breaking changes"
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        # Dev version
        read -p "Enter dev number (e.g., 1 for 0.9.0.dev1): " dev_num
        NEW_VERSION="${CURRENT_VERSION}.dev${dev_num}"
        BUMP_TYPE="dev"
        TARGET="TestPyPI"
        ;;
    2)
        BUMP_TYPE="patch"
        TARGET="PyPI"
        ;;
    3)
        BUMP_TYPE="minor"
        TARGET="PyPI"
        ;;
    4)
        BUMP_TYPE="major"
        TARGET="PyPI"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Bump version
if [ "$BUMP_TYPE" = "dev" ]; then
    echo -e "\n${YELLOW}Setting version to ${NEW_VERSION}${NC}"
    # Manually set version for dev
    sed -i.bak "s/version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml
    sed -i.bak "s/VERSION = \".*\"/VERSION = \"${NEW_VERSION}\"/" setup.py
    rm pyproject.toml.bak setup.py.bak

    git add pyproject.toml setup.py
    git commit -m "Bump version to ${NEW_VERSION}"
    git tag "${NEW_VERSION}"
else
    echo -e "\n${YELLOW}Bumping version (${BUMP_TYPE})${NC}"
    uvx bump-my-version bump "${BUMP_TYPE}"
    NEW_VERSION=$(grep "^version = " pyproject.toml | cut -d'"' -f2)
fi

echo -e "${GREEN}New version: ${NEW_VERSION}${NC}\n"

# Confirm before pushing
echo -e "${YELLOW}Ready to push to GitHub (target: ${TARGET})${NC}"
echo "This will:"
echo "  - Push commits and tag ${NEW_VERSION}"
if [ "$BUMP_TYPE" = "dev" ]; then
    echo "  - Trigger TestPyPI publish workflow"
else
    echo "  - You'll need to create GitHub Release manually for PyPI publish"
fi

read -p "Continue? [y/N]: " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted${NC}"
    exit 1
fi

# Push
git push origin main --tags

echo -e "\n${GREEN}✓ Pushed successfully!${NC}\n"

if [ "$BUMP_TYPE" = "dev" ]; then
    echo -e "${GREEN}Dev version ${NEW_VERSION} will be published to TestPyPI${NC}"
    echo -e "Check: https://github.com/imZack/mbox2sqlite-llm/actions"
    echo -e "\nInstall from TestPyPI:"
    echo -e "  pip install --index-url https://test.pypi.org/simple/ mbox2sqlite-llm==${NEW_VERSION}"
else
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "1. Go to: https://github.com/imZack/mbox2sqlite-llm/releases/new"
    echo -e "2. Select tag: ${NEW_VERSION}"
    echo -e "3. Create release to trigger PyPI publish"
fi
