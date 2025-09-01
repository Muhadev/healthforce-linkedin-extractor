# scripts/playwright_install.sh
#!/bin/bash
"""Install Playwright browsers."""

set -e

echo "Installing Playwright browsers..."
playwright install chromium

echo "Installing system dependencies..."
playwright install-deps chromium

echo "Playwright installation complete!"