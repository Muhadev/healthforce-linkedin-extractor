# Makefile
.PHONY: help install fmt lint test clean run all playwright-install

PYTHON := python3
PIP := pip3
PROFILE_URL ?= https://www.linkedin.com/in/juansebastianmd/
MIN_POSTS ?= 10
MAX_SECONDS ?= 60

help: ## Show this help message
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install: ## Install dependencies
	$(PIP) install -e .[dev]

playwright-install: ## Install Playwright browsers
	playwright install chromium

fmt: ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

lint: ## Run linters (ruff, mypy)
	ruff check src/ tests/
	mypy src/

lint-fix: ## Run linters and fix auto-fixable issues
	ruff check --fix src/ tests/
	mypy src/

test: ## Run tests
	PYTHONPATH=src pytest tests/ -v --cov=src/li_extractor

clean: ## Clean output directory and cache
	rm -rf out/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run: ## Run the extractor (use PROFILE_URL= to override)
	$(PYTHON) -m li_extractor.cli \
		--profile-url "$(PROFILE_URL)" \
		--min-posts $(MIN_POSTS) \
		--max-seconds $(MAX_SECONDS) \
		--headful

all: fmt lint test ## Run all checks
