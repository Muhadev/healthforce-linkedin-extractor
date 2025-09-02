# scripts/run_local.sh
#!/bin/bash
"""Local development runner script."""

set -e

# Default values
PROFILE_URL=${PROFILE_URL:-"https://www.linkedin.com/in/fayemi-muhammed/"}
MIN_POSTS=${MIN_POSTS:-10}
MAX_SECONDS=${MAX_SECONDS:-60}
OUT_DIR=${OUT_DIR:-"out"}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "Running LinkedIn Posts Extractor..."
echo "Profile: $PROFILE_URL"
echo "Min Posts: $MIN_POSTS"
echo "Max Time: ${MAX_SECONDS}s"
echo "Output: $OUT_DIR"
echo ""

python -m li_extractor.cli \
    --profile-url "$PROFILE_URL" \
    --min-posts "$MIN_POSTS" \
    --max-seconds "$MAX_SECONDS" \
    --out-dir "$OUT_DIR" \
    --log-level "$LOG_LEVEL" \
    --headful

echo ""
echo "Results saved to: $OUT_DIR/li_posts.json"
echo "Logs saved to: $OUT_DIR/run.log"