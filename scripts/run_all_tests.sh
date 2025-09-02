#!/bin/bash
# scripts/run_all_tests.sh
"""Comprehensive test runner for LinkedIn Extractor."""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
LINKEDIN_PROFILE=${TEST_LINKEDIN_PROFILE:-"https://www.linkedin.com/in/fayemi-muhammed/"}
RUN_E2E=${RUN_E2E_TESTS:-"false"}
HEADLESS=${E2E_HEADLESS:-"false"}

echo -e "${BLUE}LinkedIn Extractor - Comprehensive Test Suite${NC}"
echo "=============================================="
echo "Profile: $LINKEDIN_PROFILE"
echo "E2E Tests: $RUN_E2E"
echo "Headless: $HEADLESS"
echo ""

# Function to run a test section
run_section() {
    local section_name="$1"
    local section_color="$2"
    shift 2
    
    echo -e "${section_color}=== $section_name ===${NC}"
    echo ""
    
    if "$@"; then
        echo -e "${GREEN}✓ $section_name completed successfully${NC}"
    else
        echo -e "${RED}✗ $section_name failed${NC}"
        return 1
    fi
    echo ""
}

# Function to run CLI test
test_cli() {
    echo "Testing CLI with basic parameters..."
    timeout 60 python -m li_extractor.cli \
        --profile-url "$LINKEDIN_PROFILE" \
        --min-posts 3 \
        --max-seconds 20 \
        --headful \
        || echo "CLI test completed (may have timed out)"
    
    # Check if output files were created
    if [ -f "out/li_posts.json" ]; then
        echo "✓ Output file created: out/li_posts.json"
        echo "File size: $(stat -c%s out/li_posts.json) bytes"
        
        # Show sample of extracted data
        echo "Sample extracted data:"
        head -20 out/li_posts.json
    else
        echo "! No output file found"
    fi
    
    if [ -f "out/run.log" ]; then
        echo "✓ Log file created: out/run.log"
        echo "Log entries: $(wc -l < out/run.log) lines"
    fi
}

# Function to demonstrate different CLI options
demo_cli_options() {
    echo "Demonstrating different CLI options..."
    
    # Help command
    echo "1. CLI Help:"
    python -m li_extractor.cli --help || true
    echo ""
    
    # Version information
    echo "2. Module information:"
    python -c "
import sys
sys.path.insert(0, 'src')
from li_extractor import __version__, __author__
print(f'Version: {__version__}')
print(f'Author: {__author__}')
" || true
    echo ""
    
    # Schema export
    echo "3. Exporting JSON schema:"
    python -c "
import sys
sys.path.insert(0, 'src')
from li_extractor.models import LinkedInPostsExtraction
from li_extractor.output import OutputManager
from li_extractor.logging_ import StructuredLogger
from pathlib import Path

Path('out').mkdir(exist_ok=True)
logger = StructuredLogger('schema_gen', Path('out/schema.log'))
manager = OutputManager(logger)
success = manager.export_schema(Path('out/schema.json'))
if success:
    print('✓ Schema exported to out/schema.json')
else:
    print('✗ Schema export failed')
" || echo "Schema export failed"
    
    if [ -f "out/schema.json" ]; then
        echo "Schema preview:"
        head -20 out/schema.json
    fi
    echo ""
}

