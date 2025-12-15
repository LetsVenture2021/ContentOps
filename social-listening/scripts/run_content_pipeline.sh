#!/bin/bash
# Content Pipeline Orchestration Script
# 
# This script orchestrates the complete content automation pipeline:
# 1. Daily synthesis (aggregate content opportunities from mentions)
# 2. Content draft generation (generate platform-optimized drafts)
#
# Usage:
#   ./run_content_pipeline.sh [full|drafts-only]
#
# Options:
#   full        - Run complete pipeline (synthesis + draft generation)
#   drafts-only - Only run draft generation (skip synthesis)
#
# Cron Schedule (recommended):
#   # Run synthesis daily at 6 AM
#   0 6 * * * cd ~/ContentOps/social-listening && ./scripts/run_content_pipeline.sh full >> logs/pipeline.log 2>&1
#
#   # Run draft generation every 2 hours
#   0 */2 * * * cd ~/ContentOps/social-listening && ./scripts/run_content_pipeline.sh drafts-only >> logs/pipeline.log 2>&1

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$ROOT_DIR/logs"
PYTHON="${PYTHON:-python3}"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if virtual environment should be used
if [ -d "$ROOT_DIR/.venv" ]; then
    PYTHON="$ROOT_DIR/.venv/bin/python3"
    log "Using virtual environment: $ROOT_DIR/.venv"
fi

# Determine mode
MODE="${1:-full}"

log "=========================================="
log "CONTENT PIPELINE - STARTING ($MODE mode)"
log "=========================================="

# Check environment
if [ ! -f "$ROOT_DIR/.env" ]; then
    error_exit ".env file not found in $ROOT_DIR"
fi

# Step 1: Daily Synthesis (if full mode)
if [ "$MODE" = "full" ]; then
    log "Step 1: Running daily synthesis..."
    
    if ! $PYTHON "$SCRIPT_DIR/daily_synthesis.py"; then
        log "WARNING: Daily synthesis failed, but continuing..."
    else
        log "✓ Daily synthesis completed"
    fi
    
    # Brief pause between steps
    sleep 2
fi

# Step 2: Content Draft Generation
log "Step 2: Generating content drafts..."

if ! $PYTHON "$SCRIPT_DIR/generate_content_draft.py"; then
    error_exit "Content draft generation failed"
fi

log "✓ Content draft generation completed"

log "=========================================="
log "CONTENT PIPELINE - COMPLETED"
log "=========================================="

# Optional: Send completion notification
# Uncomment and configure if you want email/slack notifications
# if [ "$MODE" = "full" ]; then
#     echo "Pipeline completed successfully at $(date)" | mail -s "Content Pipeline Success" your-email@example.com
# fi

exit 0
