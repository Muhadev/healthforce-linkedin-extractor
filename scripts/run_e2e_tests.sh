#!/bin/bash
# scripts/run_e2e_tests.sh
"""Run end-to-end tests with proper environment setup."""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}LinkedIn Posts Extractor - E2E Tests${NC}"
echo "=========================================="

# Check if Playwright browsers are installed
if ! command -v playwright &> /dev/null; then
    echo -e "${RED}Error: Playwright is not installed or not in PATH${NC}"
    echo "Please run: playwright install chromium"
    exit 1
fi

# Check if browsers are installed
if [ ! -d "$HOME/.cache/ms-playwright" ] && [ ! -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo -e "${YELLOW}Warning: Playwright browsers may not be installed${NC}"
    echo "Run: playwright install chromium"
fi

# Set environment variables for E2E tests
export RUN_E2E_TESTS=true
export E2E_HEADLESS=${E2E_HEADLESS:-false}
export TEST_LINKEDIN_PROFILE=${TEST_LINKEDIN_PROFILE:-"https://www.linkedin.com/in/fayemi-muhammed/"}

echo "Configuration:"
echo "  E2E Tests: ${RUN_E2E_TESTS}"
echo "  Headless: ${E2E_HEADLESS}"
echo "  Test Profile: ${TEST_LINKEDIN_PROFILE}"
echo ""

# Warn about manual login requirement
if [ "${E2E_HEADLESS}" = "false" ]; then
    echo -e "${YELLOW}Note: These tests may require manual LinkedIn login${NC}"
    echo "A browser window will open for authentication if needed."
    echo ""
fi

# Run E2E tests specifically
echo "Running E2E tests..."
PYTHONPATH=src pytest tests/e2e/ -v -m e2e --tb=short

# Also run a quick unit test to ensure everything else still works
echo ""
echo "Running quick unit tests to verify no regressions..."
PYTHONPATH=src pytest tests/test_models.py tests/test_timeparse.py -v --tb=short

echo ""
echo -e "${GREEN}E2E test run completed!${NC}"

# Instructions for troubleshooting
cat << EOF

Troubleshooting:
================
1. If tests fail with browser errors:
   - Run: playwright install chromium
   - Run: playwright install-deps chromium

2. If LinkedIn login is required:
   - Set E2E_HEADLESS=false to see browser window
   - Complete login manually when prompted
   - Session will be saved for future runs

3. To run tests against a different profile:
   - Set TEST_LINKEDIN_PROFILE=https://www.linkedin.com/in/yourprofile/

4. For debugging:
   - Add --log-cli-level=DEBUG to pytest command
   - Check logs in out/test.log

Example commands:
  ./scripts/run_e2e_tests.sh                    # Run with default settings
  E2E_HEADLESS=true ./scripts/run_e2e_tests.sh  # Run headless
  TEST_LINKEDIN_PROFILE=https://www.linkedin.com/in/yourprofile/ ./scripts/run_e2e_tests.sh
EOF