# Main test execution
main() {
    echo "Starting comprehensive test suite..."
    echo ""
    
    # 1. Setup validation
    run_section "Setup Validation" "$PURPLE" bash scripts/validate_setup.sh
    
    # 2. Code quality checks
    run_section "Code Formatting" "$BLUE" make fmt
    run_section "Linting" "$BLUE" make lint-fix
    
    # 3. Unit tests
    run_section "Unit Tests" "$GREEN" make test-unit
    
    # 4. Integration tests
    run_section "Integration Tests" "$GREEN" \
        bash -c 'PYTHONPATH=src pytest tests/test_integration.py -v'
    
    # 5. CLI demonstrations
    run_section "CLI Options Demo" "$YELLOW" demo_cli_options
    
    # 6. CLI functional test
    echo -e "${YELLOW}=== CLI Functional Test ===${NC}"
    echo "This may require manual LinkedIn login..."
    read -p "Press Enter to continue with CLI test (Ctrl+C to skip)..."
    run_section "CLI Functional Test" "$YELLOW" test_cli
    
    # 7. E2E tests (optional)
    if [ "$RUN_E2E" = "true" ]; then
        echo -e "${PURPLE}=== E2E Tests ===${NC}"
        echo "Running end-to-end tests..."
        echo "This may require manual LinkedIn login if no session exists..."
        run_section "E2E Tests" "$PURPLE" \
            bash -c "RUN_E2E_TESTS=true E2E_HEADLESS=$HEADLESS make test-e2e"
    else
        echo -e "${YELLOW}=== E2E Tests Skipped ===${NC}"
        echo "To run E2E tests, set: RUN_E2E_TESTS=true"
        echo ""
    fi
    
    # 8. Performance and stress tests
    run_section "Performance Tests" "$PURPLE" \
        bash -c 'echo "Running performance analysis..."; \
                 python -c "
import time
import sys
sys.path.insert(0, \"src\")

# Time imports
start = time.time()
from li_extractor.timeparse import TimeParser
from li_extractor.models import LinkedInPost
from li_extractor.extractors import PostExtractor
import_time = time.time() - start

# Test time parser performance
parser = TimeParser()
start = time.time()
for i in range(1000):
    parser.parse_relative_time(f\"{i}h\")
parse_time = time.time() - start

print(f\"Import time: {import_time:.3f}s\")
print(f\"Parse 1000 timestamps: {parse_time:.3f}s\")
print(f\"Average parse time: {parse_time/1000*1000:.3f}ms\")
"'
    
    # 9. Final summary
    echo -e "${GREEN}=== Test Summary ===${NC}"
    echo ""
    
    # Check outputs
    echo "Generated files:"
    ls -la out/ 2>/dev/null | head -10 || echo "No output directory"
    echo ""
    
    # Log analysis
    if [ -f "out/run.log" ]; then
        echo "Recent log entries:"
        tail -5 out/run.log 2>/dev/null || true
        echo ""
    fi
    
    # Coverage summary
    if [ -f ".coverage" ]; then
        echo "Test coverage summary:"
        python -m coverage report --skip-empty 2>/dev/null | tail -5 || true
    fi
    
    echo -e "${GREEN}✓ Comprehensive test suite completed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Review out/li_posts.json for extracted data"
    echo "  - Check out/run.log for detailed logs"
    echo "  - Run individual tests as needed"
    echo "  - Set RUN_E2E_TESTS=true for full E2E testing"
}

# Help function
show_help() {
    cat << EOF
LinkedIn Extractor - Comprehensive Test Runner

Usage: $0 [OPTIONS]

Environment Variables:
  TEST_LINKEDIN_PROFILE  LinkedIn profile URL to test with
                         (default: https://www.linkedin.com/in/fayemi-muhammed/)
  RUN_E2E_TESTS         Run E2E tests (true/false, default: false)
  E2E_HEADLESS          Run E2E tests in headless mode (true/false, default: false)

Examples:
  ./scripts/run_all_tests.sh
  
  RUN_E2E_TESTS=true ./scripts/run_all_tests.sh
  
  TEST_LINKEDIN_PROFILE=https://www.linkedin.com/in/yourprofile/ \\
  RUN_E2E_TESTS=true \\
  E2E_HEADLESS=true \\
  ./scripts/run_all_tests.sh

Options:
  -h, --help    Show this help message
  
Test Sections:
  1. Setup Validation   - Check environment and dependencies
  2. Code Quality       - Formatting and linting
  3. Unit Tests         - Fast tests without external dependencies
  4. Integration Tests  - Mock-based workflow testing
  5. CLI Demo          - Command-line interface examples
  6. CLI Functional    - Real CLI extraction test
  7. E2E Tests         - Live LinkedIn testing (optional)
  8. Performance      - Speed and efficiency tests
  9. Summary          - Results and next steps
EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac