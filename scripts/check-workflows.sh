#!/bin/bash
# Script to monitor GitHub Actions workflows

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Checking GitHub Actions workflows...${NC}\n"

# Check if gh is authenticated
if ! gh auth status &>/dev/null; then
    echo -e "${YELLOW}GitHub CLI not authenticated. Authenticating...${NC}"
    gh auth login
fi

echo -e "${GREEN}Latest commit:${NC}"
git log --oneline -1
echo ""

echo -e "${BLUE}Workflow runs:${NC}"
gh run list --limit 5

echo -e "\n${BLUE}Watching latest run...${NC}"
echo "Press Ctrl+C to stop watching"
echo ""

# Get the latest run ID
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

if [ -z "$RUN_ID" ]; then
    echo -e "${RED}No workflow runs found${NC}"
    exit 1
fi

# Watch the run
gh run watch "$RUN_ID"

# Check if it succeeded
STATUS=$(gh run view "$RUN_ID" --json conclusion --jq '.conclusion')

if [ "$STATUS" = "success" ]; then
    echo -e "\n${GREEN}✓ Workflow succeeded!${NC}"
    exit 0
elif [ "$STATUS" = "failure" ]; then
    echo -e "\n${RED}✗ Workflow failed!${NC}"
    echo -e "\n${YELLOW}Showing failed jobs:${NC}\n"
    gh run view "$RUN_ID"

    echo -e "\n${YELLOW}View detailed logs at:${NC}"
    echo "https://github.com/imZack/mbox2sqlite-llm/actions/runs/$RUN_ID"
    exit 1
else
    echo -e "\n${YELLOW}Status: $STATUS${NC}"
    exit 0
fi
