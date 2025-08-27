# Additional Documentation Files

# RUNBOOK.md
# LinkedIn Posts Extractor - Operations Runbook

## Quick Reference

### Commands
```bash
# First-time setup
make install
make playwright-install

# Basic extraction
make run PROFILE_URL=https://www.linkedin.com/in/username/

# Custom parameters
python -m li_extractor.cli \
  --profile-url "https://www.linkedin.com/in/username/" \
  --min-posts 20 \
  --max-seconds 120 \
  --headless

# Development
make all  # Run fmt, lint, test
```

### File Locations
- **Output**: `out/li_posts.json`
- **Logs**: `out/run.log` (JSONL format)
- **Session**: `out/session/storage.json` (git-ignored)
- **Config**: `.env` (optional)

## Session Management

### Initial Setup
1. Run with `--headful` flag
2. Browser opens to LinkedIn login
3. Complete authentication manually
4. Session automatically saved to `out/session/storage.json`

### Session Rotation
```bash
# Force new login
rm out/session/storage.json
python -m li_extractor.cli --profile-url URL --headful
```

### Troubleshooting Sessions

**Problem**: "Session invalid" errors
```bash
# Solution: Clear and re-authenticate
rm -rf out/session/
make run PROFILE_URL=https://linkedin.com/in/username/
```

**Problem**: Login timeout
- Increase timeout in browser.py: `timeout=300000` (5 minutes)
- Ensure 2FA completion within time limit
- Check browser console for JavaScript errors

## Monitoring & Observability

### Log Event Codes
- **LI001-LI004**: Session management
- **LI101-LI106**: Navigation and loading  
- **LI201-LI205**: Data extraction
- **LI301-LI303**: Output generation
- **LI900+**: Error conditions

### Key Metrics
```bash
# Check extraction metrics
cat out/run.log | jq 'select(.event_code == "LI301") | .context'

# Monitor action rates  
cat out/run.log | jq 'select(.metrics.actions_per_second) | .metrics'

# Find errors
cat out/run.log | jq 'select(.level == "ERROR")'
```

### Health Checks
```bash
# Verify output structure
python -c "
import json
with open('out/li_posts.json') as f:
    data = json.load(f)
    print(f'Posts: {data[\"total_posts\"]}')
    print(f'Fetched: {data[\"fetched_at\"]}')
"

# Check log completeness
grep -c "LI" out/run.log  # Should see multiple event codes
```

## Performance Tuning

### Rate Limiting
- Default: 100-400ms jitter between actions
- Target: ~1 action per second average
- Adjust in `rate_limit.py`: `min_ms`, `max_ms` parameters

### Timeout Configuration
- **Navigation**: 30s default in `browser.py`
- **Post loading**: 60s default via `--max-seconds`
- **Network idle**: 5s in `action_tracker.py`

### Resource Usage
```bash
# Monitor browser memory
ps aux | grep chromium

# Check disk usage
du -sh out/

# Log file size
ls -lh out/run.log
```

## Data Quality

### Validation
```bash
# Validate output schema
python -c "
from li_extractor.models import LinkedInPostsExtraction
import json
with open('out/li_posts.json') as f:
    data = json.load(f)
    result = LinkedInPostsExtraction(**data)
    print('✅ Schema valid')
"
```

### Common Issues

**Missing Fields**
- Check `LI204` (field_missing) events in logs
- LinkedIn UI changes may require selector updates
- Review `extractors.py` selectors

**Low Post Counts**
- Profile may have limited public posts
- Check `LI102` (load_timeout) vs `LI103` (min_posts_met)
- Increase `--max-seconds` for sparse profiles

**Parse Errors**
- Check `LI203` (parse_warning) events
- HTML structure changes require code updates
- Capture DOM snippets for debugging

## Security & Compliance

### Data Handling
- No credentials stored (only session cookies)
- PII redaction in logs
- Output contains only public post data

### Session Security
```bash
# Optional: Encrypt session storage
# Implementation in browser.py with OS keyring

# Rotate sessions regularly
find out/session -name "*.json" -mtime +7 -delete
```

### Audit Trail
- All actions logged with timestamps
- Trace ID correlates single extraction run
- Event codes enable automated monitoring

## Deployment

### Environment Setup
```bash
# Production deployment
pip install li-extractor
playwright install chromium --with-deps

# Docker (example)
FROM python:3.11-slim
RUN apt-get update && apt-get install -y chromium
COPY requirements.txt .
RUN pip install -r requirements.txt
```

### Scheduling
```bash
# Cron example (daily extraction)
0 2 * * * cd /path/to/extractor && python -m li_extractor.cli --profile-url URL --headless >> cron.log 2>&1
```

### Monitoring Integration
```bash
# Send metrics to monitoring system
cat out/run.log | jq -r 'select(.metrics) | [.ts, .metrics.total_posts] | @csv'

# Alert on errors
grep "LI9" out/run.log && echo "ALERT: Extraction errors detected"
```

## Maintenance

### Regular Tasks
1. **Weekly**: Review log event patterns
2. **Monthly**: Update Playwright browser
3. **Quarterly**: Validate selectors against LinkedIn UI changes

### Updates
```bash
# Update browsers
playwright install chromium

# Update dependencies  
pip install --upgrade li-extractor

# Test after updates
make test
```

### Backup
```bash
# Backup session (encrypted recommended)
cp -r out/session/ backup/session-$(date +%Y%m%d)/

# Archive logs
gzip out/run.log && mv out/run.log.gz logs/archive/
```

---

# CHANGELOG.md
# Changelog

All notable changes to the LinkedIn Posts Extractor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-27

### Added
- Initial release of LinkedIn Posts Extractor
- Enterprise-grade session management with zero credential storage
- Structured JSON logging with event codes and trace correlation
- Human-like automation with configurable rate limiting (100-400ms jitter)
- Robust DOM extraction with graceful field handling
- Pydantic models with JSON Schema export
- Comprehensive test suite (unit + E2E)
- CLI with rich progress indicators
- Complete documentation and runbook
- Pre-commit hooks and CI/CD configuration

### Features
- **Session Management**: Playwright storage_state persistence, no credential storage
- **Navigation**: Direct URL construction + UI fallback navigation
- **Post Loading**: Incremental scrolling with timeout and minimum post limits
- **Data Extraction**: Author, timestamp, text, hashtags, links, engagement counts
- **Time Parsing**: Relative time normalization to ISO-8601 UTC
- **Rate Limiting**: Action tracking with ~1 action/second average
- **Output**: Schema-validated JSON with structured logging
- **Observability**: Event codes, trace correlation, timing metrics

### Technical
- Python 3.9+ support
- Playwright automation framework
- Pydantic for data validation
- Typer for CLI interface
- Rich for progress display
- Comprehensive linting (black, ruff, isort, mypy)
- pytest with coverage reporting
- GitHub Actions CI/CD

### Security
- Zero credential persistence (session cookies only)
- PII redaction in logs  
- Public post data only
- Optional session encryption at rest