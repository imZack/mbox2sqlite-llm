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
echo "1) Patch (0.9.0 → 0.9.1) - bug fixes"
echo "2) Minor (0.9.0 → 0.10.0) - new features"
echo "3) Major (0.9.0 → 1.0.0) - breaking changes"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        BUMP_TYPE="patch"
        ;;
    2)
        BUMP_TYPE="minor"
        ;;
    3)
        BUMP_TYPE="major"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Bump version using bump-my-version
echo -e "\n${YELLOW}Bumping version (${BUMP_TYPE})${NC}"
uvx bump-my-version bump "${BUMP_TYPE}"
NEW_VERSION=$(grep "^version = " pyproject.toml | cut -d'"' -f2)

echo -e "${GREEN}New version: ${NEW_VERSION}${NC}\n"

# Confirm before pushing
echo -e "${YELLOW}Ready to push to GitHub${NC}"
echo "This will:"
echo "  - Push commits and tag ${NEW_VERSION}"
echo "  - You'll need to create GitHub Release manually to trigger PyPI publish"

read -p "Continue? [y/N]: " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted${NC}"
    exit 1
fi

# Push
git push origin main --tags

echo -e "\n${GREEN}✓ Pushed successfully!${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Go to: https://github.com/imZack/mbox2sqlite-llm/releases/new"
echo -e "2. Select tag: ${NEW_VERSION}"
echo -e "3. Create release to trigger PyPI publish workflow"
echo -e "\nAfter publish, verify at:"
echo -e "  https://pypi.org/project/mbox2sqlite-llm/"
