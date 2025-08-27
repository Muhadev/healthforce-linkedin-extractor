# README.md
# LinkedIn Posts Extractor

Enterprise-grade LinkedIn posts extraction tool with robust session management, structured logging, and data handling.

## Features

- **Zero-credential storage**: Only Playwright `storage_state` is persisted
- **Human-like automation**: Rate-limited with jitter (100-400ms between actions)
- **Structured observability**: JSON logs with event codes and trace correlation
- **Resilient extraction**: Graceful handling of missing fields and timeouts
- **Schema validation**: Pydantic models with exported JSON Schema

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -e .[dev]

# Install Playwright browsers
make playwright-install
# or manually: playwright install chromium
```
#
### 2. First Run (Interactive Login)

```bash
# First run opens headful browser for manual LinkedIn login
make run PROFILE_URL=https://www.linkedin.com/in/username/

# Or directly:
python -m li_extractor.cli \
  --profile-url "https://www.linkedin.com/in/username/" \
  --min-posts 15 \
  --max-seconds 90 \
  --headful
```

**Important**: The first run will:
1. Open a browser window
2. Navigate to LinkedIn login
3. Wait for you to manually log in
4. Save session to `out/session/storage.json`
5. Begin extraction

### 3. Subsequent Runs (Automated)

```bash
# Subsequent runs reuse saved session - no login required
python -m li_extractor.cli \
  --profile-url "https://www.linkedin.com/in/username/" \
  --headless
```

## Output

### Generated Files

- `out/li_posts.json` - Extracted posts in structured format
- `out/run.log` - Structured JSONL logs with event codes
- `out/session/storage.json` - Playwright session state (git-ignored)

### Sample Output Structure

```json
{
  "profile_url": "https://www.linkedin.com/in/username/",
  "fetched_at": "2025-08-27T12:34:56Z",
  "total_posts": 12,
  "posts": [
    {
      "post_id": "abc123",
      "author_name": "John Doe",
      "posted_at": "2025-08-26T15:30:00Z",
      "text": "Excited to share insights on #AI and #healthcare...",
      "hashtags": ["ai", "healthcare"],
      "links": ["https://example.com/article"],
      "reactions_count": 45,
      "comments_count": 8
    }
  ]
}
```

## CLI Options

```bash
python -m li_extractor.cli [OPTIONS]

Options:
  --profile-url TEXT        LinkedIn profile URL (required)
  --min-posts INTEGER       Minimum posts to extract [default: 10]
  --max-seconds INTEGER     Maximum extraction time [default: 60]
  --out-dir PATH           Output directory [default: out]
  --storage-state PATH     Session storage path [default: out/session/storage.json]
  --headful/--headless     Browser mode [default: headful on first run]
  --log-level TEXT         Log level [default: INFO]
  --help                   Show this message and exit
```

## Development

### Make Targets

```bash
make help              # Show available targets
make install           # Install dependencies
make playwright-install # Install Playwright browsers
make fmt               # Format code (black, isort)
make lint              # Run linters (ruff, mypy)
make test              # Run tests with coverage
make clean             # Clean output and cache
make all               # Run fmt, lint, test
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test files
pytest tests/test_timeparse.py -v
pytest tests/test_extractors.py -v

# Run with coverage
pytest --cov=src/li_extractor --cov-report=html
```

## Architecture

### Project Structure

```
src/li_extractor/
├── cli.py           # Typer CLI entrypoint
├── browser.py       # Playwright session management
├── navigator.py     # Profile navigation and post loading
├── extractors.py    # DOM parsing and field extraction
├── models.py        # Pydantic data models
├── rate_limit.py    # Rate limiting utilities
├── logging_.py      # Structured JSON logging
├── timeparse.py     # Time normalization
└── output.py        # Output file generation
```

### Event Codes

- **Session**: `LI001-LI004` (reused, login required, saved, invalid)
- **Navigation**: `LI101-LI106` (opened, timeout, min met, scrolled, idle, error)
- **Extraction**: `LI201-LI205` (found, validation error, warning, missing, parsed)
- **Output**: `LI301-LI303` (started, ok, failed)
- **Errors**: `LI900+` (exceptions)

## Security & Compliance

- **No credential storage**: Only session state is persisted
- **PII protection**: Logs are scrubbed of sensitive information
- **Rate limiting**: Human-like interaction patterns
- **Session rotation**: Delete `out/session/storage.json` to re-authenticate

## Session Management

### First-Time Setup
1. Run with `--headful` flag
2. Browser opens to LinkedIn login
3. Manually complete authentication
4. Session automatically saved

### Session Rotation
```bash
# Force re-authentication
rm out/session/storage.json
python -m li_extractor.cli --profile-url URL --headful
```

### Troubleshooting

**Session Invalid**
- Delete `out/session/storage.json`
- Re-run with `--headful`

**Rate Limiting**
- Tool automatically uses 100-400ms jitter
- Averages ~1 action per second
- Check logs for timing metrics

**Extraction Failures**
- Review `out/run.log` for event codes
- Missing fields logged as warnings
- Partial results still output on timeout

## Legal & Ethics

This tool is designed for:
- Public profile data extraction
- Research and analysis purposes
- Compliance with robots.txt and rate limits

**Important**: Ensure compliance with:
- LinkedIn Terms of Service
- Local data protection laws
- Your organization's data policies

Only extract from public profiles and respect platform rate limits.

## Contributing

1. Install dev dependencies: `pip install -e .[dev]`
2. Set up pre-commit: `pre-commit install`
3. Run checks: `make all`
4. Submit PR with tests