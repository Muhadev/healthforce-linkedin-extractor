#!/bin/bash
# scripts/validate_setup.sh
"""Validate that everything is set up correctly for testing."""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}LinkedIn Extractor - Setup Validation${NC}"
echo "======================================"

# Function to check command availability
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is available"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not available"
        return 1
    fi
}

# Function to check file existence
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing $1"
        return 1
    fi
}

# Function to check directory existence
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Found directory $1"
        return 0
    else
        echo -e "${YELLOW}!${NC} Missing directory $1"
        return 1
    fi
}

echo "Checking basic requirements..."

# Check Python
if check_command python3; then
    PYTHON_VERSION=$(python3 --version)
    echo "  Version: $PYTHON_VERSION"
fi

# Check pip
check_command pip3

# Check virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✓${NC} Virtual environment active: $VIRTUAL_ENV"
else
    echo -e "${YELLOW}!${NC} No virtual environment detected"
    echo "  Consider activating your virtual environment"
fi

echo ""
echo "Checking project structure..."

# Check important files
check_file "pyproject.toml"
check_file "Makefile"
check_file "requirements.txt"

# Check source directory
check_dir "src/li_extractor"
check_file "src/li_extractor/__init__.py"
check_file "src/li_extractor/cli.py"

# Check test directory
check_dir "tests"
check_file "tests/conftest.py"

echo ""
echo "Checking dependencies..."

# Check if playwright is installed
if python3 -c "import playwright" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Playwright Python package installed"
    
    # Check if browsers are installed
    if check_command playwright; then
        echo -e "${GREEN}✓${NC} Playwright CLI available"
        
        # Check browser installation
        if [ -d "$HOME/.cache/ms-playwright" ] || [ -d "$HOME/Library/Caches/ms-playwright" ]; then
            echo -e "${GREEN}✓${NC} Playwright browsers appear to be installed"
        else
            echo -e "${YELLOW}!${NC} Playwright browsers may not be installed"
            echo "  Run: make playwright-install"
        fi
    else
        echo -e "${RED}✗${NC} Playwright CLI not available"
        echo "  Run: make install"
    fi
else
    echo -e "${RED}✗${NC} Playwright Python package not installed"
    echo "  Run: make install"
fi

# Check other key dependencies
for package in "pydantic" "typer" "rich"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $package installed"
    else
        echo -e "${RED}✗${NC} $package not installed"
    fi
done

echo ""
echo "Checking make targets..."

# Check if make is available
if check_command make; then
    echo "Available make targets:"
    make help 2>/dev/null | grep -E "^\s+[a-zA-Z_-]+.*##" | head -10
fi

echo ""
echo "Testing basic functionality..."

# Test import
echo -n "Testing Python imports... "
if python3 -c "
import sys
sys.path.insert(0, 'src')
from li_extractor.cli import main
from li_extractor.models import LinkedInPost
from li_extractor.timeparse import TimeParser
print('OK')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "  Python imports failed - check dependencies"
fi

# Test basic time parsing
echo -n "Testing time parser... "
if python3 -c "
import sys
sys.path.insert(0, 'src')
from li_extractor.timeparse import TimeParser
parser = TimeParser()
result = parser.parse_relative_time('2h')
assert result is not None
print('OK')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test model validation
echo -n "Testing data models... "
if python3 -c "
import sys
sys.path.insert(0, 'src')
from li_extractor.models import LinkedInPost
post = LinkedInPost(post_id='test-123')
assert post.post_id == 'test-123'
print('OK')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo ""
echo "Quick test recommendations:"
echo "=========================="
echo "1. Run unit tests first:"
echo "   make test-unit"
echo ""
echo "2. Test CLI help:"
echo "   python -m li_extractor.cli --help"
echo ""
echo "3. Run a quick extraction (will need login):"
echo "   make run"
echo ""
echo "4. Run E2E tests (after CLI test works):"
echo "   make test-e2e"
echo ""

# Final summary
echo -e "${BLUE}Setup validation complete!${NC}"

# Check if we can recommend next steps
if command -v python3 &> /dev/null && python3 -c "import playwright" 2>/dev/null; then
    echo -e "${GREEN}✓ Ready for testing${NC}"
    echo ""
    echo "Next steps:"
    echo "  make test-unit    # Start with unit tests"
    echo "  make run          # Try CLI extraction"
    echo "  make test-e2e     # Run E2E tests"
else
    echo -e "${YELLOW}! Setup incomplete${NC}"
    echo ""
    echo "Required actions:"
    echo "  make install           # Install dependencies"
    echo "  make playwright-install # Install browsers"
fi